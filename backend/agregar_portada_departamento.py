"""
Migracion para "producto portada de departamento".

Agrega `productos.es_portada_departamento` (BOOLEAN, default FALSE) -- marca
cual producto representa a su departamento en el mosaico del catalogo
publico (reemplaza la heuristica de "primer producto con foto" del sitio).

Es idempotente: si la columna ya existe, no hace nada (ni en dry-run ni con
--aplicar).

Uso: python agregar_portada_departamento.py            (dry-run, solo diagnostica)
     python agregar_portada_departamento.py --aplicar   (ejecuta el ALTER TABLE)

Nota: backend/.env puede tener un DATABASE_URL de produccion (Luis lo deja ahi
para scripts manuales puntuales). Este script no importa main.py (no corre
load_dotenv), asi que por defecto usa sqlite local salvo que DATABASE_URL ya
este seteada en el entorno -- igual se fuerza explicito abajo por seguridad.
Para aplicar contra produccion a proposito, exportar DATABASE_URL con el DSN
real antes de correr con --aplicar.
"""
import os
import sys

if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "sqlite:///./ferreteria.db"

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from database import SessionLocal, engine


def columna_existe(db: Session) -> bool:
    insp = inspect(engine)
    columnas = [c["name"] for c in insp.get_columns("productos")]
    return "es_portada_departamento" in columnas


def main():
    aplicar_cambios = "--aplicar" in sys.argv
    db = SessionLocal()
    try:
        existe = columna_existe(db)
        print(f"Columna productos.es_portada_departamento ya existe: {existe}")

        if existe:
            print("\nNada que hacer -- la migracion ya fue aplicada antes.")
            return

        if not aplicar_cambios:
            print("\nDRY-RUN -- no se modifico nada. Correr con --aplicar para ejecutar.")
            print("Se ejecutaria: ALTER TABLE productos ADD COLUMN es_portada_departamento BOOLEAN DEFAULT FALSE")
            return

        db.execute(text("ALTER TABLE productos ADD COLUMN es_portada_departamento BOOLEAN DEFAULT FALSE"))
        db.commit()
        print("\nColumna agregada. Verificando...")
        print(f"Post-migracion -- columna existe: {columna_existe(db)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
