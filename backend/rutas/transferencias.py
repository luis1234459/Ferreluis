from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from database import get_db
from models import TransferenciaSede, TransferenciaDetalle, Sede, Producto, Usuario, ExistenciaSede
from rutas.usuarios import require_admin
from rutas.auth import ajustar_existencia_sede

router = APIRouter(prefix="/transferencias", tags=["transferencias"])


def _existencia(db: Session, producto_id: int, sede_id: int) -> float:
    es = db.query(ExistenciaSede).filter(
        ExistenciaSede.producto_id == producto_id,
        ExistenciaSede.sede_id == sede_id,
    ).first()
    return float(es.existencia) if es else 0.0


def _validar_disponibilidad(db: Session, producto_id: int, sede_id: int, cantidad: float):
    disponible = _existencia(db, producto_id, sede_id)
    if cantidad > disponible:
        prod = db.query(Producto).filter(Producto.id == producto_id).first()
        nombre = prod.nombre if prod else f"Producto #{producto_id}"
        raise HTTPException(
            status_code=400,
            detail=f"No hay suficiente existencia de '{nombre}' en la sede de origen (disponible: {disponible})",
        )


def _serializar(t: TransferenciaSede, db: Session) -> dict:
    detalles = db.query(TransferenciaDetalle).filter(TransferenciaDetalle.transferencia_id == t.id).all()
    origen  = db.query(Sede).filter(Sede.id == t.sede_origen_id).first()
    destino = db.query(Sede).filter(Sede.id == t.sede_destino_id).first()
    usuario = db.query(Usuario).filter(Usuario.id == t.usuario_id).first() if t.usuario_id else None
    prod_ids = [d.producto_id for d in detalles]
    productos_map = {}
    if prod_ids:
        for p in db.query(Producto).filter(Producto.id.in_(prod_ids)).all():
            productos_map[p.id] = p.nombre
    return {
        "id":                  t.id,
        "sede_origen_id":      t.sede_origen_id,
        "sede_origen_nombre":  origen.nombre if origen else None,
        "sede_destino_id":     t.sede_destino_id,
        "sede_destino_nombre": destino.nombre if destino else None,
        "fecha":               t.fecha.isoformat() if t.fecha else None,
        "usuario_id":          t.usuario_id,
        "usuario_nombre":      usuario.nombre if usuario else None,
        "estado":              t.estado,
        "notas":               t.notas,
        "detalles": [
            {
                "id":               d.id,
                "producto_id":      d.producto_id,
                "nombre_producto":  productos_map.get(d.producto_id, f"Producto #{d.producto_id}"),
                "cantidad":         d.cantidad,
            }
            for d in detalles
        ],
    }


# ---------------------------------------------------------------------------
# POST /transferencias/ — crear (solo admin)
# ---------------------------------------------------------------------------

