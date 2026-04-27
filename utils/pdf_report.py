"""
CarbonIQ – PDF Report Generator
Uses ReportLab to produce a downloadable, branded PDF for each calculation.

Install: pip install reportlab
"""

from __future__ import annotations
import io
from datetime import datetime

from reportlab.lib             import colors
from reportlab.lib.pagesizes   import A4
from reportlab.lib.styles      import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units       import cm
from reportlab.platypus        import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics        import renderPDF

# ── Brand colours ──────────────────────────────────────────────────────────────
GREEN      = colors.HexColor("#22c55e")
DARK       = colors.HexColor("#0f172a")
LIGHT_GREY = colors.HexColor("#f1f5f9")
MID_GREY   = colors.HexColor("#64748b")
WHITE      = colors.white

W, H = A4   # 595 × 842 pts


def _styles():
    base = getSampleStyleSheet()
    custom = {
        "Title": ParagraphStyle(
            "Title", fontSize=22, fontName="Helvetica-Bold",
            textColor=DARK, spaceAfter=4
        ),
        "Subtitle": ParagraphStyle(
            "Subtitle", fontSize=11, fontName="Helvetica",
            textColor=MID_GREY, spaceAfter=16
        ),
        "SectionHead": ParagraphStyle(
            "SectionHead", fontSize=13, fontName="Helvetica-Bold",
            textColor=DARK, spaceBefore=14, spaceAfter=6
        ),
        "Body": ParagraphStyle(
            "Body", fontSize=10, fontName="Helvetica",
            textColor=DARK, leading=15, spaceAfter=4
        ),
        "SmallGrey": ParagraphStyle(
            "SmallGrey", fontSize=9, fontName="Helvetica",
            textColor=MID_GREY
        ),
    }
    return custom


def _bar_chart(current: float, optimized: float, max_val: float) -> Drawing:
    """Draw a simple horizontal bar comparison (current vs optimised)."""
    bar_w   = 300
    bar_h   = 18
    d       = Drawing(bar_w + 110, 60)

    labels = [("Current", current, colors.HexColor("#ef4444")),
              ("Optimised", optimized, GREEN)]

    for i, (lbl, val, col) in enumerate(labels):
        y      = 36 - i * 26
        filled = int(bar_w * min(val / max_val, 1.0)) if max_val else 0
        # background track
        d.add(Rect(80, y, bar_w, bar_h, fillColor=LIGHT_GREY, strokeColor=None))
        # filled portion
        d.add(Rect(80, y, filled, bar_h, fillColor=col, strokeColor=None))
        # label
        d.add(String(0, y + 4, lbl, fontSize=9, fillColor=DARK))
        d.add(String(80 + bar_w + 6, y + 4, f"{val:.1f} kg", fontSize=9, fillColor=DARK))
    return d


def _table_style(header_bg=GREEN):
    return TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  header_bg),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  10),
        ("BOTTOMPADDING",(0, 0), (-1, 0),  8),
        ("TOPPADDING",   (0, 0), (-1, 0),  8),
        ("BACKGROUND",   (0, 1), (-1, -1), LIGHT_GREY),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING",   (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 6),
    ])


