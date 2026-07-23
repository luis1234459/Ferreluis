from fastapi import APIRouter, Depends, Body, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import (
    Venta, PagoVenta, DetalleVenta, Producto, VarianteProducto, CierreCaja, LABELS_METODO,
    Cliente, VentaCliente, NivelFidelidad,
    Departamento, Proveedor, OrdenCompra, DetalleOrdenCompra, RecepcionCompra,
    VendedorPerfil, ComisionVenta, Usuario,
    Area, Pasillo, Estante, UbicacionProducto, CuentaBancaria,
    MovimientoBancario, Sede,
)
from datetime import datetime, timedelta, date
from rutas.usuarios import require_admin, require_admin_o_gestionador
from typing import Optional

def require_admin_o_vendedor(
    x_usuario_rol: Optional[str] = Header(None),
):
    if x_usuario_rol not in ("admin", "gestionador", "vendedor"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Sin permiso")

router = APIRouter(prefix="/reportes", tags=["reportes"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalizar_fechas(desde, hasta):
    """Agrega hora a fechas ISO sin hora para que el rango sea inclusivo."""
    if desde and "T" not in desde and " " not in desde:
        desde = desde + " 00:00:00"
    if hasta and "T" not in hasta and " " not in hasta:
        hasta = hasta + " 23:59:59"
    return desde, hasta


def _filtro_fecha(query, modelo, desde, hasta):
    desde, hasta = _normalizar_fechas(desde, hasta)
    if desde:
        query = query.filter(modelo.fecha >= desde)
    if hasta:
        query = query.filter(modelo.fecha <= hasta)
    return query


def _venta_ids_en_periodo(db: Session, desde, hasta) -> set:
    desde, hasta = _normalizar_fechas(desde, hasta)
    q = db.query(Venta.id)
    if desde: q = q.filter(Venta.fecha >= desde)
    if hasta: q = q.filter(Venta.fecha <= hasta)
    return {r[0] for r in q.all()}


def _detalles_en_periodo(db: Session, desde, hasta):
    ids = _venta_ids_en_periodo(db, desde, hasta)
    if not ids:
        return []
    return db.query(DetalleVenta).filter(DetalleVenta.venta_id.in_(ids)).all()


def _calcular_dias_periodo(desde, hasta) -> int:
    try:
        d1 = datetime.fromisoformat(desde).date() if desde else date.today() - timedelta(days=30)
        d2 = datetime.fromisoformat(hasta).date() if hasta else date.today()
        return max(1, (d2 - d1).days + 1)
    except Exception:
        return 30


# ---------------------------------------------------------------------------
# VENTAS — endpoints existentes
# ---------------------------------------------------------------------------

@router.get("/ventas")
def reporte_ventas(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    q = db.query(Venta)
    q = _filtro_fecha(q, Venta, desde, hasta)
    ventas = q.order_by(Venta.fecha.desc()).all()

    total_usd = sum(float(v.total or 0) for v in ventas if v.moneda_venta == "USD")
    total_bs  = sum(float(v.total or 0) for v in ventas if v.moneda_venta == "Bs")

    return {
        "cantidad":     len(ventas),
        "total_usd":    round(total_usd, 2),
        "total_bs":     round(total_bs,  2),
        "promedio_usd": round(total_usd / len(ventas), 2) if ventas else 0,
        "ventas": [
            {
                "id":          v.id,
                "fecha":       v.fecha.isoformat() if v.fecha else None,
                "usuario":     v.usuario,
                "moneda":      v.moneda_venta,
                "tipo_precio": v.tipo_precio_usado,
                "total":       round(float(v.total or 0), 2),
                "estado":      v.estado,
            }
            for v in ventas
        ],
    }


@router.get("/ventas/por-metodo")
def reporte_por_metodo(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    q = db.query(PagoVenta)
    if desde: q = q.filter(PagoVenta.fecha_hora >= desde)
    if hasta: q = q.filter(PagoVenta.fecha_hora <= hasta)
    pagos = q.all()

    totales = {}
    for p in pagos:
        key = p.metodo_pago
        if key not in totales:
            totales[key] = {"label": LABELS_METODO.get(key, key), "moneda": p.moneda_pago, "monto": 0.0, "cantidad": 0}
        totales[key]["monto"]    += float(p.monto_original or 0)
        totales[key]["cantidad"] += 1
    for key in totales:
        totales[key]["monto"] = round(totales[key]["monto"], 2)
    return totales


# ---------------------------------------------------------------------------
# VENTAS — nuevos endpoints
# ---------------------------------------------------------------------------

@router.get("/ventas/por-departamento")
def ventas_por_departamento(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_o_vendedor),
):
    detalles      = _detalles_en_periodo(db, desde, hasta)
    productos     = {p.id: p for p in db.query(Producto).all()}
    departamentos = {d.id: d for d in db.query(Departamento).all()}

    grupos: dict = {}
    for d in detalles:
        prod    = productos.get(d.producto_id)
        dept_id = prod.departamento_id if prod else None
        if dept_id not in grupos:
            dept = departamentos.get(dept_id)
            grupos[dept_id] = {
                "departamento_id":     dept_id,
                "departamento_nombre": dept.nombre if dept else "Sin departamento",
                "ventas_ids":          set(),
                "unidades_vendidas":   0,
                "total_usd":           0.0,
            }
        grupos[dept_id]["ventas_ids"].add(d.venta_id)
        grupos[dept_id]["unidades_vendidas"] += int(d.cantidad or 0)
        grupos[dept_id]["total_usd"]         += float(d.precio_unitario or 0) * int(d.cantidad or 0)

    total_global = sum(g["total_usd"] for g in grupos.values())
    resultado = []
    for g in sorted(grupos.values(), key=lambda x: x["total_usd"], reverse=True):
        resultado.append({
            "departamento_id":     g["departamento_id"],
            "departamento_nombre": g["departamento_nombre"],
            "cantidad_ventas":     len(g["ventas_ids"]),
            "unidades_vendidas":   g["unidades_vendidas"],
            "total_usd":           round(g["total_usd"], 2),
            "pct_del_total":       round(g["total_usd"] / total_global * 100, 1) if total_global > 0 else 0,
        })
    return resultado


@router.get("/ventas/por-proveedor")
def ventas_por_proveedor(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    detalles   = _detalles_en_periodo(db, desde, hasta)
    productos  = {p.id: p for p in db.query(Producto).all()}
    proveedores = {p.id: p for p in db.query(Proveedor).all()}

    grupos: dict = {}
    for d in detalles:
        prod    = productos.get(d.producto_id)
        prov_id = prod.proveedor_id if prod else None
        if prov_id not in grupos:
            prov = proveedores.get(prov_id)
            grupos[prov_id] = {
                "proveedor_id":      prov_id,
                "proveedor_nombre":  prov.nombre if prov else "Sin proveedor",
                "ventas_ids":        set(),
                "unidades_vendidas": 0,
                "total_usd":         0.0,
            }
        grupos[prov_id]["ventas_ids"].add(d.venta_id)
        grupos[prov_id]["unidades_vendidas"] += int(d.cantidad or 0)
        grupos[prov_id]["total_usd"]         += float(d.precio_unitario or 0) * int(d.cantidad or 0)

    total_global = sum(g["total_usd"] for g in grupos.values())
    resultado = []
    for g in sorted(grupos.values(), key=lambda x: x["total_usd"], reverse=True):
        resultado.append({
            "proveedor_id":      g["proveedor_id"],
            "proveedor_nombre":  g["proveedor_nombre"],
            "cantidad_ventas":   len(g["ventas_ids"]),
            "unidades_vendidas": g["unidades_vendidas"],
            "total_usd":         round(g["total_usd"], 2),
            "pct_del_total":     round(g["total_usd"] / total_global * 100, 1) if total_global > 0 else 0,
        })
    return resultado


@router.get("/ventas/por-pareto")
def ventas_por_pareto(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    detalles  = _detalles_en_periodo(db, desde, hasta)
    productos = {p.id: p for p in db.query(Producto).all()}

    pareto = {"ventas_ids": set(), "unidades": 0, "total_usd": 0.0, "prods": {}}
    resto  = {"ventas_ids": set(), "unidades": 0, "total_usd": 0.0}

    for d in detalles:
        prod      = productos.get(d.producto_id)
        es_clave  = bool(prod.es_producto_clave) if prod else False
        linea_usd = float(d.precio_unitario or 0) * int(d.cantidad or 0)
        if es_clave:
            pareto["ventas_ids"].add(d.venta_id)
            pareto["unidades"]  += int(d.cantidad or 0)
            pareto["total_usd"] += linea_usd
            pid = d.producto_id
            if pid not in pareto["prods"]:
                pareto["prods"][pid] = {"id": pid, "nombre": prod.nombre, "unidades": 0, "total_usd": 0.0}
            pareto["prods"][pid]["unidades"]  += int(d.cantidad or 0)
            pareto["prods"][pid]["total_usd"] += linea_usd
        else:
            resto["ventas_ids"].add(d.venta_id)
            resto["unidades"]   += int(d.cantidad or 0)
            resto["total_usd"]  += linea_usd

    total_global      = pareto["total_usd"] + resto["total_usd"]
    total_prods_pareto = sum(1 for p in productos.values() if p.es_producto_clave)

    productos_pareto = sorted(pareto["prods"].values(), key=lambda x: x["total_usd"], reverse=True)
    for p in productos_pareto:
        p["total_usd"] = round(p["total_usd"], 2)

    return {
        "pareto": {
            "cantidad_productos": total_prods_pareto,
            "unidades_vendidas":  pareto["unidades"],
            "total_usd":          round(pareto["total_usd"], 2),
            "pct_del_total":      round(pareto["total_usd"] / total_global * 100, 1) if total_global > 0 else 0,
        },
        "resto": {
            "cantidad_productos": len(productos) - total_prods_pareto,
            "unidades_vendidas":  resto["unidades"],
            "total_usd":          round(resto["total_usd"], 2),
            "pct_del_total":      round(resto["total_usd"] / total_global * 100, 1) if total_global > 0 else 0,
        },
        "productos_pareto": productos_pareto,
    }


@router.get("/ventas/por-vendedor")
def ventas_por_vendedor(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_o_vendedor),
    x_usuario_rol: Optional[str] = Header(None),
    x_usuario_nombre: Optional[str] = Header(None),
):
    q = db.query(ComisionVenta)
    if desde or hasta:
        ids = _venta_ids_en_periodo(db, desde, hasta)
        if not ids:
            return []
        q = q.filter(ComisionVenta.venta_id.in_(ids))
    comisiones = q.all()

    perfiles = {p.id: p for p in db.query(VendedorPerfil).all()}
    usuarios = {u.id: u for u in db.query(Usuario).all()}

    grupos: dict = {}
    for c in comisiones:
        vid = c.vendedor_id
        if vid not in grupos:
            perfil  = perfiles.get(vid)
            usuario = usuarios.get(perfil.usuario_id) if perfil else None
            grupos[vid] = {
                "vendedor_id":     vid,
                "vendedor_nombre": usuario.nombre if usuario else f"Vendedor {vid}",
                "ventas_ids":      set(),
                "total_usd":       0.0,
                "total_comision":  0.0,
            }
        grupos[vid]["ventas_ids"].add(c.venta_id)
        grupos[vid]["total_usd"]      += float(c.monto_venta_usd or 0)
        grupos[vid]["total_comision"] += float(c.monto_comision or 0)

    resultado = []
    for g in sorted(grupos.values(), key=lambda x: x["total_usd"], reverse=True):
        resultado.append({
            "vendedor_id":           g["vendedor_id"],
            "vendedor_nombre":       g["vendedor_nombre"],
            "cantidad_ventas":       len(g["ventas_ids"]),
            "total_usd":             round(g["total_usd"], 2),
            "total_comision":        round(g["total_comision"], 2),
            "pct_comision_promedio": round(g["total_comision"] / g["total_usd"] * 100, 2) if g["total_usd"] > 0 else 0,
        })
    # Vendedor solo ve sus propias comisiones
    if x_usuario_rol == "vendedor" and x_usuario_nombre:
        resultado = [r for r in resultado if r["vendedor_nombre"] == x_usuario_nombre]
    return resultado


@router.get("/ventas/resumen-dia")
def ventas_resumen_dia(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_o_vendedor),
    x_usuario_rol: Optional[str] = Header(None),
    x_usuario_nombre: Optional[str] = Header(None),
):
    desde, hasta = _normalizar_fechas(desde, hasta)
    q = db.query(Venta)
    if desde: q = q.filter(Venta.fecha >= desde)
    if hasta: q = q.filter(Venta.fecha <= hasta)
    ventas = q.filter(Venta.estado != 'anulada').all()

    if not ventas:
        return {
            "cantidad_ventas": 0,
            "total_usd": 0.0,
            "total_bs": 0.0,
            "total_usd_equiv": 0.0,
            "por_metodo_cuenta": [],
            "por_vendedor": [],
        }

    venta_ids  = {v.id for v in ventas}
    ventas_map = {v.id: v for v in ventas}

    total_usd = sum(float(v.total or 0) for v in ventas if v.moneda_venta == "USD")
    total_bs  = sum(float(v.total or 0) for v in ventas if v.moneda_venta != "USD")

    total_usd_equiv = 0.0
    for v in ventas:
        if v.moneda_venta == "USD":
            total_usd_equiv += float(v.total or 0)
        else:
            tasa = float(v.tasa_bcv or 1)
            total_usd_equiv += float(v.total or 0) / tasa if tasa > 0 else 0.0

    # Pagos agrupados por método + cuenta destino
    pagos       = db.query(PagoVenta).filter(PagoVenta.venta_id.in_(venta_ids)).all()
    cuentas_map = {c.id: c for c in db.query(CuentaBancaria).all()}

    por_metodo: dict = {}
    for p in pagos:
        label_key = f"{p.metodo_pago}_{p.cuenta_destino_id or 'sin_cuenta'}"
        if label_key not in por_metodo:
            cuenta = cuentas_map.get(p.cuenta_destino_id)
            por_metodo[label_key] = {
                "metodo":        p.metodo_pago,
                "label":         LABELS_METODO.get(p.metodo_pago, p.metodo_pago),
                "cuenta_id":     p.cuenta_destino_id,
                "cuenta_nombre": cuenta.nombre if cuenta else None,
                "moneda":        p.moneda_pago,
                "monto_original": 0.0,
                "monto_usd":      0.0,
                "cantidad":       0,
            }
        monto = float(p.monto_original or 0)
        venta = ventas_map.get(p.venta_id)
        tasa  = float(venta.tasa_bcv or 1) if venta and venta.tasa_bcv else 1.0
        monto_usd = monto if p.moneda_pago == "USD" else (monto / tasa if tasa > 0 else 0.0)
        por_metodo[label_key]["monto_original"] += monto
        por_metodo[label_key]["monto_usd"]      += monto_usd
        por_metodo[label_key]["cantidad"]        += 1

    for k in por_metodo:
        por_metodo[k]["monto_original"] = round(por_metodo[k]["monto_original"], 2)
        por_metodo[k]["monto_usd"]      = round(por_metodo[k]["monto_usd"],      2)

    # Ventas agrupadas por vendedor (v.usuario)
    detalles = db.query(DetalleVenta).filter(DetalleVenta.venta_id.in_(venta_ids)).all()
    detalles_por_venta: dict = {}
    for d in detalles:
        detalles_por_venta.setdefault(d.venta_id, []).append(d)

    por_vendedor: dict = {}
    for v in ventas:
        uname = v.usuario or "Sin usuario"
        if uname not in por_vendedor:
            por_vendedor[uname] = {
                "vendedor_nombre": uname,
                "cantidad_ventas": 0,
                "subtotal_usd":    0.0,
                "subtotal_venta":  0.0,
            }
        por_vendedor[uname]["cantidad_ventas"] += 1
        tasa = float(v.tasa_bcv or 1) if v.tasa_bcv else 1.0
        for d in detalles_por_venta.get(v.id, []):
            subtotal_usd   = float(d.precio_unitario or 0) * int(d.cantidad or 0)
            subtotal_venta = subtotal_usd if v.moneda_venta == "USD" else subtotal_usd * tasa
            por_vendedor[uname]["subtotal_usd"]   += subtotal_usd
            por_vendedor[uname]["subtotal_venta"] += subtotal_venta

    for k in por_vendedor:
        por_vendedor[k]["subtotal_usd"]   = round(por_vendedor[k]["subtotal_usd"],   2)
        por_vendedor[k]["subtotal_venta"] = round(por_vendedor[k]["subtotal_venta"], 2)

    productos_map = {p.id: p for p in db.query(Producto).all()}
    variantes_map = {v.id: v for v in db.query(VarianteProducto).all()}

    # Ventas últimos 30 días por producto (para semáforo de reposición)
    hace_30_dias = datetime.utcnow() - timedelta(days=30)
    detalles_30 = db.query(DetalleVenta).join(
        Venta, DetalleVenta.venta_id == Venta.id
    ).filter(
        Venta.fecha >= hace_30_dias,
        Venta.estado != 'anulada',
    ).all()
    ventas_30d: dict = {}
    for d30 in detalles_30:
        ventas_30d[d30.producto_id] = ventas_30d.get(d30.producto_id, 0) + int(d30.cantidad or 0)

    lineas_productos = []
    for v in sorted(ventas, key=lambda x: x.fecha or x.id):
        tasa = float(v.tasa_bcv or 1) if v.tasa_bcv else 1.0
        for d in detalles_por_venta.get(v.id, []):
            prod   = productos_map.get(d.producto_id)
            nombre = prod.nombre if prod else f"Producto {d.producto_id}"
            if d.variante_id:
                var = variantes_map.get(d.variante_id)
                if var:
                    sufijo = f" ({var.clase}"
                    if var.color: sufijo += f"/{var.color}"
                    sufijo += ")"
                    nombre += sufijo
            cantidad       = int(d.cantidad or 0)
            precio_usd     = float(d.precio_unitario or 0)
            subtotal_usd   = round(precio_usd * cantidad, 2)
            if v.moneda_venta == "USD":
                precio_display   = precio_usd
                subtotal_display = subtotal_usd
                moneda_display   = "USD"
            else:
                precio_display   = round(precio_usd * tasa, 2)
                subtotal_display = round(subtotal_usd * tasa, 2)
                moneda_display   = "Bs"
            var_obj    = variantes_map.get(d.variante_id) if d.variante_id else None
            costo_unit = float(
                (var_obj.costo_usd if var_obj and var_obj.costo_usd is not None
                 else prod.costo_usd) or 0
            ) if prod else 0
            if v.moneda_venta == "Bs" and v.tipo_precio_usado == "referencial":
                factor = float(v.factor_cambio or 1)
                precio_base_equiv = precio_usd / factor if factor > 0 else precio_usd
                ganancia_usd = round((precio_base_equiv - costo_unit) * cantidad, 2)
                margen_pct   = round((precio_base_equiv - costo_unit) / precio_base_equiv * 100, 1) if precio_base_equiv > 0 else 0
            else:
                ganancia_usd = round((precio_usd - costo_unit) * cantidad, 2)
                margen_pct   = round((precio_usd - costo_unit) / precio_usd * 100, 1) if precio_usd > 0 else 0
            stock_actual    = int(prod.stock or 0) if prod else 0
            stock_min       = int(prod.stock_minimo or 0) if prod else 0
            vendidos_30d    = ventas_30d.get(d.producto_id, 0)
            promedio_diario = round(vendidos_30d / 30, 2)
            dias_cobertura  = round(stock_actual / promedio_diario, 1) if promedio_diario > 0 else 999
            if stock_actual == 0:
                semaforo = 'rojo'
            elif stock_min > 0 and stock_actual <= stock_min:
                semaforo = 'rojo'
            elif dias_cobertura <= 7:
                semaforo = 'rojo'
            elif dias_cobertura <= 15:
                semaforo = 'amarillo'
            else:
                semaforo = 'verde'
            es_solo_vendedor = x_usuario_rol == "vendedor"
            linea = {
                "hora":            v.fecha.strftime('%H:%M') if v.fecha else '—',
                "venta_id":        v.id,
                "producto_id":     d.producto_id,
                "producto":        nombre,
                "cantidad":        cantidad,
                "moneda":          moneda_display,
                "precio_unitario": precio_display,
                "subtotal_venta":  subtotal_display,
                "subtotal_usd":    subtotal_usd,
                "tasa_bcv":        round(tasa, 2) if moneda_display == "Bs" else None,
                "precio_libre":    False,
                "vendedor":        v.usuario or "—",
                "stock_actual":    stock_actual,
                "stock_minimo":    stock_min,
                "vendidos_30d":    vendidos_30d,
                "promedio_diario": promedio_diario,
                "dias_cobertura":  dias_cobertura,
                "semaforo":        semaforo,
                "auditado":            bool(prod.auditado) if prod else False,
                "auditoria_pendiente": bool(prod.auditoria_pendiente) if prod else False,
                "fecha_auditoria":     prod.fecha_auditoria.strftime('%d/%m/%Y') if prod and prod.fecha_auditoria else None,
            }
            if not es_solo_vendedor:
                linea["costo_usd"]    = round(costo_unit, 4)
                linea["margen_pct"]   = margen_pct
                linea["ganancia_usd"] = ganancia_usd
            lineas_productos.append(linea)

    # ── Facturas agrupadas por venta ─────────────────────────────────────────
    # Incluir anuladas también (filtro solo excluye anuladas del resumen)
    todas_ventas = db.query(Venta)
    if desde: todas_ventas = todas_ventas.filter(Venta.fecha >= desde)
    if hasta: todas_ventas = todas_ventas.filter(Venta.fecha <= hasta)
    todas_ventas = todas_ventas.all()
    todos_ids = {v.id for v in todas_ventas}

    pagos_todos = db.query(PagoVenta).filter(PagoVenta.venta_id.in_(todos_ids)).all()
    pagos_por_venta: dict = {}
    for p in pagos_todos:
        pagos_por_venta.setdefault(p.venta_id, []).append(p)

    detalles_todos = db.query(DetalleVenta).filter(DetalleVenta.venta_id.in_(todos_ids)).all()
    detalles_todos_por_venta: dict = {}
    for d in detalles_todos:
        detalles_todos_por_venta.setdefault(d.venta_id, []).append(d)

    vinculos = db.query(VentaCliente).filter(VentaCliente.venta_id.in_(todos_ids)).all()
    cliente_ids = {vc.cliente_id for vc in vinculos}
    clientes_map = {c.id: c for c in db.query(Cliente).filter(Cliente.id.in_(cliente_ids)).all()}
    cliente_por_venta = {vc.venta_id: clientes_map.get(vc.cliente_id) for vc in vinculos}

    facturas = []
    for v in sorted(todas_ventas, key=lambda x: x.fecha or x.id, reverse=True):
        tasa = float(v.tasa_bcv or 1) if v.tasa_bcv else 1.0
        cliente = cliente_por_venta.get(v.id)
        cliente_nombre = cliente.nombre if cliente and not getattr(cliente, 'es_cliente_generico', False) else None

        metodos_pago = []
        for p in pagos_por_venta.get(v.id, []):
            cuenta = cuentas_map.get(p.cuenta_destino_id)
            monto = float(p.monto_original or 0)
            monto_usd = monto if p.moneda_pago == "USD" else (monto / tasa if tasa > 0 else 0.0)
            metodos_pago.append({
                "metodo": p.metodo_pago,
                "cuenta": cuenta.nombre if cuenta else None,
                "monto":  round(monto_usd, 2),
            })

        productos_factura = []
        for d in detalles_todos_por_venta.get(v.id, []):
            prod   = productos_map.get(d.producto_id)
            nombre = prod.nombre if prod else f"Producto {d.producto_id}"
            if d.variante_id:
                var = variantes_map.get(d.variante_id)
                if var:
                    sufijo = f" ({var.clase}"
                    if var.color: sufijo += f"/{var.color}"
                    sufijo += ")"
                    nombre += sufijo
            precio_usd = float(d.precio_unitario or 0)
            cantidad   = int(d.cantidad or 0)
            if v.moneda_venta == "USD":
                precio_display = precio_usd
                subtotal       = round(precio_usd * cantidad, 2)
            else:
                precio_display = round(precio_usd * tasa, 2)
                subtotal       = round(precio_usd * cantidad * tasa, 2)
            productos_factura.append({
                "nombre":          nombre,
                "cantidad":        cantidad,
                "precio_unitario": precio_display,
                "subtotal":        subtotal,
                "moneda":          v.moneda_venta or "USD",
            })

        total_venta = float(v.total or 0)
        if v.moneda_venta != "USD":
            total_venta = round(total_venta / tasa, 2) if tasa > 0 else 0.0
        else:
            total_venta = round(total_venta, 2)

        facturas.append({
            "venta_id":    v.id,
            "hora":        v.fecha.strftime('%H:%M') if v.fecha else '—',
            "usuario":     v.usuario or '—',
            "cliente":     cliente_nombre,
            "total_usd":   total_venta,
            "moneda":      v.moneda_venta or "USD",
            "estado":      v.estado or "pagado",
            "metodos_pago": metodos_pago,
            "productos":   productos_factura,
        })

    es_solo_vendedor = x_usuario_rol == "vendedor"

    # Vendedor solo ve sus propias líneas y facturas
    if es_solo_vendedor and x_usuario_nombre:
        lineas_productos = [l for l in lineas_productos if l["vendedor"] == x_usuario_nombre]
        facturas = [f for f in facturas if f["usuario"] == x_usuario_nombre]
        por_vendedor_filtrado = {k: v for k, v in por_vendedor.items() if k == x_usuario_nombre}
    else:
        por_vendedor_filtrado = por_vendedor

    return {
        "cantidad_ventas":   len(ventas),
        "total_usd":         round(total_usd,      2),
        "total_bs":          round(total_bs,        2),
        "total_usd_equiv":   round(total_usd_equiv, 2),
        "por_metodo_cuenta": [] if es_solo_vendedor else sorted(por_metodo.values(), key=lambda x: x["monto_usd"], reverse=True),
        "por_vendedor":      sorted(por_vendedor_filtrado.values(), key=lambda x: x["subtotal_usd"], reverse=True),
        "lineas_productos":  lineas_productos,
        "facturas":          facturas,
    }


# ---------------------------------------------------------------------------
# PRODUCTOS — top (mejorado con depto y proveedor)
# ---------------------------------------------------------------------------

@router.get("/productos/top")
def top_productos(
    n: int = 10,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_o_vendedor),
):
    q = db.query(
        DetalleVenta.producto_id,
        DetalleVenta.variante_id,
        func.sum(DetalleVenta.cantidad).label("total_cantidad"),
        func.sum(DetalleVenta.subtotal).label("total_monto"),
    )
    if desde or hasta:
        q = q.join(Venta, Venta.id == DetalleVenta.venta_id)
        if desde: q = q.filter(Venta.fecha >= desde)
        if hasta: q = q.filter(Venta.fecha <= hasta)
    q = (q.group_by(DetalleVenta.producto_id, DetalleVenta.variante_id)
          .order_by(func.sum(DetalleVenta.cantidad).desc()).limit(n))
    rows = q.all()

    departamentos = {d.id: d for d in db.query(Departamento).all()}
    proveedores   = {p.id: p for p in db.query(Proveedor).all()}
    variantes_map = {v.id: v for v in db.query(VarianteProducto).all()}

    resultado = []
    for r in rows:
        p    = db.query(Producto).filter(Producto.id == r.producto_id).first()
        dept = departamentos.get(p.departamento_id) if p else None
        prov = proveedores.get(p.proveedor_id)     if p else None
        nombre = p.nombre if p else f"ID {r.producto_id}"
        if r.variante_id:
            v = variantes_map.get(r.variante_id)
            if v:
                nombre += f" ({v.clase} {v.color or ''})".rstrip()
        resultado.append({
            "producto_id":    r.producto_id,
            "variante_id":    r.variante_id,
            "nombre":         nombre,
            "departamento":   dept.nombre if dept else "—",
            "proveedor":      prov.nombre if prov else "—",
            "total_cantidad": int(r.total_cantidad or 0),
            "total_monto":    round(float(r.total_monto or 0), 2),
        })
    return resultado


# ---------------------------------------------------------------------------
# INVENTARIO — endpoints existentes
# ---------------------------------------------------------------------------

@router.get("/inventario")
def reporte_inventario(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    productos  = db.query(Producto).order_by(Producto.nombre).all()
    variantes_map: dict = {}
    for v in db.query(VarianteProducto).all():
        variantes_map.setdefault(v.producto_id, []).append(v)

    resultado = []
    for p in productos:
        vs = variantes_map.get(p.id, [])
        if vs:
            for v in vs:
                costo = float(v.costo_usd if v.costo_usd is not None else (p.costo_usd or 0))
                stock = int(v.stock or 0)
                label = f"{v.clase}" + (f" / {v.color}" if v.color else "")
                resultado.append({
                    "id":               p.id,
                    "variante_id":      v.id,
                    "nombre":           f"{p.nombre} ({label})",
                    "categoria":        p.categoria,
                    "stock":            stock,
                    "costo_usd":        round(costo, 2),
                    "valor_inventario": round(costo * stock, 2),
                    "alerta_stock":     stock < 5,
                    "activo":           v.activo,
                })
        else:
            resultado.append({
                "id":               p.id,
                "variante_id":      None,
                "nombre":           p.nombre,
                "categoria":        p.categoria,
                "stock":            p.stock,
                "costo_usd":        round(float(p.costo_usd or 0), 2),
                "valor_inventario": round(float(p.costo_usd or 0) * int(p.stock or 0), 2),
                "alerta_stock":     p.stock < 5,
                "activo":           p.activo,
            })
    return resultado


# ---------------------------------------------------------------------------
# INVENTARIO — nuevos endpoints
# ---------------------------------------------------------------------------

@router.get("/inventario/por-departamento")
def inventario_por_departamento(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    productos     = db.query(Producto).order_by(Producto.nombre).all()
    departamentos = {d.id: d for d in db.query(Departamento).all()}
    variantes_map: dict = {}
    for v in db.query(VarianteProducto).all():
        variantes_map.setdefault(v.producto_id, []).append(v)

    grupos: dict = {}
    for p in productos:
        dept_id = p.departamento_id
        if dept_id not in grupos:
            dept = departamentos.get(dept_id)
            grupos[dept_id] = {
                "departamento_id":      dept_id,
                "departamento_nombre":  dept.nombre if dept else "Sin departamento",
                "cantidad_productos":   0,
                "stock_total":          0,
                "valor_usd":            0.0,
                "productos_bajo_stock": 0,
            }
        vs = variantes_map.get(p.id, [])
        if vs:
            for v in vs:
                costo = float(v.costo_usd if v.costo_usd is not None else (p.costo_usd or 0))
                stock = int(v.stock or 0)
                grupos[dept_id]["cantidad_productos"]   += 1
                grupos[dept_id]["stock_total"]          += stock
                grupos[dept_id]["valor_usd"]            += costo * stock
                if stock < 5:
                    grupos[dept_id]["productos_bajo_stock"] += 1
        else:
            grupos[dept_id]["cantidad_productos"]   += 1
            grupos[dept_id]["stock_total"]          += int(p.stock or 0)
            grupos[dept_id]["valor_usd"]            += float(p.costo_usd or 0) * int(p.stock or 0)
            if (p.stock or 0) < 5:
                grupos[dept_id]["productos_bajo_stock"] += 1

    resultado = sorted(grupos.values(), key=lambda x: x["valor_usd"], reverse=True)
    for g in resultado:
        g["valor_usd"] = round(g["valor_usd"], 2)
    return resultado


@router.get("/inventario/por-proveedor")
def inventario_por_proveedor(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    productos   = db.query(Producto).order_by(Producto.nombre).all()
    proveedores = {p.id: p for p in db.query(Proveedor).all()}
    variantes_map: dict = {}
    for v in db.query(VarianteProducto).all():
        variantes_map.setdefault(v.producto_id, []).append(v)

    grupos: dict = {}
    for p in productos:
        prov_id = p.proveedor_id
        if prov_id not in grupos:
            prov = proveedores.get(prov_id)
            grupos[prov_id] = {
                "proveedor_id":      prov_id,
                "proveedor_nombre":  prov.nombre if prov else "Sin proveedor",
                "cantidad_productos": 0,
                "stock_total":       0,
                "valor_usd":         0.0,
            }
        vs = variantes_map.get(p.id, [])
        if vs:
            for v in vs:
                costo = float(v.costo_usd if v.costo_usd is not None else (p.costo_usd or 0))
                stock = int(v.stock or 0)
                grupos[prov_id]["cantidad_productos"] += 1
                grupos[prov_id]["stock_total"]        += stock
                grupos[prov_id]["valor_usd"]          += costo * stock
        else:
            grupos[prov_id]["cantidad_productos"] += 1
            grupos[prov_id]["stock_total"]        += int(p.stock or 0)
            grupos[prov_id]["valor_usd"]          += float(p.costo_usd or 0) * int(p.stock or 0)

    resultado = sorted(grupos.values(), key=lambda x: x["valor_usd"], reverse=True)
    for g in resultado:
        g["valor_usd"] = round(g["valor_usd"], 2)
    return resultado


@router.get("/inventario/pareto")
def inventario_pareto(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    productos_clave = db.query(Producto).filter(Producto.es_producto_clave == True).order_by(Producto.nombre).all()

    detalles = _detalles_en_periodo(db, desde, hasta)
    ventas_por_prod: dict = {}
    for d in detalles:
        pid = d.producto_id
        ventas_por_prod[pid] = ventas_por_prod.get(pid, 0) + int(d.cantidad or 0)

    resultado = []
    for p in productos_clave:
        stock    = int(p.stock or 0)
        unidades = ventas_por_prod.get(p.id, 0)
        rotacion = round(unidades / stock, 2) if stock > 0 else None
        resultado.append({
            "id":               p.id,
            "nombre":           p.nombre,
            "stock":            stock,
            "costo_usd":        round(float(p.costo_usd or 0), 2),
            "valor_inventario": round(float(p.costo_usd or 0) * stock, 2),
            "unidades_vendidas": unidades,
            "rotacion":         rotacion,
        })
    return sorted(resultado, key=lambda x: x["valor_inventario"], reverse=True)


@router.get("/inventario/rotacion")
def inventario_rotacion(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    dias_periodo  = _calcular_dias_periodo(desde, hasta)
    productos     = db.query(Producto).order_by(Producto.nombre).all()
    departamentos = {d.id: d for d in db.query(Departamento).all()}
    variantes_map: dict = {}
    for v in db.query(VarianteProducto).all():
        variantes_map.setdefault(v.producto_id, []).append(v)

    detalles = _detalles_en_periodo(db, desde, hasta)
    ventas_por_prod: dict = {}
    ventas_por_variante: dict = {}
    for d in detalles:
        ventas_por_prod[d.producto_id] = ventas_por_prod.get(d.producto_id, 0) + int(d.cantidad or 0)
        if d.variante_id:
            ventas_por_variante[d.variante_id] = ventas_por_variante.get(d.variante_id, 0) + int(d.cantidad or 0)

    resultado = []
    for p in productos:
        dept = departamentos.get(p.departamento_id)
        vs   = variantes_map.get(p.id, [])
        if vs:
            for v in vs:
                stock    = int(v.stock or 0)
                unidades = ventas_por_variante.get(v.id, 0)
                rotacion = round(unidades / stock, 2) if stock > 0 else None
                dias_agotamiento = round(stock * dias_periodo / unidades) if (unidades > 0 and stock > 0) else None
                label = f"{v.clase}" + (f" / {v.color}" if v.color else "")
                resultado.append({
                    "id":                p.id,
                    "variante_id":       v.id,
                    "nombre":            f"{p.nombre} ({label})",
                    "departamento":      dept.nombre if dept else "—",
                    "stock":             stock,
                    "unidades_vendidas": unidades,
                    "rotacion":          rotacion,
                    "dias_agotamiento":  dias_agotamiento,
                })
        else:
            stock    = int(p.stock or 0)
            unidades = ventas_por_prod.get(p.id, 0)
            rotacion = round(unidades / stock, 2) if stock > 0 else None
            dias_agotamiento = round(stock * dias_periodo / unidades) if (unidades > 0 and stock > 0) else None
            resultado.append({
                "id":                p.id,
                "variante_id":       None,
                "nombre":            p.nombre,
                "departamento":      dept.nombre if dept else "—",
                "stock":             stock,
                "unidades_vendidas": unidades,
                "rotacion":          rotacion,
                "dias_agotamiento":  dias_agotamiento,
            })
    return sorted(resultado, key=lambda x: x["rotacion"] if x["rotacion"] is not None else -1, reverse=True)


@router.get("/inventario/valorizacion")
def valorizacion_inventario(
    agrupar_por: Optional[str] = "departamento",
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    from models import Categoria

    productos = db.query(Producto).filter(
        Producto.activo == True,
        Producto.stock > 0,
    ).order_by(Producto.nombre).all()

    deptos = {d.id: d.nombre for d in db.query(Departamento).all()}
    cats   = {c.id: c.nombre for c in db.query(Categoria).all()}
    provs  = {pv.id: pv.nombre for pv in db.query(Proveedor).all()}

    por_proveedor = (agrupar_por == "proveedor")

    grupos: dict = {}
    for p in productos:
        gid = (p.proveedor_id or 0) if por_proveedor else (p.departamento_id or 0)
        if gid not in grupos:
            if por_proveedor:
                nombre_grupo = provs.get(gid, "Sin proveedor")
            else:
                nombre_grupo = deptos.get(gid, "Sin departamento")
            grupos[gid] = {
                "departamento_id":    gid,
                "departamento":       nombre_grupo,
                "productos":          [],
                "total_unidades":     0,
                "total_costo_usd":    0.0,
                "total_precio_usd":   0.0,
                "ganancia_potencial": 0.0,
            }
        costo       = float(p.costo_usd or 0)
        margen      = float(p.margen or 0.30)
        precio_base = round(costo * (1 + margen), 4)
        stock       = int(p.stock or 0)
        valor_costo  = round(costo * stock, 2)
        valor_precio = round(precio_base * stock, 2)
        ganancia     = round((precio_base - costo) * stock, 2)

        grupos[gid]["productos"].append({
            "id":          p.id,
            "nombre":      p.nombre,
            "categoria":   cats.get(p.categoria_id, "—"),
            "stock":       stock,
            "costo_usd":   round(costo, 4),
            "precio_base": round(precio_base, 4),
            "valor_costo": valor_costo,
            "valor_precio": valor_precio,
            "ganancia":    ganancia,
            "margen_pct":  round(margen * 100, 1),
            "auditado":            bool(p.auditado) if p.auditado else False,
            "auditoria_pendiente": bool(p.auditoria_pendiente) if p.auditoria_pendiente else False,
            "fecha_auditoria":     p.fecha_auditoria.strftime('%d/%m/%Y') if p.fecha_auditoria else None,
        })
        grupos[gid]["total_unidades"]     += stock
        grupos[gid]["total_costo_usd"]    += valor_costo
        grupos[gid]["total_precio_usd"]   += valor_precio
        grupos[gid]["ganancia_potencial"] += ganancia

    resultado = []
    for g in sorted(grupos.values(), key=lambda x: x["total_costo_usd"], reverse=True):
        g["total_costo_usd"]    = round(g["total_costo_usd"], 2)
        g["total_precio_usd"]   = round(g["total_precio_usd"], 2)
        g["ganancia_potencial"] = round(g["ganancia_potencial"], 2)
        resultado.append(g)
    return resultado


@router.get("/inventario/no-auditados/pdf")
def pdf_no_auditados(
    departamento_id: Optional[int] = None,
    desde_nombre:    Optional[str] = None,
    hasta_nombre:    Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from fastapi.responses import StreamingResponse
    import io
    from models import Categoria

    q = db.query(Producto).filter(
        Producto.activo == True,
        Producto.auditado == False,
    )
    if departamento_id:
        q = q.filter(Producto.departamento_id == departamento_id)

    productos = q.order_by(Producto.nombre).all()

    if desde_nombre:
        productos = [p for p in productos if p.nombre.upper() >= desde_nombre.upper()]
    if hasta_nombre:
        productos = [p for p in productos if p.nombre.upper() <= hasta_nombre.upper()]

    deptos = {d.id: d.nombre for d in db.query(Departamento).all()}
    cats   = {c.id: c.nombre for c in db.query(Categoria).all()}

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
        topMargin=0.75*inch, bottomMargin=0.75*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch)

    styles   = getSampleStyleSheet()
    elements = []
    fecha_hoy = datetime.utcnow().strftime('%d/%m/%Y %H:%M')

    elements.append(Paragraph("<b>PRODUCTOS NO AUDITADOS — FERRE-UTIL</b>", styles['Title']))
    elements.append(Paragraph(
        f"Generado: {fecha_hoy} | Total: {len(productos)} productos", styles['Normal']
    ))
    elements.append(Spacer(1, 0.25*inch))

    if not productos:
        elements.append(Paragraph("✓ No hay productos pendientes de auditoría.", styles['Normal']))
    else:
        headers = ['#', 'Producto', 'Departamento', 'Categoría', 'Stock', 'Costo USD']
        data = [headers]
        for i, p in enumerate(productos, 1):
            data.append([
                str(i),
                p.nombre[:50],
                deptos.get(p.departamento_id, '—'),
                cats.get(p.categoria_id, '—'),
                str(int(p.stock or 0)),
                f"${float(p.costo_usd or 0):.2f}",
            ])

        tabla = Table(data, colWidths=[
            0.4*inch, 3.0*inch, 1.5*inch, 1.3*inch, 0.6*inch, 0.9*inch
        ])
        tabla.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#1A1A1A')),
            ('TEXTCOLOR',     (0, 0), (-1, 0), colors.HexColor('#FFCC00')),
            ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, 0), 9),
            ('FONTSIZE',      (0, 1), (-1,-1), 8),
            ('ROWBACKGROUNDS',(0, 1), (-1,-1), [colors.white, colors.HexColor('#F8F8F4')]),
            ('GRID',          (0, 0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
            ('VALIGN',        (0, 0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1,-1), 4),
            ('BOTTOMPADDING', (0, 0), (-1,-1), 4),
        ]))
        elements.append(tabla)

    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=no_auditados_{fecha_hoy[:10].replace('/','-')}.pdf"},
    )


# ---------------------------------------------------------------------------
# COMPRAS — nuevos endpoints
# ---------------------------------------------------------------------------

@router.get("/compras/por-proveedor")
def compras_por_proveedor(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    q = db.query(OrdenCompra).filter(OrdenCompra.estado == "cerrada")
    if desde: q = q.filter(OrdenCompra.fecha_creacion >= desde)
    if hasta: q = q.filter(OrdenCompra.fecha_creacion <= hasta)
    ordenes     = q.all()
    proveedores = {p.id: p for p in db.query(Proveedor).all()}

    grupos: dict = {}
    for o in ordenes:
        pid = o.proveedor_id
        if pid not in grupos:
            prov = proveedores.get(pid)
            grupos[pid] = {
                "proveedor_id":     pid,
                "proveedor_nombre": prov.nombre if prov else f"ID {pid}",
                "cantidad_ordenes": 0,
                "total_usd":        0.0,
                "ultima_compra":    None,
            }
        grupos[pid]["cantidad_ordenes"] += 1
        grupos[pid]["total_usd"]        += float(o.total or 0)
        fecha_str = o.fecha_creacion.isoformat() if o.fecha_creacion else None
        if fecha_str and (not grupos[pid]["ultima_compra"] or fecha_str > grupos[pid]["ultima_compra"]):
            grupos[pid]["ultima_compra"] = fecha_str

    # Agregar ubicaciones de productos comprados por proveedor
    areas_map    = {a.id: a for a in db.query(Area).all()}
    pasillos_map = {p.id: p for p in db.query(Pasillo).all()}
    estantes_map = {e.id: e for e in db.query(Estante).all()}

    for grupo in grupos.values():
        pid = grupo["proveedor_id"]
        ords_prov = [o for o in ordenes if o.proveedor_id == pid]
        prod_ids  = set()
        for o in ords_prov:
            detalles = db.query(DetalleOrdenCompra).filter(
                DetalleOrdenCompra.orden_id == o.id,
                DetalleOrdenCompra.producto_id.isnot(None),
            ).all()
            prod_ids.update(d.producto_id for d in detalles)

        ubicaciones = []
        for prod_id in prod_ids:
            ubs = db.query(UbicacionProducto).filter(
                UbicacionProducto.producto_id == prod_id,
                UbicacionProducto.activa == True,
            ).all()
            prod = db.query(Producto).filter(Producto.id == prod_id).first()
            for u in ubs:
                area    = areas_map.get(u.area_id)
                pasillo = pasillos_map.get(u.pasillo_id)
                estante = estantes_map.get(u.estante_id)
                ubicaciones.append({
                    "producto":  prod.nombre if prod else f"ID {prod_id}",
                    "ubicacion": f"{area.nombre if area else '?'} / P{pasillo.numero if pasillo else '?'} / E{estante.numero if estante else '?'} / Nivel {u.nivel}",
                })
        grupo["ubicaciones"] = ubicaciones

    resultado = sorted(grupos.values(), key=lambda x: x["total_usd"], reverse=True)
    for g in resultado:
        g["total_usd"] = round(g["total_usd"], 2)
    return resultado


@router.get("/compras/por-departamento")
def compras_por_departamento(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    q = db.query(OrdenCompra).filter(OrdenCompra.estado == "cerrada")
    if desde: q = q.filter(OrdenCompra.fecha_creacion >= desde)
    if hasta: q = q.filter(OrdenCompra.fecha_creacion <= hasta)
    ordenes_cerradas = {o.id for o in q.all()}
    if not ordenes_cerradas:
        return []

    detalles = db.query(DetalleOrdenCompra).filter(
        DetalleOrdenCompra.orden_id.in_(ordenes_cerradas),
        DetalleOrdenCompra.producto_id.isnot(None),
    ).all()

    productos     = {p.id: p for p in db.query(Producto).all()}
    departamentos = {d.id: d for d in db.query(Departamento).all()}

    grupos: dict = {}
    for d in detalles:
        prod    = productos.get(d.producto_id)
        dept_id = prod.departamento_id if prod else None
        if dept_id not in grupos:
            dept = departamentos.get(dept_id)
            grupos[dept_id] = {
                "departamento_id":     dept_id,
                "departamento_nombre": dept.nombre if dept else "Sin departamento",
                "cantidad_items":      0,
                "total_usd":           0.0,
            }
        grupos[dept_id]["cantidad_items"] += int(d.cantidad_pedida or 0)
        grupos[dept_id]["total_usd"]      += float(d.subtotal or 0)

    resultado = sorted(grupos.values(), key=lambda x: x["total_usd"], reverse=True)
    for g in resultado:
        g["total_usd"] = round(g["total_usd"], 2)
    return resultado


@router.get("/compras/facturas-pendientes")
def compras_facturas_pendientes(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    hoy = date.today()
    recs = db.query(RecepcionCompra).filter(
        RecepcionCompra.fecha_vencimiento_pago.isnot(None),
        RecepcionCompra.estado_pago.in_(["pendiente", "vencido"]),
    ).order_by(RecepcionCompra.fecha_vencimiento_pago).all()

    proveedores = {p.id: p for p in db.query(Proveedor).all()}
    ordenes     = {o.id: o for o in db.query(OrdenCompra).all()}

    resultado = []
    for r in recs:
        orden = ordenes.get(r.orden_id)
        prov  = proveedores.get(orden.proveedor_id) if orden else None
        dias  = (r.fecha_vencimiento_pago - hoy).days if r.fecha_vencimiento_pago else None

        if r.estado_pago == "vencido" or (dias is not None and dias < 0):
            alerta = "vencida"
        elif dias is not None and dias <= 5:
            alerta = "proxima"
        else:
            alerta = "ok"

        resultado.append({
            "recepcion_id":      r.id,
            "proveedor_nombre":  prov.nombre if prov else "—",
            "numero_orden":      orden.numero if orden else "—",
            "numero_factura":    r.numero_factura or "—",
            "monto":             round(float(r.monto_factura or 0), 2),
            "fecha_vencimiento": r.fecha_vencimiento_pago.isoformat() if r.fecha_vencimiento_pago else None,
            "dias_restantes":    dias,
            "estado_pago":       r.estado_pago,
            "alerta":            alerta,
        })
    return resultado


# ---------------------------------------------------------------------------
# CIERRES y CLIENTES — endpoints existentes
# ---------------------------------------------------------------------------

@router.get("/cierre/comparativo")
def reporte_comparativo_cierres(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    cierres = db.query(CierreCaja).order_by(CierreCaja.fecha.desc()).limit(10).all()
    metodos = ["efectivo_usd", "zelle", "binance",
               "efectivo_bs", "transferencia_bs", "pago_movil",
               "punto_banesco", "punto_provincial"]
    return [
        {
            "id":              c.id,
            "fecha":           c.fecha.isoformat() if c.fecha else None,
            "usuario":         c.usuario,
            "cantidad_ventas": c.cantidad_ventas,
            "total_usd":       round(float(c.total_ventas_usd or 0), 2),
            "detalle": {
                m: {
                    "esperado":   round(float(getattr(c, f"esp_{m}", 0) or 0), 2),
                    "contado":    round(float(getattr(c, f"cnt_{m}", 0) or 0), 2),
                    "diferencia": round(
                        float(getattr(c, f"cnt_{m}", 0) or 0) -
                        float(getattr(c, f"esp_{m}", 0) or 0), 2
                    ),
                }
                for m in metodos
            },
        }
        for c in cierres
    ]


@router.get("/bancos/movimientos-por-sede")
def reporte_movimientos_por_sede(
    sede_id:  Optional[int] = None,
    desde:    Optional[str] = None,
    hasta:    Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """
    Movimientos bancarios filtrables por sede de origen.

    movimientos_bancarios es global (misma cuenta para ambas sedes), asi que
    la sede de origen se obtiene indirectamente: solo los movimientos que un
    cierre de caja genero automaticamente (cierre_caja_id no nulo) tienen una
    sede conocida, via cierres_caja.sede_id. Los movimientos sin cierre_caja_id
    (pagos a proveedores, ajustes, gastos, etc.) no tienen sede de origen y se
    devuelven con sede_id=None salvo que se filtre explicitamente por sede_id
    (en cuyo caso quedan fuera).
    """
    q = db.query(MovimientoBancario, CierreCaja.sede_id, Sede.nombre).outerjoin(
        CierreCaja, MovimientoBancario.cierre_caja_id == CierreCaja.id
    ).outerjoin(
        Sede, CierreCaja.sede_id == Sede.id
    ).filter(MovimientoBancario.estado == "registrado")

    q = _filtro_fecha(q, MovimientoBancario, desde, hasta)
    if sede_id:
        q = q.filter(CierreCaja.sede_id == sede_id)

    filas = q.order_by(MovimientoBancario.fecha.desc()).all()

    movimientos = []
    total_por_sede = {}
    for m, sede_id_origen, sede_nombre in filas:
        movimientos.append({
            "id":               m.id,
            "fecha":            m.fecha.isoformat() if m.fecha else None,
            "tipo":             m.tipo,
            "monto":            round(float(m.monto or 0), 2),
            "moneda":           m.moneda,
            "concepto":         m.concepto,
            "categoria":        m.categoria,
            "registrado_por":   m.registrado_por,
            "cierre_caja_id":   m.cierre_caja_id,
            "sede_id":          sede_id_origen,
            "sede_nombre":      sede_nombre,
        })
        clave = sede_nombre or "Sin sede (origen no rastreable)"
        total_por_sede[clave] = round(total_por_sede.get(clave, 0) + float(m.monto or 0), 2)

    return {
        "movimientos":    movimientos,
        "total_por_sede": total_por_sede,
        "cantidad":       len(movimientos),
    }


@router.get("/clientes/resumen")
def reporte_clientes(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    import importlib
    _clientes_mod   = importlib.import_module("rutas.clientes")
    _stats_cliente  = _clientes_mod._stats_cliente
    _calcular_nivel = _clientes_mod._calcular_nivel

    clientes = db.query(Cliente).filter(Cliente.activo == True).all()
    niveles  = db.query(NivelFidelidad).order_by(NivelFidelidad.orden).all()

    por_nivel   = {n.nombre: 0 for n in niveles}
    por_nivel["Sin nivel"] = 0
    top_monto   = []
    top_compras = []

    for c in clientes:
        stats        = _stats_cliente(c.id, db)
        nivel        = _calcular_nivel(stats["total_compras"], stats["monto_acumulado_usd"], niveles)
        nombre_nivel = nivel["nombre"] if nivel else "Sin nivel"
        por_nivel[nombre_nivel] = por_nivel.get(nombre_nivel, 0) + 1
        top_monto.append({"id": c.id, "nombre": c.nombre, "monto": stats["monto_acumulado_usd"], "nivel": nombre_nivel})
        top_compras.append({"id": c.id, "nombre": c.nombre, "compras": stats["total_compras"], "nivel": nombre_nivel})

    top_monto.sort(key=lambda x: x["monto"], reverse=True)
    top_compras.sort(key=lambda x: x["compras"], reverse=True)

    hace_30 = datetime.now() - timedelta(days=30)
    vinculos_recientes = db.query(VentaCliente).join(
        Venta, Venta.id == VentaCliente.venta_id
    ).filter(Venta.fecha >= hace_30).all()
    ids_activos = {v.cliente_id for v in vinculos_recientes}
    inactivos   = [c for c in clientes if c.id not in ids_activos]

    nuevos = len(clientes)
    if desde or hasta:
        nuevos = sum(
            1 for c in clientes
            if c.fecha_registro
            and (not desde or c.fecha_registro.isoformat()[:10] >= desde)
            and (not hasta or c.fecha_registro.isoformat()[:10] <= hasta)
        )

    return {
        "total_clientes":  len(clientes),
        "nuevos_periodo":  nuevos,
        "por_nivel":       por_nivel,
        "top_monto":       top_monto[:10],
        "top_compras":     top_compras[:10],
        "inactivos_30d":   len(inactivos),
    }


# ---------------------------------------------------------------------------
# PRODUCTOS — rotación individual (panel lateral)
# ---------------------------------------------------------------------------

@router.get("/productos/{producto_id}/rotacion30")
def rotacion_30_dias(
    producto_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    hace_30 = datetime.utcnow() - timedelta(days=30)
    detalles = db.query(DetalleVenta, Venta).join(
        Venta, DetalleVenta.venta_id == Venta.id
    ).filter(
        DetalleVenta.producto_id == producto_id,
        Venta.fecha >= hace_30,
        Venta.estado != 'anulada',
    ).all()

    por_dia = {}
    for dv, v in detalles:
        dia = v.fecha.strftime('%Y-%m-%d')
        por_dia[dia] = por_dia.get(dia, 0) + int(dv.cantidad or 0)

    resultado = []
    for i in range(29, -1, -1):
        d = datetime.utcnow() - timedelta(days=i)
        fecha_str = d.strftime('%Y-%m-%d')
        resultado.append({
            "fecha":    fecha_str,
            "dia":      d.strftime('%d/%m'),
            "cantidad": por_dia.get(fecha_str, 0),
        })
    return resultado


# ---------------------------------------------------------------------------
# LIQUIDEZ PRUDENTE
# ---------------------------------------------------------------------------

@router.get("/liquidez-prudente")
def liquidez_prudente(
    colchon_pct: float = 0.18,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    from models import AbonoCredito, MovimientoBancario

    hoy = date.today()
    DIAS_HABILES_30 = 22  # ~22 días hábiles en 30 días corridos

    # ── 1. Deudas a proveedores: reusar el cálculo oficial de Pagos Proveedores ─
    from rutas.bancos import deuda_proveedores as _deuda_oficial
    saldos_oficiales = {d["proveedor_id"]: d["saldo_pendiente"] for d in _deuda_oficial(db)}
    deuda_total = sum(saldos_oficiales.values())

    proveedores = db.query(Proveedor).filter(Proveedor.activo == True).all()

    # ── Proyección ventas 10 días hábiles ───────────────────────────────────
    hace_30      = datetime.utcnow() - timedelta(days=30)
    ventas_30d   = db.query(Venta).filter(
        Venta.fecha >= hace_30,
        Venta.estado != 'anulada',
    ).all()
    total_v30 = sum(
        float(v.total or 0) if v.moneda_venta == 'USD'
        else float(v.total or 0) / float(v.tasa_bcv or 1)
        for v in ventas_30d
    )
    proyeccion_ventas_10d = round(total_v30 / DIAS_HABILES_30 * 10, 2)

    # ── Abonos proyectados 10d (para capa realista) ──────────────────────────
    abonos_30d = db.query(AbonoCredito).filter(
        AbonoCredito.fecha >= hace_30,
        AbonoCredito.monto > 0,
    ).all()
    total_abonos_30d  = sum(float(a.monto or 0) for a in abonos_30d)
    abonos_proyectados = round(total_abonos_30d / DIAS_HABILES_30 * 10, 2)

    # ── Detalle y crédito por proveedor ─────────────────────────────────────
    deudas = []
    credito_formal_total = 0.0
    credito_real_total   = 0.0
    sum_dias_formal = 0.0
    sum_dias_real   = 0.0
    sum_saldo       = 0.0

    for p in proveedores:
        saldo = saldos_oficiales.get(p.id, 0)
        if saldo <= 0:
            continue

        # Ritmo de abonos últimos 30 días (para capa realista)
        pagos = db.query(MovimientoBancario).filter(
            MovimientoBancario.proveedor_id == p.id,
            MovimientoBancario.tipo.in_(["pago_proveedor", "ajuste_deuda_proveedor"]),
            MovimientoBancario.estado == "registrado",
        ).all()

        dias_formal = int(p.dias_credito or 0)
        dias_real   = int(p.dias_credito_real if p.dias_credito_real is not None else dias_formal)

        # Fracción de la deuda cubierta dentro de los próximos 10 días hábiles
        cred_formal = round(saldo * min(1.0, 10 / dias_formal), 2) if dias_formal > 0 else 0.0
        cred_real   = round(saldo * min(1.0, 10 / dias_real),   2) if dias_real   > 0 else 0.0

        abono_prov  = round(abonos_proyectados * saldo / deuda_total, 2) if deuda_total > 0 else 0.0

        credito_formal_total += cred_formal
        credito_real_total   += cred_real
        sum_dias_formal      += dias_formal * saldo
        sum_dias_real        += dias_real   * saldo
        sum_saldo            += saldo

        deudas.append({
            "proveedor_id":        p.id,
            "proveedor":           p.nombre,
            "saldo":               round(saldo, 2),
            "dias_credito_formal": dias_formal,
            "dias_credito_real":   dias_real,
            "abono_proyectado_10d": abono_prov,
        })

    dias_formal_prom = round(sum_dias_formal / sum_saldo, 1) if sum_saldo > 0 else 0
    dias_real_prom   = round(sum_dias_real   / sum_saldo, 1) if sum_saldo > 0 else 0

    # ── Calcular liquidez prudente por capa ──────────────────────────────────
    base_c   = deuda_total + proyeccion_ventas_10d - credito_formal_total
    colchon_c = round(max(base_c, 0) * colchon_pct, 2)
    liquidez_c = round(max(0.0, base_c + colchon_c), 2)

    base_r   = deuda_total - abonos_proyectados + proyeccion_ventas_10d - credito_real_total
    colchon_r = round(max(base_r, 0) * colchon_pct, 2)
    liquidez_r = round(max(0.0, base_r + colchon_r), 2)

    return {
        "conservadora": {
            "liquidez":              liquidez_c,
            "deuda_proveedores":     round(deuda_total, 2),
            "proyeccion_ventas_10d": proyeccion_ventas_10d,
            "credito_proveedores":   round(credito_formal_total, 2),
            "dias_credito_usados":   dias_formal_prom,
            "colchon":               colchon_c,
        },
        "realista": {
            "liquidez":              liquidez_r,
            "deuda_proveedores":     round(deuda_total, 2),
            "abonos_proyectados":    abonos_proyectados,
            "proyeccion_ventas_10d": proyeccion_ventas_10d,
            "credito_proveedores":   round(credito_real_total, 2),
            "dias_credito_usados":   dias_real_prom,
            "colchon":               colchon_r,
        },
        "detalle_proveedores": sorted(deudas, key=lambda x: x["saldo"], reverse=True),
    }


@router.patch("/liquidez-prudente/credito-real/{proveedor_id}")
def actualizar_credito_real(
    proveedor_id: int,
    dias_credito_real: int = Body(..., embed=True),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    prov = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not prov:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    prov.dias_credito_real = max(0, dias_credito_real)
    db.commit()
    return {"ok": True}


@router.get("/ejecutivo/pdf")
def reporte_ejecutivo_pdf(
    dias: int = 90,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from fastapi.responses import StreamingResponse
    from datetime import timedelta
    import io

    AMARILLO  = colors.HexColor("#FFCC00")
    NEGRO     = colors.HexColor("#1A1A1A")
    VERDE     = colors.HexColor("#16A34A")
    GRIS      = colors.HexColor("#F5F5F0")
    GRIS_MED  = colors.HexColor("#888888")

    hoy    = datetime.utcnow()
    desde  = hoy - timedelta(days=dias)
    desde_str = desde.strftime('%d/%m/%Y')
    hasta_str = hoy.strftime('%d/%m/%Y')
    fecha_gen = hoy.strftime('%d/%m/%Y %H:%M')

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('titulo', fontSize=20, fontName='Helvetica-Bold',
                                   textColor=NEGRO, spaceAfter=2)
    sub_style    = ParagraphStyle('sub', fontSize=9, fontName='Helvetica',
                                   textColor=GRIS_MED, spaceAfter=12)
    seccion_style= ParagraphStyle('sec', fontSize=11, fontName='Helvetica-Bold',
                                   textColor=NEGRO, spaceBefore=16, spaceAfter=6)
    normal_style = ParagraphStyle('norm', fontSize=8, fontName='Helvetica',
                                   textColor=NEGRO)

    def tabla(data, col_widths, header_color=NEGRO, header_text=AMARILLO):
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), header_color),
            ('TEXTCOLOR',     (0,0), (-1,0), header_text),
            ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',      (0,0), (-1,0), 8),
            ('FONTSIZE',      (0,1), (-1,-1), 7.5),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, GRIS]),
            ('GRID',          (0,0), (-1,-1), 0.3, colors.HexColor('#DDDDDD')),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING',    (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING',   (0,0), (-1,-1), 6),
            ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ]))
        return t

    elements = []

    # ── Encabezado ────────────────────────────────────────────────────────
    elements.append(Paragraph("FERREUTIL", titulo_style))
    elements.append(Paragraph(
        f"Reporte Ejecutivo de Expansión · Período: {desde_str} → {hasta_str} ({dias} días) · Generado: {fecha_gen}",
        sub_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=AMARILLO, spaceAfter=12))

    # ── 1. KPIs generales ─────────────────────────────────────────────────
    ventas = db.query(Venta).filter(
        Venta.fecha >= desde,
        Venta.estado != 'anulada',
    ).all()
    total_usd = sum(float(v.total or 0) for v in ventas if v.moneda_venta == 'USD')
    total_bs  = sum(float(v.total or 0) for v in ventas if v.moneda_venta != 'USD')
    tasa_prom = 0.0
    ventas_bs = [v for v in ventas if v.moneda_venta != 'USD' and v.tasa_bcv]
    if ventas_bs:
        tasa_prom = sum(float(v.tasa_bcv) for v in ventas_bs) / len(ventas_bs)
    total_equiv = total_usd + (total_bs / tasa_prom if tasa_prom > 0 else 0)
    ticket_prom = total_equiv / len(ventas) if ventas else 0
    unidades = db.query(func.sum(DetalleVenta.cantidad)).join(
        Venta, Venta.id == DetalleVenta.venta_id
    ).filter(Venta.fecha >= desde, Venta.estado != 'anulada').scalar() or 0

    elements.append(Paragraph("1. Resumen General", seccion_style))
    kpi_data = [
        ['Métrica', 'Valor'],
        ['Total ventas (período)', str(len(ventas))],
        ['Total facturado USD equiv.', f'${total_equiv:,.2f}'],
        ['Promedio diario USD', f'${total_equiv/dias:,.2f}'],
        ['Ticket promedio USD', f'${ticket_prom:,.2f}'],
        ['Unidades vendidas', f'{int(unidades):,}'],
        ['Ventas por día hábil (est.)', f'{len(ventas)/dias*22/30:.1f}'],
    ]
    elements.append(tabla(kpi_data, [3.5*inch, 3.5*inch]))
    elements.append(Spacer(1, 8))

    # ── 2. Ventas por departamento ─────────────────────────────────────────
    elements.append(Paragraph("2. Ventas por Departamento", seccion_style))
    detalles  = db.query(DetalleVenta).join(
        Venta, Venta.id == DetalleVenta.venta_id
    ).filter(Venta.fecha >= desde, Venta.estado != 'anulada').all()
    productos_map = {p.id: p for p in db.query(Producto).all()}
    deptos_map    = {d.id: d.nombre for d in db.query(Departamento).all()}

    grupos_dept: dict = {}
    for d in detalles:
        prod    = productos_map.get(d.producto_id)
        dept_id = prod.departamento_id if prod else None
        if dept_id not in grupos_dept:
            grupos_dept[dept_id] = {'nombre': deptos_map.get(dept_id, 'Sin depto'), 'usd': 0.0, 'unidades': 0}
        grupos_dept[dept_id]['usd']      += float(d.precio_unitario or 0) * int(d.cantidad or 0)
        grupos_dept[dept_id]['unidades'] += int(d.cantidad or 0)

    total_dept = sum(g['usd'] for g in grupos_dept.values())
    dept_sorted = sorted(grupos_dept.values(), key=lambda x: x['usd'], reverse=True)

    dept_data = [['Departamento', 'Total USD', '% del total', 'Unidades']]
    for g in dept_sorted:
        pct = g['usd'] / total_dept * 100 if total_dept > 0 else 0
        dept_data.append([
            g['nombre'],
            f'${g["usd"]:,.2f}',
            f'{pct:.1f}%',
            f'{g["unidades"]:,}',
        ])
    elements.append(tabla(dept_data, [2.8*inch, 1.5*inch, 1.2*inch, 1.2*inch]))
    elements.append(Spacer(1, 8))

    # ── 3. Top 20 productos ────────────────────────────────────────────────
    elements.append(Paragraph("3. Top 20 Productos por Facturación", seccion_style))
    grupos_prod: dict = {}
    for d in detalles:
        pid = d.producto_id
        if pid not in grupos_prod:
            prod = productos_map.get(pid)
            grupos_prod[pid] = {'nombre': prod.nombre if prod else f'ID {pid}', 'usd': 0.0, 'unidades': 0}
        grupos_prod[pid]['usd']      += float(d.precio_unitario or 0) * int(d.cantidad or 0)
        grupos_prod[pid]['unidades'] += int(d.cantidad or 0)

    top20 = sorted(grupos_prod.values(), key=lambda x: x['usd'], reverse=True)[:20]
    total_top20 = sum(g['usd'] for g in top20)
    pct_top20   = total_top20 / total_dept * 100 if total_dept > 0 else 0

    prod_data = [['#', 'Producto', 'Total USD', 'Unidades']]
    for i, g in enumerate(top20, 1):
        prod_data.append([str(i), g['nombre'][:45], f'${g["usd"]:,.2f}', f'{g["unidades"]:,}'])
    elements.append(tabla(prod_data, [0.3*inch, 3.8*inch, 1.4*inch, 1.2*inch]))
    elements.append(Paragraph(
        f"Los top 20 productos representan ${total_top20:,.2f} USD ({pct_top20:.1f}% del total facturado en el período).",
        ParagraphStyle('nota', fontSize=7.5, textColor=GRIS_MED, spaceBefore=4)))
    elements.append(Spacer(1, 8))

    # ── 4. Análisis Pareto ────────────────────────────────────────────────
    elements.append(Paragraph("4. Análisis Pareto (Productos Clave)", seccion_style))
    prods_pareto = [p for p in productos_map.values() if p.es_producto_clave]
    usd_pareto   = sum(grupos_prod.get(p.id, {}).get('usd', 0) for p in prods_pareto)
    pct_pareto   = usd_pareto / total_dept * 100 if total_dept > 0 else 0

    pareto_data = [['Métrica', 'Valor'],
        ['Productos marcados como Pareto', str(len(prods_pareto))],
        ['Total productos en catálogo',    str(len(productos_map))],
        ['% del catálogo que es Pareto',   f'{len(prods_pareto)/len(productos_map)*100:.1f}%' if productos_map else '—'],
        ['Facturación productos Pareto',   f'${usd_pareto:,.2f}'],
        ['% del total que generan',        f'{pct_pareto:.1f}%'],
    ]
    elements.append(tabla(pareto_data, [3.5*inch, 3.5*inch]))
    elements.append(Spacer(1, 8))

    # ── 5. Ventas por vendedor ─────────────────────────────────────────────
    elements.append(Paragraph("5. Desempeño por Vendedor", seccion_style))
    grupos_vend: dict = {}
    for v in ventas:
        u = v.usuario or 'Sin usuario'
        if u not in grupos_vend:
            grupos_vend[u] = {'ventas': 0, 'usd': 0.0}
        grupos_vend[u]['ventas'] += 1
        if v.moneda_venta == 'USD':
            grupos_vend[u]['usd'] += float(v.total or 0)
        elif v.tasa_bcv:
            grupos_vend[u]['usd'] += float(v.total or 0) / float(v.tasa_bcv)

    vend_data = [['Vendedor', 'Ventas', 'Total USD', 'Ticket prom.']]
    for nombre, g in sorted(grupos_vend.items(), key=lambda x: x[1]['usd'], reverse=True):
        ticket = g['usd'] / g['ventas'] if g['ventas'] > 0 else 0
        vend_data.append([nombre, str(g['ventas']), f'${g["usd"]:,.2f}', f'${ticket:,.2f}'])
    elements.append(tabla(vend_data, [2.5*inch, 1*inch, 1.8*inch, 1.4*inch]))
    elements.append(Spacer(1, 8))

    # ── 6. Inventario snapshot ────────────────────────────────────────────
    elements.append(Paragraph("6. Snapshot de Inventario", seccion_style))
    todos_prods = list(productos_map.values())
    valor_inv   = sum(float(p.costo_usd or 0) * int(p.stock or 0) for p in todos_prods)
    sin_stock   = sum(1 for p in todos_prods if (p.stock or 0) <= 0)
    bajo_stock  = sum(1 for p in todos_prods if 0 < (p.stock or 0) <= 5)

    inv_data = [['Métrica', 'Valor'],
        ['Total SKUs activos',       f'{len(todos_prods):,}'],
        ['Valor inventario (costo)', f'${valor_inv:,.2f}'],
        ['SKUs sin stock',           str(sin_stock)],
        ['SKUs stock bajo (≤5)',     str(bajo_stock)],
        ['SKUs Pareto sin stock',    str(sum(1 for p in prods_pareto if (p.stock or 0) <= 0))],
    ]
    elements.append(tabla(inv_data, [3.5*inch, 3.5*inch]))

    # ── Pie ───────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=1, color=AMARILLO))
    elements.append(Paragraph(
        f"Ferreutil · Sistema administrativo · Reporte generado el {fecha_gen} · Confidencial",
        ParagraphStyle('pie', fontSize=7, textColor=GRIS_MED, spaceBefore=6, alignment=TA_CENTER)))

    # ── Generar PDF ───────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        topMargin=0.6*inch, bottomMargin=0.6*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch)
    doc.build(elements)
    buffer.seek(0)
    nombre_archivo = f"ferreutil_ejecutivo_{dias}d_{hoy.strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"})


@router.get("/sugerir-pareto")
def sugerir_pareto(
    dias: int = 90,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Devuelve IDs de productos que componen el top 20% de utilidad en los últimos N días.
    Utilidad = (precio_unitario - precio_base_snap) * cantidad, sumado por producto."""
    desde = datetime.utcnow() - timedelta(days=dias)
    detalles = db.query(DetalleVenta, Venta).join(
        Venta, DetalleVenta.venta_id == Venta.id
    ).filter(
        Venta.fecha >= desde,
        Venta.estado != "anulada",
    ).all()

    utilidad_por_prod = {}
    for d, v in detalles:
        pid = d.producto_id
        if not pid:
            continue
        precio  = float(d.precio_unitario or 0)
        costo   = float(d.precio_base_snap or 0)
        cant    = float(d.cantidad or 0)
        utilidad = (precio - costo) * cant
        utilidad_por_prod[pid] = utilidad_por_prod.get(pid, 0) + utilidad

    if not utilidad_por_prod:
        return {"ids": [], "total_evaluados": 0, "umbral_utilidad": 0}

    # Ordenar y cortar al top 20%
    ordenados = sorted(utilidad_por_prod.items(), key=lambda x: x[1], reverse=True)
    corte = max(1, int(len(ordenados) * 0.20))
    top = ordenados[:corte]

    return {
        "ids":                [pid for pid, _ in top],
        "total_evaluados":    len(ordenados),
        "umbral_utilidad":    round(top[-1][1], 2) if top else 0,
        "dias_evaluados":     dias,
    }
