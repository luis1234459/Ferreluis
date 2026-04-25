"""
Módulo de Compras — Órdenes, Recepciones, Proveedores y Facturas.

Flujo de estado:
  borrador → aprobada (solo admin)
  aprobada → recibida_parcial / cerrada (al recibir)
  recibida_parcial → cerrada (al recibir el resto)
  borrador/aprobada → anulada (admin; cajero solo su borrador)
  cerrada → inmutable
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from database import get_db
from models import (
    Proveedor, CatalogoProveedor, OrdenCompra, DetalleOrdenCompra,
    RecepcionCompra, DetalleRecepcion, Producto, VarianteProducto,
)
from rutas.usuarios import require_admin
from typing import Optional
from datetime import datetime, date, timedelta

router = APIRouter(prefix="/compras", tags=["compras"])

ESTADOS_VALIDOS = {"borrador", "aprobada", "recibida_parcial", "cerrada", "anulada"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_numero(db: Session) -> str:
    ultimo = db.query(OrdenCompra).order_by(OrdenCompra.id.desc()).first()
    siguiente = (ultimo.id + 1) if ultimo else 1
    return f"OC-{siguiente:04d}"


def _serializar_orden(o: OrdenCompra, db: Session) -> dict:
    prov = db.query(Proveedor).filter(Proveedor.id == o.proveedor_id).first()
    detalles = db.query(DetalleOrdenCompra).filter(DetalleOrdenCompra.orden_id == o.id).all()
    return {
        "id":               o.id,
        "numero":           o.numero,
        "proveedor_id":     o.proveedor_id,
        "proveedor_nombre": prov.nombre if prov else None,
        "fecha_creacion":   o.fecha_creacion.isoformat() if o.fecha_creacion else None,
        "fecha_aprobacion": o.fecha_aprobacion.isoformat() if o.fecha_aprobacion else None,
        "fecha_esperada":   o.fecha_esperada.isoformat() if o.fecha_esperada else None,
        "estado":           o.estado,
        "creado_por":       o.creado_por,
        "aprobado_por":     o.aprobado_por,
        "moneda":           o.moneda,
        "subtotal":         round(float(o.subtotal or 0), 2),
        "descuento":        round(float(o.descuento or 0), 2),
        "total":            round(float(o.total or 0), 2),
        "observacion":      o.observacion,
        "detalles": [
            {
                "id":                  d.id,
                "producto_id":         d.producto_id,
                "variante_id":         d.variante_id,
                "nombre_producto":     d.nombre_producto,
                "codigo_proveedor":    d.codigo_proveedor,
                "cantidad_pedida":     d.cantidad_pedida,
                "precio_unitario_usd": d.precio_unitario_usd,
                "subtotal":            round(float(d.subtotal or 0), 2),
                "es_producto_nuevo":   d.es_producto_nuevo,
            }
            for d in detalles
        ],
    }


def _recalcular_totales(orden: OrdenCompra, db: Session):
    detalles = db.query(DetalleOrdenCompra).filter(DetalleOrdenCompra.orden_id == orden.id).all()
    subtotal = sum(float(d.subtotal or 0) for d in detalles)
    orden.subtotal = round(subtotal, 2)
    orden.total    = round(subtotal - float(orden.descuento or 0), 2)


def _serializar_factura(r: RecepcionCompra, db: Session) -> dict:
    orden = db.query(OrdenCompra).filter(OrdenCompra.id == r.orden_id).first()
    prov  = db.query(Proveedor).filter(Proveedor.id == orden.proveedor_id).first() if orden else None
    hoy   = date.today()

    dias_restantes = None
    alerta         = "sin_vencimiento"
    if r.fecha_vencimiento_pago:
        dias_restantes = (r.fecha_vencimiento_pago - hoy).days
        if dias_restantes < 0:
            alerta = "vencida"
        elif dias_restantes <= 5:
            alerta = "proxima"
        else:
            alerta = "ok"

    return {
        "id":                     r.id,
        "orden_id":               r.orden_id,
        "numero_orden":           orden.numero if orden else None,
        "proveedor_id":           prov.id if prov else None,
        "proveedor_nombre":       prov.nombre if prov else None,
        "fecha_recepcion":        r.fecha_recepcion.isoformat() if r.fecha_recepcion else None,
        "fecha_vencimiento_pago": r.fecha_vencimiento_pago.isoformat() if r.fecha_vencimiento_pago else None,
        "monto_factura":          float(r.monto_factura) if r.monto_factura else None,
        "numero_factura":         r.numero_factura,
        "estado_pago":            r.estado_pago or "pendiente",
        "dias_restantes":         dias_restantes,
        "alerta":                 alerta,
    }


# ---------------------------------------------------------------------------
# PROVEEDORES
# ---------------------------------------------------------------------------

@router.get("/proveedores/")
def listar_proveedores(db: Session = Depends(get_db)):
    return db.query(Proveedor).filter(Proveedor.activo == True).order_by(Proveedor.nombre).all()


@router.post("/proveedores/")
def crear_proveedor(datos: dict, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    if not datos.get("nombre"):
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    p = Proveedor(
        nombre         = datos["nombre"],
        rif            = datos.get("rif"),
        telefono       = datos.get("telefono"),
        email          = datos.get("email"),
        direccion      = datos.get("direccion"),
        contacto       = datos.get("contacto"),
        dias_credito   = int(datos.get("dias_credito", 0) or 0),
        activo         = True,
        fecha_registro = datetime.now(),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    if not p.codigo:
        p.codigo = f"PRV-{p.id:04d}"
        db.commit()
        db.refresh(p)
    return p


@router.put("/proveedores/{proveedor_id}")
def actualizar_proveedor(proveedor_id: int, datos: dict, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    for k in ("nombre", "rif", "telefono", "email", "direccion", "contacto"):
        if k in datos:
            setattr(p, k, datos[k])
    if "dias_credito" in datos:
        p.dias_credito = int(datos["dias_credito"] or 0)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/proveedores/{proveedor_id}")
def eliminar_proveedor(proveedor_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    p.activo = False
    db.commit()
    return {"mensaje": "Proveedor desactivado"}


# Catálogo del proveedor
@router.get("/proveedores/{proveedor_id}/catalogo")
def listar_catalogo(proveedor_id: int, db: Session = Depends(get_db)):
    return db.query(CatalogoProveedor).filter(CatalogoProveedor.proveedor_id == proveedor_id).all()


@router.post("/proveedores/{proveedor_id}/catalogo")
def agregar_catalogo(proveedor_id: int, datos: dict, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    vid = datos.get("variante_id")
    item = CatalogoProveedor(
        proveedor_id          = proveedor_id,
        producto_id           = datos.get("producto_id"),
        variante_id           = int(vid) if vid else None,
        nombre_producto       = datos.get("nombre_producto", ""),
        codigo_proveedor      = datos.get("codigo_proveedor"),
        precio_referencia_usd = datos.get("precio_referencia_usd"),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/proveedores/{proveedor_id}/catalogo/{item_id}")
def actualizar_catalogo(proveedor_id: int, item_id: int, datos: dict,
                         db: Session = Depends(get_db), _: None = Depends(require_admin)):
    item = db.query(CatalogoProveedor).filter(
        CatalogoProveedor.id == item_id,
        CatalogoProveedor.proveedor_id == proveedor_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Ítem de catálogo no encontrado")
    for k in ("nombre_producto", "codigo_proveedor", "precio_referencia_usd", "producto_id", "variante_id"):
        if k in datos:
            setattr(item, k, datos[k])
    db.commit()
    db.refresh(item)
    return item


@router.delete("/proveedores/{proveedor_id}/catalogo/{item_id}")
def eliminar_catalogo(proveedor_id: int, item_id: int,
                       db: Session = Depends(get_db), _: None = Depends(require_admin)):
    item = db.query(CatalogoProveedor).filter(CatalogoProveedor.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(item)
    db.commit()
    return {"mensaje": "Eliminado"}


# ---------------------------------------------------------------------------
# ÓRDENES DE COMPRA
# ---------------------------------------------------------------------------

@router.get("/ordenes/")
def listar_ordenes(
    estado:       Optional[str] = None,
    proveedor_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(OrdenCompra)
    if estado:
        q = q.filter(OrdenCompra.estado == estado)
    if proveedor_id:
        q = q.filter(OrdenCompra.proveedor_id == proveedor_id)
    ordenes = q.order_by(OrdenCompra.id.desc()).all()
    return [_serializar_orden(o, db) for o in ordenes]


@router.get("/ordenes/{orden_id}")
def obtener_orden(orden_id: int, db: Session = Depends(get_db)):
    o = db.query(OrdenCompra).filter(OrdenCompra.id == orden_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    return _serializar_orden(o, db)


@router.post("/ordenes/")
def crear_orden(datos: dict, db: Session = Depends(get_db),
                x_usuario_rol: Optional[str] = Header(None)):
    if not datos.get("proveedor_id"):
        raise HTTPException(status_code=400, detail="proveedor_id es obligatorio")
    if not datos.get("detalles"):
        raise HTTPException(status_code=400, detail="La orden debe tener al menos un producto")

    numero = _next_numero(db)
    orden  = OrdenCompra(
        numero       = numero,
        proveedor_id = datos["proveedor_id"],
        creado_por   = datos.get("creado_por", ""),
        moneda       = datos.get("moneda", "USD"),
        descuento    = float(datos.get("descuento", 0) or 0),
        observacion  = datos.get("observacion"),
        fecha_esperada = datetime.fromisoformat(datos["fecha_esperada"]) if datos.get("fecha_esperada") else None,
        estado       = "borrador",
    )
    db.add(orden)
    db.flush()

    for d in datos["detalles"]:
        cantidad = float(d.get("cantidad_pedida", 1))
        precio   = float(d.get("precio_unitario_usd", 0))
        vid      = d.get("variante_id")
        det = DetalleOrdenCompra(
            orden_id           = orden.id,
            producto_id        = d.get("producto_id"),
            variante_id        = int(vid) if vid else None,
            nombre_producto    = d.get("nombre_producto", ""),
            codigo_proveedor   = d.get("codigo_proveedor"),
            cantidad_pedida    = cantidad,
            precio_unitario_usd= precio,
            subtotal           = round(cantidad * precio, 2),
            es_producto_nuevo  = bool(d.get("es_producto_nuevo", False)),
        )
        db.add(det)

    db.flush()
    _recalcular_totales(orden, db)
    db.commit()
    db.refresh(orden)
    return _serializar_orden(orden, db)


@router.put("/ordenes/{orden_id}")
def actualizar_orden(orden_id: int, datos: dict, db: Session = Depends(get_db)):
    o = db.query(OrdenCompra).filter(OrdenCompra.id == orden_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if o.estado not in ("borrador",):
        raise HTTPException(status_code=400, detail=f"No se puede editar una orden en estado '{o.estado}'")

    for k in ("proveedor_id", "observacion", "moneda", "descuento"):
        if k in datos:
            setattr(o, k, datos[k])
    if "fecha_esperada" in datos and datos["fecha_esperada"]:
        o.fecha_esperada = datetime.fromisoformat(datos["fecha_esperada"])

    if "detalles" in datos:
        db.query(DetalleOrdenCompra).filter(DetalleOrdenCompra.orden_id == o.id).delete()
        for d in datos["detalles"]:
            cantidad = float(d.get("cantidad_pedida", 1))
            precio   = float(d.get("precio_unitario_usd", 0))
            det = DetalleOrdenCompra(
                orden_id           = o.id,
                producto_id        = d.get("producto_id"),
                nombre_producto    = d.get("nombre_producto", ""),
                codigo_proveedor   = d.get("codigo_proveedor"),
                cantidad_pedida    = cantidad,
                precio_unitario_usd= precio,
                subtotal           = round(cantidad * precio, 2),
                es_producto_nuevo  = bool(d.get("es_producto_nuevo", False)),
            )
            db.add(det)

    db.flush()
    _recalcular_totales(o, db)
    db.commit()
    return _serializar_orden(o, db)


@router.post("/ordenes/{orden_id}/aprobar")
def aprobar_orden(orden_id: int, db: Session = Depends(get_db),
                   datos: dict = {}, _: None = Depends(require_admin)):
    o = db.query(OrdenCompra).filter(OrdenCompra.id == orden_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if o.estado != "borrador":
        raise HTTPException(status_code=400, detail=f"Solo se pueden aprobar órdenes en borrador (estado actual: {o.estado})")
    o.estado           = "aprobada"
    o.fecha_aprobacion = datetime.now()
    o.aprobado_por     = datos.get("aprobado_por", "admin")
    db.commit()
    return _serializar_orden(o, db)


@router.post("/ordenes/{orden_id}/anular")
def anular_orden(orden_id: int, datos: dict = {}, db: Session = Depends(get_db),
                  x_usuario_rol: Optional[str] = Header(None)):
    o = db.query(OrdenCompra).filter(OrdenCompra.id == orden_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if o.estado == "cerrada":
        raise HTTPException(status_code=400, detail="Una orden cerrada no puede anularse")
    if o.estado not in ("borrador", "aprobada"):
        raise HTTPException(status_code=400, detail=f"No se puede anular una orden en estado '{o.estado}'")
    if x_usuario_rol != "admin" and o.estado == "aprobada":
        raise HTTPException(status_code=403, detail="Solo admin puede anular órdenes aprobadas")
    o.estado = "anulada"
    db.commit()
    return _serializar_orden(o, db)


# ---------------------------------------------------------------------------
# RECEPCIONES
# ---------------------------------------------------------------------------

@router.get("/ordenes/{orden_id}/recepciones/")
def listar_recepciones(orden_id: int, db: Session = Depends(get_db)):
    recs = db.query(RecepcionCompra).filter(RecepcionCompra.orden_id == orden_id).all()
    resultado = []
    for r in recs:
        detalles = db.query(DetalleRecepcion).filter(DetalleRecepcion.recepcion_id == r.id).all()
        resultado.append({
            "id":              r.id,
            "orden_id":        r.orden_id,
            "fecha_recepcion": r.fecha_recepcion.isoformat() if r.fecha_recepcion else None,
            "recibido_por":    r.recibido_por,
            "observacion":     r.observacion,
            "total_recibido":  round(float(r.total_recibido or 0), 2),
            "detalles": [
                {
                    "detalle_orden_id":        d.detalle_orden_id,
                    "producto_id":             d.producto_id,
                    "cantidad_recibida":       d.cantidad_recibida,
                    "precio_unitario_real_usd":d.precio_unitario_real_usd,
                    "subtotal":                round(float(d.subtotal or 0), 2),
                    "actualizo_costo":         d.actualizo_costo,
                    "costo_anterior":          d.costo_anterior,
                }
                for d in detalles
            ],
        })
    return resultado


@router.post("/ordenes/{orden_id}/recepciones/")
def registrar_recepcion(orden_id: int, datos: dict, db: Session = Depends(get_db)):
    orden = db.query(OrdenCompra).filter(OrdenCompra.id == orden_id).first()
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    if orden.estado not in ("aprobada", "recibida_parcial"):
        raise HTTPException(status_code=400, detail=f"No se puede recibir una orden en estado '{orden.estado}'")

    items_in = datos.get("items", [])
    if not items_in:
        raise HTTPException(status_code=400, detail="Debes indicar al menos un ítem recibido")

    # Verificar que no haya productos nuevos sin vincular
    nuevos_sin_registrar = []
    for item in items_in:
        det_ord = db.query(DetalleOrdenCompra).filter(
            DetalleOrdenCompra.id == item.get("detalle_orden_id")
        ).first()
        if det_ord and det_ord.es_producto_nuevo and not item.get("producto_id") and not det_ord.producto_id:
            nuevos_sin_registrar.append(det_ord.nombre_producto)

    if nuevos_sin_registrar:
        raise HTTPException(
            status_code=400,
            detail=f"Productos nuevos sin registrar en inventario: {', '.join(nuevos_sin_registrar)}. Regístralos primero.",
        )

    recepcion = RecepcionCompra(
        orden_id      = orden_id,
        recibido_por  = datos.get("recibido_por", ""),
        observacion   = datos.get("observacion"),
        fecha_recepcion = datetime.now(),
    )
    db.add(recepcion)
    db.flush()

    total = 0.0
    detalles_orden = {d.id: d for d in db.query(DetalleOrdenCompra).filter(DetalleOrdenCompra.orden_id == orden_id).all()}
    cantidades_pedidas = {d.id: float(d.cantidad_pedida) for d in detalles_orden.values()}

    for item in items_in:
        det_ord_id = item.get("detalle_orden_id")
        prod_id    = item.get("producto_id")
        cantidad   = float(item.get("cantidad_recibida", 0))
        precio_real= float(item.get("precio_unitario_real_usd", 0))
        subtotal   = round(cantidad * precio_real, 2)
        total     += subtotal

        # Si el producto_id llega en el item, actualizarlo en el detalle (vinculación automática)
        det_ord = detalles_orden.get(det_ord_id)
        if det_ord and prod_id and not det_ord.producto_id:
            det_ord.producto_id       = prod_id
            det_ord.es_producto_nuevo = False

        variante_id = item.get("variante_id")
        if variante_id is not None:
            variante_id = int(variante_id)

        producto = db.query(Producto).filter(Producto.id == prod_id).first() if prod_id else None
        variante = None
        if variante_id:
            variante = db.query(VarianteProducto).filter(
                VarianteProducto.id == variante_id,
                VarianteProducto.producto_id == prod_id,
            ).first()

        actualizo_costo = False
        costo_anterior  = None

        if producto:
            # Stock: si tiene variante → actualizar variante; si no → actualizar producto
            if variante:
                variante.stock = float(variante.stock or 0) + cantidad
            else:
                tiene_variantes = db.query(VarianteProducto).filter(
                    VarianteProducto.producto_id == prod_id
                ).first() is not None
                if not tiene_variantes:
                    producto.stock += int(cantidad)
                # producto con variantes sin variante_id especificada: no tocar nada

            # Actualizar costo en el producto padre (precio de compra siempre en el padre)
            precio_ord = float(detalles_orden[det_ord_id].precio_unitario_usd) if det_ord_id in detalles_orden else 0
            if abs(precio_real - precio_ord) > 0.01 and precio_real > 0:
                costo_anterior     = float(producto.costo_usd or 0)
                producto.costo_usd = precio_real
                actualizo_costo    = True

        dr = DetalleRecepcion(
            recepcion_id             = recepcion.id,
            detalle_orden_id         = det_ord_id,
            producto_id              = prod_id,
            variante_id              = variante_id,
            cantidad_recibida        = cantidad,
            precio_unitario_real_usd = precio_real,
            subtotal                 = subtotal,
            actualizo_costo          = actualizo_costo,
            costo_anterior           = costo_anterior,
        )
        db.add(dr)

    recepcion.total_recibido = round(total, 2)

    # ── Crédito: calcular fecha de vencimiento de pago ────────────────────
    proveedor = db.query(Proveedor).filter(Proveedor.id == orden.proveedor_id).first()
    dias_credito = int(proveedor.dias_credito or 0) if proveedor else 0
    if dias_credito > 0:
        recepcion.fecha_vencimiento_pago = date.today() + timedelta(days=dias_credito)
        recepcion.monto_factura          = recepcion.total_recibido
        recepcion.estado_pago            = "pendiente"
    recepcion.numero_factura = datos.get("numero_factura")

    # Determinar si la recepción fue total o parcial
    cantidades_recibidas_previas = {}
    recepciones_anteriores = db.query(RecepcionCompra).filter(
        RecepcionCompra.orden_id == orden_id,
        RecepcionCompra.id != recepcion.id,
    ).all()
    for r in recepciones_anteriores:
        for dr in db.query(DetalleRecepcion).filter(DetalleRecepcion.recepcion_id == r.id).all():
            cantidades_recibidas_previas[dr.detalle_orden_id] = (
                cantidades_recibidas_previas.get(dr.detalle_orden_id, 0) + float(dr.cantidad_recibida)
            )

    cantidades_esta = {item["detalle_orden_id"]: float(item.get("cantidad_recibida", 0)) for item in items_in}
    todo_recibido = all(
        cantidades_recibidas_previas.get(did, 0) + cantidades_esta.get(did, 0) >= cantidades_pedidas.get(did, 0)
        for did in cantidades_pedidas
    )
    orden.estado = "cerrada" if todo_recibido else "recibida_parcial"
    db.commit()

    return {
        "recepcion_id":   recepcion.id,
        "orden_estado":   orden.estado,
        "total_recibido": recepcion.total_recibido,
    }


@router.get("/recepciones/{recepcion_id}")
def obtener_recepcion(recepcion_id: int, db: Session = Depends(get_db)):
    r = db.query(RecepcionCompra).filter(RecepcionCompra.id == recepcion_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    detalles = db.query(DetalleRecepcion).filter(DetalleRecepcion.recepcion_id == r.id).all()
    return {
        "id":              r.id,
        "orden_id":        r.orden_id,
        "fecha_recepcion": r.fecha_recepcion.isoformat() if r.fecha_recepcion else None,
        "recibido_por":    r.recibido_por,
        "total_recibido":  r.total_recibido,
        "detalles": [
            {
                "producto_id":      d.producto_id,
                "variante_id":      d.variante_id,
                "cantidad_recibida":d.cantidad_recibida,
                "precio_real":      d.precio_unitario_real_usd,
                "actualizo_costo":  d.actualizo_costo,
            }
            for d in detalles
        ],
    }


# ---------------------------------------------------------------------------
# FACTURAS DE PROVEEDORES (crédito)
# ---------------------------------------------------------------------------

@router.get("/facturas/pendientes")
def facturas_pendientes(db: Session = Depends(get_db)):
    recs = db.query(RecepcionCompra).filter(
        RecepcionCompra.fecha_vencimiento_pago.isnot(None),
        or_(
            RecepcionCompra.estado_pago == "pendiente",
            RecepcionCompra.estado_pago == "vencido",
        )
    ).order_by(RecepcionCompra.fecha_vencimiento_pago).all()
    return [_serializar_factura(r, db) for r in recs]


@router.get("/facturas/")
def listar_facturas(db: Session = Depends(get_db)):
    recs = db.query(RecepcionCompra).filter(
        RecepcionCompra.fecha_vencimiento_pago.isnot(None)
    ).order_by(RecepcionCompra.fecha_vencimiento_pago.desc()).all()
    return [_serializar_factura(r, db) for r in recs]


@router.put("/facturas/{recepcion_id}/pagar")
def marcar_factura_pagada(
    recepcion_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    r = db.query(RecepcionCompra).filter(RecepcionCompra.id == recepcion_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    r.estado_pago   = "pagado"
    r.fecha_pago_real = datetime.now()
    db.commit()
    return {"mensaje": "Factura marcada como pagada", "id": r.id}


@router.post("/facturas/actualizar-estados")
def actualizar_estados_facturas(db: Session = Depends(get_db)):
    """Marca como 'vencido' todas las facturas pendientes cuya fecha ya pasó."""
    hoy = date.today()
    pendientes = db.query(RecepcionCompra).filter(
        RecepcionCompra.estado_pago == "pendiente",
        RecepcionCompra.fecha_vencimiento_pago.isnot(None),
        RecepcionCompra.fecha_vencimiento_pago < hoy,
    ).all()
    count = 0
    for r in pendientes:
        r.estado_pago = "vencido"
        count += 1
    db.commit()
    return {"actualizadas": count}


# ---------------------------------------------------------------------------
# REPORTES de compras
# ---------------------------------------------------------------------------

@router.get("/reportes/por-proveedor")
def reporte_por_proveedor(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    proveedores = db.query(Proveedor).filter(Proveedor.activo == True).all()
    resultado = []
    for p in proveedores:
        ordenes = db.query(OrdenCompra).filter(OrdenCompra.proveedor_id == p.id).all()
        total = sum(float(o.total or 0) for o in ordenes if o.estado == "cerrada")
        resultado.append({
            "proveedor_id":   p.id,
            "proveedor":      p.nombre,
            "total_ordenes":  len(ordenes),
            "total_comprado": round(total, 2),
        })
    return resultado


@router.get("/reportes/ordenes-pendientes")
def ordenes_pendientes(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    ordenes = db.query(OrdenCompra).filter(
        OrdenCompra.estado.in_(["aprobada", "recibida_parcial"])
    ).order_by(OrdenCompra.fecha_esperada).all()
    return [_serializar_orden(o, db) for o in ordenes]


@router.get("/reportes/variaciones-precio")
def variaciones_precio(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    cambios = db.query(DetalleRecepcion).filter(DetalleRecepcion.actualizo_costo == True).all()
    resultado = []
    for d in cambios:
        prod = db.query(Producto).filter(Producto.id == d.producto_id).first()
        resultado.append({
            "producto_id":      d.producto_id,
            "producto":         prod.nombre if prod else f"ID {d.producto_id}",
            "costo_anterior":   d.costo_anterior,
            "precio_real":      d.precio_unitario_real_usd,
            "variacion_pct":    round(
                ((d.precio_unitario_real_usd - (d.costo_anterior or 0)) / (d.costo_anterior or 1)) * 100, 1
            ),
        })
    return resultado
