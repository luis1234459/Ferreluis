"""
Recodificacion masiva de productos.codigo bajo la norma:
    2 letras de departamento + 2 letras de categoria + "-" + NNN correlativo
    (ej: Impermeabilizacion + Mantos -> IMMA-001, IMMA-002, ...)

Reglas de prefijo (confirmadas con Luis/Ken antes de escribir este script):
  - Departamento: 1ra letra de la 1ra palabra + 1ra letra de la 2da palabra
    "real" del nombre (se saltan conectores: y/de/en/para/o/del/la/los/las/el).
    Si el nombre tiene una sola palabra util, se usa la 2da letra de esa misma
    palabra (ej: Impermeabilizacion -> IM).
  - Categoria: primeras 2 letras del nombre de la categoria.
  - Colision de PREFIJO DE DEPARTAMENTO (dos deptos DISTINTOS reducen a las
    mismas 2 letras): el departamento con el producto de menor id entre los
    dos se queda con las 2 letras base; el otro cede su 2da letra, probando
    letras siguientes de la MISMA palabra que la origino hasta encontrar una
    libre (validado contra TODOS los prefijos de depto ya asignados, no solo
    contra el que colisiona).
  - Colision de PREFIJO DE 4 LETRAS (dos combinaciones (departamento,
    categoria) DISTINTAS, dentro del mismo depto, reducen al mismo prefijo de
    4 letras): el departamento nunca se toca; la combinacion con el producto
    de menor id se queda con la base; la otra cede la 2da letra de la parte
    de categoria, con la misma logica de "siguiente letra libre en la
    palabra", validado contra TODOS los prefijos de 4 letras ya asignados.
  - Si una palabra se agota sin encontrar una letra libre, NO se resuelve
    solo -> se marca como colision sin resolver en el reporte.

Casos borde:
  - Producto sin departamento_id: NO se toca su codigo. Va a la lista de
    "productos sin depto" (casos_borde.csv).
  - Producto con departamento pero sin categoria_id: prefijo = 2 letras de
    depto + "XX" (placeholder), + "-" + correlativo. Tambien se reporta en
    casos_borde.csv (es un caso valido pero fuera de la logica principal).

Uso:
    cd backend
    python recodificar_catalogo.py                # solo genera el preview (CSVs), no toca la DB
    python recodificar_catalogo.py --ejecutar      # aplica el UPDATE real (requiere aprobacion)

Por defecto SOLO genera preview. --ejecutar es el unico modo que escribe en
la base, y hace backup en backup_productos_codigos antes del UPDATE, todo en
una sola transaccion con rollback total si algo falla.
"""
import os
import sys
import csv
import argparse
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from database import SessionLocal
import sqlalchemy as sa

STOPWORDS = {'y', 'de', 'en', 'para', 'o', 'del', 'la', 'los', 'las', 'el'}

SALIDA_DIR = os.path.join(os.path.dirname(__file__), "recodificacion_preview")

# Departamento virtual para productos sin departamento_id real. Cambio de
# alcance confirmado: en vez de dejarlos sin tocar, entran a la recodificacion
# como si perteneciesen a este depto — Luis los migra a su depto real despues,
# uno a uno, y ahi cambian de codigo de nuevo (ya con su prefijo definitivo).
# El nombre es real texto, no un prefijo hardcodeado: el propio algoritmo de
# iniciales de palabra ("Sin" + "departamento") da SD.
SENTINEL_SIN_DEPTO = -1
NOMBRE_SIN_DEPTO = "Sin departamento"


# ============================================================================
# Helpers de letras
# ============================================================================

def _letras(palabra: str) -> list[str]:
    return [c.upper() for c in palabra if c.isalpha()]


def _primera_palabra_real(palabras: list[str]) -> str | None:
    for p in palabras:
        if p.lower() not in STOPWORDS and _letras(p):
            return p
    return None


