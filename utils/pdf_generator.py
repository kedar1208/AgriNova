"""Premium farming report PDF (reportlab only). Backward compatible: build_report(cfg, meta, risks, irr, alerts, optim, compare_df) still works;
the optional `extras` dict adds crop/stage, weather table, prioritised actions, data quality and the AgroCast-informed comparison.
Every section is optional so partial sessions still produce a report. Data-provenance labels and limitations are always included."""
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether

EMERALD, FOREST, GOLD, MIST, INK = colors.HexColor("#0b3d2a"), colors.HexColor("#14532d"), colors.HexColor("#c79a2b"), colors.HexColor("#f1f8f3"), colors.HexColor("#1b2a22")
CATC = {"Low": "#4f9a63", "Moderate": "#c79a2b", "High": "#d27a2c", "Severe": "#b04030"}
W = A4[0] - 72
SS = getSampleStyleSheet()
BODY = ParagraphStyle("b", parent=SS["BodyText"], fontName="Helvetica", fontSize=9, leading=12.5, textColor=INK)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=7.5, leading=10, textColor=colors.HexColor("#4a5d52"))
CELL = ParagraphStyle("c", parent=BODY, fontSize=8, leading=10.5)
H = ParagraphStyle("h", parent=SS["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=FOREST, spaceBefore=12, spaceAfter=5)
KL = ParagraphStyle("kl", parent=SMALL, fontName="Helvetica-Bold", textColor=colors.HexColor("#6b7d72"), fontSize=7)
KV = ParagraphStyle("kv", parent=BODY, fontName="Helvetica-Bold", fontSize=13, leading=15, textColor=FOREST)


def P(t, st=BODY):
    return Paragraph(escape(str(t)), st)


def rs(x):
    return f"-Rs {abs(x):,.0f}" if x < 0 else f"Rs {x:,.0f}"


def _tbl(data, widths=None, cat_col=None):
    t = Table(data, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), FOREST), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
          ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfdcd3")),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, MIST]), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 6)]
    if cat_col is not None:
        for i, row in enumerate(data[1:], 1):
            c = CATC.get(str(row[cat_col]))
            if c:
                st += [("TEXTCOLOR", (cat_col, i), (cat_col, i), colors.HexColor(c)), ("FONTNAME", (cat_col, i), (cat_col, i), "Helvetica-Bold")]
    t.setStyle(TableStyle(st))
    return t


def _kpis(items):
    """Row of tiles: [(label, value), ...]."""
    n = len(items)
    cells = [[[P(l.upper(), KL), P(v, KV)] for l, v in items]]
    t = Table(cells, colWidths=[W / n] * n)
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfdcd3")), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cfdcd3")), ("BACKGROUND", (0, 0), (-1, -1), MIST),
                           ("LINEABOVE", (0, 0), (-1, 0), 2, GOLD), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7), ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
    return t


def _bar(pct, label):
    pct = max(0, min(100, pct))
    if pct in (0, 100):
        t = Table([[""]], colWidths=[W], rowHeights=[9])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), FOREST if pct else colors.HexColor("#dfe9e2"))]))
    else:
        t = Table([["", ""]], colWidths=[W * pct / 100, W * (100 - pct) / 100], rowHeights=[9])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), FOREST), ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#dfe9e2"))]))
    return [t, P(label, SMALL)]


