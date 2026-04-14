from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Producto, TasaCambio, Departamento, VarianteProducto, ComponenteProducto, Oferta
from pydantic import BaseModel
from typing import Optional
from datetime import date
from rutas.usuarios import require_admin

router = APIRouter(prefix="/productos", tags=["productos"])


# ============================================================================
# Schemas
# ============================================================================

class ProductoSchema(BaseModel):
    nombre:      str
    descripcion: Optional[str]  = None
    categoria:   Optional[str]  = None
    stock:       int            = 0
    foto_url:    Optional[str]  = None
    costo_usd:   float          = 0.0
    margen:      float          = 0.30

    departamento_id:         Optional[int]   = None
    proveedor_id:            Optional[int]   = None
    es_producto_clave:       bool            = False
    es_producto_compuesto:   bool            = False
    descuento_compuesto_pct: float           = 0.0
    codigo:                  Optional[str]   = None

    class Config:
        from_attributes = True


class DepartamentoSchema(BaseModel):
    nombre:      str
    descripcion: Optional[str] = None
    activo:      bool          = True

    class Config:
        from_attributes = True


class VarianteSchema(BaseModel):
    clase:               str
    color:               Optional[str]  = None
    stock:               int            = 0
    precio_override_usd: Optional[float]= None
    activo:              bool           = True

    class Config:
        from_attributes = True


class ComponenteSchema(BaseModel):
    producto_componente_id: int
    cantidad:               float

    class Config:
        from_attributes = True


class OfertaSchema(BaseModel):
    producto_id:     int
    tipo_precio:     str            # "porcentaje" | "directo"
    valor:           float
    fecha_inicio:    date
    fecha_fin:       Optional[date] = None
    cantidad_limite: Optional[int]  = None
    activo:          bool           = True

    class Config:
        from_attributes = True


# ============================================================================
# Helpers internos
# ============================================================================

def _precios_computados(p: Producto, tasa_bcv: float, tasa_binance: float) -> dict:
    """Retorna los precios calculados de un producto dado las tasas actuales."""
    factor      = round(tasa_binance / tasa_bcv, 6) if tasa_bcv > 0 else 1.0
    precio_base = round(float(p.costo_usd or 0) * (1 + float(p.margen or 0)), 4)
    precio_ref  = round(precio_base * factor, 4)
    precio_bs   = round(precio_base * tasa_binance, 2)
    return {
        "precio_base_usd":        precio_base,
        "precio_referencial_usd": precio_ref,
        "precio_bs":              precio_bs,
        "factor":                 factor,
    }


def _enriquecer(p: Producto, tasa_bcv: float, tasa_binance: float) -> dict:
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    d.update(_precios_computados(p, tasa_bcv, tasa_binance))
    return d


def _tasas_actuales(db: Session):
    obj = db.query(TasaCambio).order_by(TasaCambio.id.desc()).first()
    if not obj:
        return 1.0, 1.0
    bcv     = float(obj.tasa or 1)
    binance = float(obj.tasa_binance or bcv)
    return bcv, binance


# ============================================================================
# IMPORTANTE: Las rutas con segmentos literales (departamentos, ofertas,
# variantes/{id}, componentes/{id}) deben registrarse ANTES que /{producto_id}
# para que FastAPI no intente parsear la cadena literal como entero.
# ============================================================================

# ============================================================================
# Endpoints: Departamentos  (registrados antes que /{producto_id})
# ============================================================================

@router.get("/departamentos")
def listar_departamentos(db: Session = Depends(get_db)):
    return db.query(Departamento).all()


