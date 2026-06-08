"""
Tandas 2 y 3 — Reclasificar genéricos y corregir errores de mapeo.

TANDA 2 (genéricos): los códigos de familia que el proveedor reutiliza
(ROL, CUN de cindu) no son errores. Se marcan sus productos como
es_generico = True para que queden exentos del candado de código único.
Al volverse genéricos, se DESBLOQUEAN sus filas de catálogo (bloqueado = False).

TANDA 3 (errores de mapeo): un mismo código específico apunta a 2 productos
distintos. El dueño legítimo es el PRIMERO del par; al segundo se le quita
ese código (se borra su fila de catálogo para ese código+proveedor).

SEGURIDAD:
  - Por defecto DRY-RUN: solo lista lo que haría, NO toca nada.
  - Para aplicar de verdad: --ejecutar

Identificación robusta: NO se usan IDs hardcodeados (pueden variar). Se ubica
cada caso por (proveedor + código), y dentro del grupo se resuelve por nombre.

Ejecutar desde backend/ (apuntando a producción vía DATABASE_URL):
    python corregir_mapeos.py             # solo lista (seguro)
    python corregir_mapeos.py --ejecutar  # aplica los cambios
"""
import sys
from database import get_db
from models import CatalogoProveedor, Producto, Proveedor


def _norm(cod):
    return (cod or "").strip().upper()


# ── TANDA 2: familias genéricas ───────────────────────────────────────────────
#   (nombre_proveedor, codigo) cuyos productos pasan a genérico
GENERICOS = [
    ("cindu", "ROL"),
    ("cindu", "CUN"),
]

# ── TANDA 3: errores de mapeo ──────────────────────────────────────────────────
#   (nombre_proveedor, codigo, fragmento_del_DUEÑO_legitimo)
#   El dueño se queda con el código; a los demás del grupo se les quita.
MAPEOS = [
    ("Resinglas",                "LAYF90267", "mediano"),
    ("Litani",                   "52-CH35",   "amarillo"),
    ("Inversiones La Fuente",    "PW-710WP",  "12"),
    ("Inversiones La Fuente",    "PN202205",  "platead"),
]


def _buscar_proveedor(db, nombre_frag, codigo=None):
    """Encuentra proveedor por fragmento de nombre (case-insensitive).

    Si se pasa `codigo`, entre los proveedores que matchean el fragmento
    prioriza el que efectivamente tiene filas de catálogo con ese código —
    desambigua nombres de proveedor casi idénticos (p.ej. dos registros
    para el mismo proveedor con distinta puntuación/mayúsculas)."""
    nf = nombre_frag.strip().lower()
    candidatos = [p for p in db.query(Proveedor).all() if nf in (p.nombre or "").lower()]
    if not candidatos:
        return None
    if codigo is not None:
        cod_norm = _norm(codigo)
        for p in candidatos:
            filas = db.query(CatalogoProveedor).filter(
                CatalogoProveedor.proveedor_id == p.id
            ).all()
            if any(_norm(f.codigo_proveedor) == cod_norm for f in filas):
                return p
    return candidatos[0]


def main():
    ejecutar = "--ejecutar" in sys.argv
    db = next(get_db())
    try:
        productos = {p.id: p for p in db.query(Producto).all()}

        print("=" * 70)
        modo = "EJECUTAR (aplica)" if ejecutar else "DRY-RUN (solo lista, no toca nada)"
        print(f"TANDAS 2 y 3 — GENÉRICOS + ERRORES DE MAPEO   |   MODO: {modo}")
        print("=" * 70)

        acciones_generico = []   # productos a marcar genérico
        acciones_quitar   = []   # filas de catálogo a borrar (código mal asignado)

        # ── TANDA 2 ─────────────────────────────────────────────────────────────
        print("\n[TANDA 2] Familias genéricas — marcar es_generico = True")
        print("-" * 70)
        for prov_frag, cod in GENERICOS:
            prov = _buscar_proveedor(db, prov_frag, cod)
            if not prov:
                print(f"  ⚠ proveedor «{prov_frag}» no encontrado — se omite {cod}")
                continue
            filas = [f for f in db.query(CatalogoProveedor).filter(
                        CatalogoProveedor.proveedor_id == prov.id).all()
                     if _norm(f.codigo_proveedor) == _norm(cod)]
            pids = sorted({f.producto_id for f in filas if f.producto_id in productos})
            print(f"  {prov.nombre} | «{cod}» → {len(pids)} producto(s):")
            for pid in pids:
                p = productos[pid]
                ya = " (ya era genérico)" if p.es_generico else ""
                print(f"      #{pid} «{p.nombre}»{ya}")
                if not p.es_generico:
                    acciones_generico.append(pid)
            for f in filas:
                if f.bloqueado:
                    print(f"      → fila catálogo #{f.id} se DESBLOQUEA")

        # ── TANDA 3 ─────────────────────────────────────────────────────────────
        print("\n[TANDA 3] Errores de mapeo — el código queda en el dueño legítimo")
        print("-" * 70)
        for prov_frag, cod, fragmento_dueno in MAPEOS:
            prov = _buscar_proveedor(db, prov_frag, cod)
            if not prov:
                print(f"  ⚠ proveedor «{prov_frag}» no encontrado — se omite {cod}")
                continue
            filas = [f for f in db.query(CatalogoProveedor).filter(
                        CatalogoProveedor.proveedor_id == prov.id).all()
                     if _norm(f.codigo_proveedor) == _norm(cod)]
            print(f"  {prov.nombre} | «{cod}»:")
            dueno_pid = None
            for f in filas:
                p = productos.get(f.producto_id)
                nombre = p.nombre if p else f"(producto {f.producto_id} inexistente)"
                if p and fragmento_dueno.lower() in (p.nombre or "").lower():
                    dueno_pid = f.producto_id
                    print(f"      ✓ DUEÑO: #{f.producto_id} «{nombre}» — conserva el código")
            if dueno_pid is None:
                print(f"      ⚠ no se identificó dueño con fragmento «{fragmento_dueno}» — NADA se toca aquí")
                continue
            for f in filas:
                if f.producto_id != dueno_pid:
                    p = productos.get(f.producto_id)
                    nombre = p.nombre if p else f"(producto {f.producto_id})"
                    print(f"      ✗ quita código: fila #{f.id} → #{f.producto_id} «{nombre}»")
                    acciones_quitar.append(f)

        # ── Resumen ──────────────────────────────────────────────────────────────
        print("\n" + "=" * 70)
        print(f"Productos a marcar genérico: {len(acciones_generico)}")
        print(f"Filas de catálogo a borrar (código mal asignado): {len(acciones_quitar)}")
        print("=" * 70)

        if not ejecutar:
            print("DRY-RUN: no se aplicó nada.")
            print("Para aplicar: python corregir_mapeos.py --ejecutar")
            return

        # ── Aplicar ────────────────────────────────────────────────────────────
        for pid in acciones_generico:
            p = productos[pid]
            p.es_generico = True
        # desbloquear filas de los códigos genéricos
        for prov_frag, cod in GENERICOS:
            prov = _buscar_proveedor(db, prov_frag, cod)
            if not prov:
                continue
            for f in db.query(CatalogoProveedor).filter(
                        CatalogoProveedor.proveedor_id == prov.id).all():
                if _norm(f.codigo_proveedor) == _norm(cod):
                    f.bloqueado = False
        for f in acciones_quitar:
            db.delete(f)
        db.commit()
        print(f"✓ APLICADO: {len(acciones_generico)} productos marcados genéricos, "
              f"{len(acciones_quitar)} filas de código corregidas.")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()
