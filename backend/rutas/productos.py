from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Producto, TasaCambio, Departamento, Categoria, VarianteProducto, ComponenteProducto, Oferta, PlantillaGarantia, CatalogoProveedor, Proveedor
from pricing import calcular_precios, resolver_policy
from pydantic import BaseModel
from typing import Optional
from datetime import date
from rutas.usuarios import require_admin
import io
import re
import pandas as pd

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

    categoria_id:            Optional[int]   = None
    departamento_id:         Optional[int]   = None
    proveedor_id:            Optional[int]   = None
    es_producto_clave:       bool            = False
    es_producto_compuesto:   bool            = False
    descuento_compuesto_pct: float           = 0.0
    codigo:                  Optional[str]   = None
    activo:                  bool            = True
    requiere_serial:         bool            = False
    plantilla_garantia_id:   Optional[int]   = None

    class Config:
        from_attributes = True


class DepartamentoSchema(BaseModel):
    nombre:      str
    descripcion: Optional[str] = None
    activo:      bool          = True

    class Config:
        from_attributes = True


class CategoriaSchema(BaseModel):
    nombre:          str
    departamento_id: int

    class Config:
        from_attributes = True


class VarianteSchema(BaseModel):
    clase:               str
    color:               Optional[str]  = None
    stock:               int            = 0
    precio_override_usd: Optional[float]= None
    costo_usd:           Optional[float]= None
    margen:              Optional[float]= None
    activo:              bool           = True
    codigo:              Optional[str]  = None

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

def _precios_computados(p: Producto, tasa_bcv: float, tasa_binance: float,
                         policy: str = "MARKET_FACTOR",
                         ajuste_divisa_pct: float = 0.0) -> dict:
    return calcular_precios(
        costo_usd         = float(p.costo_usd or 0),
        margen            = float(p.margen or 0),
        tasa_bcv          = tasa_bcv,
        tasa_binance      = tasa_binance,
        policy            = policy,
        ajuste_divisa_pct = ajuste_divisa_pct,
    )


def _enriquecer(p: Producto, tasa_bcv: float, tasa_binance: float,
                variantes: list = None, plantilla: PlantillaGarantia = None,
                tiene_catalogo: bool = False,
                policy: str = "MARKET_FACTOR",
                ajuste_divisa_pct: float = 0.0,
                codigo_proveedor: str = "") -> dict:
    d = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    d.update(_precios_computados(p, tasa_bcv, tasa_binance, policy, ajuste_divisa_pct))
    d["tiene_catalogo"]    = tiene_catalogo
    d["codigo_proveedor"]  = codigo_proveedor  # código del proveedor vinculado (inamovible tras 1ª compra)
    vs = variantes or []
    d["tiene_variantes"]   = len(vs) > 0
    d["variantes_resumen"] = [
        {
            "id":                  v.id,
            "clase":               v.clase,
            "color":               v.color,
            "stock":               v.stock,
            "activo":              v.activo,
            "codigo":              v.codigo,
            "precio_override_usd": v.precio_override_usd,
            "costo_usd":           v.costo_usd,
            "margen":              v.margen,
        }
        for v in vs
    ]
    if plantilla:
        d["garantia"] = {
            "id":          plantilla.id,
            "nombre":      plantilla.nombre,
            "meses":       plantilla.meses,
            "condiciones": plantilla.condiciones,
        }
    else:
        d["garantia"] = None
    return d


def _plantilla_de(p: Producto, db: Session):
    if p.plantilla_garantia_id:
        return db.query(PlantillaGarantia).filter(PlantillaGarantia.id == p.plantilla_garantia_id).first()
    return None


def _tasas_actuales(db: Session):
    obj = db.query(TasaCambio).order_by(TasaCambio.id.desc()).first()
    if not obj:
        return 1.0, 1.0
    bcv     = float(obj.tasa or 1)
    binance = float(obj.tasa_binance or bcv)
    return bcv, binance


