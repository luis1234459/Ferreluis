from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Date, Index, ForeignKey
from datetime import datetime
from sqlalchemy.sql import func
from database import Base

# ---------------------------------------------------------------------------
# Catálogo de métodos de pago y su moneda nativa
# ---------------------------------------------------------------------------
METODOS_USD = {"efectivo_usd", "zelle", "binance", "credito"}
METODOS_BS  = {"efectivo_bs", "transferencia_bs", "pago_movil",
               "punto_banesco", "punto_provincial"}
METODOS_VALIDOS = METODOS_USD | METODOS_BS

LABELS_METODO = {
    "efectivo_usd":    "Efectivo $",
    "zelle":           "Zelle",
    "binance":         "Binance",
    "efectivo_bs":     "Efectivo Bs",
    "transferencia_bs":"Transferencia Bs",
    "pago_movil":      "Pago Móvil",
    "punto_banesco":   "Punto Banesco",
    "punto_provincial":"Punto Provincial",
    "credito":         "A crédito",
}

TOLERANCIA    = 1.0    # diferencia mínima aceptable por redondeo
DECIMALES_USD = 2
DECIMALES_BS  = 2


# ---------------------------------------------------------------------------
# Módulo de Inventario
# ---------------------------------------------------------------------------

class Departamento(Base):
    __tablename__ = "departamentos"

    id          = Column(Integer, primary_key=True, index=True)
    nombre      = Column(String)
    descripcion = Column(String, nullable=True)
    activo      = Column(Boolean, default=True)


class Categoria(Base):
    __tablename__ = "categorias"

    id              = Column(Integer, primary_key=True, index=True)
    nombre          = Column(String, nullable=False)
    departamento_id = Column(Integer, ForeignKey("departamentos.id"), nullable=False)


class Producto(Base):
    __tablename__ = "productos"

    id          = Column(Integer, primary_key=True, index=True)
    nombre      = Column(String)
    descripcion = Column(String,  nullable=True)
    categoria   = Column(String,  nullable=True)
    stock       = Column(Integer, default=0)
    foto_url    = Column(String,  nullable=True)
    costo_usd   = Column(Float,   default=0)    # precio de compra en USD
    margen      = Column(Float,   default=0.30) # ej: 0.30 = 30%

    # ── Nuevos campos ────────────────────────────────────────────────────────
    departamento_id         = Column(Integer, nullable=True)   # FK → Departamento
    categoria_id            = Column(Integer, nullable=True)   # FK → Categoria
    proveedor_id            = Column(Integer, nullable=True)   # FK → Proveedor
    es_producto_clave       = Column(Boolean, default=False)   # producto Pareto
    es_producto_compuesto   = Column(Boolean, default=False)
    descuento_compuesto_pct = Column(Float,   default=0)       # % dto solo admin
    comision_pct            = Column(Float,   default=0.0)     # % comisión al vendedor por este producto
    codigo                  = Column(String,  nullable=True, unique=True, index=True)
    activo                  = Column(Boolean, default=True)
    esquema_variante        = Column(String,  nullable=True)   # 'clase' | 'clase_color'
    requiere_serial         = Column(Boolean, default=False)
    plantilla_garantia_id   = Column(Integer, nullable=True)   # FK → PlantillaGarantia

    pricing_policy_override = Column(String, nullable=True)   # None → hereda del Proveedor
    es_generico             = Column(Boolean, default=False)  # True = multi-proveedor, código interno manda

    unidad_medida             = Column(String,  default='unidad')  # metro | kilo | litro | unidad
    unidades_por_paquete      = Column(Integer, default=1)         # 1 = sin paquete; N = unidades/paquete
    nombre_paquete            = Column(String,  nullable=True)     # rollo | caja | saco | …
    precio_paquete_base_usd   = Column(Float,   nullable=True)     # precio base del paquete (manual)
    precio_paquete_ref_usd    = Column(Float,   nullable=True)     # precio referencial del paquete (manual)

    # Precios calculados (NO se guardan, se computan al vuelo):
    #   MARKET_FACTOR: precio_referencial = precio_base * (binance/BCV); precio_bs = base * binance
    #   BCV_DIRECT:    precio_referencial = precio_base;                  precio_bs = base * BCV