def _codigo_base_departamento(nombre: str) -> tuple[str, str]:
    """(prefijo_2_letras, palabra_que_dio_la_2da_letra, letras_consumidas_de_esa_palabra).
    letras_consumidas: 1 si la 2da letra vino de una palabra DISTINTA a la 1ra
    (el caso normal, 2+ palabras reales); 2 si ambas letras del prefijo salen
    de la MISMA palabra (nombre de una sola palabra util, se usa su propia
    2da letra)."""
    palabras = (nombre or "").split()
    if not palabras:
        return "??", "", 1
    primera = palabras[0]
    letras_primera = _letras(primera)
    l1 = letras_primera[0] if letras_primera else "?"

    segunda_palabra = _primera_palabra_real(palabras[1:])
    if segunda_palabra:
        l2 = _letras(segunda_palabra)[0]
        palabra_origen = segunda_palabra
        letras_consumidas = 1
    elif len(letras_primera) > 1:
        l2 = letras_primera[1]
        palabra_origen = primera
        letras_consumidas = 2
    else:
        l2 = "X"
        palabra_origen = primera
        letras_consumidas = 1
    return l1 + l2, palabra_origen, letras_consumidas


def _siguiente_letra_libre(prefijo_fijo: str, palabra_origen: str, letras_consumidas: int, existentes: set) -> tuple[str | None, str | None]:
    """Avanza por las letras de palabra_origen saltando las primeras
    `letras_consumidas` (ya usadas para construir el prefijo actual) buscando
    prefijo_fijo+letra que no este en `existentes`.

    letras_consumidas es la cantidad de letras iniciales de palabra_origen que
    ya estan "gastadas" en el prefijo base — 1 cuando la letra vino de una
    palabra DISTINTA (departamento con 2 palabras reales), 2 cuando ambas
    letras del prefijo de categoria salen de la MISMA palabra (categoria =
    siempre primeras 2 letras de su propio nombre)."""
    letras = _letras(palabra_origen)[letras_consumidas:]
    for l in letras:
        candidato = prefijo_fijo + l
        if candidato not in existentes:
            return candidato, l
    return None, None


# ============================================================================
# Paso 1: prefijo de 2 letras por departamento
# ============================================================================

def calcular_prefijos_departamento(departamentos: list[dict], min_id_por_depto: dict) -> tuple[dict, list]:
    base_por_depto = {}
    palabra_origen_por_depto = {}
    consumidas_por_depto = {}
    for d in departamentos:
        base, palabra_origen, consumidas = _codigo_base_departamento(d["nombre"])
        base_por_depto[d["id"]] = base
        palabra_origen_por_depto[d["id"]] = palabra_origen
        consumidas_por_depto[d["id"]] = consumidas

    grupos = defaultdict(list)
    for d in departamentos:
        grupos[base_por_depto[d["id"]]].append(d["id"])

    prefijo_final = {}
    existentes = set()
    colisiones = []

    # Pasada 1: grupos sin colision, para poblar `existentes` antes de resolver nada
    for base, ids in grupos.items():
        if len(ids) == 1:
            prefijo_final[ids[0]] = base
            existentes.add(base)

    # Pasada 2: colisiones reales
    for base, ids in grupos.items():
        if len(ids) == 1:
            continue
        ids_ordenados = sorted(ids, key=lambda did: (min_id_por_depto.get(did, float("inf")), did))
        ganador = ids_ordenados[0]
        prefijo_final[ganador] = base
        existentes.add(base)
        for perdedor in ids_ordenados[1:]:
            candidato, letra_nueva = _siguiente_letra_libre(
                base[0], palabra_origen_por_depto[perdedor], consumidas_por_depto[perdedor], existentes
            )
            if candidato is None:
                colisiones.append({
                    "tipo": "departamento_SIN_RESOLVER",
                    "depto_id": perdedor,
                    "base": base,
                })
                prefijo_final[perdedor] = base  # queda colisionando, requiere resolucion manual
                continue
            prefijo_final[perdedor] = candidato
            existentes.add(candidato)
            colisiones.append({
                "tipo": "departamento",
                "depto_ganador_id": ganador,
                "depto_perdedor_id": perdedor,
                "base": base,
                "nuevo_prefijo": candidato,
                "letra_usada": letra_nueva,
                "palabra_origen": palabra_origen_por_depto[perdedor],
            })

    return prefijo_final, colisiones


