"""
Reset selectivo de saldo inicial — Tanda A, decisión C de Luis (2026-07-23).

Luis revisó los 16 proveedores con saldo pendiente y decidió, uno por uno:
  - 5 MANTIENEN su saldo real (no se tocan en este script):
    CIN, DEC, RES, MIX, ICO
  - 11 se RESETEAN a cero porque ya están pagos y el sistema arrastra números
    viejos: FEB, DIS, PRV-0057, MMC, ZET, SIN, LAF, LIT, EXE, BEL, GRI

Por cada proveedor a resetear, crea un PagoProveedor tipo="ajuste_manual" por
exactamente su saldo_pendiente ACTUAL (recalculado en el momento de correr este
script, no un monto fijo hardcodeado) y lo aplica en cascada FIFO contra sus
recepciones pendientes hasta dejarlo en $0.00.

DEBE correrse DESPUÉS de backfill_pagos_proveedor.py --apply, nunca antes (si no,
el saldo "actual" que ve este script todavía sería el de antes del backfill).

Uso (desde backend/, con DATABASE_URL ya exportado en el entorno):
    python reset_selectivo_proveedores.py            # dry-run
    python reset_selectivo_proveedores.py --apply     # aplica de verdad
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models import Proveedor
from pagos_proveedor import PagoProveedor, aplicar_pago, resumen_deuda_proveedor

CODIGOS_A_RESETEAR = ["FEB", "DIS", "PRV-0057", "MMC", "ZET", "SIN", "LAF", "LIT", "EXE", "BEL", "GRI"]
CODIGOS_MANTIENEN  = ["CIN", "DEC", "RES", "MIX", "ICO"]  # solo para el chequeo de no-toque

CONCEPTO = "Reset saldo inicial Tanda A — aprobado por Luis 2026-07-23"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Aplica de verdad (default: dry-run)")
    args = parser.parse_args()

    db = SessionLocal()
    url = str(db.get_bind().url)
    print(f"# Conectado a: {url.split('@')[-1] if '@' in url else url}")
    print(f"# Modo: {'APPLY' if args.apply else 'DRY-RUN (solo lectura, se hace rollback al final)'}\n")

    try:
        print("-- Saldo ANTES del reset --")
        antes_mantienen = {}
        for cod in CODIGOS_MANTIENEN:
            p = db.query(Proveedor).filter(Proveedor.codigo == cod).first()
            if not p:
                print(f"  {cod}: NO ENCONTRADO — abortando"); db.rollback(); sys.exit(1)
            antes_mantienen[cod] = resumen_deuda_proveedor(db, p.id)["saldo_pendiente"]
            print(f"  {cod} (mantiene, no se toca): {antes_mantienen[cod]}")

        pagos_creados = []
        for cod in CODIGOS_A_RESETEAR:
            p = db.query(Proveedor).filter(Proveedor.codigo == cod).first()
            if not p:
                print(f"  {cod}: NO ENCONTRADO — abortando"); db.rollback(); sys.exit(1)
            saldo = resumen_deuda_proveedor(db, p.id)["saldo_pendiente"]
            print(f"  {cod} ({p.nombre}): saldo actual {saldo} -> se resetea a 0")
            if saldo <= 0.01:
                print(f"    (ya está en 0, no se crea ajuste)")
                continue
            pago = PagoProveedor(
                proveedor_id   = p.id,
                tipo           = "ajuste_manual",
                monto          = saldo,
                moneda         = "USD",
                monto_usd      = saldo,
                concepto       = CONCEPTO,
                registrado_por = "reset_tanda_a",
            )
            db.add(pago)
            db.flush()
            aplicar_pago(db, pago)
            pagos_creados.append((cod, saldo))

        db.flush()

        print("\n-- Verificación --")
        ok = True
        for cod in CODIGOS_MANTIENEN:
            p = db.query(Proveedor).filter(Proveedor.codigo == cod).first()
            despues = resumen_deuda_proveedor(db, p.id)["saldo_pendiente"]
            if abs(despues - antes_mantienen[cod]) > 0.02:
                print(f"  ❌ {cod} cambió de {antes_mantienen[cod]} a {despues} — NO debía tocarse")
                ok = False
            else:
                print(f"  ✅ {cod} sigue en {despues} (sin cambios)")

        for cod in CODIGOS_A_RESETEAR:
            p = db.query(Proveedor).filter(Proveedor.codigo == cod).first()
            despues = resumen_deuda_proveedor(db, p.id)["saldo_pendiente"]
            if abs(despues) > 0.02:
                print(f"  ❌ {cod} debía quedar en 0, quedó en {despues}")
                ok = False
            else:
                print(f"  ✅ {cod} quedó en {despues}")

        if not ok:
            print("\n❌ Verificación falló — rollback, no se aplica nada.")
            db.rollback()
            sys.exit(1)

        print(f"\n✅ {len(pagos_creados)} ajuste(s) de reset creados correctamente.")

        if not args.apply:
            print("\nDry-run OK. Rollback (no se escribió nada). Corré con --apply para aplicar de verdad.")
            db.rollback()
            return

        db.commit()
        print("✅ APPLY commiteado.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
