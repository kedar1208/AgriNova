import streamlit as st
from engine.crop_database import load_crops
from engine.optimization_engine import crop_economics_table
from utils import charts, ui


def render(ctx):
    ui.page_head("Crop comparison", eyebrow="FarmOptimizer", sub= "Per-acre economics at three rainfall levels: 70%, 100% and 135% of normal. Every number is a starting assumption - edit the table and FarmOptimizer will use your values.")
    base = st.session_state.get("crops_df")
    if base is None:
        base = load_crops()
    names = list(base.crop)
    pick = st.multiselect("Crops", names, default=names[:6])
    if not pick:
        ui.empty_state("Pick a crop to compare", "Choose one or more crops above to see per-acre profit under drought, normal and excess rain.", "🌾")
        return
    cols = ["crop", "yield_q_acre", "price_per_q", "cost_per_acre", "etm_mm", "ky", "waterlog_sens"]
    edited = ui.editor(base.loc[base.crop.isin(pick), cols], disabled=["crop"])
    merged = base.set_index("crop")
    merged.update(edited.set_index("crop"))
    st.session_state["crops_df"] = merged.reset_index()[list(base.columns)]
    sel = st.session_state["crops_df"]
    sel = sel[sel.crop.isin(pick)]
    econ = crop_economics_table(sel, st.session_state.get("assum", {}))
    ui.chart(charts.economics_bars(econ))
    ui.table(econ.round(1))
    st.caption("Break-even yield = cost / price. Profit = yield x price - cost.")
    ui.footer()
