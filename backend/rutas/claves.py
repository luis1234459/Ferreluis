"""
Claves de Autorización — gestión de contraseñas para acciones protegidas.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ClaveAutorizacion
from rutas.usuarios import require_admin

router = APIRouter(prefix="/claves", tags=["claves"])

LABELS_ACCION = {
    "descuento":   "Descuento en venta / precio base",
    "stock":       "Venta sin stock",
    "devolucion":  "Devolución de productos",
    "precio_base": "Precio base (sin protección cambiaria)",
}


@router.get("/", dependencies=[Depends(require_admin)])
def listar_claves(db: Session = Depends(get_db)):
    claves = db.query(ClaveAutorizacion).order_by(ClaveAutorizacion.id).all()
    return [
        {
            "id":          c.id,
            "accion":      c.accion,
            "descripcion": c.descripcion or LABELS_ACCION.get(c.accion, c.accion),
            "tiene_clave": bool(c.clave),
        }
        for c in claves
    ]


@router.put("/{accion}", dependencies=[Depends(require_admin)])
def actualizar_clave(accion: str, datos: dict, db: Session = Depends(get_db)):
    nueva_clave = (datos.get("clave") or "").strip()
    if not nueva_clave:
        raise HTTPException(status_code=400, detail="La clave no puede estar vacía")

    obj = db.query(ClaveAutorizacion).filter(
        ClaveAutorizacion.accion == accion
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Acción '{accion}' no encontrada")

    obj.clave = nueva_clave
    db.commit()
    return {"ok": True, "accion": accion}


@router.post("/verificar")
def verificar_clave(datos: dict, db: Session = Depends(get_db)):
    accion = (datos.get("accion") or "").strip()
    clave  = (datos.get("clave")  or "").strip()

    if not accion or not clave:
        raise HTTPException(status_code=400, detail="accion y clave son requeridos")

    obj = db.query(ClaveAutorizacion).filter(
        ClaveAutorizacion.accion == accion
    ).first()
    if not obj:
        raise HTTPException(status_code=404, detail=f"Acción '{accion}' no encontrada")

    if obj.clave != clave:
        raise HTTPException(status_code=401, detail="Clave incorrecta")

    return {"ok": True, "accion": accion}