from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Usuario, Sede
from rutas.usuarios import get_current_user, security

router = APIRouter(prefix="/auth", tags=["auth"])


def _sede_dict(s: Sede) -> dict:
    return {
        "id":        s.id,
        "codigo":    s.codigo,
        "nombre":    s.nombre,
        "ciudad":    s.ciudad,
        "activa":    s.activa,
    }


def _usuario_o_401(db: Session, current_user: dict) -> Usuario:
    usuario = db.query(Usuario).filter(Usuario.id == current_user.get("id")).first()
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return usuario


def resolver_sede_activa(
    x_sede_id: Optional[str] = Header(None, alias="X-Sede-Id"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """
    Resuelve la sede en la que debe operar el request actual.

    - Sin header X-Sede-Id            -> sede "home" del usuario (usuarios.sede_id).
    - Header == sede propia           -> se permite siempre.
    - Header == "todas"               -> vista agregada (None); requiere admin o
                                          puede_alternar_sedes=True.
    - Header != sede propia (id)      -> requiere rol admin o puede_alternar_sedes=True,
                                          y que la sede exista y este activa.
    """
    usuario = _usuario_o_401(db, current_user)
    sede_propia = usuario.sede_id or 1
    puede_alternar = usuario.rol == "admin" or bool(usuario.puede_alternar_sedes)

    if not x_sede_id:
        return sede_propia

    if x_sede_id.strip().lower() == "todas":
        if not puede_alternar:
            raise HTTPException(status_code=403, detail="No tiene permiso para ver todas las sedes")
        return None

    try:
        sede_solicitada = int(x_sede_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Header X-Sede-Id inválido")

    if sede_solicitada == sede_propia:
        return sede_propia

    if not puede_alternar:
        raise HTTPException(status_code=403, detail="No tiene permiso para operar en otra sede")

    sede = db.query(Sede).filter(Sede.id == sede_solicitada).first()
    if not sede:
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    if not sede.activa:
        raise HTTPException(status_code=400, detail="La sede solicitada está inactiva")

    return sede_solicitada


def resolver_sede_activa_opcional(
    x_sede_id: Optional[str] = Header(None, alias="X-Sede-Id"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_usuario_rol: Optional[str] = Header(None),
    x_usuario_id: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """
    Igual que resolver_sede_activa(), pero no exige sesion: sin usuario
    autenticado -> None (vista agregada, sin filtrar por sede). Pensado para
    endpoints de lectura que hoy son publicos (listar_productos) — no romper
    el acceso anonimo mientras se activa el filtrado por sede para quien si
    esta logueado.
    """
    try:
        current_user = get_current_user(credentials, x_usuario_rol, x_usuario_id)
    except HTTPException:
        return None
    return resolver_sede_activa(x_sede_id=x_sede_id, current_user=current_user, db=db)


@router.get("/contexto-sede")
def contexto_sede(
    sede_activa_id: int = Depends(resolver_sede_activa),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    usuario = _usuario_o_401(db, current_user)
    puede_alternar = usuario.rol == "admin" or bool(usuario.puede_alternar_sedes)

    if puede_alternar:
        sedes_disponibles = db.query(Sede).filter(Sede.activa == True).order_by(Sede.id).all()
    else:
        sedes_disponibles = db.query(Sede).filter(Sede.id == usuario.sede_id).all()

    return {
        "usuario_id":            usuario.id,
        "rol":                   usuario.rol,
        "sede_id":                usuario.sede_id,
        "sede_activa":           sede_activa_id,
        "puede_alternar_sedes":  puede_alternar,
        "sedes_disponibles":     [_sede_dict(s) for s in sedes_disponibles],
    }


@router.put("/cambiar-sede/{sede_id}")
def cambiar_sede(
    sede_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    usuario = _usuario_o_401(db, current_user)
    puede_alternar = usuario.rol == "admin" or bool(usuario.puede_alternar_sedes)
    if not puede_alternar:
        raise HTTPException(status_code=403, detail="No tiene permiso para alternar de sede")

    sede = db.query(Sede).filter(Sede.id == sede_id).first()
    if not sede:
        raise HTTPException(status_code=404, detail="Sede no encontrada")
    if not sede.activa:
        raise HTTPException(status_code=400, detail="La sede solicitada está inactiva")

    return {
        "mensaje":  "Sede activa cambiada correctamente",
        "sede_id":  sede.id,
        "codigo":   sede.codigo,
        "nombre":   sede.nombre,
    }
