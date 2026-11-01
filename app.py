"""AGRINOVA - Streamlit entry point.  Run:  streamlit run app.py
Flow: landing page (views/landing.py) -> AgroCast or FarmOptimizer space -> that solution's dashboard pages.
st.session_state["view"] is "home" | "agrocast" | "farmopt".
(UI modules live in views/ - not pages/ - so Streamlit does not auto-create a second navigation.)"""
from datetime import date, timedelta
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Agri Nova · Predict. Protect. Optimize. Grow.", page_icon="🌾", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"<style>{(Path(__file__).parent / 'assets' / 'styles.css').read_text()}</style>", unsafe_allow_html=True)

from engine.crop_database import load_crops, get_crop, stage_for, SOILS, IRRIGATION_EFF
from engine.locations import states, districts_for, DEFAULT_DISTRICT
from engine.weather_engine import get_live_weather, get_sample_weather
from engine.climate_risk import assess_risks
from engine.irrigation_engine import advise
from engine.recommendation_engine import generate_alerts
from utils.helpers import to_acres, validate_farm
from views import dashboard, agrocast, farmoptimizer, weather, crop_comparison, reports, about, landing, assistant
from views import demo as demo_page
from utils import ui, demo as demo_data

PAGES = {"Dashboard": dashboard, "AgroCast": agrocast, "FarmOptimizer": farmoptimizer,
         "Weather": weather, "Crop Comparison": crop_comparison, "Assistant": assistant, "Demo": demo_page, "Report": reports, "About": about}
# Every page stays reachable; each solution simply lists its own pages first.
SPACES = {
    "agrocast": dict(label="AgroCast", pages=["Dashboard", "AgroCast", "Weather", "Assistant", "Demo", "Report", "About"], other="farmopt"),
    "farmopt": dict(label="FarmOptimizer", pages=["FarmOptimizer", "Crop Comparison", "Dashboard", "Assistant", "Demo", "Report", "About"], other="agrocast"),
}
NAV_LABEL = {"Dashboard": "Field overview", "AgroCast": "Risk and irrigation", "FarmOptimizer": "Crop planner", "Weather": "Weather", "Crop Comparison": "Crop comparison", "Assistant": "Farm assistant", "Demo": "Guided demo",
             "Report": "Report", "About": "About"}

NAV_ICON = {"Dashboard": "🌾", "AgroCast": "🌦️", "FarmOptimizer": "🧮", "Weather": "☁️", "Crop Comparison": "📊", "Assistant": "💬", "Demo": "🎯", "Report": "📄", "About": "ℹ️"}

view = st.session_state.get("view", "home")
if view not in SPACES:
    # Streamlit forgets widgets that are not drawn in a run; re-assigning keeps the sidebar inputs while the landing page is showing.
    for k in [k for k in list(st.session_state.keys()) if str(k).startswith(("w_", "district_"))]:
        st.session_state[k] = st.session_state[k]
    landing.render()
    st.stop()
space = SPACES[view]
ui.apply_theme(view)


@st.cache_data(ttl=1800, show_spinner="Fetching weather...")
def live_weather(state, district):
    """Cached ONLY on success: a failed lookup raises, so a network hiccup is never remembered for 30 minutes."""
    return get_live_weather(state, district)


def load_weather(state, district, offline):
    if not offline:
        try:
            return live_weather(state, district)
        except Exception as e:
            return get_sample_weather(state, district, f"Live weather unavailable ({type(e).__name__}) - showing sample data instead.")
    return get_sample_weather(state, district)


