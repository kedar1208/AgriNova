"""Illustrative interactive farm layout (Plotly). NOT satellite imagery and NOT GPS field boundaries: plot areas are proportional to the
acres FarmOptimizer allocated, arranged by a simple recursive split. Colours can show crop, planned-irrigation zone, or simulated crop risk."""
import numpy as np
import plotly.graph_objects as go
from utils.charts import BASE, G, _fin

W, H = 3.0, 2.0
ZONES = [("Rain-fed", "#e9e2c4"), ("Light irrigation", "#a9d6ef"), ("Moderate irrigation", "#5fb0e0"), ("Heavy irrigation", "#1f6fb0")]
RISK = [("Low", "#4f9a63"), ("Moderate", "#c79a2b"), ("High", "#d27a2c"), ("Severe", "#b04030")]
FREE = "#cfd8d2"


def _split(items, x, y, w, h, out):
    if len(items) == 1:
        out.append((items[0][0], x, y, w, h)); return
    total, cum, best = sum(a for _, a in items), 0.0, 1
    for i in range(1, len(items)):
        cum += items[i - 1][1]
        if abs(cum - total / 2) <= abs(sum(a for _, a in items[:best]) - total / 2):
            best = i
    left, right = items[:best], items[best:]
    frac = sum(a for _, a in left) / total
    if w >= h:
        _split(left, x, y, w * frac, h, out); _split(right, x + w * frac, y, w * (1 - frac), h, out)
    else:
        _split(left, x, y, w, h * frac, out); _split(right, x, y + h * frac, w, h * (1 - frac), out)


def plots(plan, area):
    """List of dicts (name, rect, acres, per-crop facts) for each planted crop plus unallocated land."""
    M, names = plan["matrices"], list(plan["allocation"])
    x = np.array(list(plan["allocation"].values()))
    items = sorted([(i, a) for i, a in enumerate(x) if a > 0.01], key=lambda t: -t[1])
    free = max(area - float(sum(a for _, a in items)), 0.0)
    if free > 0.01 * area:
        items.append((-1, free))
    if not items:
        return []
    rects = []
    _split(items, 0.0, 0.0, W, H, rects)
    pw_max = max([M["plan_w"][i] for i, _ in items if i >= 0] + [1e-9])
    out = []
    for i, rx, ry, rw, rh in rects:
        if i < 0:
            out.append(dict(name="Unallocated", j=-1, acres=free, rect=(rx, ry, rw, rh))); continue
        pw = float(M["plan_w"][i])
        zone = 0 if pw <= 1e-6 else 1 if pw / pw_max < .34 else 2 if pw / pw_max < .67 else 3
        pl = float((M["A"][:, i] < 0).mean())
        risk = 0 if pl < .10 else 1 if pl < .25 else 2 if pl < .50 else 3
        mean_y = float(M["Y"][:, i].mean())
        out.append(dict(name=names[i], j=i, acres=float(x[i]), rect=(rx, ry, rw, rh), zone=zone, risk=risk, p_loss=pl, water=pw * x[i], water_per_acre=pw,
                        invest=float(M["cost"][i] * x[i]), cv=float(M["Y"][:, i].std() / mean_y) if mean_y > 0 else 0.0))
    return out


def _dark(hex_):
    r, g, b = (int(hex_[k:k + 2], 16) for k in (1, 3, 5))
    return (0.299 * r + 0.587 * g + 0.114 * b) < 140