# ============================================================================
# Paso 2: prefijo de 4 letras por (departamento, categoria)
# ============================================================================

def calcular_prefijos_categoria(prefijo_depto: dict, categorias: list[dict], min_id_por_combo: dict) -> tuple[dict, list]:
    categorias_por_id = {c["id"]: c for c in categorias}

    base_por_combo = {}
    palabra_cat_por_combo = {}
    consumidas_por_combo = {}
    for (did, cid) in min_id_por_combo:
        depto_pref = prefijo_depto.get(did)
        cat = categorias_por_id.get(cid)
        if depto_pref is None or cat is None:
            continue
        letras_cat = _letras(cat["nombre"])
        if len(letras_cat) >= 2:
            cat2 = letras_cat[0] + letras_cat[1]
            consumidas = 2
        elif len(letras_cat) == 1:
            cat2 = letras_cat[0] + "X"
            consumidas = 1
        else:
            cat2 = "XX"
            consumidas = 0
        base_por_combo[(did, cid)] = depto_pref + cat2
        palabra_cat_por_combo[(did, cid)] = cat["nombre"]
        consumidas_por_combo[(did, cid)] = consumidas

    grupos = defaultdict(list)
    for combo, base in base_por_combo.items():
        grupos[base].append(combo)

    prefijo_final = {}
    existentes = set()
    colisiones = []

    # Pasada 1: sin colision
    for base, combos in grupos.items():
        if len(combos) == 1:
            prefijo_final[combos[0]] = base
            existentes.add(base)

    # Pasada 2: colisiones
    for base, combos in grupos.items():
        if len(combos) == 1:
            continue
        combos_ordenados = sorted(combos, key=lambda c: min_id_por_combo[c])
        ganador = combos_ordenados[0]
        prefijo_final[ganador] = base
        existentes.add(base)
        for perdedor in combos_ordenados[1:]:
            depto_pref = base[:2]
            candidato, letra_nueva = _siguiente_letra_libre(
                depto_pref + base[2], palabra_cat_por_combo[perdedor], consumidas_por_combo[perdedor], existentes
            )
            if candidato is None:
                colisiones.append({
                    "tipo": "categoria_SIN_RESOLVER",
                    "combo": perdedor,
                    "base": base,
                })
                prefijo_final[perdedor] = base
                continue
            prefijo_final[perdedor] = candidato
            existentes.add(candidato)
            colisiones.append({
                "tipo": "categoria",
                "combo_ganador": ganador,
                "combo_perdedor": perdedor,
                "base": base,
                "nuevo_prefijo": candidato,
                "letra_usada": letra_nueva,
            })

    return prefijo_final, colisiones


# ============================================================================
# Orquestacion: leer DB, calcular mapeo completo, generar codigos nuevos
# ============================================================================

def cargar_datos(db):
    departamentos = [dict(r._mapping) for r in db.execute(sa.text(
        "SELECT id, nombre FROM departamentos"
    )).fetchall()]
    categorias = [dict(r._mapping) for r in db.execute(sa.text(
        "SELECT id, nombre, departamento_id FROM categorias"
    )).fetchall()]
    productos = [dict(r._mapping) for r in db.execute(sa.text(
        "SELECT id, nombre, codigo, departamento_id, categoria_id, activo FROM productos ORDER BY id"
    )).fetchall()]
    return departamentos, categorias, productos


def _departamentos_con_virtual(departamentos):
    return departamentos + [{"id": SENTINEL_SIN_DEPTO, "nombre": NOMBRE_SIN_DEPTO}]