class VarianteProducto(Base):
    __tablename__ = "variantes_producto"

    id                  = Column(Integer, primary_key=True, index=True)
    producto_id         = Column(Integer, index=True)              # FK → Producto
    clase               = Column(String)                           # "Clase A", "Clase B", etc.
    color               = Column(String,  nullable=True)
    stock               = Column(Integer, default=0)
    precio_override_usd = Column(Float,   nullable=True)           # legado — usar costo_usd+margen en su lugar
    costo_usd           = Column(Float,   nullable=True)           # None → hereda del producto padre
    margen              = Column(Float,   nullable=True)           # None → hereda del producto padre
    activo              = Column(Boolean, default=True)
    codigo              = Column(String,  nullable=True, index=True)  # código del proveedor para esta variante


class ComponenteProducto(Base):
    __tablename__ = "componentes_producto"

    id                    = Column(Integer, primary_key=True, index=True)
    producto_compuesto_id = Column(Integer, index=True)            # FK → Producto (compuesto)
    producto_componente_id= Column(Integer, index=True)            # FK → Producto (componente)
    cantidad              = Column(Float)


class Oferta(Base):
    __tablename__ = "ofertas"

    id               = Column(Integer, primary_key=True, index=True)
    producto_id      = Column(Integer, index=True)                 # FK → Producto
    tipo_precio      = Column(String)                              # "porcentaje" | "directo"
    valor            = Column(Float)                               # % dto o precio directo USD
    fecha_inicio     = Column(Date)
    fecha_fin        = Column(Date,    nullable=True)              # None = activa hasta agotar
    cantidad_limite  = Column(Integer, nullable=True)              # None = ilimitada por fechas
    cantidad_usada   = Column(Integer, default=0)
    activo           = Column(Boolean, default=True)


class TasaCambio(Base):
    __tablename__ = "tasa_cambio"

    id           = Column(Integer, primary_key=True, index=True)
    tasa         = Column(Float)               # tasa BCV (Bs por USD)
    tasa_binance = Column(Float, nullable=True) # tasa Binance (Bs por USD)
    fecha        = Column(DateTime, default=func.now())


class Venta(Base):
    """
    Encabezado de la venta.
    - moneda_venta    : "USD" | "Bs"
    - tipo_precio_usado: "base" | "referencial" | "mixto"
    - factor_cambio   : tasa_binance / tasa_bcv al momento de la venta
    - subtotal/descuento/total : en moneda_venta
    """
    __tablename__ = "ventas"

    id               = Column(Integer, primary_key=True, index=True)
    fecha            = Column(DateTime)
    usuario          = Column(String)
    moneda_venta     = Column(String)    # "USD" | "Bs"
    tipo_precio_usado= Column(String, default="referencial")  # base|referencial|mixto
    subtotal         = Column(Float)
    descuento        = Column(Float,  default=0)
    total            = Column(Float)
    tasa_bcv         = Column(Float)
    tasa_binance     = Column(Float,  nullable=True)
    factor_cambio    = Column(Float,  nullable=True)   # tasa_binance / tasa_bcv
    total_abonado    = Column(Float,  default=0)
    saldo_pendiente  = Column(Float,  default=0)
    exceso           = Column(Float,  default=0)
    estado           = Column(String, default="pagado")
    observacion      = Column(String, nullable=True)


class PagoVenta(Base):
    """Cada abono individual de una venta en su moneda nativa."""
    __tablename__ = "pagos_venta"

    id                = Column(Integer, primary_key=True, index=True)
    venta_id          = Column(Integer, index=True)
    metodo_pago       = Column(String)
    moneda_pago       = Column(String)    # "USD" | "Bs"
    monto_original    = Column(Float)     # en moneda_pago
    tasa_cambio       = Column(Float)
    monto_equivalente = Column(Float)     # en moneda_venta
    moneda_venta      = Column(String)
    referencia         = Column(String, nullable=True)
    fecha_hora         = Column(DateTime)
    usuario            = Column(String)
    cuenta_destino_id  = Column(Integer, nullable=True)  # FK → CuentaBancaria


