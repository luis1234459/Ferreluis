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
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import (
    Proveedor, CatalogoProveedor, OrdenCompra, DetalleOrdenCompra,
    RecepcionCompra, DetalleRecepcion, Producto, VarianteProducto,
    Venta, DetalleVenta, ProductoProveedor, MovimientoBancario,
    DevolucionProveedor, AliasProveedor,
)
from rutas.usuarios import require_admin
from rutas.auth import ajustar_existencia_sede
from rutas.productos import listar_productos as _listar_productos_completo
from pagos_proveedor import recalcular_estado_pago
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
        "proveedor_telefono": prov.telefono if prov else None,
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

import re

_RE_CODIGO_PROVEEDOR = re.compile(r"^[A-Z]{3}$")


def _validar_codigo_proveedor(db: Session, codigo: str, excluir_id: int | None = None) -> None:
    if not _RE_CODIGO_PROVEEDOR.match(codigo or ""):
        raise HTTPException(
            status_code=400,
            detail=f"Código inválido: '{codigo}'. Debe ser exactamente 3 letras mayúsculas (ej: CIN, DEC, LEO)",
        )
    q = db.query(Proveedor).filter(Proveedor.codigo == codigo)
    if excluir_id is not None:
        q = q.filter(Proveedor.id != excluir_id)
    if q.first():
        raise HTTPException(status_code=400, detail=f"El código '{codigo}' ya está en uso por otro proveedor")


@router.get("/proveedores/")
def listar_proveedores(incluir_inactivos: bool = False, db: Session = Depends(get_db)):
    q = db.query(Proveedor)
    if not incluir_inactivos:
        q = q.filter(Proveedor.activo == True)
    return q.order_by(Proveedor.nombre).all()