def calcular_mapeo_completo(departamentos, categorias, productos):
    departamentos_efectivo = _departamentos_con_virtual(departamentos)

    min_id_por_depto = {}
    min_id_por_combo = {}
    for p in productos:
        did = p["departamento_id"] if p["departamento_id"] is not None else SENTINEL_SIN_DEPTO
        cid = p["categoria_id"]
        if did not in min_id_por_depto or p["id"] < min_id_por_depto[did]:
            min_id_por_depto[did] = p["id"]
        if cid is not None and did != SENTINEL_SIN_DEPTO:
            key = (did, cid)
            if key not in min_id_por_combo or p["id"] < min_id_por_combo[key]:
                min_id_por_combo[key] = p["id"]

    prefijo_depto, colisiones_depto = calcular_prefijos_departamento(departamentos_efectivo, min_id_por_depto)
    prefijo_combo, colisiones_cat = calcular_prefijos_categoria(prefijo_depto, categorias, min_id_por_combo)

    return prefijo_depto, prefijo_combo, colisiones_depto, colisiones_cat


def asignar_codigos_nuevos(productos, prefijo_depto, prefijo_combo):
    """
    Devuelve:
      cambios: lista de dict {producto_id, nombre, codigo_viejo, codigo_nuevo, prefijo}
      sin_depto: productos cuyo departamento_id apunta a un depto INEXISTENTE
                 (no confundir con "sin departamento_id" — esos ahora entran
                 con el prefijo virtual SD, ver SENTINEL_SIN_DEPTO)
      sin_categoria: productos con depto (real o virtual SD) pero sin
                     categoria_id (usan placeholder XX)
    """
    contador_por_prefijo = defaultdict(int)
    cambios = []
    sin_depto = []
    sin_categoria = []

    for p in productos:
        did_real, cid = p["departamento_id"], p["categoria_id"]
        did = did_real if did_real is not None else SENTINEL_SIN_DEPTO

        if cid is not None and did != SENTINEL_SIN_DEPTO and (did, cid) in prefijo_combo:
            prefijo4 = prefijo_combo[(did, cid)]
        else:
            depto_pref = prefijo_depto.get(did)
            if depto_pref is None:
                sin_depto.append(p)  # departamento_id apunta a un depto inexistente
                continue
            prefijo4 = depto_pref + "XX"
            sin_categoria.append(p)

        contador_por_prefijo[prefijo4] += 1
        numero = contador_por_prefijo[prefijo4]
        codigo_nuevo = f"{prefijo4}-{numero:03d}"
        cambios.append({
            "producto_id": p["id"],
            "nombre": p["nombre"],
            "codigo_viejo": p["codigo"],
            "codigo_nuevo": codigo_nuevo,
            "prefijo": prefijo4,
        })

    return cambios, sin_depto, sin_categoria


# ============================================================================
# Reportes / preview
# ============================================================================

def ranking_ventas_90d(db) -> dict:
    """producto_id -> ingreso (cantidad * precio_unitario) en los ultimos 90 dias.
    Mismo criterio que departamentos-resumen (ingreso_90d), no unidades: un ranking
    por unidades queda dominado por insumos baratos de alto volumen (cable, nylon)
    en vez de los productos de mayor peso real en el negocio."""
    corte = datetime.now(timezone.utc).replace(tzinfo=None)
    desde = corte - timedelta(days=90)
    filas = db.execute(sa.text("""
        SELECT dv.producto_id AS producto_id, SUM(dv.cantidad * dv.precio_unitario) AS ingreso
        FROM detalle_ventas dv
        JOIN ventas v ON v.id = dv.venta_id
        WHERE v.fecha >= :desde AND v.fecha < :corte AND v.estado != 'anulada'
        GROUP BY dv.producto_id
    """), {"desde": desde, "corte": corte}).fetchall()
    return {r.producto_id: float(r.ingreso or 0) for r in filas}


