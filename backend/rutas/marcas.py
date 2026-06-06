from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Marca
from rutas.usuarios import require_admin

router = APIRouter(prefix="/marcas", tags=["marcas"])


@router.get("/")
def listar_marcas(db: Session = Depends(get_db)):
    return db.query(Marca).filter(Marca.activa == True).order_by(Marca.nombre).all()


@router.post("/")
def crear_marca(
    datos: dict,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    existente = db.query(Marca).filter(Marca.nombre == nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe una marca con ese nombre")
    m = Marca(nombre=nombre)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.put("/{marca_id}")
def editar_marca(
    marca_id: int,
    datos: dict,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    m = db.query(Marca).filter(Marca.id == marca_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    nombre = (datos.get("nombre") or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    duplicado = db.query(Marca).filter(Marca.nombre == nombre, Marca.id != marca_id).first()
    if duplicado:
        raise HTTPException(status_code=400, detail="Ya existe una marca con ese nombre")
    m.nombre = nombre
    db.commit()
    db.refresh(m)
    return m
