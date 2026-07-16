"""
Módulo de reposición — ficha por producto, cálculo de semáforo y recomendación
de pedido. La lógica pura (calcular_reposicion) no toca DB ni FastAPI, es
importable y testeable directo, igual que pricing.py.

obtener_ficha_reposicion(db, producto_id) es la orquestación: resuelve
proveedores, ventas 90d y pedidos vencidos desde la base, y llama a la
función pura con esos valores ya resueltos.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    Producto, Proveedor, ProductoProveedor, ProductoReposicion,
    Venta, DetalleVenta, OrdenCompra, DetalleOrdenCompra, RecepcionCompra,
)

MODO_STOCK_CONTINUO    = "stock_continuo"
MODO_PEDIDO_BAJO_DEMANDA = "pedido_bajo_demanda"
MODO_LOTE_GRANDE       = "lote_grande"
MODO_STOCK_ESTRATEGICO = "stock_estrategico_descuento"
MODOS_VALIDOS = {
    MODO_STOCK_CONTINUO, MODO_PEDIDO_BAJO_DEMANDA, MODO_LOTE_GRANDE, MODO_STOCK_ESTRATEGICO,
}

DIAS_COBERTURA_INFINITO = 999   # mismo sentinel que ya usa rutas/reportes.py

CAUSA_PROVEEDOR = "proveedor_sin_producto"


# ============================================================================
# Función pura — el corazón del modelo. Sin DB, sin FastAPI.
# ============================================================================

def _dias_cobertura(disponible: float, venta_diaria: float) -> float:
    if venta_diaria and venta_diaria > 0:
        return round(disponible / venta_diaria, 1)
    return DIAS_COBERTURA_INFINITO


def _semaforo_stock_continuo(dias_cobertura: float, lead_time_dias: int, colchon_dias: int) -> str:
    umbral_alerta = lead_time_dias + colchon_dias
    piso_rojo     = umbral_alerta - lead_time_dias   # == colchon_dias
    if dias_cobertura > umbral_alerta:
        return "verde"
    if dias_cobertura >= piso_rojo:
        return "amarillo"
    return "rojo"


def _semaforo_lote_grande(disponible: float, venta_diaria: float,
                           lead_time_dias: int, colchon_dias: int) -> str:
    # Alerta única en unidades, sin escalonar amarillo — o se pide el próximo lote, o no.
    umbral_unidades = venta_diaria * (lead_time_dias + colchon_dias)
    return "rojo" if disponible < umbral_unidades else "verde"


def _semaforo_stock_estrategico(disponible: float, stock_min_objetivo: int) -> str:
    # stock_min acá es el mínimo del descuento del proveedor, no un cálculo de rotación.
    return "rojo" if disponible < stock_min_objetivo else "verde"


def _semaforo_pedido_bajo_demanda(pedido_vencido: bool) -> str:
    # Nunca alerta por stock bajo — solo por pedido abierto vencido.
    return "rojo" if pedido_vencido else "verde"


def _texto_recomendacion(estado, cantidad_sugerida, proveedor_sugerido,
                          usar_alternativo, sin_stock_fecha, pedido_vencido) -> str:
    if estado == "gris":
        fecha_txt = f" desde {sin_stock_fecha}" if sin_stock_fecha else ""
        return (f"Proveedor(es) sin stock declarado{fecha_txt}. "
                f"No es falla de gestión — esperar reposición del mercado o buscar otro proveedor.")
    if estado == "verde":
        return "Cobertura suficiente. No hace falta pedir todavía."

    partes = [f"Pedir {cantidad_sugerida} unidades"]
    if proveedor_sugerido:
        partes.append(f"a {proveedor_sugerido}")
    texto = " ".join(partes)
    if usar_alternativo:
        texto += " (proveedor principal sin stock declarado — usar alternativo)"
    if pedido_vencido:
        texto += ". Hay un pedido previo vencido sin despachar."
    return texto


def calcular_reposicion(
    modo: str,
    disponible: float,
    venta_diaria: float,
    lead_time_dias: int,
    colchon_dias: int,
    stock_min_objetivo: int = 0,
    stock_max_objetivo: int = 0,
    minimo_compra: int | None = None,
    sin_stock_todos: bool = False,
    sin_stock_principal: bool = False,
    sin_stock_fecha: str | None = None,
    pedido_vencido: bool = False,
    proveedor_principal_nombre: str | None = None,
    proveedor_alternativo_nombre: str | None = None,
) -> dict:
    """
    Calcula días de cobertura, semáforo, causa de quiebre y recomendación de
    pedido para UN producto. Todos los inputs ya vienen resueltos (sin
    herencia pendiente, sin acceso a DB).
    """
    dias_cob = _dias_cobertura(disponible, venta_diaria)

    if modo == MODO_PEDIDO_BAJO_DEMANDA:
        estado = _semaforo_pedido_bajo_demanda(pedido_vencido)
    elif modo == MODO_LOTE_GRANDE:
        estado = _semaforo_lote_grande(disponible, venta_diaria, lead_time_dias, colchon_dias)
    elif modo == MODO_STOCK_ESTRATEGICO:
        estado = _semaforo_stock_estrategico(disponible, stock_min_objetivo)
    else:
        estado = _semaforo_stock_continuo(dias_cob, lead_time_dias, colchon_dias)

    causa_quiebre = None

    # C24: si TODOS los proveedores cargados están sin stock declarado, gris
    # manda sobre cualquier otro estado — no es responsabilidad de gestión.
    if sin_stock_todos:
        estado = "gris"
        causa_quiebre = CAUSA_PROVEEDOR
    elif pedido_vencido and estado == "rojo":
        causa_quiebre = CAUSA_PROVEEDOR

    cantidad_sugerida = int(round(max(
        (stock_max_objetivo or 0) - disponible,
        minimo_compra or 0,
        0,
    )))

    # Si el principal está sin stock declarado (pero no todos), recomendar el alternativo.
    usar_alternativo = bool(sin_stock_principal and not sin_stock_todos and proveedor_alternativo_nombre)
    proveedor_sugerido = proveedor_alternativo_nombre if usar_alternativo else proveedor_principal_nombre

    recomendacion_texto = _texto_recomendacion(
        estado, cantidad_sugerida, proveedor_sugerido, usar_alternativo, sin_stock_fecha, pedido_vencido,
    )

    return {
        "venta_diaria_90d":       round(venta_diaria, 4),
        "existencia_disponible":  disponible,
        "dias_cobertura":         dias_cob,
        "estado_semaforo":        estado,
        "causa_quiebre":          causa_quiebre,
        "recomendacion_pedido": {
            "texto":              recomendacion_texto,
            "cantidad_sugerida":  cantidad_sugerida,
            "proveedor_sugerido": proveedor_sugerido,
        },
    }


# ============================================================================
# Orquestación — toca DB, resuelve herencia, arma inputs y llama a la función
# pura. No importa FastAPI: retorna dict o None, sin HTTPException.
# ============================================================================

def _resolver_lead_time(pp: ProductoProveedor, proveedor: Proveedor) -> int:
    if pp.lead_time_dias is not None:
        return int(pp.lead_time_dias)
    return int(proveedor.lead_time_dias_default or 0)


def _resolver_credito(pp: ProductoProveedor, proveedor: Proveedor) -> int:
    if pp.credito_dias is not None:
        return int(pp.credito_dias)
    return int(proveedor.dias_credito or 0)


def _hay_pedido_vencido(db: Session, producto_id: int, proveedor_id: int, corte: datetime) -> bool:
    ordenes = (
        db.query(OrdenCompra)
        .join(DetalleOrdenCompra, DetalleOrdenCompra.orden_id == OrdenCompra.id)
        .filter(
            DetalleOrdenCompra.producto_id == producto_id,
            OrdenCompra.proveedor_id == proveedor_id,
            OrdenCompra.estado == "aprobada",
            OrdenCompra.fecha_esperada.isnot(None),
            OrdenCompra.fecha_esperada < corte,
        )
        .all()
    )
    for orden in ordenes:
        tiene_recepcion = db.query(RecepcionCompra).filter(RecepcionCompra.orden_id == orden.id).first()
        if not tiene_recepcion:
            return True
    return False


def _venta_diaria_90d(db: Session, producto_id: int, corte: datetime) -> float:
    desde = corte - timedelta(days=90)
    total_vendido = (
        db.query(func.sum(DetalleVenta.cantidad))
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .filter(
            DetalleVenta.producto_id == producto_id,
            Venta.fecha >= desde, Venta.fecha < corte,
            Venta.estado != "anulada",
        )
        .scalar()
    ) or 0
    return float(total_vendido) / 90


def obtener_ficha_reposicion(db: Session, producto_id: int) -> dict | None:
    """
    Retorna None si el producto no existe.
    Retorna {"producto_id":.., "ficha_cargada": False, ...} si el producto existe
    pero todavía no tiene ProductoReposicion (caso "Ficha no cargada" del frontend
    y filas sin cargar en la vista tabla). Igual trae código/descripción/existencia/
    venta_diaria_90d porque la vista tabla los necesita para ordenar y mostrar la
    fila aunque no haya ficha todavía.
    """
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        return None

    ficha = db.query(ProductoReposicion).filter(ProductoReposicion.producto_id == producto_id).first()
    if not ficha:
        corte = datetime.now(timezone.utc).replace(tzinfo=None)
        return {
            "producto_id": producto_id,
            "ficha_cargada": False,
            "producto_codigo": producto.codigo,
            "producto_descripcion": producto.descripcion or producto.nombre,
            "existencia": producto.stock,
            "venta_diaria_90d": round(_venta_diaria_90d(db, producto_id, corte), 4),
        }

    filas_pp = (
        db.query(ProductoProveedor)
        .filter(ProductoProveedor.producto_id == producto_id)
        .order_by(ProductoProveedor.prioridad)
        .all()
    )
    proveedores_map = {}
    if filas_pp:
        proveedores_map = {
            p.id: p for p in db.query(Proveedor).filter(
                Proveedor.id.in_([pp.proveedor_id for pp in filas_pp])
            ).all()
        }

    principal   = next((pp for pp in filas_pp if pp.prioridad == 1), None)
    alternativo = next((pp for pp in filas_pp if pp.prioridad == 2), None)

    lead_time_dias = 0
    credito_dias   = 0
    proveedor_principal_nombre = None
    if principal:
        prov = proveedores_map.get(principal.proveedor_id)
        if prov:
            lead_time_dias = _resolver_lead_time(principal, prov)
            credito_dias   = _resolver_credito(principal, prov)
            proveedor_principal_nombre = prov.nombre

    proveedor_alternativo_nombre = None
    if alternativo:
        prov_alt = proveedores_map.get(alternativo.proveedor_id)
        if prov_alt:
            proveedor_alternativo_nombre = prov_alt.nombre

    sin_stock_todos     = bool(filas_pp) and all(pp.sin_stock_declarado for pp in filas_pp)
    sin_stock_principal = bool(principal and principal.sin_stock_declarado)
    sin_stock_fecha = (
        principal.sin_stock_fecha.isoformat()
        if principal and principal.sin_stock_fecha else None
    )

    # datetime.now(timezone.utc).replace(tzinfo=None) en vez de datetime.utcnow()
    # (deprecado) — se mantiene NAIVE a propósito: Venta.fecha se guarda sin
    # tzinfo en toda la base (igual que el resto del proyecto), así que un
    # datetime.now(UTC) con tzinfo puesto rompería la comparación en Postgres
    # ("cannot compare timestamp with time zone and without time zone").
    corte = datetime.now(timezone.utc).replace(tzinfo=None)
    venta_diaria = _venta_diaria_90d(db, producto_id, corte)

    disponible = float(producto.stock or 0) - float(ficha.unidades_exhibicion or 0)

    pedido_vencido = False
    if principal:
        pedido_vencido = _hay_pedido_vencido(db, producto_id, principal.proveedor_id, corte)

    resultado = calcular_reposicion(
        modo=ficha.modo_reposicion,
        disponible=disponible,
        venta_diaria=venta_diaria,
        lead_time_dias=lead_time_dias,
        colchon_dias=int(ficha.colchon_dias or 0),
        stock_min_objetivo=int(ficha.stock_min_objetivo or 0),
        stock_max_objetivo=int(ficha.stock_max_objetivo or 0),
        minimo_compra=principal.minimo_compra if principal else None,
        sin_stock_todos=sin_stock_todos,
        sin_stock_principal=sin_stock_principal,
        sin_stock_fecha=sin_stock_fecha,
        pedido_vencido=pedido_vencido,
        proveedor_principal_nombre=proveedor_principal_nombre,
        proveedor_alternativo_nombre=proveedor_alternativo_nombre,
    )

    resultado.update({
        "producto_id":    producto_id,
        "ficha_cargada":  True,
        "producto_codigo": producto.codigo,
        "producto_descripcion": producto.descripcion or producto.nombre,
        "existencia":     producto.stock,
        "modo_reposicion": ficha.modo_reposicion,
        "activo":         ficha.activo,
        "stock_min_objetivo": ficha.stock_min_objetivo,
        "stock_max_objetivo": ficha.stock_max_objetivo,
        "unidades_exhibicion": ficha.unidades_exhibicion,
        "colchon_dias":   ficha.colchon_dias,
        "notas":          ficha.notas,
        "actualizado_en": ficha.actualizado_en.isoformat() if ficha.actualizado_en else None,
        "lead_time_dias_proveedor_principal": lead_time_dias,
        "credito_dias_proveedor_principal":   credito_dias,
        "proveedores": [
            {
                "prioridad":           pp.prioridad,
                "proveedor_id":        pp.proveedor_id,
                "proveedor_nombre":    proveedores_map.get(pp.proveedor_id).nombre if proveedores_map.get(pp.proveedor_id) else None,
                "precio_actual_usd":   pp.precio_actual_usd,
                "credito_dias":        pp.credito_dias,
                "lead_time_dias":      pp.lead_time_dias,
                "minimo_compra":       pp.minimo_compra,
                "notas":               pp.notas,
                "sin_stock_declarado": pp.sin_stock_declarado,
                "sin_stock_fecha":     pp.sin_stock_fecha.isoformat() if pp.sin_stock_fecha else None,
            }
            for pp in filas_pp
        ],
    })
    return resultado
