from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rutas import productos, ventas, usuarios, facturas, tasa, cierres, depositos, reportes, compras, bancos, clientes, vendedores, ajustes, dashboard, presupuestos, devoluciones, ubicaciones, claves, garantias, admin, notificaciones, export, reposicion, sedes, auth, transferencias
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
    "https://ferreutil-web-production.up.railway.app",
]

if FRONTEND_URL and FRONTEND_URL not in _origins:
    _origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["date", "Date"],
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
app.include_router(garantias.router)
app.include_router(admin.router)
app.include_router(notificaciones.router)
app.include_router(export.router)
app.include_router(reposicion.router)
app.include_router(sedes.router)
app.include_router(auth.router)
app.include_router(transferencias.router)

from rutas import marcas as _marcas_mod
app.include_router(_marcas_mod.router, prefix="/marcas")

from rutas import chuito as _chuito_mod
app.include_router(_chuito_mod.router, prefix="/chuito")

from rutas import apartados as _apartados_mod
app.include_router(_apartados_mod.router, prefix="/apartados")


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
            ["ALTER TABLE usuarios ADD COLUMN permisos TEXT DEFAULT NULL",
             "ALTER TABLE usuarios ADD COLUMN activo BOOLEAN DEFAULT 1"],
            ["ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS permisos TEXT DEFAULT NULL",
             "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE"],
        )

        # ── productos ────────────────────────────────────────────────────────
        migrar(
            ["ALTER TABLE productos ADD COLUMN departamento_id INTEGER",
             "ALTER TABLE productos ADD COLUMN proveedor_id INTEGER",
             "ALTER TABLE productos ADD COLUMN es_producto_clave BOOLEAN DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN es_producto_compuesto BOOLEAN DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN descuento_compuesto_pct FLOAT DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN comision_pct FLOAT DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN comision_push FLOAT",
             "ALTER TABLE productos ADD COLUMN es_delicado BOOLEAN DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN activo BOOLEAN DEFAULT 1",
             "ALTER TABLE productos ADD COLUMN codigo TEXT",
             "ALTER TABLE productos ADD COLUMN categoria_id INTEGER",
             "ALTER TABLE productos ADD COLUMN esquema_variante TEXT",
             "ALTER TABLE productos ADD COLUMN es_generico BOOLEAN DEFAULT 0"],
            ["ALTER TABLE productos ADD COLUMN IF NOT EXISTS departamento_id INTEGER",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS proveedor_id INTEGER",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS es_producto_clave BOOLEAN DEFAULT FALSE",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS es_producto_compuesto BOOLEAN DEFAULT FALSE",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS descuento_compuesto_pct FLOAT DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS comision_pct FLOAT DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS comision_push FLOAT",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS es_delicado BOOLEAN DEFAULT FALSE",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS codigo TEXT",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS categoria_id INTEGER",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS esquema_variante TEXT",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS es_generico BOOLEAN DEFAULT FALSE"],
        )

        # ── productos: es_generico deprecated, forzado a true para todos ───────
        # La ficha de reposición (proveedor principal + alternativos) reemplaza
        # la distinción genérico/específico. La columna no se borra (ver nota en
        # models.py) pero deja de tener ningún efecto — se fuerza a true en todos
        # los productos existentes. El WHERE evita reescribir filas ya migradas
        # en cada arranque.
        migrar(
            ["UPDATE productos SET es_generico = 1 WHERE es_generico IS NULL OR es_generico = 0"],
            ["UPDATE productos SET es_generico = TRUE WHERE es_generico IS NOT TRUE"],
        )

        # ── proveedores ──────────────────────────────────────────────────────
        migrar(
            ["ALTER TABLE proveedores ADD COLUMN dias_credito INTEGER DEFAULT 0",
             "ALTER TABLE proveedores ADD COLUMN credito_disponible FLOAT DEFAULT 0",
             "ALTER TABLE proveedores ADD COLUMN codigo TEXT",
             "ALTER TABLE proveedores ADD COLUMN pricing_policy TEXT DEFAULT 'MARKET_FACTOR'",
             "ALTER TABLE proveedores ADD COLUMN ajuste_divisa_pct FLOAT DEFAULT 0.0",
             "ALTER TABLE proveedores ADD COLUMN ajuste_tipo TEXT DEFAULT 'manual'",
             "ALTER TABLE proveedores ADD COLUMN descuento_pct FLOAT DEFAULT 0"],
            ["ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS dias_credito INTEGER DEFAULT 0",
             "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS credito_disponible FLOAT DEFAULT 0",
             "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS codigo TEXT",
             "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS pricing_policy TEXT DEFAULT 'MARKET_FACTOR'",
             "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS ajuste_divisa_pct FLOAT DEFAULT 0.0",
             "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS ajuste_tipo TEXT DEFAULT 'manual'",
             "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS descuento_pct FLOAT DEFAULT 0"],
        )

        # ── proveedores: dias_credito_real ───────────────────────────────────
        migrar(
            ["ALTER TABLE proveedores ADD COLUMN dias_credito_real INTEGER"],
            ["ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS dias_credito_real INTEGER"],
        )

        # ── productos: pricing_policy_override ───────────────────────────────
        migrar(
            ["ALTER TABLE productos ADD COLUMN pricing_policy_override TEXT"],
            ["ALTER TABLE productos ADD COLUMN IF NOT EXISTS pricing_policy_override TEXT"],
        )

        # ── productos: auditoría de inventario ───────────────────────────────
        migrar(
            ["ALTER TABLE productos ADD COLUMN auditado BOOLEAN DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN fecha_auditoria DATETIME",
             "ALTER TABLE productos ADD COLUMN auditoria_pendiente BOOLEAN DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN conteo_pendiente INTEGER",
             "ALTER TABLE productos ADD COLUMN diferencia_pendiente INTEGER"],
            ["ALTER TABLE productos ADD COLUMN IF NOT EXISTS auditado BOOLEAN DEFAULT FALSE",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS fecha_auditoria TIMESTAMP",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS auditoria_pendiente BOOLEAN DEFAULT FALSE",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS conteo_pendiente INTEGER",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS diferencia_pendiente INTEGER"],
        )

        # ── productos: stock_minimo ──────────────────────────────────────────
        migrar(
            ["ALTER TABLE productos ADD COLUMN stock_minimo INTEGER DEFAULT 0"],
            ["ALTER TABLE productos ADD COLUMN IF NOT EXISTS stock_minimo INTEGER DEFAULT 0"],
        )

        # ── descuento_max_pct en categorías, productos y proveedores ─────────
        migrar(
            ["ALTER TABLE categorias ADD COLUMN descuento_max_pct FLOAT"],
            ["ALTER TABLE categorias ADD COLUMN IF NOT EXISTS descuento_max_pct FLOAT"],
        )
        migrar(
            ["ALTER TABLE productos ADD COLUMN descuento_max_pct FLOAT"],
            ["ALTER TABLE productos ADD COLUMN IF NOT EXISTS descuento_max_pct FLOAT"],
        )
        migrar(
            ["ALTER TABLE proveedores ADD COLUMN descuento_max_pct FLOAT"],
            ["ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS descuento_max_pct FLOAT"],
        )

        # ── apartados ────────────────────────────────────────────────────────
        migrar(
            ["""CREATE TABLE IF NOT EXISTS apartados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero VARCHAR UNIQUE,
                vendedor VARCHAR NOT NULL,
                cliente_nombre VARCHAR,
                cliente_telefono VARCHAR,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                fecha_maxima DATETIME,
                cuotas INTEGER,
                monto_cuota FLOAT,
                total_usd FLOAT DEFAULT 0,
                abonado_usd FLOAT DEFAULT 0,
                estado VARCHAR DEFAULT 'activo',
                observacion VARCHAR,
                moneda VARCHAR DEFAULT 'USD',
                tasa_bcv FLOAT
            )"""],
            ["""CREATE TABLE IF NOT EXISTS apartados (
                id SERIAL PRIMARY KEY,
                numero VARCHAR UNIQUE,
                vendedor VARCHAR NOT NULL,
                cliente_nombre VARCHAR,
                cliente_telefono VARCHAR,
                fecha_creacion TIMESTAMP DEFAULT NOW(),
                fecha_maxima TIMESTAMP,
                cuotas INTEGER,
                monto_cuota FLOAT,
                total_usd FLOAT DEFAULT 0,
                abonado_usd FLOAT DEFAULT 0,
                estado VARCHAR DEFAULT 'activo',
                observacion VARCHAR,
                moneda VARCHAR DEFAULT 'USD',
                tasa_bcv FLOAT
            )"""],
        )
        migrar(
            ["""CREATE TABLE IF NOT EXISTS detalles_apartado (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apartado_id INTEGER REFERENCES apartados(id),
                producto_id INTEGER,
                variante_id INTEGER,
                nombre_producto VARCHAR,
                cantidad INTEGER DEFAULT 1,
                precio_unitario_usd FLOAT DEFAULT 0,
                subtotal_usd FLOAT DEFAULT 0
            )"""],
            ["""CREATE TABLE IF NOT EXISTS detalles_apartado (
                id SERIAL PRIMARY KEY,
                apartado_id INTEGER REFERENCES apartados(id),
                producto_id INTEGER,
                variante_id INTEGER,
                nombre_producto VARCHAR,
                cantidad INTEGER DEFAULT 1,
                precio_unitario_usd FLOAT DEFAULT 0,
                subtotal_usd FLOAT DEFAULT 0
            )"""],
        )
        migrar(
            ["""CREATE TABLE IF NOT EXISTS abonos_apartado (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apartado_id INTEGER REFERENCES apartados(id),
                monto FLOAT DEFAULT 0,
                moneda_pago VARCHAR DEFAULT 'USD',
                metodo_pago VARCHAR,
                cuenta_destino_id INTEGER,
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                registrado_por VARCHAR,
                referencia VARCHAR
            )"""],
            ["""CREATE TABLE IF NOT EXISTS abonos_apartado (
                id SERIAL PRIMARY KEY,
                apartado_id INTEGER REFERENCES apartados(id),
                monto FLOAT DEFAULT 0,
                moneda_pago VARCHAR DEFAULT 'USD',
                metodo_pago VARCHAR,
                cuenta_destino_id INTEGER,
                fecha TIMESTAMP DEFAULT NOW(),
                registrado_por VARCHAR,
                referencia VARCHAR
            )"""],
        )

        # ── mensajes_chuito ──────────────────────────────────────────────────
        migrar(
            ["""CREATE TABLE IF NOT EXISTS mensajes_chuito (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo VARCHAR NOT NULL,
                vendedor VARCHAR NOT NULL,
                mensaje VARCHAR NOT NULL,
                detalle TEXT,
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                leido_admin BOOLEAN DEFAULT 0
            )"""],
            ["""CREATE TABLE IF NOT EXISTS mensajes_chuito (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR NOT NULL,
                vendedor VARCHAR NOT NULL,
                mensaje VARCHAR NOT NULL,
                detalle TEXT,
                fecha TIMESTAMP DEFAULT NOW(),
                leido_admin BOOLEAN DEFAULT FALSE
            )"""],
        )

        # ── avisos_vistos ────────────────────────────────────────────────────
        migrar(
            ["""CREATE TABLE IF NOT EXISTS avisos_vistos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aviso_id INTEGER REFERENCES avisos(id),
                usuario VARCHAR NOT NULL,
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""],
            ["""CREATE TABLE IF NOT EXISTS avisos_vistos (
                id SERIAL PRIMARY KEY,
                aviso_id INTEGER REFERENCES avisos(id),
                usuario VARCHAR NOT NULL,
                fecha TIMESTAMP DEFAULT NOW()
            )"""],
        )

        # ── productos: unidades de medida y paquete ──────────────────────────
        migrar(
            ["ALTER TABLE productos ADD COLUMN unidad_medida TEXT DEFAULT 'unidad'",
             "ALTER TABLE productos ADD COLUMN unidades_por_paquete INTEGER DEFAULT 1",
             "ALTER TABLE productos ADD COLUMN nombre_paquete TEXT",
             "ALTER TABLE productos ADD COLUMN precio_paquete_base_usd FLOAT",
             "ALTER TABLE productos ADD COLUMN precio_paquete_ref_usd FLOAT"],
            ["ALTER TABLE productos ADD COLUMN IF NOT EXISTS unidad_medida TEXT DEFAULT 'unidad'",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS unidades_por_paquete INTEGER DEFAULT 1",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS nombre_paquete TEXT",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS precio_paquete_base_usd FLOAT",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS precio_paquete_ref_usd FLOAT"],
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

        # ── variante_id en tablas de detalle ─────────────────────────────────
        migrar(
            ["ALTER TABLE detalle_ventas ADD COLUMN variante_id INTEGER",
             "ALTER TABLE detalle_presupuesto ADD COLUMN variante_id INTEGER",
             "ALTER TABLE detalle_devolucion_cliente ADD COLUMN variante_id INTEGER"],
            ["ALTER TABLE detalle_ventas ADD COLUMN IF NOT EXISTS variante_id INTEGER",
             "ALTER TABLE detalle_presupuesto ADD COLUMN IF NOT EXISTS variante_id INTEGER",
             "ALTER TABLE detalle_devolucion_cliente ADD COLUMN IF NOT EXISTS variante_id INTEGER"],
        )

        migrar(
            ["ALTER TABLE detalle_ventas ADD COLUMN precio_libre BOOLEAN DEFAULT 0"],
            ["ALTER TABLE detalle_ventas ADD COLUMN IF NOT EXISTS precio_libre BOOLEAN DEFAULT FALSE"],
        )

        # ── catalogo_proveedor: rif_proveedor como clave de cruce ───────────
        migrar(
            ["ALTER TABLE catalogo_proveedor ADD COLUMN rif_proveedor TEXT"],
            ["ALTER TABLE catalogo_proveedor ADD COLUMN IF NOT EXISTS rif_proveedor TEXT"],
        )

        # ── catalogo_proveedor: huella para match tolerante de códigos largos ─
        migrar(
            ["ALTER TABLE catalogo_proveedor ADD COLUMN codigo_huella TEXT"],
            ["ALTER TABLE catalogo_proveedor ADD COLUMN IF NOT EXISTS codigo_huella TEXT"],
        )

        # ── catalogo_proveedor: bloqueado tras primera compra confirmada ──────
        migrar(
            ["ALTER TABLE catalogo_proveedor ADD COLUMN bloqueado BOOLEAN DEFAULT 0"],
            ["ALTER TABLE catalogo_proveedor ADD COLUMN IF NOT EXISTS bloqueado BOOLEAN DEFAULT FALSE"],
        )

        # ── recepciones_compra: devuelta ─────────────────────────────────────
        migrar(
            ["ALTER TABLE recepciones_compra ADD COLUMN devuelta BOOLEAN DEFAULT 0"],
            ["ALTER TABLE recepciones_compra ADD COLUMN IF NOT EXISTS devuelta BOOLEAN DEFAULT FALSE"],
        )

        # ── variantes_producto.codigo + variante_id en tablas de compras ─────
        migrar(
            ["ALTER TABLE variantes_producto ADD COLUMN codigo TEXT",
             "ALTER TABLE catalogo_proveedor ADD COLUMN variante_id INTEGER",
             "ALTER TABLE detalle_orden_compra ADD COLUMN variante_id INTEGER",
             "ALTER TABLE detalle_recepcion ADD COLUMN variante_id INTEGER"],
            ["ALTER TABLE variantes_producto ADD COLUMN IF NOT EXISTS codigo TEXT",
             "ALTER TABLE catalogo_proveedor ADD COLUMN IF NOT EXISTS variante_id INTEGER",
             "ALTER TABLE detalle_orden_compra ADD COLUMN IF NOT EXISTS variante_id INTEGER",
             "ALTER TABLE detalle_recepcion ADD COLUMN IF NOT EXISTS variante_id INTEGER"],
        )

        # ── variantes_producto: costo y margen propios ───────────────────────
        migrar(
            ["ALTER TABLE variantes_producto ADD COLUMN costo_usd FLOAT",
             "ALTER TABLE variantes_producto ADD COLUMN margen FLOAT"],
            ["ALTER TABLE variantes_producto ADD COLUMN IF NOT EXISTS costo_usd FLOAT",
             "ALTER TABLE variantes_producto ADD COLUMN IF NOT EXISTS margen FLOAT"],
        )

        # ── garantías ────────────────────────────────────────────────────────
        migrar(
            ["ALTER TABLE productos ADD COLUMN requiere_serial BOOLEAN DEFAULT 0",
             "ALTER TABLE productos ADD COLUMN plantilla_garantia_id INTEGER",
             """CREATE TABLE IF NOT EXISTS plantillas_garantia (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 nombre TEXT NOT NULL,
                 meses INTEGER DEFAULT 0,
                 condiciones TEXT,
                 activa BOOLEAN DEFAULT 1
             )""",
             """CREATE TABLE IF NOT EXISTS garantias_venta (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 venta_id INTEGER NOT NULL,
                 producto_id INTEGER NOT NULL,
                 variante_id INTEGER,
                 serial TEXT,
                 modelo TEXT,
                 meses_garantia INTEGER,
                 condiciones_snapshot TEXT,
                 fecha DATETIME
             )"""],
            ["ALTER TABLE productos ADD COLUMN IF NOT EXISTS requiere_serial BOOLEAN DEFAULT FALSE",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS plantilla_garantia_id INTEGER",
             """CREATE TABLE IF NOT EXISTS plantillas_garantia (
                 id SERIAL PRIMARY KEY,
                 nombre TEXT NOT NULL,
                 meses INTEGER DEFAULT 0,
                 condiciones TEXT,
                 activa BOOLEAN DEFAULT TRUE
             )""",
             """CREATE TABLE IF NOT EXISTS garantias_venta (
                 id SERIAL PRIMARY KEY,
                 venta_id INTEGER NOT NULL,
                 producto_id INTEGER NOT NULL,
                 variante_id INTEGER,
                 serial TEXT,
                 modelo TEXT,
                 meses_garantia INTEGER,
                 condiciones_snapshot TEXT,
                 fecha TIMESTAMP
             )"""],
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

        # ── ventas: despacho ──────────────────────────────────────────────────
        migrar(
            ["ALTER TABLE ventas ADD COLUMN despachado_por TEXT"],
            ["ALTER TABLE ventas ADD COLUMN IF NOT EXISTS despachado_por TEXT"],
        )

        # ── proveedores: ficha de reposición (lead time default + notas) ─────
        migrar(
            ["ALTER TABLE proveedores ADD COLUMN lead_time_dias_default INTEGER DEFAULT 0",
             "ALTER TABLE proveedores ADD COLUMN notas TEXT"],
            ["ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS lead_time_dias_default INTEGER DEFAULT 0",
             "ALTER TABLE proveedores ADD COLUMN IF NOT EXISTS notas TEXT"],
        )

        # ── producto_proveedor: hasta 3 proveedores por producto con prioridad ─
        migrar(
            ["""CREATE TABLE IF NOT EXISTS producto_proveedor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                proveedor_id INTEGER NOT NULL REFERENCES proveedores(id) ON DELETE RESTRICT,
                prioridad INTEGER NOT NULL CHECK (prioridad IN (1,2,3)),
                precio_actual_usd FLOAT,
                credito_dias INTEGER,
                lead_time_dias INTEGER,
                minimo_compra INTEGER,
                notas TEXT,
                sin_stock_declarado BOOLEAN DEFAULT 0,
                sin_stock_fecha DATE,
                UNIQUE(producto_id, prioridad)
            )""",
             "CREATE INDEX IF NOT EXISTS ix_pp_producto ON producto_proveedor(producto_id)",
             "CREATE INDEX IF NOT EXISTS ix_pp_proveedor ON producto_proveedor(proveedor_id)"],
            ["""CREATE TABLE IF NOT EXISTS producto_proveedor (
                id SERIAL PRIMARY KEY,
                producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                proveedor_id INTEGER NOT NULL REFERENCES proveedores(id) ON DELETE RESTRICT,
                prioridad INTEGER NOT NULL CHECK (prioridad IN (1,2,3)),
                precio_actual_usd FLOAT,
                credito_dias INTEGER,
                lead_time_dias INTEGER,
                minimo_compra INTEGER,
                notas TEXT,
                sin_stock_declarado BOOLEAN DEFAULT FALSE,
                sin_stock_fecha DATE,
                UNIQUE(producto_id, prioridad)
            )""",
             "CREATE INDEX IF NOT EXISTS ix_pp_producto ON producto_proveedor(producto_id)",
             "CREATE INDEX IF NOT EXISTS ix_pp_proveedor ON producto_proveedor(proveedor_id)"],
        )

        # ── producto_reposicion: ficha 1:1 con producto ──────────────────────
        migrar(
            ["""CREATE TABLE IF NOT EXISTS producto_reposicion (
                producto_id INTEGER PRIMARY KEY REFERENCES productos(id) ON DELETE CASCADE,
                modo_reposicion TEXT NOT NULL DEFAULT 'stock_continuo',
                stock_min_objetivo INTEGER DEFAULT 0,
                stock_max_objetivo INTEGER DEFAULT 0,
                unidades_exhibicion INTEGER DEFAULT 0,
                colchon_dias INTEGER DEFAULT 3,
                activo BOOLEAN DEFAULT 1,
                notas TEXT,
                actualizado_en DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""],
            ["""CREATE TABLE IF NOT EXISTS producto_reposicion (
                producto_id INTEGER PRIMARY KEY REFERENCES productos(id) ON DELETE CASCADE,
                modo_reposicion TEXT NOT NULL DEFAULT 'stock_continuo',
                stock_min_objetivo INTEGER DEFAULT 0,
                stock_max_objetivo INTEGER DEFAULT 0,
                unidades_exhibicion INTEGER DEFAULT 0,
                colchon_dias INTEGER DEFAULT 3,
                activo BOOLEAN DEFAULT TRUE,
                notas TEXT,
                actualizado_en TIMESTAMP DEFAULT NOW()
            )"""],
        )

        # ── proveedores: codigo único (3 letras) — el formato se valida en el
        # endpoint, acá solo se asegura que no haya dos proveedores con el
        # mismo código. Los PRV-XXXX autogenerados históricos ya son únicos
        # entre sí, así que el índice se puede crear sin migrar datos.
        migrar(
            ["CREATE UNIQUE INDEX IF NOT EXISTS ux_proveedores_codigo ON proveedores(codigo)"],
            ["CREATE UNIQUE INDEX IF NOT EXISTS ux_proveedores_codigo ON proveedores(codigo)"],
        )

        # ── productos: limpieza one-shot de descripcion residual de Factura IA ──
        # "Creado desde factura IA — <numero_factura>" (y variante histórica en
        # minúscula "ia") se guardaba en descripcion antes de que el nombre del
        # producto quedara bien resuelto. El nombre ya es correcto, así que la
        # descripcion residual se reemplaza por el nombre. Idempotente: una vez
        # reemplazada, la fila deja de matchear el LIKE/ILIKE, así que reintentos
        # en próximos arranques no hacen nada.
        migrar(
            ["UPDATE productos SET descripcion = nombre WHERE descripcion LIKE 'Creado desde factura%'"],
            ["UPDATE productos SET descripcion = nombre WHERE descripcion ILIKE 'Creado desde factura%'"],
        )

        # ── marcas ───────────────────────────────────────────────────────────
        migrar(
            ["""CREATE TABLE IF NOT EXISTS marcas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                activa BOOLEAN DEFAULT 1
            )""",
             "ALTER TABLE productos ADD COLUMN marca_id INTEGER REFERENCES marcas(id)"],
            ["""CREATE TABLE IF NOT EXISTS marcas (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR NOT NULL UNIQUE,
                activa BOOLEAN DEFAULT TRUE
            )""",
             "ALTER TABLE productos ADD COLUMN IF NOT EXISTS marca_id INTEGER REFERENCES marcas(id)"],
        )

        # ── conteo_prioritario ───────────────────────────────────────────────
        migrar(
            ["""CREATE TABLE IF NOT EXISTS conteo_prioritario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER,
                variante_id INTEGER,
                enviado_por TEXT,
                fecha_envio DATETIME DEFAULT CURRENT_TIMESTAMP,
                nota TEXT,
                prioridad TEXT DEFAULT 'manual',
                estado TEXT DEFAULT 'pendiente',
                fecha_conteo DATETIME,
                contado_por TEXT,
                stock_sistema INTEGER,
                stock_real INTEGER,
                diferencia INTEGER,
                aprobado_admin BOOLEAN,
                fecha_aprobacion DATETIME
            )""",
             "CREATE INDEX IF NOT EXISTS ix_conteo_prio_estado ON conteo_prioritario(estado)",
             "CREATE INDEX IF NOT EXISTS ix_conteo_prio_prod ON conteo_prioritario(producto_id)"],
            ["""CREATE TABLE IF NOT EXISTS conteo_prioritario (
                id SERIAL PRIMARY KEY,
                producto_id INTEGER,
                variante_id INTEGER,
                enviado_por TEXT,
                fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                nota TEXT,
                prioridad TEXT DEFAULT 'manual',
                estado TEXT DEFAULT 'pendiente',
                fecha_conteo TIMESTAMP,
                contado_por TEXT,
                stock_sistema INTEGER,
                stock_real INTEGER,
                diferencia INTEGER,
                aprobado_admin BOOLEAN,
                fecha_aprobacion TIMESTAMP
             )""",
             "CREATE INDEX IF NOT EXISTS ix_conteo_prio_estado ON conteo_prioritario(estado)",
             "CREATE INDEX IF NOT EXISTS ix_conteo_prio_prod ON conteo_prioritario(producto_id)"],
        )

        # ══════════════════════════════════════════════════════════════════════
        # Multisede Fase 1A — schema + migracion historica, SIN cambios de
        # comportamiento (no se toca ningun endpoint ni models.py en esta
        # sub-fase). Todo el codigo existente sigue leyendo/escribiendo
        # productos.stock exactamente igual que antes; las tablas y columnas
        # nuevas quedan pobladas pero invisibles para la app hasta 1B+.
        # ══════════════════════════════════════════════════════════════════════

        # ── sedes ────────────────────────────────────────────────────────────
        migrar(
            ["""CREATE TABLE IF NOT EXISTS sedes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                ciudad TEXT,
                direccion TEXT,
                telefono TEXT,
                activa BOOLEAN DEFAULT 1,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
             "INSERT OR IGNORE INTO sedes (id, codigo, nombre, ciudad, activa) VALUES (1, 'OJEDA', 'Ferreutil Ojeda', 'Ojeda', 1)",
             "INSERT OR IGNORE INTO sedes (id, codigo, nombre, ciudad, activa) VALUES (2, 'VALERA', 'Ferreutil Valera', 'Valera', 1)"],
            ["""CREATE TABLE IF NOT EXISTS sedes (
                id SERIAL PRIMARY KEY,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                ciudad TEXT,
                direccion TEXT,
                telefono TEXT,
                activa BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT NOW()
            )""",
             "INSERT INTO sedes (id, codigo, nombre, ciudad, activa) VALUES (1, 'OJEDA', 'Ferreutil Ojeda', 'Ojeda', TRUE) ON CONFLICT (id) DO NOTHING",
             "INSERT INTO sedes (id, codigo, nombre, ciudad, activa) VALUES (2, 'VALERA', 'Ferreutil Valera', 'Valera', TRUE) ON CONFLICT (id) DO NOTHING",
             # ids insertados a mano (1,2) -> hay que adelantar la secuencia para
             # que el proximo INSERT sin id explicito (POST /sedes/ en 1B) no choque
             "SELECT setval(pg_get_serial_sequence('sedes','id'), (SELECT MAX(id) FROM sedes))"],
        )

        # ── existencia_sede ──────────────────────────────────────────────────
        migrar(
            ["""CREATE TABLE IF NOT EXISTS existencia_sede (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                sede_id INTEGER NOT NULL REFERENCES sedes(id) ON DELETE RESTRICT,
                existencia INTEGER DEFAULT 0,
                ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(producto_id, sede_id)
            )"""],
            ["""CREATE TABLE IF NOT EXISTS existencia_sede (
                id SERIAL PRIMARY KEY,
                producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE CASCADE,
                sede_id INTEGER NOT NULL REFERENCES sedes(id) ON DELETE RESTRICT,
                existencia INTEGER DEFAULT 0,
                ultima_actualizacion TIMESTAMP DEFAULT NOW(),
                UNIQUE(producto_id, sede_id)
            )"""],
        )

        # Backfill: una fila por producto en Ojeda (id=1), salvo los que tienen
        # variantes ACTIVAS — esos siguen operando solo por variantes_producto.stock
        # (congelado, fuera de alcance de existencia_sede en Fase 1). La ausencia
        # de fila en existencia_sede para un producto asi ES la señal de "todavia
        # vive en el flujo viejo de variantes" — no hace falta una columna aparte.
        migrar(
            ["""INSERT OR IGNORE INTO existencia_sede (producto_id, sede_id, existencia)
                SELECT p.id, 1, p.stock FROM productos p
                WHERE NOT EXISTS (
                    SELECT 1 FROM variantes_producto vp
                    WHERE vp.producto_id = p.id AND vp.activo = 1
                )"""],
            ["""INSERT INTO existencia_sede (producto_id, sede_id, existencia)
                SELECT p.id, 1, p.stock FROM productos p
                WHERE NOT EXISTS (
                    SELECT 1 FROM variantes_producto vp
                    WHERE vp.producto_id = p.id AND vp.activo = TRUE
                )
                ON CONFLICT (producto_id, sede_id) DO NOTHING"""],
        )

        # ── usuarios: sede principal + permiso de alternar ──────────────────
        migrar(
            ["ALTER TABLE usuarios ADD COLUMN sede_id INTEGER",
             "ALTER TABLE usuarios ADD COLUMN puede_alternar_sedes BOOLEAN DEFAULT 0"],
            ["ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS sede_id INTEGER REFERENCES sedes(id)",
             "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS puede_alternar_sedes BOOLEAN DEFAULT FALSE"],
        )
        migrar(
            ["UPDATE usuarios SET sede_id = 1 WHERE sede_id IS NULL",
             "UPDATE usuarios SET puede_alternar_sedes = 1 WHERE rol = 'admin'"],
            ["UPDATE usuarios SET sede_id = 1 WHERE sede_id IS NULL",
             "UPDATE usuarios SET puede_alternar_sedes = TRUE WHERE rol = 'admin'"],
        )

        # ── ventas.sede_id — NOT NULL DEFAULT 1 en el mismo ALTER: codigo viejo
        # que hace INSERT sin mencionar sede_id sigue funcionando igual, Postgres/
        # SQLite completan el default solos. Sin esto no habria forma segura de
        # endurecer el constraint sin arriesgar el INSERT de registrar_venta.
        migrar(
            ["ALTER TABLE ventas ADD COLUMN sede_id INTEGER NOT NULL DEFAULT 1"],
            ["ALTER TABLE ventas ADD COLUMN IF NOT EXISTS sede_id INTEGER NOT NULL DEFAULT 1 REFERENCES sedes(id)"],
        )

        # ── ordenes_compra.sede_id_destino ───────────────────────────────────
        migrar(
            ["ALTER TABLE ordenes_compra ADD COLUMN sede_id_destino INTEGER NOT NULL DEFAULT 1"],
            ["ALTER TABLE ordenes_compra ADD COLUMN IF NOT EXISTS sede_id_destino INTEGER NOT NULL DEFAULT 1 REFERENCES sedes(id)"],
        )

        # ── cierres_caja.sede_id — el cierre del dia es por sede ────────────
        migrar(
            ["ALTER TABLE cierres_caja ADD COLUMN sede_id INTEGER NOT NULL DEFAULT 1"],
            ["ALTER TABLE cierres_caja ADD COLUMN IF NOT EXISTS sede_id INTEGER NOT NULL DEFAULT 1 REFERENCES sedes(id)"],
        )

        # ── apartados.sede_id — Fase 1F: reserva de stock por sede. Se guarda
        # en el registro (no se recalcula al cancelar) para que cancelar_apartado
        # libere siempre en la misma sede donde se reservo, aunque quien cancele
        # este operando desde otra sede en ese momento.
        migrar(
            ["ALTER TABLE apartados ADD COLUMN sede_id INTEGER NOT NULL DEFAULT 1"],
            ["ALTER TABLE apartados ADD COLUMN IF NOT EXISTS sede_id INTEGER NOT NULL DEFAULT 1 REFERENCES sedes(id)"],
        )

        # ── movimientos_bancarios.cierre_caja_id — SIN sede_id propio: las
        # cuentas bancarias son globales (misma cuenta Zelle/pago movil para
        # las dos sedes). El link al cierre permite saber que sede origino el
        # movimiento de forma indirecta cuando el cierre lo genera automatico.
        migrar(
            ["ALTER TABLE movimientos_bancarios ADD COLUMN cierre_caja_id INTEGER"],
            ["ALTER TABLE movimientos_bancarios ADD COLUMN IF NOT EXISTS cierre_caja_id INTEGER REFERENCES cierres_caja(id)"],
        )

        # ── transferencias_sede / transferencias_detalle (schema de 1H, se
        # crea ahora para no volver a tocar la base esa noche — sin endpoints
        # ni UI todavia, tablas inertes hasta 1H) ────────────────────────────
        migrar(
            ["""CREATE TABLE IF NOT EXISTS transferencias_sede (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sede_origen_id INTEGER NOT NULL REFERENCES sedes(id),
                sede_destino_id INTEGER NOT NULL REFERENCES sedes(id),
                fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
                usuario_id INTEGER REFERENCES usuarios(id),
                estado TEXT DEFAULT 'pendiente',
                notas TEXT,
                CHECK (sede_origen_id != sede_destino_id)
            )""",
             """CREATE TABLE IF NOT EXISTS transferencias_detalle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transferencia_id INTEGER NOT NULL REFERENCES transferencias_sede(id) ON DELETE CASCADE,
                producto_id INTEGER NOT NULL REFERENCES productos(id),
                cantidad INTEGER NOT NULL CHECK (cantidad > 0)
            )"""],
            ["""CREATE TABLE IF NOT EXISTS transferencias_sede (
                id SERIAL PRIMARY KEY,
                sede_origen_id INTEGER NOT NULL REFERENCES sedes(id),
                sede_destino_id INTEGER NOT NULL REFERENCES sedes(id),
                fecha TIMESTAMP DEFAULT NOW(),
                usuario_id INTEGER REFERENCES usuarios(id),
                estado TEXT DEFAULT 'pendiente',
                notas TEXT,
                CHECK (sede_origen_id != sede_destino_id)
            )""",
             """CREATE TABLE IF NOT EXISTS transferencias_detalle (
                id SERIAL PRIMARY KEY,
                transferencia_id INTEGER NOT NULL REFERENCES transferencias_sede(id) ON DELETE CASCADE,
                producto_id INTEGER NOT NULL REFERENCES productos(id),
                cantidad INTEGER NOT NULL CHECK (cantidad > 0)
            )"""],
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
