from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from datetime import datetime, date
from typing import Optional, List
import json
import io

from database import get_db
from models import (
    Producto, VarianteProducto, VendedorPerfil, Usuario, HistorialAjuste,
    Departamento, Proveedor, TasaCambio,
)
from rutas.usuarios import require_admin
from pydantic import BaseModel

router = APIRouter(prefix="/ajustes", tags=["ajustes"])


# ============================================================================
# Schemas
# ============================================================================

class AjusteStockItem(BaseModel):
    producto_id: int
    tipo:        str    # "agregar" | "restar" | "fijar"
    cantidad:    float
    motivo:      str


class AjusteStockLote(BaseModel):
    items: List[AjusteStockItem]


class AjustePrecioItem(BaseModel):
    producto_id: int
    costo_usd:   Optional[float] = None
    margen:      Optional[float] = None


class AjustePrecioLote(BaseModel):
    items: List[AjustePrecioItem]


class AjusteGlobalPrecio(BaseModel):
    filtro_tipo: str            # "todos" | "departamento" | "proveedor" | "pareto"
    filtro_id:   Optional[int] = None
    tipo_ajuste: str            # "costo_pct" | "margen_fijo"
    valor:       float


class AjusteComisionItem(BaseModel):
    producto_id:  int
    comision_pct: float


class AjusteComisionLote(BaseModel):
    items: List[AjusteComisionItem]


# ============================================================================
# Helpers
# ============================================================================

def _tasas(db: Session):
    obj = db.query(TasaCambio).order_by(TasaCambio.id.desc()).first()
    if not obj:
        return 1.0, 1.0
    bcv     = float(obj.tasa or 1)
    binance = float(obj.tasa_binance or bcv)
    return bcv, binance


def _filtrar_productos(db: Session, filtro_tipo: str, filtro_id: Optional[int]):
    q = db.query(Producto)
    if filtro_tipo == "departamento" and filtro_id:
        q = q.filter(Producto.departamento_id == filtro_id)
    elif filtro_tipo == "proveedor" and filtro_id:
        q = q.filter(Producto.proveedor_id == filtro_id)
    elif filtro_tipo == "pareto":
        q = q.filter(Producto.es_producto_clave == True)
    return q.all()


def _stock_real(producto: Producto, db: Session) -> int:
    """Para productos con variantes devuelve la suma del stock de variantes."""
    variantes = db.query(VarianteProducto).filter(
        VarianteProducto.producto_id == producto.id
    ).all()
    if variantes:
        return sum(int(v.stock or 0) for v in variantes)
    return int(producto.stock or 0)


def _tiene_variantes(producto_id: int, db: Session) -> int:
    return db.query(VarianteProducto).filter(
        VarianteProducto.producto_id == producto_id
    ).count()


def _guardar_historial(db, usuario, tipo, descripcion, cambios):
    db.add(HistorialAjuste(
        usuario             = usuario or "admin",
        tipo                = tipo,
        descripcion         = descripcion,
        productos_afectados = len(cambios),
        detalle_json        = json.dumps(cambios, ensure_ascii=False),
    ))
    db.commit()


# ============================================================================
# Endpoints — rutas literales antes que cualquier /{id}
# ============================================================================

# ── Catálogo de productos con filtros ────────────────────────────────────────

@router.get("/productos")
def listar_productos_ajuste(
    filtro_tipo: str           = "todos",
    filtro_id:   Optional[int] = None,
    db: Session  = Depends(get_db),
    _: None      = Depends(require_admin),
):
    productos     = _filtrar_productos(db, filtro_tipo, filtro_id)
    bcv, binance  = _tasas(db)

    deptos_map = {d.id: d for d in db.query(Departamento).all()}
    provs_map  = {p.id: p for p in db.query(Proveedor).all()}

    result = []
    for p in productos:
        precio_base     = round(float(p.costo_usd or 0) * (1 + float(p.margen or 0)), 4)
        depto           = deptos_map.get(p.departamento_id)
        prov            = provs_map.get(p.proveedor_id)
        n_variantes     = _tiene_variantes(p.id, db)
        stock_real      = _stock_real(p, db)
        result.append({
            "id":                 p.id,
            "nombre":             p.nombre,
            "departamento_id":    p.departamento_id,
            "departamento_nombre":depto.nombre if depto else "—",
            "proveedor_id":       p.proveedor_id,
            "proveedor_nombre":   prov.nombre  if prov  else "—",
            "costo_usd":          float(p.costo_usd    or 0),
            "margen":             float(p.margen        or 0),
            "comision_pct":       float(p.comision_pct  or 0),
            "precio_base_usd":    precio_base,
            "stock":              stock_real,
            "es_producto_clave":  p.es_producto_clave,
            "tiene_variantes":    n_variantes > 0,
            "variantes_count":    n_variantes,
        })
    return result


