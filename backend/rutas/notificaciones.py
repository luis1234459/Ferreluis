"""
Módulo de notificaciones: avisos del admin y radar de demanda.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Aviso, DemandaRegistro, Producto
from rutas.usuarios import require_admin, get_current_user
from datetime import datetime, date

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


# ── AVISOS ────────────────────────────────────────────────────────────────────

@router.get("/avisos")
def listar_avisos(usuario: str = "", db: Session = Depends(get_db)):
    """Devuelve avisos activos para el usuario (generales + específicos para él)."""
    q = db.query(Aviso).filter(Aviso.activo == True)
    if usuario:
        from sqlalchemy import or_
        q = q.filter(or_(Aviso.destinatario == None, Aviso.destinatario == usuario))
    return q.order_by(Aviso.fecha.desc()).limit(50).all()


@router.post("/avisos")
def crear_aviso(datos: dict, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    if not datos.get("titulo") or not datos.get("mensaje"):
        raise HTTPException(status_code=400, detail="Título y mensaje son obligatorios")
    aviso = Aviso(
        titulo       = datos["titulo"],
        mensaje      = datos["mensaje"],
        creado_por   = datos.get("creado_por", "admin"),
        destinatario = datos.get("destinatario") or None,
    )
    db.add(aviso)
    db.commit()
    db.refresh(aviso)
    return aviso


@router.delete("/avisos/{aviso_id}")
def eliminar_aviso(aviso_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    a = db.query(Aviso).filter(Aviso.id == aviso_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Aviso no encontrado")
    a.activo = False
    db.commit()
    return {"ok": True}


@router.get("/avisos/count")
def count_avisos(usuario: str = "", db: Session = Depends(get_db)):
    """Cantidad de avisos activos — para el badge del sidebar."""
    from sqlalchemy import or_
    q = db.query(func.count(Aviso.id)).filter(Aviso.activo == True)
    if usuario:
        q = q.filter(or_(Aviso.destinatario == None, Aviso.destinatario == usuario))
    return {"count": q.scalar()}


# ── RADAR DE DEMANDA ──────────────────────────────────────────────────────────

@router.post("/demanda")
def registrar_demanda(datos: dict, db: Session = Depends(get_db)):
    tipo = datos.get("tipo")
    if tipo not in ("venta_perdida", "consulta", "alerta_precio"):
        raise HTTPException(status_code=400, detail="Tipo inválido")

    registro = DemandaRegistro(
        tipo               = tipo,
        producto_id        = datos.get("producto_id"),
        nombre_producto    = datos.get("nombre_producto", ""),
        cantidad           = datos.get("cantidad"),
        competencia        = datos.get("competencia"),
        precio_competencia = datos.get("precio_competencia"),
        vendedor           = datos.get("vendedor", ""),
        observacion        = datos.get("observacion"),
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro


@router.get("/demanda")
def listar_demanda(
    fecha: str = "",
    visto: str = "",
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    q = db.query(DemandaRegistro)
    if fecha:
        dia = date.fromisoformat(fecha)
        q = q.filter(func.date(DemandaRegistro.fecha) == dia)
    if visto == "no":
        q = q.filter(DemandaRegistro.visto_por_admin == False)
    registros = q.order_by(DemandaRegistro.fecha.desc()).all()

    resultado = []
    for r in registros:
        item = {
            "id":                r.id,
            "tipo":              r.tipo,
            "producto_id":       r.producto_id,
            "nombre_producto":   r.nombre_producto,
            "cantidad":          r.cantidad,
            "competencia":       r.competencia,
            "precio_competencia":r.precio_competencia,
            "vendedor":          r.vendedor,
            "fecha":             r.fecha.isoformat() if r.fecha else None,
            "visto_por_admin":   r.visto_por_admin,
            "observacion":       r.observacion,
            "precio_sistema":    None,
        }
        if r.producto_id:
            p = db.query(Producto).filter(Producto.id == r.producto_id).first()
            if p:
                item["precio_sistema"] = float(p.costo_usd or 0) * (1 + float(p.margen or 0))
        resultado.append(item)
    return resultado


@router.get("/demanda/resumen")
def resumen_demanda(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    """Resumen del día agrupado por producto."""
    hoy = date.today()
    registros = db.query(DemandaRegistro).filter(
        func.date(DemandaRegistro.fecha) == hoy
    ).all()

    agrupado = {}
    for r in registros:
        key = r.nombre_producto
        if key not in agrupado:
            agrupado[key] = {
                "nombre_producto":  r.nombre_producto,
                "producto_id":      r.producto_id,
                "consultas":        0,
                "ventas_perdidas":  0,
                "cantidad_perdida": 0,
                "alertas_precio":   [],
            }
        if r.tipo == "consulta":
            agrupado[key]["consultas"] += 1
        elif r.tipo == "venta_perdida":
            agrupado[key]["ventas_perdidas"] += 1
            agrupado[key]["cantidad_perdida"] += float(r.cantidad or 0)
        elif r.tipo == "alerta_precio":
            agrupado[key]["alertas_precio"].append({
                "competencia": r.competencia,
                "precio":      r.precio_competencia,
            })

    return sorted(agrupado.values(), key=lambda x: x["ventas_perdidas"], reverse=True)


@router.patch("/demanda/{registro_id}/visto")
def marcar_visto(registro_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    r = db.query(DemandaRegistro).filter(DemandaRegistro.id == registro_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    r.visto_por_admin = True
    db.commit()
    return {"ok": True}


@router.get("/demanda/count-nuevos")
def count_demanda_nuevos(db: Session = Depends(get_db)):
    """Cantidad de registros no vistos — para badge del admin."""
    count = db.query(func.count(DemandaRegistro.id)).filter(
        DemandaRegistro.visto_por_admin == False
    ).scalar()
    return {"count": count}
