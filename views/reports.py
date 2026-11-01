import sqlite3
import streamlit as st
from database import database as db
from utils import ui
from utils.pdf_generator import build_report
from engine.agrocast_insights import weather_summary, daily_table, recommendations, data_quality


def _extras(ctx):
    """Optional report sections; each is skipped if its data cannot be built, so the PDF never fails because of an extra."""
    x = {"stage_label": ctx["stage_label"] if ctx["stage_idx"] >= 0 else "Not sown yet", "das": ctx["das"], "duration": int(ctx["crop"]["duration_days"])}
    for key, fn in (("sm", lambda: weather_summary(ctx["wx"], ctx["crop"])), ("daily", lambda: daily_table(ctx["wx"], ctx["crop"], ctx["irr"])),
                    ("recs", lambda: recommendations(ctx["wx"], ctx["crop"], ctx["risks"], ctx["irr"], ctx["stage_idx"], ctx["meta"]["source"])), ("dq", lambda: data_quality(ctx["meta"], ctx["wx"]))):
        try:
            x[key] = fn()
        except Exception:
            pass
    cmp_ = (st.session_state.get("unified") or {}).get("comparison")
    if cmp_:
        x["comparison"] = cmp_
    return x


def render(ctx):
    ui.page_head("Report", "Download a PDF with farm details, crop stage, weather summary, risks, irrigation, prioritised actions and alerts" + (", plus the FarmOptimizer plan and comparison." if st.session_state.get("optim") else ". Open FarmOptimizer first to include its plan."), eyebrow="Export")
    cfg = dict(ctx["farm"])
    opt, cmp_df = st.session_state.get("optim"), st.session_state.get("compare")
    ui.section("Included in this report")
    inc = [("Farm and location", True), ("Weather and data quality", True), ("Climate risks and irrigation", True), ("Prioritised actions", True),
           ("FarmOptimizer plan", bool(opt)), ("Baseline comparison", cmp_df is not None), ("Risk-aware what-if", bool((st.session_state.get("unified") or {}).get("comparison")))]
    ui.html(ui.chips([(k, "included" if v else "not yet - run FarmOptimizer") for k, v in inc]))
    try:
        with st.spinner("Preparing your report..."):
            pdf = build_report(cfg, ctx["meta"], ctx["risks"], ctx["irr"], ctx["alerts"], opt, cmp_df, _extras(ctx))
        st.download_button("Download PDF report", pdf, file_name="agri_nova_report.pdf", mime="application/pdf", help="A4 PDF with data-source labels and limitations")
        st.caption(f"{len(pdf) / 1024:.0f} KB · opens in any PDF reader · sample weather is labelled as sample inside the report.")
    except Exception as e:
        ui.callout("error", "Could not build the PDF", str(e), "Check the farm inputs in the sidebar and try again.")
    ui.section("Save for later")
    name = st.text_input("Name", value="my-farm", max_chars=60, help="A short label, e.g. the field or season.").strip()
    if not name:
        st.caption("Enter a name to enable saving.")
    c = st.columns(2)
    try:
        if c[0].button("Save farm details", key="save_cfg", disabled=not name):
            db.save_config(name, cfg)
            ui.callout("ok", f"Saved '{name}'", "Your farm details are stored locally in the app database.")
        if c[1].button("Save latest FarmOptimizer plan", key="save_plan", disabled=not (opt and name), help=None if opt else "Run FarmOptimizer first to create a plan."):
            db.save_plan(name, opt["priority"], {"allocation": opt["allocation"], "metrics": opt["metrics"]})
            ui.callout("ok", "Plan saved", "The latest FarmOptimizer allocation is stored locally.")
        saved = db.list_configs()
        if saved:
            st.caption("Saved farms: " + ", ".join(saved))
        for p in db.list_plans()[:5]:
            st.caption(f"{p['saved_at']} - {p['farm']} ({p['priority']}): " + ", ".join(f"{k} {v:.1f} ac" for k, v in p["plan"]["allocation"].items() if v > 0.01))
    except (ValueError, sqlite3.Error, OSError) as e:
        ui.callout("error", "Could not use the saved-farm database", str(e), "Your report download is unaffected. Check that the data folder is writable.")
    ui.footer()
