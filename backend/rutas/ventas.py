"""
Módulo de ventas y cobro — lógica de precios con protección cambiaria.

PRECIOS
  precio_base_usd        = costo_usd * (1 + margen)       ← precio interno
  factor                 = tasa_binance / tasa_bcv
  precio_referencial_usd = precio_base_usd * factor        ← precio comercial
  precio_bs              = precio_base_usd * tasa_binance  ← lo que ve el cliente en Bs

TIPOS DE PRECIO
  "referencial" (por defecto): se cobra precio_referencial_usd (con protección)
  "base":                      se cobra precio_base_usd (descuento divisa, requiere auth)

TIPO AUTO-DETECTADO EN LA VENTA
  "mixto": cuando se mezclan métodos USD y Bs en el mismo cobro

CONVERSIÓN DE PAGOS
  Venta USD, pago Bs  → equivalente_usd = monto_bs / tasa_bcv
  Venta Bs,  pago USD → equivalente_bs  = monto_usd * tasa_bcv
  Misma moneda        → sin conversión

EXCESO
  Solo efectivo (USD o Bs) puede tener exceso; métodos digitales no.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from datetime import datetime, date
from database import get_db
from models import (
    Producto, VarianteProducto, Venta, PagoVenta, DetalleVenta,
    TasaCambio, Configuracion, ExcepcionVenta, ClaveAutorizacion, AbonoCredito,
    VentaCliente, Cliente, VendedorPerfil, ComisionVenta,
    GarantiaVenta, PlantillaGarantia,
    METODOS_USD, METODOS_BS, METODOS_VALIDOS,
    TOLERANCIA, DECIMALES_USD, DECIMALES_BS,
)

router = APIRouter()

METODOS_EFECTIVO = {"efectivo_usd", "efectivo_bs"}


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _moneda_de_metodo(metodo: str) -> str:
    if metodo in METODOS_USD:
        return "USD"
    if metodo in METODOS_BS:
        return "Bs"
    raise HTTPException(status_code=400, detail=f"Método de pago inválido: '{metodo}'")


def _calcular_equivalente(monto: float, moneda_pago: str,
                           moneda_venta: str, tasa: float) -> float:
    """Convierte monto desde moneda_pago a moneda_venta usando tasa_bcv."""
    dec = DECIMALES_USD if moneda_venta == "USD" else DECIMALES_BS
    if moneda_pago == moneda_venta:
        return round(monto, dec)
    if moneda_pago == "USD" and moneda_venta == "Bs":
        return round(monto * tasa, DECIMALES_BS)
    if moneda_pago == "Bs" and moneda_venta == "USD":
        if tasa <= 0:
            raise HTTPException(status_code=400, detail="Tasa inválida para convertir Bs → USD")
        return round(monto / tasa, DECIMALES_USD)
    raise HTTPException(status_code=500, detail="Conversión no soportada")


def _obtener_tasas(db: Session):
    """Retorna (tasa_bcv, tasa_binance, factor)."""
    obj = db.query(TasaCambio).order_by(TasaCambio.id.desc()).first()
    if not obj or float(obj.tasa or 0) <= 0:
        raise HTTPException(status_code=400, detail="No hay tasa de cambio válida definida")
    bcv     = float(obj.tasa)
    binance = float(obj.tasa_binance or bcv)   # si no hay binance, usar bcv
    factor  = round(binance / bcv, 6) if bcv > 0 else 1.0
    return bcv, binance, factor


def _calcular_precio_base(producto: Producto) -> float:
    return round(float(producto.costo_usd or 0) * (1 + float(producto.margen or 0)), 4)


def _calcular_precio_referencial(precio_base: float, factor: float) -> float:
    return round(precio_base * factor, 4)


def _validar_autorizacion(db: Session, clave: str) -> bool:
    obj = db.query(ClaveAutorizacion).filter(
        ClaveAutorizacion.accion == "descuento"
    ).first()
    if not obj or not obj.clave:
        # Fallback: check legacy Configuracion table
        config = db.query(Configuracion).first()
        if not config or not config.clave_autorizacion:
            return False
        return clave == config.clave_autorizacion
    return clave == obj.clave


def _registrar_excepcion(db: Session, venta_id: int, motivo: str,
                          usuario: str, **kwargs):
    try:
        db.add(ExcepcionVenta(venta_id=venta_id, motivo=motivo,
                               usuario=usuario, **kwargs))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/ventas/")
def listar_ventas(db: Session = Depends(get_db)):
    return db.query(Venta).order_by(Venta.id.desc()).all()


@router.get("/ventas/hoy")
def ventas_hoy(db: Session = Depends(get_db)):
    """Ventas del día actual con nombre de cliente. Para el tab Historial."""
    hoy = date.today().isoformat()
    ventas = (
        db.query(Venta)
        .filter(sqlfunc.date(Venta.fecha) == hoy)
        .order_by(Venta.fecha.desc())
        .all()
    )

    resultado = []
    for v in ventas:
        vc = db.query(VentaCliente).filter(VentaCliente.venta_id == v.id).first()
        cliente_nombre = "—"
        if vc:
            c = db.query(Cliente).filter(Cliente.id == vc.cliente_id).first()
            if c:
                cliente_nombre = c.nombre

        resultado.append({
            "id":     v.id,
            "hora":   v.fecha.strftime("%H:%M") if v.fecha else "—",
            "cliente": cliente_nombre,
            "total":  round(float(v.total or 0), 2),
            "moneda": v.moneda_venta,
            "estado": v.estado,
        })

    return resultado


@router.get("/ventas/{venta_id}")
def obtener_venta(venta_id: int, db: Session = Depends(get_db)):
    venta = db.query(Venta).filter(Venta.id == venta_id).first()
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    pagos    = db.query(PagoVenta).filter(PagoVenta.venta_id == venta_id).all()
    detalles = db.query(DetalleVenta).filter(DetalleVenta.venta_id == venta_id).all()

    detalles_out = []
    for d in detalles:
        prod = db.query(Producto).filter(Producto.id == d.producto_id).first()
        variante_label  = None
        variante_codigo = None
        if d.variante_id:
            v = db.query(VarianteProducto).filter(VarianteProducto.id == d.variante_id).first()
            if v:
                variante_label  = f"{v.clase} {v.color or ''}".strip()
                variante_codigo = v.codigo
        detalles_out.append({
            "id":               d.id,
            "producto_id":      d.producto_id,
            "variante_id":      d.variante_id,
            "variante_label":   variante_label,
            "variante_codigo":  variante_codigo,
            "nombre":           prod.nombre if prod else f"Producto #{d.producto_id}",
            "cantidad":         d.cantidad,
            "tipo_precio_usado":d.tipo_precio_usado,
            "precio_unitario":  d.precio_unitario,
            "subtotal":         d.subtotal,
        })

    pagos_out = [
        {
            "metodo_pago":       p.metodo_pago,
            "moneda_pago":       p.moneda_pago,
            "monto_original":    p.monto_original,
            "monto_equivalente": p.monto_equivalente,
            "referencia":        p.referencia,
        }
        for p in pagos
    ]

    # Nombre de cliente vinculado
    vc = db.query(VentaCliente).filter(VentaCliente.venta_id == venta_id).first()
    cliente_nombre = None
    if vc:
        c = db.query(Cliente).filter(Cliente.id == vc.cliente_id).first()
        if c:
            cliente_nombre = c.nombre

    # Garantías registradas para esta venta
    garantias_raw = db.query(GarantiaVenta).filter(GarantiaVenta.venta_id == venta_id).all()
    garantias_out = [
        {c.name: getattr(g, c.name) for c in g.__table__.columns}
        for g in garantias_raw
    ]

    return {
        "venta": {
            "id":             venta.id,
            "fecha":          venta.fecha.isoformat() if venta.fecha else None,
            "usuario":        venta.usuario,
            "cliente":        cliente_nombre,
            "moneda_venta":   venta.moneda_venta,
            "tipo_precio_usado": venta.tipo_precio_usado,
            "subtotal":       venta.subtotal,
            "descuento":      venta.descuento,
            "total":          venta.total,
            "tasa_bcv":       venta.tasa_bcv,
            "tasa_binance":   venta.tasa_binance,
            "total_abonado":  venta.total_abonado,
            "exceso":         venta.exceso,
            "estado":         venta.estado,
            "observacion":    venta.observacion,
        },
        "detalles":  detalles_out,
        "pagos":     pagos_out,
        "garantias": garantias_out,
    }


@router.post("/ventas/")
def registrar_venta(data: dict, db: Session = Depends(get_db)):
    """
    Payload esperado:
    {
        "usuario":            "cajero",
        "moneda_venta":       "USD",       // "USD" | "Bs"
        "tipo_precio":        "referencial", // "referencial" | "base"
        "descuento":          0,           // descuento global en moneda_venta
        "observacion":        "",
        "autorizacion_clave": "",
        "cliente_id":         1,           // requerido; si null → se asigna Consumidor Final
        "detalles": [
            { "producto_id": 1, "cantidad": 2 }
        ],
        "pagos": [
            { "metodo": "efectivo_usd", "monto": 20.0, "referencia": "" }
        ]
    }
    """

    # ── Datos básicos ────────────────────────────────────────────────────────
    usuario         = data.get("usuario", "")
    moneda_venta    = data.get("moneda_venta", "USD")
    tipo_precio     = data.get("tipo_precio", "referencial")   # "base" | "referencial"
    descuento_input = float(data.get("descuento", 0) or 0)
    observacion     = data.get("observacion", "") or ""
    autorizacion    = data.get("autorizacion_clave", "") or ""
    detalles_in     = data.get("detalles", [])
    pagos_in        = data.get("pagos", [])
    cliente_id      = data.get("cliente_id")

    # ── Si no viene cliente_id, asignar "Consumidor Final" automáticamente ──
    if not cliente_id:
        consumidor = db.query(Cliente).filter(
            Cliente.es_cliente_generico == True
        ).first()
        if consumidor:
            cliente_id = consumidor.id

    # ── Validaciones de estructura ───────────────────────────────────────────
    if moneda_venta not in ("USD", "Bs"):
        raise HTTPException(status_code=400, detail="moneda_venta debe ser 'USD' o 'Bs'")
    if tipo_precio not in ("base", "referencial"):
        raise HTTPException(status_code=400, detail="tipo_precio debe ser 'base' o 'referencial'")
    if not detalles_in:
        raise HTTPException(status_code=400, detail="No hay productos en la venta")
    if not pagos_in:
        raise HTTPException(status_code=400, detail="No hay pagos registrados")
    if descuento_input < 0:
        raise HTTPException(status_code=400, detail="El descuento no puede ser negativo")

    # ── Tasas de cambio ──────────────────────────────────────────────────────
    tasa_bcv, tasa_binance, factor = _obtener_tasas(db)

    # ── Validar métodos de pago ──────────────────────────────────────────────
    for i, p in enumerate(pagos_in):
        metodo = p.get("metodo", "")
        monto  = float(p.get("monto", 0) or 0)
        if metodo not in METODOS_VALIDOS:
            raise HTTPException(status_code=400,
                                detail=f"Pago #{i+1}: método inválido '{metodo}'")
        if monto <= 0:
            raise HTTPException(status_code=400,
                                detail=f"Pago #{i+1} ({metodo}): monto debe ser > 0")
        moneda_pago = _moneda_de_metodo(metodo)
        if moneda_pago != moneda_venta and tasa_bcv <= 0:
            raise HTTPException(status_code=400,
                                detail="Se requiere tasa activa para cobros en distinta moneda")

    # ── Validación especial: pagos a crédito ─────────────────────────────────
    pagos_credito_in = [p for p in pagos_in if p.get("metodo") == "credito"]
    if pagos_credito_in:
        if not cliente_id:
            raise HTTPException(status_code=400,
                                detail="Se requiere cliente identificado para ventas a crédito")
        cliente_obj = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente_obj or not cliente_obj.tiene_credito:
            raise HTTPException(status_code=400,
                                detail="El cliente no tiene crédito habilitado")
        monto_credito_usd = sum(float(p.get("monto", 0)) for p in pagos_credito_in)
        if moneda_venta == "Bs" and tasa_bcv > 0:
            monto_credito_usd = round(monto_credito_usd / tasa_bcv, DECIMALES_USD)
        saldo_disponible = float(cliente_obj.saldo_credito or 0)
        if saldo_disponible < monto_credito_usd - TOLERANCIA:
            raise HTTPException(
                status_code=400,
                detail=f"CREDITO_EXCEDIDO: saldo disponible ${saldo_disponible:.2f}, "
                       f"crédito solicitado ${monto_credito_usd:.2f}"
            )

    # ── Procesar productos ───────────────────────────────────────────────────
    motivos_autorizacion = []
    subtotal             = 0.0
    detalles_procesados  = []
    decimales            = DECIMALES_USD if moneda_venta == "USD" else DECIMALES_BS

    # Descuento divisa: usar precio_base en lugar de referencial
    if tipo_precio == "base":
        motivos_autorizacion.append("Descuento divisa: precios en USD base")

    for item in detalles_in:
        producto_id = int(item.get("producto_id"))
        variante_id = item.get("variante_id")
        if variante_id is not None:
            variante_id = int(variante_id)
        cantidad    = float(item.get("cantidad", 1) or 1)

        if cantidad <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser > 0")

        producto = db.query(Producto).filter(Producto.id == producto_id).first()
        if not producto:
            raise HTTPException(status_code=404,
                                detail=f"Producto no encontrado: ID {producto_id}")

        variante = None
        if variante_id:
            variante = db.query(VarianteProducto).filter(
                VarianteProducto.id == variante_id,
                VarianteProducto.producto_id == producto_id,
            ).first()
            if not variante:
                raise HTTPException(status_code=404,
                                    detail=f"Variante no encontrada: ID {variante_id}")

        # Precios base del sistema
        if variante:
            if variante.precio_override_usd is not None:
                p_base = float(variante.precio_override_usd)
            else:
                costo  = float(variante.costo_usd  if variante.costo_usd  is not None else (producto.costo_usd  or 0))
                margen = float(variante.margen      if variante.margen     is not None else (producto.margen     or 0))
                p_base = round(costo * (1 + margen), 4)
        else:
            p_base = _calcular_precio_base(producto)
        p_ref  = _calcular_precio_referencial(p_base, factor)

        # Precio esperado según tier seleccionado
        precio_esperado_usd = p_base if tipo_precio == "base" else p_ref

        # El frontend puede enviar precio_unitario para descuento manual
        precio_unitario_usd = float(item.get("precio_unitario", 0) or 0)
        if precio_unitario_usd <= 0:
            precio_unitario_usd = precio_esperado_usd

        if precio_unitario_usd < 0:
            raise HTTPException(status_code=400, detail="El precio no puede ser negativo")

        # Sin stock — verificar contra variante o producto
        stock_disponible = float(variante.stock or 0) if variante else float(producto.stock or 0)
        if cantidad > stock_disponible:
            label = f"{producto.nombre}" + (f" ({variante.clase} {variante.color or ''})".rstrip() if variante else "")
            motivos_autorizacion.append(f"Venta sin stock: {label}")

        # Descuento manual (por debajo del precio del tier)
        if precio_unitario_usd < precio_esperado_usd - TOLERANCIA:
            motivos_autorizacion.append(f"Descuento en producto: {producto.nombre}")

        # Convertir a moneda del documento
        if moneda_venta == "USD":
            precio_en_moneda = precio_unitario_usd
        else:
            precio_en_moneda = round(precio_unitario_usd * tasa_bcv, DECIMALES_BS)

        subtotal_linea = round(precio_en_moneda * cantidad, decimales)
        subtotal       = round(subtotal + subtotal_linea, decimales)

        detalles_procesados.append({
            "producto":               producto,
            "producto_id":            producto_id,
            "variante":               variante,
            "variante_id":            variante_id,
            "cantidad":               cantidad,
            "tipo_precio_usado":      tipo_precio,
            "precio_base_snap":       p_base,
            "precio_referencial_snap":p_ref,
            "precio_unitario":        precio_unitario_usd,
            "subtotal":               subtotal_linea,
        })

    # ── Descuento global ─────────────────────────────────────────────────────
    if descuento_input > 0:
        motivos_autorizacion.append("Descuento global de factura")

    if descuento_input > subtotal + TOLERANCIA:
        raise HTTPException(status_code=400,
                            detail="El descuento no puede superar el subtotal")

    descuento = round(min(descuento_input, subtotal), decimales)
    total     = round(subtotal - descuento, decimales)

    # ── Clave de autorización ────────────────────────────────────────────────
    if motivos_autorizacion:
        if not autorizacion:
            raise HTTPException(status_code=400,
                                detail="Se requiere clave de autorización para: "
                                       + "; ".join(motivos_autorizacion))
        if not _validar_autorizacion(db, autorizacion):
            raise HTTPException(status_code=400,
                                detail="Clave de autorización inválida")

    # ── Procesar pagos ───────────────────────────────────────────────────────
    pagos_procesados = []
    total_abonado    = 0.0

    for i, pago in enumerate(pagos_in):
        metodo     = pago["metodo"]
        monto      = float(pago.get("monto", 0))
        referencia = pago.get("referencia", "") or ""

        moneda_pago = _moneda_de_metodo(metodo)
        equivalente = _calcular_equivalente(monto, moneda_pago, moneda_venta, tasa_bcv)

        pendiente_actual = round(total - total_abonado, decimales)
        if equivalente > pendiente_actual + TOLERANCIA:
            if metodo not in METODOS_EFECTIVO:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Pago #{i+1} ({metodo}): equivalente "
                        f"({equivalente:.2f} {moneda_venta}) excede saldo "
                        f"({pendiente_actual:.2f} {moneda_venta}). "
                        "Solo efectivo puede tener exceso."
                    )
                )

        total_abonado = round(total_abonado + equivalente, decimales)
        pagos_procesados.append({
            "metodo_pago":       metodo,
            "moneda_pago":       moneda_pago,
            "monto_original":    monto,
            "tasa_cambio":       tasa_bcv,
            "monto_equivalente": equivalente,
            "moneda_venta":      moneda_venta,
            "referencia":        referencia,
            "cuenta_destino_id": pago.get("cuenta_destino_id"),
        })

    # ── Verificar cobertura ──────────────────────────────────────────────────
    saldo_pendiente = round(total - total_abonado, decimales)
    exceso          = round(total_abonado - total, decimales) if total_abonado > total else 0.0

    if saldo_pendiente > TOLERANCIA:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Pago insuficiente. "
                f"Total: {total:.2f} {moneda_venta} | "
                f"Abonado: {total_abonado:.2f} {moneda_venta} | "
                f"Falta: {saldo_pendiente:.2f} {moneda_venta}"
            )
        )

    # ── Determinar tipo_precio final ─────────────────────────────────────────
    metodos_usados = {p["metodo_pago"] for p in pagos_procesados}
    hay_usd = bool(metodos_usados & METODOS_USD)
    hay_bs  = bool(metodos_usados & METODOS_BS)
    tipo_precio_final = "mixto" if (hay_usd and hay_bs) else tipo_precio

    # ── Guardar en base de datos ─────────────────────────────────────────────
    ahora = datetime.now()

    venta = Venta(
        fecha             = ahora,
        usuario           = usuario,
        moneda_venta      = moneda_venta,
        tipo_precio_usado = tipo_precio_final,
        subtotal          = subtotal,
        descuento         = descuento,
        total             = total,
        tasa_bcv          = tasa_bcv,
        tasa_binance      = tasa_binance,
        factor_cambio     = factor,
        total_abonado     = total_abonado,
        saldo_pendiente   = max(saldo_pendiente, 0),
        exceso            = exceso,
        estado            = "pagado",
        observacion       = observacion,
    )
    db.add(venta)
    db.commit()
    db.refresh(venta)

    for p in pagos_procesados:
        db.add(PagoVenta(
            venta_id          = venta.id,
            metodo_pago       = p["metodo_pago"],
            moneda_pago       = p["moneda_pago"],
            monto_original    = p["monto_original"],
            tasa_cambio       = p["tasa_cambio"],
            monto_equivalente = p["monto_equivalente"],
            moneda_venta      = p["moneda_venta"],
            referencia        = p["referencia"],
            fecha_hora        = ahora,
            usuario           = usuario,
            cuenta_destino_id = p.get("cuenta_destino_id"),
        ))

    for d in detalles_procesados:
        db.add(DetalleVenta(
            venta_id              = venta.id,
            producto_id           = d["producto_id"],
            variante_id           = d["variante_id"],
            cantidad              = d["cantidad"],
            tipo_precio_usado     = d["tipo_precio_usado"],
            precio_base_snap      = d["precio_base_snap"],
            precio_referencial_snap = d["precio_referencial_snap"],
            precio_unitario       = d["precio_unitario"],
            subtotal              = d["subtotal"],
        ))
        if d["variante"]:
            d["variante"].stock = float(d["variante"].stock or 0) - d["cantidad"]
        else:
            d["producto"].stock = float(d["producto"].stock or 0) - d["cantidad"]

    db.commit()

    # Vincular cliente (siempre — nunca queda sin cliente)
    if cliente_id:
        db.add(VentaCliente(venta_id=venta.id, cliente_id=int(cliente_id)))
        db.commit()

    # ── Guardar garantías (snapshot del texto al momento de la venta) ─────────
    garantias_in = data.get("garantias", []) or []
    for g in garantias_in:
        prod_id = g.get("producto_id")
        if not prod_id:
            continue
        prod_g = db.query(Producto).filter(Producto.id == prod_id).first()
        meses_snap = None
        cond_snap  = None
        if prod_g and prod_g.plantilla_garantia_id:
            pl = db.query(PlantillaGarantia).filter(
                PlantillaGarantia.id == prod_g.plantilla_garantia_id
            ).first()
            if pl:
                meses_snap = pl.meses
                cond_snap  = pl.condiciones
        db.add(GarantiaVenta(
            venta_id             = venta.id,
            producto_id          = prod_id,
            variante_id          = g.get("variante_id"),
            serial               = g.get("serial") or None,
            modelo               = g.get("modelo") or None,
            meses_garantia       = meses_snap,
            condiciones_snapshot = cond_snap,
        ))
    if garantias_in:
        db.commit()

    # ── Procesar cargos a crédito ─────────────────────────────────────────────
    if pagos_credito_in:
        cliente_obj = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if cliente_obj:
            for p in pagos_procesados:
                if p["metodo_pago"] == "credito":
                    monto_cargo = float(p["monto_original"])
                    # En Bs, convertir a USD para descontar del saldo (saldo está en USD)
                    if moneda_venta == "Bs" and tasa_bcv > 0:
                        monto_cargo = round(monto_cargo / tasa_bcv, DECIMALES_USD)
                    cliente_obj.saldo_credito = round(
                        float(cliente_obj.saldo_credito or 0) - monto_cargo, 2
                    )
                    db.add(AbonoCredito(
                        cliente_id  = int(cliente_id),
                        venta_id    = venta.id,
                        monto       = -monto_cargo,   # negativo = cargo (deuda)
                        observacion = f"Venta #{venta.id}",
                        usuario     = usuario,
                    ))
            db.commit()

    # Excepciones
    for motivo in motivos_autorizacion:
        if "divisa" in motivo.lower():
            _registrar_excepcion(db, venta.id, "descuento_divisa", usuario)
        elif "sin stock" in motivo.lower():
            _registrar_excepcion(db, venta.id, "venta_sin_stock", usuario)
        elif "descuento en producto" in motivo.lower():
            _registrar_excepcion(db, venta.id, "descuento_producto", usuario)
        elif "descuento global" in motivo.lower():
            _registrar_excepcion(db, venta.id, "descuento_total", usuario)
    db.commit()

    # ── Comisiones de vendedor (no interrumpe la venta si falla) ─────────────
    try:
        from rutas.vendedores import calcular_porcentaje_comision
        perfil_vendedor = db.query(VendedorPerfil).join(
            __import__('models').Usuario,
            VendedorPerfil.usuario_id == __import__('models').Usuario.id
        ).filter(
            __import__('models').Usuario.nombre == usuario,
            VendedorPerfil.activo == True,
        ).first()

        if perfil_vendedor:
            detalles_guardados = db.query(DetalleVenta).filter(
                DetalleVenta.venta_id == venta.id
            ).all()
            for det in detalles_guardados:
                prod = db.query(Producto).filter(Producto.id == det.producto_id).first()
                if not prod:
                    continue
                pct, tipo_regla = calcular_porcentaje_comision(perfil_vendedor.id, prod, db)
                if pct <= 0:
                    continue
                monto_usd  = float(det.precio_unitario or 0) * float(det.cantidad or 0)
                db.add(ComisionVenta(
                    venta_id            = venta.id,
                    vendedor_id         = perfil_vendedor.id,
                    detalle_venta_id    = det.id,
                    producto_id         = prod.id,
                    monto_venta_usd     = round(monto_usd, 4),
                    porcentaje_aplicado = pct,
                    monto_comision      = round(monto_usd * pct, 4),
                    tipo_regla          = tipo_regla,
                ))
            db.commit()
    except Exception:
        db.rollback()
    # ── fin comisiones ────────────────────────────────────────────────────────

    return {
        "ok":               True,
        "venta_id":         venta.id,
        "moneda_venta":     moneda_venta,
        "tipo_precio_usado":tipo_precio_final,
        "tasa_bcv":         tasa_bcv,
        "tasa_binance":     tasa_binance,
        "factor":           factor,
        "subtotal":         subtotal,
        "descuento":        descuento,
        "total":            total,
        "total_abonado":    total_abonado,
        "saldo_pendiente":  max(saldo_pendiente, 0),
        "exceso":           exceso,
        "pagos":            pagos_procesados,
    }


@router.get("/productos-frecuentes")
def productos_frecuentes(n: int = 10, db: Session = Depends(get_db)):
    """Top N productos más vendidos por cantidad. Sin restricción de rol."""
    rows = (
        db.query(DetalleVenta.producto_id, sqlfunc.sum(DetalleVenta.cantidad).label("total"))
        .group_by(DetalleVenta.producto_id)
        .order_by(sqlfunc.sum(DetalleVenta.cantidad).desc())
        .limit(n)
        .all()
    )
    resultado = []
    for r in rows:
        p = db.query(Producto).filter(Producto.id == r.producto_id, Producto.activo == True).first()
        if p:
            resultado.append({"id": p.id, "nombre": p.nombre, "codigo": p.codigo or ""})
    return resultado
