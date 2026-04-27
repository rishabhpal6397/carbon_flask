/* ═══════════════════════════════════════════════════════════════
   CarbonIQ — app.js
   Handles: slider sync · calculate API · UI rendering ·
            donut chart · trend chart · score arc · history delete
═══════════════════════════════════════════════════════════════ */

"use strict";

/* ── Donut Chart (vanilla canvas) ─────────────────────────── */
const DONUT_COLORS = ["#22c55e", "#3b82f6", "#f59e0b"];

function drawDonut(canvas, values) {
  const ctx  = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  const cx = W / 2, cy = H / 2, r = 78;
  ctx.clearRect(0, 0, W, H);

  const total = values.reduce((a, b) => a + b, 0) || 1;
  let angle = -Math.PI / 2;
  values.forEach((v, i) => {
    const slice = (v / total) * 2 * Math.PI;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, angle, angle + slice);
    ctx.closePath();
    ctx.fillStyle = DONUT_COLORS[i % DONUT_COLORS.length];
    ctx.fill();
    angle += slice;
  });
  // Hollow centre
  ctx.beginPath();
  ctx.arc(cx, cy, r * 0.58, 0, 2 * Math.PI);
  ctx.fillStyle = "#0b0f1a";
  ctx.fill();
}

/* ── Trend Line Chart ─────────────────────────────────────── */
function drawTrendChart(canvas, data) {
  if (!data || data.length == 2) return;
  const W   = canvas.width  = canvas.parentElement.clientWidth;
  const H   = canvas.height = 120;
  const ctx = canvas.getContext("2d");
  if (data.length === 1) {
    ctx.fillStyle = "#22c55e";
    ctx.font = "14px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(
      `${data[0].month}: ${data[0].total} kg`,
      W / 2,
      H / 2
    );
    return;
  }
  const pad = { t: 16, r: 16, b: 36, l: 48 };
  const vals = data.map(d => d.total);
  const minV = Math.min(...vals) * 0.9;
  const maxV = Math.max(...vals) * 1.05;
  const xStep = (W - pad.l - pad.r) / (data.length - 1);
  const xOf = i => pad.l + i * xStep;
  const yOf = v => pad.t + (1 - (v - minV) / (maxV - minV)) * (H - pad.t - pad.b);

  ctx.clearRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = "#1e293b"; ctx.lineWidth = 1;
  [0.25, 0.5, 0.75, 1].forEach(t => {
    const y = pad.t + t * (H - pad.t - pad.b);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
  });

  // Fill area
  const grad = ctx.createLinearGradient(0, pad.t, 0, H - pad.b);
  grad.addColorStop(0, "rgba(34,197,94,.25)");
  grad.addColorStop(1, "rgba(34,197,94,0)");
  ctx.beginPath();
  ctx.moveTo(xOf(0), yOf(vals[0]));
  vals.forEach((v, i) => ctx.lineTo(xOf(i), yOf(v)));
  ctx.lineTo(xOf(vals.length - 1), H - pad.b);
  ctx.lineTo(xOf(0), H - pad.b);
  ctx.closePath(); ctx.fillStyle = grad; ctx.fill();

  // Line
  ctx.beginPath();
  ctx.strokeStyle = "#22c55e"; ctx.lineWidth = 2.5; ctx.lineJoin = "round";
  vals.forEach((v, i) => i === 0 ? ctx.moveTo(xOf(i), yOf(v)) : ctx.lineTo(xOf(i), yOf(v)));
  ctx.stroke();

  // Dots + x-labels
  data.forEach((d, i) => {
    const x = xOf(i), y = yOf(d.total);
    ctx.beginPath(); ctx.arc(x, y, 4, 0, 2 * Math.PI);
    ctx.fillStyle = "#22c55e"; ctx.fill();
    ctx.strokeStyle = "#0b0f1a"; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = "#64748b"; ctx.font = "10px sans-serif"; ctx.textAlign = "center";
    ctx.fillText(d.month, x, H - 8);
  });
}

/* ── Score Arc animation ──────────────────────────────────── */
function animateScore(value, color) {
  const arc   = document.getElementById("scoreArc");
  const valEl = document.getElementById("scoreVal");
  if (!arc) return;
  arc.style.stroke = color || "#22c55e";
  arc.style.strokeDashoffset = 314 - (value / 100) * 314;
  let cur = 0;
  const step = value / 50;
  const t = setInterval(() => {
    cur = Math.min(cur + step, value);
    valEl.textContent = Math.round(cur);
    if (cur >= value) clearInterval(t);
  }, 20);
}

/* ── Slider output sync ───────────────────────────────────── */
document.querySelectorAll("input[type=range]").forEach(s => {
  const out = document.getElementById(s.id + "_out");
  if (out) s.addEventListener("input", () => { out.value = s.value; });
});

/* ── Sex toggle ───────────────────────────────────────────── */
let selectedSex = "Male";
document.querySelectorAll(".toggle").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".toggle").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    selectedSex = btn.dataset.val;
  });
});

/* ── Calculate button ─────────────────────────────────────── */
const loader       = document.getElementById("loader");
const emptyState   = document.getElementById("emptyState");
const resultsBlock = document.getElementById("resultsBlock");

