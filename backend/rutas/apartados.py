import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import (
    Apartado, DetalleApartado, AbonoApartado,
    Producto, VarianteProducto, MovimientoBancario,
    Venta, DetalleVenta,
)

router = APIRouter(tags=["apartados"])


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
):
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

    apt.estado = "cancelado"
    db.commit()
    return {"ok": True}


# ── POST /apartados/{id}/convertir-venta ────────────────────────────────────

@router.post("/{apt_id}/convertir-venta")
def convertir_a_venta(
    apt_id: int,
    db: Session = Depends(get_db),
    x_usuario_nombre: Optional[str] = Header(None),
):
    apt = db.query(Apartado).filter(Apartado.id == apt_id).first()
    if not apt:
        raise HTTPException(status_code=404, detail="Apartado no encontrado")
    if apt.estado not in ("activo", "pagado"):
        raise HTTPException(status_code=400, detail=f"Estado inválido para convertir: '{apt.estado}'")

    tasa = float(apt.tasa_bcv or 1)
    venta = Venta(
        fecha            = datetime.utcnow(),
        usuario          = x_usuario_nombre or apt.vendedor,
        moneda_venta     = apt.moneda,
        tipo_precio_usado= "referencial",
        subtotal         = apt.total_usd,
        descuento        = 0,
        total            = apt.total_usd if apt.moneda == "USD" else round(apt.total_usd * tasa, 2),
        tasa_bcv         = tasa,
        estado           = "pagado",
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

    apt.estado = "pagado"
    db.commit()
    return {"ok": True, "venta_id": venta.id}
