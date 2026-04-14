from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import (
    DevolucionCliente, DetalleDevolucionCliente,
    DevolucionProveedor,
    Producto, Cliente, Proveedor, RecepcionCompra,
    MovimientoBancario, CuentaBancaria,
)
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/devoluciones", tags=["devoluciones"])


# ---------------------------------------------------------------------------
# Helpers — serialización
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
                "producto_id":      dd.producto_id,
                "nombre_producto":  dd.nombre_producto,
                "cantidad":         dd.cantidad,
                "precio_unitario":  dd.precio_unitario,
                "vuelve_inventario":dd.vuelve_inventario,
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


# ---------------------------------------------------------------------------
# Devoluciones de clientes
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

        # Retornar al inventario si aplica
        if item.get("vuelve_inventario", True) and item.get("producto_id"):
            prod = db.query(Producto).filter(Producto.id == item["producto_id"]).first()
            if prod:
                prod.stock += int(float(item.get("cantidad", 0)))

    # Acreditar al cliente si es tipo crédito
    if datos.get("tipo_resolucion") == "credito" and datos.get("cliente_id"):
        cliente = db.query(Cliente).filter(Cliente.id == datos["cliente_id"]).first()
        if cliente:
            cliente.credito_disponible = round((cliente.credito_disponible or 0) + monto_total, 2)

    # Si se devuelve dinero, registrar egreso en movimientos bancarios
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

    # Descontar stock inmediatamente
    if datos.get("producto_id"):
        prod = db.query(Producto).filter(Producto.id == datos["producto_id"]).first()
        if prod:
            prod.stock = max(0, prod.stock - int(cantidad))

    # Si es crédito a favor: registrar en el proveedor
    if datos.get("tipo_resolucion") == "credito" and datos.get("proveedor_id"):
        prov = db.query(Proveedor).filter(Proveedor.id == datos["proveedor_id"]).first()
        if prov:
            prov.credito_disponible = round((prov.credito_disponible or 0) + monto_total, 2)

    # Si es descuento en factura: descontar del monto de la recepción pendiente
    if datos.get("tipo_resolucion") == "descuento_factura" and datos.get("orden_compra_id"):
        recepcion = db.query(RecepcionCompra).filter(
            RecepcionCompra.orden_id  == datos["orden_compra_id"],
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