def _page(canvas, doc):
    canvas.saveState()
    if doc.page == 1:
        canvas.setFillColor(EMERALD); canvas.rect(0, A4[1] - 92, A4[0], 92, stroke=0, fill=1)
        canvas.setFillColor(GOLD); canvas.rect(0, A4[1] - 95, A4[0], 3, stroke=0, fill=1)
        canvas.setFillColor(colors.white); canvas.setFont("Helvetica-Bold", 23); canvas.drawString(36, A4[1] - 50, "AGRI NOVA")
        canvas.setFont("Helvetica", 10.5); canvas.drawString(36, A4[1] - 68, "Farm Decision Intelligence Report")
        canvas.setFillColor(colors.HexColor("#f4c25b")); canvas.setFont("Helvetica-Oblique", 9); canvas.drawRightString(A4[0] - 36, A4[1] - 50, "Predict. Protect. Optimize. Grow.")
        canvas.setFillColor(colors.HexColor("#cfe8d8")); canvas.setFont("Helvetica", 8.5); canvas.drawRightString(A4[0] - 36, A4[1] - 68, f"Generated {datetime.now():%d %b %Y, %H:%M}")
    else:
        canvas.setStrokeColor(GOLD); canvas.setLineWidth(1.2); canvas.line(36, A4[1] - 30, A4[0] - 36, A4[1] - 30)
        canvas.setFillColor(FOREST); canvas.setFont("Helvetica-Bold", 8); canvas.drawString(36, A4[1] - 24, "AGRI NOVA")
    canvas.setFillColor(colors.HexColor("#6b7d72")); canvas.setFont("Helvetica", 7)
    canvas.drawString(36, 22, "Decision support: heuristic risk indicators and simulated scenarios - not a forecast, guarantee or professional agronomic advice.")
    canvas.drawRightString(A4[0] - 36, 22, f"Page {doc.page}")
    canvas.restoreState()


def _cfg_rows(cfg):
    pretty = {"state": "State", "district": "District", "crop": "Crop", "area_acres": "Farm area", "sowing_date": "Sowing date", "soil": "Soil type", "irrigation": "Irrigation method",
              "water_m3": "Season irrigation water", "budget": "Budget"}
    fmt = {"area_acres": lambda v: f"{float(v):.1f} acres", "water_m3": lambda v: f"{float(v):,.0f} m3", "budget": lambda v: rs(float(v)),
           "sowing_date": lambda v: v.strftime("%d %b %Y") if hasattr(v, "strftime") else str(v)}
    rows = [[P("Item", CELL), P("Value", CELL)]]
    for k in pretty:
        if k in cfg:
            rows.append([P(pretty[k], CELL), P(fmt.get(k, str)(cfg[k]), CELL)])
    rows.append([P("Soil moisture", CELL), P("Measured by farmer" if cfg.get("measured_pct") is not None else "ESTIMATED by water-balance model", CELL)])
    return rows


