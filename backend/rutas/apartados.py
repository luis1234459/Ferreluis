import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from database import get_db
from models import (
    Apartado, DetalleApartado, AbonoApartado,
    Producto, VarianteProducto, MovimientoBancario,
    Venta, DetalleVenta, PagoVenta,
    METODOS_USD, METODOS_BS, TOLERANCIA,
)
from rutas.auth import resolver_sede_activa, ajustar_existencia_sede
from rutas.ventas import _moneda_de_metodo, _calcular_equivalente

router = APIRouter(tags=["apartados"])

METODOS_CIERRE_APARTADO = (METODOS_USD | METODOS_BS) - {"credito"}


def _numero(db: Session) -> str:
    ultimo = db.query(Apartado).order_by(Apartado.id.desc()).first()
    n = (ultimo.id + 1) if ultimo else 1
    return f"APT-{n:04d}"


def _serializar(apt: Apartado, db: Session) -> dict:
    detalles = db.query(DetalleApartado).filter(DetalleApartado.apartado_id == apt.id).all()
    abonos   = db.query(AbonoApartado).filter(AbonoApartado.apartado_id == apt.id).order_by(AbonoApartado.fecha).all()
    return {
        "id":               apt.id,
        "numero":           apt.numero,
        "vendedor":         apt.vendedor,
        "cliente_nombre":   apt.cliente_nombre,
        "cliente_telefono": apt.cliente_telefono,
        "fecha_creacion":   apt.fecha_creacion.isoformat() if apt.fecha_creacion else None,
        "fecha_maxima":     apt.fecha_maxima.isoformat() if apt.fecha_maxima else None,
        "cuotas":           apt.cuotas,
        "monto_cuota":      apt.monto_cuota,
        "total_usd":        round(float(apt.total_usd or 0), 2),
        "abonado_usd":      round(float(apt.abonado_usd or 0), 2),
        "estado":           apt.estado,
        "observacion":      apt.observacion,
        "moneda":           apt.moneda,
        "tasa_bcv":         apt.tasa_bcv,
        "sede_id":          apt.sede_id,
        "detalles": [
            {
                "id":                 d.id,
                "producto_id":        d.producto_id,
                "variante_id":        d.variante_id,
                "nombre_producto":    d.nombre_producto,
                "cantidad":           d.cantidad,
                "precio_unitario_usd": d.precio_unitario_usd,
                "subtotal_usd":       d.subtotal_usd,
            }
            for d in detalles
        ],
        "abonos": [
            {
                "id":              a.id,
                "monto":           a.monto,
                "moneda_pago":     a.moneda_pago,
                "metodo_pago":     a.metodo_pago,
                "fecha":           a.fecha.isoformat() if a.fecha else None,
                "registrado_por":  a.registrado_por,
                "referencia":      a.referencia,
            }
            for a in abonos
        ],
    }


# ── POST /apartados/ ─────────────────────────────────────────────────────────

