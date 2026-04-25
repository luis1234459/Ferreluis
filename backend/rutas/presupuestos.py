from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import (
    Presupuesto, DetallePresupuesto,
    Producto, VarianteProducto, TasaCambio,
    Venta, DetalleVenta, VentaCliente,
)
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter(prefix="/presupuestos", tags=["presupuestos"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _numero_siguiente(db: Session) -> str:
    ultimo = db.query(Presupuesto).order_by(Presupuesto.id.desc()).first()
    n = (ultimo.id + 1) if ultimo else 1
    return f"PRE-{n:04d}"


def _serializar(p: Presupuesto, db: Session) -> dict:
    detalles = db.query(DetallePresupuesto).filter(
        DetallePresupuesto.presupuesto_id == p.id
    ).all()
    return {
        "id":               p.id,
        "numero":           p.numero,
        "cliente_id":       p.cliente_id,
        "cliente_nombre":   p.cliente_nombre,
        "cliente_telefono": p.cliente_telefono,
        "usuario":          p.usuario,
        "fecha":            p.fecha.isoformat() if p.fecha else None,
        "fecha_vencimiento":p.fecha_vencimiento.isoformat() if p.fecha_vencimiento else None,
        "subtotal":         round(float(p.subtotal or 0), 2),
        "descuento":        round(float(p.descuento or 0), 2),
        "total":            round(float(p.total or 0), 2),
        "moneda":           p.moneda,
        "tasa_bcv":         p.tasa_bcv,
        "estado":           p.estado,
        "observacion":      p.observacion,
        "venta_id":         p.venta_id,
        "productos": [
            {
                "id":              d.id,
                "producto_id":     d.producto_id,
                "variante_id":     d.variante_id,
                "nombre_producto": d.nombre_producto,
                "cantidad":        d.cantidad,
                "precio_unitario": d.precio_unitario,
                "subtotal":        d.subtotal,
            }
            for d in detalles
        ],
    }


def _marcar_vencidos(db: Session):
    """Marca como vencidos todos los presupuestos pendientes que pasaron su fecha."""
    ahora = datetime.now()
    vencidos = db.query(Presupuesto).filter(
        Presupuesto.estado == "pendiente",
        Presupuesto.fecha_vencimiento < ahora,
    ).all()
    for p in vencidos:
        p.estado = "vencido"
    if vencidos:
        db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/vencidos/actualizar")
def actualizar_vencidos(db: Session = Depends(get_db)):
    ahora = datetime.now()
    pendientes = db.query(Presupuesto).filter(
        Presupuesto.estado == "pendiente",
        Presupuesto.fecha_vencimiento < ahora,
    ).all()
    for p in pendientes:
        p.estado = "vencido"
    db.commit()
    return {"actualizados": len(pendientes)}


@router.get("/")
def listar_presupuestos(
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
):
    _marcar_vencidos(db)
    q = db.query(Presupuesto)
    if estado:
        q = q.filter(Presupuesto.estado == estado)
    presupuestos = q.order_by(Presupuesto.fecha.desc()).all()
    return [_serializar(p, db) for p in presupuestos]


@router.post("/")
def crear_presupuesto(datos: dict, db: Session = Depends(get_db)):
    tasa_rec = db.query(TasaCambio).order_by(TasaCambio.fecha.desc()).first()
    tasa_bcv = tasa_rec.tasa if tasa_rec else 1.0

    productos_data = datos.get("productos", [])
    subtotal = sum(
        float(item.get("precio_unitario", 0)) * float(item.get("cantidad", 0))
        for item in productos_data
    )
    descuento = float(datos.get("descuento", 0))
    total     = subtotal - descuento

    p = Presupuesto(
        numero           = _numero_siguiente(db),
        cliente_id       = datos.get("cliente_id"),
        cliente_nombre   = datos.get("cliente_nombre"),
        cliente_telefono = datos.get("cliente_telefono"),
        usuario          = datos.get("usuario", "admin"),
        fecha            = datetime.now(),
        fecha_vencimiento= (
            datetime.fromisoformat(datos["fecha_vencimiento"])
            if datos.get("fecha_vencimiento")
            else datetime.now() + timedelta(hours=24)
        ),
        subtotal         = round(subtotal, 2),
        descuento        = round(descuento, 2),
        total            = round(total, 2),
        moneda           = datos.get("moneda", "USD"),
        tasa_bcv         = tasa_bcv,
        estado           = "pendiente",
        observacion      = datos.get("observacion"),
    )
    db.add(p)
    db.flush()

    for item in productos_data:
        cant  = float(item.get("cantidad", 0))
        precio = float(item.get("precio_unitario", 0))
        vid   = item.get("variante_id")
        db.add(DetallePresupuesto(
            presupuesto_id  = p.id,
            producto_id     = item.get("producto_id"),
            variante_id     = int(vid) if vid else None,
            nombre_producto = item.get("nombre_producto", ""),
            cantidad        = cant,
            precio_unitario = precio,
            subtotal        = round(cant * precio, 2),
        ))

    db.commit()
    db.refresh(p)
    return _serializar(p, db)


@router.get("/{presupuesto_id}")
def obtener_presupuesto(presupuesto_id: int, db: Session = Depends(get_db)):
    p = db.query(Presupuesto).filter(Presupuesto.id == presupuesto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return _serializar(p, db)


@router.put("/{presupuesto_id}/aprobar")
def aprobar_presupuesto(presupuesto_id: int, db: Session = Depends(get_db)):
    p = db.query(Presupuesto).filter(Presupuesto.id == presupuesto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    if p.estado == "vencido":
        raise HTTPException(status_code=400, detail="El presupuesto ha vencido")
    if p.estado in ("convertido", "aprobado"):
        raise HTTPException(status_code=400, detail=f"El presupuesto ya está {p.estado}")
    p.estado = "aprobado"
    db.commit()
    return _serializar(p, db)


@router.post("/{presupuesto_id}/convertir")
def convertir_a_venta(
    presupuesto_id: int,
    datos: dict = {},
    db: Session = Depends(get_db),
):
    p = db.query(Presupuesto).filter(Presupuesto.id == presupuesto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    if p.estado == "convertido":
        raise HTTPException(status_code=400, detail="El presupuesto ya fue convertido")
    if p.estado == "vencido" or (p.fecha_vencimiento and p.fecha_vencimiento < datetime.now()):
        raise HTTPException(status_code=400, detail="El presupuesto ha vencido")

    tasa_rec     = db.query(TasaCambio).order_by(TasaCambio.fecha.desc()).first()
    tasa_bcv     = tasa_rec.tasa         if tasa_rec else 1.0
    tasa_binance = tasa_rec.tasa_binance if tasa_rec else None
    factor       = (tasa_binance / tasa_bcv) if (tasa_binance and tasa_bcv) else 1.0

    venta = Venta(
        fecha            = datetime.now(),
        usuario          = datos.get("usuario", p.usuario),
        moneda_venta     = p.moneda,
        tipo_precio_usado= "base",
        subtotal         = p.subtotal,
        descuento        = p.descuento,
        total            = p.total,
        tasa_bcv         = tasa_bcv,
        tasa_binance     = tasa_binance,
        factor_cambio    = factor,
        total_abonado    = 0,
        saldo_pendiente  = p.total,
        exceso           = 0,
        estado           = "pendiente",
        observacion      = f"Convertido de {p.numero}",
    )
    db.add(venta)
    db.flush()

    detalles = db.query(DetallePresupuesto).filter(
        DetallePresupuesto.presupuesto_id == p.id
    ).all()

    for d in detalles:
        db.add(DetalleVenta(
            venta_id               = venta.id,
            producto_id            = d.producto_id,
            variante_id            = d.variante_id,
            cantidad               = int(d.cantidad),
            tipo_precio_usado      = "base",
            precio_base_snap       = d.precio_unitario,
            precio_referencial_snap= d.precio_unitario,
            precio_unitario        = d.precio_unitario,
            subtotal               = d.subtotal,
        ))
        if d.variante_id:
            var = db.query(VarianteProducto).filter(VarianteProducto.id == d.variante_id).first()
            if var:
                var.stock = max(0, float(var.stock or 0) - int(d.cantidad))
        elif d.producto_id:
            prod = db.query(Producto).filter(Producto.id == d.producto_id).first()
            if prod:
                prod.stock = max(0, prod.stock - int(d.cantidad))

    if p.cliente_id:
        db.add(VentaCliente(venta_id=venta.id, cliente_id=p.cliente_id))

    p.estado  = "convertido"
    p.venta_id = venta.id
    db.commit()

    return {"venta_id": venta.id, "numero": p.numero, "mensaje": "Convertido exitosamente"}
