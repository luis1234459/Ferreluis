from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rutas import productos, ventas, usuarios, facturas, tasa, cierres, depositos, reportes, compras, bancos, clientes, vendedores, ajustes, dashboard, presupuestos, devoluciones, ubicaciones
from database import engine, SessionLocal
from database import Base
from config import ENVIRONMENT, FRONTEND_URL
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema Ferretería", version="1.0.0")

_origins = (
    [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    if ENVIRONMENT == "development"
    else [FRONTEND_URL]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(productos.router)
app.include_router(ventas.router)
app.include_router(usuarios.router)
app.include_router(facturas.router)
app.include_router(tasa.router)
app.include_router(cierres.router)
app.include_router(depositos.router)
app.include_router(reportes.router)
app.include_router(compras.router)
app.include_router(bancos.router)
app.include_router(clientes.router)
app.include_router(vendedores.router)
app.include_router(ajustes.router)
app.include_router(dashboard.router)
app.include_router(presupuestos.router)
app.include_router(devoluciones.router)
app.include_router(ubicaciones.router)


@app.on_event("startup")
def inicializar_datos():
    """
    Migración segura para SQLite y seed del cliente genérico 'Consumidor Final'.
    Se ejecuta cada vez que arranca el servidor; es idempotente.
    """
    db = SessionLocal()
    try:
        from sqlalchemy import text

        # ── Migración: agregar columna es_cliente_generico si no existe ──────
        try:
            db.execute(text(
                "ALTER TABLE clientes ADD COLUMN es_cliente_generico BOOLEAN DEFAULT 0"
            ))
            db.commit()
        except Exception:
            # La columna ya existe — ignorar
            db.rollback()

        # ── Migración: columnas nuevas en productos ───────────────────────────
        nuevas_columnas_productos = [
            ("departamento_id",         "INTEGER"),
            ("proveedor_id",            "INTEGER"),
            ("es_producto_clave",       "BOOLEAN DEFAULT 0"),
            ("es_producto_compuesto",   "BOOLEAN DEFAULT 0"),
            ("descuento_compuesto_pct", "FLOAT DEFAULT 0"),
            ("comision_pct",            "FLOAT DEFAULT 0"),
        ]
        for col, tipo in nuevas_columnas_productos:
            try:
                db.execute(text(f"ALTER TABLE productos ADD COLUMN {col} {tipo}"))
                db.commit()
            except Exception:
                db.rollback()

        # ── Migración: columna permisos en usuarios ───────────────────────────
        try:
            db.execute(text("ALTER TABLE usuarios ADD COLUMN permisos TEXT DEFAULT NULL"))
            db.commit()
        except Exception:
            db.rollback()

        # ── Migración: crédito de proveedores y tracking de pago ─────────────
        for sql in [
            "ALTER TABLE proveedores ADD COLUMN dias_credito INTEGER DEFAULT 0",
            "ALTER TABLE recepciones_compra ADD COLUMN fecha_vencimiento_pago DATE",
            "ALTER TABLE recepciones_compra ADD COLUMN monto_factura FLOAT",
            "ALTER TABLE recepciones_compra ADD COLUMN estado_pago TEXT DEFAULT 'pendiente'",
            "ALTER TABLE recepciones_compra ADD COLUMN fecha_pago_real DATETIME",
            "ALTER TABLE recepciones_compra ADD COLUMN numero_factura TEXT",
        ]:
            try:
                db.execute(text(sql))
                db.commit()
            except Exception:
                db.rollback()

        # ── Migración: crédito disponible en clientes y proveedores ──────────
        for sql in [
            "ALTER TABLE clientes ADD COLUMN credito_disponible FLOAT DEFAULT 0",
            "ALTER TABLE proveedores ADD COLUMN credito_disponible FLOAT DEFAULT 0",
        ]:
            try:
                db.execute(text(sql))
                db.commit()
            except Exception:
                db.rollback()

        # ── Seed: crear "Consumidor Final" si no existe ──────────────────────
        consumidor = db.query(models.Cliente).filter(
            models.Cliente.es_cliente_generico == True
        ).first()

        if not consumidor:
            db.add(models.Cliente(
                nombre              = "Consumidor Final",
                telefono            = "0000000000",
                tipo_cliente        = "natural",
                activo              = True,
                notas               = "Cliente genérico para ventas sin identificación",
                es_cliente_generico = True,
            ))
            db.commit()

    finally:
        db.close()


@app.get("/")
def inicio():
    return {"mensaje": "Sistema Ferretería funcionando correctamente"}

@app.get("/salud")
def salud():
    return {"estado": "activo"}
