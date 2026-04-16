from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import (
    DevolucionCliente, DetalleDevolucionCliente,
    DevolucionProveedor,
    Producto, Cliente, Proveedor, RecepcionCompra,
    MovimientoBancario, CuentaBancaria, MetodoPagoCuenta,
    Venta, VentaCliente, DetalleVenta,
)
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/devoluciones", tags=["devoluciones"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serializar_dev_cliente(d: DevolucionCliente, db: Session) -> dict:
    detalles = db.query(DetalleDevolucionCliente).filter(
        DetalleDevolucionCliente.devolucion_id == d.id
    ).all()
    cliente = db.query(Cliente).filter(Cliente.id == d.cliente_id).first() if d.cliente_id else None
    return {
        "id":              d.id,
        "venta_id":        d.venta_id,
        "cliente_id":      d.cliente_id,
        "cliente_nombre":  cliente.nombre if cliente else None,
        "usuario":         d.usuario,
        "fecha":           d.fecha.isoformat() if d.fecha else None,
        "motivo":          d.motivo,
        "tipo_resolucion": d.tipo_resolucion,
        "monto_total":     round(float(d.monto_total or 0), 2),
        "observacion":     d.observacion,
        "detalles": [
            {
                "producto_id":       dd.producto_id,
                "nombre_producto":   dd.nombre_producto,
                "cantidad":          dd.cantidad,
                "precio_unitario":   dd.precio_unitario,
                "vuelve_inventario": dd.vuelve_inventario,
            }
            for dd in detalles
        ],
    }


def _serializar_dev_proveedor(d: DevolucionProveedor, db: Session) -> dict:
    prov = db.query(Proveedor).filter(Proveedor.id == d.proveedor_id).first() if d.proveedor_id else None
    return {
        "id":               d.id,
        "proveedor_id":     d.proveedor_id,
        "proveedor_nombre": prov.nombre if prov else None,
        "producto_id":      d.producto_id,
        "nombre_producto":  d.nombre_producto,
        "cantidad":         d.cantidad,
        "costo_unitario":   d.costo_unitario,
        "monto_total":      round(float(d.monto_total or 0), 2),
        "motivo":           d.motivo,
        "tipo_resolucion":  d.tipo_resolucion,
        "estado":           d.estado,
        "fecha":            d.fecha.isoformat() if d.fecha else None,
        "fecha_resolucion": d.fecha_resolucion.isoformat() if d.fecha_resolucion else None,
        "orden_compra_id":  d.orden_compra_id,
        "usuario":          d.usuario,
        "observacion":      d.observacion,
    }


def _cuenta_para_metodo(db: Session, metodo_pago: str) -> Optional[int]:
    """Devuelve el cuenta_id vinculado al método de pago, o None si no existe."""
    mc = db.query(MetodoPagoCuenta).filter(
        MetodoPagoCuenta.metodo_pago == metodo_pago,
        MetodoPagoCuenta.activo == True,
    ).first()
    return mc.cuenta_id if mc else None


# ---------------------------------------------------------------------------
# Devoluciones de clientes — búsqueda de ventas
# ---------------------------------------------------------------------------