def build_report(cfg, weather_meta, risks=None, irrigation=None, alerts=None, optim=None, compare_df=None, extras=None) -> bytes:
    x = extras or {}
    buf = BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=108, bottomMargin=40, title="AGRI NOVA Farm Decision Report", author="AGRI NOVA")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(36, 40, W, A4[1] - 40 - 108, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=_page)])
    # later pages have a thin header: reuse the frame; the first-page band is drawn by _page
    el, n = [], [0]

    def head(t):
        n[0] += 1
        el.append(Paragraph(f"{n[0]}. {escape(t)}", H))

    # --- headline KPIs ---
    tiles = [("Crop", str(cfg.get("crop", "-")))]
    if x.get("stage_label"):
        tiles.append(("Growth stage", x["stage_label"].split("/")[0]))
    if risks:
        o = risks["overall"]; tiles.append(("Top weather risk", f"{o['category']} ({o['score']:.0f})"))
    if optim and optim.get("metrics"):
        tiles.append(("Resilience", f"{optim['metrics']['resilience']:.0f}/100"))
    el.append(_kpis(tiles))
    if weather_meta.get("source") and weather_meta["source"] != "open-meteo":
        el += [Spacer(1, 6), P("This report uses SAMPLE (synthetic) weather - for demonstration only, not for real farm decisions.", ParagraphStyle("w", parent=BODY, textColor=colors.HexColor("#b04030"), fontName="Helvetica-Bold"))]

    head("Farm configuration and location")
    el.append(_tbl(_cfg_rows(cfg), [150, W - 150]))

    if x.get("stage_label") is not None and x.get("duration"):
        head("Crop and growth stage")
        el.append(P(f"{cfg.get('crop', 'Crop')} - stage: {x['stage_label']}" + (f", day {x['das']} of about {x['duration']}." if x.get("das", -1) >= 0 else f". Sowing is {-x['das']} days away.")))
        if x.get("das", -1) >= 0:
            el += _bar(100 * x["das"] / x["duration"], "Season progress (generic split of crop duration; not a crop-specific phenology model)")

    head("Weather summary")
    dq = x.get("dq")
    el.append(P(f"Source: {dq['source'] if dq else weather_meta.get('source', 'n/a')}. " + (f"Last update: {dq['fetched']}. Data quality: {dq['rating']}. " if dq else "") + (weather_meta.get("error") or "")))
    if dq:
        el.append(P(" ".join(dq["notes"]), SMALL))
    if x.get("sm"):
        el += [Spacer(1, 3), P(x["sm"]["headline"])]
    d = x.get("daily")
    if d is not None and len(d):
        rows = [["Day", "High C", "Low C", "Rain mm", "Soil water %"]] + [[r.date.strftime("%a %d %b") if hasattr(r.date, "strftime") else str(r.date), f"{r.tmax:.0f}", f"{r.tmin:.0f}", f"{r.rain_mm:.0f}",
                                                                          "-" if r.soil_pct != r.soil_pct else f"{r.soil_pct:.0f}"] for r in d.itertuples()]
        el += [Spacer(1, 4), _tbl(rows, [110, 80, 80, 80, 100])]

    if risks:
        head("Climate-risk assessment (AgroCast, next 7 days)")
        data = [["Hazard", "Score", "Level", "Main factors", "Next step"]]
        for k, r in risks.items():
            if k in ("overall", "features"):
                continue
            data.append([P(r["name"], CELL), f"{r['score']:.0f}", r["category"], P("; ".join(dd for dd, _ in r["factors"][:2]) or "-", CELL), P(r["action"], CELL)])
        el += [_tbl(data, [88, 34, 52, W - 88 - 34 - 52 - 150, 150], cat_col=2), P("Scores rank weather exposure for this crop and stage. They are heuristics, not probabilities of crop loss or disease.", SMALL)]

    if irrigation:
        head("Irrigation recommendation")
        el.append(P(irrigation["decision"]))
        if irrigation.get("reasons"):
            el.append(P(" ".join(irrigation["reasons"]), SMALL))
        if irrigation.get("volume_m3"):
            el.append(P(f"Per round: about {irrigation['volume_m3']:,.0f} m3 ({irrigation.get('gross_mm', 0):.0f} mm gross)." + f" Season water entered: {cfg.get('water_m3', 0):,.0f} m3."))

    recs = x.get("recs")
    if recs:
        head("Recommended actions (highest priority first)")
        for r in recs[:6]:
            rows = [[P(f"P{r['priority']} - {r['title']} ({r['category']})", ParagraphStyle("t", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)), ""],
                    [P("What", CELL), P(r["what"], CELL)], [P("Why it matters", CELL), P(r["why"], CELL)], [P("What to do", CELL), P(r["do"], CELL)], [P("When", CELL), P(r["when"], CELL)]]
            t = Table(rows, colWidths=[80, W - 80])
            t.setStyle(TableStyle([("SPAN", (0, 0), (1, 0)), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(CATC.get(r["category"], "#4f9a63"))), ("BACKGROUND", (0, 1), (0, -1), MIST),
                                   ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"), ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfdcd3")), ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#e3ece6")),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
            el += [KeepTogether([t, Spacer(1, 5)])]
    elif alerts:
        head("Early-warning alerts")
        el += [P(f"[{a['level'].upper()}] {a['message']} ({a['basis']})") for a in alerts]

    if optim and optim.get("metrics"):
        m = optim["metrics"]
        head("Crop allocation and financial estimates (FarmOptimizer, SIMULATED scenarios)")
        alloc = {c: a for c, a in optim["allocation"].items() if a > 0.01}
        tot = sum(alloc.values()) or 1
        el.append(P(f"Priority: {optim.get('priority', 'balanced')}."))
        el += [Spacer(1, 3), _tbl([["Crop", "Acres", "Share"]] + [[c, f"{a:.1f}", f"{a / tot * 100:.0f}%"] for c, a in sorted(alloc.items(), key=lambda kv: -kv[1])], [200, 100, 100]), Spacer(1, 6)]
        el.append(_kpis([("Expected profit", rs(m["expected_profit"])), ("Worst-10% avg", rs(m["cvar"])), ("Chance of loss", f"{m['p_loss'] * 100:.0f}%"), ("Investment", rs(m["investment"])) if "investment" in m else ("Resilience", f"{m['resilience']:.0f}/100")]))
        el += [Spacer(1, 5), _tbl([["Metric", "Value"], ["5th percentile profit", rs(m["p5_profit"])], ["Worst simulated profit", rs(m["worst_profit"])], ["Expected extra irrigation", f"{m['expected_water_m3']:,.0f} m3"],
                                   ["Yield variability (CV)", f"{m['yield_cv']:.2f}"], ["Resilience score", f"{m['resilience']:.0f}/100"]], [250, 150])]

    if compare_df is not None and len(compare_df):
        head("Optimization comparison")
        base = compare_df[compare_df.strategy.str.startswith("Baseline")]
        if len(base) and optim and optim.get("metrics"):
            b, m = base.iloc[0], optim["metrics"]
            el += [P("Baseline = same land split evenly across the selected crops. Both are scored on the same simulated seasons."), Spacer(1, 3),
                   _tbl([["Metric", "Baseline", "Optimized", "Change"], ["Expected profit", rs(b.expected_profit), rs(m["expected_profit"]), rs(m["expected_profit"] - b.expected_profit)],
                         ["Worst-10% average", rs(b.cvar), rs(m["cvar"]), rs(m["cvar"] - b.cvar)], ["Chance of loss", f"{b.p_loss * 100:.0f}%", f"{m['p_loss'] * 100:.0f}%", f"{(m['p_loss'] - b.p_loss) * 100:+.0f} pts"],
                         ["Resilience", f"{b.resilience:.0f}", f"{m['resilience']:.0f}", f"{m['resilience'] - b.resilience:+.0f}"]], [130, 120, 120, 120]), Spacer(1, 6)]
        d = [["Strategy", "Exp. profit", "CVaR10", "P(loss)", "Resilience"]] + [[r.strategy, f"{r.expected_profit:,.0f}", f"{r.cvar:,.0f}", f"{r.p_loss * 100:.0f}%", f"{r.resilience:.0f}"] for r in compare_df.itertuples()]
        el.append(_tbl(d, [190, 85, 85, 60, 60]))

    c = x.get("comparison")
    if c and c.get("ok"):
        head("Risk-aware plan (AgroCast-informed what-if)")
        k, r = c["original_under_risk"], c["risk_aware"]
        el += [P("; ".join(c["adj"]["rationale"]) + " Scenario sizes are stated assumptions, not measured effects."), Spacer(1, 3),
               _tbl([["", "Original plan, risk happens", "Risk-aware plan"], ["Expected profit", rs(k["expected_profit"]), rs(r["expected_profit"])], ["Worst-10% average", rs(k["cvar"]), rs(r["cvar"])],
                     ["Chance of loss", f"{k['p_loss'] * 100:.0f}%", f"{r['p_loss'] * 100:.0f}%"], ["Expected extra water", f"{k['expected_water_m3']:,.0f} m3", f"{r['expected_water_m3']:,.0f} m3"]], [150, 160, 160]),
               P(f"Irrigation water assumed: {c['water0']:,.0f} m3 normally, {c['water1']:,.0f} m3 in the risk scenario.", SMALL)]

    head("Assumptions and limitations")
    for t in ["Crop parameters, prices and costs are illustrative planning defaults (FAO-style Kc/Ky; approximate price levels) and must be verified locally.",
              "Risk scores are transparent heuristics, not validated probabilities of loss. The fungal indicator is a weather heuristic, not a disease forecast.",
              "FarmOptimizer results come from simulated seasons (CVaR linear programme); they are not weather forecasts or yield guarantees. Not modelled: price volatility, pests, labour, sowing-date shifts.",
              "Any layout or plot view in the app is illustrative, not satellite imagery or GPS field data.",
              "Consult your local agriculture officer or Krishi Vigyan Kendra (KVK) before major decisions."]:
        el.append(P("- " + t))
    doc.build(el)
    return buf.getvalue()