# ── Ajuste de stock por lotes ────────────────────────────────────────────────

@router.post("/stock/lote")
def ajuste_stock_lote(
    datos: AjusteStockLote,
    db:    Session           = Depends(get_db),
    _:     None              = Depends(require_admin),
    x_usuario_nombre: Optional[str] = Header(None),
):
    cambios = []
    for item in datos.items:
        p = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if not p:
            continue
        ant = p.stock
        if item.tipo == "agregar":
            p.stock = p.stock + int(item.cantidad)
        elif item.tipo == "restar":
            p.stock = max(0, p.stock - int(item.cantidad))
        elif item.tipo == "fijar":
            p.stock = int(item.cantidad)
        cambios.append({
            "producto_id":    p.id,
            "nombre":         p.nombre,
            "stock_anterior": ant,
            "stock_nuevo":    p.stock,
            "tipo":           item.tipo,
            "motivo":         item.motivo,
        })
    db.commit()
    _guardar_historial(
        db, x_usuario_nombre, "stock",
        f"Ajuste de stock — {len(cambios)} productos", cambios,
    )
    return {"ok": True, "productos_afectados": len(cambios)}


# ── Ajuste de precios por lotes ──────────────────────────────────────────────

@router.post("/precio/lote")
def ajuste_precio_lote(
    datos: AjustePrecioLote,
    db:    Session           = Depends(get_db),
    _:     None              = Depends(require_admin),
    x_usuario_nombre: Optional[str] = Header(None),
):
    cambios = []
    for item in datos.items:
        p = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if not p:
            continue
        c_ant, m_ant = p.costo_usd, p.margen
        if item.costo_usd is not None:
            p.costo_usd = round(item.costo_usd, 4)
        if item.margen is not None:
            p.margen = round(item.margen, 6)
        cambios.append({
            "producto_id":    p.id,
            "nombre":         p.nombre,
            "costo_anterior": c_ant,
            "costo_nuevo":    p.costo_usd,
            "margen_anterior":m_ant,
            "margen_nuevo":   p.margen,
        })
    db.commit()
    _guardar_historial(
        db, x_usuario_nombre, "precio",
        f"Ajuste de precios por lotes — {len(cambios)} productos", cambios,
    )
    return {"ok": True, "productos_afectados": len(cambios)}


# ── Ajuste global de precios por filtro ──────────────────────────────────────

@router.post("/precio/global")
def ajuste_precio_global(
    datos: AjusteGlobalPrecio,
    db:    Session             = Depends(get_db),
    _:     None                = Depends(require_admin),
    x_usuario_nombre: Optional[str] = Header(None),
):
    productos = _filtrar_productos(db, datos.filtro_tipo, datos.filtro_id)
    cambios = []
    for p in productos:
        c_ant, m_ant = p.costo_usd, p.margen
        if datos.tipo_ajuste == "costo_pct":
            p.costo_usd = round(float(p.costo_usd or 0) * (1 + datos.valor / 100), 4)
        elif datos.tipo_ajuste == "margen_fijo":
            p.margen = round(datos.valor / 100, 6)
        cambios.append({
            "producto_id":    p.id,
            "nombre":         p.nombre,
            "costo_anterior": c_ant,
            "costo_nuevo":    p.costo_usd,
            "margen_anterior":m_ant,
            "margen_nuevo":   p.margen,
        })
    db.commit()
    desc = f"Ajuste global ({datos.tipo_ajuste}={datos.valor}) — {len(cambios)} productos"
    _guardar_historial(db, x_usuario_nombre, "precio", desc, cambios)
    return {"ok": True, "productos_afectados": len(cambios)}