def farm_figure(plan, area, mode="Crop", agrocast=None):
    """mode: Crop | Irrigation zone | Simulated crop risk. agrocast: optional dict(crop=..., category=...) shown in the hover of that crop."""
    ps = plots(plan, area)
    f = go.Figure()
    seen = set()
    cols = {n: G[k % len(G)] for k, n in enumerate(plan["allocation"])}
    for p in ps:
        if p["j"] < 0:
            key, col = "Unallocated land", FREE
        elif mode == "Irrigation zone":
            key, col = ZONES[p["zone"]]
        elif mode == "Simulated crop risk":
            key, col = RISK[p["risk"]][0] + " simulated risk", RISK[p["risk"]][1]
        else:
            key, col = p["name"], cols[p["name"]]
        rx, ry, rw, rh = p["rect"]; g = 0.02
        x0, x1, y0, y1 = rx + g, rx + rw - g, ry + g, ry + rh - g
        if p["j"] < 0:
            tip = f"<b>Unallocated land</b><br>{p['acres']:.2f} acres ({p['acres'] / area * 100:.0f}% of farm)<br>Left unplanted by the optimiser's constraints"
        else:
            note = f"<br>AgroCast this week ({agrocast['crop']}): {agrocast['category']} risk" if agrocast and agrocast["crop"] == p["name"] else ""
            tip = (f"<b>{p['name']}</b><br>{p['acres']:.2f} acres ({p['acres'] / area * 100:.0f}% of farm)<br>Irrigation zone: {ZONES[p['zone']][0]}<br>"
                   f"Planned irrigation: {p['water']:,.0f} m³ ({p['water_per_acre']:,.0f} m³/acre)<br>Investment: Rs {p['invest']:,.0f}<br>"
                   f"Simulated chance of loss: {p['p_loss'] * 100:.0f}% ({RISK[p['risk']][0]})<br>Yield variability (CV): {p['cv']:.2f}{note}")
        f.add_trace(go.Scatter(x=[x0, x1, x1, x0, x0], y=[y0, y0, y1, y1, y0], fill="toself", fillcolor=col, mode="lines", line=dict(color="#fff", width=2),
                               name=key, legendgroup=key, showlegend=key not in seen, text=tip, hoverinfo="text", hoveron="fills"))
        seen.add(key)
        label = "Unallocated" if p["j"] < 0 else f"<b>{p['name']}</b><br>{p['acres']:.1f} ac" + ("" if p["water"] <= 0 else f"<br>💧 {p['water']:,.0f} m³")
        f.add_annotation(x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=label, showarrow=False, font=dict(size=13, color="#fff" if _dark(col) else "#14281f"))
    f.add_annotation(x=0, y=H + 0.07, xanchor="left", yanchor="bottom", showarrow=False, font=dict(size=11, color="#51655a"),
                     text="💧 Illustrative water source (position not real) → drawn along the left edge")
    f.add_shape(type="line", x0=-0.04, x1=-0.04, y0=0, y1=H, line=dict(color="#2f9be0", width=5, dash="dot"))
    f.update_xaxes(visible=False, range=[-0.12, W + 0.04]); f.update_yaxes(visible=False, range=[-0.04, H + 0.22], scaleanchor="x")
    f.update_layout(title="Illustrative farm layout (not a map)", height=480, **{**BASE, "legend": dict(orientation="h", y=-0.04, font=dict(size=12))})
    return f


def resource_shares(plan, area):
    """Share of land vs share of investment vs share of planned irrigation per crop - shows which crops pull the most resources."""
    ps = [p for p in plots(plan, area) if p["j"] >= 0]
    if not ps:
        return go.Figure()
    inv, wat = sum(p["invest"] for p in ps) or 1, sum(p["water"] for p in ps) or 1
    names = [p["name"] for p in ps]
    f = go.Figure()
    f.add_bar(x=names, y=[p["acres"] / area * 100 for p in ps], name="Share of farm area", marker_color="#0f7a5a")
    f.add_bar(x=names, y=[p["invest"] / inv * 100 for p in ps], name="Share of investment", marker_color="#e7a93a")
    f.add_bar(x=names, y=[p["water"] / wat * 100 for p in ps], name="Share of planned irrigation", marker_color="#1f8fcf")
    f.update_layout(barmode="group", title="Resource allocation by crop (%)", yaxis_title="% of total", height=340, **{**BASE, "legend": dict(orientation="h", y=-0.2)})
    return _fin(f)
