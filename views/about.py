import streamlit as st

TEAM = ""   # e.g. "Team Name - College - Members"; shown at the bottom of this page when set


def render(ctx):
    from utils import ui
    ui.page_head("About", "Two separate answers to the same problem: weather no longer follows the calendar.", eyebrow="Agri Nova")
    st.markdown("""
| | **AgroCast** | **FarmOptimizer** |
|---|---|---|
| Asks | What will this week's weather do to my crop? | Which crop mix survives good *and* bad seasons? |
| Looks at | 14 days past, 7 days ahead, growth stage, soil | Land, budget, water, simulated rainfall seasons |
| Method | Stage-weighted threshold scores, FAO-56 soil-water balance | Monte-Carlo scenarios, FAO-33 yield response, CVaR linear programming |
| Gives | Risk scores, irrigation timing and volume, alerts | Acres per crop, profit spread, resilience score |
| Code | `engine/climate_risk.py`, `irrigation_engine.py` | `engine/scenario_generator.py`, `optimization_engine.py` |

The two engines never import each other. They share only the crop table.

**What is real and what is not.** Live weather comes from Open-Meteo. Offline mode uses made-up sample data and says so. Crop yields, prices and costs are starting assumptions - check them locally. Scenarios are simulations, not forecasts.

**Limits.** The risk scores are rules of thumb, not validated against loss records. The fungal indicator is not a disease forecast. Price swings, pests and sowing-date choice are not modelled. Nothing here guarantees a yield; talk to your local agriculture officer or KVK before big decisions.
""")
    if TEAM:
        st.caption(TEAM)
