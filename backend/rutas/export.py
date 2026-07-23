"""
Export del catálogo completo con métricas de venta por producto.
Única fuente confiable: ventas. Stock referencial (solo confiable si auditado),
sin valor de inventario, sin flag Pareto (descalibrado). Insumo base para
recalibrar Pareto externamente y definir el surtido de la sede nueva.
"""
import csv
import io
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Departamento, Categoria, Marca, Producto,
    Venta, DetalleVenta, DevolucionCliente, DetalleDevolucionCliente,
)
from rutas.usuarios import require_admin
from rutas.auth import mapa_existencia_por_sede

router = APIRouter(prefix="/export", tags=["export"])


def _num(x):
    return float(x or 0)


@router.get("/catalogo")
def export_catalogo(
    dias_corto: int = Query(90, gt=0, le=730),
    dias_largo: int = Query(365, gt=0, le=1825),
    formato: str = Query("json", pattern="^(json|csv)$"),
    sede_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    corte   = datetime.utcnow()
    d_corto = corte - timedelta(days=dias_corto)
    d_largo = corte - timedelta(days=dias_largo)

    # ── Catálogo base (completo, incluye inactivos y sin ventas) ───────────
    productos_db  = db.query(Producto).all()
    departamentos = db.query(Departamento).all()
    categorias    = db.query(Categoria).all()
    marcas        = db.query(Marca).all()
    mapa_ex       = mapa_existencia_por_sede(db) if sede_id else {}

    # ── Última venta por producto, sin límite de ventana ────────────────────
    q_ultima = (
        db.query(DetalleVenta.producto_id, func.max(Venta.fecha))
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .filter(Venta.estado != 'anulada')
    )
    if sede_id:
        q_ultima = q_ultima.filter(Venta.sede_id == sede_id)
    ultima_venta_map = dict(q_ultima.group_by(DetalleVenta.producto_id).all())

    # ── Líneas de venta dentro de la ventana larga (incluye la corta) ──────
    q_filas_venta = (
        db.query(DetalleVenta.producto_id, DetalleVenta.cantidad,
                  DetalleVenta.precio_unitario, Venta.id, Venta.fecha)
        .join(Venta, Venta.id == DetalleVenta.venta_id)
        .filter(Venta.fecha >= d_largo, Venta.fecha < corte, Venta.estado != 'anulada')
    )
    if sede_id:
        q_filas_venta = q_filas_venta.filter(Venta.sede_id == sede_id)
    filas_venta = q_filas_venta.all()

    agregados: dict = {}
    tickets_90d_global = set()
    tickets_12m_global = set()

    def _agregado(pid):
        return agregados.setdefault(pid, {
            'usd_90d': 0.0, 'usd_12m': 0.0,
            'uds_90d': 0.0, 'uds_12m': 0.0,
            'tk_90d': set(), 'tk_12m': set(),
        })

    for producto_id, cantidad, precio_unitario, venta_id, fecha in filas_venta:
        a = _agregado(producto_id)
        monto = _num(precio_unitario) * _num(cantidad)
        a['usd_12m'] += monto
        a['uds_12m'] += _num(cantidad)
        a['tk_12m'].add(venta_id)
        tickets_12m_global.add(venta_id)
        if fecha >= d_corto:
            a['usd_90d'] += monto
            a['uds_90d'] += _num(cantidad)
            a['tk_90d'].add(venta_id)
            tickets_90d_global.add(venta_id)

    # ── Devoluciones dentro de la ventana larga: se restan ──────────────────
    # DevolucionCliente no tiene sede_id propio (igual que movimientos_bancarios,
    # ver Fase 1I) pero si tiene venta_id — con filtro de sede, solo se restan
    # las devoluciones de ventas de esa sede (join a Venta.sede_id), para no
    # contaminar el neto de una sede con devoluciones de otra.
    q_filas_dev = (
        db.query(DetalleDevolucionCliente.producto_id, DetalleDevolucionCliente.cantidad,
                  DetalleDevolucionCliente.precio_unitario, DevolucionCliente.fecha)
        .join(DevolucionCliente, DevolucionCliente.id == DetalleDevolucionCliente.devolucion_id)
        .filter(DevolucionCliente.fecha >= d_largo, DevolucionCliente.fecha < corte)
    )
    if sede_id:
        q_filas_dev = q_filas_dev.join(Venta, Venta.id == DevolucionCliente.venta_id).filter(Venta.sede_id == sede_id)
    filas_dev = q_filas_dev.all()
    for producto_id, cantidad, precio_unitario, fecha in filas_dev:
        a = _agregado(producto_id)
        monto = _num(precio_unitario) * _num(cantidad)
        a['usd_12m'] -= monto
        a['uds_12m'] -= _num(cantidad)
        if fecha >= d_corto:
            a['usd_90d'] -= monto
            a['uds_90d'] -= _num(cantidad)

    # ── Totales globales de venta: sobre TODA la actividad, incluida la de
    #    productos que ya no existen en el catálogo (p.ej. borrados por tener
    #    stock cero). Así el total refleja las ventas reales del período,
    #    no solo las del catálogo vigente. ──────────────────────────────────
    ventas_90d_usd_global = round(sum(a['usd_90d'] for a in agregados.values()), 2)
    ventas_12m_usd_global = round(sum(a['usd_12m'] for a in agregados.values()), 2)
    unidades_90d_global   = round(sum(a['uds_90d'] for a in agregados.values()), 2)
    unidades_12m_global   = round(sum(a['uds_12m'] for a in agregados.values()), 2)

    # ── Ensamblar productos (solo catálogo vigente) ─────────────────────────
    productos = []
    totales = {
        "productos": 0, "productos_con_venta_12m": 0, "productos_auditados": 0,
        "ventas_90d_usd": ventas_90d_usd_global, "ventas_12m_usd": ventas_12m_usd_global,
        "unidades_90d": unidades_90d_global, "unidades_12m": unidades_12m_global,
        "tickets_90d": len(tickets_90d_global),
        "tickets_12m": len(tickets_12m_global),
    }

    for p in productos_db:
        a = agregados.get(p.id, {})
        ultima = ultima_venta_map.get(p.id)
        fila = {
            "id":                p.id,
            "codigo":            p.codigo,
            "nombre":            p.nombre,
            "categoria_id":      p.categoria_id,
            "departamento_id":   p.departamento_id,
            "marca_id":          p.marca_id,
            "ventas_90d_usd":    round(a.get('usd_90d', 0.0), 2),
            "ventas_12m_usd":    round(a.get('usd_12m', 0.0), 2),
            "unidades_90d":      round(a.get('uds_90d', 0.0), 2),
            "unidades_12m":      round(a.get('uds_12m', 0.0), 2),
            "tickets_90d":       len(a.get('tk_90d', ())),
            "tickets_12m":       len(a.get('tk_12m', ())),
            "ultima_venta":      ultima.date().isoformat() if ultima else None,
            "existencia_sistema":mapa_ex.get(p.id, {}).get(sede_id, 0.0) if sede_id else _num(p.stock),
            "stock_auditado":    bool(p.auditado),
            "fecha_auditoria":   p.fecha_auditoria.isoformat() if p.fecha_auditoria else None,
        }
        productos.append(fila)
        totales["productos"] += 1
        if fila["tickets_12m"] > 0:
            totales["productos_con_venta_12m"] += 1
        if fila["stock_auditado"]:
            totales["productos_auditados"] += 1

    advertencias = ["existencia_sistema solo es confiable en productos con stock_auditado=true"]
    ids_catalogo = {p.id for p in productos_db}
    huerfanos = (set(agregados) | set(ultima_venta_map)) - ids_catalogo
    if huerfanos:
        advertencias.append(
            f"{len(huerfanos)} producto_id con ventas/devoluciones no existen en el catálogo actual"
        )

    if formato == "csv":
        nombre_dep   = {d.id: d.nombre for d in departamentos}
        nombre_cat   = {c.id: c.nombre for c in categorias}
        nombre_marca = {m.id: m.nombre for m in marcas}
        buf = io.StringIO()
        campos = ["id", "codigo", "nombre", "departamento", "categoria", "marca",
                  "ventas_90d_usd", "ventas_12m_usd", "unidades_90d", "unidades_12m",
                  "tickets_90d", "tickets_12m", "ultima_venta", "existencia_sistema",
                  "stock_auditado", "fecha_auditoria"]
        w = csv.DictWriter(buf, fieldnames=campos)
        w.writeheader()
        for f in productos:
            w.writerow({
                **{k: f[k] for k in campos if k in f},
                "departamento": nombre_dep.get(f["departamento_id"], ""),
                "categoria":    nombre_cat.get(f["categoria_id"], ""),
                "marca":        nombre_marca.get(f["marca_id"], ""),
            })
        buf.seek(0)
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="catalogo_ferreutil.csv"'},
        )

    return {
        "generado_en": corte.isoformat() + "Z",
        "ventanas": {
            "corto": {"desde": d_corto.isoformat() + "Z", "hasta": corte.isoformat() + "Z",
                      "dias": dias_corto},
            "largo": {"desde": d_largo.isoformat() + "Z", "hasta": corte.isoformat() + "Z",
                      "dias": dias_largo},
        },
        "totales": totales,
        "departamentos": [{"id": d.id, "nombre": d.nombre, "padre_id": None} for d in departamentos],
        "categorias":    [{"id": c.id, "nombre": c.nombre, "departamento_id": c.departamento_id} for c in categorias],
        "marcas":        [{"id": m.id, "nombre": m.nombre} for m in marcas],
        "productos": productos,
        "advertencias": advertencias,
    }
