"""
Ficha de reposición por producto.

El CRUD de proveedores NO vive acá — ya existe en rutas/compras.py
(GET/POST/PUT /compras/proveedores), solo se le agregaron los campos
lead_time_dias_default y notas. Acá solo la ficha 1:1 + sus proveedores.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Producto, Proveedor, ProductoProveedor, ProductoReposicion
from reposicion import obtener_ficha_reposicion, MODOS_VALIDOS
from rutas.usuarios import require_admin_o_gestionador

router = APIRouter(prefix="/productos", tags=["reposicion"])


def _validar_payload(datos: dict):
    modo = datos.get("modo_reposicion")
    if modo not in MODOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=(f"modo_reposicion inválido: '{modo}'. "
                    f"Valores válidos: {', '.join(sorted(MODOS_VALIDOS))}"),
        )

    proveedores = datos.get("proveedores", []) or []
    if len(proveedores) > 3:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo 3 proveedores por producto (recibidos: {len(proveedores)})",
        )

    prioridades_vistas = set()
    for item in proveedores:
        prioridad = item.get("prioridad")
        if prioridad not in (1, 2, 3):
            raise HTTPException(
                status_code=400,
                detail=f"Prioridad inválida: {prioridad}. Debe ser 1 (principal), 2 (alternativo) o 3 (terciario)",
            )
        if prioridad in prioridades_vistas:
            raise HTTPException(
                status_code=400,
                detail=f"Prioridad {prioridad} repetida — cada proveedor debe tener una prioridad distinta",
            )
        prioridades_vistas.add(prioridad)
        if not item.get("proveedor_id"):
            raise HTTPException(status_code=400, detail="Cada proveedor debe tener proveedor_id")

    return modo, proveedores


@router.get("/{producto_id}/reposicion")
def get_reposicion(producto_id: int, db: Session = Depends(get_db)):
    resultado = obtener_ficha_reposicion(db, producto_id)
    if resultado is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return resultado


def _validar_ficha_para_guardar(db: Session, producto_id: int, datos: dict) -> tuple[str, list]:
    """Valida producto + payload de una ficha. Lanza HTTPException si algo falla."""
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    modo, proveedores_in = _validar_payload(datos)

    ids_pedidos = [item["proveedor_id"] for item in proveedores_in]
    if ids_pedidos:
        existentes = {p.id for p in db.query(Proveedor.id).filter(Proveedor.id.in_(ids_pedidos)).all()}
        faltantes = set(ids_pedidos) - existentes
        if faltantes:
            raise HTTPException(
                status_code=400,
                detail=f"Proveedor(es) no encontrado(s): {sorted(faltantes)}",
            )
    return modo, proveedores_in


def _guardar_ficha(db: Session, producto_id: int, datos: dict, modo: str, proveedores_in: list) -> None:
    """Upsert de ProductoReposicion + reemplazo de ProductoProveedor. No commitea."""
    ficha = db.query(ProductoReposicion).filter(ProductoReposicion.producto_id == producto_id).first()
    if not ficha:
        ficha = ProductoReposicion(producto_id=producto_id)
        db.add(ficha)

    ficha.modo_reposicion     = modo
    ficha.stock_min_objetivo  = int(datos.get("stock_min_objetivo", 0) or 0)
    ficha.stock_max_objetivo  = int(datos.get("stock_max_objetivo", 0) or 0)
    ficha.unidades_exhibicion = int(datos.get("unidades_exhibicion", 0) or 0)
    ficha.colchon_dias        = int(datos.get("colchon_dias", 3) or 0)
    ficha.activo              = bool(datos.get("activo", True))
    ficha.notas               = datos.get("notas")

    # Estado previo por proveedor, para decidir si sin_stock_fecha se
    # setea/limpia automáticamente al cambiar el flag.
    anteriores = {
        pp.proveedor_id: pp
        for pp in db.query(ProductoProveedor).filter(ProductoProveedor.producto_id == producto_id).all()
    }

    db.query(ProductoProveedor).filter(ProductoProveedor.producto_id == producto_id).delete()
    db.flush()

    for item in proveedores_in:
        proveedor_id     = item["proveedor_id"]
        sin_stock_nuevo  = bool(item.get("sin_stock_declarado", False))
        anterior         = anteriores.get(proveedor_id)
        sin_stock_previo = bool(anterior.sin_stock_declarado) if anterior else False

        if sin_stock_nuevo and not sin_stock_previo:
            sin_stock_fecha = date.today()          # false -> true: se asienta hoy
        elif not sin_stock_nuevo and sin_stock_previo:
            sin_stock_fecha = None                  # true -> false: se limpia sola
        elif anterior:
            sin_stock_fecha = anterior.sin_stock_fecha   # sin cambios: se preserva
        else:
            sin_stock_fecha = date.today() if sin_stock_nuevo else None

        db.add(ProductoProveedor(
            producto_id=producto_id,
            proveedor_id=proveedor_id,
            prioridad=item["prioridad"],
            precio_actual_usd=item.get("precio_actual_usd"),
            credito_dias=item.get("credito_dias"),
            lead_time_dias=item.get("lead_time_dias"),
            minimo_compra=item.get("minimo_compra"),
            notas=item.get("notas"),
            sin_stock_declarado=sin_stock_nuevo,
            sin_stock_fecha=sin_stock_fecha,
        ))


@router.put("/{producto_id}/reposicion")
def put_reposicion(
    producto_id: int,
    datos: dict,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_o_gestionador),
):
    modo, proveedores_in = _validar_ficha_para_guardar(db, producto_id, datos)

    try:
        _guardar_ficha(db, producto_id, datos, modo, proveedores_in)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar la ficha de reposición: {e}")

    return obtener_ficha_reposicion(db, producto_id)


@router.put("/reposicion/bulk")
def put_reposicion_bulk(
    payload: dict,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_o_gestionador),
):
    """
    Guardado en lote para la vista tabla de reposición. Una sola transacción:
    si cualquier ficha falla la validación, no se guarda ninguna (rollback total)
    y se devuelve la lista completa de errores por producto_id.
    """
    fichas = payload.get("fichas", []) or []
    if not fichas:
        raise HTTPException(status_code=400, detail="No se recibieron fichas para guardar")

    validadas = []   # [(producto_id, datos, modo, proveedores_in), ...]
    errores   = []
    for item in fichas:
        producto_id = item.get("producto_id")
        try:
            modo, proveedores_in = _validar_ficha_para_guardar(db, producto_id, item)
            validadas.append((producto_id, item, modo, proveedores_in))
        except HTTPException as e:
            errores.append({"producto_id": producto_id, "detail": e.detail})

    if errores:
        raise HTTPException(status_code=400, detail={"errores": errores})

    try:
        for producto_id, item, modo, proveedores_in in validadas:
            _guardar_ficha(db, producto_id, item, modo, proveedores_in)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al guardar el lote de reposición: {e}")

    return {
        "actualizadas": [
            obtener_ficha_reposicion(db, producto_id) for producto_id, *_ in validadas
        ]
    }
