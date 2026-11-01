import streamlit as st
from engine.recommendation_engine import risk_explanation
from engine.agrocast_insights import weather_summary, daily_table, risk_trend, stage_progress, recommendations, data_quality
from utils import charts, ui


def render(ctx):
    ui.banner("agrocast", "AgroCast", "What will the next seven days of weather do to the crop already in my field? Rule-based and fully traceable - no trained model, so no accuracy figure is claimed.")
    risks, irr, c = ctx["risks"], ctx["irr"], ctx["crop"]
    f, wx, meta = ctx["farm"], ctx["wx"], ctx["meta"]
    dq = data_quality(meta, wx)
    ui.html(ui.source_strip(dq))
    ui.html(ui.stage_card(stage_progress(c, ctx["stage_idx"], ctx["das"]), f["crop"]))
    ta, tw, t1, t2, tq = st.tabs(["Actions", "Weather outlook", "Risks", "Irrigation", "Data quality"])
    with t1:
        ui.html(ui.risk_dials(risks))
        ui.chart(charts.risk_bars(risks))
        o = risks["overall"]
        st.markdown(f"Overall = the single highest hazard: **{o['driver']}**, {o['category'].lower()} ({o['score']:.0f}/100).")
        for k, r in risks.items():
            if k in ("overall", "features"):
                continue
            e = risk_explanation(r)
            with st.expander(f"{r['name']} - {r['category']} ({r['score']:.0f}/100)"):
                st.markdown(f"**Predicted:** {e['predicted']}  \n**Why it matters:** {e['why']}  \n**What drove the score:** {e['factors']}  \n**What to do:** {e['next']}")
                if r.get("estimated_moisture"):
                    st.caption("Soil moisture here is an estimate - no measured value was entered.")
        with st.expander("How these numbers are calculated"):
            q = ctx["meta"]["quality"]
            st.markdown(f"Weather source: **{ctx['meta']['source']}** · rows with filled-in values: **{q['imputed_rows']}** · "
                        f"humidity data: **{'yes' if q['rh_available'] else 'no (rain used as a stand-in)'}**.")
            st.caption(f"{c['crop']} thresholds: heat above {c['heat_c']}°C, cold below {c['cold_c']}°C, heavy rain from {c['heavy_rain_mm']} mm/day, "
                       f"fungal-friendly {c['fungal_tmin']}-{c['fungal_tmax']}°C with humidity of 85% or more. These are starting values in data/crops.csv - adjust them for your area. "
                       "Soil moisture is estimated unless you enter a measurement in the sidebar (Advanced).")
    with t2:
        st.markdown(f"##### {irr['decision']}")
        m = st.columns(4)
        m[0].metric("Irrigate?", "Yes" if irr["needed"] else "No")
        m[1].metric("Wait for rain?", "Yes" if irr["postpone"] else "No")
        m[2].metric("Water per round", f"{irr['volume_m3']:,.0f} m³")
        m[3].metric("Depth", f"{irr['gross_mm']:.0f} mm")
        st.caption("Soil moisture is " + ("an ESTIMATE from the water-balance model." if irr["estimated"] else "the value you measured.") + " " + " ".join(irr["reasons"]))
        if "projection" in irr:
            ui.chart(charts.moisture_figure(irr["projection"], irr["threshold_frac"], irr["estimated"]))
    with ta:
        recs = recommendations(wx, c, risks, irr, ctx["stage_idx"], meta["source"])
        n_urgent = sum(1 for r in recs if r["priority"] <= 2)
        st.markdown(f"**{len(recs)} recommendation(s), highest priority first**" + (f" - {n_urgent} need action within the next few days." if n_urgent else " - nothing urgent."))
        ui.html(ui.reco_cards(recs))
        st.caption("P1 = act now, P2 = plan within 1-3 days, P3 = monitor. Scores rank exposure; they are not probabilities of crop loss or disease.")
    with tw:
        sm = weather_summary(wx, c)
        ui.html(ui.note("info", sm["headline"], f"Source: {dq['source']} · updated {dq['fetched']}"))
        fc = wx[wx.kind == "forecast"].head(7)
        ui.section("Seven-day timeline")
        ui.html(ui.outlook(fc if len(fc) else wx.tail(7), c["heat_c"], c["heavy_rain_mm"]))
        dt = daily_table(wx, c, irr)
        a, b = st.columns(2)
        with a:
            ui.chart(charts.temp_vs_thresholds(dt, c))
        with b:
            ui.chart(charts.rain_and_soil(dt, irr.get("threshold_frac")))
        ui.section("Risk trend")
        ui.chart(charts.risk_trend_lines(risk_trend(wx, c, ctx["stage_idx"], f["soil"], f["measured_pct"])))
        st.caption("Each point re-runs the same risk rules on observed days plus the forecast up to that day, so you can see when exposure builds. It is a heuristic trend, not a forecast of risk.")
    with tq:
        m = st.columns(4)
        m[0].metric("Source", dq["source"]); m[1].metric("Quality", dq["rating"]); m[2].metric("Filled-in days", f"{dq['imputed_pct']:.0f}%"); m[3].metric("Last update", dq["fetched"])
        for line in dq["notes"]:
            ui.html(ui.note("ok" if dq["rating"] == "Good" else "warning" if dq["rating"] == "Fair" else "critical", line))
        st.caption("Live weather is cached for 30 minutes. Quality counts sample data, approximate location, filled-in values, missing humidity and short forecasts.")
    ui.footer()
