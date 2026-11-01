"""Hackathon demo scenario: ONE clearly-labelled SAMPLE farm in Maharashtra that pre-fills the sidebar and FarmOptimizer crop choices.
Nothing here is real farmer data or a measured result; every number the app shows for it is computed live by the normal engines.
The sowing date is set relative to today so the demo crop is always mid-season."""
from datetime import date, timedelta
import streamlit as st

DEMO = {"state": "Maharashtra", "district": "Nashik", "crop": "Wheat", "sowing_days_ago": 40, "area": 5.0, "unit": "acres", "soil": "Black cotton soil",
        "irrigation": "Sprinkler", "water_m3": 6000.0, "budget": 150000.0, "compare_crops": ["Wheat", "Maize", "Groundnut", "Tomato"]}
LABEL = "SAMPLE DEMO FARM - illustrative values, not a real farmer's data"


def load():
    """Callback: write the demo farm into the sidebar widget keys (must run as a callback, before the widgets are drawn)."""
    d, s = DEMO, st.session_state
    s["w_state"] = d["state"]
    s[f"district_{d['state']}"] = d["district"]
    s["w_crop"], s["w_sowing"] = d["crop"], date.today() - timedelta(days=d["sowing_days_ago"])
    s["w_area"], s["w_unit"], s["w_soil"], s["w_irrigation"] = d["area"], d["unit"], d["soil"], d["irrigation"]
    s["w_water"], s["w_budget"], s["w_has_m"] = d["water_m3"], d["budget"], False
    s["opt_pick"] = list(d["compare_crops"])
    s["demo_loaded"] = True


def goto(view, page):
    st.session_state["view"] = view
    st.session_state["nav"] = page


def start():
    """Landing-page shortcut: load the sample farm and open the guided demo."""
    load()
    goto("agrocast", "Demo")


def matches(farm):
    """True while the sidebar still holds the sample farm (sowing date ignored: it moves with today)."""
    d = DEMO
    return (farm["state"] == d["state"] and farm["district"] == d["district"] and farm["crop"] == d["crop"] and abs(farm["area_acres"] - d["area"]) < 1e-6
            and farm["soil"] == d["soil"] and farm["irrigation"] == d["irrigation"] and farm["water_m3"] == d["water_m3"] and farm["budget"] == d["budget"])
