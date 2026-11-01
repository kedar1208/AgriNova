"""Plotly figures (imported lazily by the UI). Colours follow the forest-green theme."""
import numpy as np
import plotly.graph_objects as go
from utils.helpers import CAT_COLOR

G = ["#0f7a5a", "#e7a93a", "#c4572f", "#1f8fcf", "#7a9b3c", "#8a6240", "#2aa57f", "#b9a77a"]
BASE = dict(template="plotly_white", margin=dict(l=10, r=10, t=48, b=10),
            font=dict(family="DM Sans, Segoe UI, sans-serif", color="#14281f", size=13),
            title_font=dict(family="Bricolage Grotesque, Segoe UI, sans-serif", size=18, color="#0a3a33"), title_x=0.0,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", colorway=G,
            hoverlabel=dict(bgcolor="#0a3a33", font=dict(color="#fff", family="DM Sans, Segoe UI, sans-serif", size=13), bordercolor="#e0b04a"),
            legend=dict(bgcolor="rgba(255,255,255,0)", font=dict(size=12)))


def _fin(f):
    f.update_xaxes(gridcolor="rgba(20,60,45,.07)", zeroline=False, linecolor="rgba(20,60,45,.18)", ticks="outside", tickcolor="rgba(20,60,45,.18)")
    f.update_yaxes(gridcolor="rgba(20,60,45,.07)", zeroline=False)
    return f


def risk_bars(risks):
    items = [(r["name"], r["score"], r["category"]) for k, r in risks.items() if k not in ("overall", "features")]
    f = go.Figure(go.Bar(x=[s for _, s, _ in items], y=[n for n, _, _ in items], orientation="h",
                         marker_color=[CAT_COLOR[c] for _, _, c in items], text=[f"{s:.0f} - {c}" for _, s, c in items], textposition="outside"))
    f.update_layout(title="Climate risk scores (0-100)", xaxis=dict(range=[0, 115]), yaxis=dict(autorange="reversed"), height=330, **BASE)
    return _fin(f)


def weather_figure(wx):
    f = go.Figure()
    for kind, dash in (("observed", "solid"), ("forecast", "dot")):
        d = wx[wx.kind == kind]
        f.add_bar(x=d.date, y=d.rain_mm, name=f"Rain mm ({kind})", marker_color="#a9cde6" if kind == "observed" else "#1f8fcf", yaxis="y2", opacity=.7)
        f.add_scatter(x=d.date, y=d.tmax, name=f"Tmax ({kind})", line=dict(color="#c4572f", width=2.5, dash=dash))
        f.add_scatter(x=d.date, y=d.tmin, name=f"Tmin ({kind})", line=dict(color="#1f6fa3", width=2.5, dash=dash))
    f.update_layout(title="Observed (solid/light) vs forecast (dotted/dark)", yaxis=dict(title="°C"), yaxis2=dict(title="mm", overlaying="y", side="right", showgrid=False),
                    height=380, **{**BASE, "legend": dict(orientation="h", y=-0.2, bgcolor="rgba(255,255,255,0)")})
    return _fin(f)


def moisture_figure(proj, threshold, estimated):
    f = go.Figure(go.Scatter(x=proj.date, y=proj.frac * 100, fill="tozeroy", line=dict(color="#0f7a5a", width=3, shape="spline"), fillcolor="rgba(42,165,127,.22)", name="Root-zone water %"))
    f.add_hline(y=threshold * 100, line_dash="dash", line_color="#a63d2f", annotation_text="stress level")
    f.update_layout(title="Root-zone water (% of capacity) - " + ("ESTIMATED by model" if estimated else "from MEASURED start value"), yaxis=dict(range=[0, 100]), height=320, **BASE)
    return _fin(f)


def allocation_bar(plan):
    a = {k: v for k, v in plan["allocation"].items() if v > 0.01}
    f = go.Figure(go.Bar(x=list(a), y=list(a.values()), marker_color=G[:len(a)], text=[f"{v:.1f}" for v in a.values()], textposition="outside"))
    f.update_layout(title="Recommended acres per crop", yaxis_title="acres", height=320, **BASE)
    return _fin(f)


def profit_hist(plan, strategies=None):
    f = go.Figure()
    for name, p in (strategies or {"Selected plan": plan}).items():
        x = np.array([p["allocation"][c] for c in p["allocation"]])
        f.add_histogram(x=p["matrices"]["A"] @ x, name=name, opacity=.6, nbinsx=40)
    f.update_layout(barmode="overlay", title="Simulated profit distribution (SIMULATED scenarios)", xaxis_title="Profit (Rs)", height=360, **BASE)
    return _fin(f)


