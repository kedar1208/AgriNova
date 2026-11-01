from html import escape as esc
import streamlit as st
from utils import ui
from utils.helpers import inr
from engine.unified_intelligence import scenario_adjustment, interpret
from views import landing


def _headline(o, irr, sown=True):
    if not sown:
        return esc(irr["decision"])
    if o["category"] == "Low":
        threat = "No major weather threat is expected over the next seven days."
    else:
        threat = f'Biggest threat this week: <b>{esc(o["driver"].lower())}</b> ({esc(o["category"].lower())} risk).'
    return f'{threat} {esc(irr["decision"])}'


def _irrigation_kpi(irr, water_m3):
    if irr["postpone"]:
        return "Postpone", "Rain is coming - re-check after it passes"
    if not irr["needed"]:
        return "Not needed", "Soil water stays above the stress level"
    vol = irr["volume_m3"]
    if vol <= 0:
        return "Needed", "No irrigation source selected"
    rounds = water_m3 / vol
    return "Needed", f"~{vol:,.0f} m³ per round · season water covers ~{rounds:.1f} rounds"


def render(ctx):
    f, wx, meta, o, irr, crop = ctx["farm"], ctx["wx"], ctx["meta"], ctx["risks"]["overall"], ctx["irr"], ctx["crop"]
    fc = wx[wx.kind == "forecast"].head(7)
    if fc.empty:
        fc = wx.tail(7)
    today = fc.iloc[0]

    ui.html(ui.hero(f["crop"], ctx["stage_idx"], ctx["stage_label"], ctx["das"], meta.get("location") or f'{f["district"]}, {f["state"]}',
                    meta.get("location_exact", False) or meta["source"] != "open-meteo", meta["source"] == "open-meteo",
                    _headline(o, irr, ctx["stage_idx"] >= 0), o["score"], o["category"]))
    if meta.get("error"):
        ui.callout("warn", "Live weather unavailable", meta["error"], "Showing clearly-labelled sample data instead. Reload to retry.")

    ui.html(ui.chips([("Area", f"{f['area_acres']:.1f} acres"), ("Soil", f["soil"]), ("Irrigation", f["irrigation"]),
                      ("Sown", f["sowing_date"].strftime("%d %b %Y")), ("Water", f"{f['water_m3']:,.0f} m³"), ("Budget", inr(f["budget"]))]))

    irr_val, irr_sub = _irrigation_kpi(irr, f["water_m3"])
    soil_val, soil_sub = "-", "Not sown yet"
    if "projection" in irr:
        p = irr["projection"]
        p = p[p.kind == "forecast"] if (p.kind == "forecast").any() else p
        soil_val = f"{p.frac.min() * 100:.0f}%"
        soil_sub = ("Lowest this week · " + ("estimated" if irr["estimated"] else "from your reading") +
                    f" · stress below {irr['threshold_frac'] * 100:.0f}%")
    k = st.columns(4)
    k[0].markdown(ui.kpi("Today", f"{today.tmax:.0f}° / {today.tmin:.0f}°C", f"Rain {today.rain_mm:.0f} mm"), unsafe_allow_html=True)
    k[1].markdown(ui.kpi("Rain this week", f"{fc.rain_mm.sum():.0f} mm", f"Hottest day {fc.tmax.max():.0f}°C"), unsafe_allow_html=True)
    k[2].markdown(ui.kpi("Irrigation", irr_val, irr_sub, "#b04030" if irr_val == "Needed" else None), unsafe_allow_html=True)
    k[3].markdown(ui.kpi("Soil water", soil_val, soil_sub), unsafe_allow_html=True)

    ui.section("Next 7 days")
    ui.html(ui.outlook(fc, crop["heat_c"], crop["heavy_rain_mm"]))

    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.section("Alerts")
        for a in ctx["alerts"]:
            ui.html(ui.note(a["level"], a["message"]))
    with right:
        ui.section("Risk breakdown")
        ui.html(ui.meters(ctx["risks"]))
    adj = scenario_adjustment(ctx["risks"])
    items = interpret(ctx["risks"], irr, adj)
    st.session_state["unified"] = {"insights": items, "adjustment": adj}
    ui.section("From weather risk to farm plan")
    ui.html(ui.insights(items))
    if adj["applied"]:
        st.caption("FarmOptimizer can test these as an optional planning scenario. " + " ".join(adj["rationale"]))
    if st.session_state.get("view") == "agrocast":
        st.button("Compare plans in FarmOptimizer →", key="to_farmopt", on_click=landing.go, args=("farmopt",))
    ui.footer()
