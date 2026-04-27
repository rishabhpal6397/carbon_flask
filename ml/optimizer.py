"""
CarbonIQ – Emission Optimizer
Simulates a "what-if best-case" scenario by applying reduction targets
to each input dimension, then calculates the potential savings.
"""

# Relative diet multipliers when switching to each category
DIET_FACTORS: dict[str, float] = {
    "Vegetarian":     1.0,
    "Mixed":          0.9,   # 10 % higher than vegetarian baseline
    "Non-Vegetarian": 0.8,   # 20 % higher
}


def optimize_emissions(
    travel_km: float,
    electricity_kwh: float,
    diet_type: str,
) -> dict:
    """
    Apply realistic improvement targets:
      - Travel      → 20 % reduction (carpooling / EV shift)
      - Electricity → 15 % reduction (LED / solar / efficiency)
      - Diet        → multiplier applied downstream

    Returns dict consumed by calculate_emissions + a diet_factor for scaling.
    """
    return {
        "travel":      round(travel_km      * 0.80, 2),
        "electricity": round(electricity_kwh * 0.85, 2),
        "diet_factor": DIET_FACTORS.get(diet_type, 1.0),
    }
