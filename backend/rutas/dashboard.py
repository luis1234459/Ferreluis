from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from datetime import date, datetime, timedelta
import models

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumen")
def resumen_dashboard(db: Session = Depends(get_db)):
    hoy = date.today()
    inicio_hoy = datetime.combine(hoy, datetime.min.time())
    fin_hoy    = datetime.combine(hoy, datetime.max.time())

    # ── Ventas de hoy ─────────────────────────────────────────────────────────
    ventas_hoy_list = db.query(models.Venta).filter(
        models.Venta.fecha >= inicio_hoy,
        models.Venta.fecha <= fin_hoy,
        models.Venta.estado != "anulada",
    ).all()

    ventas_hoy_count    = len(ventas_hoy_list)
    total_hoy_usd       = sum(v.total for v in ventas_hoy_list if v.moneda_venta == "USD")
    total_hoy_bs        = sum(v.total for v in ventas_hoy_list if v.moneda_venta == "Bs")
    ticket_promedio_usd = round(total_hoy_usd / ventas_hoy_count, 2) if ventas_hoy_count > 0 else 0

    ids_hoy = [v.id for v in ventas_hoy_list]

    unidades_hoy = 0
    clientes_hoy = 0
    comision_hoy = 0.0

    if ids_hoy:
        unidades_hoy = db.query(func.sum(models.DetalleVenta.cantidad)).filter(
            models.DetalleVenta.venta_id.in_(ids_hoy)
        ).scalar() or 0

        clientes_hoy = db.query(func.count(func.distinct(models.VentaCliente.cliente_id))).filter(
            models.VentaCliente.venta_id.in_(ids_hoy)
        ).scalar() or 0

        comision_hoy = db.query(func.sum(models.ComisionVenta.monto_comision)).filter(
            models.ComisionVenta.venta_id.in_(ids_hoy)
        ).scalar() or 0.0

    # ── Inventario ────────────────────────────────────────────────────────────
    productos = db.query(models.Producto).all()
    total_productos       = len(productos)
    productos_stock_bajo  = sum(1 for p in productos if 0 < (p.stock or 0) < 5)
    productos_sin_stock   = sum(1 for p in productos if (p.stock or 0) <= 0)
    valor_inventario_usd  = sum((p.costo_usd or 0) * (p.stock or 0) for p in productos)

    # ── Comisiones pendientes ─────────────────────────────────────────────────
    comisiones_pendientes = db.query(func.sum(models.PeriodoComision.total_comision)).filter(
        models.PeriodoComision.estado == "pendiente"
    ).scalar() or 0.0

    # ── Tasa de cambio ────────────────────────────────────────────────────────
    tasa = db.query(models.TasaCambio).order_by(models.TasaCambio.id.desc()).first()
    tasa_bcv     = tasa.tasa         if tasa else 0
    tasa_binance = tasa.tasa_binance if tasa else 0
    factor       = round(tasa_binance / tasa_bcv, 4) if tasa_bcv else 1.0

    # ── Alertas ───────────────────────────────────────────────────────────────
    alertas = []

    if productos_sin_stock > 0:
        alertas.append({"tipo": "sin_stock",  "mensaje": f"{productos_sin_stock} producto(s) sin stock"})
    if productos_stock_bajo > 0:
        alertas.append({"tipo": "stock_bajo", "mensaje": f"{productos_stock_bajo} producto(s) con stock bajo (< 5 unid.)"})

    facturas_vencidas = db.query(models.RecepcionCompra).filter(
        models.RecepcionCompra.fecha_vencimiento_pago.isnot(None),
        models.RecepcionCompra.estado_pago == "vencido",
    ).count()
    if facturas_vencidas > 0:
        alertas.append({"tipo": "factura_vencida", "mensaje": f"{facturas_vencidas} factura(s) de proveedor vencida(s)"})

    prox = hoy + timedelta(days=5)
    facturas_proximas = db.query(models.RecepcionCompra).filter(
        models.RecepcionCompra.fecha_vencimiento_pago.isnot(None),
        models.RecepcionCompra.fecha_vencimiento_pago >= hoy,
        models.RecepcionCompra.fecha_vencimiento_pago <= prox,
        models.RecepcionCompra.estado_pago == "pendiente",
    ).count()
    if facturas_proximas > 0:
        alertas.append({"tipo": "factura_proxima", "mensaje": f"{facturas_proximas} factura(s) vencen en los próximos 5 días"})

    comisiones_p = db.query(models.PeriodoComision).filter(
        models.PeriodoComision.estado == "pendiente"
    ).count()
    if comisiones_p > 0:
        alertas.append({"tipo": "comision_pendiente", "mensaje": f"{comisiones_p} período(s) de comisión pendiente(s) de pago"})

    # ── Últimas ventas del día ────────────────────────────────────────────────
    ultimas_ventas = [
        {
            "id":           v.id,
            "usuario":      v.usuario,
            "moneda_venta": v.moneda_venta,
            "total":        round(v.total, 2),
            "estado":       v.estado,
            "fecha":        v.fecha.isoformat() if v.fecha else None,
        }
        for v in sorted(ventas_hoy_list, key=lambda x: x.fecha or datetime.min, reverse=True)[:10]
    ]

    # ── Productos con alerta de stock ─────────────────────────────────────────
    productos_alerta = [
        {
            "id":        p.id,
            "nombre":    p.nombre,
            "stock":     p.stock or 0,
            "categoria": p.categoria or "—",
        }
        for p in sorted(productos, key=lambda x: x.stock or 0)[:10]
        if (p.stock or 0) < 5
    ]

    # ── Facturas de proveedores pendientes ────────────────────────────────────
    rows = db.query(models.RecepcionCompra, models.OrdenCompra, models.Proveedor).join(
        models.OrdenCompra, models.RecepcionCompra.orden_id == models.OrdenCompra.id
    ).join(
        models.Proveedor, models.OrdenCompra.proveedor_id == models.Proveedor.id
    ).filter(
        models.RecepcionCompra.fecha_vencimiento_pago.isnot(None),
        models.RecepcionCompra.estado_pago.in_(["pendiente", "vencido"]),
    ).order_by(models.RecepcionCompra.fecha_vencimiento_pago).all()

    facturas_pendientes = []
    for rec, orden, prov in rows:
        dias_restantes = (rec.fecha_vencimiento_pago - hoy).days if rec.fecha_vencimiento_pago else None
        if rec.estado_pago == "vencido" or (dias_restantes is not None and dias_restantes < 0):
            alerta = "vencida"
        elif dias_restantes is not None and dias_restantes <= 5:
            alerta = "proxima"
        else:
            alerta = "ok"
        facturas_pendientes.append({
            "recepcion_id":      rec.id,
            "proveedor":         prov.nombre,
            "numero_factura":    rec.numero_factura or "—",
            "orden":             orden.numero,
            "monto_factura":     round(rec.monto_factura or 0, 2),
            "fecha_vencimiento": rec.fecha_vencimiento_pago.isoformat() if rec.fecha_vencimiento_pago else None,
            "dias_restantes":    dias_restantes,
            "estado_pago":       rec.estado_pago,
            "alerta":            alerta,
        })

    return {
        "ventas_hoy":                 ventas_hoy_count,
        "total_hoy_usd":              round(total_hoy_usd, 2),
        "total_hoy_bs":               round(total_hoy_bs, 2),
        "ticket_promedio_usd":        ticket_promedio_usd,
        "unidades_vendidas_hoy":      int(unidades_hoy),
        "clientes_hoy":               int(clientes_hoy),
        "total_productos":            total_productos,
        "productos_stock_bajo":       productos_stock_bajo,
        "productos_sin_stock":        productos_sin_stock,
        "valor_inventario_usd":       round(valor_inventario_usd, 2),
        "comision_total_hoy":         round(comision_hoy, 2),
        "comisiones_pendientes_pago": round(comisiones_pendientes, 2),
        "tasa_bcv":                   tasa_bcv,
        "tasa_binance":               tasa_binance,
        "factor":                     factor,
        "alertas":                    alertas,
        "ultimas_ventas":             ultimas_ventas,
        "productos_alerta":           productos_alerta,
        "facturas_pendientes":        facturas_pendientes,
    }