def generate_pdf(username: str, calc: dict) -> bytes:
    """
    Build and return a PDF as raw bytes.

    Parameters
    ----------
    username : display name of the user
    calc     : Calculation document (from Calculation.get_by_id)
               containing 'inputs', 'results', 'created_at'
    """
    buf     = io.BytesIO()
    doc     = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    st      = _styles()
    story   = []
    inputs  = calc.get("inputs",  {})
    results = calc.get("results", {})
    em      = results.get("emissions",    {})
    opt     = results.get("optimization", {})
    pred    = results.get("prediction",   {})
    score   = results.get("score",        {})
    recs    = results.get("recommendations", [])

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("⬡ CarbonIQ", st["Title"]))
    story.append(Paragraph("Personal Carbon Footprint Report", st["Subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN))
    story.append(Spacer(1, 8))

    meta = [
        ["User", username],
        ["Report Date", calc.get("created_at", datetime.utcnow().strftime("%d %b %Y"))],
        ["Carbon Score", f"{score.get('value', '—')} / 100   {score.get('label', '')}"],
    ]
    t = Table(meta, colWidths=[4*cm, 12*cm])
    t.setStyle(_table_style(header_bg=DARK))
    story.append(t)
    story.append(Spacer(1, 14))

    # ── 1. Inputs ─────────────────────────────────────────────────────────────
    story.append(Paragraph("1. Your Lifestyle Inputs", st["SectionHead"]))
    rows = [["Parameter", "Value"]] + [
        ["Daily Travel",    f"{inputs.get('travel_km', 0)} km/day ({inputs.get('vehicle','')})"],
        ["Electricity",     f"{inputs.get('electricity', 0)} kWh/month"],
        ["Diet Type",       inputs.get("diet", "—")],
        ["New Clothes",     f"{inputs.get('clothes_monthly', 0)} per month"],
        ["Waste Bags",      f"{inputs.get('waste_weekly', 0)} per week"],
        ["Grocery Bill",    f"₹{inputs.get('grocery_bill', 0)}/month"],
    ]
    t = Table(rows, colWidths=[7*cm, 9*cm])
    t.setStyle(_table_style())
    story.append(t)
    story.append(Spacer(1, 10))

    # ── 2. Emission Breakdown ─────────────────────────────────────────────────
    story.append(Paragraph("2. Monthly CO₂ Emission Breakdown", st["SectionHead"]))
    rows = [["Category", "kg CO₂/month", "% of Total"]]
    total = em.get("Total", 1) or 1
    for cat in ("Travel", "Electricity", "Diet"):
        val = em.get(cat, 0)
        rows.append([cat, f"{val:.2f}", f"{val/total*100:.1f}%"])
    rows.append(["TOTAL", f"{em.get('Total', 0):.2f}", "100 %"])

    t = Table(rows, colWidths=[7*cm, 5*cm, 4*cm])
    t.setStyle(_table_style())
    # Bold total row
    t.setStyle(TableStyle([
        ("FONTNAME",    (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND",  (0, -1), (-1, -1), colors.HexColor("#dcfce7")),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # ── 3. Optimisation Bar Chart ─────────────────────────────────────────────
    story.append(Paragraph("3. What-If Optimisation", st["SectionHead"]))
    story.append(Paragraph(
        f"By making the recommended changes you could reduce your footprint by "
        f"<b>{opt.get('reduction_kg', 0)} kg/month</b> "
        f"({opt.get('reduction_pct', 0)} % reduction).",
        st["Body"]
    ))
    story.append(Spacer(1, 6))
    max_val = em.get("Total", 1)
    story.append(_bar_chart(
        em.get("Total", 0),
        opt.get("optimized_total", 0),
        max_val * 1.05,
    ))
    story.append(Spacer(1, 10))

    # ── 4. ML Prediction ──────────────────────────────────────────────────────
    story.append(Paragraph("4. Next-Month Forecast (ML)", st["SectionHead"]))
    rows = [
        ["This Month", f"{pred.get('current', 0)} kg CO₂"],
        ["Next Month", f"{pred.get('predicted', 0)} kg CO₂"],
        ["Trend",      f"{pred.get('trend', '—').capitalize()} ({pred.get('delta', 0)} kg)"],
    ]
    t = Table(rows, colWidths=[7*cm, 9*cm])
    t.setStyle(_table_style())
    story.append(t)
    story.append(Spacer(1, 10))

    # ── 5. Recommendations ────────────────────────────────────────────────────
    story.append(Paragraph("5. Smart Recommendations", st["SectionHead"]))
    if recs:
        rows = [["#", "Action", "Category", "Impact", "Est. Saving (kg)"]]
        for i, r in enumerate(recs[:6], 1):     # top 6
            rows.append([
                str(i),
                r.get("title", ""),
                r.get("category", ""),
                r.get("impact", ""),
                f"{r.get('estimated_saving', 0):.2f}",
            ])
        t = Table(rows, colWidths=[1*cm, 6.5*cm, 3*cm, 2.5*cm, 3*cm])
        t.setStyle(_table_style())
        story.append(t)

        story.append(Spacer(1, 10))
        for r in recs[:3]:
            story.append(Paragraph(f"<b>{r['title']}</b>", st["Body"]))
            story.append(Paragraph(r.get("description", ""), st["SmallGrey"]))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("No recommendations at this time.", st["Body"]))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Generated by CarbonIQ — Track. Optimise. Act.",
        st["SmallGrey"]
    ))

    doc.build(story)
    return buf.getvalue()
