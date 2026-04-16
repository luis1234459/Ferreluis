"""
Módulo de Clientes y Fidelidad.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import datetime
from typing import Optional

from database import get_db
from models import (
    Cliente, VentaCliente, NivelFidelidad, PremioFidelidad,
    Venta, PagoVenta, AbonoCredito
)
from rutas.usuarios import require_admin

router = APIRouter(prefix="/clientes", tags=["clientes"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stats_cliente(cliente_id: int, db: Session) -> dict:
    """Calcula total_compras y monto_acumulado_usd desde VentaCliente + Venta."""
    vinculos = db.query(VentaCliente).filter(VentaCliente.cliente_id == cliente_id).all()
    venta_ids = [v.venta_id for v in vinculos]

    if not venta_ids:
        return {"total_compras": 0, "monto_acumulado_usd": 0.0}

    ventas = db.query(Venta).filter(
        Venta.id.in_(venta_ids),
        Venta.estado == "pagado"
    ).all()

    monto_usd = 0.0
    for v in ventas:
        t = float(v.total or 0)
        if v.moneda_venta == "USD":
            monto_usd += t
        elif v.moneda_venta == "Bs":
            tasa = float(v.tasa_bcv or 1)
            monto_usd += round(t / tasa, 2) if tasa > 0 else 0

    return {
        "total_compras":      len(ventas),
        "monto_acumulado_usd": round(monto_usd, 2),
    }


def _calcular_nivel(total_compras: int, monto_usd: float, niveles: list) -> Optional[dict]:
    """Devuelve el nivel más alto que cumple ambas condiciones."""
    for nivel in sorted(niveles, key=lambda n: n.orden, reverse=True):
        if total_compras >= nivel.min_compras and monto_usd >= nivel.min_monto_usd:
            return {
                "id":     nivel.id,
                "nombre": nivel.nombre,
                "color":  nivel.color_badge,
                "beneficio": nivel.beneficio_descripcion,
            }
    return None


def _proximo_nivel(total_compras: int, monto_usd: float, niveles: list, nivel_actual_orden: int) -> Optional[dict]:
    """Devuelve info del próximo nivel y cuánto falta."""
    candidatos = [n for n in sorted(niveles, key=lambda x: x.orden)
                  if n.orden > nivel_actual_orden]
    if not candidatos:
        return None
    prox = candidatos[0]
    return {
        "nombre":        prox.nombre,
        "color":         prox.color_badge,
        "faltan_compras": max(0, prox.min_compras - total_compras),
        "faltan_monto":   round(max(0, prox.min_monto_usd - monto_usd), 2),
    }


def _serializar_cliente(c: Cliente, db: Session, niveles: list) -> dict:
    stats = _stats_cliente(c.id, db)
    nivel = _calcular_nivel(stats["total_compras"], stats["monto_acumulado_usd"], niveles)
    nivel_orden = nivel["id"] if nivel else 0
    # obtener orden real
    if nivel:
        n_obj = next((n for n in niveles if n.id == nivel["id"]), None)
        nivel_orden = n_obj.orden if n_obj else 0

    return {
        "id":               c.id,
        "nombre":           c.nombre,
        "telefono":         c.telefono,
        "email":            c.email,
        "direccion":        c.direccion,
        "tipo_cliente":     c.tipo_cliente,
        "rif_cedula":       c.rif_cedula,
        "fecha_registro":   c.fecha_registro.isoformat() if c.fecha_registro else None,
        "activo":           c.activo,
        "notas":            c.notas,
        "es_cliente_generico": c.es_cliente_generico,
        "codigo":           c.codigo,
        "tiene_credito":    bool(c.tiene_credito),
        "limite_credito":   float(c.limite_credito or 0),
        "saldo_credito":    round(float(c.saldo_credito or 0), 2),
        "total_compras":    stats["total_compras"],
        "monto_acumulado_usd": stats["monto_acumulado_usd"],
        "nivel_fidelidad":  nivel,
        "proximo_nivel":    _proximo_nivel(
            stats["total_compras"], stats["monto_acumulado_usd"],
            niveles, nivel_orden
        ),
    }


# ---------------------------------------------------------------------------
# Endpoints de clientes
# ---------------------------------------------------------------------------

@router.get("/buscar-rapido")
def buscar_rapido(q: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    """Autocomplete para el punto de venta. Excluye al cliente genérico."""
    like = f"%{q}%"
    clientes = db.query(Cliente).filter(
        Cliente.activo == True,
        Cliente.es_cliente_generico == False,
        or_(Cliente.nombre.ilike(like), Cliente.telefono.ilike(like))
    ).limit(8).all()

    niveles = db.query(NivelFidelidad).order_by(NivelFidelidad.orden).all()
    return [_serializar_cliente(c, db, niveles) for c in clientes]


@router.get("/consumidor-final")
def obtener_consumidor_final(db: Session = Depends(get_db)):
    """Retorna el cliente genérico 'Consumidor Final'."""
    c = db.query(Cliente).filter(Cliente.es_cliente_generico == True).first()
    if not c:
        raise HTTPException(
            status_code=404,
            detail="El cliente 'Consumidor Final' no existe. Reinicia el servidor para crearlo."
        )
    niveles = db.query(NivelFidelidad).order_by(NivelFidelidad.orden).all()
    return _serializar_cliente(c, db, niveles)


@router.get("/recientes")
def clientes_recientes(db: Session = Depends(get_db)):
    """Últimos 10 clientes únicos que realizaron una compra."""
    vinculos = (
        db.query(VentaCliente)
        .join(Venta, Venta.id == VentaCliente.venta_id)
        .order_by(Venta.fecha.desc())
        .limit(60)   # amplio para encontrar 10 únicos
        .all()
    )

    seen = set()
    cliente_ids = []
    for vc in vinculos:
        if vc.cliente_id not in seen:
            seen.add(vc.cliente_id)
            cliente_ids.append(vc.cliente_id)
            if len(cliente_ids) >= 10:
                break

    if not cliente_ids:
        return []

    clientes = db.query(Cliente).filter(
        Cliente.id.in_(cliente_ids),
        Cliente.activo == True,
        Cliente.es_cliente_generico == False,
    ).all()

    # Mantener el orden por recencia
    orden = {cid: i for i, cid in enumerate(cliente_ids)}
    clientes.sort(key=lambda c: orden.get(c.id, 999))

    niveles = db.query(NivelFidelidad).order_by(NivelFidelidad.orden).all()
    return [_serializar_cliente(c, db, niveles) for c in clientes]


@router.get("/fidelidad/niveles")
def listar_niveles(db: Session = Depends(get_db)):
    return db.query(NivelFidelidad).order_by(NivelFidelidad.orden).all()


@router.put("/fidelidad/niveles/{nivel_id}", dependencies=[Depends(require_admin)])
def editar_nivel(nivel_id: int, datos: dict, db: Session = Depends(get_db)):
    nivel = db.query(NivelFidelidad).filter(NivelFidelidad.id == nivel_id).first()
    if not nivel:
        raise HTTPException(status_code=404, detail="Nivel no encontrado")
    for campo in ["nombre", "min_compras", "min_monto_usd", "beneficio_descripcion", "color_badge", "orden"]:
        if campo in datos:
            setattr(nivel, campo, datos[campo])
    db.commit()
    db.refresh(nivel)
    return nivel


@router.get("/fidelidad/ranking")
def ranking_clientes(
    criterio: str = "monto",
    limite: int = 20,
    db: Session = Depends(get_db),
):
    # Excluir cliente genérico del ranking
    clientes = db.query(Cliente).filter(
        Cliente.activo == True,
        Cliente.es_cliente_generico == False,
    ).all()
    niveles  = db.query(NivelFidelidad).order_by(NivelFidelidad.orden).all()

    resultado = [_serializar_cliente(c, db, niveles) for c in clientes]

    if criterio == "monto":
        resultado.sort(key=lambda x: x["monto_acumulado_usd"], reverse=True)
    else:
        resultado.sort(key=lambda x: x["total_compras"], reverse=True)

    return resultado[:limite]


@router.get("/")
def listar_clientes(
    buscar: Optional[str] = None,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Cliente)
    if activo is not None:
        q = q.filter(Cliente.activo == activo)
    if buscar:
        like = f"%{buscar}%"
        q = q.filter(or_(Cliente.nombre.ilike(like), Cliente.telefono.ilike(like)))
    clientes = q.order_by(Cliente.fecha_registro.desc()).all()
    niveles  = db.query(NivelFidelidad).order_by(NivelFidelidad.orden).all()
    return [_serializar_cliente(c, db, niveles) for c in clientes]


@router.post("/")
def crear_cliente(datos: dict, db: Session = Depends(get_db)):
    if not datos.get("nombre") or not datos.get("telefono"):
        raise HTTPException(status_code=400, detail="nombre y telefono son requeridos")

    # Verificar teléfono duplicado
    existente = db.query(Cliente).filter(
        Cliente.telefono == datos["telefono"],
        Cliente.activo == True,
        Cliente.es_cliente_generico == False,
    ).first()
    if existente:
        return JSONResponse(
            status_code=409,
            content={
                "error": "telefono_duplicado",
                "mensaje": f"Ya existe un cliente con ese teléfono",
                "cliente_existente": {
                    "id":       existente.id,
                    "nombre":   existente.nombre,
                    "telefono": existente.telefono,
                },
            }
        )

    c = Cliente(
        nombre       = datos["nombre"],
        telefono     = datos["telefono"],
        email        = datos.get("email"),
        direccion    = datos.get("direccion"),
        tipo_cliente = datos.get("tipo_cliente", "natural"),
        rif_cedula   = datos.get("rif_cedula"),
        notas        = datos.get("notas"),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    if not c.codigo:
        c.codigo = f"CLI-{c.id:04d}"
        db.commit()
        db.refresh(c)
    niveles = db.query(NivelFidelidad).order_by(NivelFidelidad.orden).all()
    return _serializar_cliente(c, db, niveles)


@router.get("/{cliente_id}")
def obtener_cliente(cliente_id: int, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    niveles = db.query(NivelFidelidad).order_by(NivelFidelidad.orden).all()
    datos   = _serializar_cliente(c, db, niveles)

    # Historial de compras
    vinculos = db.query(VentaCliente).filter(VentaCliente.cliente_id == cliente_id).all()
    venta_ids = [v.venta_id for v in vinculos]
    ventas = db.query(Venta).filter(Venta.id.in_(venta_ids)).order_by(Venta.fecha.desc()).all() if venta_ids else []

    datos["historial"] = [
        {
            "id":     v.id,
            "fecha":  v.fecha.isoformat() if v.fecha else None,
            "total":  round(float(v.total or 0), 2),
            "moneda": v.moneda_venta,
            "estado": v.estado,
            "pagos":  [
                {
                    "metodo": p.metodo_pago,
                    "monto":  round(float(p.monto_original or 0), 2),
                    "moneda": p.moneda_pago,
                }
                for p in db.query(PagoVenta).filter(PagoVenta.venta_id == v.id).all()
            ],
        }
        for v in ventas
    ]

    # Premios
    premios = db.query(PremioFidelidad).filter(
        PremioFidelidad.cliente_id == cliente_id
    ).order_by(PremioFidelidad.fecha.desc()).all()
    datos["premios"] = [
        {
            "id":           p.id,
            "tipo":         p.tipo,
            "descripcion":  p.descripcion,
            "fecha":        p.fecha.isoformat() if p.fecha else None,
            "otorgado_por": p.otorgado_por,
            "observacion":  p.observacion,
        }
        for p in premios
    ]

    return datos


@router.put("/{cliente_id}")
def editar_cliente(cliente_id: int, datos: dict, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for campo in ["nombre", "telefono", "email", "direccion", "tipo_cliente",
                  "rif_cedula", "notas", "activo", "tiene_credito", "limite_credito"]:
        if campo in datos:
            setattr(c, campo, datos[campo])
    # Si se habilita crédito y saldo está en 0, inicializar con el límite
    if datos.get("tiene_credito") and float(c.saldo_credito or 0) == 0 and float(c.limite_credito or 0) > 0:
        c.saldo_credito = float(c.limite_credito)
    db.commit()
    niveles = db.query(NivelFidelidad).order_by(NivelFidelidad.orden).all()
    return _serializar_cliente(c, db, niveles)


@router.delete("/{cliente_id}")
def desactivar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    c.activo = False
    db.commit()
    return {"ok": True}


@router.get("/{cliente_id}/credito")
def obtener_credito(cliente_id: int, db: Session = Depends(get_db)):
    """Estado de cuenta de crédito del cliente."""
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    movimientos = (
        db.query(AbonoCredito)
        .filter(AbonoCredito.cliente_id == cliente_id)
        .order_by(AbonoCredito.fecha.desc())
        .limit(50)
        .all()
    )
    return {
        "tiene_credito":  bool(c.tiene_credito),
        "limite_credito": float(c.limite_credito or 0),
        "saldo_credito":  round(float(c.saldo_credito or 0), 2),
        "movimientos": [
            {
                "id":          m.id,
                "monto":       m.monto,
                "metodo_pago": m.metodo_pago,
                "fecha":       m.fecha.isoformat() if m.fecha else None,
                "observacion": m.observacion,
                "usuario":     m.usuario,
                "venta_id":    m.venta_id,
            }
            for m in movimientos
        ],
    }


@router.post("/{cliente_id}/abono", dependencies=[Depends(require_admin)])
def registrar_abono(cliente_id: int, datos: dict, db: Session = Depends(get_db)):
    """Registra un abono (pago) al crédito del cliente."""
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if not c.tiene_credito:
        raise HTTPException(status_code=400, detail="El cliente no tiene crédito habilitado")

    monto = float(datos.get("monto", 0) or 0)
    if monto <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor a cero")

    c.saldo_credito = round(float(c.saldo_credito or 0) + monto, 2)
    db.add(AbonoCredito(
        cliente_id  = cliente_id,
        monto       = monto,
        metodo_pago = datos.get("metodo_pago"),
        observacion = datos.get("observacion"),
        usuario     = datos.get("usuario"),
    ))
    db.commit()
    return {"ok": True, "saldo_credito": c.saldo_credito}


@router.post("/{cliente_id}/premios", dependencies=[Depends(require_admin)])
def registrar_premio(cliente_id: int, datos: dict, db: Session = Depends(get_db)):
    c = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    premio = PremioFidelidad(
        cliente_id   = cliente_id,
        tipo         = datos.get("tipo", "por_cantidad"),
        descripcion  = datos.get("descripcion", ""),
        otorgado_por = datos.get("otorgado_por", "admin"),
        observacion  = datos.get("observacion"),
    )
    db.add(premio)
    db.commit()
    return {"ok": True, "id": premio.id}
