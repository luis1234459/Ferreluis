from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import (
    Venta, PagoVenta, DetalleVenta, Producto, VarianteProducto, CierreCaja, LABELS_METODO,
    Cliente, VentaCliente, NivelFidelidad,
    Departamento, Proveedor, OrdenCompra, DetalleOrdenCompra, RecepcionCompra,
    VendedorPerfil, ComisionVenta, Usuario,
    Area, Pasillo, Estante, UbicacionProducto,
)
from datetime import datetime, timedelta, date
from rutas.usuarios import require_admin
from typing import Optional

router = APIRouter(prefix="/reportes", tags=["reportes"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _filtro_fecha(query, modelo, desde, hasta):
    if desde:
        query = query.filter(modelo.fecha >= desde)
    if hasta:
        query = query.filter(modelo.fecha <= hasta)
    return query


def _venta_ids_en_periodo(db: Session, desde, hasta) -> set:
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
    _: None = Depends(require_admin),
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
    _: None = Depends(require_admin),
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
            "vendedor_id":          g["vendedor_id"],
            "vendedor_nombre":      g["vendedor_nombre"],
            "cantidad_ventas":      len(g["ventas_ids"]),
            "total_usd":            round(g["total_usd"], 2),
            "total_comision":       round(g["total_comision"], 2),
            "pct_comision_promedio": round(g["total_comision"] / g["total_usd"] * 100, 2) if g["total_usd"] > 0 else 0,
        })
    return resultado


# ---------------------------------------------------------------------------
# PRODUCTOS — top (mejorado con depto y proveedor)
# ---------------------------------------------------------------------------

@router.get("/productos/top")
def top_productos(
    n: int = 10,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
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
    productos  = db.query(Producto).all()
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
    productos     = db.query(Producto).all()
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
    productos   = db.query(Producto).all()
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
    productos_clave = db.query(Producto).filter(Producto.es_producto_clave == True).all()

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
    productos     = db.query(Producto).all()
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
