"""
Backfill 1:1 de pagos historicos de proveedores al nuevo modelo pagos_proveedor /
pago_proveedor_aplicacion / saldo_favor_proveedor (Tanda A, aprobado por Luis
2026-07-23 — ver plan velvet-sparking-storm).

Fuentes migradas (53 eventos reales en produccion, verificado por lectura directa):
  - 46 MovimientoBancario tipo=pago_proveedor, estado=registrado         -> PagoProveedor tipo="pago"
  - 7  MovimientoBancario tipo=ajuste_deuda_proveedor, estado=registrado -> PagoProveedor tipo="ajuste_manual"

NOTA sobre las 3 recepciones "fantasma" del proveedor LIT (id 6, recepciones 18/20/40):
estan marcadas estado_pago="pagado" via el extinto PUT /compras/facturas/{id}/pagar,
pero NO tienen NINGUN movimiento bancario ni ajuste que las respalde -- ni siquiera un
registro parcial. A diferencia de lo que se penso al principio, esto NO se trata como
"pago legitimo sin registrar": no hay ninguna evidencia de que se haya pagado algo, asi
que backfillear un pago sintetico para justificarlas seria inventar historia financiera.
Se dejan sin aplicaciones -- recalcular_estado_pago las vuelve a "pendiente", que es lo
que la plata real dice. Como LIT esta en el grupo de 11 proveedores que Luis aprobo
resetear a cero, esto no cambia el resultado final, pero SI es un hallazgo a reportarle
aparte (documentado en el resumen que imprime este script).

Cada evento se aplica en cascada FIFO (misma logica que aplicar_pago en produccion):
  - Si el MovimientoBancario original tenia orden_compra_id (35 de los 46), la cascada
    se limita a las recepciones de ESA orden -- no a todo el historial del proveedor.
    Sin este scope, un pago dirigido a una factura puntual termina cascadeando sobre
    facturas mas viejas del mismo proveedor que en la realidad quedaron pendientes a
    proposito (confirmado con el dry-run inicial: sin este scope daba 24 discrepancias
    de estado_pago que no existian con el scope puesto).
  - Si no la tenia (11 pagos generales + los 7 ajustes), cascada FIFO contra todo el
    historial de recepciones pendientes del proveedor, en orden cronologico de eventos.
El sobrante de cualquiera de los dos casos genera saldo_favor_proveedor.

Validacion (la que bloquea el --apply): el SALDO AGREGADO por proveedor (facturado
menos aplicado) debe coincidir, proveedor por proveedor, con el que calculaba el
sistema viejo (orden.total sumado menos movimientos_bancarios reales) -- ese es el
numero que Luis ya reviso y aprobo (los $30,684.36 de los 16 proveedores). El
estado_pago individual de cada recepcion PUEDE cambiar respecto al valor actual (por
ejemplo de "pendiente" a "pagado" cuando un pago con orden_compra_id la cubria pero
nunca se reflejo a nivel de recepcion) -- eso es la mejora que trae Tanda A, no un
error, así que no se compara recepcion por recepcion como gate.

Uso (desde backend/, con DATABASE_URL ya exportado en el entorno — este script NO
carga .env solo, hay que setearlo explicitamente antes de correrlo):
    python backfill_pagos_proveedor.py            # dry-run: no escribe nada
    python backfill_pagos_proveedor.py --apply     # aplica de verdad: crea las tablas
                                                    # de backup, inserta todo en una
                                                    # transaccion, hace commit SOLO si
                                                    # el dry-run interno da limpio

Nunca hace commit si hay una sola discrepancia de saldo agregado sin explicar.
"""
import os
import sys
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from database import SessionLocal
from models import MovimientoBancario, RecepcionCompra, OrdenCompra, Proveedor
from pagos_proveedor import (
    PagoProveedor, aplicar_pago, pendiente_recepcion, resumen_deuda_proveedor,
    recalcular_estado_pago,
)

TOLERANCIA = 0.05


def _monto_usd_movimiento(m: MovimientoBancario) -> float:
    if m.moneda == "Bs":
        return round(float(m.monto_convertido or 0), 2)
    return round(float(m.monto or 0), 2)