# ── Ajuste de comisiones por lotes ───────────────────────────────────────────

@router.post("/comisiones/lote")
def ajuste_comisiones_lote(
    datos: AjusteComisionLote,
    db:    Session             = Depends(get_db),
    _:     None                = Depends(require_admin),
    x_usuario_nombre: Optional[str] = Header(None),
):
    cambios = []
    for item in datos.items:
        p = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if not p:
            continue
        ant = p.comision_pct
        p.comision_pct = round(item.comision_pct, 6)
        cambios.append({
            "producto_id":      p.id,
            "nombre":           p.nombre,
            "comision_anterior":ant,
            "comision_nueva":   p.comision_pct,
        })
    db.commit()
    _guardar_historial(
        db, x_usuario_nombre, "comision",
        f"Ajuste de comisión por producto — {len(cambios)} productos", cambios,
    )
    return {"ok": True, "productos_afectados": len(cambios)}


# ── Historial ────────────────────────────────────────────────────────────────

@router.get("/historial")
def listar_historial(
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    tipo:        Optional[str]  = None,
    db:  Session = Depends(get_db),
    _:   None    = Depends(require_admin),
):
    q = db.query(HistorialAjuste).order_by(HistorialAjuste.fecha.desc())
    if fecha_desde:
        q = q.filter(sqlfunc.date(HistorialAjuste.fecha) >= fecha_desde)
    if fecha_hasta:
        q = q.filter(sqlfunc.date(HistorialAjuste.fecha) <= fecha_hasta)
    if tipo:
        q = q.filter(HistorialAjuste.tipo == tipo)
    return [
        {
            "id":                  h.id,
            "fecha":               h.fecha.isoformat(),
            "usuario":             h.usuario,
            "tipo":                h.tipo,
            "descripcion":         h.descripcion,
            "productos_afectados": h.productos_afectados,
        }
        for h in q.all()
    ]


# ── Exportar Excel ───────────────────────────────────────────────────────────

@router.get("/exportar/excel")
def exportar_excel(
    db: Session = Depends(get_db),
    _:  None    = Depends(require_admin),
):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    registros = db.query(HistorialAjuste).order_by(HistorialAjuste.fecha.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Historial Ajustes"

    headers = ["Fecha", "Usuario", "Tipo", "Descripción", "Registros afectados"]
    ws.append(headers)

    header_fill = PatternFill("solid", fgColor="1A1A1A")
    header_font = Font(color="FFCC00", bold=True)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 12
    ws.column_dimensions["D"].width = 55
    ws.column_dimensions["E"].width = 20

    for h in registros:
        ws.append([
            h.fecha.strftime("%d/%m/%Y %H:%M") if h.fecha else "",
            h.usuario    or "",
            h.tipo       or "",
            h.descripcion or "",
            h.productos_afectados or 0,
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=historial_ajustes.xlsx"},
    )


# ── Exportar PDF ─────────────────────────────────────────────────────────────

@router.get("/exportar/pdf")
def exportar_pdf(
    db: Session = Depends(get_db),
    _:  None    = Depends(require_admin),
):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    registros = db.query(HistorialAjuste).order_by(HistorialAjuste.fecha.desc()).all()

    output = io.BytesIO()
    doc    = SimpleDocTemplate(output, pagesize=landscape(A4), topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Historial de Ajustes — Ferreutil", styles["Title"]),
        Spacer(1, 12),
    ]

    data = [["Fecha", "Usuario", "Tipo", "Descripción", "Afectados"]]
    for h in registros:
        data.append([
            h.fecha.strftime("%d/%m/%Y %H:%M") if h.fecha else "",
            h.usuario    or "",
            h.tipo       or "",
            (h.descripcion or "")[:70],
            str(h.productos_afectados or 0),
        ])

    tbl = Table(data, colWidths=[110, 80, 60, 310, 60])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1A1A1A")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.HexColor("#FFCC00")),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F0")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#DDDDDD")),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(tbl)

    doc.build(elements)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=historial_ajustes.pdf"},
    )