@router.get("/buscar-ventas")
def buscar_ventas(
    telefono:     Optional[str] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin:    Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Devuelve ventas con sus productos.
    Requiere: telefono  ó  fecha_inicio (+ fecha_fin opcional).
    """
    if not telefono and not fecha_inicio:
        raise HTTPException(status_code=400,
                            detail="Proporciona telefono o fecha_inicio")

    if telefono:
        cliente = db.query(Cliente).filter(Cliente.telefono == telefono).first()
        if not cliente:
            return []
        vinculos  = db.query(VentaCliente).filter(VentaCliente.cliente_id == cliente.id).all()
        venta_ids = [v.venta_id for v in vinculos]
        if not venta_ids:
            return []
        ventas = (
            db.query(Venta)
            .filter(Venta.id.in_(venta_ids))
            .order_by(Venta.fecha.desc())
            .limit(50)
            .all()
        )
    else:
        try:
            fi = datetime.strptime(fecha_inicio, "%Y-%m-%d")
            ff = (
                datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
                if fecha_fin
                else fi.replace(hour=23, minute=59, second=59)
            )
        except ValueError:
            raise HTTPException(status_code=400,
                                detail="Formato de fecha inválido — usa YYYY-MM-DD")
        ventas = (
            db.query(Venta)
            .filter(Venta.fecha >= fi, Venta.fecha <= ff)
            .order_by(Venta.fecha.desc())
            .limit(100)
            .all()
        )

    resultado = []
    for v in ventas:
        detalles = db.query(DetalleVenta).filter(DetalleVenta.venta_id == v.id).all()
        vc = db.query(VentaCliente).filter(VentaCliente.venta_id == v.id).first()

        cliente_nombre   = "Consumidor Final"
        cliente_telefono = None
        cliente_id       = None
        es_consumidor    = True

        if vc:
            c = db.query(Cliente).filter(Cliente.id == vc.cliente_id).first()
            if c:
                cliente_nombre   = c.nombre
                cliente_telefono = c.telefono
                cliente_id       = c.id
                es_consumidor    = bool(c.es_cliente_generico)

        productos = []
        for d in detalles:
            prod  = db.query(Producto).filter(Producto.id == d.producto_id).first()
            productos.append({
                "detalle_id":      d.id,
                "producto_id":     d.producto_id,
                "nombre":          prod.nombre if prod else f"Producto #{d.producto_id}",
                "cantidad":        d.cantidad,
                "precio_unitario": round(float(d.precio_unitario or 0), 2),
            })

        resultado.append({
            "venta_id":         v.id,
            "fecha":            v.fecha.isoformat() if v.fecha else None,
            "cliente_nombre":   cliente_nombre,
            "cliente_telefono": cliente_telefono,
            "cliente_id":       cliente_id,
            "es_consumidor":    es_consumidor,
            "total":            round(float(v.total or 0), 2),
            "moneda":           v.moneda_venta,
            "productos":        productos,
        })

    return resultado


# ---------------------------------------------------------------------------
# Devoluciones de clientes — registro nuevo (por detalle individual)
# ---------------------------------------------------------------------------

@router.post("/cliente/procesar")
def procesar_devolucion_cliente(datos: dict, db: Session = Depends(get_db)):
    """
    Procesa una devolución de un producto individual.
    Body: { detalle_id, producto_id, cantidad_devuelta, tipo,
            producto_nuevo_id, monto_diferencia, direccion_diferencia,
            metodo_pago, usuario, observacion }
    """
    detalle_id        = datos.get("detalle_id")
    cantidad_dev      = float(datos.get("cantidad_devuelta", 1) or 1)
    tipo              = datos.get("tipo", "reembolso")
    producto_nuevo_id = datos.get("producto_nuevo_id")
    monto_diferencia  = float(datos.get("monto_diferencia", 0) or 0)
    dir_diferencia    = datos.get("direccion_diferencia", "ninguna")
    metodo_pago       = datos.get("metodo_pago", "efectivo_usd")
    usuario           = datos.get("usuario", "admin")
    observacion       = datos.get("observacion", "")

    if not detalle_id:
        raise HTTPException(status_code=400, detail="detalle_id es requerido")
    if tipo not in ("reembolso", "cambio", "credito"):
        raise HTTPException(status_code=400, detail="tipo debe ser reembolso | cambio | credito")
    if cantidad_dev <= 0:
        raise HTTPException(status_code=400, detail="cantidad_devuelta debe ser > 0")

    # ── Cargar detalle de venta ──────────────────────────────────────────────
    detalle = db.query(DetalleVenta).filter(DetalleVenta.id == detalle_id).first()
    if not detalle:
        raise HTTPException(status_code=404, detail="Detalle de venta no encontrado")
    if cantidad_dev > float(detalle.cantidad or 0):
        raise HTTPException(
            status_code=400,
            detail=f"No puede devolver más de {detalle.cantidad} unidad(es)"
        )

    # ── Cargar cliente vinculado ─────────────────────────────────────────────
    vc      = db.query(VentaCliente).filter(VentaCliente.venta_id == detalle.venta_id).first()
    cliente = None
    if vc:
        cliente = db.query(Cliente).filter(Cliente.id == vc.cliente_id).first()

    # ── Producto original ────────────────────────────────────────────────────
    prod_original   = db.query(Producto).filter(Producto.id == detalle.producto_id).first()
    nombre_producto = prod_original.nombre if prod_original else f"Producto #{detalle.producto_id}"
    precio_unitario = round(float(detalle.precio_unitario or 0), 2)
    monto_devolucion = round(precio_unitario * cantidad_dev, 2)

    # ── 1. Restaurar stock del producto original ─────────────────────────────
    if prod_original:
        prod_original.stock = int(float(prod_original.stock or 0)) + int(cantidad_dev)

    ahora = datetime.now()

    # ── 2. Lógica por tipo ───────────────────────────────────────────────────
    METODOS_USD_SET = {"efectivo_usd", "zelle", "binance", "credito"}

    if tipo == "reembolso":
        # Egreso de caja — se devuelve dinero al cliente
        cuenta_id = _cuenta_para_metodo(db, metodo_pago)
        moneda    = "USD" if metodo_pago in METODOS_USD_SET else "Bs"
        db.add(MovimientoBancario(
            fecha             = ahora,
            tipo              = "devolucion_cliente",
            cuenta_origen_id  = cuenta_id,
            monto             = monto_devolucion,
            moneda            = moneda,
            concepto          = f"Reembolso devolución venta #{detalle.venta_id}",
            categoria         = "devoluciones",
            registrado_por    = usuario,
            estado            = "registrado",
        ))

    elif tipo == "cambio":
        # Descontar stock del producto nuevo
        if producto_nuevo_id:
            prod_nuevo = db.query(Producto).filter(Producto.id == producto_nuevo_id).first()
            if prod_nuevo:
                prod_nuevo.stock = max(0, int(float(prod_nuevo.stock or 0)) - int(cantidad_dev))

        # Diferencia de precio
        if dir_diferencia == "cobrar" and monto_diferencia > 0:
            # Cliente paga la diferencia → ingreso de caja
            cuenta_id = _cuenta_para_metodo(db, metodo_pago)
            db.add(MovimientoBancario(
                fecha              = ahora,
                tipo               = "ingreso_venta",
                cuenta_destino_id  = cuenta_id,
                monto              = round(monto_diferencia, 2),
                moneda             = "USD",
                concepto           = f"Cobro diferencia cambio venta #{detalle.venta_id}",
                categoria          = "ventas",
                registrado_por     = usuario,
                estado             = "registrado",
            ))
        elif dir_diferencia == "devolver" and monto_diferencia > 0:
            # Negocio devuelve diferencia → egreso de caja
            cuenta_id = _cuenta_para_metodo(db, metodo_pago)
            db.add(MovimientoBancario(
                fecha             = ahora,
                tipo              = "devolucion_cliente",
                cuenta_origen_id  = cuenta_id,
                monto             = round(monto_diferencia, 2),
                moneda            = "USD",
                concepto          = f"Vuelto cambio devolución venta #{detalle.venta_id}",
                categoria         = "devoluciones",
                registrado_por    = usuario,
                estado            = "registrado",
            ))

    elif tipo == "credito":
        # Acreditar saldo_a_favor al cliente
        if cliente and not cliente.es_cliente_generico:
            cliente.saldo_a_favor = round(float(cliente.saldo_a_favor or 0) + monto_devolucion, 2)

    # ── 3. Registrar DevolucionCliente + Detalle ─────────────────────────────
    dev = DevolucionCliente(
        venta_id        = detalle.venta_id,
        cliente_id      = cliente.id if cliente else None,
        usuario         = usuario,
        motivo          = f"Devolución {tipo}",
        tipo_resolucion = tipo,
        monto_total     = monto_devolucion,
        observacion     = observacion,
    )
    db.add(dev)
    db.flush()

    db.add(DetalleDevolucionCliente(
        devolucion_id     = dev.id,
        producto_id       = detalle.producto_id,
        nombre_producto   = nombre_producto,
        cantidad          = cantidad_dev,
        precio_unitario   = precio_unitario,
        vuelve_inventario = True,
    ))

    db.commit()
    db.refresh(dev)

    return {
        "ok":            True,
        "devolucion_id": dev.id,
        "monto_total":   monto_devolucion,
        "tipo":          tipo,
        "saldo_a_favor": round(float(cliente.saldo_a_favor or 0), 2) if cliente else 0,
    }


# ---------------------------------------------------------------------------
# Devoluciones de clientes — historial (endpoint legado, se mantiene)
# ---------------------------------------------------------------------------

@router.get("/cliente/")
def listar_devoluciones_cliente(db: Session = Depends(get_db)):
    devs = db.query(DevolucionCliente).order_by(DevolucionCliente.fecha.desc()).all()
    return [_serializar_dev_cliente(d, db) for d in devs]


@router.post("/cliente/")
def registrar_devolucion_cliente(datos: dict, db: Session = Depends(get_db)):
    productos_data = datos.get("productos", [])
    if not productos_data:
        raise HTTPException(status_code=400, detail="Debe incluir al menos un producto")
    if not datos.get("motivo"):
        raise HTTPException(status_code=400, detail="El motivo es obligatorio")

    monto_total = sum(
        float(p.get("precio_unitario", 0)) * float(p.get("cantidad", 0))
        for p in productos_data
    )

    dev = DevolucionCliente(
        venta_id        = datos.get("venta_id"),
        cliente_id      = datos.get("cliente_id"),
        usuario         = datos.get("usuario", "admin"),
        motivo          = datos["motivo"],
        tipo_resolucion = datos.get("tipo_resolucion", "dinero"),
        monto_total     = round(monto_total, 2),
        observacion     = datos.get("observacion"),
    )
    db.add(dev)
    db.flush()

    for item in productos_data:
        dd = DetalleDevolucionCliente(
            devolucion_id     = dev.id,
            producto_id       = item.get("producto_id"),
            nombre_producto   = item.get("nombre_producto", ""),
            cantidad          = float(item.get("cantidad", 0)),
            precio_unitario   = float(item.get("precio_unitario", 0)),
            vuelve_inventario = item.get("vuelve_inventario", True),
        )
        db.add(dd)
        if item.get("vuelve_inventario", True) and item.get("producto_id"):
            prod = db.query(Producto).filter(Producto.id == item["producto_id"]).first()
            if prod:
                prod.stock += int(float(item.get("cantidad", 0)))

    if datos.get("tipo_resolucion") == "credito" and datos.get("cliente_id"):
        cliente = db.query(Cliente).filter(Cliente.id == datos["cliente_id"]).first()
        if cliente:
            cliente.credito_disponible = round((cliente.credito_disponible or 0) + monto_total, 2)

    if datos.get("tipo_resolucion") == "dinero":
        moneda     = datos.get("moneda", "USD")
        nombre_caja = "Caja Ferreutil USD" if moneda == "USD" else "Caja Ferreutil Bs"
        cuenta_caja = db.query(CuentaBancaria).filter(
            CuentaBancaria.nombre == nombre_caja,
            CuentaBancaria.activa == True,
        ).first()
        if cuenta_caja:
            db.add(MovimientoBancario(
                tipo             = "devolucion_cliente",
                cuenta_origen_id = cuenta_caja.id,
                monto            = round(monto_total, 2),
                moneda           = moneda,
                concepto         = f"Devolución cliente - {datos.get('motivo', '')}",
                categoria        = "devoluciones",
                registrado_por   = datos.get("usuario", "admin"),
            ))

    db.commit()
    db.refresh(dev)
    return _serializar_dev_cliente(dev, db)


# ---------------------------------------------------------------------------
# Devoluciones a proveedores
# ---------------------------------------------------------------------------

@router.get("/proveedor/pendientes/")
def devoluciones_proveedor_pendientes(db: Session = Depends(get_db)):
    devs = db.query(DevolucionProveedor).filter(
        DevolucionProveedor.estado == "pendiente"
    ).order_by(DevolucionProveedor.fecha.desc()).all()
    return [_serializar_dev_proveedor(d, db) for d in devs]


@router.get("/proveedor/")
def listar_devoluciones_proveedor(
    proveedor_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(DevolucionProveedor)
    if proveedor_id:
        q = q.filter(DevolucionProveedor.proveedor_id == proveedor_id)
    devs = q.order_by(DevolucionProveedor.fecha.desc()).all()
    return [_serializar_dev_proveedor(d, db) for d in devs]


@router.post("/proveedor/")
def registrar_devolucion_proveedor(datos: dict, db: Session = Depends(get_db)):
    cantidad       = float(datos.get("cantidad", 0))
    costo_unitario = float(datos.get("costo_unitario", 0))
    if cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor que cero")
    if not datos.get("motivo"):
        raise HTTPException(status_code=400, detail="El motivo es obligatorio")

    monto_total = round(cantidad * costo_unitario, 2)

    dev = DevolucionProveedor(
        proveedor_id    = datos.get("proveedor_id"),
        producto_id     = datos.get("producto_id"),
        nombre_producto = datos.get("nombre_producto", ""),
        cantidad        = cantidad,
        costo_unitario  = costo_unitario,
        monto_total     = monto_total,
        motivo          = datos["motivo"],
        tipo_resolucion = datos.get("tipo_resolucion", "credito"),
        estado          = "pendiente",
        orden_compra_id = datos.get("orden_compra_id"),
        usuario         = datos.get("usuario", "admin"),
        observacion     = datos.get("observacion"),
    )
    db.add(dev)
    db.flush()

    if datos.get("producto_id"):
        prod = db.query(Producto).filter(Producto.id == datos["producto_id"]).first()
        if prod:
            prod.stock = max(0, prod.stock - int(cantidad))

    if datos.get("tipo_resolucion") == "credito" and datos.get("proveedor_id"):
        prov = db.query(Proveedor).filter(Proveedor.id == datos["proveedor_id"]).first()
        if prov:
            prov.credito_disponible = round((prov.credito_disponible or 0) + monto_total, 2)

    if datos.get("tipo_resolucion") == "descuento_factura" and datos.get("orden_compra_id"):
        recepcion = db.query(RecepcionCompra).filter(
            RecepcionCompra.orden_id    == datos["orden_compra_id"],
            RecepcionCompra.estado_pago == "pendiente",
        ).first()
        if recepcion and recepcion.monto_factura:
            recepcion.monto_factura = max(0, round(recepcion.monto_factura - monto_total, 2))

    db.commit()
    db.refresh(dev)
    return _serializar_dev_proveedor(dev, db)


@router.put("/proveedor/{devolucion_id}/resolver")
def resolver_devolucion_proveedor(
    devolucion_id: int,
    datos: dict = {},
    db: Session = Depends(get_db),
):
    dev = db.query(DevolucionProveedor).filter(DevolucionProveedor.id == devolucion_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Devolución no encontrada")
    dev.estado           = "resuelto"
    dev.fecha_resolucion = datetime.now()
    if "tipo_resolucion" in datos:
        dev.tipo_resolucion = datos["tipo_resolucion"]
    if "observacion" in datos:
        dev.observacion = datos["observacion"]
    db.commit()
    return _serializar_dev_proveedor(dev, db)