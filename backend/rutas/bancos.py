"""
Módulo Bancario — Cuentas, Movimientos y Pagos a Proveedores.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import (
    CuentaBancaria, MetodoPagoCuenta, MovimientoBancario,
    PagoVenta, Proveedor, OrdenCompra, DetalleOrdenCompra,
    CierreCaja,
)
from rutas.usuarios import require_admin
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/bancos", tags=["bancos"])

TIPOS_VALIDOS = {
    "ingreso_venta", "transferencia_interna", "pago_proveedor",
    "gasto_nomina", "gasto_operativo", "gasto_administrativo",
    "ingreso_externo", "retiro", "devolucion_cliente",
}
CATEGORIAS_POR_TIPO = {
    "ingreso_venta":        "ventas",
    "transferencia_interna":"financiero",
    "pago_proveedor":       "proveedores",
    "gasto_nomina":         "nomina",
    "gasto_operativo":      "operativo",
    "gasto_administrativo": "administrativo",
    "ingreso_externo":      "financiero",
    "retiro":               "propietario",
    "devolucion_cliente":   "devoluciones",
}

# ---------------------------------------------------------------------------
# Seeds — ejecutar una vez al arrancar si la tabla está vacía
# ---------------------------------------------------------------------------

CUENTAS_SEED = [
    dict(nombre="Caja Ferreutil USD",    banco="Caja",       tipo_cuenta="caja_fisica",       moneda="USD", identificador=None,              orden_display=1),
    dict(nombre="Caja Ferreutil Bs",     banco="Caja",       tipo_cuenta="caja_fisica",       moneda="Bs",  identificador=None,              orden_display=2),
    dict(nombre="Chase Bank Zelle",      banco="Chase",      tipo_cuenta="billetera_digital", moneda="USD", identificador="ferreutil.123",   orden_display=3),
    dict(nombre="Trust Bank Zelle",      banco="Trust",      tipo_cuenta="billetera_digital", moneda="USD", identificador="aquatimeca1",     orden_display=4),
    dict(nombre="Provincial Personal",   banco="Provincial", tipo_cuenta="personal",          moneda="Bs",  identificador=None,              orden_display=5),
    dict(nombre="Venezuela Personal",    banco="Venezuela",  tipo_cuenta="personal",          moneda="Bs",  identificador=None,              orden_display=6),
    dict(nombre="Banesco Personal",      banco="Banesco",    tipo_cuenta="personal",          moneda="Bs",  identificador=None,              orden_display=7),
    dict(nombre="Banesco Jurídica",      banco="Banesco",    tipo_cuenta="juridica",          moneda="Bs",  identificador=None,              orden_display=8),
    dict(nombre="Venezuela Jurídica",    banco="Venezuela",  tipo_cuenta="juridica",          moneda="Bs",  identificador=None,              orden_display=9),
    dict(nombre="Banesco Personal Eira", banco="Banesco",    tipo_cuenta="personal",          moneda="Bs",  identificador=None,              orden_display=10),
    dict(nombre="Provincial Jurídica",   banco="Provincial", tipo_cuenta="juridica",          moneda="Bs",  identificador=None,              orden_display=11),
    dict(nombre="Binance USDT",          banco="Binance",    tipo_cuenta="billetera_digital", moneda="USD", identificador=None,              orden_display=12),
]

VINCULOS_SEED = [
    ("efectivo_usd",    "Caja Ferreutil USD"),
    ("efectivo_bs",     "Caja Ferreutil Bs"),
    ("zelle",           "Chase Bank Zelle"),
    ("zelle",           "Trust Bank Zelle"),
    ("pago_movil",      "Provincial Personal"),
    ("pago_movil",      "Venezuela Personal"),
    ("transferencia_bs","Provincial Personal"),
    ("transferencia_bs","Banesco Personal"),
    ("transferencia_bs","Venezuela Personal"),
    ("transferencia_bs","Banesco Jurídica"),
    ("transferencia_bs","Venezuela Jurídica"),
    ("binance",         "Binance USDT"),
    ("punto_banesco",   "Banesco Personal Eira"),
    ("punto_provincial","Provincial Jurídica"),
]


def sembrar_si_vacio(db: Session):
    if db.query(CuentaBancaria).count() > 0:
        return
    cuentas_creadas = {}
    for d in CUENTAS_SEED:
        c = CuentaBancaria(**d)
        db.add(c)
        db.flush()
        cuentas_creadas[d["nombre"]] = c.id

    for metodo, nombre_cuenta in VINCULOS_SEED:
        cuenta_id = cuentas_creadas.get(nombre_cuenta)
        if cuenta_id:
            db.add(MetodoPagoCuenta(metodo_pago=metodo, cuenta_id=cuenta_id))

    db.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _saldo_cuenta(cuenta_id: int, db: Session) -> float:
    ingresos = db.query(func.sum(MovimientoBancario.monto)).filter(
        MovimientoBancario.cuenta_destino_id == cuenta_id,
        MovimientoBancario.estado == "registrado",
    ).scalar() or 0.0
    salidas = db.query(func.sum(MovimientoBancario.monto)).filter(
        MovimientoBancario.cuenta_origen_id == cuenta_id,
        MovimientoBancario.estado == "registrado",
    ).scalar() or 0.0
    return round(float(ingresos) - float(salidas), 2)


def _serializar_cuenta(c: CuentaBancaria, db: Session) -> dict:
    return {
        "id":            c.id,
        "nombre":        c.nombre,
        "banco":         c.banco,
        "tipo_cuenta":   c.tipo_cuenta,
        "moneda":        c.moneda,
        "identificador": c.identificador,
        "activa":        c.activa,
        "orden_display": c.orden_display,
        "saldo":         _saldo_cuenta(c.id, db),
    }


def _serializar_movimiento(m: MovimientoBancario, db: Session) -> dict:
    c_orig = db.query(CuentaBancaria).filter(CuentaBancaria.id == m.cuenta_origen_id).first()  if m.cuenta_origen_id  else None
    c_dest = db.query(CuentaBancaria).filter(CuentaBancaria.id == m.cuenta_destino_id).first() if m.cuenta_destino_id else None
    prov   = db.query(Proveedor).filter(Proveedor.id == m.proveedor_id).first()                if m.proveedor_id      else None
    return {
        "id":               m.id,
        "fecha":            m.fecha.isoformat() if m.fecha else None,
        "tipo":             m.tipo,
        "cuenta_origen":    c_orig.nombre if c_orig else None,
        "cuenta_origen_id": m.cuenta_origen_id,
        "cuenta_destino":   c_dest.nombre if c_dest else None,
        "cuenta_destino_id":m.cuenta_destino_id,
        "monto":            round(float(m.monto or 0), 2),
        "moneda":           m.moneda,
        "tasa_cambio":      m.tasa_cambio,
        "monto_convertido": m.monto_convertido,
        "referencia":       m.referencia,
        "concepto":         m.concepto,
        "beneficiario":     m.beneficiario,
        "categoria":        m.categoria,
        "proveedor":        prov.nombre if prov else None,
        "proveedor_id":     m.proveedor_id,
        "orden_compra_id":  m.orden_compra_id,
        "registrado_por":   m.registrado_por,
        "estado":           m.estado,
        "venta_id":         m.venta_id,
    }


# ---------------------------------------------------------------------------
# CUENTAS BANCARIAS
# ---------------------------------------------------------------------------

@router.get("/cuentas/")
def listar_cuentas(db: Session = Depends(get_db)):
    sembrar_si_vacio(db)
    cuentas = db.query(CuentaBancaria).filter(CuentaBancaria.activa == True).order_by(CuentaBancaria.orden_display).all()
    return [_serializar_cuenta(c, db) for c in cuentas]


@router.post("/cuentas/", dependencies=[Depends(require_admin)])
def crear_cuenta(datos: dict, db: Session = Depends(get_db)):
    c = CuentaBancaria(
        nombre        = datos["nombre"],
        banco         = datos.get("banco", ""),
        tipo_cuenta   = datos.get("tipo_cuenta", "personal"),
        moneda        = datos.get("moneda", "Bs"),
        identificador = datos.get("identificador"),
        orden_display = datos.get("orden_display", 99),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _serializar_cuenta(c, db)


@router.put("/cuentas/{cuenta_id}", dependencies=[Depends(require_admin)])
def editar_cuenta(cuenta_id: int, datos: dict, db: Session = Depends(get_db)):
    c = db.query(CuentaBancaria).filter(CuentaBancaria.id == cuenta_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    for k in ("nombre", "banco", "tipo_cuenta", "moneda", "identificador", "orden_display", "activa"):
        if k in datos:
            setattr(c, k, datos[k])
    db.commit()
    return _serializar_cuenta(c, db)


@router.get("/cuentas/{cuenta_id}/movimientos")
def movimientos_de_cuenta(
    cuenta_id: int,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    q = db.query(MovimientoBancario).filter(
        (MovimientoBancario.cuenta_origen_id == cuenta_id) |
        (MovimientoBancario.cuenta_destino_id == cuenta_id)
    )
    if desde:
        q = q.filter(MovimientoBancario.fecha >= datetime.fromisoformat(desde))
    if hasta:
        q = q.filter(MovimientoBancario.fecha <= datetime.fromisoformat(hasta))
    return [_serializar_movimiento(m, db) for m in q.order_by(MovimientoBancario.fecha.desc()).all()]


# ---------------------------------------------------------------------------
# MÉTODOS DE PAGO → CUENTAS (para el frontend de Ventas)
# ---------------------------------------------------------------------------

@router.get("/metodos-pago/cuentas")
def metodos_pago_con_cuentas(db: Session = Depends(get_db)):
    sembrar_si_vacio(db)
    vinculos = db.query(MetodoPagoCuenta).filter(MetodoPagoCuenta.activo == True).all()
    resultado = {}
    for v in vinculos:
        cuenta = db.query(CuentaBancaria).filter(CuentaBancaria.id == v.cuenta_id, CuentaBancaria.activa == True).first()
        if not cuenta:
            continue
        if v.metodo_pago not in resultado:
            resultado[v.metodo_pago] = []
        resultado[v.metodo_pago].append({
            "id":            cuenta.id,
            "nombre":        cuenta.nombre,
            "banco":         cuenta.banco,
            "identificador": cuenta.identificador,
            "moneda":        cuenta.moneda,
        })
    return resultado


# ---------------------------------------------------------------------------
# MOVIMIENTOS BANCARIOS
# ---------------------------------------------------------------------------

@router.get("/movimientos/")
def listar_movimientos(
    tipo:      Optional[str] = None,
    cuenta_id: Optional[int] = None,
    categoria: Optional[str] = None,
    desde:     Optional[str] = None,
    hasta:     Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    q = db.query(MovimientoBancario)
    if tipo:
        q = q.filter(MovimientoBancario.tipo == tipo)
    if categoria:
        q = q.filter(MovimientoBancario.categoria == categoria)
    if cuenta_id:
        q = q.filter(
            (MovimientoBancario.cuenta_origen_id == cuenta_id) |
            (MovimientoBancario.cuenta_destino_id == cuenta_id)
        )
    if desde:
        q = q.filter(MovimientoBancario.fecha >= datetime.fromisoformat(desde))
    if hasta:
        q = q.filter(MovimientoBancario.fecha <= datetime.fromisoformat(hasta))
    movs = q.filter(MovimientoBancario.estado == "registrado").order_by(MovimientoBancario.fecha.desc()).all()
    return [_serializar_movimiento(m, db) for m in movs]


@router.post("/movimientos/", dependencies=[Depends(require_admin)])
def registrar_movimiento(datos: dict, db: Session = Depends(get_db),
                          x_usuario_rol: Optional[str] = Header(None)):
    tipo = datos.get("tipo")
    if tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido: {tipo}")
    if tipo == "ingreso_venta":
        raise HTTPException(status_code=400, detail="Los ingresos de venta son generados automáticamente")

    monto = float(datos.get("monto", 0) or 0)
    if monto <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor que cero")

    m = MovimientoBancario(
        tipo              = tipo,
        cuenta_origen_id  = datos.get("cuenta_origen_id"),
        cuenta_destino_id = datos.get("cuenta_destino_id"),
        monto             = monto,
        moneda            = datos.get("moneda", "USD"),
        tasa_cambio       = datos.get("tasa_cambio"),
        monto_convertido  = datos.get("monto_convertido"),
        referencia        = datos.get("referencia"),
        concepto          = datos.get("concepto", ""),
        beneficiario      = datos.get("beneficiario"),
        categoria         = datos.get("categoria") or CATEGORIAS_POR_TIPO.get(tipo, "financiero"),
        proveedor_id      = datos.get("proveedor_id"),
        orden_compra_id   = datos.get("orden_compra_id"),
        registrado_por    = datos.get("registrado_por", "admin"),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _serializar_movimiento(m, db)


@router.delete("/movimientos/{mov_id}", dependencies=[Depends(require_admin)])
def anular_movimiento(mov_id: int, db: Session = Depends(get_db)):
    m = db.query(MovimientoBancario).filter(MovimientoBancario.id == mov_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    m.estado = "anulado"
    db.commit()
    return {"mensaje": "Movimiento anulado"}


@router.get("/resumen/")
def resumen_bancario(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    sembrar_si_vacio(db)
    cuentas = db.query(CuentaBancaria).filter(CuentaBancaria.activa == True).order_by(CuentaBancaria.orden_display).all()
    total_usd = 0.0
    total_bs  = 0.0
    detalle   = []
    for c in cuentas:
        saldo = _saldo_cuenta(c.id, db)
        detalle.append({"id": c.id, "nombre": c.nombre, "banco": c.banco, "moneda": c.moneda, "saldo": saldo})
        if c.moneda == "USD":
            total_usd += saldo
        else:
            total_bs += saldo

    # Deuda a proveedores
    ordenes_recibidas = db.query(OrdenCompra).filter(
        OrdenCompra.estado.in_(["recibida_parcial", "cerrada"])
    ).all()
    pagos_todos = db.query(MovimientoBancario).filter(
        MovimientoBancario.tipo == "pago_proveedor",
        MovimientoBancario.estado == "registrado",
    ).all()
    pagado_a_proveedores = sum(
        float(m.monto_convertido or 0) if m.moneda == "Bs"
        else float(m.monto or 0)
        for m in pagos_todos
    )
    total_compras = sum(float(o.total or 0) for o in ordenes_recibidas)
    deuda_proveedores = round(total_compras - pagado_a_proveedores, 2)

    return {
        "total_usd":        round(total_usd, 2),
        "total_bs":         round(total_bs,  2),
        "deuda_proveedores":deuda_proveedores,
        "cuentas":          detalle,
    }


# ---------------------------------------------------------------------------
# PROVEEDORES — DEUDA Y PAGOS
# ---------------------------------------------------------------------------

@router.get("/proveedores/deuda/", dependencies=[Depends(require_admin)])
def deuda_proveedores(db: Session = Depends(get_db)):
    proveedores = db.query(Proveedor).filter(Proveedor.activo == True).all()
    resultado = []
    for p in proveedores:
        ordenes = db.query(OrdenCompra).filter(
            OrdenCompra.proveedor_id == p.id,
            OrdenCompra.estado.in_(["recibida_parcial", "cerrada"]),
        ).all()
        total_comprado = sum(float(o.total or 0) for o in ordenes)
        if total_comprado == 0:
            continue
        pagos_prov = db.query(MovimientoBancario).filter(
            MovimientoBancario.proveedor_id == p.id,
            MovimientoBancario.tipo == "pago_proveedor",
            MovimientoBancario.estado == "registrado",
        ).all()
        pagado = sum(
            float(m.monto_convertido or 0) if m.moneda == "Bs"
            else float(m.monto or 0)
            for m in pagos_prov
        )
        saldo = round(total_comprado - float(pagado), 2)
        resultado.append({
            "proveedor_id":    p.id,
            "proveedor":       p.nombre,
            "total_comprado":  round(total_comprado, 2),
            "total_pagado":    round(float(pagado), 2),
            "saldo_pendiente": saldo,
        })
    return resultado


@router.post("/proveedores/{proveedor_id}/pago/", dependencies=[Depends(require_admin)])
def pagar_proveedor(proveedor_id: int, datos: dict, db: Session = Depends(get_db)):
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    monto = float(datos.get("monto", 0) or 0)
    if monto <= 0:
        raise HTTPException(status_code=400, detail="Monto inválido")

    tasa = float(datos.get("tasa_cambio", 0) or 0)
    moneda = datos.get("moneda", "USD")
    monto_convertido = round(monto / tasa, 2) if moneda == "Bs" and tasa > 0 else None

    m = MovimientoBancario(
        tipo              = "pago_proveedor",
        cuenta_origen_id  = datos.get("cuenta_id"),
        monto             = monto,
        moneda            = moneda,
        tasa_cambio       = tasa if tasa > 0 else None,
        monto_convertido  = monto_convertido,
        referencia        = datos.get("referencia"),
        concepto          = f"Pago a proveedor: {proveedor.nombre}",
        beneficiario      = proveedor.nombre,
        categoria         = "proveedores",
        proveedor_id      = proveedor_id,
        orden_compra_id   = datos.get("orden_compra_id"),
        registrado_por    = datos.get("registrado_por", "admin"),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return _serializar_movimiento(m, db)


@router.get("/proveedores/{proveedor_id}/estado/", dependencies=[Depends(require_admin)])
def estado_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    ordenes = db.query(OrdenCompra).filter(OrdenCompra.proveedor_id == proveedor_id).all()
    pagos   = db.query(MovimientoBancario).filter(
        MovimientoBancario.proveedor_id == proveedor_id,
        MovimientoBancario.tipo == "pago_proveedor",
        MovimientoBancario.estado == "registrado",
    ).order_by(MovimientoBancario.fecha.desc()).all()
    total_comprado = sum(float(o.total or 0) for o in ordenes if o.estado in ("recibida_parcial", "cerrada"))
    total_pagado   = sum(
        float(m.monto_convertido or 0) if m.moneda == "Bs"
        else float(m.monto or 0)
        for m in pagos
    )
    return {
        "proveedor":       p.nombre,
        "total_comprado":  round(total_comprado, 2),
        "total_pagado":    round(total_pagado,   2),
        "saldo_pendiente": round(total_comprado - total_pagado, 2),
        "ordenes": [{"id": o.id, "numero": o.numero, "estado": o.estado, "total": o.total} for o in ordenes],
        "pagos":   [_serializar_movimiento(m, db) for m in pagos],
    }


# ---------------------------------------------------------------------------
# REPORTE FINANCIERO MENSUAL
# ---------------------------------------------------------------------------

@router.get("/reporte/mensual/", dependencies=[Depends(require_admin)])
def reporte_mensual(mes: int, anio: int, db: Session = Depends(get_db)):
    from calendar import monthrange
    ultimo_dia = monthrange(anio, mes)[1]
    desde = datetime(anio, mes, 1)
    hasta = datetime(anio, mes, ultimo_dia, 23, 59, 59)

    movs = db.query(MovimientoBancario).filter(
        MovimientoBancario.fecha >= desde,
        MovimientoBancario.fecha <= hasta,
        MovimientoBancario.estado == "registrado",
    ).all()

    ingresos  = [m for m in movs if m.cuenta_destino_id and not m.cuenta_origen_id]
    salidas   = [m for m in movs if m.cuenta_origen_id]

    por_categoria = {}
    for m in movs:
        cat = m.categoria or "otros"
        if cat not in por_categoria:
            por_categoria[cat] = 0.0
        # ingresos suman, salidas restan para el neto
        if m.cuenta_destino_id and not m.cuenta_origen_id:
            por_categoria[cat] += float(m.monto or 0)
        else:
            por_categoria[cat] -= float(m.monto or 0)

    cierres_mes = db.query(CierreCaja).filter(
        CierreCaja.fecha >= desde,
        CierreCaja.fecha <= hasta,
    ).all()
    diferencias = []
    for c in cierres_mes:
        if c.estado_revision == "con_diferencias":
            diferencias.append({"cierre_id": c.id, "fecha": c.fecha.isoformat(), "usuario": c.usuario})

    return {
        "mes":                mes,
        "anio":               anio,
        "total_ingresos":     round(sum(float(m.monto or 0) for m in ingresos), 2),
        "total_salidas":      round(sum(float(m.monto or 0) for m in salidas),  2),
        "neto":               round(sum(float(m.monto or 0) for m in ingresos) - sum(float(m.monto or 0) for m in salidas), 2),
        "por_categoria":      {k: round(v, 2) for k, v in por_categoria.items()},
        "cierres_con_diferencias": diferencias,
        "total_movimientos":  len(movs),
    }
