from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import PlantillaGarantia, GarantiaVenta, Producto
from rutas.usuarios import require_admin

router = APIRouter(prefix="/garantias", tags=["garantias"])


# ============================================================================
# Schemas
# ============================================================================

class PlantillaSchema(BaseModel):
    nombre:      str
    meses:       int   = 0
    condiciones: Optional[str] = None
    activa:      bool  = True

    class Config:
        from_attributes = True


# ============================================================================
# Plantillas — CRUD
# ============================================================================

@router.get("/plantillas")
def listar_plantillas(solo_activas: bool = True, db: Session = Depends(get_db)):
    q = db.query(PlantillaGarantia)
    if solo_activas:
        q = q.filter(PlantillaGarantia.activa == True)
    return q.order_by(PlantillaGarantia.nombre).all()


@router.post("/plantillas")
def crear_plantilla(
    datos: PlantillaSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    nueva = PlantillaGarantia(**datos.dict())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.put("/plantillas/{plantilla_id}")
def actualizar_plantilla(
    plantilla_id: int,
    datos: PlantillaSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(PlantillaGarantia).filter(PlantillaGarantia.id == plantilla_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    for key, value in datos.dict().items():
        setattr(p, key, value)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/plantillas/{plantilla_id}")
def eliminar_plantilla(
    plantilla_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(PlantillaGarantia).filter(PlantillaGarantia.id == plantilla_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    en_uso = db.query(Producto).filter(
        Producto.plantilla_garantia_id == plantilla_id
    ).first()
    if en_uso:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: hay productos usando esta plantilla. Desactívala primero."
        )
    db.delete(p)
    db.commit()
    return {"mensaje": "Plantilla eliminada"}


# ============================================================================
# Garantías registradas por venta
# ============================================================================

@router.get("/venta/{venta_id}")
def garantias_de_venta(venta_id: int, db: Session = Depends(get_db)):
    garantias = db.query(GarantiaVenta).filter(
        GarantiaVenta.venta_id == venta_id
    ).all()
    resultado = []
    for g in garantias:
        d = {c.name: getattr(g, c.name) for c in g.__table__.columns}
        prod = db.query(Producto).filter(Producto.id == g.producto_id).first()
        d["nombre_producto"] = prod.nombre if prod else f"Producto #{g.producto_id}"
        resultado.append(d)
    return resultado