class DetalleVenta(Base):
    __tablename__ = "detalle_ventas"

    id                    = Column(Integer, primary_key=True, index=True)
    venta_id              = Column(Integer)
    producto_id           = Column(Integer)
    variante_id           = Column(Integer, nullable=True)
    cantidad              = Column(Integer)
    tipo_precio_usado     = Column(String)   # "base" | "referencial"
    precio_base_snap      = Column(Float)    # costo_usd*(1+margen) al momento
    precio_referencial_snap = Column(Float)  # precio_base*factor al momento
    precio_unitario       = Column(Float)    # precio efectivamente cobrado (USD)
    subtotal              = Column(Float)    # en moneda_venta
    precio_libre          = Column(Boolean, default=False)


class Usuario(Base):
    __tablename__ = "usuarios"

    id       = Column(Integer, primary_key=True, index=True)
    nombre   = Column(String)
    email    = Column(String)
    password = Column(String)
    rol      = Column(String, default="vendedor")
    permisos = Column(String, nullable=True)   # JSON string: ["ventas","clientes",...]
    activo   = Column(Boolean, default=True)


class Configuracion(Base):
    __tablename__ = "configuracion"

    id                 = Column(Integer, primary_key=True, index=True)
    clave_autorizacion = Column(String)


class ClaveAutorizacion(Base):
    __tablename__ = "claves_autorizacion"

    id          = Column(Integer, primary_key=True, index=True)
    accion      = Column(String,  unique=True, nullable=False)  # "descuento"|"stock"|"devolucion"
    clave       = Column(String,  nullable=False)
    descripcion = Column(String,  nullable=True)


class ExcepcionVenta(Base):
    __tablename__ = "excepciones_venta"

    id              = Column(Integer, primary_key=True, index=True)
    venta_id        = Column(Integer)
    usuario         = Column(String)
    motivo          = Column(String)
    # descuento_divisa | venta_sin_stock | descuento_producto | descuento_total
    producto_id     = Column(Integer,  nullable=True)
    precio_original = Column(Float,    nullable=True)
    precio_aplicado = Column(Float,    nullable=True)
    descuento       = Column(Float,    nullable=True)
    cantidad        = Column(Integer,  nullable=True)
    created_at      = Column(DateTime, default=datetime.now)


class CierreCaja(Base):
    __tablename__ = "cierres_caja"

    id               = Column(Integer, primary_key=True, index=True)
    fecha            = Column(DateTime, default=datetime.now)
    usuario          = Column(String)
    fecha_desde      = Column(DateTime, nullable=True)
    fecha_hasta      = Column(DateTime)
    cantidad_ventas  = Column(Integer, default=0)
    total_ventas_usd = Column(Float,   default=0)

    esp_efectivo_usd     = Column(Float, default=0)
    esp_zelle            = Column(Float, default=0)
    esp_binance          = Column(Float, default=0)
    esp_efectivo_bs      = Column(Float, default=0)
    esp_transferencia_bs = Column(Float, default=0)
    esp_pago_movil       = Column(Float, default=0)
    esp_punto_banesco    = Column(Float, default=0)
    esp_punto_provincial = Column(Float, default=0)

    cnt_efectivo_usd     = Column(Float, default=0)
    cnt_zelle            = Column(Float, default=0)
    cnt_binance          = Column(Float, default=0)
    cnt_efectivo_bs      = Column(Float, default=0)
    cnt_transferencia_bs = Column(Float, default=0)
    cnt_pago_movil       = Column(Float, default=0)
    cnt_punto_banesco    = Column(Float, default=0)
    cnt_punto_provincial = Column(Float, default=0)

    observacion      = Column(String, nullable=True)
    revisado_por     = Column(String,   nullable=True)
    fecha_revision   = Column(DateTime, nullable=True)
    estado_revision  = Column(String,   default="pendiente")  # pendiente|aprobado|con_diferencias
    nota_revision    = Column(String,   nullable=True)


class Deposito(Base):
    __tablename__ = "depositos"

    id              = Column(Integer,  primary_key=True, index=True)
    fecha           = Column(DateTime, default=datetime.now)
    tipo            = Column(String)                    # "deposito" | "transferencia" | "retiro"
    banco_origen    = Column(String,   nullable=True)
    banco_destino   = Column(String,   nullable=True)
    monto           = Column(Float)
    moneda          = Column(String)                    # "USD" | "Bs"
    referencia      = Column(String,   nullable=True)
    concepto        = Column(String,   nullable=True)
    usuario         = Column(String)
    comprobante_url = Column(String,   nullable=True)


