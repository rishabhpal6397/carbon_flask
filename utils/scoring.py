"""
CarbonIQ – Carbon Score & Gamification
Converts a monthly CO₂ total into a 0–100 score with a badge category.

Scale (kg CO₂ / month):
  ≤ 200  → score near 100   (Eco Pro 🌳)
  ~ 400  → score ~ 60       (Conscious 🌿)
  ≥ 700  → score near 0     (Beginner 🌱)

Formula: inverse-linear clamp mapped to [0, 100].
"""

from __future__ import annotations

# Thresholds (kg CO₂/month)
_MIN_KG  = 50    # best realistic  → score 100
_MAX_KG  = 800   # worst realistic → score 0

# Badge tiers  (min_score inclusive)
_TIERS = [
    (75, "Eco Pro",   "🌳", "#22c55e"),   # green
    (45, "Conscious", "🌿", "#84cc16"),   # lime
    (0,  "Beginner",  "🌱", "#f59e0b"),   # amber
]


def carbon_score(total_kg: float) -> dict:
    """
    Parameters
    ----------
    total_kg : Monthly total CO₂ emission in kg.

    Returns
    -------
    {
        "value":    int,    # 0–100
        "category": str,    # "Eco Pro" | "Conscious" | "Beginner"
        "emoji":    str,
        "color":    str,    # hex colour for UI badge
        "label":    str,    # e.g. "Eco Pro 🌳"
        "message":  str,    # motivational text
    }
    """
    # Clamp then invert
    clamped = max(_MIN_KG, min(total_kg, _MAX_KG))
    score   = round(100 * (1 - (clamped - _MIN_KG) / (_MAX_KG - _MIN_KG)))

    # Determine tier
    category, emoji, color = "Beginner", "🌱", "#f59e0b"
    for min_score, cat, em, col in _TIERS:
        if score >= min_score:
            category, emoji, color = cat, em, col
            break

    # Motivational messages per tier
    messages = {
        "Eco Pro":   "Amazing! You are leading by example. Keep inspiring others. 🌍",
        "Conscious": "Great effort! A few more tweaks and you could reach Eco Pro status.",
        "Beginner":  "Everyone starts somewhere. Follow the recommendations to cut your footprint!",
    }

    return {
        "value":    score,
        "category": category,
        "emoji":    emoji,
        "color":    color,
        "label":    f"{category} {emoji}",
        "message":  messages[category],
    }