def cargar_eventos(db):
    """Devuelve lista de dicts {proveedor_id, fecha, tipo, monto, moneda, tasa_cambio,
    monto_usd, movimiento_bancario_id, concepto, orden_compra_id}, orden cronologico
    global (se agrupa por proveedor al aplicar)."""
    eventos = []

    movimientos = db.query(MovimientoBancario).filter(
        MovimientoBancario.tipo.in_(["pago_proveedor", "ajuste_deuda_proveedor"]),
        MovimientoBancario.estado == "registrado",
    ).order_by(MovimientoBancario.fecha.asc()).all()

    for m in movimientos:
        if not m.proveedor_id:
            continue
        eventos.append({
            "proveedor_id":           m.proveedor_id,
            "fecha":                  m.fecha or datetime.now(),
            "tipo":                   "pago" if m.tipo == "pago_proveedor" else "ajuste_manual",
            "monto":                  float(m.monto or 0),
            "moneda":                 m.moneda,
            "tasa_cambio":            m.tasa_cambio,
            "monto_usd":              _monto_usd_movimiento(m),
            "movimiento_bancario_id": m.id,
            "concepto":               m.concepto or "Backfill Tanda A",
            "orden_compra_id":        m.orden_compra_id,
        })

    eventos.sort(key=lambda e: e["fecha"])
    return eventos


def _cascada_manual_en_cola(db, disponible: float, cola) -> list:
    """FIFO manual sobre una cola de recepciones ya filtrada/ordenada. Lo que no
    alcance a cubrir la cola simplemente no se lista — el sobrante lo resuelve
    aplicar_pago() como saldo a favor."""
    aplicaciones = []
    for r in cola:
        if disponible <= 0.01:
            break
        pend = pendiente_recepcion(db, r)
        if pend <= 0.01:
            continue
        monto = round(min(pend, disponible), 2)
        aplicaciones.append({"recepcion_id": r.id, "monto": monto})
        disponible = round(disponible - monto, 2)
    return aplicaciones


def aplicar_eventos(db, eventos, registrado_por="backfill_tanda_a"):
    """Crea los PagoProveedor + aplica cascada para cada evento. No hace commit."""
    creados = []
    for ev in eventos:
        pago = PagoProveedor(
            proveedor_id            = ev["proveedor_id"],
            fecha                   = ev["fecha"],
            tipo                    = ev["tipo"],
            monto                   = ev["monto"],
            moneda                  = ev["moneda"],
            tasa_cambio             = ev["tasa_cambio"],
            monto_usd               = ev["monto_usd"],
            concepto                = ev["concepto"],
            registrado_por          = registrado_por,
            movimiento_bancario_id  = ev["movimiento_bancario_id"],
        )
        db.add(pago)
        db.flush()

        if ev["orden_compra_id"]:
            # Pago histórico tenía una orden asociada: cascada FIFO SOLO dentro de
            # esa orden, no contra todo el historial del proveedor.
            cola = (
                db.query(RecepcionCompra)
                .filter(
                    RecepcionCompra.orden_id == ev["orden_compra_id"],
                    RecepcionCompra.monto_factura.isnot(None),
                    RecepcionCompra.devuelta == False,  # noqa: E712
                )
                .order_by(RecepcionCompra.fecha_recepcion.asc(), RecepcionCompra.id.asc())
                .all()
            )
            aplicaciones = _cascada_manual_en_cola(db, ev["monto_usd"], cola)
            aplicar_pago(db, pago, aplicaciones_manuales=aplicaciones)
        else:
            # Pago general del proveedor (11 de los 46) o ajuste manual (7): cascada
            # FIFO contra todo el historial del proveedor, como corresponde.
            aplicar_pago(db, pago)

        creados.append(pago)
    return creados


def saldo_viejo_sistema1(db, proveedor_id: int) -> float:
    """Reproduce la formula que usaba /bancos/proveedores/deuda/ ANTES de Tanda A,
    independiente de estado_pago -- es el numero que Luis ya revisó y aprobó."""
    ordenes = db.query(OrdenCompra).filter(
        OrdenCompra.proveedor_id == proveedor_id,
        OrdenCompra.estado.in_(["recibida_parcial", "cerrada"]),
    ).all()
    total_comprado = sum(float(o.total or 0) for o in ordenes)
    pagos = db.query(MovimientoBancario).filter(
        MovimientoBancario.proveedor_id == proveedor_id,
        MovimientoBancario.tipo.in_(["pago_proveedor", "ajuste_deuda_proveedor"]),
        MovimientoBancario.estado == "registrado",
    ).all()
    pagado = sum(
        float(m.monto_convertido or 0) if m.moneda == "Bs" else float(m.monto or 0)
        for m in pagos
    )
    return round(total_comprado - pagado, 2)


def comparar_saldos_agregados(db, proveedor_ids) -> list:
    """Compara, proveedor por proveedor, el saldo agregado viejo vs el nuevo motor.
    Devuelve lista de (proveedor_id, nombre, saldo_viejo, saldo_nuevo, diff) para los
    que excedan la tolerancia."""
    discrepancias = []
    for pid in proveedor_ids:
        viejo = saldo_viejo_sistema1(db, pid)
        nuevo = resumen_deuda_proveedor(db, pid)["saldo_pendiente"]
        diff = round(nuevo - viejo, 2)
        if abs(diff) > TOLERANCIA:
            p = db.query(Proveedor).filter(Proveedor.id == pid).first()
            discrepancias.append((pid, p.nombre if p else "?", viejo, nuevo, diff))
    return discrepancias


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Aplica de verdad (default: dry-run)")
    args = parser.parse_args()

    db = SessionLocal()
    url = str(db.get_bind().url)
    print(f"# Conectado a: {url.split('@')[-1] if '@' in url else url}")
    print(f"# Modo: {'APPLY' if args.apply else 'DRY-RUN (solo lectura, se hace rollback al final)'}\n")

    try:
        eventos = cargar_eventos(db)
        print(f"Eventos a backfillear: {len(eventos)}")

        proveedor_ids = sorted({ev["proveedor_id"] for ev in eventos} | {
            p.id for p in db.query(Proveedor).filter(Proveedor.activo == True).all()
        })

        fecha_tag = "20260723"
        if args.apply:
            # Backup ANTES de mutar nada — misma transacción, se comitea junto con
            # el resto solo si todo da limpio (si no, el rollback también lo deshace).
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS backup_pagos_proveedor_reset_{fecha_tag} AS
                SELECT * FROM movimientos_bancarios
                WHERE tipo IN ('pago_proveedor', 'ajuste_deuda_proveedor') AND estado = 'registrado'
            """))
            db.execute(text(f"""
                CREATE TABLE IF NOT EXISTS backup_recepciones_compra_reset_{fecha_tag} AS
                SELECT * FROM recepciones_compra
            """))
            db.flush()

        pagos = aplicar_eventos(db, eventos)
        db.flush()

        # Normaliza estado_pago de TODAS las recepciones a crédito, no solo las que
        # tocó algún evento — deja atrás cualquier estado seteado a mano (ej. LIT
        # 18/20/40, "pagado" sin ningún respaldo) y las alinea con la plata real.
        recepciones_credito = db.query(RecepcionCompra).filter(RecepcionCompra.monto_factura.isnot(None)).all()
        for r in recepciones_credito:
            recalcular_estado_pago(db, r)
        db.flush()

        discrepancias = comparar_saldos_agregados(db, proveedor_ids)

        if discrepancias:
            print(f"\n❌ {len(discrepancias)} proveedor(es) con saldo agregado distinto (tolerancia ${TOLERANCIA}) — NO se aplica nada:\n")
            for pid, nombre, viejo, nuevo, diff in discrepancias:
                print(f"  proveedor {pid} ({nombre}): sistema1={viejo}  backfill={nuevo}  diff={diff}")
            db.rollback()
            sys.exit(1)

        print(f"\n✅ 0 discrepancias de saldo agregado sobre {len(proveedor_ids)} proveedores.")
        print(f"   {len(pagos)} pagos_proveedor creados, cascada aplicada correctamente.")

        # Aviso informativo (no bloquea): recepciones LIT sin ningún respaldo real.
        lit_ids = [18, 20, 40]
        lit_estados = {r.id: r.estado_pago for r in db.query(RecepcionCompra).filter(RecepcionCompra.id.in_(lit_ids)).all()}
        print(f"\n⚠ Recepciones {lit_ids} (proveedor LIT/id 6): marcadas 'pagado' hoy sin NINGÚN respaldo de "
              f"plata en ningún lado. Tras el backfill vuelven a estado_pago={lit_estados} (ningún evento real "
              f"las cubre). No afecta el resultado final porque LIT está en el grupo de 11 a resetear a cero.")

        if not args.apply:
            print("\nDry-run OK. Rollback (no se escribió nada). Corré con --apply para aplicar de verdad.")
            db.rollback()
            return

        db.commit()
        print(f"\nBackup creado: backup_pagos_proveedor_reset_{fecha_tag}, backup_recepciones_compra_reset_{fecha_tag}")
        print(f"✅ APPLY commiteado: {len(pagos)} pagos_proveedor + aplicaciones.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