# ---------------------------------------------------------------------------
# Módulo de Compras
# ---------------------------------------------------------------------------

class Proveedor(Base):
    __tablename__ = "proveedores"

    id               = Column(Integer, primary_key=True, index=True)
    nombre           = Column(String)
    rif              = Column(String,  nullable=True)
    telefono         = Column(String,  nullable=True)
    email            = Column(String,  nullable=True)
    direccion        = Column(String,  nullable=True)
    contacto         = Column(String,  nullable=True)
    activo           = Column(Boolean, default=True)
    fecha_registro   = Column(DateTime, default=datetime.now)
    dias_credito       = Column(Integer,  default=0)
    credito_disponible = Column(Float,    default=0)
    codigo             = Column(String,   nullable=True, unique=True, index=True)
    pricing_policy     = Column(String,   default="MARKET_FACTOR")   # MARKET_FACTOR | BCV_DIRECT
    ajuste_divisa_pct  = Column(Float,    default=0.0)               # deprecated — ya no se usa en pricing


class CatalogoProveedor(Base):
    __tablename__ = "catalogo_proveedor"

    id                    = Column(Integer, primary_key=True, index=True)
    proveedor_id          = Column(Integer, index=True)
    rif_proveedor         = Column(String,  nullable=True, index=True)  # clave de cruce: codigo+rif identifica unívocamente el ítem
    producto_id           = Column(Integer, nullable=True)   # None si producto aún no existe
    variante_id           = Column(Integer, nullable=True)   # None si es producto sin variantes
    nombre_producto       = Column(String)
    codigo_proveedor      = Column(String,  nullable=True)
    codigo_huella         = Column(String,  nullable=True, index=True)  # primeros5+ultimos5 normalizado; tolera variaciones OCR en el centro
    precio_referencia_usd = Column(Float,   nullable=True)
    bloqueado             = Column(Boolean, default=False)              # True tras primera compra confirmada — asociacion inamovible


class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"

    id               = Column(Integer, primary_key=True, index=True)
    numero           = Column(String, unique=True)            # "OC-0001"
    proveedor_id     = Column(Integer, index=True)
    fecha_creacion   = Column(DateTime, default=datetime.now)
    fecha_aprobacion = Column(DateTime, nullable=True)
    fecha_esperada   = Column(DateTime, nullable=True)
    estado           = Column(String, default="borrador")     # borrador|aprobada|recibida_parcial|cerrada|anulada
    creado_por       = Column(String)
    aprobado_por     = Column(String, nullable=True)
    moneda           = Column(String, default="USD")
    subtotal         = Column(Float,  default=0)
    descuento        = Column(Float,  default=0)
    total            = Column(Float,  default=0)
    observacion      = Column(String, nullable=True)


class DetalleOrdenCompra(Base):
    __tablename__ = "detalle_orden_compra"

    id                = Column(Integer, primary_key=True, index=True)
    orden_id          = Column(Integer, index=True)
    producto_id       = Column(Integer, nullable=True)
    variante_id       = Column(Integer, nullable=True)
    nombre_producto   = Column(String)
    codigo_proveedor  = Column(String,  nullable=True)
    cantidad_pedida   = Column(Float)
    precio_unitario_usd = Column(Float)
    subtotal          = Column(Float)
    es_producto_nuevo = Column(Boolean, default=False)


class RecepcionCompra(Base):
    __tablename__ = "recepciones_compra"

    id                      = Column(Integer,  primary_key=True, index=True)
    orden_id                = Column(Integer,  index=True)
    fecha_recepcion         = Column(DateTime, default=datetime.now)
    recibido_por            = Column(String)
    observacion             = Column(String,   nullable=True)
    total_recibido          = Column(Float,    default=0)
    fecha_vencimiento_pago  = Column(Date,     nullable=True)
    monto_factura           = Column(Float,    nullable=True)
    estado_pago             = Column(String,   default="pendiente")  # pendiente|pagado|vencido
    fecha_pago_real         = Column(DateTime, nullable=True)
    numero_factura          = Column(String,   nullable=True)
    devuelta                = Column(Boolean,  default=False)        # True cuando admin ejecuta devolución total


