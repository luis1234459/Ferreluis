from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from datetime import datetime, date
from typing import Optional

from database import get_db
from models import (
    VendedorPerfil, ComisionEspecial, ComisionVenta,
    PeriodoComision, Usuario, Producto,
)
from rutas.usuarios import require_admin

router = APIRouter(prefix="/vendedores", tags=["vendedores"])


# ============================================================================
# Schemas
# ============================================================================

from pydantic import BaseModel


class PerfilSchema(BaseModel):
    usuario_id:   int
    periodo_pago: str   = "quincenal"
    comision_base: float = 0.0
    activo:       bool  = True

    class Config:
        from_attributes = True


class ComisionEspecialSchema(BaseModel):
    vendedor_id:   int
    tipo:          str           # departamento | proveedor | pareto | producto
    referencia_id: Optional[int] = None
    porcentaje:    float

    class Config:
        from_attributes = True


class PeriodoSchema(BaseModel):
    vendedor_id:  int
    fecha_inicio: date
    fecha_fin:    date

    class Config:
        from_attributes = True


class PagarPeriodoSchema(BaseModel):
    observacion: Optional[str] = None


# ============================================================================
# Lógica de cálculo de comisión
# ============================================================================

def calcular_porcentaje_comision(vendedor_id: int, producto: Producto, db: Session) -> tuple[float, str]:
    """
    Retorna (porcentaje, tipo_regla).
    Aplica la regla con el porcentaje más alto encontrado.
    Orden de evaluación: producto → departamento → proveedor → pareto → base
    """
    perfil = db.query(VendedorPerfil).filter(VendedorPerfil.id == vendedor_id).first()
    comision_base = float(perfil.comision_base or 0) if perfil else 0.0

    especiales = db.query(ComisionEspecial).filter(
        ComisionEspecial.vendedor_id == vendedor_id
    ).all()

    candidatos = [( comision_base, "base" )]

    if producto.comision_pct and producto.comision_pct > 0:
        candidatos.append((producto.comision_pct, "producto_directo"))

    for ce in especiales:
        if ce.tipo == "producto" and ce.referencia_id == producto.id:
            candidatos.append((ce.porcentaje, "producto"))
        elif ce.tipo == "departamento" and producto.departamento_id and ce.referencia_id == producto.departamento_id:
            candidatos.append((ce.porcentaje, "departamento"))
        elif ce.tipo == "proveedor" and producto.proveedor_id and ce.referencia_id == producto.proveedor_id:
            candidatos.append((ce.porcentaje, "proveedor"))
        elif ce.tipo == "pareto" and producto.es_producto_clave:
            candidatos.append((ce.porcentaje, "pareto"))

    return max(candidatos, key=lambda x: x[0])


# ============================================================================
# IMPORTANTE: rutas literales ANTES que /{id}
# ============================================================================

# ── Períodos (literal /periodos/ antes que /{id}) ───────────────────────────