@router.post("/departamentos")
def crear_departamento(
    datos: DepartamentoSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    nuevo = Departamento(**datos.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


@router.put("/departamentos/{departamento_id}")
def actualizar_departamento(
    departamento_id: int,
    datos: DepartamentoSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    dep = db.query(Departamento).filter(Departamento.id == departamento_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    for key, value in datos.dict().items():
        setattr(dep, key, value)
    db.commit()
    db.refresh(dep)
    return dep


@router.delete("/departamentos/{departamento_id}")
def eliminar_departamento(
    departamento_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    dep = db.query(Departamento).filter(Departamento.id == departamento_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    tiene_productos = db.query(Producto).filter(
        Producto.departamento_id == departamento_id
    ).first()
    if tiene_productos:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: hay productos asignados a este departamento"
        )
    db.delete(dep)
    db.commit()
    return {"mensaje": "Departamento eliminado"}


# ============================================================================
# Endpoints: Variantes — rutas sin {producto_id} en primer segmento
# ============================================================================

@router.put("/variantes/{variante_id}")
def actualizar_variante(
    variante_id: int,
    datos: VarianteSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    v = db.query(VarianteProducto).filter(VarianteProducto.id == variante_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Variante no encontrada")
    for key, value in datos.dict().items():
        setattr(v, key, value)
    db.commit()
    db.refresh(v)
    return v


@router.delete("/variantes/{variante_id}")
def eliminar_variante(
    variante_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    v = db.query(VarianteProducto).filter(VarianteProducto.id == variante_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Variante no encontrada")
    db.delete(v)
    db.commit()
    return {"mensaje": "Variante eliminada"}


# ============================================================================
# Endpoints: Componentes — rutas sin {producto_id} en primer segmento
# ============================================================================

@router.delete("/componentes/{componente_id}")
def eliminar_componente(
    componente_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    c = db.query(ComponenteProducto).filter(ComponenteProducto.id == componente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Componente no encontrado")
    db.delete(c)
    db.commit()
    return {"mensaje": "Componente eliminado"}


# ============================================================================
# Endpoints: Ofertas  (registrados antes que /{producto_id})
# ============================================================================

@router.get("/ofertas")
def listar_ofertas(db: Session = Depends(get_db)):
    ofertas = db.query(Oferta).all()
    resultado = []
    bcv, binance = _tasas_actuales(db)
    for o in ofertas:
        d = {c.name: getattr(o, c.name) for c in o.__table__.columns}
        prod = db.query(Producto).filter(Producto.id == o.producto_id).first()
        d["nombre_producto"] = prod.nombre if prod else "—"
        if prod and o.tipo_precio == "porcentaje":
            precio_base = _precios_computados(prod, bcv, binance)["precio_base_usd"]
            d["precio_efectivo_usd"] = round(precio_base * (1 - o.valor / 100), 4)
        elif o.tipo_precio == "directo":
            d["precio_efectivo_usd"] = o.valor
        else:
            d["precio_efectivo_usd"] = None
        resultado.append(d)
    return resultado


@router.post("/ofertas")
def crear_oferta(
    datos: OfertaSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    prod = db.query(Producto).filter(Producto.id == datos.producto_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if datos.tipo_precio not in ("porcentaje", "directo"):
        raise HTTPException(status_code=400, detail="tipo_precio debe ser 'porcentaje' o 'directo'")
    nueva = Oferta(**datos.dict())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.put("/ofertas/{oferta_id}")
def actualizar_oferta(
    oferta_id: int,
    datos: OfertaSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    o = db.query(Oferta).filter(Oferta.id == oferta_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    if datos.tipo_precio not in ("porcentaje", "directo"):
        raise HTTPException(status_code=400, detail="tipo_precio debe ser 'porcentaje' o 'directo'")
    for key, value in datos.dict().items():
        setattr(o, key, value)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/ofertas/{oferta_id}")
def eliminar_oferta(
    oferta_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    o = db.query(Oferta).filter(Oferta.id == oferta_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    db.delete(o)
    db.commit()
    return {"mensaje": "Oferta eliminada"}


# ============================================================================
# Endpoints: Productos (existentes — sin cambios en lógica)
# Registrados DESPUÉS de todas las rutas con segmentos literales
# ============================================================================

@router.get("/")
def listar_productos(db: Session = Depends(get_db)):
    bcv, binance = _tasas_actuales(db)
    return [_enriquecer(p, bcv, binance) for p in db.query(Producto).all()]


@router.get("/buscar")
def buscar_por_codigo(codigo: str, db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.codigo == codigo).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    bcv, binance = _tasas_actuales(db)
    return _enriquecer(p, bcv, binance)


@router.post("/")
def crear_producto(
    producto: ProductoSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    if producto.codigo:
        existe = db.query(Producto).filter(Producto.codigo == producto.codigo).first()
        if existe:
            raise HTTPException(status_code=400, detail="Ya existe un producto con ese código")
    nuevo = Producto(**producto.dict())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    bcv, binance = _tasas_actuales(db)
    return _enriquecer(nuevo, bcv, binance)


@router.get("/{producto_id}")
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    bcv, binance = _tasas_actuales(db)
    return _enriquecer(p, bcv, binance)


@router.put("/{producto_id}")
def actualizar_producto(
    producto_id: int,
    datos: ProductoSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for key, value in datos.dict().items():
        setattr(p, key, value)
    db.commit()
    db.refresh(p)
    bcv, binance = _tasas_actuales(db)
    return _enriquecer(p, bcv, binance)


@router.put("/{producto_id}/codigo")
def actualizar_codigo_producto(
    producto_id: int,
    datos: dict,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    nuevo_codigo = datos.get("codigo", "").strip() or None
    if nuevo_codigo:
        existe = db.query(Producto).filter(
            Producto.codigo == nuevo_codigo,
            Producto.id != producto_id,
        ).first()
        if existe:
            raise HTTPException(status_code=400, detail="Ese código ya está en uso")
    p.codigo = nuevo_codigo
    db.commit()
    db.refresh(p)
    bcv, binance = _tasas_actuales(db)
    return _enriquecer(p, bcv, binance)


@router.delete("/{producto_id}")
def eliminar_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.delete(p)
    db.commit()
    return {"mensaje": "Producto eliminado"}


# ============================================================================
# Endpoints: Variantes — rutas con {producto_id} en primer segmento
# Registrados después de /{producto_id} para no ocultar rutas literales
# ============================================================================

@router.get("/{producto_id}/variantes")
def listar_variantes(producto_id: int, db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db.query(VarianteProducto).filter(
        VarianteProducto.producto_id == producto_id
    ).all()


@router.post("/{producto_id}/variantes")
def crear_variante(
    producto_id: int,
    datos: VarianteSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    nueva = VarianteProducto(producto_id=producto_id, **datos.dict())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


# ============================================================================
# Endpoints: Componentes — rutas con {producto_id} en primer segmento
# ============================================================================

@router.get("/{producto_id}/componentes")
def listar_componentes(producto_id: int, db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    componentes = db.query(ComponenteProducto).filter(
        ComponenteProducto.producto_compuesto_id == producto_id
    ).all()
    bcv, binance = _tasas_actuales(db)
    resultado = []
    for c in componentes:
        comp = db.query(Producto).filter(Producto.id == c.producto_componente_id).first()
        resultado.append({
            "id":                     c.id,
            "producto_compuesto_id":  c.producto_compuesto_id,
            "producto_componente_id": c.producto_componente_id,
            "nombre_componente":      comp.nombre if comp else "—",
            "cantidad":               c.cantidad,
            "precio_base_usd":        _precios_computados(comp, bcv, binance)["precio_base_usd"] if comp else 0,
        })
    return resultado


@router.post("/{producto_id}/componentes")
def agregar_componente(
    producto_id: int,
    datos: ComponenteSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if not p.es_producto_compuesto:
        raise HTTPException(status_code=400, detail="El producto no está marcado como compuesto")
    comp = db.query(Producto).filter(Producto.id == datos.producto_componente_id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Producto componente no encontrado")
    if datos.producto_componente_id == producto_id:
        raise HTTPException(status_code=400, detail="Un producto no puede ser componente de sí mismo")
    nuevo = ComponenteProducto(
        producto_compuesto_id  = producto_id,
        producto_componente_id = datos.producto_componente_id,
        cantidad               = datos.cantidad,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo
