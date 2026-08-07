"""
Backfill de apartados.convertido_a_venta (feature: buscar y cerrar apartados
desde Ventas, con cobro del saldo — ver rutas/apartados.py).

Por que hace falta: el buscador nuevo (GET /apartados/buscar-rapido) ahora
tambien muestra apartados en estado="pagado" que NO se hayan convertido
todavia a Venta (100% abonados por /abono pero sin pasar por "Convertir a
venta"). Antes de este backfill, TODOS los apartados "pagado" -- incluyendo
los que ya se convirtieron hace tiempo con el boton viejo de /apartados --
tienen convertido_a_venta=False por default. Sin correr esto una vez antes
de desplegar el codigo nuevo, un apartado ya convertido podria reaparecer en
el buscador de Ventas y reconvertirse por error, duplicando la venta.

Que hace: marca convertido_a_venta=True en TODOS los apartados que estan en
estado="pagado" en este momento -- es la foto conservadora ("todo lo que ya
esta pagado hoy, se asume ya resuelto"). Efecto secundario aceptado: si
justo ahora existe algun apartado 100% abonado que en la realidad AUN no se
convirtio, este backfill lo deja igual de "atascado" que estaba antes de
que existiera este feature (antes tampoco tenia boton para convertirlo,
asi que no es una regresion). El script imprime esos casos para que se
revisen a mano si aparecen.

Uso (desde backend/, con DATABASE_URL ya exportado en el entorno si se
quiere apuntar a produccion -- este script NO carga .env, usa lo que ya
este en el entorno o sqlite local por default):
    python backfill_apartados_convertidos.py            # dry-run
    python backfill_apartados_convertidos.py --apply     # aplica de verdad
"""
import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(__file__))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from database import SessionLocal
from models import Apartado, Venta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Aplica de verdad (default: dry-run)")
    args = parser.parse_args()

    db = SessionLocal()
    url = str(db.get_bind().url)
    print(f"# Conectado a: {url.split('@')[-1] if '@' in url else url}")
    print(f"# Modo: {'APPLY' if args.apply else 'DRY-RUN (solo lectura, se hace rollback al final)'}\n")

    try:
        pagados = db.query(Apartado).filter(Apartado.estado == "pagado").all()
        print(f"Apartados en estado='pagado' encontrados: {len(pagados)}")

        ya_marcados = [a for a in pagados if a.convertido_a_venta]
        por_marcar  = [a for a in pagados if not a.convertido_a_venta]
        print(f"  ya tenian convertido_a_venta=True: {len(ya_marcados)}")
        print(f"  se van a marcar ahora:            {len(por_marcar)}")

        # Aviso informativo: de los que se van a marcar, cuales NO tienen
        # ninguna Venta con apartado_id apuntandolos -- son el caso ambiguo
        # (pudieron convertirse antes de que existiera ventas.apartado_id, o
        # genuinamente nunca se convirtieron). Se marcan igual (lado seguro:
        # evita venta duplicada), pero se listan para revision manual.
        sin_venta_vinculada = [
            a for a in por_marcar
            if not db.query(Venta.id).filter(Venta.apartado_id == a.id).first()
        ]
        if sin_venta_vinculada:
            print(f"\n⚠ {len(sin_venta_vinculada)} de esos NO tienen ninguna Venta vinculada "
                  f"(probablemente convertidos antes de este cambio, o nunca convertidos):")
            for a in sin_venta_vinculada[:30]:
                print(f"    {a.numero}  cliente={a.cliente_nombre!r}  total_usd={a.total_usd}  "
                      f"abonado_usd={a.abonado_usd}")
            if len(sin_venta_vinculada) > 30:
                print(f"    ... y {len(sin_venta_vinculada) - 30} mas")

        if not por_marcar:
            print("\nNada que hacer.")
            db.rollback()
            return

        for a in por_marcar:
            a.convertido_a_venta = True

        if not args.apply:
            print("\nDry-run OK. Rollback (no se escribió nada). Corré con --apply para aplicar de verdad.")
            db.rollback()
            return

        db.commit()
        print(f"\n✅ APPLY commiteado: {len(por_marcar)} apartado(s) marcados convertido_a_venta=True.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