class DetalleRecepcion(Base):
    __tablename__ = "detalle_recepcion"

    id                     = Column(Integer, primary_key=True, index=True)
    recepcion_id           = Column(Integer, index=True)
    detalle_orden_id       = Column(Integer)
    producto_id            = Column(Integer)
    variante_id            = Column(Integer, nullable=True)
    cantidad_recibida      = Column(Float)
    precio_unitario_real_usd = Column(Float)
    subtotal               = Column(Float)
    actualizo_costo        = Column(Boolean, default=False)
    costo_anterior         = Column(Float,   nullable=True)


# ---------------------------------------------------------------------------
# Módulo Bancario
# ---------------------------------------------------------------------------

class CuentaBancaria(Base):
    __tablename__ = "cuentas_bancarias"

    id             = Column(Integer, primary_key=True, index=True)
    nombre         = Column(String)
    banco          = Column(String)
    tipo_cuenta    = Column(String)   # personal|juridica|caja_fisica|billetera_digital
    moneda         = Column(String)   # USD|Bs
    identificador  = Column(String,  nullable=True)
    activa         = Column(Boolean, default=True)
    orden_display  = Column(Integer, default=99)


class MetodoPagoCuenta(Base):
    """Vínculo entre un método de pago y una cuenta bancaria destino."""
    __tablename__ = "metodo_pago_cuenta"

    id          = Column(Integer, primary_key=True, index=True)
    metodo_pago = Column(String, index=True)
    cuenta_id   = Column(Integer, index=True)
    activo      = Column(Boolean, default=True)


class MovimientoBancario(Base):
    __tablename__ = "movimientos_bancarios"

    id                = Column(Integer, primary_key=True, index=True)
    fecha             = Column(DateTime, default=datetime.now)
    tipo              = Column(String)   # ingreso_venta|transferencia_interna|pago_proveedor|gasto_nomina|gasto_operativo|gasto_administrativo|ingreso_externo|retiro
    cuenta_origen_id  = Column(Integer, nullable=True)
    cuenta_destino_id = Column(Integer, nullable=True)
    monto             = Column(Float)
    moneda            = Column(String)
    tasa_cambio       = Column(Float,   nullable=True)
    monto_convertido  = Column(Float,   nullable=True)
    referencia        = Column(String,  nullable=True)
    concepto          = Column(String)
    beneficiario      = Column(String,  nullable=True)
    categoria         = Column(String)  # ventas|proveedores|nomina|operativo|administrativo|financiero|propietario
    proveedor_id      = Column(Integer, nullable=True)
    orden_compra_id   = Column(Integer, nullable=True)
    registrado_por    = Column(String)
    estado            = Column(String, default="registrado")  # registrado|anulado
    venta_id          = Column(Integer, nullable=True)        # si viene de una venta


# ---------------------------------------------------------------------------
# Módulo de Clientes y Fidelidad
# ---------------------------------------------------------------------------

class Cliente(Base):
    __tablename__ = "clientes"

    id                  = Column(Integer,  primary_key=True, index=True)
    nombre              = Column(String)
    telefono            = Column(String,   index=True)
    email               = Column(String,   nullable=True)
    direccion           = Column(String,   nullable=True)
    tipo_cliente        = Column(String,   default="natural")   # natural|juridico
    rif_cedula          = Column(String,   nullable=True)
    fecha_registro      = Column(DateTime, default=datetime.now)
    activo              = Column(Boolean,  default=True)
    notas               = Column(String,   nullable=True)
    es_cliente_generico = Column(Boolean,  default=False)  # True = "Consumidor Final"
    credito_disponible  = Column(Float,    default=0)
    codigo              = Column(String,   nullable=True, unique=True, index=True)
    tiene_credito       = Column(Boolean,  default=False)
    limite_credito      = Column(Float,    default=0)
    saldo_credito       = Column(Float,    default=0)
    saldo_a_favor       = Column(Float,    default=0)   # crédito acumulado por devoluciones

    __table_args__ = (
        Index('ix_cliente_nombre_busq',    'nombre'),
        Index('ix_cliente_telefono_busq',  'telefono'),
    )


