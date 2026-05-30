import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import MensajeChuito
from rutas.usuarios import require_admin

router = APIRouter(tags=["chuito"])


@router.post("/mensaje")
def crear_mensaje(datos: dict, db: Session = Depends(get_db)):
    msg = MensajeChuito(
        tipo     = datos.get("tipo"),
        vendedor = datos.get("vendedor"),
        mensaje  = datos.get("mensaje"),
        detalle  = json.dumps(datos.get("detalle", {}), ensure_ascii=False),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
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
