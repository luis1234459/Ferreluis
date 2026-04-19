from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import anthropic
import base64
import json
import io
import os
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from models import (
    OrdenCompra, DetalleOrdenCompra,
    RecepcionCompra, DetalleRecepcion,
    Producto, Proveedor, CatalogoProveedor, AliasProveedor,
    MovimientoBancario, TasaCambio,
)

router = APIRouter(prefix="/facturas", tags=["facturas"])

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

TIPOS_IMAGEN   = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
MEDIA_TYPE_MAP = {
    "image/jpg":  "image/jpeg",
    "image/jpeg": "image/jpeg",
    "image/png":  "image/png",
    "image/webp": "image/webp",
    "image/gif":  "image/gif",
}


def _pdf_a_imagen_base64(contenido: bytes) -> tuple[str, str]:
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="pdf2image no está instalado. Ejecuta: pip install pdf2image",
        )
    try:
        paginas = convert_from_bytes(contenido, first_page=1, last_page=1, dpi=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo convertir el PDF: {e}")
    buffer = io.BytesIO()
    paginas[0].save(buffer, format="JPEG", quality=90)
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8"), "image/jpeg"


def _next_oc_numero(db: Session) -> str:
    ultimo = db.query(OrdenCompra).order_by(OrdenCompra.id.desc()).first()
    n = (ultimo.id + 1) if ultimo else 1
    return f"OC-{n:04d}"


def _normalizar(texto: str) -> str:
    import re
    texto = texto.upper().strip()
    texto = re.sub(r'\s+', ' ', texto)
    for palabra in ['C.A', 'C.A.', 'S.A', 'S.A.', 'CA', 'SA', 'COMPANIA', 'EMPRESA', 'GRUPO', 'COMERCIAL']:
        texto = texto.replace(palabra, '')
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto


# ---------------------------------------------------------------------------
# POST /facturas/escanear
# ---------------------------------------------------------------------------

@router.post("/escanear")
async def escanear_factura(archivo: UploadFile = File(...)):
    client       = anthropic.Anthropic(api_key=API_KEY)
    contenido    = await archivo.read()
    content_type = (archivo.content_type or "").lower().split(";")[0].strip()

    if content_type == "application/pdf":
        imagen_b64, media_type = _pdf_a_imagen_base64(contenido)
    elif content_type in TIPOS_IMAGEN:
        imagen_b64 = base64.standard_b64encode(contenido).decode("utf-8")
        media_type = MEDIA_TYPE_MAP.get(content_type, "image/jpeg")
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo no soportado: '{content_type}'. Usa JPEG, PNG, WebP, GIF o PDF.",
        )

    mensaje = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": imagen_b64},
                },
                {
                    "type": "text",
                    "text": (
                        "Analiza esta factura de proveedor y extrae todos los datos.\n"
                        "Devuelve SOLO un JSON con este formato exacto, sin texto adicional:\n"
                        "{\n"
                        '  "proveedor": "nombre del proveedor o vacío",\n'
                        '  "numero_factura": "número de factura o vacío",\n'
                        '  "fecha": "fecha en formato YYYY-MM-DD o vacío",\n'
                        '  "subtotal": numero o null,\n'
                        '  "descuento_detectado": numero o null,\n'
                        '  "total": numero o null,\n'
                        '  "productos": [\n'
                        "    {\n"
                        '      "nombre": "nombre del producto",\n'
                        '      "codigo_proveedor": "código del proveedor si aparece o vacío",\n'
                        '      "cantidad": numero,\n'
                        '      "precio_unitario": numero,\n'
                        '      "subtotal_linea": numero o null\n'
                        "    }\n"
                        "  ]\n"
                        "}\n"
                        "IMPORTANTE: Si la factura incluye IVA u otros impuestos, inclúyelos en el total final.\n"
                        "No separes IVA — trabaja siempre con valores finales netos.\n"
                        "precio_unitario debe ser el costo final unitario incluyendo cualquier impuesto proporcional."
                    ),
                },
            ],
        }],
    )

    texto = mensaje.content[0].text.strip()
    if texto.startswith("```"):
        lineas = texto.splitlines()
        texto = "\n".join(lineas[1:-1] if lineas[-1].strip() == "```" else lineas[1:])

    try:
        return json.loads(texto)
    except Exception as e:
        return {"error": str(e), "respuesta": texto}


# ---------------------------------------------------------------------------
# GET /facturas/buscar-proveedor
# ---------------------------------------------------------------------------