class VentaCliente(Base):
    """Vínculo entre una venta y un cliente (máximo uno por venta)."""
    __tablename__ = "venta_cliente"

    id         = Column(Integer,  primary_key=True, index=True)
    venta_id   = Column(Integer,  unique=True, index=True)
    cliente_id = Column(Integer,  index=True)
    fecha      = Column(DateTime, default=datetime.now)


class NivelFidelidad(Base):
    __tablename__ = "niveles_fidelidad"

    id                    = Column(Integer, primary_key=True, index=True)
    nombre                = Column(String)
    min_compras           = Column(Integer, default=0)
    min_monto_usd         = Column(Float,   default=0)
    beneficio_descripcion = Column(String,  nullable=True)
    color_badge           = Column(String,  default="#a8a8b3")
    orden                 = Column(Integer, default=99)


class PremioFidelidad(Base):
    __tablename__ = "premios_fidelidad"

    id           = Column(Integer,  primary_key=True, index=True)
    cliente_id   = Column(Integer,  index=True)
    tipo         = Column(String)   # por_cantidad|por_monto
    descripcion  = Column(String)
    fecha        = Column(DateTime, default=datetime.now)
    otorgado_por = Column(String)
    observacion  = Column(String,   nullable=True)


class AbonoCredito(Base):
    """Registro de cargos (deuda) y abonos (pagos) de crédito a clientes."""
    __tablename__ = "abonos_credito"

    id          = Column(Integer,  primary_key=True, index=True)
    cliente_id  = Column(Integer,  nullable=False, index=True)
    venta_id    = Column(Integer,  nullable=True)   # si viene de una venta a crédito
    monto       = Column(Float,    nullable=False)  # positivo=abono(pago), negativo=cargo(deuda)
    metodo_pago = Column(String,   nullable=True)   # método con que abonó (null si es cargo)
    fecha       = Column(DateTime, default=datetime.now)
    observacion = Column(String,   nullable=True)
    usuario     = Column(String,   nullable=True)


# ---------------------------------------------------------------------------
# Módulo de Vendedores y Comisiones
# ---------------------------------------------------------------------------

class VendedorPerfil(Base):
    __tablename__ = "vendedor_perfil"

    id           = Column(Integer, primary_key=True, index=True)
    usuario_id   = Column(Integer, unique=True, index=True)
    periodo_pago = Column(String,  default="quincenal")  # "semanal" | "quincenal"
    comision_base= Column(Float,   default=0)            # ej: 0.03 = 3%
    activo       = Column(Boolean, default=True)


class ComisionEspecial(Base):
    __tablename__ = "comision_especial"

    id            = Column(Integer, primary_key=True, index=True)
    vendedor_id   = Column(Integer, index=True)          # FK → VendedorPerfil
    tipo          = Column(String)                       # "departamento"|"proveedor"|"pareto"|"producto"
    referencia_id = Column(Integer, nullable=True)       # id del depto/proveedor/producto
    porcentaje    = Column(Float)                        # ej: 0.05 = 5%


class ComisionVenta(Base):
    __tablename__ = "comision_venta"

    id                  = Column(Integer, primary_key=True, index=True)
    venta_id            = Column(Integer, index=True)
    vendedor_id         = Column(Integer, index=True)
    detalle_venta_id    = Column(Integer, index=True)
    producto_id         = Column(Integer)
    monto_venta_usd     = Column(Float)
    porcentaje_aplicado = Column(Float)
    monto_comision      = Column(Float)
    tipo_regla          = Column(String)                 # qué regla ganó
    fecha               = Column(DateTime, default=datetime.now)


class PeriodoComision(Base):
    __tablename__ = "periodo_comision"

    id               = Column(Integer, primary_key=True, index=True)
    vendedor_id      = Column(Integer, index=True)
    fecha_inicio     = Column(Date)
    fecha_fin        = Column(Date)
    total_ventas_usd = Column(Float,    default=0)
    total_comision   = Column(Float,    default=0)
    estado           = Column(String,   default="pendiente")  # "pendiente" | "pagado"
    fecha_pago       = Column(DateTime, nullable=True)
    pagado_por       = Column(String,   nullable=True)
    observacion      = Column(String,   nullable=True)


