"""UI helpers: a thin compatibility layer over Streamlit plus small HTML components (hero, KPI cards, alerts...).
`use_container_width` was replaced by `width="stretch"` in newer Streamlit releases; try the new form, fall back.
All HTML strings are built on ONE line - Markdown treats indented/blank-line-separated HTML as a code block."""
import inspect
from html import escape as esc
import streamlit as st

RING = {"Low": "#7fc88f", "Moderate": "#ecc24f", "High": "#f19a4a", "Severe": "#ee7561"}   # lighter tones for the dark hero
BAR = {"Low": "#4f9a63", "Moderate": "#c79a2b", "High": "#d27a2c", "Severe": "#b04030"}
STAGE_SHORT = ["Establish", "Vegetative", "Flowering", "Filling", "Harvest"]


def _stretch(fn, *a, **k):
    try:
        if "width" in inspect.signature(fn).parameters:
            return fn(*a, width="stretch", **k)
    except Exception:
        pass
    return fn(*a, use_container_width=True, **k)


PLOT_CONFIG = {"displaylogo": False, "responsive": True, "displayModeBar": "hover",
               "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}


def chart(fig, **k):
    """Every chart goes through here: same toolbar, responsive width, and a legend that sits below the plot so it never squeezes narrow screens."""
    try:
        fig.update_layout(autosize=True, margin=dict(l=10, r=10, t=52, b=10),
                          legend=dict(orientation="h", y=-0.22, yanchor="top", x=0, bgcolor="rgba(255,255,255,0)", font=dict(size=12)),
                          title_font=dict(size=16))
    except Exception:
        pass
    k.setdefault("config", PLOT_CONFIG)
    return _stretch(st.plotly_chart, fig, **k)


def tidy(df, digits=2):
    """Display copy of a table: floats rounded, no raw NaN text. The original frame is left untouched."""
    try:
        d = df.copy()
        for c in d.select_dtypes("float").columns:
            d[c] = d[c].round(digits)
        return d
    except Exception:
        return df


def table(df, **k):
    d = tidy(df)
    k.setdefault("height", min(38 + 35 * len(d), 460))
    return _stretch(st.dataframe, d, hide_index=True, **k)


def editor(df, **k):
    return _stretch(st.data_editor, df, hide_index=True, **k)


def html(s):
    st.markdown(s, unsafe_allow_html=True)


def page_head(title, sub="", eyebrow=""):
    eb = f'<div class="eb">{esc(eyebrow)}</div>' if eyebrow else ""
    html(f'<div class="page-head">{eb}<div class="t">{esc(title)}</div>' + (f'<div class="s">{esc(sub)}</div>' if sub else "") + "</div>")


def section(title):
    html(f'<div class="sec">{esc(title)}</div>')


def empty_state(title, text="", icon="🌱"):
    """Friendly placeholder for a page/section that has nothing to show yet."""
    html(f'<div class="empty"><div class="ei">{esc(icon)}</div><div class="et">{esc(title)}</div>' + (f'<div class="ed">{esc(text)}</div>' if text else "") + "</div>")


def callout(kind, title, text="", hint=""):
    """Error / warning / info box with an optional next step. kind: error | warn | info | ok."""
    icon = {"error": "⛔", "warn": "⚠️", "info": "ℹ️", "ok": "✅"}.get(kind, "ℹ️")
    cls = "" if kind == "error" else f" {kind}"
    role = "alert" if kind in ("error", "warn") else "status"
    html(f'<div class="callout{cls}" role="{role}"><div class="ci" aria-hidden="true">{icon}</div><div><div class="ct">{esc(title)}</div>' + (f'<div class="cd">{esc(text)}</div>' if text else "")
         + (f'<div class="ch">{esc(hint)}</div>' if hint else "") + "</div></div>")


def insights(items):
    """Cards linking a weather-risk indicator to the irrigation advice and to how FarmOptimizer treats it."""
    if not items:
        return '<div class="empty"><div class="ei">✅</div><div class="et">No elevated weather risk this week</div><div class="ed">Nothing needs to be passed to the planner. FarmOptimizer can still be used for season planning.</div></div>'
    out = []
    for i in items:
        rows = "".join(f"<li>{esc(x)}</li>" for x in i["indicators"])
        irr = f'<div class="ir"><b>Irrigation</b>{esc(i["irrigation"])}</div>' if i["irrigation"] else ""
        out.append(f'<div class="ins {esc(i["level"])}"><div class="ih"><span class="lvl {esc(i["category"].lower())}">{esc(i["category"])}</span><b>{esc(i["title"])}</b><span class="isc">{i["score"]:.0f}/100</span></div>'
                   f'<ul>{rows}</ul><div class="ir"><b>Do</b>{esc(i["action"])}</div>{irr}<div class="ip{" on" if i["affects_optimizer"] else ""}"><b>Planner</b>{esc(i["planning"])}</div></div>')
    return '<div class="insg">' + "".join(out) + "</div>"


def source_strip(dq):
    """Data-source pills: source, last update, quality rating, forecast coverage."""
    cls = {"Good": "", "Fair": " warn", "Limited": " bad"}[dq["rating"]]
    live = "" if dq["live"] else " warn"
    return ('<div class="srcs">' f'<span class="spill{live}"><i></i>{esc(dq["source"])}</span>' f'<span class="spill"><i></i>Last weather update: {esc(dq["fetched"])}</span>'
            f'<span class="spill{cls}"><i></i>Data quality: {esc(dq["rating"])}</span>' f'<span class="spill"><i></i>{dq["observed_days"]} observed + {dq["forecast_days"]} forecast days</span></div>')


def stage_card(sp, crop_name):
    """Crop growth stage indicator: proportional stage bar with a marker for today, and what the stage is sensitive to."""
    if not sp["sown"]:
        return (f'<div class="stage-card"><div class="sc-h"><b>{esc(crop_name)}</b> · not sown yet</div><div class="sc-s">Sowing in {sp["days_to_sowing"]} day(s). Growth-stage risk weighting starts at sowing.</div></div>')
    b = sp["bounds_days"]; dur = max(sp["duration"], 1)
    segs = "".join(f'<div class="ss{" done" if i < sp["idx"] else " now" if i == sp["idx"] else ""}" style="flex:{max(b[i + 1] - b[i], 1)}"><span>{esc(STAGE_SHORT[i])}</span></div>' for i in range(5))
    nxt = f' · next stage in ~{sp["days_to_next"]} day(s)' if sp.get("days_to_next") is not None else " · harvest window"
    return (f'<div class="stage-card"><div class="sc-h"><b>{esc(crop_name)}</b> · {esc(sp["stage"])}<span class="sc-d">Day {sp["das"]} of ~{sp["duration"]}</span></div>'
            f'<div class="sbar">{segs}<i class="mk" style="left:{min(sp["das"] / dur * 100, 100):.1f}%"></i></div>'
            f'<div class="sc-s">~{sp["days_to_harvest"]} day(s) to expected harvest{nxt}. Most sensitive now to: <b>{esc(" and ".join(sp["sensitive_to"]))}</b>. Generic stage split of the crop duration - not a phenology model.</div></div>')


def reco_cards(recs):
    """Prioritised recommendations, each answering WHAT / WHY / DO / WHEN."""
    out = []
    for r in recs:
        out.append(f'<div class="reco {esc(r["level"])}"><div class="rh"><span class="pr">P{r["priority"]}</span><b>{esc(r["title"])}</b><span class="lvl {esc(r["category"].lower())}">{esc(r["label"])}</span></div>'
                   f'<dl><dt>What</dt><dd>{esc(r["what"])}</dd><dt>Why it matters</dt><dd>{esc(r["why"])}</dd><dt>What to do</dt><dd>{esc(r["do"])}</dd><dt>When</dt><dd>{esc(r["when"])}</dd></dl>'
                   f'<div class="basis">{esc(r["basis"])}</div></div>')
    return '<div class="recos">' + "".join(out) + "</div>"


def skeleton(n=4):
    """Shimmering placeholder cards, for use inside st.empty() while something loads."""
    return '<div style="display:grid;grid-template-columns:repeat(%d,1fr);gap:14px">' % n + '<div class="skeleton"></div>' * n + "</div>"


def footer(text="Heuristic risk indicators and simulated scenarios - decision support, not a guarantee."):
    html(f'<div class="foot"><b>AgriNova</b> · Predict. Protect. Optimize. Grow. · {esc(text)}</div>')


def kpi(label, value, sub="", color=None):
    style = f' style="color:{color}"' if color else ""
    return f'<div class="kpi"><div class="lab">{esc(label)}</div><div class="val"{style}>{esc(str(value))}</div><div class="sub">{esc(sub)}</div></div>'


# kept for older callers
stat = kpi


def chips(items):
    return '<div class="chips">' + "".join(f'<div class="chip"><span>{esc(k)}</span>{esc(v)}</div>' for k, v in items) + "</div>"


def note(level, text, basis=""):
    b = f'<div class="basis">{esc(basis)}</div>' if basis else ""
    tag = {"ok": "all clear", "info": "note", "warning": "watch", "critical": "act now"}.get(level, level)
    return f'<div class="alert {esc(level)}" role="{"alert" if level == "critical" else "status"}"><span class="tag">{tag}</span><div>{esc(text)}{b}</div></div>'


CIRC_BIG, CIRC_SMALL = 2 * 3.14159 * 50, 2 * 3.14159 * 30


def hero(crop, stage_idx, stage_label, das, location, exact, source_live, headline, score, category):
    pill_src = ('<span class="pill"><span class="dot"></span>Live weather · Open-Meteo</span>' if source_live
                else '<span class="pill warn"><span class="dot"></span>Sample data (not live)</span>')
    pill_loc = f'<span class="pill{"" if exact else " warn"}"><span class="dot"></span>{esc(location)}{"" if exact else " · approximate"}</span>'
    sub = f"Day {das} · {esc(stage_label)}" if das >= 0 else f"Sowing in {-das} day{'s' if das != -1 else ''}"
    track = "".join(f'<div><div class="seg {"done" if i < stage_idx else "now" if i == stage_idx else ""}"></div>'
                    f'<div class="lbl{" now" if i == stage_idx else ""}">{s}</div></div>' for i, s in enumerate(STAGE_SHORT))
    col = RING[category]
    ring = (f'<div class="ring"><svg viewBox="0 0 120 120" width="132" height="132" role="img" aria-label="Overall weather risk {score:.0f} out of 100, {esc(category)}"><circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,.16)" stroke-width="10"/>'
            f'<circle class="rf" cx="60" cy="60" r="50" fill="none" stroke="{col}" stroke-width="10" stroke-linecap="round" stroke-dasharray="{CIRC_BIG * score / 100:.1f} {CIRC_BIG:.1f}" '
            f'style="--d:{CIRC_BIG * score / 100:.1f};--c:{CIRC_BIG:.1f}" transform="rotate(-90 60 60)"/>'
            f'<text x="60" y="68" text-anchor="middle" font-size="34" font-weight="800" fill="#fff" font-family="Bricolage Grotesque, Segoe UI, sans-serif">{score:.0f}</text></svg>'
            f'<div class="cat" style="color:{col}">{esc(category)} risk</div><div class="cap">out of 100</div></div>')
    return (f'<div class="hero"><i class="cloud c1"></i><i class="cloud c2"></i><div class="hbody"><div class="pills">{pill_src}{pill_loc}</div><div class="crop">{esc(crop)}</div>'
            f'<div class="stage">{sub}</div><div class="track">{track}</div><div class="headline">{headline}</div></div>{ring}</div>')


def _icon(tmax, rain, heat_c, heavy_mm):
    """Small weather glyph for a forecast day: storm / shower / hot / part-cloud / clear."""
    sun = '<circle cx="24" cy="24" r="9" fill="#f4b73e"/><g stroke="#f4b73e" stroke-width="3" stroke-linecap="round"><path d="M24 7v4M24 37v4M7 24h4M37 24h4M12 12l3 3M33 33l3 3M36 12l-3 3M15 33l-3 3"/></g>'
    cloud = '<path d="M13 37a8 8 0 0 1 1-16 11 11 0 0 1 21 3 6.5 6.5 0 0 1-1 13z" fill="#cfe1ee"/><path d="M15 23a11 11 0 0 1 20 1" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round" opacity=".8"/>'
    if rain >= max(heavy_mm, 10):
        body = cloud + '<g stroke="#2f7fc6" stroke-width="3" stroke-linecap="round"><path d="M16 40l-2 5M24 40l-2 5M32 40l-2 5"/></g>'
    elif rain >= 2:
        body = '<g transform="translate(9 -7) scale(.62)">' + sun + '</g>' + cloud + '<g stroke="#2f7fc6" stroke-width="3" stroke-linecap="round"><path d="M19 40l-2 5M29 40l-2 5"/></g>'
    elif tmax > heat_c:
        body = sun.replace("#f4b73e", "#ef6a3a")
    elif rain >= .5:
        body = '<g transform="translate(9 -7) scale(.62)">' + sun + '</g>' + cloud
    else:
        body = sun
    return f'<svg class="wi" viewBox="0 0 48 48" width="40" height="40">{body}</svg>'


def outlook(days, heat_c, heavy_mm):
    """days: DataFrame rows (date, tmax, tmin, rain_mm). Seven small day cards."""
    top = max(float(days.rain_mm.max()), heavy_mm, 1.0)
    out = []
    for i, r in enumerate(days.itertuples()):
        cls = " hot" if r.tmax > heat_c else " wet" if r.rain_mm >= heavy_mm else ""
        out.append(f'<div class="day{cls}" style="--i:{i}"><div class="dn">{r.date:%a}</div><div class="dd">{r.date.day} {r.date:%b}</div>{_icon(r.tmax, r.rain_mm, heat_c, heavy_mm)}'
                   f'<div class="hi">{r.tmax:.0f}°</div><div class="lo">{r.tmin:.0f}°</div>'
                   f'<div class="rain"><i style="width:{min(r.rain_mm / top, 1) * 100:.0f}%"></i></div><div class="mm">{r.rain_mm:.0f} mm</div></div>')
    return '<div class="fc">' + "".join(out) + "</div>"


def meters(risks):
    rows = []
    for k, r in risks.items():
        if k in ("overall", "features"):
            continue
        rows.append(f'<div class="meter"><div class="n">{esc(r["name"])}<span class="lvl {r["category"].lower()}">{esc(r["category"])}</span></div><div class="v">{r["score"]:.0f}</div>'
                    f'<div class="bar"><i style="width:{max(r["score"], 2):.0f}%;background:{BAR[r["category"]]}"></i></div></div>')
    return '<div class="meters">' + "".join(rows) + "</div>"


def risk_dials(risks):
    """One animated ring per hazard; High and Severe rings pulse."""
    out = []
    for k, r in risks.items():
        if k in ("overall", "features"):
            continue
        col, cat = BAR[r["category"]], r["category"]
        d = CIRC_SMALL * max(r["score"], 1) / 100
        out.append(f'<div class="dial {"alarm" if cat in ("High", "Severe") else ""}"><svg viewBox="0 0 80 80" width="86" height="86" role="img" aria-label="{esc(r["name"])} risk {r["score"]:.0f} out of 100, {esc(cat)}"><circle cx="40" cy="40" r="30" fill="none" stroke="rgba(20,60,45,.10)" stroke-width="8"/>'
                   f'<circle class="rf" cx="40" cy="40" r="30" fill="none" stroke="{col}" stroke-width="8" stroke-linecap="round" stroke-dasharray="{d:.1f} {CIRC_SMALL:.1f}" style="--d:{d:.1f};--c:{CIRC_SMALL:.1f}" transform="rotate(-90 40 40)"/>'
                   f'<text x="40" y="46" text-anchor="middle" font-size="19" font-weight="800" fill="#14281f" font-family="Bricolage Grotesque, Segoe UI, sans-serif">{r["score"]:.0f}</text></svg>'
                   f'<div class="dn">{esc(r["name"])}</div><div class="dc" style="color:{col}">{esc(cat)}</div></div>')
    return '<div class="dials">' + "".join(out) + "</div>"


# ---- one visual identity per solution ----------------------------------------------------------------------
def _iso_art():
    """Isometric mini-farm for the FarmOptimizer banner: patchwork fields, a flowing canal, a barn."""
    def P(x, y):
        return 150 + (x - y) * 34, 24 + (x + y) * 17

    def poly(pts, fill, extra=""):
        return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pts)}" fill="{fill}" {extra}/>'

    def tile(x, y, fill, z=0):
        p = [P(x, y), P(x + 1, y), P(x + 1, y + 1), P(x, y + 1)]
        return poly([(a, b - z) for a, b in p], fill, 'stroke="rgba(255,255,255,.35)" stroke-width="1"')

    colors = {(0, 0): "#e4c15d", (0, 1): "#e4c15d", (0, 2): "#7bb356", (0, 3): "#7bb356", (2, 0): "#8a5e36", (2, 1): "#8a5e36", (2, 2): "#e4c15d", (2, 3): "#7bb356",
              (3, 0): "#6aa84f", (3, 1): "#6aa84f", (3, 2): "#a67b4a", (3, 3): "#d8c58f"}
    out = ['<ellipse cx="150" cy="110" rx="132" ry="52" fill="rgba(0,0,0,.18)"/>']
    for (x, y), c in sorted(colors.items(), key=lambda kv: sum(kv[0])):
        out.append(tile(x, y, c, 4))
    for y in range(4):   # canal through column 1, drawn as a dashed flowing stroke
        out.append(tile(1, y, "#59b4e6", 2))
    c0, c1 = P(1.5, 0), P(1.5, 4)
    out.append(f'<path d="M{c0[0]:.1f} {c0[1] - 2:.1f} L{c1[0]:.1f} {c1[1] - 2:.1f}" stroke="#fff" stroke-width="3" stroke-dasharray="3 9" stroke-linecap="round" fill="none" class="flowline"/>')
    bx, by = P(3.4, 2.4)   # barn: a small isometric box
    out.append(poly([(bx - 14, by - 8), (bx, by), (bx, by - 20), (bx - 14, by - 28)], "#b24a2f") + poly([(bx, by), (bx + 14, by - 8), (bx + 14, by - 28), (bx, by - 20)], "#8f3922")
               + poly([(bx - 14, by - 28), (bx, by - 20), (bx + 14, by - 28), (bx, by - 36)], "#d6b087"))
    out.append('<g class="bobber"><rect x="196" y="6" width="48" height="24" rx="12" fill="rgba(255,255,255,.9)"/><path d="M208 22l6-7 4 3 7-8" stroke="#3f8c38" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></g>')
    return '<svg viewBox="0 0 300 180" width="300" height="180">' + "".join(out) + "</svg>"


