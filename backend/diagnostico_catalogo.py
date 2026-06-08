"""
Diagnóstico de catálogo proveedor↔producto — SOLO LECTURA.

Objetivo: antes de crear el índice único parcial sobre
(proveedor_id, codigo_proveedor) WHERE bloqueado = TRUE, detectar duplicados
y colisiones existentes que lo harían fallar o que son errores de mapeo.

NO modifica nada. Solo imprime un reporte.

Ejecutar desde la carpeta backend/:
    python diagnostico_catalogo.py

En Railway: abrir la shell del servicio backend y correr el mismo comando
(DATABASE_URL ya está en el entorno).
"""
from collections import defaultdict
from database import get_db
from models import CatalogoProveedor, Producto, Proveedor


def _norm(cod):
    """Normaliza el código para comparar: None/espacios → '' ; sin distinguir mayúsculas."""
    return (cod or "").strip().upper()


def main():
    db = next(get_db())
    try:
        filas = db.query(CatalogoProveedor).all()

        # Mapas auxiliares de nombres / genericidad
        prov_nombre = {
            p.id: (p.nombre or f"proveedor #{p.id}")
            for p in db.query(Proveedor).all()
        }
        productos = {p.id: p for p in db.query(Producto).all()}

        # Agrupar por (proveedor_id, codigo_normalizado)
        grupos = defaultdict(list)
        for f in filas:
            grupos[(f.proveedor_id, _norm(f.codigo_proveedor))].append(f)

        colisiones_especificas = []  # mismo (prov,cod) → varios productos, alguno NO genérico
        colisiones_genericas   = []  # mismo (prov,cod) → varios productos, todos genéricos
        duplicados_exactos     = []  # mismo (prov,cod,producto,variante) repetido
        codigos_vacios_bloq    = []  # filas bloqueadas con código vacío

        for (prov_id, cod), grupo in grupos.items():
            # Filas bloqueadas con código vacío → chocarían en el índice
            if cod == "":
                bloq_vacias = [f for f in grupo if f.bloqueado]
                if len(bloq_vacias) > 1:
                    codigos_vacios_bloq.append((prov_id, bloq_vacias))
                continue  # sin código no hay colisión de código que analizar

            # Duplicado exacto: misma combinación producto+variante repetida
            por_producto = defaultdict(list)
            for f in grupo:
                por_producto[(f.producto_id, f.variante_id)].append(f)
            for (pid, vid), repes in por_producto.items():
                if len(repes) > 1:
                    duplicados_exactos.append((prov_id, cod, pid, vid, repes))

            # Colisión: el mismo código apunta a productos DISTINTOS
            productos_distintos = {f.producto_id for f in grupo if f.producto_id}
            if len(productos_distintos) > 1:
                todos_genericos = all(
                    getattr(productos.get(pid), "es_generico", False)
                    for pid in productos_distintos
                )
                if todos_genericos:
                    colisiones_genericas.append((prov_id, cod, productos_distintos))
                else:
                    colisiones_especificas.append((prov_id, cod, productos_distintos))

        # ── Reporte ───────────────────────────────────────────────────────────
        print("=" * 70)
        print("DIAGNÓSTICO CATÁLOGO PROVEEDOR ↔ PRODUCTO (solo lectura)")
        print("=" * 70)
        print(f"Filas totales en catalogo_proveedor: {len(filas)}")
        print(f"Combinaciones (proveedor, código) únicas: {len(grupos)}")
        print()

        def _nombre_prod(pid):
            p = productos.get(pid)
            if not p:
                return f"producto #{pid} (NO EXISTE)"
            gen = " [GENÉRICO]" if getattr(p, "es_generico", False) else ""
            return f"#{pid} «{p.nombre}»{gen}"

        # 1. Colisiones específicas — ESTO HAY QUE RESOLVER
        print("-" * 70)
        print(f"[1] COLISIONES EN PRODUCTOS ESPECÍFICOS: {len(colisiones_especificas)}")
        print("    (un mismo código → varios productos, alguno NO genérico)")
        print("    >>> Estas bloquearían el índice único y son errores de mapeo.")
        print("-" * 70)
        for prov_id, cod, pids in colisiones_especificas:
            print(f"  Proveedor: {prov_nombre.get(prov_id, prov_id)}  |  Código: «{cod}»")
            for pid in sorted(pids):
                print(f"      → {_nombre_prod(pid)}")
            print()
        if not colisiones_especificas:
            print("  (ninguna — nada que resolver aquí)\n")

        # 2. Colisiones genéricas — OK, quedan exentas
        print("-" * 70)
        print(f"[2] COLISIONES EN PRODUCTOS GENÉRICOS: {len(colisiones_genericas)}")
        print("    (mismo código → varios productos, TODOS genéricos)")
        print("    >>> Inofensivas: los genéricos quedan exentos del candado.")
        print("-" * 70)
        for prov_id, cod, pids in colisiones_genericas:
            print(f"  Proveedor: {prov_nombre.get(prov_id, prov_id)}  |  Código: «{cod}»")
            for pid in sorted(pids):
                print(f"      → {_nombre_prod(pid)}")
            print()
        if not colisiones_genericas:
            print("  (ninguna)\n")

        # 3. Duplicados exactos
        print("-" * 70)
        print(f"[3] FILAS DUPLICADAS EXACTAS: {len(duplicados_exactos)}")
        print("    (misma combinación proveedor+código+producto+variante repetida)")
        print("-" * 70)
        for prov_id, cod, pid, vid, repes in duplicados_exactos:
            ids = ", ".join(str(f.id) for f in repes)
            vtxt = f" / variante {vid}" if vid else ""
            print(f"  Proveedor {prov_nombre.get(prov_id, prov_id)} | «{cod}» | "
                  f"{_nombre_prod(pid)}{vtxt} | filas: {ids}")
        if not duplicados_exactos:
            print("  (ninguna)\n")

        # 4. Códigos vacíos bloqueados
        print("-" * 70)
        print(f"[4] FILAS BLOQUEADAS CON CÓDIGO VACÍO: {len(codigos_vacios_bloq)} grupo(s)")
        print("    >>> Más de una fila bloqueada sin código en el mismo proveedor.")
        print("-" * 70)
        for prov_id, grupo in codigos_vacios_bloq:
            print(f"  Proveedor {prov_nombre.get(prov_id, prov_id)}:")
            for f in grupo:
                print(f"      fila #{f.id} → {_nombre_prod(f.producto_id)}")
        if not codigos_vacios_bloq:
            print("  (ninguna)\n")

        # ── Veredicto ─────────────────────────────────────────────────────────
        print("=" * 70)
        problemas = len(colisiones_especificas) + len(duplicados_exactos) + len(codigos_vacios_bloq)
        if problemas == 0:
            print("VEREDICTO: ✓ SEGURO crear el índice único. No hay conflictos reales.")
        else:
            print(f"VEREDICTO: ⚠ RESOLVER {problemas} conflicto(s) antes de crear el índice.")
            print("           Las colisiones genéricas [2] no cuentan: quedan exentas.")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()
