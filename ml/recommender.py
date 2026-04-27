"""
CarbonIQ – Smart Recommendation Engine
Replaces the original rule-based system with a ranked, impact-aware approach.

Each recommendation includes:
  - title           : short action name
  - impact          : High / Medium / Low
  - description     : human-readable guidance
  - optimized_value : suggested target for the input
  - estimated_saving: kg CO₂ saved per month (used for ranking)
  - category        : Travel / Energy / Food / Lifestyle
"""

from __future__ import annotations


# ── Recommendation Configs ────────────────────────────────────────────────────
# Each entry defines how to compute the saving from a given input value.

_RECS = [
    {
        "key":   "travel_km_monthly",         # matches key in user_inputs passed in
        "title": "Switch to Public Transport or EV",
        "category": "Travel",
        "impact": "High",
        "description": (
            "Switching from a petrol/diesel vehicle to public transport or an EV "
            "can cut your travel emissions by up to 60 %. Even 3 days of remote work "
            "per week reduces your monthly km significantly."
        ),
        "reduction_factor": 0.40,              # 40 % of travel emission = saving potential
        "input_emission_key": "Travel",
    },
    {
        "key":   "electricity_kwh",
        "title": "Cut Electricity Consumption",
        "category": "Energy",
        "impact": "High",
        "description": (
            "Switch to LED bulbs, set AC to 24 °C, unplug idle devices, and consider "
            "rooftop solar or a green-energy tariff. A 15 % reduction is easily achievable."
        ),
        "reduction_factor": 0.15,
        "input_emission_key": "Electricity",
    },
    {
        "key":   "diet",
        "title": "Shift Towards Plant-Based Diet",
        "category": "Food",
        "impact": "Medium",
        "description": (
            "Reducing red-meat consumption to 3 meals per week and increasing vegetables, "
            "legumes, and grains can lower diet emissions by 30–50 %."
        ),
        "reduction_factor": 0.30,
        "input_emission_key": "Diet",
    },
    {
        "key":   "clothes_monthly",
        "title": "Embrace Slow Fashion",
        "category": "Lifestyle",
        "impact": "Medium",
        "description": (
            "Fast fashion has a heavy carbon footprint. Buying second-hand, swapping with "
            "friends, or halving monthly purchases can save meaningful CO₂."
        ),
        "reduction_factor": 0.50,             # saving = 50 % × (count × per-item factor)
        "per_unit_kg": 5.5,                   # ~5.5 kg CO₂ per new garment
        "input_emission_key": None,           # compute directly from input value
    },
    {
        "key":   "waste_weekly",
        "title": "Reduce & Compost Household Waste",
        "category": "Lifestyle",
        "impact": "Low",
        "description": (
            "Composting organic waste, recycling, and avoiding single-use plastics can "
            "halve your waste bag count and its associated methane emissions."
        ),
        "reduction_factor": 0.50,
        "per_unit_kg": 2.0,                   # ~2 kg CO₂-eq per bag per week × 4 weeks
        "input_emission_key": None,
    },
    {
        "key":   "grocery_bill",
        "title": "Buy Local & Seasonal Produce",
        "category": "Food",
        "impact": "Low",
        "description": (
            "Choosing locally grown, seasonal produce cuts transport emissions and "
            "supports regional farmers. Aim to source 50 % of groceries locally."
        ),
        "reduction_factor": 0.10,
        "per_unit_kg": 0.004,                 # ~0.4 % of grocery bill as kg CO₂
        "input_emission_key": None,
    },
]

# Impact sorting weight (higher = shown first among equal savings)
_IMPACT_ORDER = {"High": 3, "Medium": 2, "Low": 1}


def generate_recommendations(emissions: dict, user_inputs: dict) -> list[dict]:
    """
    Builds and ranks recommendations based on actual emission values and inputs.

    Parameters
    ----------
    emissions   : output of calculate_emissions()  { Travel, Electricity, Diet, Total }
    user_inputs : {
        "travel_km_monthly": float,
        "electricity_kwh":   float,
        "diet":              str,
        "clothes_monthly":   int,
        "waste_weekly":      int,
        "grocery_bill":      float,
    }

    Returns
    -------
    List of recommendation dicts sorted by estimated_saving (desc).
    """
    recs: list[dict] = []

    for cfg in _RECS:
        key = cfg["key"]
        val = user_inputs.get(key, 0)

        if val == 0 or val is None:
            continue  # no data → skip

        # ── Compute estimated saving ──────────────────────────────────────────
        if cfg.get("input_emission_key"):
            # Saving based on existing emission breakdown
            base_emission = emissions.get(cfg["input_emission_key"], 0)
            saving = round(base_emission * cfg["reduction_factor"], 2)
        else:
            # Saving computed directly from input quantity
            per_unit = cfg.get("per_unit_kg", 1.0)
            if key == "waste_weekly":
                # weekly bags → monthly
                saving = round(val * 4 * per_unit * cfg["reduction_factor"], 2)
            else:
                saving = round(val * per_unit * cfg["reduction_factor"], 2)

        if saving <= 0:
            continue

        recs.append({
            "title":            cfg["title"],
            "category":         cfg["category"],
            "impact":           cfg["impact"],
            "description":      cfg["description"],
            "estimated_saving": saving,
        })

    # Sort: primary = estimated_saving (desc), secondary = impact weight (desc)
    recs.sort(
        key=lambda r: (r["estimated_saving"], _IMPACT_ORDER[r["impact"]]),
        reverse=True,
    )
    return recs