THEMES = {
    # AgroCast = reading the sky: emerald + sky blue + gold, sun / cloud / rain over crop rows
    "agrocast": dict(tag="Predict the risk",
                     vars=dict(g900="#0a3a33", g700="#0f7a5a", g500="#2aa57f", g100="#dff3ec", acc="#1f8fcf", sun="#e7a93a", bg1="#e9f5ef", bg2="#dcedf6",
                               glow1="rgba(31,143,207,.16)", glow2="rgba(42,165,127,.16)", side1="#072a25", side2="#0d4a3e"),
                     art='<svg viewBox="0 0 300 180" width="300" height="180"><g class="sunrays"><circle cx="70" cy="46" r="19" fill="#ffd36b"/><g stroke="#ffd36b" stroke-width="3.4" stroke-linecap="round"><path d="M70 14v8M70 70v8M38 46h8M94 46h8M47 23l6 6M93 23l-6 6M47 69l6-6M93 69l-6-6"/></g></g>'
                          '<g class="drift"><path d="M110 78a17 17 0 0 1 3-33 24 24 0 0 1 46 7 15 15 0 0 1-2 26z" fill="#f3f8fb"/><path d="M118 50a24 24 0 0 1 38 4" stroke="#fff" stroke-width="3" fill="none" opacity=".7"/></g>'
                          '<g stroke="#8fd0ea" stroke-width="3.2" stroke-linecap="round" class="rainfall"><path d="M122 88l-4 12M138 88l-4 12M154 88l-4 12"/></g>'
                          '<path d="M0 118 80 108 220 108 300 118V180H0z" fill="#3f9a56"/><g stroke="#2a7a40" stroke-width="2.4"><path d="M150 108 20 180M150 108 80 180M150 108 150 180M150 108 220 180M150 108 280 180"/></g>'
                          '<g fill="#f2c14e"><circle cx="60" cy="152" r="3"/><circle cx="108" cy="150" r="3"/><circle cx="190" cy="150" r="3"/><circle cx="240" cy="152" r="3"/></g></svg>'),
    # FarmOptimizer = a managed farm: earth, growing green, water blue and warm sun, isometric patchwork
    "farmopt": dict(tag="Optimize the farm",
                    vars=dict(g900="#3a2a12", g700="#5f8c2e", g500="#8bb44a", g100="#f1ecd6", acc="#2a86b5", sun="#f0ad3e", bg1="#f7f0de", bg2="#e6efd8",
                              glow1="rgba(240,173,62,.20)", glow2="rgba(42,134,181,.12)", side1="#2a2113", side2="#3e3a1d"),
                    art=_iso_art()),
}