def generar_codigo(nombre: str, db: Session) -> str:
    letras = re.sub(r'[^A-Za-z]', '', nombre).upper()[:3]
    if len(letras) < 3:
        letras = letras.ljust(3, 'X')
    prefijo = letras + '-'

    existentes = db.query(Producto.codigo).filter(
        Producto.codigo.like(f"{prefijo}%")
    ).all()

    numeros = []
    for (cod,) in existentes:
        if cod:
            match = re.search(r'(\d+)$', cod)
            if match:
                numeros.append(int(match.group(1)))

    siguiente = max(numeros) + 1 if numeros else 1
    return f"{prefijo}{siguiente:03d}"


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
    return db.query(Departamento).filter(Departamento.activo == True).order_by(Departamento.nombre).all()


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
# Endpoints: Categorías  (registrados antes que /{producto_id})
# ============================================================================

@router.get("/categorias")
def listar_categorias(
    departamento_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Categoria)
    if departamento_id:
        q = q.filter(Categoria.departamento_id == departamento_id)
    cats = q.order_by(Categoria.nombre).all()
    return [
        {
            "id":              c.id,
            "nombre":          c.nombre,
            "departamento_id": c.departamento_id,
        }
        for c in cats
    ]


@router.post("/categorias")
def crear_categoria(
    datos: CategoriaSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    nueva = Categoria(**datos.dict())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.put("/categorias/{categoria_id}")
def actualizar_categoria(
    categoria_id: int,
    datos: CategoriaSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    cat = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    for key, value in datos.dict().items():
        setattr(cat, key, value)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categorias/{categoria_id}")
def eliminar_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    cat = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    tiene_productos = db.query(Producto).filter(
        Producto.categoria_id == categoria_id
    ).first()
    if tiene_productos:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: hay productos asignados a esta categoría"
        )
    db.delete(cat)
    db.commit()
    return {"mensaje": "Categoría eliminada"}


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
def listar_productos(
    incluir_inactivos: bool = False,
    skip: int = 0,
    limit: int = 100,
    busqueda: str = "",
    departamento_id: Optional[int] = None,
    categoria_id: Optional[int] = None,
    proveedor_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Producto)
    if not incluir_inactivos:
        q = q.filter(Producto.activo == True)
    if busqueda:
        from sqlalchemy import or_
        variante_ids = db.query(VarianteProducto.producto_id).filter(
            VarianteProducto.codigo.ilike(f"%{busqueda}%")
        ).subquery()
        catalogo_ids_busq = db.query(CatalogoProveedor.producto_id).filter(
            CatalogoProveedor.codigo_proveedor.ilike(f"%{busqueda}%")
        ).subquery()
        q = q.filter(
            or_(
                Producto.nombre.ilike(f"%{busqueda}%"),
                Producto.codigo.ilike(f"%{busqueda}%"),
                Producto.id.in_(variante_ids),
                Producto.id.in_(catalogo_ids_busq),
            )
        )
    if departamento_id is not None:
        q = q.filter(Producto.departamento_id == departamento_id)
    if categoria_id is not None:
        q = q.filter(Producto.categoria_id == categoria_id)
    if proveedor_id is not None:
        q = q.filter(Producto.proveedor_id == proveedor_id)
    total = q.count()
    bcv, binance = _tasas_actuales(db)
    q = q.order_by(func.length(Producto.nombre), Producto.nombre)
    lista = q.offset(skip).limit(limit).all()
    ids   = [p.id for p in lista]
    variantes_map: dict = {}
    if ids:
        for v in db.query(VarianteProducto).filter(VarianteProducto.producto_id.in_(ids)).all():
            variantes_map.setdefault(v.producto_id, []).append(v)
    plantilla_ids = {p.plantilla_garantia_id for p in lista if p.plantilla_garantia_id}
    plantillas_map: dict = {}
    if plantilla_ids:
        for pl in db.query(PlantillaGarantia).filter(PlantillaGarantia.id.in_(plantilla_ids)).all():
            plantillas_map[pl.id] = pl
    catalogo_ids: set = set()
    catalogo_codigo_map: dict = {}  # producto_id -> codigo_proveedor
    if ids:
        for c in db.query(CatalogoProveedor).filter(
            CatalogoProveedor.producto_id.in_(ids),
            CatalogoProveedor.codigo_proveedor != None,
        ).all():
            catalogo_ids.add(c.producto_id)
            if c.producto_id not in catalogo_codigo_map:
                catalogo_codigo_map[c.producto_id] = c.codigo_proveedor or ""
    prov_ids = {p.proveedor_id for p in lista if p.proveedor_id}
    prov_policy_map: dict = {}
    if prov_ids:
        for prov in db.query(Proveedor).filter(Proveedor.id.in_(prov_ids)).all():
            prov_policy_map[prov.id] = (
                prov.pricing_policy or "MARKET_FACTOR",
                float(prov.ajuste_divisa_pct or 0.0),
            )
    productos = []
    for p in lista:
        policy, ajuste = resolver_policy(
            pricing_policy_override=p.pricing_policy_override,
            proveedor_id=p.proveedor_id,
            prov_policy_map=prov_policy_map,
        )
        productos.append(
            _enriquecer(p, bcv, binance, variantes_map.get(p.id, []),
                        plantillas_map.get(p.plantilla_garantia_id),
                        tiene_catalogo=(p.id in catalogo_ids),
                        policy=policy,
                        ajuste_divisa_pct=ajuste,
                        codigo_proveedor=catalogo_codigo_map.get(p.id, ""))
        )
    return {"total": total, "productos": productos}


@router.post("/importar-masivo")
async def importar_masivo(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    contenido = await archivo.read()
    nombre = archivo.filename or ""

    # Leer archivo según extensión
    try:
        if nombre.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contenido))
        elif nombre.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(contenido))
        else:
            raise HTTPException(status_code=400, detail="Formato no soportado. Use .xlsx o .csv")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer el archivo: {e}")

    # Normalizar nombres de columnas (minúsculas, sin espacios extra)
    df.columns = [str(c).strip().lower() for c in df.columns]

    COLUMNAS = ["nombre", "categoria", "departamento", "proveedor",
                "costo_usd", "margen_pct", "stock", "es_producto_clave", "descripcion"]
    for col in ["nombre"]:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Columna obligatoria ausente: '{col}'")

    # Precargar departamentos y productos existentes
    departamentos = {d.nombre.lower(): d.id for d in db.query(Departamento).all()}
    nombres_existentes = {
        p.nombre.lower() for p in db.query(Producto.nombre).all()
    }

    importados = 0
    omitidos   = 0
    errores    = []

    for idx, row in df.iterrows():
        fila = idx + 2  # fila real en Excel (1 = encabezado)

        nombre_prod = str(row.get("nombre", "")).strip()
        if not nombre_prod:
            omitidos += 1
            errores.append({"fila": fila, "nombre": "(vacío)", "motivo": "Nombre vacío"})
            continue

        # Duplicado
        if nombre_prod.lower() in nombres_existentes:
            omitidos += 1
            errores.append({"fila": fila, "nombre": nombre_prod, "motivo": "Ya existe en inventario"})
            continue

        # Departamento
        depto_nombre = str(row.get("departamento", "")).strip()
        departamento_id = None
        if depto_nombre and depto_nombre.lower() != "nan":
            departamento_id = departamentos.get(depto_nombre.lower())
            if departamento_id is None:
                omitidos += 1
                errores.append({"fila": fila, "nombre": nombre_prod,
                                "motivo": f"Departamento '{depto_nombre}' no encontrado"})
                continue

        # Valores numéricos con fallback seguro
        def _float(val, default=0.0):
            try:
                v = float(val)
                return v if not pd.isna(v) else default
            except Exception:
                return default

        def _int(val, default=0):
            try:
                v = int(float(val))
                return v
            except Exception:
                return default

        def _bool(val):
            if isinstance(val, bool): return val
            return str(val).strip().lower() in ("1", "true", "si", "sí", "yes", "x")

        costo_usd   = _float(row.get("costo_usd",   0))
        margen_pct  = _float(row.get("margen_pct",  30))
        stock       = _int  (row.get("stock",        0))
        es_clave    = _bool (row.get("es_producto_clave", False))
        descripcion = str(row.get("descripcion", "")).strip()
        categoria   = str(row.get("categoria",   "")).strip()
        if categoria.lower() == "nan": categoria = None
        if descripcion.lower() == "nan": descripcion = None

        nuevo = Producto(
            nombre                = nombre_prod,
            descripcion           = descripcion,
            categoria             = categoria or None,
            departamento_id       = departamento_id,
            costo_usd             = costo_usd,
            margen                = margen_pct / 100.0,
            stock                 = stock,
            es_producto_clave     = es_clave,
            activo                = True,
        )
        db.add(nuevo)
        nombres_existentes.add(nombre_prod.lower())
        importados += 1

    db.commit()
    return {"importados": importados, "omitidos": omitidos, "errores": errores}


