"""
Cierre de caja.

Los montos esperados se calculan desde PagoVenta:
cada método se suma en su moneda nativa (USD para métodos USD, Bs para Bs).
El cajero ingresa lo que físicamente contó en cada "caja/cuenta".
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from database import get_db
from models import Venta, PagoVenta, CierreCaja, CuentaBancaria, MovimientoBancario, MetodoPagoCuenta, METODOS_VALIDOS
from rutas.usuarios import require_admin

router = APIRouter(prefix="/cierres", tags=["cierres"])

ALL_METODOS = [
    "efectivo_usd", "zelle", "binance",
    "efectivo_bs", "transferencia_bs", "pago_movil",
    "punto_banesco", "punto_provincial",
]


def _calcular_totales_por_metodo(pagos: list) -> dict:
    """
    Suma monto_original por método de pago.
    Cada método se mantiene en su moneda nativa.
    """
    totales = {m: 0.0 for m in ALL_METODOS}
    for p in pagos:
        if p.metodo_pago in totales:
            totales[p.metodo_pago] = round(
                totales[p.metodo_pago] + float(p.monto_original or 0), 2
            )
    return totales


def _total_ventas_en_usd(ventas: list) -> float:
    """
    Normaliza todos los totales de ventas a USD para el resumen del cierre.
    - Venta en USD  → total directo
    - Venta en Bs   → total / tasa_bcv
    """
    total = 0.0
    for v in ventas:
        t = float(v.total or 0)
        if v.moneda_venta == "USD":
            total += t
        elif v.moneda_venta == "Bs":
            tasa = float(v.tasa_bcv or 1)
            total += round(t / tasa, 2) if tasa > 0 else 0
    return round(total, 2)


@router.get("/resumen")
def resumen_caja(db: Session = Depends(get_db)):
    ultimo  = db.query(CierreCaja).order_by(CierreCaja.id.desc()).first()
    desde   = ultimo.fecha_hasta if ultimo else None

    q = db.query(Venta)
    if desde:
        q = q.filter(Venta.fecha > desde)
    ventas = q.all()

    if not ventas:
        return {
            "totales":         {m: 0.0 for m in ALL_METODOS},
            "cantidad_ventas": 0,
            "total_usd":       0.0,
            "desde":           desde.isoformat() if desde else None,
            "hasta":           datetime.now().isoformat(),
        }

    venta_ids = [v.id for v in ventas]
    pagos     = db.query(PagoVenta).filter(
        PagoVenta.venta_id.in_(venta_ids)
    ).all()

    return {
        "totales":         _calcular_totales_por_metodo(pagos),
        "cantidad_ventas": len(ventas),
        "total_usd":       _total_ventas_en_usd(ventas),
        "desde":           desde.isoformat() if desde else None,
        "hasta":           datetime.now().isoformat(),
    }


@router.post("/")
def cerrar_caja(data: dict, db: Session = Depends(get_db)):
    ultimo  = db.query(CierreCaja).order_by(CierreCaja.id.desc()).first()
    desde   = ultimo.fecha_hasta if ultimo else None
    ahora   = datetime.now()

    q = db.query(Venta)
    if desde:
        q = q.filter(Venta.fecha > desde)
    ventas = q.all()

    if not ventas:
        raise HTTPException(status_code=400,
                            detail="No hay ventas pendientes de cierre")

    venta_ids = [v.id for v in ventas]
    pagos     = db.query(PagoVenta).filter(
        PagoVenta.venta_id.in_(venta_ids)
    ).all()

    esperados = _calcular_totales_por_metodo(pagos)
    contados  = data.get("contados", {})

    cierre = CierreCaja(
        fecha               = ahora,
        usuario             = data.get("usuario", ""),
        fecha_desde         = desde,
        fecha_hasta         = ahora,
        cantidad_ventas     = len(ventas),
        total_ventas_usd    = _total_ventas_en_usd(ventas),

        esp_efectivo_usd    = esperados["efectivo_usd"],
        esp_zelle           = esperados["zelle"],
        esp_binance         = esperados["binance"],
        esp_efectivo_bs     = esperados["efectivo_bs"],
        esp_transferencia_bs= esperados["transferencia_bs"],
        esp_pago_movil      = esperados["pago_movil"],
        esp_punto_banesco   = esperados["punto_banesco"],
        esp_punto_provincial= esperados["punto_provincial"],

        cnt_efectivo_usd    = float(contados.get("efectivo_usd")    or 0),
        cnt_zelle           = float(contados.get("zelle")           or 0),
        cnt_binance         = float(contados.get("binance")         or 0),
        cnt_efectivo_bs     = float(contados.get("efectivo_bs")     or 0),
        cnt_transferencia_bs= float(contados.get("transferencia_bs")or 0),
        cnt_pago_movil      = float(contados.get("pago_movil")      or 0),
        cnt_punto_banesco   = float(contados.get("punto_banesco")   or 0),
        cnt_punto_provincial= float(contados.get("punto_provincial")or 0),

        observacion         = data.get("observacion", ""),
    )
    db.add(cierre)
    db.flush()  # obtener cierre.id antes del commit

    # -----------------------------------------------------------------------
    # Crear movimientos bancarios por cuenta destino
    # Agrupa los pagos por cuenta_destino_id y crea un ingreso_venta por cuenta
    # -----------------------------------------------------------------------
    acumulado = {}  # {cuenta_id: {monto, moneda, metodo_pago}}

    for p in pagos:
        cid = p.cuenta_destino_id
        if not cid:
            # Si el pago no tiene cuenta asignada, buscar la cuenta por defecto del método
            link = db.query(MetodoPagoCuenta).filter(
                MetodoPagoCuenta.metodo_pago == p.metodo_pago,
                MetodoPagoCuenta.activo == True,
            ).first()
            cid = link.cuenta_id if link else None

        if not cid:
            continue

        monto = float(p.monto_original or 0)
        if monto <= 0:
            continue

        # Determinar moneda del pago
        from models import METODOS_USD
        moneda = "USD" if p.metodo_pago in METODOS_USD else "Bs"

        if cid not in acumulado:
            acumulado[cid] = {"monto": 0.0, "moneda": moneda, "metodo": p.metodo_pago}
        acumulado[cid]["monto"] = round(acumulado[cid]["monto"] + monto, 2)

    for cid, info in acumulado.items():
        if info["monto"] <= 0:
            continue
        mov = MovimientoBancario(
            fecha             = ahora,
            tipo              = "ingreso_venta",
            cuenta_origen_id  = None,
            cuenta_destino_id = cid,
            monto             = info["monto"],
            moneda            = info["moneda"],
            concepto          = f"Cierre de caja #{cierre.id} - {info['metodo']}",
            categoria         = "ventas",
            referencia        = f"cierre_{cierre.id}",
        )
        db.add(mov)

    db.commit()
    db.refresh(cierre)

    return {"ok": True, "cierre_id": cierre.id}


@router.get("/pendientes/", dependencies=[Depends(require_admin)])
def cierres_pendientes(db: Session = Depends(get_db)):
    cierres = db.query(CierreCaja).filter(
        CierreCaja.estado_revision == "pendiente"
    ).order_by(CierreCaja.id.desc()).all()
    return [_serializar_cierre(c, db) for c in cierres]


@router.put("/{cierre_id}/revisar", dependencies=[Depends(require_admin)])
def revisar_cierre(cierre_id: int, datos: dict, db: Session = Depends(get_db)):
    c = db.query(CierreCaja).filter(CierreCaja.id == cierre_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cierre no encontrado")

    estado_rev = datos.get("estado_revision", "aprobado")
    if estado_rev not in ("aprobado", "con_diferencias"):
        raise HTTPException(status_code=400, detail="estado_revision debe ser 'aprobado' o 'con_diferencias'")

    c.revisado_por    = datos.get("revisado_por", "admin")
    c.fecha_revision  = datetime.now()
    c.estado_revision = estado_rev
    c.nota_revision   = datos.get("nota_revision")
    db.commit()
    return _serializar_cierre(c, db)


@router.get("/")
def listar_cierres(db: Session = Depends(get_db)):
    cierres = db.query(CierreCaja).order_by(CierreCaja.id.desc()).all()
    return [_serializar_cierre(c, db) for c in cierres]


def _serializar_cierre(c: CierreCaja, db: Session) -> dict:
    """Desglose por cuenta bancaria real usando cuenta_destino_id de PagoVenta."""
    # Ventas del período
    q = db.query(Venta)
    if c.fecha_desde:
        q = q.filter(Venta.fecha > c.fecha_desde)
    q = q.filter(Venta.fecha <= c.fecha_hasta)
    ventas = q.all()
    venta_ids = [v.id for v in ventas]

    pagos = db.query(PagoVenta).filter(PagoVenta.venta_id.in_(venta_ids)).all() if venta_ids else []

    # Desglose por cuenta destino
    desglose_cuentas = {}
    for p in pagos:
        cid = p.cuenta_destino_id
        if not cid:
            continue
        if cid not in desglose_cuentas:
            cuenta = db.query(CuentaBancaria).filter(CuentaBancaria.id == cid).first()
            desglose_cuentas[cid] = {
                "cuenta_id":     cid,
                "cuenta_nombre": cuenta.nombre if cuenta else f"Cuenta #{cid}",
                "moneda":        cuenta.moneda if cuenta else "?",
                "metodo_pago":   p.metodo_pago,
                "esperado":      0.0,
                "contado":       0.0,
            }
        desglose_cuentas[cid]["esperado"] = round(
            desglose_cuentas[cid]["esperado"] + float(p.monto_original or 0), 2
        )

    return {
        "id":              c.id,
        "fecha":           c.fecha.isoformat() if c.fecha else None,
        "usuario":         c.usuario,
        "cantidad_ventas": c.cantidad_ventas,
        "total_ventas_usd":c.total_ventas_usd,
        "observacion":     c.observacion,
        "estado_revision": c.estado_revision,
        "revisado_por":    c.revisado_por,
        "fecha_revision":  c.fecha_revision.isoformat() if c.fecha_revision else None,
        "nota_revision":   c.nota_revision,
        "desglose_cuentas":list(desglose_cuentas.values()),
        "totales": {
            "efectivo_usd":    c.esp_efectivo_usd,
            "zelle":           c.esp_zelle,
            "binance":         c.esp_binance,
            "efectivo_bs":     c.esp_efectivo_bs,
            "transferencia_bs":c.esp_transferencia_bs,
            "pago_movil":      c.esp_pago_movil,
            "punto_banesco":   c.esp_punto_banesco,
            "punto_provincial":c.esp_punto_provincial,
        },
    }
