from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Deposito
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/depositos", tags=["depositos"])

TIPOS_VALIDOS   = {"deposito", "transferencia", "retiro"}
MONEDAS_VALIDAS = {"USD", "Bs"}


class DepositoSchema(BaseModel):
    tipo:            str
    banco_origen:    Optional[str] = None
    banco_destino:   Optional[str] = None
    monto:           float
    moneda:          str
    referencia:      Optional[str] = None
    concepto:        Optional[str] = None
    usuario:         str
    comprobante_url: Optional[str] = None


def _serializar(d: Deposito) -> dict:
    return {
        "id":              d.id,
        "fecha":           d.fecha.isoformat() if d.fecha else None,
        "tipo":            d.tipo,
        "banco_origen":    d.banco_origen,
        "banco_destino":   d.banco_destino,
        "monto":           d.monto,
        "moneda":          d.moneda,
        "referencia":      d.referencia,
        "concepto":        d.concepto,
        "usuario":         d.usuario,
        "comprobante_url": d.comprobante_url,
    }


@router.get("/")
def listar_depositos(
    moneda:   Optional[str] = None,
    tipo:     Optional[str] = None,
    desde:    Optional[str] = None,
    hasta:    Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Deposito)
    if moneda:
        q = q.filter(Deposito.moneda == moneda)
    if tipo:
        q = q.filter(Deposito.tipo == tipo)
    if desde:
        q = q.filter(Deposito.fecha >= datetime.fromisoformat(desde))
    if hasta:
        q = q.filter(Deposito.fecha <= datetime.fromisoformat(hasta))
    depositos = q.order_by(Deposito.fecha.desc()).all()
    return [_serializar(d) for d in depositos]


@router.get("/resumen")
def resumen_depositos(db: Session = Depends(get_db)):
    todos = db.query(Deposito).all()
    total_usd = sum(d.monto for d in todos if d.moneda == "USD")
    total_bs  = sum(d.monto for d in todos if d.moneda == "Bs")
    return {
        "total_usd":   round(total_usd, 2),
        "total_bs":    round(total_bs,  2),
        "cantidad":    len(todos),
        "por_tipo": {
            "deposito":      sum(d.monto for d in todos if d.tipo == "deposito"  and d.moneda == "USD"),
            "transferencia": sum(d.monto for d in todos if d.tipo == "transferencia" and d.moneda == "USD"),
            "retiro":        sum(d.monto for d in todos if d.tipo == "retiro"    and d.moneda == "USD"),
        },
    }


@router.post("/")
def crear_deposito(datos: DepositoSchema, db: Session = Depends(get_db)):
    if datos.tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {TIPOS_VALIDOS}")
    if datos.moneda not in MONEDAS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"Moneda inválida. Use: {MONEDAS_VALIDAS}")
    if datos.monto <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor que cero")

    nuevo = Deposito(**datos.dict(), fecha=datetime.now())
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return _serializar(nuevo)


@router.put("/{deposito_id}")
def actualizar_deposito(
    deposito_id: int,
    datos: DepositoSchema,
    db: Session = Depends(get_db),
):
    d = db.query(Deposito).filter(Deposito.id == deposito_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Depósito no encontrado")
    for key, value in datos.dict().items():
        setattr(d, key, value)
    db.commit()
    db.refresh(d)
    return _serializar(d)


@router.delete("/{deposito_id}")
def eliminar_deposito(deposito_id: int, db: Session = Depends(get_db)):
    d = db.query(Deposito).filter(Deposito.id == deposito_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Depósito no encontrado")
    db.delete(d)
    db.commit()
    return {"mensaje": "Depósito eliminado"}
