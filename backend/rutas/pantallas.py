from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Pantalla, PantallaDepartamento, SlideMarca, Producto, Oferta, Departamento
from rutas.usuarios import require_admin
from rutas.productos import _precios_computados, _resolver_policy, _tasas_actuales

router = APIRouter(prefix="/pantallas", tags=["pantallas"])


# ============================================================================
# Schemas
# ============================================================================

class PantallaSchema(BaseModel):
    nombre:            str
    activa:            bool = True
    segundos_producto: int  = 8
    segundos_oferta:   int  = 8
    segundos_marca:    int  = 6
    ratio_producto:    int  = 3
    ratio_oferta:      int  = 1
    ratio_marca:       int  = 1
    departamento_ids:  list[int] = []

    class Config:
        from_attributes = True


class SlideMarcaSchema(BaseModel):
    foto_url: str
    titulo:   Optional[str] = None
    orden:    int           = 0
    activo:   bool          = True

    class Config:
        from_attributes = True


# ============================================================================
# Helpers
# ============================================================================

def _pantalla_dict(p: Pantalla, db: Session) -> dict:
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    d["departamento_ids"] = [
        pd.departamento_id for pd in
        db.query(PantallaDepartamento).filter(PantallaDepartamento.pantalla_id == p.id).all()
    ]
    return d


def _weighted_pattern(weights: dict, length: int) -> list:
    """Distribuye `length` slots entre las claves de `weights` según su peso
    relativo, intercalando en vez de agrupar todos los de un tipo seguidos
    (algoritmo de round-robin ponderado / surplus scheduling)."""
    keys  = [k for k, w in weights.items() if w > 0]
    if not keys:
        return []
    total = sum(weights[k] for k in keys)
    acc   = {k: 0 for k in keys}
    resultado = []
    for _ in range(length):
        for k in keys:
            acc[k] += weights[k]
        ganador = max(keys, key=lambda k: acc[k])
        acc[ganador] -= total
        resultado.append(ganador)
    return resultado


# ============================================================================
# CRUD Pantallas (admin)
# ============================================================================

