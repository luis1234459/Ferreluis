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
    Producto, VarianteProducto, Proveedor, CatalogoProveedor, AliasProveedor,
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


import re as _re_global

def _huella_codigo(codigo: str) -> str:
    """
    Fingerprint tolerante para códigos largos de proveedor.
    Normaliza (solo alfanuméricos, mayúsculas) y luego:
      - Si el resultado tiene <= 10 chars: usa el código completo.
      - Si tiene > 10 chars: usa primeros 5 + últimos 5, ignorando el centro.
    Así dos extracciones OCR del mismo código que difieran en el centro igual hacen match.
    """
    norm = _re_global.sub(r'[^A-Z0-9]', '', codigo.upper())
    if not norm:
        return ""
    if len(norm) <= 10:
        return norm
    return norm[:5] + norm[-5:]


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
                        '  "rif_proveedor": "RIF o NIT del proveedor si aparece, o vacío",\n'
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


@router.post("/resolver-proveedor")
def resolver_proveedor(datos: dict, db: Session = Depends(get_db)):
    """
    Busca proveedor por RIF exacto.
    Si encuentra → devuelve el proveedor y actualiza nombre si cambió.
    Si no encuentra → crea proveedor nuevo y lo devuelve.
    """
    nombre  = (datos.get("nombre") or "").strip()
    rif     = (datos.get("rif") or "").strip()
    usuario = datos.get("usuario", "")

    if not nombre and not rif:
        raise HTTPException(status_code=400, detail="Se requiere nombre o RIF")

    proveedor = None

    # Buscar por RIF exacto primero
    if rif:
        proveedor = db.query(Proveedor).filter(
            Proveedor.rif == rif,
            Proveedor.activo == True,
        ).first()

    # Si encontró por RIF, actualizar nombre si cambió
    if proveedor and nombre and proveedor.nombre != nombre:
        nombre_anterior  = proveedor.nombre
        proveedor.nombre = nombre
        db.commit()
        db.refresh(proveedor)
        return {
            "id":               proveedor.id,
            "nombre":           proveedor.nombre,
            "rif":              proveedor.rif or "",
            "es_nuevo":         False,
            "nombre_anterior":  nombre_anterior,
            "actualizo_nombre": True,
        }

    # Si encontró sin cambio de nombre
    if proveedor:
        return {
            "id":               proveedor.id,
            "nombre":           proveedor.nombre,
            "rif":              proveedor.rif or "",
            "es_nuevo":         False,
            "actualizo_nombre": False,
        }

    # No encontró → crear proveedor nuevo
    nuevo = Proveedor(
        nombre         = nombre or f"Proveedor {rif}",
        rif            = rif or None,
        activo         = True,
        fecha_registro = datetime.now(),
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    if not nuevo.codigo:
        nuevo.codigo = f"PRV-{nuevo.id:04d}"
        db.commit()
        db.refresh(nuevo)

    return {
        "id":               nuevo.id,
        "nombre":           nuevo.nombre,
        "rif":              nuevo.rif or "",
        "es_nuevo":         True,
        "actualizo_nombre": False,
    }


# ---------------------------------------------------------------------------
# GET /facturas/buscar-producto
# ---------------------------------------------------------------------------

@router.get("/buscar-producto")
def buscar_producto(
    nombre: str = "",
    codigo: str = "",
    proveedor_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    resultados = []
    ids_ya: set = set()  # (producto_id, variante_id_or_None)

    def _res_variante(p, v, codigo_prov="", match_exacto=False):
        partes = [x for x in [v.clase, v.color] if x]
        sufijo = f" ({' / '.join(partes)})" if partes else ""
        cod_var = v.codigo or ""
        nombre_display = f"[{cod_var}] {p.nombre}{sufijo}" if cod_var else f"{p.nombre}{sufijo}"
        return {
            "id": p.id, "nombre": nombre_display,
            "codigo_proveedor": codigo_prov,
            "variante_id": v.id, "variante_codigo": cod_var,
            "costo_usd": float(v.costo_usd or p.costo_usd or 0),
            "stock": int(v.stock or 0),
            "match_exacto": match_exacto,
        }

    def _res_producto(p, codigo_prov="", match_exacto=False):
        return {
            "id": p.id, "nombre": p.nombre,
            "codigo_proveedor": codigo_prov,
            "variante_id": None, "variante_codigo": None,
            "costo_usd": float(p.costo_usd or 0),
            "stock": int(p.stock or 0),
            "match_exacto": match_exacto,
        }

    def _expandir(p, codigo_prov="", match_exacto=False):
        vs = db.query(VarianteProducto).filter(
            VarianteProducto.producto_id == p.id,
            VarianteProducto.activo == True,
        ).all()
        if vs:
            return [_res_variante(p, v, codigo_prov, match_exacto) for v in vs]
        return [_res_producto(p, codigo_prov, match_exacto)]

    # Prioridad 1a: match exacto por código en catálogo del proveedor
    if proveedor_id and codigo:
        cats = db.query(CatalogoProveedor).filter(
            CatalogoProveedor.proveedor_id == proveedor_id,
            CatalogoProveedor.codigo_proveedor == codigo.strip(),
        ).all()
        for c in cats:
            if not c.producto_id:
                continue
            p = db.query(Producto).filter(Producto.id == c.producto_id).first()
            if not p:
                continue
            if c.variante_id:
                key = (p.id, c.variante_id)
                if key not in ids_ya:
                    v = db.query(VarianteProducto).filter(VarianteProducto.id == c.variante_id).first()
                    if v:
                        resultados.append(_res_variante(p, v, c.codigo_proveedor, True))
                        ids_ya.add(key)
            else:
                for r in _expandir(p, c.codigo_proveedor, True):
                    key = (p.id, r["variante_id"])
                    if key not in ids_ya:
                        resultados.append(r)
                        ids_ya.add(key)

    # Prioridad 1b: match por huella (primeros5+ultimos5) — tolera variaciones OCR en el centro
    if proveedor_id and codigo and not resultados:
        huella = _huella_codigo(codigo)
        if huella:
            cats = db.query(CatalogoProveedor).filter(
                CatalogoProveedor.proveedor_id == proveedor_id,
                CatalogoProveedor.codigo_huella == huella,
            ).all()
            for c in cats:
                if not c.producto_id:
                    continue
                p = db.query(Producto).filter(Producto.id == c.producto_id).first()
                if not p:
                    continue
                if c.variante_id:
                    key = (p.id, c.variante_id)
                    if key not in ids_ya:
                        v = db.query(VarianteProducto).filter(VarianteProducto.id == c.variante_id).first()
                        if v:
                            resultados.append(_res_variante(p, v, c.codigo_proveedor, True))
                            ids_ya.add(key)
                else:
                    for r in _expandir(p, c.codigo_proveedor, True):
                        key = (p.id, r["variante_id"])
                        if key not in ids_ya:
                            resultados.append(r)
                            ids_ya.add(key)

    # Prioridad 2: match parcial por código en catálogo
    if proveedor_id and codigo and not resultados:
        cats = db.query(CatalogoProveedor).filter(
            CatalogoProveedor.proveedor_id == proveedor_id,
            CatalogoProveedor.codigo_proveedor.ilike(f"%{codigo}%"),
        ).limit(5).all()
        for c in cats:
            if not c.producto_id:
                continue
            p = db.query(Producto).filter(Producto.id == c.producto_id).first()
            if not p:
                continue
            if c.variante_id:
                key = (p.id, c.variante_id)
                if key not in ids_ya:
                    v = db.query(VarianteProducto).filter(VarianteProducto.id == c.variante_id).first()
                    if v:
                        resultados.append(_res_variante(p, v, c.codigo_proveedor, False))
                        ids_ya.add(key)
            else:
                for r in _expandir(p, c.codigo_proveedor, False):
                    key = (p.id, r["variante_id"])
                    if key not in ids_ya:
                        resultados.append(r)
                        ids_ya.add(key)

    # Prioridad 3: buscar por nombre — SOLO si no hay código de proveedor para cruzar.
    # Cuando hay proveedor_id + codigo y no hay match en catálogo, el producto es nuevo
    # y NO debe mezclarse con productos de otros proveedores por similitud de nombre.
    if not (proveedor_id and codigo):
        busq = nombre or codigo
        if len(busq) >= 2:
            prods = db.query(Producto).filter(
                Producto.nombre.ilike(f"%{busq}%")
            ).limit(10).all()
            for p in prods:
                for r in _expandir(p, "", False):
                    key = (p.id, r["variante_id"])
                    if key not in ids_ya:
                        resultados.append(r)
                        ids_ya.add(key)

    return resultados[:15]


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
                    "variante_id":         d.variante_id,
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
                variante_id         = p.get("variante_id"),
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

    # ── RIF del proveedor para indexar catálogo ──────────────────────────────
    prov_obj_rif = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first() if proveedor_id else None
    rif_prov = (prov_obj_rif.rif or "").strip() if prov_obj_rif else ""

    # ── Detalles de recepción + stock + costo ─────────────────────────────────
    for p in productos_data:
        prod_id     = p.get("producto_id")
        variante_id = p.get("variante_id")
        cantidad    = float(p.get("cantidad", 0))
        precio      = float(p.get("precio_unitario_usd", 0))
        actualizar  = bool(p.get("actualizar_costo", False))
        es_nuevo    = bool(p.get("es_nuevo", False))
        codigo_prov = (p.get("codigo_proveedor") or "").strip()
        nombre_prod = p.get("nombre_producto") or p.get("nombre_ia") or ""
        costo_ant   = None

        # Si es producto nuevo, crearlo en inventario
        if es_nuevo and not prod_id:
            nuevo_prod = Producto(
                nombre       = nombre_prod,
                descripcion  = f"Creado desde factura IA — {numero_factura}",
                stock        = 0,
                costo_usd    = precio,
                margen       = 0.30,
                proveedor_id = proveedor_id,
                activo       = True,
            )
            db.add(nuevo_prod)
            db.flush()
            prod_id = nuevo_prod.id

        if prod_id:
            prod = db.query(Producto).filter(Producto.id == prod_id).first()
            if prod:
                if variante_id:
                    variante = db.query(VarianteProducto).filter(VarianteProducto.id == variante_id).first()
                    if variante:
                        variante.stock = (variante.stock or 0) + int(cantidad)
                        if actualizar:
                            costo_ant = variante.costo_usd
                            variante.costo_usd = precio
                else:
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

        # ── Vincular código en catálogo (inamovible una vez guardado) ─────────
        if prod_id and proveedor_id:
            existente_catalogo = db.query(CatalogoProveedor).filter(
                CatalogoProveedor.proveedor_id == proveedor_id,
                CatalogoProveedor.producto_id  == prod_id,
                CatalogoProveedor.variante_id  == variante_id,
            ).first()
            huella_prov = _huella_codigo(codigo_prov) if codigo_prov else None
            if not existente_catalogo:
                db.add(CatalogoProveedor(
                    proveedor_id          = proveedor_id,
                    producto_id           = prod_id,
                    variante_id           = variante_id,
                    nombre_producto       = nombre_prod,
                    codigo_proveedor      = codigo_prov if codigo_prov else None,
                    codigo_huella         = huella_prov,
                    rif_proveedor         = rif_prov if rif_prov else None,
                    precio_referencia_usd = precio,
                    bloqueado             = True,  # primera compra → asociación inamovible
                ))
            else:
                existente_catalogo.precio_referencia_usd = precio
                existente_catalogo.bloqueado              = True  # confirmar compra bloquea
                if not existente_catalogo.codigo_proveedor and codigo_prov:
                    existente_catalogo.codigo_proveedor = codigo_prov
                    existente_catalogo.codigo_huella     = huella_prov
                elif existente_catalogo.codigo_proveedor and not existente_catalogo.codigo_huella:
                    existente_catalogo.codigo_huella = _huella_codigo(existente_catalogo.codigo_proveedor)
                if not existente_catalogo.rif_proveedor and rif_prov:
                    existente_catalogo.rif_proveedor = rif_prov

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


# ---------------------------------------------------------------------------
# POST /facturas/escanear-catalogo
# Lee un PDF de catálogo de proveedor (NO es una factura/compra).
# Extrae: código, descripción y precio de cada producto del catálogo.
# ---------------------------------------------------------------------------

def _pdf_paginas_base64(contenido: bytes) -> list[tuple[str, str]]:
    """Convierte todas las páginas de un PDF a imágenes base64 usando PyMuPDF."""
    try:
        import fitz
    except ImportError:
        raise HTTPException(status_code=500, detail="pymupdf no está instalado.")
    doc    = fitz.open(stream=contenido, filetype="pdf")
    paginas = []
    for pagina in doc:
        mat  = fitz.Matrix(2.0, 2.0)  # 2x zoom = ~150 DPI efectivo
        pix  = pagina.get_pixmap(matrix=mat, alpha=False)
        img  = io.BytesIO(pix.tobytes("jpeg", jpg_quality=90))
        paginas.append((base64.standard_b64encode(img.getvalue()).decode("utf-8"), "image/jpeg"))
    doc.close()
    return paginas


@router.post("/escanear-catalogo")
async def escanear_catalogo(
    archivo: UploadFile = File(...),
    proveedor_nombre: str = Form(""),
):
    client       = anthropic.Anthropic(api_key=API_KEY)
    contenido    = await archivo.read()
    content_type = (archivo.content_type or "").lower().split(";")[0].strip()

    # Construir bloques de contenido visual
    bloques_imagen: list[dict] = []
    if content_type == "application/pdf":
        for img_b64, mtype in _pdf_paginas_base64(contenido):
            bloques_imagen.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mtype, "data": img_b64},
            })
    elif content_type in TIPOS_IMAGEN:
        bloques_imagen.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": MEDIA_TYPE_MAP.get(content_type, content_type),
                "data": base64.standard_b64encode(contenido).decode("utf-8"),
            },
        })
    else:
        raise HTTPException(status_code=400, detail=f"Formato no soportado: {content_type}")

    prov_ctx = f'El catálogo pertenece al proveedor: "{proveedor_nombre}".\n' if proveedor_nombre.strip() else ""
    texto_prompt = {
        "type": "text",
        "text": (
            "Estás analizando un CATÁLOGO DE PRODUCTOS DE PROVEEDOR. "
            "NO es una factura ni una orden de compra.\n"
            f"{prov_ctx}"
            "El catálogo tiene columnas: CÓDIGO, DESCRIPCIÓN y PRECIO.\n\n"
            "Extrae TODOS los productos de TODAS las páginas que ves.\n"
            "Devuelve SOLO un JSON con este formato exacto, sin texto adicional:\n"
            "{\n"
            f'  "proveedor": "{proveedor_nombre or "nombre del proveedor"}",\n'
            '  "productos": [\n'
            "    {\n"
            '      "codigo": "código del producto o cadena vacía",\n'
            '      "descripcion": "nombre o descripción del producto",\n'
            '      "precio": numero o null\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "IMPORTANTE: precio es el costo de compra al proveedor. "
            "No omitas ningún producto. No agregues texto fuera del JSON."
        ),
    }

    mensaje = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=8192,
        messages=[{
            "role": "user",
            "content": bloques_imagen + [texto_prompt],
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
# POST /facturas/importar-catalogo
# Crea o vincula productos en inventario desde un catálogo.
# Regla inamovible: código_proveedor queda enlazado de forma permanente.
# ---------------------------------------------------------------------------

from fastapi import Body as _Body

@router.post("/importar-catalogo")
def importar_catalogo(
    datos: dict = _Body(...),
    db: Session = Depends(get_db),
):
    proveedor_id = datos.get("proveedor_id")
    items        = datos.get("items", [])

    if not proveedor_id:
        raise HTTPException(400, "proveedor_id requerido")

    prov = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not prov:
        raise HTTPException(404, "Proveedor no encontrado")
    if not prov.rif:
        raise HTTPException(400, "El proveedor no tiene RIF registrado. Agréguelo en Proveedores antes de importar un catálogo.")

    rif_prov  = prov.rif
    creados   = 0
    vinculados = 0
    errores   = []

    for item in items:
        sp = db.begin_nested()  # SAVEPOINT por item — garantiza atomicidad
        try:
            codigo_cat  = str(item.get("codigo_catalogo", "")).strip() or None
            nombre      = str(item.get("nombre_final", "")).strip()
            depto_id    = item.get("departamento_id")
            cat_id      = item.get("categoria_id")
            accion      = item.get("accion", "nuevo")
            prod_id_ext = item.get("producto_id_existente")
            costo       = float(item.get("costo_final") or 0)

            if not nombre:
                sp.rollback()
                errores.append({"item": item, "motivo": "nombre vacío"})
                continue

            if accion == "nuevo":
                # Código: usar el del catálogo si está disponible; si ya existe en otro producto, no asignar
                codigo_a_asignar = None
                if codigo_cat:
                    ya_existe = db.query(Producto.id).filter(Producto.codigo == codigo_cat).first()
                    codigo_a_asignar = None if ya_existe else codigo_cat

                # Si el catálogo no trae código, generar uno automático
                if not codigo_a_asignar:
                    import re as _re
                    letras  = _re.sub(r'[^A-Za-z]', '', nombre).upper()[:3].ljust(3, 'X')
                    prefijo = letras + '-'
                    nums    = [int(m.group(1)) for (c,) in db.query(Producto.codigo).filter(
                                   Producto.codigo.like(f"{prefijo}%")).all()
                               if c and (m := _re.search(r'(\d+)$', c))]
                    codigo_a_asignar = f"{prefijo}{(max(nums)+1 if nums else 1):03d}"

                nuevo = Producto(
                    nombre          = nombre,
                    codigo          = codigo_a_asignar,
                    proveedor_id    = proveedor_id,
                    departamento_id = depto_id,
                    categoria_id    = cat_id,
                    costo_usd       = costo,
                    margen          = 0.30,
                    stock           = 0,
                    activo          = True,
                )
                db.add(nuevo)
                db.flush()
                prod_id = nuevo.id

            elif accion == "vincular" and prod_id_ext:
                prod_id = int(prod_id_ext)
                prod    = db.query(Producto).filter(Producto.id == prod_id).first()
                if not prod:
                    sp.rollback()
                    errores.append({"item": item, "motivo": "producto existente no encontrado"})
                    continue
                # Bloquear si el producto ya tiene compras confirmadas de OTRO proveedor
                conflicto_bloqueado = db.query(CatalogoProveedor).filter(
                    CatalogoProveedor.producto_id  == prod_id,
                    CatalogoProveedor.bloqueado    == True,
                    CatalogoProveedor.rif_proveedor != rif_prov,
                ).first()
                if conflicto_bloqueado:
                    sp.rollback()
                    errores.append({
                        "item":   item,
                        "motivo": f"El producto '{prod.nombre}' ya tiene compras confirmadas de otro proveedor "
                                  f"(RIF {conflicto_bloqueado.rif_proveedor}). Debe crearse como producto nuevo.",
                    })
                    continue
                if nombre and nombre != prod.nombre:
                    prod.nombre = nombre
                if prod.proveedor_id is None:
                    prod.proveedor_id = proveedor_id

            else:
                sp.rollback()
                errores.append({"item": item, "motivo": "acción desconocida o producto no especificado"})
                continue

            # ── Regla inamovible: (codigo_proveedor, rif_proveedor) → un solo producto ──
            # Verificar que el par código+RIF no esté ya vinculado a OTRO producto distinto
            if codigo_cat and rif_prov:
                conflicto = db.query(CatalogoProveedor).filter(
                    CatalogoProveedor.codigo_proveedor == codigo_cat,
                    CatalogoProveedor.rif_proveedor    == rif_prov,
                    CatalogoProveedor.producto_id      != prod_id,
                ).first()
                if conflicto:
                    sp.rollback()
                    errores.append({
                        "item":   item,
                        "motivo": f"Código '{codigo_cat}' (RIF {rif_prov}) ya está vinculado a otro producto — cruce inmutable.",
                    })
                    continue

            existente = db.query(CatalogoProveedor).filter(
                CatalogoProveedor.proveedor_id == proveedor_id,
                CatalogoProveedor.producto_id  == prod_id,
                CatalogoProveedor.variante_id  == None,
            ).first()

            if not existente:
                db.add(CatalogoProveedor(
                    proveedor_id          = proveedor_id,
                    rif_proveedor         = rif_prov,
                    producto_id           = prod_id,
                    variante_id           = None,
                    nombre_producto       = nombre,
                    codigo_proveedor      = codigo_cat,
                    codigo_huella         = _huella_codigo(codigo_cat) if codigo_cat else None,
                    precio_referencia_usd = costo,
                ))
            else:
                existente.precio_referencia_usd = costo
                existente.rif_proveedor         = rif_prov   # retroalimentar si faltaba
                # codigo_proveedor NO se sobreescribe si ya existe (inmutable)
                if not existente.codigo_proveedor and codigo_cat:
                    existente.codigo_proveedor = codigo_cat
                    existente.codigo_huella    = _huella_codigo(codigo_cat)
                elif existente.codigo_proveedor and not existente.codigo_huella:
                    existente.codigo_huella = _huella_codigo(existente.codigo_proveedor)

            sp.commit()  # Libera el savepoint — producto + enlace quedan atómicos
            if accion == "nuevo":
                creados += 1
            else:
                vinculados += 1

        except Exception as e:
            sp.rollback()  # Revierte solo este item; la sesión sigue usable
            errores.append({"item": item, "motivo": str(e)})

    db.commit()
    return {
        "creados":    creados,
        "vinculados": vinculados,
        "errores":    errores,
    }