"""
CarbonIQ – Main Blueprint
Serves the dashboard page and per-record PDF downloads.

KEY FIX: mongo resolved via get_mongo() inside each view, not at import time.
"""

from flask import Blueprint, render_template, send_file, abort
from flask_login import login_required, current_user
import io

from extensions import mongo
from models.calculation import Calculation

main_bp = Blueprint("main", __name__)


@main_bp.route("/dashboard")
@login_required
def dashboard():
     # resolved inside request context ✓
    history       = Calculation.get_by_user(current_user.id, limit=8)
    monthly_chart = Calculation.monthly_totals(current_user.id)
    return render_template(
        "dashboard.html",
        history=history,
        monthly_chart=monthly_chart,
    )


@main_bp.route("/report/<calc_id>")
@login_required
def download_report(calc_id: str):
    """Generate and stream a PDF report for one calculation record."""
    from utils.pdf_report import generate_pdf

               # resolved inside request context ✓
    calc  = Calculation.get_by_id(calc_id, current_user.id)
    if not calc:
        abort(404)

    pdf_bytes = generate_pdf(current_user.username, calc)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"carboniq_report_{calc_id[:8]}.pdf",
    )