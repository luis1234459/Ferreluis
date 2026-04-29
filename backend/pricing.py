"""
Módulo de pricing puro — sin dependencias de DB ni FastAPI.
Importable desde tests sin efectos secundarios.
"""

POLICY_MARKET_FACTOR = "MARKET_FACTOR"
POLICY_BCV_DIRECT    = "BCV_DIRECT"
_VALID_POLICIES      = {POLICY_MARKET_FACTOR, POLICY_BCV_DIRECT}


def calcular_precios(
    costo_usd:         float,
    margen:            float,
    tasa_bcv:          float,
    tasa_binance:      float,
    policy:            str   = POLICY_MARKET_FACTOR,
    ajuste_divisa_pct: float = 0.0,
) -> dict:
    """
    Retorna los precios calculados según la política del proveedor.

    MARKET_FACTOR  — precio_referencial = precio_base × (binance / BCV)
                     precio_bs          = precio_base × tasa_binance
    BCV_DIRECT     — precio_referencial = precio_base  (sin factor paralelo)
                     precio_bs          = precio_base × tasa_BCV
                     precio_divisa_usd  = precio_base × (1 + ajuste_divisa_pct)
    """
    factor      = round(tasa_binance / tasa_bcv, 6) if tasa_bcv > 0 else 1.0
    precio_base = round(float(costo_usd or 0) * (1 + float(margen or 0)), 4)

    if policy == POLICY_BCV_DIRECT:
        precio_ref  = precio_base
        precio_bs   = round(precio_base * float(tasa_bcv), 2)
    else:  # MARKET_FACTOR (default)
        precio_ref  = round(precio_base * factor, 4)
        precio_bs   = round(precio_base * float(tasa_binance), 2)

    precio_divisa = round(precio_base * (1.0 + float(ajuste_divisa_pct or 0)), 4)

    return {
        "precio_base_usd":        precio_base,
        "precio_referencial_usd": precio_ref,
        "precio_bs":              precio_bs,
        "precio_divisa_usd":      precio_divisa,
        "factor":                 factor,
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
