"""
Limpieza de proveedores duplicados/inactivos — registro historico.

EJECUTADO UNA SOLA VEZ contra produccion, el 2026-07-19. Este archivo NO se
vuelve a correr — a diferencia de recodificar_catalogo.py o rellenar_costos.py
(que son motores reusables con --ejecutar), este es puramente un registro de
lo que se hizo, para que quede documentado por que 26 proveedores
desaparecieron de la tabla y como se decidio cada caso. Ejecutar este archivo
solo imprime el resumen que sigue — no toca la base (ver main() al final).

============================================================================
LOGICA DE DEDUPLICACION APLICADA
============================================================================
Contexto: la tabla proveedores tenia decenas de filas duplicadas del mismo
proveedor real (ej. "COMERCIAL FERRE UTIL, C.A." en 7 variantes de nombre/id
distintas, "DISMEGA, C.A." en 3, etc.) — resultado de años de carga manual
sin normalizar. La fusion (POST /compras/proveedores/fusionar, ya existente)
reasigna todas las referencias reales de un duplicado a un canonico y lo
desactiva (activo=False), pero NUNCA borra la fila — es reversible por
diseno. Lo que hizo esta limpieza fue el paso siguiente y final: una vez
que un proveedor fusionado quedaba en cero en TODAS las tablas que pueden
referenciarlo, se lo borraba fisicamente.

Criterio de "en cero" verificado antes de borrar cada fila (las 6 tablas que
en algun momento pueden tener un proveedor_id, confirmado por inspeccion
directa del schema — ver mas abajo cual es la UNICA con FK real):
    - productos.proveedor_id            (campo legado, un proveedor "principal")
    - producto_proveedor.proveedor_id   (ficha de reposicion, N:N)
    - ordenes_compra.proveedor_id
    - catalogo_proveedor.proveedor_id
    - movimientos_bancarios.proveedor_id
    - devoluciones_proveedor.proveedor_id

Hallazgo de schema importante (verificado con information_schema antes de
borrar nada): de esas 6 tablas, la UNICA con foreign key real hacia
proveedores.id es producto_proveedor (ON DELETE RESTRICT). Las otras 5 NO
tienen constraint — un DELETE hubiera funcionado igual dejandolas huerfanas
SIN ningun error. Por eso la verificacion "en cero" se hizo a mano contra
las 6 tablas antes de cada borrado, en vez de confiar en que la base fuera
a rechazar un borrado inseguro.

============================================================================
CASO ESPECIAL: GEMPAR (id 40) -> GENPAR REPRESENTACIONES, C.A. (id 41)
============================================================================
GEMPAR (codigo GEM) tenia 4 referencias reales sin fusionar (1 producto —
MOTOBOMBA AGRICOLA AUTOCEBANTE 2x2" GASOLINA 7HP, id 4368 —, la orden de
compra OC-0052 cerrada, 1 fila de catalogo del mismo producto, y 2
movimientos bancarios de pago a proveedor por $380 y $355.12). No habia
ningun proveedor ACTIVO con nombre similar para fusionar — el candidato
obvio por nombre, GENPAR REPRESENTACIONES C.A. (id 41), tambien estaba
INACTIVO (ya en cero, migrado a su vez a otro lado en una fusion previa).

Decision (confirmada explicitamente por Luis): reactivar el 41 primero
(activo=True) y usarlo como destino, en vez de crear un tercer proveedor o
dejar a GEMPAR pendiente indefinidamente. Se reasignaron las 4 referencias
de 40 a 41, se confirmo que 40 quedaba en cero y 41 mostraba las 4
referencias con activo=True, y recien ahi se lo incluyo en el lote a
borrar junto con los otros 25.

Esta es la unica fusion+reactivacion manual de esta limpieza — todos los
demas casos ya estaban en cero de entrada (fusionados correctamente en
rondas anteriores de la sesion) y solo requirieron el DELETE final.

============================================================================
BACKUP Y BORRADO
============================================================================
Antes del DELETE se creo backup_proveedores_eliminados (persistente, no
temporal) con el snapshot completo de cada fila borrada:
    proveedor_id, nombre, codigo, rif, telefono, email, direccion,
    contacto, dias_credito, fecha_eliminacion (DEFAULT NOW())

Todo (backup + DELETE) en una sola transaccion, con un chequeo previo de
que la cantidad de filas encontradas coincidiera exactamente con la
cantidad de ids esperados antes de insertar/borrar nada (si no coincidia,
aborta sin tocar la base).

============================================================================
RESULTADO FINAL (2026-07-19)
============================================================================
26 proveedores borrados fisicamente, todos verificados en cero en las 6
tablas de referencia antes del borrado:
    1, 7, 9, 11, 14, 18, 22, 23, 24, 26, 29, 30, 32, 34, 36, 39, 40, 42,
    43, 44, 45, 48, 49, 50, 51, 52

Verificacion post-borrado (ejecutada contra produccion):
    - proveedores totales: 29 (todos activos)
    - proveedores inactivos restantes: 0
    - filas en backup_proveedores_eliminados: 26
    - huerfanos en productos/ordenes_compra/catalogo_proveedor/
      movimientos_bancarios (proveedor_id apuntando a un id ya borrado): 0

Para consultar el detalle de cualquier proveedor borrado:
    SELECT * FROM backup_proveedores_eliminados WHERE proveedor_id = <id>;
"""


def main():
    print(__doc__)
    print("\nEste script es un registro historico — no ejecuta ninguna accion.")
    print("La limpieza que documenta ya se aplico contra produccion el 2026-07-19.")


if __name__ == "__main__":
    main()
