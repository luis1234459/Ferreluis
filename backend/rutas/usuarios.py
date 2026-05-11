from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario, Configuracion
from typing import Optional
from datetime import datetime, timedelta
import bcrypt
import json
from jose import jwt, JWTError

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

# ── JWT config ────────────────────────────────────────────────────────────────
SECRET_KEY = "ferreutil-secret-key-2024-cambiar-en-produccion"
ALGORITHM  = "HS256"
TOKEN_EXPIRE_HOURS = 12

security = HTTPBearer(auto_error=False)


def _crear_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _verificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_usuario_rol: Optional[str] = Header(None),
    x_usuario_id:  Optional[str] = Header(None),
) -> dict:
    """
    Acepta JWT (nuevo) o headers legacy (compatibilidad temporal).
    """
    if credentials and credentials.credentials:
        return _verificar_token(credentials.credentials)
    # Fallback legacy para compatibilidad
    if x_usuario_rol:
        return {"rol": x_usuario_rol, "id": int(x_usuario_id or 0), "nombre": ""}
    raise HTTPException(status_code=401, detail="No autenticado")


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_usuario_rol: Optional[str] = Header(None),
    x_usuario_id:  Optional[str] = Header(None),
) -> dict:
    user = get_current_user(credentials, x_usuario_rol, x_usuario_id)
    if user.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol admin.")
    return user


def require_admin_o_gestionador(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_usuario_rol: Optional[str] = Header(None),
    x_usuario_id:  Optional[str] = Header(None),
) -> dict:
    user = get_current_user(credentials, x_usuario_rol, x_usuario_id)
    if user.get("rol") not in ("admin", "gestionador"):
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol admin o gestionador.")
    return user


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _es_hasheada(p: str) -> bool:
    return p.startswith("$2b$") or p.startswith("$2a$")


def _parse_permisos(raw) -> Optional[list]:
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/")
def listar_usuarios(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    usuarios = db.query(Usuario).order_by(Usuario.id).all()
    return [
        {
            "id":       u.id,
            "nombre":   u.nombre,
            "email":    u.email,
            "rol":      u.rol,
            "activo":   u.activo if u.activo is not None else True,
            "permisos": _parse_permisos(u.permisos),
        }
        for u in usuarios
    ]


@router.post("/")
def crear_usuario(datos: dict, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    if not datos.get("nombre") or not datos.get("email") or not datos.get("password"):
        raise HTTPException(status_code=400, detail="Nombre, email y contraseña son obligatorios")
    if db.query(Usuario).filter(Usuario.email == datos["email"]).first():
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")

    permisos = datos.get("permisos")
    u = Usuario(
        nombre   = datos["nombre"],
        email    = datos["email"],
        password = hash_password(datos["password"]),
        rol      = datos.get("rol", "vendedor"),
        activo   = True,
        permisos = json.dumps(permisos) if isinstance(permisos, list) else None,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol, "activo": u.activo}


@router.put("/{usuario_id}")
def actualizar_usuario(
    usuario_id: int, datos: dict,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if "nombre"  in datos: u.nombre = datos["nombre"]
    if "email"   in datos: u.email  = datos["email"]
    if "rol"     in datos: u.rol    = datos["rol"]
    if "activo"  in datos: u.activo = bool(datos["activo"])
    if datos.get("password"):
        u.password = hash_password(datos["password"])

    permisos = datos.get("permisos")
    if "permisos" in datos:
        u.permisos = json.dumps(permisos) if isinstance(permisos, list) else None

    db.commit()
    db.refresh(u)
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "rol": u.rol, "activo": u.activo}


@router.patch("/{usuario_id}/activo")
def toggle_activo(
    usuario_id: int,
    datos: dict,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    u.activo = bool(datos.get("activo", True))
    db.commit()
    return {"id": u.id, "activo": u.activo}


@router.delete("/{usuario_id}")
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(u)
    db.commit()
    return {"mensaje": "Usuario eliminado"}


@router.post("/login")
def login(datos: dict, db: Session = Depends(get_db)):
    u = db.query(Usuario).filter(Usuario.email == datos.get("email", "")).first()
    if not u:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if u.activo is False:
        raise HTTPException(status_code=403, detail="Usuario desactivado")
    pw = datos.get("password", "")
    if _es_hasheada(u.password):
        if not verify_password(pw, u.password):
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    else:
        if pw != u.password:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        u.password = hash_password(pw)
        db.commit()

    permisos = _parse_permisos(u.permisos)
    token = _crear_token({
        "id":       u.id,
        "nombre":   u.nombre,
        "email":    u.email,
        "rol":      u.rol,
        "permisos": permisos,
    })

    return {
        "token":    token,
        "id":       u.id,
        "usuario":  u.nombre,
        "email":    u.email,
        "rol":      u.rol,
        "permisos": permisos,
        "mensaje":  "Login exitoso",
    }


@router.get("/me/permisos")
def mis_permisos(current_user: dict = Depends(get_current_user)):
    return {
        "id":       current_user.get("id"),
        "rol":      current_user.get("rol"),
        "permisos": current_user.get("permisos"),
    }


@router.post("/config/clave-autorizacion")
def set_clave_autorizacion(
    datos: dict,
    db: Session = Depends(get_db),
    _: dict = Depends(require_admin)
):
    config = db.query(Configuracion).first()
    if not config:
        config = Configuracion(clave_autorizacion=datos.get("clave", ""))
        db.add(config)
    else:
        config.clave_autorizacion = datos.get("clave", "")
    db.commit()
    return {"mensaje": "Clave actualizada"}