crops = load_crops()
with st.sidebar:
    ui.side_brand(space["label"])
    st.button("← All solutions", key="go_home", on_click=landing.go, args=("home",))
    st.button(f"Switch to {SPACES[space['other']]['label']}", key="go_other", on_click=landing.go, args=(space["other"],))
    st.markdown('<div class="side-h">Pages</div>', unsafe_allow_html=True)
    if st.session_state.get("nav") not in space["pages"]:
        st.session_state["nav"] = space["pages"][0]
    nav = st.radio("Navigate", space["pages"], key="nav", format_func=lambda p: f"{NAV_ICON[p]}  {NAV_LABEL[p]}", label_visibility="collapsed")

    st.markdown('<div class="side-h">Location</div>', unsafe_allow_html=True)
    state = st.selectbox("State", states(), index=states().index("Maharashtra"), key="w_state")
    opts = districts_for(state)
    # keyed per state so switching state resets the district to a valid one for that state
    district = st.selectbox("District", opts, index=opts.index(DEFAULT_DISTRICT[state]), key=f"district_{state}")

    st.markdown('<div class="side-h">Crop</div>', unsafe_allow_html=True)
    crop = st.selectbox("Crop", list(crops.crop), index=list(crops.crop).index("Wheat"), key="w_crop")
    sowing = st.date_input("Sowing date", date.today() - timedelta(days=60), key="w_sowing")

    st.markdown('<div class="side-h">Field</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    area_v = c1.number_input("Farm area", 0.1, 5000.0, 3.0, 0.5, key="w_area")
    unit = c2.selectbox("Unit", ["acres", "hectares"], key="w_unit")
    soil = st.selectbox("Soil type", list(SOILS), index=list(SOILS).index("Loam"), key="w_soil")
    irrigation = st.selectbox("Irrigation method", list(IRRIGATION_EFF), index=0, key="w_irrigation")

    st.markdown('<div class="side-h">Resources</div>', unsafe_allow_html=True)
    water = st.number_input("Irrigation water for the season (m³)", 0.0, 1e7, 3000.0, 100.0, key="w_water")
    budget = st.number_input("Farming budget (₹)", 0.0, 1e8, 100000.0, 5000.0, key="w_budget")

    with st.expander("Advanced"):
        has_m = st.checkbox("I measured soil moisture today", key="w_has_m")
        mpct = st.slider("Measured soil moisture (% of capacity)", 0, 100, 60, key="w_mpct") if has_m else None
        offline = st.checkbox("Offline demo mode (sample data)", value=False, key="w_offline")

farm = dict(state=state, district=district, area_acres=to_acres(area_v, unit), crop=crop, sowing_date=sowing, soil=soil,
            irrigation=irrigation, water_m3=water, budget=budget, measured_pct=mpct)
errs = validate_farm(farm, crops)
if errs:
    for e in errs:
        ui.callout("error", "Check your farm details", e, "Fix the highlighted value in the sidebar.")
    st.stop()

try:
    wx, meta = load_weather(state, district, offline)
    c = get_crop(crop, crops)
    si, label, das = stage_for(sowing, int(c["duration_days"]), date.today())
    risks = assess_risks(wx, c, si, soil, mpct)
    irr = advise(wx, c, si, soil, farm["area_acres"], irrigation, mpct)
    alerts = generate_alerts(wx, c, risks, irr, meta["source"])
except Exception as e:
    ui.callout("error", "Could not compute the forecast results", str(e), "Try Offline demo mode in the sidebar (Advanced), or change the location or crop.")
    st.stop()

ui.topbar(space["label"], NAV_LABEL[nav], meta["source"] == "open-meteo")
if demo_data.matches(farm) and nav != "Demo":
    st.caption("🧪 " + demo_data.LABEL)
ctx = dict(farm=farm, wx=wx, meta=meta, crop=c, stage_idx=si, stage_label=label, das=das, risks=risks, irr=irr, alerts=alerts)
try:
    PAGES[nav].render(ctx)
except Exception as e:   # one broken page must not blank the whole app; st.stop/rerun signals are not Exception subclasses
    ui.callout("error", f"The {NAV_LABEL[nav]} page could not be shown", f"{type(e).__name__}: {e}",
               "Try Offline demo mode or different farm inputs in the sidebar, or open another page. Your other pages are unaffected.")
