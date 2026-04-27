"""
CarbonIQ – Next-Month Emission Predictor
Uses a saved scikit-learn model when available; falls back to a ±5 % drift model.
"""

from __future__ import annotations
import os
import random

_model = None   # lazy-loaded singleton


def _get_model():
    global _model
    if _model is None:
        try:
            import joblib
            path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "data", "linear_regression_model.pkl")
            )
            if os.path.exists(path):
                _model = joblib.load(path)
        except Exception:
            pass   # joblib not installed or model corrupt → stay None
    return _model


def predict_next_month(
    travel_km_per_day: float,
    electricity_kwh: float,
    diet: str,
    current_total: float,
) -> float:
    """
    Returns the predicted CO₂ total (kg) for next month.

    Strategy
    --------
    1. If an ML model (.pkl) exists → use it with feature engineering.
    2. Otherwise → apply a realistic ±5 % random drift around current_total.
    """
    model = _get_model()

    # ── Fallback: simple drift ────────────────────────────────────────────────
    if model is None:
        drift = 1 + random.uniform(-0.05, 0.05)
        return round(current_total * drift, 2)

    # ── ML path ───────────────────────────────────────────────────────────────
    try:
        import pandas as pd
        monthly_travel = travel_km_per_day * 30
        feature_dict   = {col: 0 for col in model.feature_names_in_}
        updates = {
            "Vehicle Monthly Distance Km":  monthly_travel,
            "Diet_Vegetarian":              1 if diet == "Vegetarian"     else 0,
            "Diet_Mixed":                   1 if diet == "Mixed"          else 0,
            "Diet_Non-Vegetarian":          1 if diet == "Non-Vegetarian" else 0,
        }
        for k, v in updates.items():
            if k in feature_dict:
                feature_dict[k] = v

        df  = pd.DataFrame([feature_dict])[list(model.feature_names_in_)]
        raw = float(model.predict(df)[0])

        # Adjust relative to current total to correct for intercept bias
        baseline   = getattr(model, "intercept_", 1186)
        adjustment = (raw - baseline) * 0.1
        return round(current_total + adjustment, 2)

    except Exception:
        # Any runtime error → graceful fallback
        drift = 1 + random.uniform(-0.05, 0.05)
        return round(current_total * drift, 2)
