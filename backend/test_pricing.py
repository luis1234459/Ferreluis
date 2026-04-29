"""
Tests del motor de pricing — se ejecutan sin DB.
    pytest backend/test_pricing.py
"""
import pytest
from pricing import (
    calcular_precios,
    resolver_policy,
    POLICY_MARKET_FACTOR,
    POLICY_BCV_DIRECT,
)

# ── Fixtures de tasas ─────────────────────────────────────────────────────────

BCV      = 50.0
BINANCE  = 55.0
FACTOR   = round(BINANCE / BCV, 6)   # 1.1


# ── calcular_precios ──────────────────────────────────────────────────────────

class TestMarketFactor:
    def test_precio_base(self):
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE)
        assert r["precio_base_usd"] == 13.0

    def test_precio_referencial_aplica_factor(self):
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE)
        assert r["precio_referencial_usd"] == round(13.0 * FACTOR, 4)

    def test_precio_bs_usa_binance(self):
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE)
        assert r["precio_bs"] == round(13.0 * BINANCE, 2)

    def test_factor_retornado(self):
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE)
        assert r["factor"] == FACTOR

    def test_policy_retornada(self):
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE)
        assert r["pricing_policy"] == POLICY_MARKET_FACTOR

    def test_margen_cero(self):
        r = calcular_precios(costo_usd=10, margen=0.0, tasa_bcv=BCV, tasa_binance=BINANCE)
        assert r["precio_base_usd"] == 10.0
        assert r["precio_referencial_usd"] == round(10.0 * FACTOR, 4)


class TestBcvDirect:
    def test_precio_referencial_igual_base(self):
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE,
                              policy=POLICY_BCV_DIRECT)
        assert r["precio_referencial_usd"] == r["precio_base_usd"]

    def test_precio_bs_usa_bcv_no_binance(self):
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE,
                              policy=POLICY_BCV_DIRECT)
        assert r["precio_bs"] == round(13.0 * BCV, 2)
        # Confirmar que NO usa binance
        assert r["precio_bs"] != round(13.0 * BINANCE, 2)

    def test_policy_retornada(self):
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE,
                              policy=POLICY_BCV_DIRECT)
        assert r["pricing_policy"] == POLICY_BCV_DIRECT

    def test_ajuste_divisa_pct(self):
        # ajuste_divisa_pct=0.03 → precio_divisa = precio_base * 1.03
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE,
                              policy=POLICY_BCV_DIRECT, ajuste_divisa_pct=0.03)
        assert r["precio_divisa_usd"] == round(13.0 * 1.03, 4)

    def test_ajuste_divisa_cero_equals_base(self):
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE,
                              policy=POLICY_BCV_DIRECT, ajuste_divisa_pct=0.0)
        assert r["precio_divisa_usd"] == r["precio_base_usd"]


class TestEdgeCases:
    def test_tasa_bcv_cero_no_divide(self):
        r = calcular_precios(costo_usd=10, margen=0.30, tasa_bcv=0, tasa_binance=BINANCE)
        assert r["factor"] == 1.0  # no divide por cero
        assert r["precio_base_usd"] == 13.0

    def test_costo_cero(self):
        r = calcular_precios(costo_usd=0, margen=0.30, tasa_bcv=BCV, tasa_binance=BINANCE)
        assert r["precio_base_usd"] == 0.0
        assert r["precio_referencial_usd"] == 0.0
        assert r["precio_bs"] == 0.0


# ── resolver_policy ───────────────────────────────────────────────────────────

class TestResolverPolicy:
    PROV_MAP = {
        1: (POLICY_BCV_DIRECT,    0.03),   # Sindú: BCV_DIRECT + 3% divisa
        2: (POLICY_MARKET_FACTOR, 0.0),
    }

    def test_override_producto_gana(self):
        # Proveedor 1 = BCV_DIRECT, pero producto override = MARKET_FACTOR
        policy, ajuste = resolver_policy(
            pricing_policy_override=POLICY_MARKET_FACTOR,
            proveedor_id=1,
            prov_policy_map=self.PROV_MAP,
        )
        assert policy == POLICY_MARKET_FACTOR
        assert ajuste == 0.0  # override no hereda ajuste del proveedor

    def test_hereda_policy_proveedor(self):
        policy, ajuste = resolver_policy(
            pricing_policy_override=None,
            proveedor_id=1,
            prov_policy_map=self.PROV_MAP,
        )
        assert policy  == POLICY_BCV_DIRECT
        assert ajuste  == 0.03

    def test_fallback_market_factor_sin_proveedor(self):
        policy, ajuste = resolver_policy(
            pricing_policy_override=None,
            proveedor_id=None,
            prov_policy_map=self.PROV_MAP,
        )
        assert policy == POLICY_MARKET_FACTOR
        assert ajuste == 0.0

    def test_fallback_market_factor_proveedor_no_en_mapa(self):
        policy, ajuste = resolver_policy(
            pricing_policy_override=None,
            proveedor_id=999,  # no existe
            prov_policy_map=self.PROV_MAP,
        )
        assert policy == POLICY_MARKET_FACTOR

    def test_override_invalido_cae_a_proveedor(self):
        # override desconocido → ignora, usa proveedor
        policy, ajuste = resolver_policy(
            pricing_policy_override="INVENTADO",
            proveedor_id=1,
            prov_policy_map=self.PROV_MAP,
        )
        assert policy == POLICY_BCV_DIRECT

    def test_mapa_vacio_fallback(self):
        policy, ajuste = resolver_policy(
            pricing_policy_override=None,
            proveedor_id=1,
            prov_policy_map={},
        )
        assert policy == POLICY_MARKET_FACTOR


# ── Integración: carrito sin regresiones ─────────────────────────────────────

class TestCarritoIntegracion:
    """
    Simula la lógica que Ventas.vue usará al agregar al carrito:
    precio_unitario = precio_referencial_usd (pre-computado por backend).
    Verifica que MARKET_FACTOR y BCV_DIRECT producen valores distintos
    y que el cambio de policy solo afecta ref/bs, no el precio_base.
    """

    def _precio_carrito(self, policy, tipo="ref"):
        r = calcular_precios(
            costo_usd=20, margen=0.25,
            tasa_bcv=BCV, tasa_binance=BINANCE,
            policy=policy,
        )
        return r["precio_referencial_usd"] if tipo == "ref" else r["precio_bs"]

    def test_precio_base_igual_en_ambos_modos(self):
        mf = calcular_precios(20, 0.25, BCV, BINANCE, POLICY_MARKET_FACTOR)
        bd = calcular_precios(20, 0.25, BCV, BINANCE, POLICY_BCV_DIRECT)
        assert mf["precio_base_usd"] == bd["precio_base_usd"]

    def test_precio_ref_difiere_entre_modos(self):
        assert self._precio_carrito(POLICY_MARKET_FACTOR) != self._precio_carrito(POLICY_BCV_DIRECT)

    def test_bcv_direct_ref_menor_que_market_cuando_binance_mayor_bcv(self):
        # Si binance > BCV, factor > 1 → MARKET_FACTOR da ref más alto
        ref_mf = self._precio_carrito(POLICY_MARKET_FACTOR)
        ref_bd = self._precio_carrito(POLICY_BCV_DIRECT)
        assert ref_bd < ref_mf   # BCV_DIRECT no aplica el spread

    def test_precio_bs_bcv_direct_usa_tasa_bcv(self):
        base = round(20 * 1.25, 4)   # 25.0
        bs   = self._precio_carrito(POLICY_BCV_DIRECT, tipo="bs")
        assert bs == round(base * BCV, 2)