# ---------------------------------------------------------------------------
# Módulo de Ajustes masivos
# ---------------------------------------------------------------------------

class HistorialAjuste(Base):
    __tablename__ = "historial_ajustes"

    id                  = Column(Integer,  primary_key=True, index=True)
    fecha               = Column(DateTime, default=datetime.now)
    usuario             = Column(String)
    tipo                = Column(String)    # "stock" | "precio" | "comision"
    descripcion         = Column(String)
    productos_afectados = Column(Integer,  default=0)
    detalle_json        = Column(String,   nullable=True)  # JSON con cambios


# ---------------------------------------------------------------------------
# Módulo de Presupuestos
# ---------------------------------------------------------------------------

class Presupuesto(Base):
    __tablename__ = "presupuestos"

    id                = Column(Integer,  primary_key=True, index=True)
    numero            = Column(String,   unique=True)
    cliente_id        = Column(Integer,  nullable=True)
    cliente_nombre    = Column(String,   nullable=True)
    cliente_telefono  = Column(String,   nullable=True)
    usuario           = Column(String)
    fecha             = Column(DateTime, default=datetime.now)
    fecha_vencimiento = Column(DateTime)
    subtotal          = Column(Float,    default=0)
    descuento         = Column(Float,    default=0)
    total             = Column(Float,    default=0)
    moneda            = Column(String,   default="USD")
    tasa_bcv          = Column(Float,    nullable=True)
    estado            = Column(String,   default="pendiente")  # pendiente|aprobado|vencido|convertido
    observacion       = Column(String,   nullable=True)
    venta_id          = Column(Integer,  nullable=True)


class DetallePresupuesto(Base):
    __tablename__ = "detalle_presupuesto"

    id              = Column(Integer, primary_key=True, index=True)
    presupuesto_id  = Column(Integer, index=True)
    producto_id     = Column(Integer, nullable=True)
    variante_id     = Column(Integer, nullable=True)
    nombre_producto = Column(String)
    cantidad        = Column(Float)
    precio_unitario = Column(Float)
    subtotal        = Column(Float)


# ---------------------------------------------------------------------------
# Módulo de Devoluciones
# ---------------------------------------------------------------------------

class DevolucionCliente(Base):
    __tablename__ = "devoluciones_cliente"

    id               = Column(Integer,  primary_key=True, index=True)
    venta_id         = Column(Integer,  index=True)
    cliente_id       = Column(Integer,  nullable=True)
    usuario          = Column(String)
    fecha            = Column(DateTime, default=datetime.now)
    motivo           = Column(String)
    tipo_resolucion  = Column(String)   # "dinero" | "credito"
    monto_total      = Column(Float,    default=0)
    observacion      = Column(String,   nullable=True)


class DetalleDevolucionCliente(Base):
    __tablename__ = "detalle_devolucion_cliente"

    id                  = Column(Integer, primary_key=True, index=True)
    devolucion_id       = Column(Integer, index=True)
    producto_id         = Column(Integer)
    variante_id         = Column(Integer, nullable=True)
    nombre_producto     = Column(String)
    cantidad            = Column(Float)
    precio_unitario     = Column(Float)
    vuelve_inventario   = Column(Boolean, default=True)


class DevolucionProveedor(Base):
    __tablename__ = "devoluciones_proveedor"

    id               = Column(Integer,  primary_key=True, index=True)
    proveedor_id     = Column(Integer,  index=True)
    producto_id      = Column(Integer,  index=True)
    nombre_producto  = Column(String)
    cantidad         = Column(Float)
    costo_unitario   = Column(Float)
    monto_total      = Column(Float)
    motivo           = Column(String)
    tipo_resolucion  = Column(String)   # "descuento_factura" | "credito"
    estado           = Column(String,   default="pendiente")  # pendiente|resuelto
    fecha            = Column(DateTime, default=datetime.now)
    fecha_resolucion = Column(DateTime, nullable=True)
    orden_compra_id  = Column(Integer,  nullable=True)
    usuario          = Column(String)
    observacion      = Column(String,   nullable=True)