@router.post("/proveedores/")
def crear_proveedor(datos: dict, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    if not datos.get("nombre"):
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    codigo = (datos.get("codigo") or "").strip().upper() or None
    if codigo:
        _validar_codigo_proveedor(db, codigo)
    p = Proveedor(
        nombre         = datos["nombre"],
        codigo         = codigo,
        rif            = datos.get("rif"),
        telefono       = datos.get("telefono"),
        email          = datos.get("email"),
        direccion      = datos.get("direccion"),
        contacto       = datos.get("contacto"),
        dias_credito   = int(datos.get("dias_credito", 0) or 0),
        lead_time_dias_default = int(datos.get("lead_time_dias_default", 0) or 0),
        notas          = datos.get("notas"),
        activo         = True,
        fecha_registro = datetime.now(),
    )
    db.add(p)
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
    if "codigo" in datos:
        codigo = (datos.get("codigo") or "").strip().upper() or None
        if codigo:
            _validar_codigo_proveedor(db, codigo, excluir_id=proveedor_id)
        p.codigo = codigo
    if "dias_credito" in datos:
        p.dias_credito = int(datos["dias_credito"] or 0)
    if "lead_time_dias_default" in datos:
        p.lead_time_dias_default = int(datos["lead_time_dias_default"] or 0)
    if "notas" in datos:
        p.notas = datos["notas"]
    if "pricing_policy" in datos:
        policy = datos["pricing_policy"]
        if policy in ("MARKET_FACTOR", "BCV_DIRECT"):
            p.pricing_policy = policy
    if "ajuste_divisa_pct" in datos:
        p.ajuste_divisa_pct = float(datos["ajuste_divisa_pct"] or 0) if datos["ajuste_divisa_pct"] is not None else 0.0
    if "ajuste_tipo" in datos:
        p.ajuste_tipo = datos["ajuste_tipo"] or "manual"
    if "descuento_pct" in datos:
        p.descuento_pct = float(datos["descuento_pct"] or 0)
    if "descuento_max_pct" in datos:
        p.descuento_max_pct = float(datos["descuento_max_pct"]) if datos["descuento_max_pct"] is not None else None
    if "activo" in datos:
        p.activo = bool(datos["activo"])
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


# Tablas con proveedor_id que no son FK declaradas en el ORM (sin ondelete),
# pero que igual hay que repuntar al fusionar dos proveedores en uno.
_TABLAS_CON_PROVEEDOR_ID_PLANO = [Producto, CatalogoProveedor, OrdenCompra, MovimientoBancario, DevolucionProveedor, AliasProveedor]


@router.post("/proveedores/fusionar")
def fusionar_proveedores(datos: dict, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    """
    Fusiona hasta 3 proveedores duplicados en un proveedor canónico: repunta
    todas las referencias (productos, catálogo, órdenes de compra, movimientos
    bancarios, devoluciones, alias) al canónico y desactiva los duplicados.
    No los borra — se preserva el historial, solo dejan de aparecer en listados.
    """
    canonico_id    = datos.get("canonico_id")
    duplicados_ids = datos.get("duplicados_ids") or []

    if not duplicados_ids or len(duplicados_ids) > 3:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo 3 proveedores duplicados por fusión (recibidos: {len(duplicados_ids)})",
        )
    if canonico_id in duplicados_ids:
        raise HTTPException(status_code=400, detail="El proveedor canónico no puede estar también en duplicados_ids")

    canonico = db.query(Proveedor).filter(Proveedor.id == canonico_id).first()
    if not canonico:
        raise HTTPException(status_code=404, detail="Proveedor canónico no encontrado")

    duplicados = db.query(Proveedor).filter(Proveedor.id.in_(duplicados_ids)).all()
    faltantes = set(duplicados_ids) - {p.id for p in duplicados}
    if faltantes:
        raise HTTPException(status_code=404, detail=f"Proveedor(es) duplicado(s) no encontrado(s): {sorted(faltantes)}")

    descartes = []   # filas de producto_proveedor del duplicado que no se pudieron repuntar

    try:
        for dup in duplicados:
            for Modelo in _TABLAS_CON_PROVEEDOR_ID_PLANO:
                db.query(Modelo).filter(Modelo.proveedor_id == dup.id).update(
                    {"proveedor_id": canonico.id}, synchronize_session=False
                )

            # producto_proveedor: cada producto admite máximo 3 filas y una
            # prioridad única — repuntar la fila del duplicado al canónico
            # puede chocar con una fila que el canónico (u otro proveedor)
            # ya tiene para ese mismo producto. En vez de fallar la fusión
            # entera, se descarta esa fila puntual y se reporta en el resumen.
            filas_dup = db.query(ProductoProveedor).filter(ProductoProveedor.proveedor_id == dup.id).all()
            for fila in filas_dup:
                otras_filas_mismo_producto = db.query(ProductoProveedor).filter(
                    ProductoProveedor.producto_id == fila.producto_id,
                    ProductoProveedor.id != fila.id,
                ).all()
                canonico_ya_presente = any(f.proveedor_id == canonico.id for f in otras_filas_mismo_producto)
                sin_espacio          = len(otras_filas_mismo_producto) >= 3

                if canonico_ya_presente or sin_espacio:
                    descartes.append({
                        "producto_id": fila.producto_id,
                        "proveedor_duplicado_id": dup.id,
                        "motivo": (
                            "el canónico ya es proveedor de este producto" if canonico_ya_presente
                            else "el producto ya tiene el máximo de 3 proveedores"
                        ),
                    })
                    db.delete(fila)
                else:
                    fila.proveedor_id = canonico.id

            dup.activo = False

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al fusionar proveedores: {e}")

    db.refresh(canonico)
    return {
        "canonico": canonico,
        "fusionados": [p.id for p in duplicados],
        "filas_descartadas_por_conflicto": descartes,
    }


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


@router.get("/ordenes/{orden_id}/pdf")
def generar_pdf_orden(orden_id: int, db: Session = Depends(get_db)):
    """Genera un PDF profesional de la Orden de Compra para envío al proveedor."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    import io

    o = db.query(OrdenCompra).filter(OrdenCompra.id == orden_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    prov = db.query(Proveedor).filter(Proveedor.id == o.proveedor_id).first()
    detalles = db.query(DetalleOrdenCompra).filter(
        DetalleOrdenCompra.orden_id == orden_id
    ).all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Empresa', fontName='Helvetica-Bold',
                              fontSize=14, spaceAfter=2))
    styles.add(ParagraphStyle(name='SubInfo', fontName='Helvetica',
                              fontSize=9, textColor=colors.grey))
    story = []

    # ── Encabezado empresa ────────────────────────────────────────────────
    story.append(Paragraph("COMERCIAL FERRE-UTIL C.A.", styles['Empresa']))
    story.append(Paragraph("RIF: J-30299737-5 · Ciudad Ojeda, Zulia, Venezuela", styles['SubInfo']))
    story.append(Spacer(1, 6*mm))

    # ── Título OC ──────────────────────────────────────────────────────────
    fecha = o.fecha_creacion.strftime('%d/%m/%Y') if o.fecha_creacion else ''
    estado_txt = (o.estado or '').upper()
    story.append(Paragraph(
        f"<b>ORDEN DE COMPRA {o.numero or ''}</b> &nbsp; — &nbsp; {fecha} "
        f"&nbsp; <font color='grey'>[{estado_txt}]</font>",
        styles['Heading2']))
    story.append(Spacer(1, 4*mm))

    # ── Datos del proveedor ────────────────────────────────────────────────
    if prov:
        info_prov = [
            ["Proveedor:", prov.nombre or '', "RIF:", prov.rif or '—'],
            ["Teléfono:", prov.telefono or '—', "Contacto:", prov.contacto or '—'],
            ["Email:", prov.email or '—', "Dirección:", (prov.direccion or '—')[:50]],
        ]
        t = Table(info_prov, colWidths=[60, 170, 60, 170])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
    story.append(Spacer(1, 6*mm))

    # ── Tabla de productos ─────────────────────────────────────────────────
    header = ['#', 'Producto', 'Cant.', 'Precio USD', 'Subtotal USD']
    data = [header]
    for i, d in enumerate(detalles, 1):
        nombre = d.nombre_producto or ''
        if d.es_producto_nuevo:
            nombre += ' [NUEVO]'
        data.append([
            str(i),
            nombre,
            str(int(d.cantidad_pedida) if d.cantidad_pedida == int(d.cantidad_pedida) else d.cantidad_pedida),
            f"${d.precio_unitario_usd:,.2f}",
            f"${d.subtotal:,.2f}",
        ])
    # Fila total
    data.append(['', '', '', 'TOTAL:', f"${o.total:,.2f}"])

    col_widths = [25, 230, 45, 75, 85]
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, 0), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A1A1A')),
        ('TEXTCOLOR',  (0, 0), (-1, 0), colors.HexColor('#FFCC00')),
        ('FONTNAME',   (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE',   (0, 1), (-1, -2), 9),
        ('ALIGN',      (2, 0), (-1, -1), 'RIGHT'),
        ('GRID',       (0, 0), (-1, -2), 0.5, colors.lightgrey),
        ('LINEABOVE',  (0, -1), (-1, -1), 1, colors.black),
        ('FONTNAME',   (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, -1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    # ── Observaciones ──────────────────────────────────────────────────────
    if o.observacion:
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph(f"<b>Observaciones:</b> {o.observacion}", styles['Normal']))

    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("Generado por Ferreutil — Sistema Administrativo", styles['SubInfo']))

    doc.build(story)
    buf.seek(0)
    filename = f"OC_{o.numero or orden_id}.pdf"
    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


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
            "numero_factura":  r.numero_factura or "",
            "total_recibido":  round(float(r.total_recibido or 0), 2),
            "devuelta":        bool(r.devuelta),
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
                    ajustar_existencia_sede(
                        db, prod_id, orden.sede_id_destino,
                        tipo="agregar", valor=int(cantidad),
                        tiene_variante_activa=False,
                    )
                # producto con variantes sin variante_id especificada: no tocar nada

            # Actualizar costo en el producto padre (precio de compra siempre en el padre)
            precio_ord = float(detalles_orden[det_ord_id].precio_unitario_usd) if det_ord_id in detalles_orden else 0
            if abs(precio_real - precio_ord) > 0.01 and precio_real > 0:
                costo_anterior     = float(producto.costo_usd or 0)
                producto.costo_usd = precio_real
                actualizo_costo    = True

            # Ficha de reposición: recibir mercancía de este proveedor demuestra
            # que sí tiene stock — se baja la bandera sola, sin que el
            # comprador tenga que acordarse.
            pp = db.query(ProductoProveedor).filter(
                ProductoProveedor.producto_id == prod_id,
                ProductoProveedor.proveedor_id == orden.proveedor_id,
            ).first()
            if pp and pp.sin_stock_declarado:
                pp.sin_stock_declarado = False
                pp.sin_stock_fecha     = None

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
        recalcular_estado_pago(db, recepcion)
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
# DEVOLUCIÓN TOTAL DE RECEPCIÓN (solo admin)
# ---------------------------------------------------------------------------

@router.post("/recepciones/{recepcion_id}/devolucion-total")
def devolucion_total_recepcion(recepcion_id: int, datos: dict, db: Session = Depends(get_db)):
    usuario_rol = datos.get("usuario_rol", "")
    if usuario_rol != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden ejecutar una devolución total")

    recepcion = db.query(RecepcionCompra).filter(RecepcionCompra.id == recepcion_id).first()
    if not recepcion:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    if recepcion.devuelta:
        raise HTTPException(status_code=400, detail="Esta recepción ya fue devuelta")

    orden = db.query(OrdenCompra).filter(OrdenCompra.id == recepcion.orden_id).first()

    detalles = db.query(DetalleRecepcion).filter(DetalleRecepcion.recepcion_id == recepcion_id).all()
    items_revertidos = 0

    for d in detalles:
        if not d.producto_id:
            continue
        prod = db.query(Producto).filter(Producto.id == d.producto_id).first()
        if not prod:
            continue

        cantidad = float(d.cantidad_recibida or 0)
        if d.variante_id:
            variante = db.query(VarianteProducto).filter(VarianteProducto.id == d.variante_id).first()
            if variante:
                variante.stock = max(0.0, float(variante.stock or 0) - cantidad)
        else:
            tiene_variantes = db.query(VarianteProducto).filter(
                VarianteProducto.producto_id == d.producto_id
            ).first() is not None
            if not tiene_variantes:
                prod.stock = max(0, int(prod.stock or 0) - int(cantidad))
                if orden:
                    ajustar_existencia_sede(
                        db, prod.id, orden.sede_id_destino,
                        tipo="restar", valor=int(cantidad),
                        tiene_variante_activa=False,
                    )

        if d.actualizo_costo and d.costo_anterior is not None:
            prod.costo_usd = d.costo_anterior

        items_revertidos += 1

    recepcion.devuelta = True
    recalcular_estado_pago(db, recepcion)

    # Recalcular estado de la orden
    if orden:
        todas = db.query(RecepcionCompra).filter(RecepcionCompra.orden_id == orden.id).all()
        activas = [r for r in todas if not r.devuelta and r.id != recepcion_id]
        if not activas:
            orden.estado = "aprobada"
        else:
            orden.estado = "recibida_parcial"

    db.commit()
    return {
        "mensaje":          f"Recepción #{recepcion_id} devuelta. {items_revertidos} ítem(s) revertido(s).",
        "items_revertidos": items_revertidos,
        "orden_estado":     orden.estado if orden else None,
    }


# ---------------------------------------------------------------------------
# FACTURAS DE PROVEEDORES (crédito)
# ---------------------------------------------------------------------------

@router.get("/facturas/pendientes")
def facturas_pendientes(db: Session = Depends(get_db)):
    recs = db.query(RecepcionCompra).filter(
        RecepcionCompra.fecha_vencimiento_pago.isnot(None),
        RecepcionCompra.estado_pago.in_(["pendiente", "vencido", "pago_parcial"]),
    ).order_by(RecepcionCompra.fecha_vencimiento_pago).all()
    return [_serializar_factura(r, db) for r in recs]


@router.get("/facturas/")
def listar_facturas(db: Session = Depends(get_db)):
    recs = db.query(RecepcionCompra).filter(
        RecepcionCompra.fecha_vencimiento_pago.isnot(None)
    ).order_by(RecepcionCompra.fecha_vencimiento_pago.desc()).all()
    return [_serializar_factura(r, db) for r in recs]


@router.post("/facturas/actualizar-estados")
def actualizar_estados_facturas(db: Session = Depends(get_db)):
    """Recalcula estado_pago de todas las facturas de crédito no pagadas (pendiente/vencido/parcial)."""
    pendientes = db.query(RecepcionCompra).filter(
        RecepcionCompra.estado_pago.in_(["pendiente", "vencido", "pago_parcial"]),
        RecepcionCompra.fecha_vencimiento_pago.isnot(None),
    ).all()
    count = 0
    for r in pendientes:
        antes = r.estado_pago
        recalcular_estado_pago(db, r)
        if r.estado_pago != antes:
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


# ---------------------------------------------------------------------------
# CATÁLOGO ENRIQUECIDO PARA "Nueva orden a proveedor"
# Reusa el listado completo de /productos/ (mismos campos de siempre) y le
# agrega, por producto: costo/fecha/cantidad de la última recepción real
# (no devuelta) y unidades vendidas desde esa fecha. Endpoint separado para
# no penalizar con estas queries extra al resto de las pantallas que usan
# /productos/ (Ventas, Inventario, Reportes, etc.).
# ---------------------------------------------------------------------------

@router.get("/catalogo-costos")
def catalogo_costos(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    resultado = _listar_productos_completo(
        incluir_inactivos=False, skip=0, limit=1_000_000, db=db
    )
    productos = resultado["productos"]

    # ── Última recepción no devuelta por producto ────────────────────────
    filas_recepcion = (
        db.query(DetalleRecepcion.producto_id, DetalleRecepcion.cantidad_recibida,
                  DetalleRecepcion.precio_unitario_real_usd, RecepcionCompra.fecha_recepcion)
        .join(RecepcionCompra, RecepcionCompra.id == DetalleRecepcion.recepcion_id)
        .filter(RecepcionCompra.devuelta == False)
        .all()
    )
    ultima_recepcion: dict = {}
    for producto_id, cantidad, precio, fecha in filas_recepcion:
        if producto_id is None or fecha is None:
            continue
        actual = ultima_recepcion.get(producto_id)
        if actual is None or fecha > actual["fecha"]:
            ultima_recepcion[producto_id] = {
                "costo":    float(precio or 0),
                "fecha":    fecha,
                "cantidad": cantidad,
            }

    # ── Ventas no anuladas por producto (se filtran por fecha en Python,
    #    ya que la fecha de corte varía según el producto) ────────────────
    filas_venta = (
        db.query(DetalleVenta.producto_id, DetalleVenta.cantidad, Venta.fecha)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .filter(Venta.estado != 'anulada')
        .all()
    )
    ventas_por_producto: dict = {}
    for producto_id, cantidad, fecha in filas_venta:
        ventas_por_producto.setdefault(producto_id, []).append((fecha, float(cantidad or 0)))

    for p in productos:
        rec = ultima_recepcion.get(p["id"])
        if rec:
            p["ultimo_costo_usd"]      = round(rec["costo"], 4)
            p["ultimo_costo_fecha"]    = rec["fecha"].date().isoformat()
            p["ultimo_costo_cantidad"] = int(rec["cantidad"] or 0)
            vendidas = sum(
                cant for fecha, cant in ventas_por_producto.get(p["id"], [])
                if fecha > rec["fecha"]
            )
            p["vendidas_desde_ultimo_costo"] = int(vendidas)
        else:
            p["ultimo_costo_usd"]            = None
            p["ultimo_costo_fecha"]          = None
            p["ultimo_costo_cantidad"]       = None
            p["vendidas_desde_ultimo_costo"] = 0

    return resultado