@router.get("/buscar-proveedor")
def buscar_proveedor(nombre: str = "", db: Session = Depends(get_db)):
    if len(nombre) < 2:
        return []

    nombre_norm = _normalizar(nombre)

    # 1. Buscar en alias_proveedores (aprendizaje previo)
    alias_matches = db.query(AliasProveedor).filter(
        AliasProveedor.alias_normalizado.ilike(f"%{nombre_norm}%")
    ).limit(5).all()

    ids_ya: set[int] = set()
    resultados = []

    for a in alias_matches:
        p = db.query(Proveedor).filter(
            Proveedor.id == a.proveedor_id,
            Proveedor.activo == True,
        ).first()
        if p and p.id not in ids_ya:
            resultados.append({
                "id": p.id,
                "nombre": p.nombre,
                "rif": p.rif or "",
                "via_alias": True,
            })
            ids_ya.add(p.id)

    # 2. Buscar por nombre directo (ilike normal)
    directos = db.query(Proveedor).filter(
        Proveedor.nombre.ilike(f"%{nombre}%"),
        Proveedor.activo == True,
    ).limit(10).all()

    for p in directos:
        if p.id not in ids_ya:
            resultados.append({
                "id": p.id,
                "nombre": p.nombre,
                "rif": p.rif or "",
                "via_alias": False,
            })
            ids_ya.add(p.id)

    return resultados[:10]


@router.post("/guardar-alias")
def guardar_alias(datos: dict, db: Session = Depends(get_db)):
    alias        = datos.get("alias", "").strip()
    proveedor_id = datos.get("proveedor_id")
    creado_por   = datos.get("usuario", "")

    if not alias or not proveedor_id:
        raise HTTPException(status_code=400, detail="alias y proveedor_id son obligatorios")

    alias_norm = _normalizar(alias)

    existente = db.query(AliasProveedor).filter(
        AliasProveedor.alias_normalizado == alias_norm,
        AliasProveedor.proveedor_id == proveedor_id,
    ).first()

    if not existente:
        db.add(AliasProveedor(
            proveedor_id      = proveedor_id,
            alias             = alias,
            alias_normalizado = alias_norm,
            creado_por        = creado_por,
        ))
        db.commit()
        return {"guardado": True}

    return {"guardado": False, "razon": "alias ya existe"}


# ---------------------------------------------------------------------------
# GET /facturas/buscar-producto
# ---------------------------------------------------------------------------

