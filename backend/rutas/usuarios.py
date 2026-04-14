from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from models import Usuario, Configuracion
from pydantic import BaseModel
from typing import Optional, List
import bcrypt
import json as _json

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _es_hasheada(password: str) -> bool:
    return password.startswith("$2b$") or password.startswith("$2a$")


def require_admin(x_usuario_rol: Optional[str] = Header(None)):
    if x_usuario_rol != "admin":
        raise HTTPException(
            status_code=403,
            detail="Acceso denegado. Se requiere rol de administrador."
        )


def _parse_permisos(raw: Optional[str]) -> Optional[List[str]]:
    if raw is None:
        return None
    try:
        return _json.loads(raw)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UsuarioSchema(BaseModel):
    nombre:   str
    email:    str
    password: str
    rol:      str                       = "vendedor"
    permisos: Optional[List[str]]       = None


class UsuarioEditSchema(BaseModel):
    nombre:   str
    email:    str
    rol:      str
    permisos: Optional[List[str]]       = None
    password: Optional[str]             = None   # None = no cambiar


class LoginSchema(BaseModel):
    email:    str
    password: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/")
def listar_usuarios(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    usuarios = db.query(Usuario).all()
    return [
        {
            "id":       u.id,
            "nombre":   u.nombre,
            "email":    u.email,
            "rol":      u.rol,
            "permisos": _parse_permisos(u.permisos),
        }
        for u in usuarios
    ]


@router.post("/")
def crear_usuario(
    datos: UsuarioSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    existe = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if existe:
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    permisos_json = _json.dumps(datos.permisos) if datos.permisos is not None else None

    nuevo = Usuario(
        nombre   = datos.nombre,
        email    = datos.email,
        password = hash_password(datos.password),
        rol      = datos.rol,
        permisos = permisos_json,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {
        "mensaje":  "Usuario creado",
        "id":       nuevo.id,
        "permisos": _parse_permisos(nuevo.permisos),
    }


@router.put("/{usuario_id}")
def editar_usuario(
    usuario_id: int,
    datos: UsuarioEditSchema,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    u.nombre   = datos.nombre
    u.email    = datos.email
    u.rol      = datos.rol
    u.permisos = _json.dumps(datos.permisos) if datos.permisos is not None else None

    if datos.password:
        u.password = hash_password(datos.password)

    db.commit()
    db.refresh(u)
    return {
        "id":       u.id,
        "nombre":   u.nombre,
        "email":    u.email,
        "rol":      u.rol,
        "permisos": _parse_permisos(u.permisos),
    }


@router.delete("/{usuario_id}")
def eliminar_usuario(
    usuario_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.delete(u)
    db.commit()
    return {"mensaje": "Usuario eliminado"}


@router.post("/login")
def login(datos: LoginSchema, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == datos.email).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    # Migración automática: si la contraseña está en texto plano, hashearla
    if not _es_hasheada(usuario.password):
        if usuario.password != datos.password:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")
        usuario.password = hash_password(datos.password)
        db.commit()
    else:
        if not verify_password(datos.password, usuario.password):
            raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    return {
        "mensaje":  "Login exitoso",
        "usuario":  usuario.nombre,
        "rol":      usuario.rol,
        "id":       usuario.id,
        "permisos": _parse_permisos(usuario.permisos),
    }


@router.get("/me/permisos")
def mis_permisos(
    x_usuario_id: Optional[int] = Header(None),
    db: Session = Depends(get_db),
):
    if not x_usuario_id:
        raise HTTPException(status_code=400, detail="Header X-Usuario-Id requerido")
    u = db.query(Usuario).filter(Usuario.id == x_usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {
        "rol":      u.rol,
        "permisos": _parse_permisos(u.permisos),
    }


@router.post("/config/clave-autorizacion")
def actualizar_clave(
    datos: dict,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    clave = datos.get("clave")
    if not clave:
        raise HTTPException(status_code=400, detail="Debe enviar una clave")

    config = db.query(Configuracion).first()
    if not config:
        config = Configuracion(clave_autorizacion=clave)
        db.add(config)
    else:
        config.clave_autorizacion = clave

    db.commit()
    return {"mensaje": "Clave de autorización actualizada"}
