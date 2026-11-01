import streamlit as st
from utils import charts, ui


def render(ctx):
    m, q = ctx["meta"], ctx["meta"]["quality"]
    ui.page_head("Weather", f"{m.get('location', '')} · {m['source']} · {m['lat']:.2f}°N, {m['lon']:.2f}°E", eyebrow="AgroCast")
    if m.get("error"):
        ui.callout("warn", "Live weather unavailable", m["error"], "Showing clearly-labelled sample data instead. Check your connection and reload to retry.")
    ui.chart(charts.weather_figure(ctx["wx"]))
    c = st.columns(3)
    c[0].metric("Days of data", q["rows"])
    c[1].metric("Days with filled-in values", q["imputed_rows"])
    c[2].metric("Humidity data", "yes" if q["rh_available"] else "no")
    with st.expander("Daily data"):
        ui.table(ctx["wx"])
        st.caption("Gaps of up to two days are interpolated, then the median is used; missing evapotranspiration comes from the Hargreaves equation. Filled rows are flagged.")
    ui.footer()