@router.get("/buscar-producto")
def buscar_producto(
    nombre: str = "",
    proveedor_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    resultados = []
    ids_ya: set[int] = set()

    # Prioridad: buscar por código en catálogo del proveedor
    if proveedor_id and nombre:
        cats = db.query(CatalogoProveedor).filter(
            CatalogoProveedor.proveedor_id == proveedor_id,
            CatalogoProveedor.codigo_proveedor.ilike(f"%{nombre}%"),
        ).limit(5).all()
        for c in cats:
            if c.producto_id:
                p = db.query(Producto).filter(Producto.id == c.producto_id).first()
                if p and p.id not in ids_ya:
                    resultados.append({
                        "id": p.id, "nombre": p.nombre,
                        "codigo": p.codigo or "", "costo_usd": p.costo_usd, "stock": p.stock,
                    })
                    ids_ya.add(p.id)

    # Buscar por nombre en inventario
    if len(nombre) >= 2:
        prods = db.query(Producto).filter(
            Producto.nombre.ilike(f"%{nombre}%")
        ).limit(10).all()
        for p in prods:
            if p.id not in ids_ya:
                resultados.append({
                    "id": p.id, "nombre": p.nombre,
                    "codigo": p.codigo or "", "costo_usd": p.costo_usd, "stock": p.stock,
                })
                ids_ya.add(p.id)

    return resultados[:10]


# ---------------------------------------------------------------------------
# GET /facturas/ordenes-pendientes
# ---------------------------------------------------------------------------

@router.get("/ordenes-pendientes")
def ordenes_pendientes(proveedor_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Devuelve OC en estado aprobada o recibida_parcial, opcionalmente filtradas por proveedor."""
    q = db.query(OrdenCompra).filter(
        OrdenCompra.estado.in_(["aprobada", "recibida_parcial"])
    )
    if proveedor_id:
        q = q.filter(OrdenCompra.proveedor_id == proveedor_id)
    ordenes = q.order_by(OrdenCompra.fecha_creacion.desc()).limit(30).all()

    resultado = []
    for o in ordenes:
        prov = db.query(Proveedor).filter(Proveedor.id == o.proveedor_id).first()
        detalles = db.query(DetalleOrdenCompra).filter(DetalleOrdenCompra.orden_id == o.id).all()
        resultado.append({
            "id":               o.id,
            "numero":           o.numero,
            "estado":           o.estado,
            "fecha_creacion":   o.fecha_creacion.isoformat() if o.fecha_creacion else None,
            "total":            round(o.total, 2),
            "proveedor_id":     o.proveedor_id,
            "proveedor_nombre": prov.nombre if prov else "",
            "detalles": [
                {
                    "id":                  d.id,
                    "producto_id":         d.producto_id,
                    "nombre_producto":     d.nombre_producto,
                    "codigo_proveedor":    d.codigo_proveedor or "",
                    "cantidad_pedida":     d.cantidad_pedida,
                    "precio_unitario_usd": d.precio_unitario_usd,
                }
                for d in detalles
            ],
        })
    return resultado


# ---------------------------------------------------------------------------
# POST /facturas/confirmar-compra
# ---------------------------------------------------------------------------

@router.post("/confirmar-compra")
def confirmar_compra(datos: dict, db: Session = Depends(get_db)):
    proveedor_id        = datos.get("proveedor_id")
    numero_factura      = datos.get("numero_factura", "")
    fecha_str           = datos.get("fecha")
    productos_data      = datos.get("productos", [])
    descuento           = float(datos.get("descuento", 0))
    total_factura       = float(datos.get("total_factura", 0))
    condicion_pago      = datos.get("condicion_pago", "credito_completo")
    monto_abonado       = float(datos.get("monto_abonado", 0))
    usuario             = datos.get("usuario", "admin")
    orden_id_existente  = datos.get("orden_id_existente")  # None = crear nueva OC

    try:
        fecha = datetime.fromisoformat(fecha_str) if fecha_str else datetime.now()
    except Exception:
        fecha = datetime.now()

    subtotal = sum(
        float(p.get("precio_unitario_usd", 0)) * float(p.get("cantidad", 0))
        for p in productos_data
    )

    # ── Orden de compra ───────────────────────────────────────────────────────
    if orden_id_existente:
        # Vincular a OC existente (aprobada o recibida_parcial)
        orden = db.query(OrdenCompra).filter(OrdenCompra.id == orden_id_existente).first()
        if not orden:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        if orden.estado not in ("aprobada", "recibida_parcial"):
            raise HTTPException(status_code=400, detail=f"La orden está en estado '{orden.estado}' y no puede recibirse")
        orden.observacion = f"{orden.observacion or ''} | Factura IA: {numero_factura}".strip(" |")
    else:
        # Crear OC nueva cerrada directamente
        orden = OrdenCompra(
            numero           = _next_oc_numero(db),
            proveedor_id     = proveedor_id,
            fecha_creacion   = fecha,
            fecha_aprobacion = fecha,
            estado           = "cerrada",
            creado_por       = usuario,
            aprobado_por     = usuario,
            moneda           = "USD",
            subtotal         = round(subtotal, 2),
            descuento        = round(descuento, 2),
            total            = round(total_factura, 2),
            observacion      = f"Factura IA: {numero_factura}",
        )
        db.add(orden)
        db.flush()

        for p in productos_data:
            db.add(DetalleOrdenCompra(
                orden_id            = orden.id,
                producto_id         = p.get("producto_id"),
                nombre_producto     = p.get("nombre_producto", ""),
                codigo_proveedor    = p.get("codigo_proveedor", ""),
                cantidad_pedida     = float(p.get("cantidad", 0)),
                precio_unitario_usd = float(p.get("precio_unitario_usd", 0)),
                subtotal            = float(p.get("subtotal", 0)),
                es_producto_nuevo   = False,
            ))

    # ── Estado de pago ────────────────────────────────────────────────────────
    if condicion_pago == "contado":
        estado_pago       = "pagado"
        abonado_real      = total_factura
        saldo_pend        = 0.0
        fecha_vencimiento = None
    elif condicion_pago == "credito_parcial":
        estado_pago  = "pendiente"
        abonado_real = monto_abonado
        saldo_pend   = round(total_factura - monto_abonado, 2)
        prov_obj     = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first() if proveedor_id else None
        dias         = (prov_obj.dias_credito or 30) if prov_obj else 30
        fecha_vencimiento = (fecha + timedelta(days=dias)).date()
    else:  # credito_completo
        estado_pago  = "pendiente"
        abonado_real = 0.0
        saldo_pend   = total_factura
        prov_obj     = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first() if proveedor_id else None
        dias         = (prov_obj.dias_credito or 30) if prov_obj else 30
        fecha_vencimiento = (fecha + timedelta(days=dias)).date()

    # ── Recepción ─────────────────────────────────────────────────────────────
    recepcion = RecepcionCompra(
        orden_id                = orden.id,
        fecha_recepcion         = fecha,
        recibido_por            = usuario,
        observacion             = f"Factura: {numero_factura}",
        total_recibido          = round(subtotal, 2),
        monto_factura           = round(total_factura, 2),
        estado_pago             = estado_pago,
        numero_factura          = numero_factura,
        fecha_vencimiento_pago  = fecha_vencimiento,
    )
    db.add(recepcion)
    db.flush()

    # ── Detalles de recepción + stock + costo ─────────────────────────────────
    for p in productos_data:
        prod_id    = p.get("producto_id")
        cantidad   = float(p.get("cantidad", 0))
        precio     = float(p.get("precio_unitario_usd", 0))
        actualizar = bool(p.get("actualizar_costo", False))
        costo_ant  = None

        if prod_id:
            prod = db.query(Producto).filter(Producto.id == prod_id).first()
            if prod:
                prod.stock = (prod.stock or 0) + int(cantidad)
                if actualizar:
                    costo_ant      = prod.costo_usd
                    prod.costo_usd = precio

        db.add(DetalleRecepcion(
            recepcion_id             = recepcion.id,
            detalle_orden_id         = 0,
            producto_id              = prod_id or 0,
            cantidad_recibida        = cantidad,
            precio_unitario_real_usd = precio,
            subtotal                 = round(cantidad * precio, 2),
            actualizo_costo          = actualizar,
            costo_anterior           = costo_ant,
        ))

        # ── Actualizar catálogo proveedor ─────────────────────────────
        if prod_id and proveedor_id:
            codigo_prov = p.get("codigo_proveedor", "").strip()
            nombre_prod = p.get("nombre_producto", "")
            existente_catalogo = db.query(CatalogoProveedor).filter(
                CatalogoProveedor.proveedor_id == proveedor_id,
                CatalogoProveedor.producto_id  == prod_id,
            ).first()
            if not existente_catalogo:
                db.add(CatalogoProveedor(
                    proveedor_id          = proveedor_id,
                    producto_id           = prod_id,
                    nombre_producto       = nombre_prod,
                    codigo_proveedor      = codigo_prov if codigo_prov else None,
                    precio_referencia_usd = precio,
                ))
            else:
                existente_catalogo.precio_referencia_usd = precio

    # ── Movimientos bancarios por cada pago ──────────────────────────────────
    pagos_data = datos.get("pagos", [])
    if pagos_data and abonado_real > 0:
        tasa_rec = db.query(TasaCambio).order_by(TasaCambio.fecha.desc()).first()
        tasa     = float(tasa_rec.tasa if tasa_rec else 1.0)
        prov     = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first() if proveedor_id else None
        for pago in pagos_data:
            monto_pago  = float(pago.get("monto", 0))
            moneda_pago = pago.get("moneda", "USD")
            cuenta_id_p = pago.get("cuenta_id")
            if monto_pago <= 0:
                continue
            db.add(MovimientoBancario(
                fecha            = datetime.now(),
                tipo             = "pago_proveedor",
                cuenta_origen_id = int(cuenta_id_p) if cuenta_id_p else None,
                monto            = monto_pago,
                moneda           = moneda_pago,
                tasa_cambio      = tasa if moneda_pago == "Bs" else None,
                monto_convertido = round(monto_pago / tasa, 2) if moneda_pago == "Bs" and tasa > 0 else monto_pago,
                concepto         = f"Pago factura {numero_factura}",
                beneficiario     = prov.nombre if prov else "",
                categoria        = "proveedores",
                proveedor_id     = proveedor_id,
                orden_compra_id  = orden.id,
                registrado_por   = usuario,
            ))

    # ── Si era OC existente, actualizar su estado ─────────────────────────────
    if orden_id_existente:
        todas_recepciones = db.query(RecepcionCompra).filter(
            RecepcionCompra.orden_id == orden.id
        ).all()
        total_recibido_acum = sum(r.total_recibido or 0 for r in todas_recepciones)
        orden.estado = "cerrada" if total_recibido_acum >= orden.total * 0.99 else "recibida_parcial"

    db.commit()
    return {
        "recepcion_id":   recepcion.id,
        "orden_id":       orden.id,
        "orden_numero":   orden.numero,
        "saldo_pendiente": round(saldo_pend, 2),
        "mensaje":        f"Compra registrada: {orden.numero}",
    }