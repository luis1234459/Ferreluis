"""
Migracion para la nueva jerarquia Subcategoria (Departamento -> Categoria ->
Subcategoria -> Marca).

La tabla `subcategorias` es nueva (no existe en produccion todavia), asi que
`Base.metadata.create_all(bind=engine)` en el arranque normal de main.py ya
la crea sola -- create_all no toca tablas que ya existen, pero si crea las
que faltan. Lo unico que create_all NO puede hacer es agregar una columna
nueva a una tabla que ya existe (`productos`), asi que este script hace
exactamente eso: agrega `productos.subcategoria_id` (nullable, arranca en
NULL para todos los productos existentes).

Es idempotente: si la columna ya existe, no hace nada (ni en dry-run ni con
--aplicar).

Uso: python agregar_subcategoria.py            (dry-run, solo diagnostica)
     python agregar_subcategoria.py --aplicar   (ejecuta el ALTER TABLE)
"""
import sys
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from database import SessionLocal, engine


def columna_existe(db: Session) -> bool:
    insp = inspect(engine)
    columnas = [c["name"] for c in insp.get_columns("productos")]
    return "subcategoria_id" in columnas


def main():
    aplicar_cambios = "--aplicar" in sys.argv
    db = SessionLocal()
    try:
        existe = columna_existe(db)
        print(f"Columna productos.subcategoria_id ya existe: {existe}")

        if existe:
            print("\nNada que hacer -- la migracion ya fue aplicada antes.")
            return

        if not aplicar_cambios:
            print("\nDRY-RUN -- no se modifico nada. Correr con --aplicar para ejecutar.")
            print("Se ejecutaria: ALTER TABLE productos ADD COLUMN subcategoria_id INTEGER")
            return

        db.execute(text("ALTER TABLE productos ADD COLUMN subcategoria_id INTEGER"))
        db.commit()
        print("\nColumna agregada. Verificando...")
        print(f"Post-migracion -- columna existe: {columna_existe(db)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
