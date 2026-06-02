import json
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import MensajeChuito
from rutas.usuarios import require_admin

router = APIRouter(tags=["chuito"])

TELEGRAM_TOKEN   = "8967651599:AAHzCZuH4czwo8YeRyToDoStYu_5SpmHI2M"
TELEGRAM_CHAT_ID = "725870794"

ICONOS = {
    "venta_perdida":  "🔴",
    "falta_producto": "📦",
    "logro":          "⭐",
    "mensaje_jefe":   "💬",
}
LABELS = {
    "venta_perdida":  "Venta perdida",
    "falta_producto": "Falta producto",
    "logro":          "Logro del día",
    "mensaje_jefe":   "Mensaje directo",
}


def enviar_telegram(texto: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        import httpx
        with httpx.Client(timeout=5) as client:
            client.post(url, json={
                "chat_id":    TELEGRAM_CHAT_ID,
                "text":       texto,
                "parse_mode": "HTML",
            })
    except Exception:
        pass


@router.post("/mensaje")
def crear_mensaje(datos: dict, db: Session = Depends(get_db)):
    tipo     = datos.get("tipo")
    vendedor = datos.get("vendedor")
    mensaje  = datos.get("mensaje")
    detalle  = datos.get("detalle", {})

    msg = MensajeChuito(
        tipo     = tipo,
        vendedor = vendedor,
        mensaje  = mensaje,
        detalle  = json.dumps(detalle, ensure_ascii=False),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    icono = ICONOS.get(tipo, "📋")
    label = LABELS.get(tipo, tipo or "")
    texto_tg = (
        f"{icono} <b>CHUITO — {label}</b>\n"
        f"👤 Vendedor: <b>{vendedor}</b>\n"
        f"💬 {mensaje}\n"
    )
    if detalle.get("producto"):
        texto_tg += f"📦 Producto: {detalle['producto']}\n"
    if detalle.get("precio_competencia"):
        texto_tg += f"💲 Precio competencia: {detalle['precio_competencia']}\n"
    if detalle.get("competidor"):
        texto_tg += f"🏪 Lugar: {detalle['competidor']}\n"
    if detalle.get("clientes"):
        texto_tg += f"👥 Clientes que lo pidieron: {detalle['clientes']}\n"
    texto_tg += f"\n⏰ {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC"

    enviar_telegram(texto_tg)

    return {"ok": True, "id": msg.id}


@router.get("/mensajes")
def listar_mensajes(db: Session = Depends(get_db), _: None = Depends(require_admin)):
    msgs = db.query(MensajeChuito).order_by(MensajeChuito.fecha.desc()).limit(50).all()
    return [
        {
            "id":          m.id,
            "tipo":        m.tipo,
            "vendedor":    m.vendedor,
            "mensaje":     m.mensaje,
            "detalle":     json.loads(m.detalle or "{}"),
            "fecha":       m.fecha.isoformat(),
            "leido_admin": m.leido_admin,
        }
        for m in msgs
    ]


@router.patch("/mensajes/{msg_id}/leer")
def marcar_leido(msg_id: int, db: Session = Depends(get_db), _: None = Depends(require_admin)):
    m = db.query(MensajeChuito).filter(MensajeChuito.id == msg_id).first()
    if m:
        m.leido_admin = True
        db.commit()
    return {"ok": True}