def strategy_scatter(df):
    f = go.Figure(go.Scatter(x=df.cvar, y=df.expected_profit, mode="markers+text", text=df.strategy, textposition="top center",
                             marker=dict(size=df.resilience.clip(lower=5) / 3 + 6, color=df.resilience, colorscale="Greens", showscale=True, colorbar=dict(title="Resilience"))))
    f.update_layout(title="Return vs downside (bubble colour = resilience score)", xaxis_title="Worst-10% average profit (Rs)", yaxis_title="Expected profit (Rs)", height=420, **BASE)
    return _fin(f)


def scenario_bars(bd):
    f = go.Figure(go.Bar(x=bd.index, y=bd["mean"], marker_color=["#c4572f" if i == "Drought" else "#1f8fcf" if i == "Excess" else "#0f7a5a" for i in bd.index]))
    f.update_layout(title="Average profit by scenario type", yaxis_title="Rs", height=300, **BASE)
    return _fin(f)


def economics_bars(econ):
    f = go.Figure()
    for col, c in (("profit Drought", "#c4572f"), ("profit Normal", "#0f7a5a"), ("profit Excess", "#1f8fcf")):
        f.add_bar(x=econ.crop, y=econ[col], name=col.replace("profit ", ""), marker_color=c)
    f.update_layout(barmode="group", title="Profit per acre by rainfall scenario", yaxis_title="Rs / acre", height=380, **BASE)
    return _fin(f)


def plan_shift_bars(res):
    f = go.Figure()
    f.add_bar(x=res["crops"], y=[res["alloc0"][c] for c in res["crops"]], name="Original plan", marker_color="#8a6240")
    f.add_bar(x=res["crops"], y=[res["alloc1"][c] for c in res["crops"]], name="Risk-aware plan", marker_color="#0f7a5a")
    f.update_layout(barmode="group", title="Acres per crop: original vs risk-aware", yaxis_title="acres", height=330, **BASE)
    return _fin(f)


def risk_outcome_bars(res):
    names = ["Original plan, normal assumptions", "Original plan, risk scenario", "Risk-aware plan, risk scenario"]
    ms = [res["original"], res["original_under_risk"], res["risk_aware"]]
    f = go.Figure()
    f.add_bar(x=names, y=[m["expected_profit"] for m in ms], name="Expected profit", marker_color="#0f7a5a")
    f.add_bar(x=names, y=[m["cvar"] for m in ms], name="Worst-10% average", marker_color="#e7a93a")
    f.update_layout(barmode="group", title="Profit (Rs) - SIMULATED scenarios", yaxis_title="Rs", height=330, **BASE)
    return _fin(f)


def temp_vs_thresholds(d, crop):
    f = go.Figure()
    f.add_scatter(x=d.date, y=d.tmax, name="Max °C", line=dict(color="#c4572f", width=3, shape="spline"), mode="lines+markers")
    f.add_scatter(x=d.date, y=d.tmin, name="Min °C", line=dict(color="#1f6fa3", width=3, shape="spline"), mode="lines+markers", fill="tonexty", fillcolor="rgba(224,176,74,.12)")
    f.add_hline(y=crop["heat_c"], line_dash="dash", line_color="#c4572f", annotation_text=f"heat threshold {crop['heat_c']}°C")
    f.add_hline(y=crop["cold_c"], line_dash="dash", line_color="#1f6fa3", annotation_text=f"cold threshold {crop['cold_c']}°C")
    f.update_layout(title="Temperature vs crop thresholds", yaxis_title="°C", height=330, **{**BASE, "legend": dict(orientation="h", y=-0.18, bgcolor="rgba(255,255,255,0)")})
    return _fin(f)


def rain_and_soil(d, threshold_frac=None):
    f = go.Figure()
    f.add_bar(x=d.date, y=d.rain_mm, name="Rain mm", marker_color="#1f8fcf", opacity=.75)
    if d.soil_pct.notna().any():
        f.add_scatter(x=d.date, y=d.soil_pct, name="Root-zone water %", yaxis="y2", line=dict(color="#0f7a5a", width=3, shape="spline"), mode="lines+markers")
        if threshold_frac:
            f.add_scatter(x=d.date, y=[threshold_frac * 100] * len(d), name="Stress level %", yaxis="y2", line=dict(color="#a63d2f", width=1.5, dash="dash"), mode="lines")
    f.update_layout(title="Rain and projected root-zone water", yaxis_title="mm", yaxis2=dict(title="% of capacity", overlaying="y", side="right", range=[0, 100], showgrid=False),
                    height=330, **{**BASE, "legend": dict(orientation="h", y=-0.18, bgcolor="rgba(255,255,255,0)")})
    return _fin(f)


