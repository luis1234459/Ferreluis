"""
Script de seed: crea el usuario admin inicial.
Ejecutar una sola vez con: python seed.py
"""
import bcrypt
from database import engine, get_db, Base
from models import Usuario

# Asegura que todas las tablas existan
Base.metadata.create_all(bind=engine)

db = next(get_db())

# Borra si ya existe (por si se corre dos veces)
existente = db.query(Usuario).filter(Usuario.email == "admin@ferreutil.com").first()
if existente:
    print("Usuario admin ya existe.")
else:
    hashed = bcrypt.hashpw("admin1234".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    admin = Usuario(
        nombre   = "Administrador",
        email    = "admin@ferreutil.com",
        password = hashed,
        rol      = "admin",
    )
    db.add(admin)
    db.commit()
    print("OK - Usuario admin creado.")
    print("  Email:    admin@ferreutil.com")
    print("  Clave:    admin1234")
    print("  Rol:      admin")

db.close()
