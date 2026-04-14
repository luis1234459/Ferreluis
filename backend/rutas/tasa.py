from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import TasaCambio
import httpx
from bs4 import BeautifulSoup

router = APIRouter(prefix="/tasa", tags=["tasa"])


@router.get("/")
def obtener_tasa(db: Session = Depends(get_db)):
    tasa = db.query(TasaCambio).order_by(TasaCambio.id.desc()).first()
    if not tasa:
        return {"tasa": 0, "tasa_binance": 0, "factor": 1, "fecha": None}
    bcv     = float(tasa.tasa or 0)
    binance = float(tasa.tasa_binance or bcv)   # si no hay binance, usar bcv
    factor  = round(binance / bcv, 6) if bcv > 0 else 1.0
    return {
        "tasa":         bcv,
        "tasa_binance": binance,
        "factor":       factor,
        "fecha":        tasa.fecha,
    }


@router.post("/actualizar-bcv")
def actualizar_desde_bcv(db: Session = Depends(get_db)):
    try:
        ultima = db.query(TasaCambio).order_by(TasaCambio.id.desc()).first()
        binance_actual = float(ultima.tasa_binance or 0) if ultima else 0

        headers  = {"User-Agent": "Mozilla/5.0"}
        response = httpx.get("https://www.bcv.org.ve/", headers=headers, timeout=10, verify=False)
        soup     = BeautifulSoup(response.text, "html.parser")
        dolar    = soup.find("div", {"id": "dolar"})
        if dolar:
            tasa_valor = float(dolar.find("strong").text.strip().replace(",", "."))
            nueva = TasaCambio(tasa=tasa_valor, tasa_binance=binance_actual or None)
            db.add(nueva)
            db.commit()
            return {"mensaje": "Tasa BCV actualizada", "tasa": tasa_valor}
        return {"error": "No se pudo extraer la tasa del BCV"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/actualizar-manual")
def actualizar_manual(datos: dict, db: Session = Depends(get_db)):
    tasa_bcv     = datos.get("tasa")
    tasa_binance = datos.get("tasa_binance")

    if not tasa_bcv:
        return {"error": "Debes enviar la tasa BCV"}

    # Conservar tasa_binance anterior si no se envía la nueva
    if not tasa_binance:
        ultima = db.query(TasaCambio).order_by(TasaCambio.id.desc()).first()
        tasa_binance = float(ultima.tasa_binance or 0) if ultima else None

    nueva = TasaCambio(
        tasa         = float(tasa_bcv),
        tasa_binance = float(tasa_binance) if tasa_binance else None,
    )
    db.add(nueva)
    db.commit()

    bcv     = float(nueva.tasa)
    binance = float(nueva.tasa_binance or bcv)
    return {
        "mensaje":      "Tasas actualizadas",
        "tasa":         bcv,
        "tasa_binance": binance,
        "factor":       round(binance / bcv, 6) if bcv > 0 else 1.0,
    }
