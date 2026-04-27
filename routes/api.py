"""
CarbonIQ – REST API Blueprint

KEY FIX: mongo resolved via get_mongo() inside each view, not at import time.

Endpoints
---------
POST   /api/calculate      → Full pipeline + DB save
POST   /api/predict        → Prediction only (no save)
GET    /api/history        → Paginated history
GET    /api/dashboard      → Aggregated dashboard data
DELETE /api/delete/<id>    → Remove a record
"""

from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from extensions import mongo
from ml.calculator  import calculate_emissions
from ml.optimizer   import optimize_emissions
from ml.recommender import generate_recommendations
from ml.predicter   import predict_next_month
from models.calculation import Calculation
from utils.scoring  import carbon_score

api_bp = Blueprint("api", __name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _err(msg: str, code: int = 400):
    return jsonify({"status": "error", "message": msg}), code


def _run_pipeline(data: dict) -> tuple[dict, dict]:
    """Core calculation shared by /calculate and /predict. Raises ValueError on bad input."""
    travel_km       = float(data["travel_km"])
    vehicle         = data["vehicle"]
    electricity     = float(data["electricity"])
    diet            = data["diet"]
    clothes_monthly = int(data.get("clothes_monthly", 5))
    waste_weekly    = int(data.get("waste_weekly", 3))
    grocery_bill    = float(data.get("grocery_bill", 300))
    sex             = data.get("sex", "Male")

    # 1. Emissions
    emissions = calculate_emissions(travel_km, vehicle, electricity, diet)

    # 2. Optimisation
    opt       = optimize_emissions(travel_km, electricity, diet)
    opt_em    = calculate_emissions(opt["travel"], vehicle, opt["electricity"], diet)
    opt_total      = round(opt_em["Total"] * opt["diet_factor"], 2)
    reduction_kg   = round(emissions["Total"] - opt_total, 2)
    reduction_pct  = round((reduction_kg / emissions["Total"]) * 100, 1) if emissions["Total"] else 0

    # 3. Prediction
    predicted = predict_next_month(travel_km, electricity, diet, emissions["Total"])
    delta     = round(predicted - emissions["Total"], 2)

    # 4. Recommendations
    user_inputs = {
        "travel_km_monthly": travel_km * 30,
        "electricity_kwh":   electricity,
        "diet":              diet,
        "clothes_monthly":   clothes_monthly,
        "waste_weekly":      waste_weekly,
        "grocery_bill":      grocery_bill,
    }
    recommendations = generate_recommendations(emissions, user_inputs)

    # 5. Carbon Score
    score = carbon_score(emissions["Total"])

    results = {
        "emissions": emissions,
        "optimization": {
            "optimized_total": opt_total,
            "reduction_kg":    reduction_kg,
            "reduction_pct":   reduction_pct,
        },
        "prediction": {
            "current":   emissions["Total"],
            "predicted": predicted,
            "delta":     abs(delta),
            "trend":     "increasing" if delta > 0 else "decreasing" if delta < 0 else "stable",
        },
        "recommendations": recommendations,
        "score":           score,
    }

    inputs_to_save = {
        "travel_km": travel_km, "vehicle": vehicle,
        "electricity": electricity, "diet": diet,
        "clothes_monthly": clothes_monthly,
        "waste_weekly": waste_weekly,
        "grocery_bill": grocery_bill,
        "sex": sex,
    }
    return results, inputs_to_save


# ── Routes ─────────────────────────────────────────────────────────────────────

@api_bp.route("/calculate", methods=["POST"])
@login_required
def calculate():
    """
    POST /api/calculate
    Body: { travel_km, vehicle, electricity, diet,
            clothes_monthly, waste_weekly, grocery_bill, sex }

    Response: { status, calc_id, results }
    """
    data = request.get_json(silent=True)
    if not data:
        return _err("Request body must be valid JSON.")

    for field in ("travel_km", "vehicle", "electricity", "diet"):
        if field not in data:
            return _err(f"Missing required field: '{field}'")

    try:
        results, inputs = _run_pipeline(data)
             # resolved inside request context ✓
        calc_id = Calculation.save(current_user.id, inputs, results)
        return jsonify({"status": "ok", "calc_id": calc_id, "results": results})
    except (ValueError, KeyError) as e:
        return _err(f"Invalid input: {e}")
    except Exception as e:
        current_app.logger.exception("calculate error")
        return _err(str(e), 500)


@api_bp.route("/predict", methods=["POST"])
@login_required
def predict():
    """
    POST /api/predict
    Body: { travel_km, electricity, diet, current_total }

    Response: { status, current, predicted, delta, trend }
    """
    data = request.get_json(silent=True) or {}
    try:
        current_total = float(data.get("current_total", 0))
        predicted     = predict_next_month(
            float(data.get("travel_km",   10)),
            float(data.get("electricity", 200)),
            data.get("diet", "Mixed"),
            current_total,
        )
        delta = round(predicted - current_total, 2)
        return jsonify({
            "status":    "ok",
            "current":   current_total,
            "predicted": predicted,
            "delta":     abs(delta),
            "trend":     "increasing" if delta > 0 else "decreasing" if delta < 0 else "stable",
        })
    except Exception as e:
        return _err(str(e), 500)


@api_bp.route("/history", methods=["GET"])
@login_required
def history():
    """
    GET /api/history?limit=20
    Response: { status, count, records }
    """
    limit   = min(int(request.args.get("limit", 20)), 100)
           # resolved inside request context ✓
    records = Calculation.get_by_user(current_user.id, limit=limit)
    return jsonify({"status": "ok", "count": len(records), "records": records})


@api_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard_data():
    """
    GET /api/dashboard
    Response: { status, username, latest_score, monthly_chart, recent_records }
    """
      # resolved inside request context ✓
    history       = Calculation.get_by_user(current_user.id, limit=8)
    monthly_chart = Calculation.monthly_totals(current_user.id)
    latest_score  = history[0].get("results", {}).get("score", {}) if history else {}

    return jsonify({
        "status":         "ok",
        "username":       current_user.username,
        "latest_score":   latest_score,
        "monthly_chart":  monthly_chart,
        "recent_records": history,
    })


@api_bp.route("/delete/<calc_id>", methods=["DELETE"])
@login_required
def delete_calc(calc_id: str):
    """DELETE /api/delete/<calc_id>"""
            # resolved inside request context ✓
    success = Calculation.delete(calc_id, current_user.id)
    return jsonify({"status": "ok" if success else "error"})