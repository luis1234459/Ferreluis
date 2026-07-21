from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Sede
from rutas.usuarios import get_current_user, require_admin

router = APIRouter(prefix="/sedes", tags=["sedes"])


def _sede_dict(s: Sede) -> dict:
    return {
        "id":        s.id,
        "codigo":    s.codigo,
        "nombre":    s.nombre,
        "ciudad":    s.ciudad,
        "direccion": s.direccion,
        "telefono":  s.telefono,
        "activa":    s.activa,
    }


@router.get("/")
def listar_sedes(db: Session = Depends(get_db), _: dict = Depends(get_current_user)):
    sedes = db.query(Sede).order_by(Sede.id).all()
    return [_sede_dict(s) for s in sedes]


@router.post("/")
def crear_sede(datos: dict, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    if not datos.get("codigo") or not datos.get("nombre"):
        raise HTTPException(status_code=400, detail="Código y nombre son obligatorios")
    if db.query(Sede).filter(Sede.codigo == datos["codigo"]).first():
        raise HTTPException(status_code=400, detail="Ya existe una sede con ese código")

    s = Sede(
        codigo    = datos["codigo"],
        nombre    = datos["nombre"],
        ciudad    = datos.get("ciudad"),
        direccion = datos.get("direccion"),
        telefono  = datos.get("telefono"),
        activa    = datos.get("activa", True),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _sede_dict(s)


@router.put("/{sede_id}")
def actualizar_sede(
    sede_id: int, datos: dict,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    s = db.query(Sede).filter(Sede.id == sede_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sede no encontrada")

    if "codigo" in datos:
        if db.query(Sede).filter(Sede.codigo == datos["codigo"], Sede.id != sede_id).first():
            raise HTTPException(status_code=400, detail="Ya existe una sede con ese código")
        s.codigo = datos["codigo"]
    if "nombre"    in datos: s.nombre    = datos["nombre"]
    if "ciudad"    in datos: s.ciudad    = datos["ciudad"]
    if "direccion" in datos: s.direccion = datos["direccion"]
    if "telefono"  in datos: s.telefono  = datos["telefono"]
    if "activa"    in datos: s.activa    = bool(datos["activa"])

    db.commit()
    db.refresh(s)
    return _sede_dict(s)
