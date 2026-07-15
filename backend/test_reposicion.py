"""
Tests del servicio de reposición — la función pura se ejecuta sin DB.
    pytest backend/test_reposicion.py
"""
from datetime import datetime, timedelta

from reposicion import calcular_reposicion


# ============================================================================
# Los 8 casos pedidos, contra la función pura calcular_reposicion
# ============================================================================

class TestStockContinuo:
    def test_stock_continuo_semaforo_verde(self):
        # venta_diaria=1, existencia=15, lead_time=7, colchon=3 -> umbral=10, cobertura=15 > 10
        r = calcular_reposicion(
            modo="stock_continuo", disponible=15, venta_diaria=1,
            lead_time_dias=7, colchon_dias=3,
        )
        assert r["dias_cobertura"] == 15
        assert r["estado_semaforo"] == "verde"

    def test_stock_continuo_semaforo_amarillo(self):
        # existencia=8 -> cobertura=8, entre piso_rojo(3) y umbral(10)
        r = calcular_reposicion(
            modo="stock_continuo", disponible=8, venta_diaria=1,
            lead_time_dias=7, colchon_dias=3,
        )
        assert r["estado_semaforo"] == "amarillo"

    def test_stock_continuo_semaforo_rojo(self):
        # existencia=2 -> cobertura=2, por debajo de piso_rojo(3)
        r = calcular_reposicion(
            modo="stock_continuo", disponible=2, venta_diaria=1,
            lead_time_dias=7, colchon_dias=3,
        )
        assert r["estado_semaforo"] == "rojo"


class TestPedidoBajoDemanda:
    def test_pedido_bajo_demanda_sin_orden_verde(self):
        # existencia=0, sin pedido abierto vencido -> no aplica alerta de stock
        r = calcular_reposicion(
            modo="pedido_bajo_demanda", disponible=0, venta_diaria=0.5,
            lead_time_dias=15, colchon_dias=3, pedido_vencido=False,
        )
        assert r["estado_semaforo"] == "verde"

    def test_pedido_bajo_demanda_con_pedido_vencido_rojo(self):
        r = calcular_reposicion(
            modo="pedido_bajo_demanda", disponible=0, venta_diaria=0.5,
            lead_time_dias=15, colchon_dias=3, pedido_vencido=True,
        )
        assert r["estado_semaforo"] == "rojo"
        assert r["causa_quiebre"] == "proveedor_sin_producto"


class TestStockEstrategicoDescuento:
    def test_stock_estrategico_descuento_alerta_bajo_umbral_aunque_haya_cobertura(self):
        # Novacapa: stock_min=150 (minimo de descuento), disponible=140 (por debajo),
        # pero venta_diaria bajo hace que la cobertura por rotacion sea enorme (1400 dias).
        # Un diseño ingenuo que solo mire dias_cobertura diria "verde" - eso es el bug a evitar.
        r = calcular_reposicion(
            modo="stock_estrategico_descuento", disponible=140, venta_diaria=0.1,
            lead_time_dias=7, colchon_dias=3, stock_min_objetivo=150,
        )
        assert r["dias_cobertura"] > 100          # cobertura por rotación sobrada
        assert r["estado_semaforo"] == "rojo"     # pero igual alerta por el umbral de descuento


class TestSinStockDeclarado:
    def test_sin_stock_todos_proveedores_pinta_gris(self):
        r = calcular_reposicion(
            modo="stock_continuo", disponible=0, venta_diaria=1,
            lead_time_dias=7, colchon_dias=3,
            sin_stock_todos=True, sin_stock_fecha="2026-06-01",
        )
        assert r["estado_semaforo"] == "gris"
        assert r["causa_quiebre"] == "proveedor_sin_producto"
        assert "gestión" in r["recomendacion_pedido"]["texto"] or "gestion" in r["recomendacion_pedido"]["texto"]

    def test_sin_stock_solo_principal_recomienda_alternativo(self):
        # 2 proveedores: principal sin stock, alternativo con stock. Existencia baja.
        # NO debe pintar gris (solo pinta gris si TODOS estan sin stock).
        r = calcular_reposicion(
            modo="stock_continuo", disponible=2, venta_diaria=1,
            lead_time_dias=7, colchon_dias=3,
            sin_stock_todos=False, sin_stock_principal=True,
            proveedor_principal_nombre="Proveedor A",
            proveedor_alternativo_nombre="Proveedor B",
        )
        assert r["estado_semaforo"] in ("amarillo", "rojo")
        assert r["estado_semaforo"] != "gris"
        assert r["recomendacion_pedido"]["proveedor_sugerido"] == "Proveedor B"
        assert "alternativo" in r["recomendacion_pedido"]["texto"]