# ── Ubicaciones físicas ───────────────────────────────────────────────────────

class Area(Base):
    __tablename__ = "areas"
    id     = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    activa = Column(Boolean, default=True)


class Pasillo(Base):
    __tablename__ = "pasillos"
    id      = Column(Integer, primary_key=True, index=True)
    area_id = Column(Integer, index=True)
    numero  = Column(Integer)
    activo  = Column(Boolean, default=True)


class Estante(Base):
    __tablename__ = "estantes"
    id         = Column(Integer, primary_key=True, index=True)
    pasillo_id = Column(Integer, index=True)
    numero     = Column(Integer)
    activo     = Column(Boolean, default=True)


class UbicacionProducto(Base):
    __tablename__ = "ubicaciones_producto"
    id          = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, index=True)
    area_id     = Column(Integer)
    pasillo_id  = Column(Integer)
    estante_id  = Column(Integer)
    nivel       = Column(Integer)
    cantidad    = Column(Float, default=0)
    activa      = Column(Boolean, default=True)


class AliasProveedor(Base):
    __tablename__ = "alias_proveedores"

    id                = Column(Integer,  primary_key=True, index=True)
    proveedor_id      = Column(Integer,  nullable=False, index=True)
    alias             = Column(String,   nullable=False)
    alias_normalizado = Column(String,   nullable=False, index=True)
    fecha_creacion    = Column(DateTime, default=datetime.now)
    creado_por        = Column(String,   nullable=True)


# ---------------------------------------------------------------------------
# Módulo de Garantías
# ---------------------------------------------------------------------------

class PlantillaGarantia(Base):
    __tablename__ = "plantillas_garantia"

    id          = Column(Integer, primary_key=True, index=True)
    nombre      = Column(String,  nullable=False)          # "Garantía Bombas Sumergibles"
    meses       = Column(Integer, default=0)               # duración en meses
    condiciones = Column(String,  nullable=True)           # texto completo de condiciones
    activa      = Column(Boolean, default=True)


class GarantiaVenta(Base):
    """Registro de garantía por ítem vendido. El texto se copia (snapshot) al momento de la venta."""
    __tablename__ = "garantias_venta"

    id                   = Column(Integer,  primary_key=True, index=True)
    venta_id             = Column(Integer,  index=True, nullable=False)
    producto_id          = Column(Integer,  index=True, nullable=False)
    variante_id          = Column(Integer,  nullable=True)
    serial               = Column(String,   nullable=True)
    modelo               = Column(String,   nullable=True)
    meses_garantia       = Column(Integer,  nullable=True)   # copiado de la plantilla
    condiciones_snapshot = Column(String,   nullable=True)   # texto copiado al momento de venta
    fecha                = Column(DateTime, default=datetime.now)


# ---------------------------------------------------------------------------
# Módulo de Notificaciones y Radar de Demanda
# ---------------------------------------------------------------------------

class Aviso(Base):
    __tablename__ = "avisos"

    id           = Column(Integer,  primary_key=True, index=True)
    titulo       = Column(String,   nullable=False)
    mensaje      = Column(String,   nullable=False)
    creado_por   = Column(String,   nullable=False)
    fecha        = Column(DateTime, default=datetime.now)
    activo       = Column(Boolean,  default=True)
    destinatario = Column(String,   nullable=True)  # None = todos, o nombre usuario específico


class DemandaRegistro(Base):
    __tablename__ = "demanda_registro"

    id                 = Column(Integer,  primary_key=True, index=True)
    tipo               = Column(String,   nullable=False)  # "venta_perdida" | "consulta" | "alerta_precio"
    producto_id        = Column(Integer,  nullable=True)
    nombre_producto    = Column(String,   nullable=False)
    cantidad           = Column(Float,    nullable=True)   # para venta_perdida
    competencia        = Column(String,   nullable=True)   # nombre competencia para alerta_precio
    precio_competencia = Column(Float,    nullable=True)   # precio que ofrece la competencia
    vendedor           = Column(String,   nullable=False)
    fecha              = Column(DateTime, default=datetime.now)
    visto_por_admin    = Column(Boolean,  default=False)
    observacion        = Column(String,   nullable=True)