@router.get("/periodos/")
def listar_periodos(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    periodos = db.query(PeriodoComision).order_by(PeriodoComision.fecha_inicio.desc()).all()
    result = []
    for p in periodos:
        vendedor = db.query(VendedorPerfil).filter(VendedorPerfil.id == p.vendedor_id).first()
        usuario_nombre = "—"
        if vendedor:
            u = db.query(Usuario).filter(Usuario.id == vendedor.usuario_id).first()
            usuario_nombre = u.nombre if u else "—"
        result.append({
            "id":               p.id,
            "vendedor_id":      p.vendedor_id,
            "vendedor_nombre":  usuario_nombre,
            "fecha_inicio":     str(p.fecha_inicio),
            "fecha_fin":        str(p.fecha_fin),
            "total_ventas_usd": p.total_ventas_usd,
            "total_comision":   p.total_comision,
            "estado":           p.estado,
            "fecha_pago":       p.fecha_pago.isoformat() if p.fecha_pago else None,
            "pagado_por":       p.pagado_por,
            "observacion":      p.observacion,
        })
    return result


@router.post("/periodos/")
def crear_periodo(
    datos: PeriodoSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    # Calcular totales del período
    comisiones = db.query(ComisionVenta).filter(
        ComisionVenta.vendedor_id == datos.vendedor_id,
        sqlfunc.date(ComisionVenta.fecha) >= datos.fecha_inicio,
        sqlfunc.date(ComisionVenta.fecha) <= datos.fecha_fin,
    ).all()

    total_ventas  = sum(c.monto_venta_usd  for c in comisiones)
    total_comision= sum(c.monto_comision   for c in comisiones)

    periodo = PeriodoComision(
        vendedor_id      = datos.vendedor_id,
        fecha_inicio     = datos.fecha_inicio,
        fecha_fin        = datos.fecha_fin,
        total_ventas_usd = round(total_ventas,   4),
        total_comision   = round(total_comision, 4),
    )
    db.add(periodo)
    db.commit()
    db.refresh(periodo)
    return periodo


@router.put("/periodos/{periodo_id}/pagar")
def pagar_periodo(
    periodo_id: int,
    datos: PagarPeriodoSchema,
    db: Session = Depends(get_db),
    x_usuario_rol: Optional[str] = Header(None),
    x_usuario_nombre: Optional[str] = Header(None),
):
    if x_usuario_rol != "admin":
        raise HTTPException(status_code=403, detail="Solo admin puede marcar períodos como pagados")
    periodo = db.query(PeriodoComision).filter(PeriodoComision.id == periodo_id).first()
    if not periodo:
        raise HTTPException(status_code=404, detail="Período no encontrado")
    if periodo.estado == "pagado":
        raise HTTPException(status_code=400, detail="El período ya está marcado como pagado")
    periodo.estado      = "pagado"
    periodo.fecha_pago  = datetime.now()
    periodo.pagado_por  = x_usuario_nombre or "admin"
    periodo.observacion = datos.observacion
    db.commit()
    db.refresh(periodo)
    return periodo


# ── Comisiones especiales (literales antes que /{id}) ───────────────────────

@router.delete("/comisiones/{comision_id}")
def eliminar_comision_especial(
    comision_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    ce = db.query(ComisionEspecial).filter(ComisionEspecial.id == comision_id).first()
    if not ce:
        raise HTTPException(status_code=404, detail="Comisión no encontrada")
    db.delete(ce)
    db.commit()
    return {"ok": True}


# ── Perfiles (CRUD principal) ────────────────────────────────────────────────

@router.get("/")
def listar_vendedores(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    perfiles = db.query(VendedorPerfil).all()
    result = []
    for p in perfiles:
        u = db.query(Usuario).filter(Usuario.id == p.usuario_id).first()
        result.append({
            "id":           p.id,
            "usuario_id":   p.usuario_id,
            "usuario_nombre": u.nombre if u else "—",
            "usuario_email":  u.email  if u else "—",
            "periodo_pago": p.periodo_pago,
            "comision_base":p.comision_base,
            "activo":       p.activo,
        })
    return result


@router.post("/")
def crear_vendedor(
    datos: PerfilSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    existe = db.query(VendedorPerfil).filter(
        VendedorPerfil.usuario_id == datos.usuario_id
    ).first()
    if existe:
        raise HTTPException(status_code=400, detail="Este usuario ya tiene perfil de vendedor")
    perfil = VendedorPerfil(**datos.dict())
    db.add(perfil)
    db.commit()
    db.refresh(perfil)
    return perfil


@router.put("/{vendedor_id}")
def editar_vendedor(
    vendedor_id: int,
    datos: PerfilSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    perfil = db.query(VendedorPerfil).filter(VendedorPerfil.id == vendedor_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    for k, v in datos.dict().items():
        setattr(perfil, k, v)
    db.commit()
    db.refresh(perfil)
    return perfil


# ── Comisiones especiales por vendedor ──────────────────────────────────────

@router.get("/{vendedor_id}/comisiones")
def listar_comisiones_especiales(
    vendedor_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    return db.query(ComisionEspecial).filter(
        ComisionEspecial.vendedor_id == vendedor_id
    ).all()


@router.post("/{vendedor_id}/comisiones")
def agregar_comision_especial(
    vendedor_id: int,
    datos: ComisionEspecialSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    perfil = db.query(VendedorPerfil).filter(VendedorPerfil.id == vendedor_id).first()
    if not perfil:
        raise HTTPException(status_code=404, detail="Vendedor no encontrado")
    ce = ComisionEspecial(
        vendedor_id   = vendedor_id,
        tipo          = datos.tipo,
        referencia_id = datos.referencia_id,
        porcentaje    = datos.porcentaje,
    )
    db.add(ce)
    db.commit()
    db.refresh(ce)
    return ce


# ── Resumen y ventas del día ─────────────────────────────────────────────────

@router.get("/{vendedor_id}/resumen")
def resumen_vendedor(
    vendedor_id: int,
    db: Session = Depends(get_db),
):
    hoy = date.today()

    comisiones_hoy = db.query(ComisionVenta).filter(
        ComisionVenta.vendedor_id == vendedor_id,
        sqlfunc.date(ComisionVenta.fecha) == hoy,
    ).all()

    comision_hoy      = round(sum(c.monto_comision  for c in comisiones_hoy), 4)
    ventas_usd_hoy    = round(sum(c.monto_venta_usd for c in comisiones_hoy), 4)

    # Período activo (el más reciente pendiente que incluye hoy)
    periodo_activo = db.query(PeriodoComision).filter(
        PeriodoComision.vendedor_id == vendedor_id,
        PeriodoComision.estado      == "pendiente",
        PeriodoComision.fecha_inicio <= hoy,
        PeriodoComision.fecha_fin   >= hoy,
    ).order_by(PeriodoComision.fecha_inicio.desc()).first()

    return {
        "vendedor_id":        vendedor_id,
        "comision_hoy":       comision_hoy,
        "ventas_usd_hoy":     ventas_usd_hoy,
        "cantidad_ventas_hoy":len(set(c.venta_id for c in comisiones_hoy)),
        "periodo_activo": {
            "id":             periodo_activo.id,
            "fecha_inicio":   str(periodo_activo.fecha_inicio),
            "fecha_fin":      str(periodo_activo.fecha_fin),
            "total_comision": periodo_activo.total_comision,
            "estado":         periodo_activo.estado,
        } if periodo_activo else None,
    }


@router.get("/{vendedor_id}/ventas-hoy")
def ventas_hoy_vendedor(
    vendedor_id: int,
    db: Session = Depends(get_db),
):
    hoy = date.today()
    comisiones = db.query(ComisionVenta).filter(
        ComisionVenta.vendedor_id == vendedor_id,
        sqlfunc.date(ComisionVenta.fecha) == hoy,
    ).order_by(ComisionVenta.fecha.asc()).all()

    result = []
    for c in comisiones:
        prod = db.query(Producto).filter(Producto.id == c.producto_id).first()
        result.append({
            "id":                  c.id,
            "venta_id":            c.venta_id,
            "producto_id":         c.producto_id,
            "producto_nombre":     prod.nombre if prod else "—",
            "monto_venta_usd":     c.monto_venta_usd,
            "porcentaje_aplicado": c.porcentaje_aplicado,
            "monto_comision":      c.monto_comision,
            "tipo_regla":          c.tipo_regla,
            "fecha":               c.fecha.isoformat(),
        })
    return result
