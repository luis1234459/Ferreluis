"""
Módulo de pricing puro — sin dependencias de DB ni FastAPI.
Importable desde tests sin efectos secundarios.
"""

POLICY_MARKET_FACTOR = "MARKET_FACTOR"
POLICY_BCV_DIRECT    = "BCV_DIRECT"
_VALID_POLICIES      = {POLICY_MARKET_FACTOR, POLICY_BCV_DIRECT}


def calcular_precios(
    costo_usd:    float,
    margen:       float,
    tasa_bcv:     float,
    tasa_binance: float,
    policy:       str = POLICY_MARKET_FACTOR,
) -> dict:
    """
    MARKET_FACTOR (proveedor normal):
        precio_base = costo × (1 + margen)
        precio_ref  = precio_base × (binance / bcv)
        precio_bs   = precio_base × binance

    BCV_DIRECT (proveedor paga en Bs al BCV):
        precio_ref  = costo × (1 + margen)       ← precio real de venta
        precio_base = precio_ref × (bcv / binance) ← factor invertido, más bajo
        precio_bs   = precio_ref × bcv
    """
    factor_normal    = round(tasa_binance / tasa_bcv,    6) if tasa_bcv     > 0 else 1.0
    factor_invertido = round(tasa_bcv    / tasa_binance, 6) if tasa_binance > 0 else 1.0

    if policy == POLICY_BCV_DIRECT:
        precio_ref  = round(float(costo_usd or 0) * (1 + float(margen or 0)), 4)
        precio_base = round(precio_ref * factor_invertido, 4)
        precio_bs   = round(precio_ref * float(tasa_bcv), 2)
    else:  # MARKET_FACTOR
        precio_base = round(float(costo_usd or 0) * (1 + float(margen or 0)), 4)
        precio_ref  = round(precio_base * factor_normal, 4)
        precio_bs   = round(precio_base * float(tasa_binance), 2)

    return {
        "precio_base_usd":        precio_base,
        "precio_referencial_usd": precio_ref,
        "precio_bs":              precio_bs,
        "factor":                 factor_normal,
        "pricing_policy":         policy,
    }


def resolver_policy(
    pricing_policy_override: str | None,
    proveedor_id:            int | None,
    prov_policy_map:         dict,          # {proveedor_id: (policy, ajuste_divisa_pct)}
) -> tuple[str, float]:
    """
    Fallback chain: override producto → policy proveedor → MARKET_FACTOR.
    Retorna (policy, ajuste_divisa_pct).
    """
    if pricing_policy_override and pricing_policy_override in _VALID_POLICIES:
        return pricing_policy_override, 0.0
    if proveedor_id and proveedor_id in prov_policy_map:
        return prov_policy_map[proveedor_id]
    return POLICY_MARKET_FACTOR, 0.0
