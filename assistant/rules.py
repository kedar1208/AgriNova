"""Offline rule-based explainer. Every number in an answer is read from `facts` (see assistant.context); nothing is recalculated and no model is involved."""
from datetime import datetime
from utils.helpers import inr
from engine.unified_intelligence import explain_comparison
from .i18n import T, CAT, HAZARD, CROP, STAGE, PRIORITY, GENERIC_ACTION, INTENTS, HAZARD_WORDS


def detect_intent(question):
    q = question.lower()
    best, best_n = None, 0
    for intent, words in INTENTS.items():          # dict order breaks ties (specific topics come first)
        n = sum(1 for w in words if w in q)
        if n > best_n:
            best, best_n = intent, n
    return best


def _hazard_focus(question):
    q = question.lower()
    hits = [(sum(w in q for w in ws), k) for k, ws in HAZARD_WORDS.items()]
    n, k = max(hits)
    return k if n else None


def _money(x, lang):
    s = inr(x)
    return s.replace("Rs ", "₹") if lang != "en" else s


def _crop(name, lang):
    return CROP.get(lang, {}).get(name, name)


def _hz(key, lang, fallback=""):
    return HAZARD[lang].get(key, fallback or key)


def _action(r, lang):
    return r["action"] if lang == "en" else GENERIC_ACTION[lang][r["category"]]


def _sample(facts, t):
    return "" if facts["weather"]["live"] else "\n\n_" + t["sample_note"] + "_"


def _summary(f, lang, t):
    o = f["overall"]
    driver = next((_hz(r["key"], lang) for r in f["risks"] if r["name"] == o["driver"]), o["driver"])
    cat = CAT[lang][o["category"]]
    crop = _crop(f["crop"], lang)
    head = (t["summary"].format(crop=crop, stage=STAGE[lang][f["stage_idx"]], das=f["das"], driver=driver, cat=cat, score=o["score"]) if f["stage_idx"] >= 0 else
            t["summary_unsown"].format(crop=crop, d=-f["das"], driver=driver, cat=cat, score=o["score"]))
    return head + "\n\n" + _irrigation(f, lang, t, short=True)


def _weather(f, lang, t):
    w = f["weather"]
    out = [t["wx_today"].format(tmax=w["tmax"], tmin=w["tmin"], rain=w["rain"]), t["wx_week"].format(days=w["days"], rain=w["week_rain"], hot=w["hottest"], cold=w["coldest"])]
    if w["live"]:
        try:
            when = datetime.fromisoformat(w["fetched_at"]).strftime("%d %b %Y, %H:%M")
        except Exception:
            when = "-"
        out.append(t["wx_live"].format(when=when))
    else:
        out.append(t["wx_sample"])
    if w["imputed_rows"]:
        out.append(t["wx_gaps"].format(n=w["imputed_rows"]))
    if not w["rh_available"]:
        out.append(t["wx_norh"])
    return "\n\n".join(out)


def _risks(f, lang, t, question):
    focus = _hazard_focus(question)
    if focus:
        r = next((r for r in f["risks"] if r["key"] == focus), None)
        if r:
            return t["risk_focus"].format(name=_hz(r["key"], lang), cat=CAT[lang][r["category"]], score=r["score"], action=_action(r, lang))
    rows = sorted((r for r in f["risks"] if r["score"] >= 25), key=lambda r: -r["score"])
    if not rows:
        return t["risk_none"]
    lines = [t["risk_head"]] + [t["risk_line"].format(name=_hz(r["key"], lang), cat=CAT[lang][r["category"]], score=r["score"]) for r in rows]
    top = rows[0]
    lines.append("\n" + t["risk_focus"].format(name=_hz(top["key"], lang), cat=CAT[lang][top["category"]], score=top["score"], action=_action(top, lang)))
    return "\n".join(lines)


def _irrigation(f, lang, t, short=False):
    i = f["irr"]
    if i["postpone"]:
        s = t["irr_post"]
    elif not i["needed"]:
        s = t["irr_none"]
    else:
        s = t["irr_needed"].format(vol=i["volume_m3"], mm=i["gross_mm"])
        if i["volume_m3"] > 0 and f["water_m3"] > 0:
            s += " " + t["irr_cover"].format(w=f["water_m3"], r=f["water_m3"] / i["volume_m3"])
    if lang == "en" and i["decision"] and not short:
        s += "\n\n" + t["irr_stage"].format(d=i["decision"])
    if not short:
        s += "\n\n" + (t["irr_est"] if i["estimated"] else t["irr_meas"])
    return s