def apply_theme(kind):
    """Re-points the colour variables so the sidebar, page background, buttons, tabs and headings take the solution's identity."""
    v = THEMES[kind]["vars"]
    html("<style>:root{" + "".join(f"--{k}:{val};" for k, val in v.items()) + "}</style>")


def banner(kind, title, sub):
    """Solution-specific header with an animated illustration."""
    t = THEMES[kind]
    html(f'<div class="banner {kind}"><div class="bcopy"><div class="btag">{esc(t["tag"])}</div><div class="bt">{esc(title)}</div><div class="bs">{esc(sub)}</div></div>'
         f'<div class="bart" aria-hidden="true">{t["art"]}</div></div>')


LOGO_MARK = ('<svg class="mark" viewBox="0 0 48 48" aria-hidden="true"><defs><linearGradient id="lg2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2fd0a0"/><stop offset="1" stop-color="#1b8fd0"/></linearGradient></defs>'
             '<path d="M24 3 6 10v13c0 11 7.6 19 18 22 10.4-3 18-11 18-22V10z" fill="url(#lg2)"/><path d="M15 31c0-9 6-15 17-16 0 9-5 16-14 16z" fill="#fff" opacity=".95"/>'
             '<circle cx="34" cy="12" r="3" fill="#ffd36b"/></svg>')


def side_brand(space_label):
    html(f'<div class="side-brandrow">{LOGO_MARK}<div><div class="side-brand">Agri<i>Nova</i></div><div class="side-sub">{esc(space_label)}</div></div></div><div class="side-tag">Predict · Protect · Optimize · Grow</div>')


def topbar(space_label, page_label, live):
    pill = '<span class="pill ok"><span class="dot"></span>Live weather</span>' if live else '<span class="pill warn"><span class="dot"></span>Sample data</span>'
    html(f'<div class="topbar"><div class="crumbs"><b>AgriNova</b><span class="sep">/</span>{esc(space_label)}<span class="sep">/</span><em>{esc(page_label)}</em></div><div>{pill}</div></div>')
