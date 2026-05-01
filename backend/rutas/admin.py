"""
Módulo de mantenimiento administrativo.
Solo accesible por admin. Operaciones destructivas con confirmación.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import (
    Venta, DetalleVenta, PagoVenta, VentaCliente, ComisionVenta,
    OrdenCompra, DetalleOrdenCompra, RecepcionCompra, DetalleRecepcion,
    MovimientoBancario, CierreCaja, CuentaBancaria,
)
from rutas.usuarios import require_admin
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/estadisticas")
def estadisticas(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    """Resumen de datos actuales para mostrar antes de limpiar."""
    return {
        "ventas":              db.query(Venta).count(),
        "ordenes_compra":      db.query(OrdenCompra).count(),
        "recepciones":         db.query(RecepcionCompra).count(),
        "movimientos":         db.query(MovimientoBancario).count(),
        "cierres":             db.query(CierreCaja).count(),
    }


@router.delete("/limpiar-ventas")
def limpiar_ventas(datos: dict, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    """
    Elimina ventas y todos sus registros dependientes.
    Si se pasan fecha_desde y fecha_hasta, filtra por rango.
    Si preservar_ids es una lista de IDs, esos se excluyen.
    """
    fecha_desde   = datos.get("fecha_desde")
    fecha_hasta   = datos.get("fecha_hasta")
    preservar_ids = datos.get("preservar_ids", [])

    q = db.query(Venta)
    if fecha_desde:
        q = q.filter(Venta.fecha >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        q = q.filter(Venta.fecha <= datetime.fromisoformat(fecha_hasta))
    if preservar_ids:
        q = q.filter(~Venta.id.in_(preservar_ids))

    ventas = q.all()
    ids = [v.id for v in ventas]

    if not ids:
        return {"eliminadas": 0}

    db.query(ComisionVenta).filter(ComisionVenta.venta_id.in_(ids)).delete(synchronize_session=False)
    db.query(VentaCliente).filter(VentaCliente.venta_id.in_(ids)).delete(synchronize_session=False)
    db.query(PagoVenta).filter(PagoVenta.venta_id.in_(ids)).delete(synchronize_session=False)
    db.query(DetalleVenta).filter(DetalleVenta.venta_id.in_(ids)).delete(synchronize_session=False)
    db.query(Venta).filter(Venta.id.in_(ids)).delete(synchronize_session=False)
    db.commit()

    return {"eliminadas": len(ids)}


@router.delete("/limpiar-compras")
def limpiar_compras(datos: dict, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    """Elimina órdenes de compra y todos sus registros dependientes."""
    fecha_desde   = datos.get("fecha_desde")
    fecha_hasta   = datos.get("fecha_hasta")
    preservar_ids = datos.get("preservar_ids", [])

    q = db.query(OrdenCompra)
    if fecha_desde:
        q = q.filter(OrdenCompra.fecha_creacion >= datetime.fromisoformat(fecha_desde))
    if fecha_hasta:
        q = q.filter(OrdenCompra.fecha_creacion <= datetime.fromisoformat(fecha_hasta))
    if preservar_ids:
        q = q.filter(~OrdenCompra.id.in_(preservar_ids))

    ordenes = q.all()
    ids = [o.id for o in ordenes]

    if not ids:
        return {"eliminadas": 0}

    rec_ids = [r.id for r in db.query(RecepcionCompra).filter(RecepcionCompra.orden_id.in_(ids)).all()]
    if rec_ids:
        db.query(DetalleRecepcion).filter(DetalleRecepcion.recepcion_id.in_(rec_ids)).delete(synchronize_session=False)
        db.query(RecepcionCompra).filter(RecepcionCompra.id.in_(rec_ids)).delete(synchronize_session=False)
    db.query(DetalleOrdenCompra).filter(DetalleOrdenCompra.orden_id.in_(ids)).delete(synchronize_session=False)
    db.query(OrdenCompra).filter(OrdenCompra.id.in_(ids)).delete(synchronize_session=False)
    db.commit()

    return {"eliminadas": len(ids)}


@router.delete("/limpiar-movimientos")
def limpiar_movimientos(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    """Elimina todos los movimientos bancarios."""
    count = db.query(MovimientoBancario).count()
    db.query(MovimientoBancario).delete(synchronize_session=False)
    db.commit()
    return {"eliminados": count}


@router.delete("/limpiar-cierres")
def limpiar_cierres(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    """Elimina todos los cierres de caja."""
    count = db.query(CierreCaja).count()
    db.query(CierreCaja).delete(synchronize_session=False)
    db.commit()
    return {"eliminados": count}


@router.put("/ajustar-cuenta/{cuenta_id}")
def ajustar_cuenta(
    cuenta_id: int,
    datos: dict,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    """Ajusta el saldo o datos de una cuenta bancaria."""
    cuenta = db.query(CuentaBancaria).filter(CuentaBancaria.id == cuenta_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    if "nombre" in datos:
        cuenta.nombre = datos["nombre"]
    db.commit()
    return {"ok": True, "cuenta_id": cuenta_id}