def _stage(f, lang, t):
    s, crop = f["stage"], _crop(f["crop"], lang)
    if not s.get("sown"):
        return t["stage_unsown"].format(crop=crop, d=s["days_to_sowing"])
    out = t["stage_sown"].format(crop=crop, stage=STAGE[lang][f["stage_idx"]], das=s["das"], dur=s["duration"], pct=s["pct"])
    if s.get("days_to_next"):
        out += t["stage_next"].format(d=s["days_to_next"])
    if s.get("days_to_harvest") is not None:
        out += t["stage_harv"].format(d=s["days_to_harvest"])
    if lang == "en" and s.get("sensitive_to"):
        out += t["stage_sens"].format(s=", ".join(s["sensitive_to"]))
    return out + "\n\n_" + t["stage_note"] + "_"


def _plan(f, lang, t):
    o = f["optim"]
    if not o:
        return t["plan_none"]
    area = sum(o["allocation"].values()) or 1
    farm_area = o["metrics"].get("acres_used", area)
    lines = [t["plan_head"].format(prio=PRIORITY[lang].get(o["priority"], o["priority"]), area=farm_area)]
    for c, a in sorted(o["allocation"].items(), key=lambda kv: -kv[1]):
        lines.append(t["plan_line"].format(crop=_crop(c, lang), acres=a, share=a / area * 100))
    return "\n".join(lines)


def _budget(f, lang, t):
    out = t["budget_text"].format(budget=_money(f["budget"], lang))
    o = f["optim"]
    if not o:
        return out + " " + t["budget_noplan"]
    inv = o["metrics"].get("investment", 0)
    pct = inv / f["budget"] * 100 if f["budget"] > 0 else 0
    return out + " " + t["budget_plan"].format(inv=_money(inv, lang), pct=pct, used=o["metrics"].get("acres_used", 0), w=f["water_m3"])


def _optim(f, lang, t):
    o = f["optim"]
    if not o:
        return t["plan_none"]
    m = o["metrics"]
    out = [t["opt_head"].format(prio=PRIORITY[lang].get(o["priority"], o["priority"])),
           t["opt_body"].format(ep=_money(m["expected_profit"], lang), cvar=_money(m["cvar"], lang), pl=m["p_loss"] * 100, res=m["resilience"], w=m["expected_water_m3"])]
    b = o.get("baseline")
    if b:
        out.append(t["opt_base"].format(d_ep=_money(m["expected_profit"] - b["expected_profit"], lang), d_cvar=_money(m["cvar"] - b["cvar"], lang)))
    c = f.get("comparison")
    if c:
        if lang == "en":
            txt = explain_comparison(c)
        else:
            k, r = c["original_under_risk"], c["risk_aware"]
            txt = t["opt_cmp"].format(k_ep=_money(k["expected_profit"], lang), k_cvar=_money(k["cvar"], lang), r_ep=_money(r["expected_profit"], lang), r_cvar=_money(r["cvar"], lang),
                                      w0=c["water0"], w1=c["water1"])
        out.append(t["opt_cmp"].format(txt=txt) if lang == "en" else txt)
    out.append("_" + t["opt_limits"] + "_")
    return "\n\n".join(out)


def _report(f, lang, t):
    return t["report_text"] + " " + (t["report_yes"] if f["optim"] else t["report_no"])


def answer(question, facts, lang="en"):
    """Returns {'text', 'intent'}. Unknown questions get a short, honest 'what I can explain' message instead of a guess."""
    t = T[lang]
    intent = detect_intent(question)
    body = {"summary": lambda: _summary(facts, lang, t), "weather": lambda: _weather(facts, lang, t), "risk": lambda: _risks(facts, lang, t, question),
            "irrigation": lambda: _irrigation(facts, lang, t), "stage": lambda: _stage(facts, lang, t), "plan": lambda: _plan(facts, lang, t),
            "budget": lambda: _budget(facts, lang, t), "optim": lambda: _optim(facts, lang, t), "report": lambda: _report(facts, lang, t)}.get(intent)
    if body is None:
        return {"text": t["fallback"], "intent": None}
    text = body()
    if intent in ("weather", "risk", "summary", "irrigation"):
        text += _sample(facts, t)
    return {"text": text, "intent": intent}