@router.get("/buscar")
def buscar_por_codigo(codigo: str, db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.codigo == codigo).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    bcv, binance = _tasas_actuales(db)
    return _enriquecer(p, bcv, binance, plantilla=_plantilla_de(p, db))


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
    datos = producto.dict()
    if not datos.get("codigo"):
        datos["codigo"] = generar_codigo(producto.nombre, db)
    nuevo = Producto(**datos)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    bcv, binance = _tasas_actuales(db)
    return _enriquecer(nuevo, bcv, binance, plantilla=_plantilla_de(nuevo, db))


@router.post("/generar-codigos-masivo")
def generar_codigos_masivo(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    sin_codigo = db.query(Producto).filter(
        (Producto.codigo == None) | (Producto.codigo == "")
    ).all()

    # Rastrear códigos asignados en esta ejecución para no depender de flush/identity map
    asignados_ahora: set[str] = set()
    actualizados = 0

    for p in sin_codigo:
        letras  = re.sub(r'[^A-Za-z]', '', p.nombre).upper()[:3].ljust(3, 'X')
        prefijo = letras + '-'

        # Números ya en BD
        existentes = db.query(Producto.codigo).filter(
            Producto.codigo.like(f"{prefijo}%")
        ).all()
        numeros = []
        for (cod,) in existentes:
            if cod:
                m = re.search(r'(\d+)$', cod)
                if m:
                    numeros.append(int(m.group(1)))

        # Números asignados en este mismo lote
        for cod in asignados_ahora:
            if cod.startswith(prefijo):
                m = re.search(r'(\d+)$', cod)
                if m:
                    numeros.append(int(m.group(1)))

        siguiente   = max(numeros) + 1 if numeros else 1
        nuevo_cod   = f"{prefijo}{siguiente:03d}"
        p.codigo    = nuevo_cod
        asignados_ahora.add(nuevo_cod)
        actualizados += 1

    db.commit()
    return {"actualizados": actualizados}


@router.post("/resetear-codigos")
def resetear_codigos(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    # Paso 1: borrar todos los códigos existentes
    todos = db.query(Producto).all()
    for p in todos:
        p.codigo = None
    db.flush()

    # Paso 2: asignar códigos nuevos con set local para evitar duplicados
    asignados_ahora: set[str] = set()
    actualizados = 0

    for p in todos:
        letras  = re.sub(r'[^A-Za-z]', '', p.nombre).upper()[:3].ljust(3, 'X')
        prefijo = letras + '-'

        # Solo los del set local (BD ya está en None para todos)
        numeros = []
        for cod in asignados_ahora:
            if cod.startswith(prefijo):
                m = re.search(r'(\d+)$', cod)
                if m:
                    numeros.append(int(m.group(1)))

        siguiente = max(numeros) + 1 if numeros else 1
        nuevo_cod = f"{prefijo}{siguiente:03d}"
        p.codigo  = nuevo_cod
        asignados_ahora.add(nuevo_cod)
        actualizados += 1

    db.commit()
    return {"actualizados": actualizados}


@router.get("/{producto_id}")
def obtener_producto(producto_id: int, db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    bcv, binance = _tasas_actuales(db)
    variantes = db.query(VarianteProducto).filter(VarianteProducto.producto_id == p.id).all()
    cat = db.query(CatalogoProveedor).filter(
        CatalogoProveedor.producto_id == p.id,
        CatalogoProveedor.codigo_proveedor != None,
    ).first()
    return _enriquecer(p, bcv, binance, variantes, plantilla=_plantilla_de(p, db),
                       tiene_catalogo=(cat is not None),
                       codigo_proveedor=cat.codigo_proveedor if cat else "")


@router.put("/edicion-masiva")
def edicion_masiva(
    items: list[dict] = Body(...),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    CAMPOS = {"nombre", "stock", "costo_usd", "margen", "descripcion", "activo", "departamento_id", "categoria_id"}
    actualizados = 0
    errores      = []
    for item in items:
        pid = item.get("id")
        if not pid:
            errores.append({"id": None, "motivo": "Falta id"})
            continue
        p = db.query(Producto).filter(Producto.id == pid).first()
        if not p:
            errores.append({"id": pid, "motivo": "Producto no encontrado"})
            continue
        for campo, valor in item.items():
            if campo in CAMPOS:
                setattr(p, campo, valor)
        actualizados += 1
    db.commit()
    return {"actualizados": actualizados, "errores": errores}


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
    return _enriquecer(p, bcv, binance, plantilla=_plantilla_de(p, db))


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
    return _enriquecer(p, bcv, binance, plantilla=_plantilla_de(p, db))


@router.put("/{producto_id}/estado")
def cambiar_estado_producto(
    producto_id: int,
    datos: dict,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    p.activo = bool(datos.get("activo", True))
    db.commit()
    db.refresh(p)
    bcv, binance = _tasas_actuales(db)
    return _enriquecer(p, bcv, binance, plantilla=_plantilla_de(p, db))


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

@router.put("/{producto_id}/esquema-variante")
def actualizar_esquema_variante(
    producto_id: int,
    datos: dict,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    esquema = datos.get("esquema_variante")
    if esquema not in ("clase", "clase_color"):
        raise HTTPException(status_code=400, detail="esquema_variante debe ser 'clase' o 'clase_color'")
    p.esquema_variante = esquema
    db.commit()
    return {"esquema_variante": p.esquema_variante}


@router.get("/{producto_id}/variantes")
def listar_variantes(producto_id: int, db: Session = Depends(get_db)):
    p = db.query(Producto).filter(Producto.id == producto_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    bcv, binance = _tasas_actuales(db)
    prov_policy_map: dict = {}
    if p.proveedor_id:
        prov = db.query(Proveedor).filter(Proveedor.id == p.proveedor_id).first()
        if prov:
            prov_policy_map[prov.id] = (
                prov.pricing_policy or "MARKET_FACTOR",
                float(prov.ajuste_divisa_pct or 0.0),
            )
    policy, ajuste = resolver_policy(
        pricing_policy_override=p.pricing_policy_override,
        proveedor_id=p.proveedor_id,
        prov_policy_map=prov_policy_map,
    )
    variantes = db.query(VarianteProducto).filter(
        VarianteProducto.producto_id == producto_id
    ).all()
    resultado = []
    for v in variantes:
        d = {c.name: getattr(v, c.name) for c in v.__table__.columns}
        d["costo_efectivo"]  = float(v.costo_usd if v.costo_usd is not None else (p.costo_usd or 0))
        d["margen_efectivo"] = float(v.margen     if v.margen    is not None else (p.margen    or 0))
        precios = calcular_precios(
            costo_usd         = d["costo_efectivo"],
            margen            = d["margen_efectivo"],
            tasa_bcv          = bcv,
            tasa_binance      = binance,
            policy            = policy,
            ajuste_divisa_pct = ajuste,
        )
        d["precio_base_usd"]        = precios["precio_base_usd"]
        d["precio_referencial_usd"] = precios["precio_referencial_usd"]
        d["precio_bs"]              = precios["precio_bs"]
        resultado.append(d)
    return resultado


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

    # Primera variante: el padre cede stock y código — las variantes son el inventario real
    es_primera = not db.query(VarianteProducto).filter(
        VarianteProducto.producto_id == producto_id
    ).first()
    if es_primera:
        p.stock  = 0
        p.codigo = None

    datos_dict = datos.model_dump()

    # Auto-generar código si no se proporcionó
    if not datos_dict.get("codigo"):
        prefijo = re.sub(r'[^A-Za-z]', '', p.nombre).upper()[:3].ljust(3, 'X') + '-V'
        existentes = db.query(VarianteProducto.codigo).filter(
            VarianteProducto.producto_id == producto_id,
            VarianteProducto.codigo.like(f"{prefijo}%"),
        ).all()
        numeros = []
        for (cod,) in existentes:
            if cod:
                m = re.search(r'(\d+)$', cod)
                if m:
                    numeros.append(int(m.group(1)))
        siguiente = max(numeros) + 1 if numeros else 1
        datos_dict["codigo"] = f"{prefijo}{siguiente:02d}"

    # Aplicar restricciones del esquema
    esquema = p.esquema_variante or "clase"
    if esquema == "clase":
        datos_dict["color"] = None
    elif esquema == "clase_color" and not datos_dict.get("color"):
        raise HTTPException(status_code=400, detail="Este esquema requiere color en cada variante")

    nueva = VarianteProducto(producto_id=producto_id, **datos_dict)
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