@router.post("/")
def crear_apartado(
    datos: dict,
    db: Session = Depends(get_db),
    x_usuario_nombre: Optional[str] = Header(None),
    sede_activa: int = Depends(resolver_sede_activa),
):
    if sede_activa is None:
        raise HTTPException(status_code=400,
                            detail="Debe seleccionar una sede específica para crear el apartado")

    productos_data = datos.get("productos", [])
    if not productos_data:
        raise HTTPException(status_code=400, detail="Debe incluir al menos un producto")

    total = sum(float(p.get("precio_usd", 0)) * int(p.get("cantidad", 1)) for p in productos_data)

    apt = Apartado(
        numero           = _numero(db),
        vendedor         = x_usuario_nombre or datos.get("vendedor", ""),
        cliente_nombre   = datos.get("cliente_nombre"),
        cliente_telefono = datos.get("cliente_telefono"),
        fecha_maxima     = datetime.fromisoformat(datos["fecha_maxima"]) if datos.get("fecha_maxima") else None,
        cuotas           = datos.get("cuotas"),
        monto_cuota      = datos.get("monto_cuota"),
        total_usd        = round(total, 2),
        observacion      = datos.get("observacion"),
        moneda           = datos.get("moneda", "USD"),
        tasa_bcv         = datos.get("tasa_bcv"),
        sede_id          = sede_activa,
    )
    db.add(apt)
    db.flush()

    for p in productos_data:
        cantidad = int(p.get("cantidad", 1))
        precio   = float(p.get("precio_usd", 0))
        db.add(DetalleApartado(
            apartado_id         = apt.id,
            producto_id         = p.get("producto_id"),
            variante_id         = p.get("variante_id"),
            nombre_producto     = p.get("nombre", ""),
            cantidad            = cantidad,
            precio_unitario_usd = precio,
            subtotal_usd        = round(precio * cantidad, 2),
        ))
        prod_id   = p.get("producto_id")
        var_id    = p.get("variante_id")
        if var_id:
            var = db.query(VarianteProducto).filter(VarianteProducto.id == var_id).first()
            if var:
                var.stock = (var.stock or 0) - cantidad
        elif prod_id:
            prod = db.query(Producto).filter(Producto.id == prod_id).first()
            if prod:
                prod.stock = (prod.stock or 0) - cantidad
                ajustar_existencia_sede(
                    db, prod.id, sede_activa,
                    tipo="restar", valor=cantidad,
                    tiene_variante_activa=False,
                )

    db.commit()
    db.refresh(apt)
    return _serializar(apt, db)


# ── GET /apartados/ ──────────────────────────────────────────────────────────

@router.get("/")
def listar_apartados(
    db: Session = Depends(get_db),
    x_usuario_nombre: Optional[str] = Header(None),
    x_usuario_rol:    Optional[str] = Header(None),
    estado: Optional[str] = None,
):
    q = db.query(Apartado)
    if x_usuario_rol not in ("admin", "gestionador"):
        q = q.filter(Apartado.vendedor == (x_usuario_nombre or ""))
    if estado:
        q = q.filter(Apartado.estado == estado)
    apts = q.order_by(Apartado.fecha_creacion.desc()).all()
    return [_serializar(a, db) for a in apts]


# ── GET /apartados/buscar-rapido ─────────────────────────────────────────────

@router.get("/buscar-rapido")
def buscar_rapido(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    x_usuario_nombre: Optional[str] = Header(None),
    x_usuario_rol:    Optional[str] = Header(None),
):
    """
    Autocomplete para cerrar apartados desde Ventas. Incluye "activo" y
    también "pagado" (100% abonado por /abono) siempre que todavía no se
    haya convertido a Venta — un "pagado" ya convertido no debe volver a
    aparecer (evitaría reconvertirlo por accidente). Apartados "pagado" de
    antes de este deploy requieren el backfill de
    backend/backfill_apartados_convertidos.py para no reaparecer aquí.
    """
    like = f"%{q}%"
    query = db.query(Apartado).filter(
        or_(
            Apartado.estado == "activo",
            (Apartado.estado == "pagado") & (Apartado.convertido_a_venta == False),  # noqa: E712
        ),
        or_(Apartado.numero.ilike(like), Apartado.cliente_nombre.ilike(like)),
    )
    if x_usuario_rol not in ("admin", "gestionador"):
        query = query.filter(Apartado.vendedor == (x_usuario_nombre or ""))
    apts = query.order_by(Apartado.fecha_creacion.desc()).limit(8).all()
    return [_serializar(a, db) for a in apts]


# ── GET /apartados/{id} ──────────────────────────────────────────────────────

@router.get("/{apt_id}")
def obtener_apartado(apt_id: int, db: Session = Depends(get_db)):
    apt = db.query(Apartado).filter(Apartado.id == apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Apartado no encontrado")
    return _serializar(apt, db)


# ── POST /apartados/{id}/abono ───────────────────────────────────────────────

@router.post("/{apt_id}/abono")
def registrar_abono(
    apt_id: int,
    datos: dict,
    db: Session = Depends(get_db),
    x_usuario_nombre: Optional[str] = Header(None),
):
    apt = db.query(Apartado).filter(Apartado.id == apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Apartado no encontrado")
    if apt.estado == "cancelado":
        raise HTTPException(status_code=400, detail="El apartado está cancelado")

    monto      = float(datos.get("monto", 0))
    moneda     = datos.get("moneda_pago", "USD")
    tasa       = float(apt.tasa_bcv or 1)
    monto_usd  = round(monto / tasa, 4) if moneda == "Bs" else monto

    db.add(AbonoApartado(
        apartado_id   = apt_id,
        monto         = monto,
        moneda_pago   = moneda,
        metodo_pago   = datos.get("metodo_pago", "efectivo_usd"),
        cuenta_destino_id = datos.get("cuenta_destino_id"),
        registrado_por = x_usuario_nombre or "vendedor",
        referencia    = datos.get("referencia"),
    ))

    apt.abonado_usd = round(float(apt.abonado_usd or 0) + monto_usd, 2)
    if apt.abonado_usd >= apt.total_usd - 0.01:
        apt.estado = "pagado"

    cuenta_id = datos.get("cuenta_destino_id")
    if cuenta_id:
        db.add(MovimientoBancario(
            tipo              = "ingreso_externo",
            cuenta_destino_id = cuenta_id,
            monto             = monto,
            moneda            = moneda,
            tasa_cambio       = tasa if moneda == "Bs" else None,
            monto_convertido  = monto_usd if moneda == "Bs" else None,
            referencia        = datos.get("referencia"),
            concepto          = f"Abono apartado {apt.numero} — {apt.cliente_nombre or ''}",
            registrado_por    = x_usuario_nombre or "vendedor",
        ))

    db.commit()
    return _serializar(apt, db)


# ── POST /apartados/{id}/cancelar ───────────────────────────────────────────

@router.post("/{apt_id}/cancelar")
def cancelar_apartado(apt_id: int, db: Session = Depends(get_db)):
    apt = db.query(Apartado).filter(Apartado.id == apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Apartado no encontrado")
    if apt.estado != "activo":
        raise HTTPException(status_code=400, detail=f"No se puede cancelar un apartado en estado '{apt.estado}'")

    detalles = db.query(DetalleApartado).filter(DetalleApartado.apartado_id == apt_id).all()
    for d in detalles:
        if d.variante_id:
            var = db.query(VarianteProducto).filter(VarianteProducto.id == d.variante_id).first()
            if var:
                var.stock = (var.stock or 0) + d.cantidad
        elif d.producto_id:
            prod = db.query(Producto).filter(Producto.id == d.producto_id).first()
            if prod:
                prod.stock = (prod.stock or 0) + d.cantidad
                ajustar_existencia_sede(
                    db, prod.id, apt.sede_id,
                    tipo="agregar", valor=d.cantidad,
                    tiene_variante_activa=False,
                )

    apt.estado = "cancelado"
    db.commit()
    return {"ok": True}


# ── POST /apartados/{id}/convertir-venta ────────────────────────────────────

@router.post("/{apt_id}/convertir-venta")
def convertir_a_venta(
    apt_id: int,
    datos: dict = {},
    db: Session = Depends(get_db),
    x_usuario_nombre: Optional[str] = Header(None),
):
    apt = db.query(Apartado).filter(Apartado.id == apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Apartado no encontrado")
    if apt.estado not in ("activo", "pagado"):
        raise HTTPException(status_code=400, detail=f"Estado inválido para convertir: '{apt.estado}'")

    if apt.convertido_a_venta:
        raise HTTPException(status_code=400, detail="Este apartado ya fue convertido a una venta")

    tasa      = float(apt.tasa_bcv or 1)
    usuario   = x_usuario_nombre or apt.vendedor
    saldo_usd = round(float(apt.total_usd or 0) - float(apt.abonado_usd or 0), 2)
    pagos_in  = (datos or {}).get("pagos") or []

    # ── Cobro del saldo pendiente (opcional, no rompe el flujo viejo) ────────
    pagos_procesados = []
    if pagos_in and saldo_usd > 0.01:
        saldo_en_moneda    = saldo_usd if apt.moneda == "USD" else round(saldo_usd * tasa, 2)
        cubierto_en_moneda = 0.0

        for i, pago in enumerate(pagos_in):
            metodo     = pago.get("metodo")
            monto      = float(pago.get("monto", 0))
            referencia = pago.get("referencia", "") or ""
            if metodo not in METODOS_CIERRE_APARTADO:
                raise HTTPException(status_code=400, detail=f"Pago #{i+1}: método inválido '{metodo}'")
            if monto <= 0:
                raise HTTPException(status_code=400, detail=f"Pago #{i+1} ({metodo}): monto debe ser > 0")

            moneda_pago  = _moneda_de_metodo(metodo)
            equiv_moneda = _calcular_equivalente(monto, moneda_pago, apt.moneda, tasa)
            equiv_usd    = _calcular_equivalente(monto, moneda_pago, "USD", tasa)
            cubierto_en_moneda = round(cubierto_en_moneda + equiv_moneda, 2)

            pagos_procesados.append({
                "metodo_pago":              metodo,
                "moneda_pago":              moneda_pago,
                "monto_original":           monto,
                "monto_equivalente_moneda": equiv_moneda,
                "monto_equivalente_usd":    equiv_usd,
                "referencia":               referencia,
                "cuenta_destino_id":        pago.get("cuenta_destino_id"),
            })

        falta = round(saldo_en_moneda - cubierto_en_moneda, 2)
        if falta > TOLERANCIA:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Pago insuficiente para cerrar el apartado. "
                    f"Saldo: {saldo_en_moneda:.2f} {apt.moneda} | "
                    f"Cubierto: {cubierto_en_moneda:.2f} {apt.moneda} | "
                    f"Falta: {falta:.2f} {apt.moneda}"
                )
            )

        for p in pagos_procesados:
            db.add(AbonoApartado(
                apartado_id    = apt.id,
                monto          = p["monto_original"],
                moneda_pago    = p["moneda_pago"],
                metodo_pago    = p["metodo_pago"],
                registrado_por = usuario,
                referencia     = p["referencia"],
            ))
            apt.abonado_usd = round(float(apt.abonado_usd or 0) + p["monto_equivalente_usd"], 2)

    # ── Crear la Venta a partir del apartado (igual que siempre) ─────────────
    venta = Venta(
        fecha            = datetime.utcnow(),
        usuario          = usuario,
        moneda_venta     = apt.moneda,
        tipo_precio_usado= "referencial",
        subtotal         = apt.total_usd,
        descuento        = 0,
        total            = apt.total_usd if apt.moneda == "USD" else round(apt.total_usd * tasa, 2),
        tasa_bcv         = tasa,
        estado           = "pagado",
        sede_id          = apt.sede_id,
        apartado_id      = apt.id,
    )
    db.add(venta)
    db.flush()

    detalles = db.query(DetalleApartado).filter(DetalleApartado.apartado_id == apt_id).all()
    for d in detalles:
        db.add(DetalleVenta(
            venta_id          = venta.id,
            producto_id       = d.producto_id,
            variante_id       = d.variante_id,
            cantidad          = d.cantidad,
            tipo_precio_usado = "referencial",
            precio_base_snap  = d.precio_unitario_usd,
            precio_referencial_snap = d.precio_unitario_usd,
            precio_unitario   = d.precio_unitario_usd,
            subtotal          = d.subtotal_usd if apt.moneda == "USD" else round(d.subtotal_usd * tasa, 2),
        ))

    if pagos_procesados:
        ahora = datetime.utcnow()
        for p in pagos_procesados:
            db.add(PagoVenta(
                venta_id          = venta.id,
                metodo_pago       = p["metodo_pago"],
                moneda_pago       = p["moneda_pago"],
                monto_original    = p["monto_original"],
                tasa_cambio       = tasa,
                monto_equivalente = p["monto_equivalente_moneda"],
                moneda_venta      = apt.moneda,
                referencia        = p["referencia"],
                fecha_hora        = ahora,
                usuario           = usuario,
                cuenta_destino_id = p["cuenta_destino_id"],
            ))
        venta.total_abonado   = venta.total
        venta.saldo_pendiente = 0
        venta.exceso          = max(round(cubierto_en_moneda - saldo_en_moneda, 2), 0)

    apt.estado = "pagado"
    apt.convertido_a_venta = True
    db.commit()
    return {"ok": True, "venta_id": venta.id}