document.getElementById("calculateBtn").addEventListener("click", async () => {
  const payload = {
    travel_km:       +document.getElementById("travel_km").value,
    vehicle:          document.getElementById("vehicle").value,
    electricity:     +document.getElementById("electricity").value,
    diet:             document.getElementById("diet").value,
    clothes_monthly: +document.getElementById("clothes_monthly").value,
    waste_weekly:    +document.getElementById("waste_weekly").value,
    grocery_bill:    +document.getElementById("grocery_bill").value,
    sex:              selectedSex,
  };

  loader.classList.remove("hidden");
  try {
    const resp = await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const json = await resp.json();
    if (json.status !== "ok") throw new Error(json.message || "Server error");
    renderResults(json.results, json.calc_id);
  } catch (err) {
    alert("Calculation failed: " + err.message);
  } finally {
    loader.classList.add("hidden");
  }
});

/* ── Render all result sections ───────────────────────────── */
function renderResults(r, calcId) {
  emptyState.classList.add("hidden");
  resultsBlock.classList.remove("hidden");

  const em = r.emissions, opt = r.optimization, pred = r.prediction, sc = r.score;

  // Score
  setText("scoreVal",   sc.value);
  setText("scoreBadge", sc.label);
  setText("scoreMsg",   sc.message);
  animateScore(sc.value, sc.color);

  // Emissions
  setText("rTotal",  em.Total);
  setText("rTravel", em.Travel);
  setText("rElec",   em.Electricity);
  setText("rDiet",   em.Diet);

  // Donut
  drawDonut(document.getElementById("donutCanvas"), [em.Travel, em.Electricity, em.Diet]);
  document.getElementById("donutVal").textContent = em.Total;

  // Legend
  const legendEl = document.getElementById("legend");
  legendEl.innerHTML = [
    { label: "Travel",      val: em.Travel,      c: DONUT_COLORS[0] },
    { label: "Electricity", val: em.Electricity, c: DONUT_COLORS[1] },
    { label: "Diet",        val: em.Diet,        c: DONUT_COLORS[2] },
  ].map(({ label, val, c }) =>
    `<div class="legend-item">
       <span class="legend-dot" style="background:${c}"></span>
       <span>${label} — <strong>${val} kg</strong></span>
     </div>`
  ).join("");

  // Optimisation
  setText("rOptTotal",     opt.optimized_total);
  setText("rReduction",    opt.reduction_kg);
  setText("rReductionPct", opt.reduction_pct + " %");
  const maxVal = em.Total || 1;
  animateBar("barCurrent", (em.Total / maxVal) * 100,               em.Total + " kg");
  animateBar("barOpt",     (opt.optimized_total / maxVal) * 100,    opt.optimized_total + " kg");

  // Prediction
  setText("rCurrent",   pred.current);
  setText("rPredicted", pred.predicted);
  setText("rDelta",     pred.delta + " kg");
  const trendEl = document.getElementById("rTrend");
  if (trendEl) trendEl.textContent = pred.trend.charAt(0).toUpperCase() + pred.trend.slice(1);
  const trendCard = document.getElementById("trendCard");
  if (trendCard) trendCard.style.borderColor =
    pred.trend === "decreasing" ? "rgba(34,197,94,.3)" :
    pred.trend === "increasing" ? "rgba(239,68,68,.3)" : "var(--border)";

  // Recommendations
  const recsList = document.getElementById("recsList");
  recsList.innerHTML = (r.recommendations || []).slice(0, 6).map(rec => `
    <div class="rec-card">
      <span class="rec-impact ${rec.impact}">${rec.impact}</span>
      <div class="rec-body">
        <div class="rec-title">${rec.title}</div>
        <div class="rec-desc">${rec.description}</div>
        <div class="rec-saving">💚 Save ~${rec.estimated_saving} kg CO₂/month</div>
        <div class="rec-cat">${rec.category}</div>
      </div>
    </div>`).join("");

  // PDF link for this specific calculation
  if (calcId) {
    const pdfRow  = document.getElementById("pdfRow");
    const pdfLink = document.getElementById("pdfLink");
    if (pdfRow && pdfLink) {
      pdfLink.href = `/report/${calcId}`;
      pdfRow.classList.remove("hidden");
    }
  }

  resultsBlock.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ── Helpers ──────────────────────────────────────────────── */
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function animateBar(barId, pct, label) {
  const bar   = document.getElementById(barId);
  const valEl = document.getElementById(barId + "Val");
  if (bar)   setTimeout(() => { bar.style.width = Math.min(pct, 100) + "%"; }, 50);
  if (valEl) valEl.textContent = label;
}

/* ── Delete history record ────────────────────────────────── */
async function deleteRecord(calcId) {          // eslint-disable-line no-unused-vars
  if (!confirm("Delete this record?")) return;
  try {
    const resp = await fetch(`/api/delete/${calcId}`, { method: "DELETE" });
    const json = await resp.json();
    if (json.status === "ok") {
      const card = document.getElementById(`hcard-${calcId}`);
      if (card) { card.style.opacity = "0"; card.style.transition = "opacity .3s"; setTimeout(() => card.remove(), 300); }
    }
  } catch { alert("Could not delete record."); }
}

/* ── Monthly trend chart (data from Jinja2 block) ─────────── */
window.addEventListener("load", () => {
  if (typeof MONTHLY_CHART_DATA !== "undefined" && MONTHLY_CHART_DATA.length >= 0) {
    const canvas = document.getElementById("trendCanvas");
    if (canvas) drawTrendChart(canvas, MONTHLY_CHART_DATA);
  }
});
