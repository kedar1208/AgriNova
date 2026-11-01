from html import escape as esc
import streamlit as st
from utils import demo, ui
from utils.helpers import inr

STEPS = [
    ("Select a farm", "Load the sample Maharashtra farm. The sidebar fills with its location, crop, area, soil, irrigation, water and budget - change any value to explore.", None, None, "load"),
    ("View weather conditions", "Open the weather page: observed days plus the seven-day forecast, with source, update time and data-quality notes.", "agrocast", "Weather", None),
    ("Understand crop risk", "See the six hazard scores for this crop and growth stage, the prioritised actions (what, why, what to do, when) and the risk explanation cards.", "agrocast", "AgroCast", None),
    ("View irrigation recommendations", "On the same page open the Irrigation tab for the decision, water per round and the projected soil-water curve.", "agrocast", "AgroCast", None),
    ("Optimize crop planning", "Run FarmOptimizer: the CVaR optimisation picks a crop mix under land, budget and water limits using simulated seasons.", "farmopt", "FarmOptimizer", "optim"),
    ("Compare baseline and optimized outcomes", "In FarmOptimizer read 'Baseline vs optimized', then the 'AgroCast-informed plan' tab for the risk-aware comparison.", "farmopt", "FarmOptimizer", "optim"),
    ("Download the agricultural report", "Export the PDF with farm configuration, weather, risks, irrigation, actions, allocation, financials and assumptions.", "agrocast", "Report", None),
    ("Ask the farm assistant (optional)", "Ask in English, Hindi or Marathi about any number on screen.", "agrocast", "Assistant", None),
]


def render(ctx):
    f = ctx["farm"]
    ui.page_head("Guided demo", "Walk through the full AGRI NOVA workflow on one sample farm in Maharashtra.", eyebrow="Demonstration")
    ui.callout("warn", demo.LABEL, "The farm is invented for demonstration. Weather is live (Open-Meteo) unless you switch to sample weather; all risks, irrigation and plans are calculated by the app's engines. "
                                   "No real farmers, users or performance statistics are claimed.")
    d = demo.DEMO
    ui.section("Sample farm")
    ui.html(ui.chips([("Location", f"{d['district']}, {d['state']}"), ("Crop", d["crop"]), ("Sown", f"{d['sowing_days_ago']} days ago (relative to today)"), ("Area", f"{d['area']:.0f} acres"),
                      ("Soil", d["soil"]), ("Irrigation", d["irrigation"]), ("Water", f"{d['water_m3']:,.0f} m³"), ("Budget", inr(d["budget"]))]))
    loaded = demo.matches(f)
    a, b, c = st.columns(3)
    a.button("Load sample farm" if not loaded else "Reload sample farm", key="demo_load", type="primary", on_click=demo.load)
    offline = st.session_state.get("w_offline", False)
    b.button("Use live weather" if offline else "Use sample weather (no internet needed)", key="demo_wx", on_click=lambda: st.session_state.__setitem__("w_offline", not offline))
    c.markdown(ui.note("ok" if loaded else "info", "Sample farm is loaded." if loaded else "Your sidebar currently holds different values - load the sample farm to follow the demo."), unsafe_allow_html=True)
    if offline:
        st.caption("Sample (synthetic) weather is on: use it only when there is no connection, and say so when presenting.")

    ui.section("Walkthrough")
    done_opt = bool(st.session_state.get("optim"))
    for i, (title, text, view, page, check) in enumerate(STEPS, 1):
        ok = (check == "load" and loaded) or (check == "optim" and done_opt)
        with st.container(border=True):
            l, r = st.columns([5, 1])
            l.markdown(f"**{i}. {title}** {'✅' if ok else ''}")
            l.caption(text)
            if view:
                r.button("Open →", key=f"demo_go_{i}", on_click=demo.goto, args=(view, page))
    st.caption("Steps 5-6 are marked done once FarmOptimizer has produced a plan in this session.")
    ui.footer("Sample demonstration scenario - values are illustrative; results are heuristic indicators and simulations, not forecasts or guarantees.")