@router.get("/")
def listar_pantallas(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    pantallas = db.query(Pantalla).order_by(Pantalla.id).all()
    return [_pantalla_dict(p, db) for p in pantallas]


@router.post("/")
def crear_pantalla(
    datos: PantallaSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    campos = datos.dict(exclude={"departamento_ids"})
    nueva = Pantalla(**campos)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    for dep_id in datos.departamento_ids:
        db.add(PantallaDepartamento(pantalla_id=nueva.id, departamento_id=dep_id))
    db.commit()
    return _pantalla_dict(nueva, db)


@router.put("/{pantalla_id}")
def actualizar_pantalla(
    pantalla_id: int,
    datos: PantallaSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(Pantalla).filter(Pantalla.id == pantalla_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pantalla no encontrada")
    for key, value in datos.dict(exclude={"departamento_ids"}).items():
        setattr(p, key, value)
    db.query(PantallaDepartamento).filter(PantallaDepartamento.pantalla_id == pantalla_id).delete()
    for dep_id in datos.departamento_ids:
        db.add(PantallaDepartamento(pantalla_id=pantalla_id, departamento_id=dep_id))
    db.commit()
    db.refresh(p)
    return _pantalla_dict(p, db)


@router.delete("/{pantalla_id}")
def eliminar_pantalla(
    pantalla_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(Pantalla).filter(Pantalla.id == pantalla_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Pantalla no encontrada")
    db.query(PantallaDepartamento).filter(PantallaDepartamento.pantalla_id == pantalla_id).delete()
    db.delete(p)
    db.commit()
    return {"mensaje": "Pantalla eliminada"}


# ============================================================================
# CRUD Slides de marca (admin)
# ============================================================================

@router.get("/slides-marca")
def listar_slides_marca(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    return db.query(SlideMarca).order_by(SlideMarca.orden, SlideMarca.id).all()


@router.post("/slides-marca")
def crear_slide_marca(
    datos: SlideMarcaSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    nuevo = SlideMarca(**datos.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.put("/slides-marca/{slide_id}")
def actualizar_slide_marca(
    slide_id: int,
    datos: SlideMarcaSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    s = db.query(SlideMarca).filter(SlideMarca.id == slide_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Slide no encontrado")
    for key, value in datos.dict().items():
        setattr(s, key, value)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/slides-marca/{slide_id}")
def eliminar_slide_marca(
    slide_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    s = db.query(SlideMarca).filter(SlideMarca.id == slide_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Slide no encontrado")
    db.delete(s)
    db.commit()
    return {"mensaje": "Slide eliminado"}


# ============================================================================
# Cola de contenido (público — lo consume el reproductor en el TV, sin login)
# ============================================================================

@router.get("/{pantalla_id}/cola")
def obtener_cola(pantalla_id: int, db: Session = Depends(get_db)):
    pantalla = db.query(Pantalla).filter(Pantalla.id == pantalla_id).first()
    if not pantalla:
        raise HTTPException(status_code=404, detail="Pantalla no encontrada")

    dep_ids = [
        pd.departamento_id for pd in
        db.query(PantallaDepartamento).filter(PantallaDepartamento.pantalla_id == pantalla_id).all()
    ]
    # Departamento inactivo (ej. consignación fuera de revisión) no debe
    # colarse en cartelería aunque la pantalla lo tenga asignado y algún
    # producto tenga foto puesta a mano.
    if dep_ids:
        dep_ids = [
            row[0] for row in db.query(Departamento.id).filter(
                Departamento.id.in_(dep_ids), Departamento.activo == True,
            ).all()
        ]

    bcv, binance = _tasas_actuales(db)
    hoy = date.today()

    slides_producto = []
    slides_oferta   = []

    if dep_ids:
        productos = db.query(Producto).filter(
            Producto.departamento_id.in_(dep_ids),
            Producto.activo == True,
            Producto.foto_url.isnot(None),
            Producto.foto_url != "",
        ).all()

        ofertas_activas = db.query(Oferta).join(
            Producto, Oferta.producto_id == Producto.id
        ).filter(
            Producto.departamento_id.in_(dep_ids),
            Oferta.activo == True,
            Oferta.foto_url.isnot(None),
            Oferta.foto_url != "",
            Oferta.fecha_inicio <= hoy,
            or_(Oferta.fecha_fin == None, Oferta.fecha_fin >= hoy),
            or_(Oferta.cantidad_limite == None, Oferta.cantidad_usada < Oferta.cantidad_limite),
        ).all()
        ofertas_producto_ids = {o.producto_id for o in ofertas_activas}

        productos_map = {p.id: p for p in productos}

        for p in productos:
            policy, ajuste_tipo, ajuste_divisa_pct = _resolver_policy(p, db)
            precios = _precios_computados(p, bcv, binance, policy, ajuste_tipo, ajuste_divisa_pct)
            slides_producto.append({
                "tipo":       "producto",
                "id":         p.id,
                "nombre":     p.nombre,
                "codigo":     p.codigo,
                "foto_url":   p.foto_url,
                "imagen_publicitaria_url": p.imagen_publicitaria_url,
                "precio_usd": round(precios["precio_base_usd"], 2),
            })

        for o in ofertas_activas:
            prod = productos_map.get(o.producto_id)
            if not prod:
                prod = db.query(Producto).filter(Producto.id == o.producto_id).first()
            if not prod:
                continue
            policy, ajuste_tipo, ajuste_divisa_pct = _resolver_policy(prod, db)
            precios = _precios_computados(prod, bcv, binance, policy, ajuste_tipo, ajuste_divisa_pct)
            precio_base = precios["precio_base_usd"]
            precio_oferta = round(precio_base * (1 - o.valor / 100), 2) if o.tipo_precio == "porcentaje" else o.valor
            slides_oferta.append({
                "tipo":            "oferta",
                "id":              o.id,
                "nombre":          prod.nombre,
                "codigo":          prod.codigo,
                "foto_url":        o.foto_url,
                "precio_base_usd": round(precio_base, 2),
                "precio_usd":      round(precio_oferta, 2),
            })

    slides_marca_db = db.query(SlideMarca).filter(SlideMarca.activo == True).order_by(SlideMarca.orden, SlideMarca.id).all()
    slides_marca = [
        {"tipo": "marca", "id": s.id, "titulo": s.titulo, "foto_url": s.foto_url}
        for s in slides_marca_db
    ]

    grupos = {
        "producto": slides_producto,
        "oferta":   slides_oferta,
        "marca":    slides_marca,
    }
    pesos = {
        "producto": pantalla.ratio_producto if slides_producto else 0,
        "oferta":   pantalla.ratio_oferta   if slides_oferta   else 0,
        "marca":    pantalla.ratio_marca    if slides_marca    else 0,
    }
    total_items = sum(len(v) for v in grupos.values())
    patron = _weighted_pattern(pesos, total_items)

    cursores = {"producto": 0, "oferta": 0, "marca": 0}
    cola = []
    duraciones = {
        "producto": pantalla.segundos_producto,
        "oferta":   pantalla.segundos_oferta,
        "marca":    pantalla.segundos_marca,
    }
    for tipo in patron:
        items = grupos[tipo]
        item = items[cursores[tipo] % len(items)]
        cursores[tipo] += 1
        cola.append({**item, "segundos": duraciones[tipo]})

    return {
        "pantalla": {
            "id":     pantalla.id,
            "nombre": pantalla.nombre,
            "activa": pantalla.activa,
        },
        "slides": cola,
    }