class TestUnidadesExhibicion:
    def test_exhibicion_no_cuenta_como_disponible(self):
        # C17: la resta stock - exhibicion se hace ANTES de llegar a la función pura
        # (ver TestIntegracionFicha para el caso completo end-to-end vía DB).
        # Acá se valida que la función pura simplemente respeta el 'disponible' que recibe.
        existencia_total    = 5
        unidades_exhibicion = 2
        disponible          = existencia_total - unidades_exhibicion
        r = calcular_reposicion(
            modo="stock_continuo", disponible=disponible, venta_diaria=1,
            lead_time_dias=7, colchon_dias=3,
        )
        assert r["existencia_disponible"] == 3


# ============================================================================
# Fixtures ancla — productos reales del top 10, con datos plausibles
# ============================================================================

class TestFixturesAncla:
    def test_anchor_novacapa_mineral_350(self):
        # stock_estrategico_descuento, stock_min=150. Disponible 130, venta_diaria=2
        # (cobertura de rotación ~65 dias, holgada) - debe alertar igual por el umbral.
        r = calcular_reposicion(
            modo="stock_estrategico_descuento", disponible=130, venta_diaria=2,
            lead_time_dias=10, colchon_dias=3, stock_min_objetivo=150,
        )
        assert r["estado_semaforo"] == "rojo"

    def test_anchor_hidroneumatico_pedido_bajo_demanda(self):
        # Lead time largo (30d), sin stock guardado (se pide contra pedido),
        # sin orden abierta vencida todavia -> verde.
        r = calcular_reposicion(
            modo="pedido_bajo_demanda", disponible=0, venta_diaria=0.2,
            lead_time_dias=30, colchon_dias=5, pedido_vencido=False,
        )
        assert r["estado_semaforo"] == "verde"

    def test_anchor_bomba_leo_sin_stock_declarado(self):
        # Un solo proveedor, sin stock declarado, existencia en cero.
        r = calcular_reposicion(
            modo="stock_continuo", disponible=0, venta_diaria=0.3,
            lead_time_dias=15, colchon_dias=3,
            sin_stock_todos=True, sin_stock_fecha="2026-07-01",
            proveedor_principal_nombre="Proveedor Único",
        )
        assert r["estado_semaforo"] == "gris"
        assert r["causa_quiebre"] == "proveedor_sin_producto"


# ============================================================================
# Integración liviana: obtener_ficha_reposicion contra SQLite en memoria.
# Verifica el wiring real (queries, joins, resta stock-exhibicion) sin
# depender de Railway/Postgres.
# ============================================================================

class TestIntegracionFicha:
    def _db(self):
        # Motor propio y aislado — NO reusa el engine/Base singleton de
        # database.py, para no depender del orden de imports ni tocar el
        # ferreteria.db local real si ya fue importado antes en el proceso.
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        import models

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        models.Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        return Session()

    def test_producto_sin_ficha_reposicion(self):
        from reposicion import obtener_ficha_reposicion
        import models
        db = self._db()
        p = models.Producto(nombre="Sin ficha", codigo="SF-001", stock=10)
        db.add(p); db.commit(); db.refresh(p)

        resultado = obtener_ficha_reposicion(db, p.id)
        assert resultado["ficha_cargada"] is False
        db.close()

    def test_producto_inexistente_retorna_none(self):
        from reposicion import obtener_ficha_reposicion
        db = self._db()
        assert obtener_ficha_reposicion(db, 999999) is None
        db.close()

    def test_exhibicion_end_to_end_via_db(self):
        # C17 end-to-end: Producto.stock=5, unidades_exhibicion=2 -> disponible=3
        from reposicion import obtener_ficha_reposicion
        import models
        db = self._db()
        p = models.Producto(nombre="Con ficha", codigo="CF-001", stock=5)
        db.add(p); db.commit(); db.refresh(p)

        ficha = models.ProductoReposicion(
            producto_id=p.id, modo_reposicion="stock_continuo",
            stock_min_objetivo=2, stock_max_objetivo=20,
            unidades_exhibicion=2, colchon_dias=3,
        )
        db.add(ficha); db.commit()

        resultado = obtener_ficha_reposicion(db, p.id)
        assert resultado["ficha_cargada"] is True
        assert resultado["existencia_disponible"] == 3
        db.close()