def risk_trend_lines(t):
    names = {"drought": "Drought", "heat": "Heat", "cold": "Cold", "rain": "Excess rain", "flood": "Waterlogging", "fungal": "Fungal-favourable"}
    f = go.Figure()
    for i, (k, n) in enumerate(names.items()):
        f.add_scatter(x=t.date, y=t[k], name=n, mode="lines+markers", line=dict(width=2.5, color=G[i % len(G)], shape="spline"))
    for y, c in ((25, "#c79a2b"), (50, "#d27a2c"), (75, "#b04030")):
        f.add_hline(y=y, line_dash="dot", line_color=c, opacity=.5)
    f.update_layout(title="How exposure builds through the week (heuristic scores, 0-100)", yaxis=dict(range=[0, 100], title="score"), height=360,
                    **{**BASE, "legend": dict(orientation="h", y=-0.2, bgcolor="rgba(255,255,255,0)")})
    return _fin(f)


# ---- Phase 4: FarmOptimizer dashboard figures -------------------------------------------------------------------
def allocation_donut(plan, area):
    """Share of the farm per crop; any land the optimiser leaves unplanted is shown explicitly as 'Unallocated'."""
    a = {k: v for k, v in plan["allocation"].items() if v > 0.01}
    free = max(area - sum(a.values()), 0.0)
    labels, vals, cols = list(a), list(a.values()), G[:len(a)]
    if free > 0.01:
        labels.append("Unallocated"); vals.append(free); cols.append("#cfd8d2")
    f = go.Figure(go.Pie(labels=labels, values=vals, hole=.58, marker=dict(colors=cols, line=dict(color="#fff", width=2)), sort=False,
                         texttemplate="%{label}<br>%{value:.1f} ac", hovertemplate="%{label}: %{value:.2f} acres (%{percent})<extra></extra>"))
    f.add_annotation(text=f"<b>{area:.1f}</b><br>acres", showarrow=False, font=dict(size=16, family="Bricolage Grotesque, Segoe UI, sans-serif", color="#0a3a33"))
    f.update_layout(title="Crop allocation of the farm", height=360, showlegend=False, **BASE)
    return f


def baseline_vs_optimized(base, opt, base_name="Baseline: even split", opt_name="Optimized plan"):
    """Grouped bars (Rs) for the three money outcomes; both plans are evaluated on the SAME simulated scenarios."""
    names = [("expected_profit", "Expected profit"), ("cvar", "Worst-10% average"), ("worst_profit", "Worst simulated season")]
    f = go.Figure()
    f.add_bar(x=[n for _, n in names], y=[base[k] for k, _ in names], name=base_name, marker_color="#b9a77a", text=[f"{base[k]:,.0f}" for k, _ in names], textposition="outside")
    f.add_bar(x=[n for _, n in names], y=[opt[k] for k, _ in names], name=opt_name, marker_color="#0f7a5a", text=[f"{opt[k]:,.0f}" for k, _ in names], textposition="outside")
    f.update_layout(barmode="group", title="Baseline vs optimized profit (Rs, SIMULATED)", yaxis_title="Rs", height=360, legend=dict(orientation="h", y=-0.15), **{k: v for k, v in BASE.items() if k != "legend"})
    return _fin(f)


def crop_water_variability(plan):
    """Per crop: planned irrigation volume (bars) and yield variability across simulated seasons (markers, right axis)."""
    M, x = plan["matrices"], np.array(list(plan["allocation"].values()))
    names = [c for c, a in plan["allocation"].items() if a > 0.01]
    keep = [i for i, a in enumerate(x) if a > 0.01]
    water = [float(M["plan_w"][i] * x[i]) for i in keep]
    cv = [float(M["Y"][:, i].std() / M["Y"][:, i].mean()) if M["Y"][:, i].mean() > 0 else 0.0 for i in keep]
    f = go.Figure()
    f.add_bar(x=names, y=water, name="Planned irrigation (m³)", marker_color="#1f8fcf")
    f.add_scatter(x=names, y=cv, name="Yield variability (CV)", yaxis="y2", mode="markers+lines", marker=dict(size=11, color="#e7a93a"), line=dict(color="#e7a93a", dash="dot"))
    f.update_layout(title="Water requirement and yield variability by crop", yaxis_title="m³ (whole planned area)", height=330,
                    yaxis2=dict(title="CV", overlaying="y", side="right", rangemode="tozero", showgrid=False), **{**BASE, "legend": dict(orientation="h", y=-0.2)})
    return _fin(f)
