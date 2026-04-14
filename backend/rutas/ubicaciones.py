from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models import Area, Pasillo, Estante, UbicacionProducto, Producto
from rutas.usuarios import require_admin

router = APIRouter(prefix="/ubicaciones", tags=["ubicaciones"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AreaIn(BaseModel):
    nombre: str

class PasilloIn(BaseModel):
    area_id: int
    numero: int

class EstanteIn(BaseModel):
    pasillo_id: int
    numero: int

class UbicacionIn(BaseModel):
    producto_id: int
    area_id: int
    pasillo_id: int
    estante_id: int
    nivel: int
    cantidad: float = 0


# ── Áreas ─────────────────────────────────────────────────────────────────────

@router.get("/areas")
def listar_areas(db: Session = Depends(get_db), _=Depends(require_admin)):
    return db.query(Area).filter(Area.activa == True).all()


@router.post("/areas")
def crear_area(body: AreaIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    area = Area(nombre=body.nombre.strip())
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


@router.put("/areas/{area_id}")
def editar_area(area_id: int, body: AreaIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(404, "Área no encontrada")
    area.nombre = body.nombre.strip()
    db.commit()
    db.refresh(area)
    return area


@router.delete("/areas/{area_id}")
def eliminar_area(area_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    area = db.query(Area).filter(Area.id == area_id).first()
    if not area:
        raise HTTPException(404, "Área no encontrada")
    area.activa = False
    db.commit()
    return {"ok": True}


# ── Pasillos ──────────────────────────────────────────────────────────────────

@router.get("/pasillos")
def listar_pasillos(area_id: Optional[int] = None, db: Session = Depends(get_db), _=Depends(require_admin)):
    q = db.query(Pasillo).filter(Pasillo.activo == True)
    if area_id:
        q = q.filter(Pasillo.area_id == area_id)
    return q.order_by(Pasillo.numero).all()


@router.post("/pasillos")
def crear_pasillo(body: PasilloIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    pasillo = Pasillo(area_id=body.area_id, numero=body.numero)
    db.add(pasillo)
    db.commit()
    db.refresh(pasillo)
    return pasillo


@router.delete("/pasillos/{pasillo_id}")
def eliminar_pasillo(pasillo_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    p = db.query(Pasillo).filter(Pasillo.id == pasillo_id).first()
    if not p:
        raise HTTPException(404, "Pasillo no encontrado")
    p.activo = False
    db.commit()
    return {"ok": True}


# ── Estantes ──────────────────────────────────────────────────────────────────

@router.get("/estantes")
def listar_estantes(pasillo_id: Optional[int] = None, db: Session = Depends(get_db), _=Depends(require_admin)):
    q = db.query(Estante).filter(Estante.activo == True)
    if pasillo_id:
        q = q.filter(Estante.pasillo_id == pasillo_id)
    return q.order_by(Estante.numero).all()


@router.post("/estantes")
def crear_estante(body: EstanteIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    estante = Estante(pasillo_id=body.pasillo_id, numero=body.numero)
    db.add(estante)
    db.commit()
    db.refresh(estante)
    return estante


@router.delete("/estantes/{estante_id}")
def eliminar_estante(estante_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    e = db.query(Estante).filter(Estante.id == estante_id).first()
    if not e:
        raise HTTPException(404, "Estante no encontrado")
    e.activo = False
    db.commit()
    return {"ok": True}


# ── Ubicaciones de producto ───────────────────────────────────────────────────

@router.get("/producto/{producto_id}")
def ubicaciones_producto(producto_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    ubs = db.query(UbicacionProducto).filter(
        UbicacionProducto.producto_id == producto_id,
        UbicacionProducto.activa == True,
    ).all()
    result = []
    for u in ubs:
        area    = db.query(Area).filter(Area.id == u.area_id).first()
        pasillo = db.query(Pasillo).filter(Pasillo.id == u.pasillo_id).first()
        estante = db.query(Estante).filter(Estante.id == u.estante_id).first()
        result.append({
            "id":          u.id,
            "producto_id": u.producto_id,
            "area_id":     u.area_id,
            "area_nombre": area.nombre if area else "",
            "pasillo_id":  u.pasillo_id,
            "pasillo_num": pasillo.numero if pasillo else "",
            "estante_id":  u.estante_id,
            "estante_num": estante.numero if estante else "",
            "nivel":       u.nivel,
            "cantidad":    u.cantidad,
        })
    return result


@router.post("/producto")
def crear_ubicacion(body: UbicacionIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    ub = UbicacionProducto(
        producto_id=body.producto_id,
        area_id=body.area_id,
        pasillo_id=body.pasillo_id,
        estante_id=body.estante_id,
        nivel=body.nivel,
        cantidad=body.cantidad,
    )
    db.add(ub)
    db.commit()
    db.refresh(ub)
    return ub


@router.put("/producto/{ub_id}")
def editar_ubicacion(ub_id: int, body: UbicacionIn, db: Session = Depends(get_db), _=Depends(require_admin)):
    ub = db.query(UbicacionProducto).filter(UbicacionProducto.id == ub_id).first()
    if not ub:
        raise HTTPException(404, "Ubicación no encontrada")
    ub.area_id    = body.area_id
    ub.pasillo_id = body.pasillo_id
    ub.estante_id = body.estante_id
    ub.nivel      = body.nivel
    ub.cantidad   = body.cantidad
    db.commit()
    db.refresh(ub)
    return ub


@router.delete("/producto/{ub_id}")
def eliminar_ubicacion(ub_id: int, db: Session = Depends(get_db), _=Depends(require_admin)):
    ub = db.query(UbicacionProducto).filter(UbicacionProducto.id == ub_id).first()
    if not ub:
        raise HTTPException(404, "Ubicación no encontrada")
    ub.activa = False
    db.commit()
    return {"ok": True}


# ── Resumen general ───────────────────────────────────────────────────────────

@router.get("/resumen")
def resumen_ubicaciones(db: Session = Depends(get_db), _=Depends(require_admin)):
    areas = db.query(Area).filter(Area.activa == True).all()
    result = []
    for area in areas:
        pasillos = db.query(Pasillo).filter(Pasillo.area_id == area.id, Pasillo.activo == True).all()
        pasillos_data = []
        for pasillo in pasillos:
            estantes = db.query(Estante).filter(Estante.pasillo_id == pasillo.id, Estante.activo == True).all()
            estantes_data = []
            for estante in estantes:
                ubs = db.query(UbicacionProducto).filter(
                    UbicacionProducto.estante_id == estante.id,
                    UbicacionProducto.activa == True,
                ).all()
                prods = []
                for u in ubs:
                    prod = db.query(Producto).filter(Producto.id == u.producto_id).first()
                    if prod:
                        prods.append({
                            "ubicacion_id": u.id,
                            "producto_id":  prod.id,
                            "nombre":       prod.nombre,
                            "nivel":        u.nivel,
                            "cantidad":     u.cantidad,
                        })
                estantes_data.append({
                    "id": estante.id, "numero": estante.numero,
                    "productos": prods,
                })
            pasillos_data.append({
                "id": pasillo.id, "numero": pasillo.numero,
                "estantes": estantes_data,
            })
        result.append({
            "id": area.id, "nombre": area.nombre,
            "pasillos": pasillos_data,
        })
    return result
