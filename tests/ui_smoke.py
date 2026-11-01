"""UI smoke test WITHOUT streamlit/plotly: injects a recording stand-in for `st` so every page's own Python
runs end-to-end (variables, data shapes, callbacks). It cannot judge real Streamlit rendering/behaviour.
Run from project root:  python tests/ui_smoke.py"""
import sys, types, runpy, datetime
from unittest.mock import MagicMock
sys.path.insert(0, ".")


class SS(dict):
    __getattr__ = dict.get
    def __setattr__(s, k, v): s[k] = v


class Ctx:
    def __enter__(s): return s
    def __exit__(s, *a): return False
    def __getattr__(s, name): return getattr(CUR, name)


class Stop(Exception): pass


class ST(types.ModuleType):
    pass


def build(overrides=None, clicked=()):
    ov, calls = overrides or {}, {"buttons": [], "downloads": [], "errors": [], "md": 0}
    st = ST("streamlit"); st.session_state = SS()
    def val(label, default): return ov.get(label, default)
    for n in ("set_page_config caption header subheader title write divider info success warning plotly_chart dataframe metric text").split():
        setattr(st, n, lambda *a, **k: None)
    st.markdown = lambda *a, **k: calls.__setitem__("md", calls["md"] + 1)
    st.error = lambda m, *a, **k: calls["errors"].append(str(m))
    def stop(): raise Stop()
    st.stop = stop
    st.rerun = lambda: None
    st.sidebar = Ctx(); st.expander = lambda *a, **k: Ctx()
    st.tabs = lambda labels: [Ctx() for _ in labels]
    st.columns = lambda n, **k: [Ctx() for _ in (range(n) if isinstance(n, int) else n)]
    st.number_input = lambda label, mn=None, mx=None, value=None, step=None, **k: val(label, value if value is not None else mn)
    st.selectbox = lambda label, opts, index=0, **k: val(label, list(opts)[index])
    st.multiselect = lambda label, opts, default=None, **k: val(label, default or [])
    st.slider = lambda label, mn=None, mx=None, value=None, step=None, **k: val(label, value if value is not None else mn)
    st.select_slider = lambda label, opts, value=None, **k: val(label, value)
    st.checkbox = lambda label, value=False, **k: val(label, value)
    st.text_input = lambda label, value="", **k: val(label, value)
    st.date_input = lambda label, value=None, **k: val(label, value)
    def radio(label, opts, index=0, key=None, **k):
        if key and key in st.session_state: return st.session_state[key]
        v = val(label, list(opts)[index])
        if key: st.session_state[key] = v
        return v
    st.radio = radio
    def button(label, on_click=None, args=(), key=None, disabled=False, **k):
        calls["buttons"].append((label, on_click, args, disabled))
        if label in clicked and not disabled:
            if on_click: on_click(*args)
            return True
        return False
    st.button = button
    st.download_button = lambda label, data, **k: calls["downloads"].append((label, len(data)))
    st.data_editor = lambda df, **k: df
    def cache_data(*a, **k):
        return a[0] if a and callable(a[0]) else (lambda f: f)
    st.cache_data = cache_data
    globals()["CUR"] = st
    return st, calls


VIEW = {"FarmOptimizer": "farmopt", "Crop Comparison": "farmopt"}   # which solution space each page lives in (see SPACES in app.py)


def run(page, overrides=None, clicked=(), state=None):
    st, calls = build({"Offline demo mode (sample data)": True, **(overrides or {})}, clicked)
    st.session_state.update(state or {}); st.session_state.setdefault("view", VIEW.get(page, "agrocast")); st.session_state["nav"] = page
    sys.modules["streamlit"] = st
    for m in ("streamlit.components", "streamlit.components.v1"):
        sys.modules[m] = MagicMock()
    for m in ("plotly", "plotly.graph_objects"): sys.modules[m] = MagicMock()
    for m in [m for m in sys.modules if m.split(".")[0] in ("views", "utils") and m != "utils.helpers"]:
        sys.modules.pop(m)
    try:
        runpy.run_path("app.py", run_name="__main__")
    except Stop:
        pass
    return st, calls


if __name__ == "__main__":
    pages = ["Dashboard", "AgroCast", "FarmOptimizer", "Weather", "Crop Comparison", "Report", "About"]
    bad = 0
    for p in pages:
        try:
            st, c = run(p); print("OK  ", p, "| app errors:", c["errors"], "| downloads:", c["downloads"])
        except Exception as e:
            bad += 1; import traceback; print("FAIL", p, type(e).__name__, e); traceback.print_exc(limit=-3)
    # dashboard variants: not sown yet, low-risk crop, bad district text is impossible (selectbox) but an invalid one must be rejected
    import datetime as _d
    for ov in ({"Sowing date": _d.date.today() + _d.timedelta(days=5)}, {"Crop": "Rice"}, {"Irrigation method": "Rainfed (none)"},
               {"State": "Karnataka"}, {"District": "seedhe maut"}):
        st, c = run(pages[0], ov); print("OK  dashboard", ov, c["errors"])
    # what-if variants
    for ov in ({"Budget (Rs)": 20000.0}, {"What-if: rainfall change (%)": -30, "What-if: cultivation cost change (%)": 15},
               {"Water (% of entered)": 0}, {"Crops to compare": ["Wheat", "Tomato"]}, {"Crops to compare": ["Rice"]},
               {"What matters most?": "water"}, {"What matters most?": "profit"}, {"Farm area": -1.0}, {"Crop": "Rice"}):
        try:
            st, c = run(pages[2], ov); print("OK  ", ov, c["errors"])
        except Exception as e:
            bad += 1; print("FAIL", ov, type(e).__name__, e)
    st, c = run(pages[5], clicked=("Save farm details",), state={}); print("reports:", c["errors"], c["downloads"])
    # landing page and navigation between the two solutions
    st, c = run("Dashboard", state={"view": "home"}); print("landing:", c["errors"], [b[0] for b in c["buttons"]])
    st, c = run("Dashboard", state={"view": "home"}, clicked=("Enter FarmOptimizer",)); print("enter FarmOptimizer ->", st.session_state["view"])
    st, c = run("Dashboard", state={"view": "farmopt"}, clicked=("\u2190 All solutions",)); print("back home ->", st.session_state["view"])
    st, c = run("Dashboard", state={"view": "agrocast"}, clicked=("Switch to FarmOptimizer",)); print("switch ->", st.session_state["view"])
    sys.exit(1 if bad else 0)
