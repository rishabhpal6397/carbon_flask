"""
CarbonIQ – Emission Calculator
Converts raw user inputs into monthly CO₂-equivalent emissions (kg).

Emission factors:
  Travel      – vehicle-type emission factor × km/day × 30 days
  Electricity – grid average factor (India: ~0.82 kg CO₂/kWh)
  Diet        – fixed monthly estimate per diet category
"""

# kg CO₂ per km
TRAVEL_FACTORS: dict[str, float] = {
    "Petrol":           0.192,
    "Diesel":           0.171,
    "Electric":         0.050,
    "Public Transport": 0.080,
}

# kg CO₂ per month (approximate averages)
DIET_FACTORS: dict[str, float] = {
    "Vegetarian":     50.0,
    "Mixed":         100.0,
    "Non-Vegetarian": 150.0,
}

# kg CO₂ per kWh (Indian grid average)
ELECTRICITY_FACTOR = 0.82


def calculate_emissions(
    travel_km_per_day: float,
    vehicle_type: str,
    electricity_kwh: float,
    diet_type: str,
) -> dict:
    """
    Returns a breakdown dict with keys:
      Travel, Electricity, Diet, Total  (all in kg CO₂/month)
    """
    travel      = travel_km_per_day * 30 * TRAVEL_FACTORS.get(vehicle_type, 0.192)
    electricity = electricity_kwh * ELECTRICITY_FACTOR
    diet        = DIET_FACTORS.get(diet_type, 100.0)

    total = travel + electricity + diet
    return {
        "Travel":      round(travel,      2),
        "Electricity": round(electricity, 2),
        "Diet":        round(diet,        2),
        "Total":       round(total,       2),
    }
