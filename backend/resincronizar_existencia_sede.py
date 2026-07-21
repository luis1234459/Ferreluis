"""
Resincronizacion de existencia_sede contra productos.stock (sede Ojeda, id=1).

Contexto: la Fase 1A hizo un backfill de existencia_sede en un solo momento
(20-jul). Desde entonces, productos.stock sigue siendo la unica fuente real
(nada lee/escribe existencia_sede todavia), y ademas se crearon o modificaron
variantes activas despues de esa fecha. Resultado: existencia_sede quedo
desincronizada de dos formas:

  1. Productos SIN variante activa que faltan en existencia_sede (nuevos
     desde 1A, o que perdieron su variante activa despues) -> se insertan.
  2. Productos SIN variante activa que ya tienen fila pero con `existencia`
     distinta de `productos.stock` (drift acumulado) -> se actualiza.
  3. Productos CON variante activa que igual tienen fila en existencia_sede
     (invariante violado: "sin fila = vive en flujo de variantes") -> se
     borran, para que la ausencia de fila vuelva a ser una senal confiable.

Es idempotente: correrlo de nuevo sin cambios de por medio no modifica nada.
Uso: python resincronizar_existencia_sede.py           (dry-run, solo cuenta)
     python resincronizar_existencia_sede.py --aplicar  (ejecuta los cambios)
"""
import sys
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import SessionLocal

SEDE_ID = 1  # Ojeda — unica sede con historia real hasta ahora


def diagnosticar(db: Session) -> dict:
    faltantes = db.execute(text("""
        SELECT p.id FROM productos p
        WHERE NOT EXISTS (SELECT 1 FROM variantes_producto vp WHERE vp.producto_id = p.id AND vp.activo = TRUE)
          AND NOT EXISTS (SELECT 1 FROM existencia_sede es WHERE es.producto_id = p.id AND es.sede_id = :sede)
    """), {"sede": SEDE_ID}).fetchall()

    desincronizados = db.execute(text("""
        SELECT es.producto_id, es.existencia, p.stock
        FROM existencia_sede es JOIN productos p ON p.id = es.producto_id
        WHERE es.sede_id = :sede AND es.existencia != p.stock
          AND NOT EXISTS (SELECT 1 FROM variantes_producto vp WHERE vp.producto_id = p.id AND vp.activo = TRUE)
    """), {"sede": SEDE_ID}).fetchall()

    huerfanos = db.execute(text("""
        SELECT es.id, es.producto_id FROM existencia_sede es
        WHERE es.sede_id = :sede
          AND EXISTS (SELECT 1 FROM variantes_producto vp WHERE vp.producto_id = es.producto_id AND vp.activo = TRUE)
    """), {"sede": SEDE_ID}).fetchall()

    return {"faltantes": faltantes, "desincronizados": desincronizados, "huerfanos": huerfanos}


def aplicar(db: Session, diag: dict):
    if diag["faltantes"]:
        db.execute(text("""
            INSERT INTO existencia_sede (producto_id, sede_id, existencia)
            SELECT p.id, :sede, p.stock FROM productos p
            WHERE NOT EXISTS (SELECT 1 FROM variantes_producto vp WHERE vp.producto_id = p.id AND vp.activo = TRUE)
              AND NOT EXISTS (SELECT 1 FROM existencia_sede es WHERE es.producto_id = p.id AND es.sede_id = :sede)
        """), {"sede": SEDE_ID})

    if diag["desincronizados"]:
        db.execute(text("""
            UPDATE existencia_sede
            SET existencia = (SELECT p.stock FROM productos p WHERE p.id = existencia_sede.producto_id)
            WHERE sede_id = :sede
              AND existencia != (SELECT p.stock FROM productos p WHERE p.id = existencia_sede.producto_id)
              AND NOT EXISTS (
                  SELECT 1 FROM variantes_producto vp
                  WHERE vp.producto_id = existencia_sede.producto_id AND vp.activo = TRUE
              )
        """), {"sede": SEDE_ID})

    if diag["huerfanos"]:
        ids = [row[0] for row in diag["huerfanos"]]
        db.execute(
            text("DELETE FROM existencia_sede WHERE id IN :ids").bindparams(
                __import__("sqlalchemy").bindparam("ids", expanding=True)
            ),
            {"ids": ids},
        )

    db.commit()


def main():
    aplicar_cambios = "--aplicar" in sys.argv
    db = SessionLocal()
    try:
        diag = diagnosticar(db)
        print(f"Productos sin fila que deberian tenerla (backfill pendiente): {len(diag['faltantes'])}")
        print(f"Filas desincronizadas (existencia != productos.stock):        {len(diag['desincronizados'])}")
        print(f"Filas huerfanas (producto ya tiene variante activa):          {len(diag['huerfanos'])}")

        if not aplicar_cambios:
            print("\nDRY-RUN — no se modifico nada. Correr con --aplicar para ejecutar.")
            return

        if not (diag["faltantes"] or diag["desincronizados"] or diag["huerfanos"]):
            print("\nNada que resincronizar.")
            return

        aplicar(db, diag)
        print("\nCambios aplicados. Verificando estado post-resync...")
        diag2 = diagnosticar(db)
        print(f"Post-resync — faltantes: {len(diag2['faltantes'])}, desincronizados: {len(diag2['desincronizados'])}, huerfanos: {len(diag2['huerfanos'])}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