@router.post("/")
def crear_transferencia(
    datos: dict,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    sede_origen_id  = datos.get("sede_origen_id")
    sede_destino_id = datos.get("sede_destino_id")
    productos_data  = datos.get("productos", [])
    notas           = datos.get("notas")

    if not sede_origen_id or not sede_destino_id:
        raise HTTPException(status_code=400, detail="Debe indicar sede de origen y destino")
    sede_origen_id  = int(sede_origen_id)
    sede_destino_id = int(sede_destino_id)
    if sede_origen_id == sede_destino_id:
        raise HTTPException(status_code=400, detail="La sede de origen y destino no pueden ser la misma")
    if not db.query(Sede).filter(Sede.id == sede_origen_id).first():
        raise HTTPException(status_code=404, detail="Sede de origen no encontrada")
    if not db.query(Sede).filter(Sede.id == sede_destino_id).first():
        raise HTTPException(status_code=404, detail="Sede de destino no encontrada")
    if not productos_data:
        raise HTTPException(status_code=400, detail="Debe incluir al menos un producto")

    for p in productos_data:
        cantidad = float(p.get("cantidad", 0))
        if cantidad <= 0:
            raise HTTPException(status_code=400, detail="La cantidad debe ser mayor que cero")
        _validar_disponibilidad(db, p.get("producto_id"), sede_origen_id, cantidad)

    t = TransferenciaSede(
        sede_origen_id  = sede_origen_id,
        sede_destino_id = sede_destino_id,
        usuario_id      = admin.get("id"),
        estado          = "pendiente",
        notas           = notas,
    )
    db.add(t)
    db.flush()

    for p in productos_data:
        db.add(TransferenciaDetalle(
            transferencia_id = t.id,
            producto_id      = p["producto_id"],
            cantidad         = int(p["cantidad"]),
        ))

    db.commit()
    db.refresh(t)
    return _serializar(t, db)


# ---------------------------------------------------------------------------
# GET /transferencias/ — listado con filtros
# ---------------------------------------------------------------------------

@router.get("/")
def listar_transferencias(
    sede_origen_id:  Optional[int] = None,
    sede_destino_id: Optional[int] = None,
    estado:          Optional[str] = None,
    fecha_inicio:    Optional[str] = None,
    fecha_fin:       Optional[str] = None,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    q = db.query(TransferenciaSede)
    if sede_origen_id is not None:
        q = q.filter(TransferenciaSede.sede_origen_id == sede_origen_id)
    if sede_destino_id is not None:
        q = q.filter(TransferenciaSede.sede_destino_id == sede_destino_id)
    if estado:
        q = q.filter(TransferenciaSede.estado == estado)
    if fecha_inicio:
        try:
            fi = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_inicio inválido — usa YYYY-MM-DD")
        q = q.filter(TransferenciaSede.fecha >= fi)
    if fecha_fin:
        try:
            ff = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_fin inválido — usa YYYY-MM-DD")
        q = q.filter(TransferenciaSede.fecha <= ff)

    transferencias = q.order_by(TransferenciaSede.fecha.desc()).limit(200).all()
    return [_serializar(t, db) for t in transferencias]


# ---------------------------------------------------------------------------
# PUT /transferencias/{id}/confirmar — pendiente -> en_transito, descuenta origen
# ---------------------------------------------------------------------------

@router.put("/{transferencia_id}/confirmar")
def confirmar_transferencia(
    transferencia_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    t = db.query(TransferenciaSede).filter(TransferenciaSede.id == transferencia_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    if t.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"No se puede confirmar una transferencia en estado '{t.estado}'")

    detalles = db.query(TransferenciaDetalle).filter(TransferenciaDetalle.transferencia_id == t.id).all()
    for d in detalles:
        _validar_disponibilidad(db, d.producto_id, t.sede_origen_id, d.cantidad)

    for d in detalles:
        ajustar_existencia_sede(
            db, d.producto_id, t.sede_origen_id,
            tipo="restar", valor=d.cantidad, tiene_variante_activa=False,
        )

    t.estado = "en_transito"
    db.commit()
    return _serializar(t, db)


# ---------------------------------------------------------------------------
# PUT /transferencias/{id}/recibir — en_transito -> recibida, suma destino
# ---------------------------------------------------------------------------

@router.put("/{transferencia_id}/recibir")
def recibir_transferencia(
    transferencia_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    t = db.query(TransferenciaSede).filter(TransferenciaSede.id == transferencia_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    if t.estado != "en_transito":
        raise HTTPException(status_code=400, detail=f"No se puede recibir una transferencia en estado '{t.estado}'")

    detalles = db.query(TransferenciaDetalle).filter(TransferenciaDetalle.transferencia_id == t.id).all()
    for d in detalles:
        ajustar_existencia_sede(
            db, d.producto_id, t.sede_destino_id,
            tipo="agregar", valor=d.cantidad, tiene_variante_activa=False,
        )

    t.estado = "recibida"
    db.commit()
    return _serializar(t, db)


# ---------------------------------------------------------------------------
# PUT /transferencias/{id}/cancelar — revierte el descuento de origen si
# estaba en_transito; desde pendiente no hay nada que revertir.
# ---------------------------------------------------------------------------

@router.put("/{transferencia_id}/cancelar")
def cancelar_transferencia(
    transferencia_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    t = db.query(TransferenciaSede).filter(TransferenciaSede.id == transferencia_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    if t.estado not in ("pendiente", "en_transito"):
        raise HTTPException(status_code=400, detail=f"No se puede cancelar una transferencia en estado '{t.estado}'")

    if t.estado == "en_transito":
        detalles = db.query(TransferenciaDetalle).filter(TransferenciaDetalle.transferencia_id == t.id).all()
        for d in detalles:
            ajustar_existencia_sede(
                db, d.producto_id, t.sede_origen_id,
                tipo="agregar", valor=d.cantidad, tiene_variante_activa=False,
            )

    t.estado = "cancelada"
    db.commit()
    return _serializar(t, db)
