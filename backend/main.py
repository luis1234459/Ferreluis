from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rutas import productos, ventas, usuarios, facturas, tasa, cierres, depositos, reportes, compras, bancos, clientes, vendedores, ajustes, dashboard, presupuestos, devoluciones, ubicaciones, claves
from database import engine, SessionLocal
from database import Base
from config import ENVIRONMENT
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema Ferretería", version="1.0.0")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "https://ferreutil.up.railway.app",
    "https://aware-heart-production-aed1.up.railway.app",
]

if FRONTEND_URL and FRONTEND_URL not in _origins:
    _origins.append(FRONTEND_URL)

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
app.include_router(claves.router)


@app.on_event("startup")
def inicializar_datos():
    """
    Migraciones seguras compatibles con SQLite (desarrollo) y PostgreSQL (Railway).
    Se ejecuta cada vez que arranca el servidor; es idempotente.
    """
    db  = SessionLocal()
    url = str(engine.url)
    es_postgres = url.startswith("postgresql")

    def migrar(sqls_sqlite: list[str], sqls_pg: list[str] | None = None):
        """Ejecuta cada sentencia ignorando errores (columna ya existe, etc.)."""
        sqls = sqls_pg if (es_postgres and sqls_pg is not None) else sqls_sqlite
        for sql in sqls:
            try:
                db.execute(text(sql))
                db.commit()
            except Exception:
                db.rollback()

    try:
        from sqlalchemy import text

        # ── clientes ─────────────────────────────────────────────────────────
        migrar(
            ["ALTER TABLE clientes ADD COLUMN es_cliente_generico BOOLEAN DEFAULT 0",
             "ALTER TABLE clientes ADD COLUMN credito_disponible FLOAT DEFAULT 0",
             "ALTER TABLE clientes ADD COLUMN codigo TEXT"],
            ["ALTER TABLE clientes ADD COLUMN IF NOT EXISTS es_cliente_generico BOOLEAN DEFAULT FALSE",
             "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS credito_disponible FLOAT DEFAULT 0",
             "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo TEXT"],
        )

        # ── usuarios ─────────────────────────────────────────────────────────
        migrar(
            ["ALTER TABLE usuarios ADD COLUMN permisos TEXT DEFAULT NULL"],
            ["ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS permisos TEXT DEFAULT NULL"],
        )

        # ── productos ────────────────────────────────────────────────────────
        migrar(
            ["ALTER TABLE productos ADD COLUMN departamento_id INTEGER",
             "ALTER TABLE productos ADD COLUMN proveedor_id INTEGER",
             "ALTER TABLE productos ADD COLUMN es_producto_clave BOOLEAN DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN es_producto_compuesto BOOLEAN DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN descuento_compuesto_pct FLOAT DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN comision_pct FLOAT DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN activo BOOLEAN DEFAULT 1",
             "ALTER TABLE productos ADD COLUMN codigo TEXT",
             "ALTER TABLE productos ADD COLUMN categoria_id INTEGER"],
            ["ALTER TABLE productos ADD COLUMN IF NOT EXISTS departamento_id INTEGER",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS proveedor_id INTEGER",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS es_producto_clave BOOLEAN DEFAULT FALSE",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS es_producto_compuesto BOOLEAN DEFAULT FALSE",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS descuento_compuesto_pct FLOAT DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS comision_pct FLOAT DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS codigo TEXT",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS categoria_id INTEGER"],
        )

        # ── proveedores ──────────────────────────────────────────────────────
        migrar(
            ["ALTER TABLE proveedores ADD COLUMN dias_credito INTEGER DEFAULT 0",
             "ALTER TABLE proveedores ADD COLUMN credito_disponible FLOAT DEFAULT 0",
             "ALTER TABLE proveedores ADD COLUMN codigo TEXT"],
            ["ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS dias_credito INTEGER DEFAULT 0",
             "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS credito_disponible FLOAT DEFAULT 0",
             "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS codigo TEXT"],
        )

        # ── recepciones_compra ───────────────────────────────────────────────
        migrar(
            ["ALTER TABLE recepciones_compra ADD COLUMN fecha_vencimiento_pago DATE",
             "ALTER TABLE recepciones_compra ADD COLUMN monto_factura FLOAT",
             "ALTER TABLE recepciones_compra ADD COLUMN estado_pago TEXT DEFAULT 'pendiente'",
             "ALTER TABLE recepciones_compra ADD COLUMN fecha_pago_real DATETIME",
             "ALTER TABLE recepciones_compra ADD COLUMN numero_factura TEXT"],
            ["ALTER TABLE recepciones_compra ADD COLUMN IF NOT EXISTS fecha_vencimiento_pago DATE",
             "ALTER TABLE recepciones_compra ADD COLUMN IF NOT EXISTS monto_factura FLOAT",
             "ALTER TABLE recepciones_compra ADD COLUMN IF NOT EXISTS estado_pago TEXT DEFAULT 'pendiente'",
             "ALTER TABLE recepciones_compra ADD COLUMN IF NOT EXISTS fecha_pago_real TIMESTAMP",
             "ALTER TABLE recepciones_compra ADD COLUMN IF NOT EXISTS numero_factura TEXT"],
        )

        # ── clientes: campos crédito y saldo a favor ─────────────────────────
        migrar(
            ["ALTER TABLE clientes ADD COLUMN tiene_credito BOOLEAN DEFAULT 0",
             "ALTER TABLE clientes ADD COLUMN limite_credito FLOAT DEFAULT 0",
             "ALTER TABLE clientes ADD COLUMN saldo_credito FLOAT DEFAULT 0",
             "ALTER TABLE clientes ADD COLUMN saldo_a_favor FLOAT DEFAULT 0"],
            ["ALTER TABLE clientes ADD COLUMN IF NOT EXISTS tiene_credito BOOLEAN DEFAULT FALSE",
             "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS limite_credito FLOAT DEFAULT 0",
             "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS saldo_credito FLOAT DEFAULT 0",
             "ALTER TABLE clientes ADD COLUMN IF NOT EXISTS saldo_a_favor FLOAT DEFAULT 0"],
        )

        # ── Seed: "Consumidor Final" ──────────────────────────────────────────
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

        # ── Seed: Claves de Autorización ──────────────────────────────────────
        for accion, desc in [
            ("descuento",        "Descuento en venta / precio base"),
            ("stock",            "Venta sin stock"),
            ("devolucion",       "Devolución de productos"),
            ("precio_base",      "Precio base (sin protección cambiaria)"),
            ("credito_excedido", "Aprobar venta con crédito excedido"),
        ]:
            existe = db.query(models.ClaveAutorizacion).filter(
                models.ClaveAutorizacion.accion == accion
            ).first()
            if not existe:
                db.add(models.ClaveAutorizacion(
                    accion      = accion,
                    clave       = "1234",
                    descripcion = desc,
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
