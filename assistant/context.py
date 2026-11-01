"""Builds a plain-data snapshot ("facts") of what the app has ALREADY calculated. Read-only: nothing here recomputes a result.
The snapshot has no farmer name, state or district. `external_payload()` further rounds farm figures before anything can leave the app."""
from engine.agrocast_insights import stage_progress

_METRIC_KEYS = ("expected_profit", "cvar", "worst_profit", "p_loss", "resilience", "expected_water_m3", "yield_cv", "investment", "acres_used")


def _metrics(m):
    return {k: float(m[k]) for k in _METRIC_KEYS if m is not None and k in m}


def build_facts(ctx, state):
    """ctx: the dict app.py passes to every page. state: st.session_state (for the FarmOptimizer results, if the user has run it)."""
    f, wx, meta, crop, risks, irr = ctx["farm"], ctx["wx"], ctx["meta"], ctx["crop"], ctx["risks"], ctx["irr"]
    fc = wx[wx.kind == "forecast"].head(7)
    if fc.empty:
        fc = wx.tail(7)
    today = fc.iloc[0]
    live = meta.get("source") == "open-meteo"
    facts = {
        "crop": f["crop"], "stage_idx": int(ctx["stage_idx"]), "stage_label": ctx["stage_label"], "das": int(ctx["das"]),
        "stage": stage_progress(crop, ctx["stage_idx"], ctx["das"]),
        "area_acres": float(f["area_acres"]), "soil": f["soil"], "irrigation_method": f["irrigation"], "water_m3": float(f["water_m3"]), "budget": float(f["budget"]),
        "weather": {"live": live, "source": meta.get("source", ""), "fetched_at": meta.get("fetched_at", ""), "tmax": float(today.tmax), "tmin": float(today.tmin),
                    "rain": float(today.rain_mm), "week_rain": float(fc.rain_mm.sum()), "hottest": float(fc.tmax.max()), "coldest": float(fc.tmin.min()), "days": int(len(fc)),
                    "imputed_rows": int(meta["quality"]["imputed_rows"]), "rh_available": bool(meta["quality"]["rh_available"])},
        "risks": [{"key": k, "name": r["name"], "score": float(r["score"]), "category": r["category"], "action": r["action"]}
                  for k, r in risks.items() if k not in ("overall", "features")],
        "overall": {"driver": risks["overall"]["driver"], "score": float(risks["overall"]["score"]), "category": risks["overall"]["category"]},
        "irr": {"needed": bool(irr.get("needed")), "postpone": bool(irr.get("postpone")), "volume_m3": float(irr.get("volume_m3", 0) or 0), "gross_mm": float(irr.get("gross_mm", 0) or 0),
                "decision": irr.get("decision", ""), "estimated": bool(irr.get("estimated", True))},
        "alerts": [a["message"] for a in ctx.get("alerts", [])][:6],
        "optim": None, "comparison": None,
    }
    opt = state.get("optim")
    if opt:
        base = None
        table = state.get("compare")
        try:
            row = table[table.strategy.str.startswith("Baseline")].iloc[0]
            base = _metrics(row)
        except Exception:
            base = None
        facts["optim"] = {"priority": opt.get("priority", "balanced"), "allocation": {c: float(a) for c, a in opt["allocation"].items() if a > 0.01},
                          "metrics": _metrics(opt["metrics"]), "baseline": base}
    cmp_ = (state.get("unified") or {}).get("comparison")
    if cmp_ and cmp_.get("ok"):
        facts["comparison"] = cmp_
    return facts


def external_payload(facts):
    """What an external LLM may see: no location, no alerts text, farm figures rounded. Crop/stage/risk/irrigation/optimiser results are needed to answer."""
    p = {k: v for k, v in facts.items() if k not in ("alerts", "comparison", "weather", "stage")}
    p["area_acres"] = round(facts["area_acres"] * 2) / 2
    p["budget"] = round(facts["budget"] / 5000) * 5000
    p["water_m3"] = round(facts["water_m3"] / 100) * 100
    w = facts["weather"]
    p["weather"] = {"live_data": w["live"], "today_tmax": round(w["tmax"]), "today_tmin": round(w["tmin"]), "today_rain_mm": round(w["rain"]), "week_rain_mm": round(w["week_rain"]),
                    "hottest_day_c": round(w["hottest"])}
    s = facts["stage"]
    p["stage"] = {k: s.get(k) for k in ("sown", "pct", "duration", "days_to_next", "days_to_harvest", "days_to_sowing") if k in s}
    if facts["comparison"]:
        c = facts["comparison"]
        p["drought_or_excess_planning_scenario"] = {"original_under_risk": _metrics(c["original_under_risk"]), "risk_aware": _metrics(c["risk_aware"]),
                                                    "water_normal_m3": round(c["water0"]), "water_risk_m3": round(c["water1"])}
    return p
