"""
Rellena costo_usd para productos con costo faltante (0 o NULL), usando la
formula:

    costo_usd = precio_usd x 0.75

"precio_usd" = precio_unitario de la venta MAS RECIENTE de ese producto en
detalle_ventas (unico precio real, independiente del costo, disponible en
este sistema — se descarto costo*(1+margen) por circular, y no hay ningun
otro campo de precio guardado con cobertura mejor; confirmado con Luis).

Productos sin ninguna venta registrada (sin precio de referencia real) NO
se pueden calcular: quedan con costo_usd = 0 explicito (no NULL), tal cual
pedido — se reporta cuantos son al final, no es un error del script.

Aplica a los 201 productos con costo_usd = 0 OR costo_usd IS NULL, sin
excepciones (con o sin historial de ventas, todos entran).

Uso:
    cd backend
    python rellenar_costos.py                # solo preview, no toca la DB
    python rellenar_costos.py --ejecutar      # aplica el UPDATE real

Por defecto SOLO genera preview (imprime en consola, no escribe archivos —
a diferencia de recodificar_catalogo.py esto es chico, no necesita CSVs).
--ejecutar es el unico modo que escribe en la base: crea (si no existe)
backup_productos_costos persistente, inserta el backup de los 201, y hace
el UPDATE, todo en una sola transaccion con rollback total si algo falla.
"""
import os
import sys
import argparse
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from database import SessionLocal
import sqlalchemy as sa

FACTOR = 0.75


def cargar_afectados(db):
    """
    Devuelve lista de dict {producto_id, nombre, costo_viejo, precio_referencia,
    costo_nuevo} para los productos con costo_usd = 0 OR NULL. precio_referencia
    es el precio_unitario de la venta mas reciente (None si nunca se vendio).
    """
    filas = db.execute(sa.text("""
        SELECT p.id, p.nombre, p.costo_usd,
               (SELECT dv.precio_unitario
                  FROM detalle_ventas dv
                  JOIN ventas v ON v.id = dv.venta_id
                 WHERE dv.producto_id = p.id
                 ORDER BY v.fecha DESC
                 LIMIT 1) AS precio_referencia
        FROM productos p
        WHERE p.costo_usd = 0 OR p.costo_usd IS NULL
        ORDER BY p.id
    """)).fetchall()

    afectados = []
    for r in filas:
        precio_ref = float(r.precio_referencia) if r.precio_referencia is not None else None
        if precio_ref is not None and precio_ref > 0:
            costo_nuevo = round(precio_ref * FACTOR, 4)
        else:
            costo_nuevo = 0.0  # sin precio de referencia real -> queda en 0 explicito, no NULL
        afectados.append({
            "producto_id": r.id,
            "nombre": r.nombre,
            "costo_viejo": r.costo_usd,
            "precio_referencia": precio_ref,
            "costo_nuevo": costo_nuevo,
        })
    return afectados


def ejecutar_update(db, afectados):
    try:
        db.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS backup_productos_costos (
                producto_id INTEGER NOT NULL,
                costo_viejo NUMERIC,
                costo_nuevo NUMERIC,
                fecha_actualizacion TIMESTAMP DEFAULT NOW()
            )
        """))

        params = [{"producto_id": a["producto_id"], "costo_viejo": a["costo_viejo"], "costo_nuevo": a["costo_nuevo"]}
                  for a in afectados]

        db.execute(sa.text("""
            INSERT INTO backup_productos_costos (producto_id, costo_viejo, costo_nuevo)
            VALUES (:producto_id, :costo_viejo, :costo_nuevo)
        """), params)

        db.execute(sa.text("UPDATE productos SET costo_usd = :costo_nuevo WHERE id = :producto_id"), params)

        db.commit()
    except Exception:
        db.rollback()
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ejecutar", action="store_true", help="Aplica el UPDATE real. Sin esto, solo preview.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        afectados = cargar_afectados(db)
        con_precio = [a for a in afectados if a["precio_referencia"] is not None and a["precio_referencia"] > 0]
        sin_precio = [a for a in afectados if a not in con_precio]

        print(f"Total con costo faltante: {len(afectados)}")
        print(f"  - se calculan con precio real de venta: {len(con_precio)}")
        print(f"  - sin precio de referencia (quedan en costo=0): {len(sin_precio)}")

        if args.ejecutar:
            print("\n--ejecutar detectado: aplicando UPDATE...")
            t0 = time.monotonic()
            ejecutar_update(db, afectados)
            segundos = time.monotonic() - t0

            print("\n=== RESUMEN FINAL ===")
            print(f"Total actualizados: {len(afectados)}")
            print(f"Con costo calculado desde precio real: {len(con_precio)}")
            print(f"Sin precio de referencia, quedaron en costo=0: {len(sin_precio)}")
            print(f"Tiempo total de ejecucion: {segundos:.1f}s")
        else:
            print("\nSolo preview (sin --ejecutar). La base NO fue modificada.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