def generar_preview(db):
    os.makedirs(SALIDA_DIR, exist_ok=True)
    departamentos, categorias, productos = cargar_datos(db)
    deptos_por_id = {d["id"]: d for d in _departamentos_con_virtual(departamentos)}
    cats_por_id = {c["id"]: c for c in categorias}

    prefijo_depto, prefijo_combo, colisiones_depto, colisiones_cat = calcular_mapeo_completo(
        departamentos, categorias, productos
    )
    cambios, sin_depto, sin_categoria = asignar_codigos_nuevos(productos, prefijo_depto, prefijo_combo)

    # ---- mapeo_prefijos.csv ----
    with open(os.path.join(SALIDA_DIR, "mapeo_prefijos.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["departamento", "categoria", "prefijo", "ganador_o_perdedor_en_colision", "letra_alternativa_usada"])

        ganadores_depto = {c["depto_ganador_id"] for c in colisiones_depto if c["tipo"] == "departamento"}
        perdedores_depto = {c["depto_perdedor_id"]: c for c in colisiones_depto if c["tipo"] == "departamento"}
        ganadores_combo = {c["combo_ganador"] for c in colisiones_cat if c["tipo"] == "categoria"}
        perdedores_combo = {c["combo_perdedor"]: c for c in colisiones_cat if c["tipo"] == "categoria"}

        for (did, cid), prefijo4 in sorted(prefijo_combo.items(), key=lambda kv: kv[1]):
            depto_nombre = deptos_por_id.get(did, {}).get("nombre", f"[depto {did}]")
            cat_nombre = cats_por_id.get(cid, {}).get("nombre", f"[cat {cid}]")
            estado = ""
            letra = ""
            if did in perdedores_depto:
                estado = "perdedor_depto"
                letra = perdedores_depto[did]["letra_usada"]
            elif did in ganadores_depto:
                estado = "ganador_depto"
            if (did, cid) in perdedores_combo:
                estado = (estado + "+perdedor_categoria").strip("+") if estado else "perdedor_categoria"
                letra = perdedores_combo[(did, cid)]["letra_usada"]
            elif (did, cid) in ganadores_combo:
                estado = (estado + "+ganador_categoria").strip("+") if estado else "ganador_categoria"
            w.writerow([depto_nombre.strip(), cat_nombre.strip(), prefijo4, estado, letra])

        # Departamentos sin ninguna categoria con productos (solo prefijo de 2 letras + XX)
        deptos_con_combo = {did for (did, _cid) in prefijo_combo}
        for did, prefijo2 in sorted(prefijo_depto.items(), key=lambda kv: kv[1]):
            if did not in deptos_con_combo:
                depto_nombre = deptos_por_id.get(did, {}).get("nombre", f"[depto {did}]")
                estado = "perdedor_depto" if did in perdedores_depto else ("ganador_depto" if did in ganadores_depto else "")
                letra = perdedores_depto[did]["letra_usada"] if did in perdedores_depto else ""
                w.writerow([depto_nombre.strip(), "(sin categoria)", prefijo2 + "XX", estado, letra])

    # ---- muestra_recodificacion.csv ----
    ventas = ranking_ventas_90d(db)
    cambios_por_id = {c["producto_id"]: c for c in cambios}

    top_ventas = sorted(ventas.items(), key=lambda kv: kv[1], reverse=True)[:10]
    ids_top = [pid for pid, _ in top_ventas if pid in cambios_por_id]

    # 10 aleatorios: uno por cada uno de los 10 departamentos con mas productos
    productos_por_depto = defaultdict(list)
    for p in productos:
        if p["departamento_id"] is not None:
            productos_por_depto[p["departamento_id"]].append(p["id"])
    top_10_deptos = sorted(productos_por_depto.items(), key=lambda kv: len(kv[1]), reverse=True)[:10]
    ids_muestra_depto = []
    for did, ids_prod in top_10_deptos:
        candidato = next((pid for pid in sorted(ids_prod) if pid in cambios_por_id), None)
        if candidato:
            ids_muestra_depto.append(candidato)

    ids_muestra = list(dict.fromkeys(ids_top + ids_muestra_depto))  # sin duplicados, preserva orden

    def _nombre_depto_display(did_real):
        did = did_real if did_real is not None else SENTINEL_SIN_DEPTO
        return deptos_por_id.get(did, {}).get("nombre", f"[depto {did}]").strip()

    productos_por_id = {p["id"]: p for p in productos}
    with open(os.path.join(SALIDA_DIR, "muestra_recodificacion.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["producto_id", "nombre", "departamento", "categoria", "codigo_viejo", "codigo_nuevo"])
        for pid in ids_muestra:
            p = productos_por_id[pid]
            c = cambios_por_id[pid]
            depto_nombre = _nombre_depto_display(p["departamento_id"])
            cat_nombre = cats_por_id.get(p["categoria_id"], {}).get("nombre", "").strip() if p["categoria_id"] else "(sin categoria)"
            w.writerow([pid, p["nombre"], depto_nombre, cat_nombre, c["codigo_viejo"] or "", c["codigo_nuevo"]])

    # ---- casos_borde.csv ----
    with open(os.path.join(SALIDA_DIR, "casos_borde.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["producto_id", "nombre", "caso", "comportamiento_propuesto"])
        for p in sin_depto:
            w.writerow([p["id"], p["nombre"], "departamento_id_inexistente", "codigo intacto, no se toca (FK huerfana)"])
        for p in sin_categoria:
            depto_nombre = _nombre_depto_display(p["departamento_id"])
            c = cambios_por_id.get(p["id"])
            propuesto = c["codigo_nuevo"] if c else "?"
            if p["departamento_id"] is None:
                caso = "sin_departamento_real (prefijo SD transitorio)"
                comportamiento = f"prefijo virtual SDXX -> {propuesto}; migrar a depto real despues"
            else:
                caso = f"con_depto_sin_categoria ({depto_nombre})"
                comportamiento = f"placeholder XX -> {propuesto}"
            w.writerow([p["id"], p["nombre"], caso, comportamiento])
        for col in colisiones_depto:
            if col["tipo"] == "departamento_SIN_RESOLVER":
                w.writerow(["-", f"[departamento {col['depto_id']}]", "colision_departamento_sin_resolver", "requiere decision manual"])
        for col in colisiones_cat:
            if col["tipo"] == "categoria_SIN_RESOLVER":
                w.writerow(["-", str(col["combo"]), "colision_categoria_sin_resolver", "requiere decision manual"])

    # ---- totales.txt ----
    total_cambian = len(cambios)
    total_iguales = sum(1 for c in cambios if c["codigo_viejo"] == c["codigo_nuevo"])
    total_cambian_de_verdad = total_cambian - total_iguales
    colisiones_resueltas = (
        sum(1 for c in colisiones_depto if c["tipo"] == "departamento")
        + sum(1 for c in colisiones_cat if c["tipo"] == "categoria")
    )
    colisiones_sin_resolver = (
        sum(1 for c in colisiones_depto if c["tipo"] == "departamento_SIN_RESOLVER")
        + sum(1 for c in colisiones_cat if c["tipo"] == "categoria_SIN_RESOLVER")
    )
    total_sin_depto_real = sum(1 for p in productos if p["departamento_id"] is None)
    with open(os.path.join(SALIDA_DIR, "totales.txt"), "w", encoding="utf-8") as f:
        f.write(f"Total productos en catalogo: {len(productos)}\n")
        f.write(f"Total procesados (reciben codigo nuevo): {total_cambian}\n")
        f.write(f"  - cambiarian de codigo: {total_cambian_de_verdad}\n")
        f.write(f"  - quedarian igual (codigo viejo == nuevo, coincidencia): {total_iguales}\n")
        f.write(f"  - de esos, sin departamento_id real (prefijo virtual SD, transitorio): {total_sin_depto_real}\n")
        f.write(f"Total con departamento_id apuntando a un depto inexistente (NO se tocan): {len(sin_depto)}\n")
        f.write(f"Total con placeholder de categoria XX (incluye los SD): {len(sin_categoria)}\n")
        f.write(f"Colisiones de prefijo resueltas automaticamente: {colisiones_resueltas}\n")
        f.write(f"  - de departamento: {sum(1 for c in colisiones_depto if c['tipo'] == 'departamento')}\n")
        f.write(f"  - de categoria: {sum(1 for c in colisiones_cat if c['tipo'] == 'categoria')}\n")
        f.write(f"Colisiones SIN resolver (requieren decision manual): {colisiones_sin_resolver}\n")

    return {
        "cambios": cambios,
        "sin_depto": sin_depto,
        "sin_categoria": sin_categoria,
        "colisiones_depto": colisiones_depto,
        "colisiones_cat": colisiones_cat,
    }


# ============================================================================
# Ejecucion real (solo con --ejecutar, requiere aprobacion explicita)
# ============================================================================

def ejecutar_update(db, cambios):
    """
    Tabla de backup persistente (NO temporal) — columnas exactas pedidas:
    producto_id, codigo_viejo, codigo_nuevo, fecha_recodificacion DEFAULT NOW().
    Todo en una sola transaccion (misma sesion, un solo commit al final;
    cualquier excepcion hace rollback total, nada queda a medias).
    Insert y update van en lote (executemany vía SQLAlchemy, una sola
    sentencia parametrizada con toda la lista) en vez de fila por fila, para
    no gastar miles de round-trips de red contra Railway.
    """
    try:
        db.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS backup_productos_codigos (
                producto_id INTEGER NOT NULL,
                codigo_viejo TEXT,
                codigo_nuevo TEXT,
                fecha_recodificacion TIMESTAMP DEFAULT NOW()
            )
        """))

        params = [{"producto_id": c["producto_id"], "codigo_viejo": c["codigo_viejo"], "codigo_nuevo": c["codigo_nuevo"]}
                  for c in cambios]

        db.execute(sa.text("""
            INSERT INTO backup_productos_codigos (producto_id, codigo_viejo, codigo_nuevo)
            VALUES (:producto_id, :codigo_viejo, :codigo_nuevo)
        """), params)

        db.execute(sa.text("UPDATE productos SET codigo = :codigo_nuevo WHERE id = :producto_id"), params)

        db.commit()
    except Exception:
        db.rollback()
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ejecutar", action="store_true", help="Aplica el UPDATE real. Sin esto, solo genera el preview.")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        resultado = generar_preview(db)
        print(f"Preview generado en {SALIDA_DIR}/")
        print(f"  - mapeo_prefijos.csv")
        print(f"  - muestra_recodificacion.csv")
        print(f"  - casos_borde.csv")
        print(f"  - totales.txt")

        if args.ejecutar:
            print("\n--ejecutar detectado: aplicando UPDATE masivo...")
            t0 = time.monotonic()
            ejecutar_update(db, resultado["cambios"])
            segundos = time.monotonic() - t0

            cambios = resultado["cambios"]
            total_sd = sum(1 for c in cambios if c["prefijo"].startswith("SD"))
            total_placeholder_xx = sum(1 for c in cambios if c["prefijo"].endswith("XX"))

            print("\n=== RESUMEN FINAL ===")
            print(f"Total actualizados: {len(cambios)}")
            print(f"Total con prefijo SD (sin departamento real, transitorio): {total_sd}")
            print(f"Total con placeholder XX de categoria (incluye los SD): {total_placeholder_xx}")
            print(f"Tiempo total de ejecucion: {segundos:.1f}s")
            print(f"Casos borde no procesados (departamento_id inexistente): {len(resultado['sin_depto'])}")
        else:
            print("\nSolo preview (sin --ejecutar). La base NO fue modificada.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
