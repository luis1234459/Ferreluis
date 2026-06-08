"""
Tanda 1 — Limpieza de filas fantasma en catalogo_proveedor.

Borra las filas de catalogo_proveedor cuyo producto_id ya NO existe en la
tabla productos (referencias a productos eliminados que quedaron huérfanas).

SEGURIDAD:
  - Por defecto corre en modo DRY-RUN: solo lista lo que borraría, NO toca nada.
  - Para borrar de verdad hay que pasar el flag --ejecutar.

Para cada fila huérfana muestra si existe un producto VIVO con el mismo código
en el mismo proveedor (el "reemplazo"), para confirmar que no perdemos el único
vínculo del producto real.

Ejecutar desde backend/ (apuntando a producción vía DATABASE_URL):
    python limpiar_fantasma.py            # solo lista (seguro)
    python limpiar_fantasma.py --ejecutar # borra de verdad
"""
import sys
from database import get_db
from models import CatalogoProveedor, Producto, Proveedor


# Proveedores a EXCLUIR del borrado (por fragmento de nombre, case-insensitive).
# Sus filas huérfanas NO se tocan — se dejan para revisión física manual.
# Caso cindu: usa códigos de familia / productos sin código → se revisa aparte.
PROVEEDORES_EXCLUIDOS = ["cindu"]


def _norm(cod):
    return (cod or "").strip().upper()


def main():
    ejecutar = "--ejecutar" in sys.argv
    db = next(get_db())
    try:
        ids_vivos = {p.id for p in db.query(Producto.id).all()}
        prov_nombre = {p.id: (p.nombre or f"proveedor #{p.id}")
                       for p in db.query(Proveedor).all()}

        # IDs de proveedores excluidos (por fragmento de nombre)
        excluidos_frag = [e.strip().lower() for e in PROVEEDORES_EXCLUIDOS]
        prov_excluidos = {
            pid for pid, nom in prov_nombre.items()
            if any(fr in (nom or "").lower() for fr in excluidos_frag)
        }

        # Índice de productos vivos por (proveedor, código) para detectar reemplazo
        vivos_por_codigo = {}
        for f in db.query(CatalogoProveedor).all():
            if f.producto_id in ids_vivos:
                vivos_por_codigo.setdefault(
                    (f.proveedor_id, _norm(f.codigo_proveedor)), []
                ).append(f.producto_id)

        filas = db.query(CatalogoProveedor).all()
        huerfanas_todas = [f for f in filas if f.producto_id and f.producto_id not in ids_vivos]
        # Excluir las de proveedores protegidos (cindu)
        huerfanas = [f for f in huerfanas_todas if f.proveedor_id not in prov_excluidos]
        protegidas = [f for f in huerfanas_todas if f.proveedor_id in prov_excluidos]

        print("=" * 70)
        modo = "EJECUTAR (borra)" if ejecutar else "DRY-RUN (solo lista, no borra)"
        print(f"TANDA 1 — LIMPIEZA DE FILAS FANTASMA   |   MODO: {modo}")
        print("=" * 70)
        print(f"Filas totales en catalogo_proveedor: {len(filas)}")
        print(f"Filas huérfanas totales (producto_id inexistente): {len(huerfanas_todas)}")
        print(f"  → protegidas (proveedores excluidos: {', '.join(PROVEEDORES_EXCLUIDOS)}): {len(protegidas)} (NO se tocan)")
        print(f"  → a borrar: {len(huerfanas)}")
        print()

        if not huerfanas:
            print("No hay filas huérfanas. Nada que borrar.")
            print("=" * 70)
            return

        con_reemplazo = 0
        sin_reemplazo = 0
        for f in sorted(huerfanas, key=lambda x: (x.proveedor_id or 0, _norm(x.codigo_proveedor))):
            cod = _norm(f.codigo_proveedor)
            vivos = [pid for pid in vivos_por_codigo.get((f.proveedor_id, cod), [])]
            if vivos:
                reemplazo = f"reemplazo vivo: producto(s) {', '.join(map(str, sorted(set(vivos))))}"
                con_reemplazo += 1
            else:
                reemplazo = "SIN reemplazo vivo con este código"
                sin_reemplazo += 1
            print(f"  fila #{f.id} | {prov_nombre.get(f.proveedor_id, f.proveedor_id)} | "
                  f"«{cod or '(vacío)'}» | producto_id muerto: {f.producto_id} | {reemplazo}")

        print()
        print(f"Con reemplazo vivo (seguras de borrar): {con_reemplazo}")
        print(f"Sin reemplazo vivo (el código quedará sin vínculo): {sin_reemplazo}")
        print()

        if not ejecutar:
            print("DRY-RUN: no se borró nada.")
            print("Para borrar de verdad: python limpiar_fantasma.py --ejecutar")
            print("=" * 70)
            return

        # ── Borrado real ──────────────────────────────────────────────────────
        for f in huerfanas:
            db.delete(f)
        db.commit()
        print(f"✓ BORRADAS {len(huerfanas)} filas huérfanas.")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()
