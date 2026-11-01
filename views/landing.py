"""Landing page: two immersive solution worlds (AgroCast, FarmOptimizer). The scenes are self-contained HTML files in
assets/scenes/ (canvas + CSS 3D, no external libraries) shown through st.components.v1.html; the ENTER buttons are native
Streamlit buttons that switch st.session_state["view"], so no page reload is needed and nothing is lost."""
from pathlib import Path
import streamlit as st
from utils import demo

ASSETS = Path(__file__).resolve().parent.parent / "assets"
SCENE_H = 540

LOGO = ('<svg class="mark" viewBox="0 0 48 48"><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2fd0a0"/><stop offset="1" stop-color="#1b8fd0"/></linearGradient></defs>'
        '<path d="M24 3 6 10v13c0 11 7.6 19 18 22 10.4-3 18-11 18-22V10z" fill="url(#lg)"/>'
        '<path d="M15 31c0-9 6-15 17-16 0 9-5 16-14 16z" fill="#fff" opacity=".95"/><path d="M16 32c4-5 8-9 13-12" stroke="#1a7f66" stroke-width="1.8" fill="none" stroke-linecap="round"/>'
        '<circle cx="34" cy="12" r="3" fill="#ffd36b"/></svg>')


def go(view):
    """Open a solution (or return home). Also forgets the last sub-page so each solution starts on its own first page."""
    st.session_state["view"] = view
    st.session_state.pop("nav", None)


def _scene(name):
    return (ASSETS / "scenes" / f"{name}.html").read_text(encoding="utf-8")


def render():
    from streamlit.components.v1 import html as component_html   # imported here so tests without the component module still load app.py
    st.markdown(f"<style>{(ASSETS / 'landing.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

    st.markdown(f'<div class="l-brand">{LOGO}<div class="name">Agri<i>Nova</i></div><div class="tag">Predict. Protect. Optimize. Grow.</div></div>', unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")
    with left:
        component_html(_scene("agrocast"), height=SCENE_H)
        st.button("Enter AgroCast", key="enter_agrocast", type="primary", on_click=go, args=("agrocast",))
    with right:
        component_html(_scene("farmoptimizer"), height=SCENE_H)
        st.button("Enter FarmOptimizer", key="enter_farmopt", type="primary", on_click=go, args=("farmopt",))
    st.button("Try the guided demo - sample Maharashtra farm", key="enter_demo", on_click=demo.start)
    st.markdown('<div class="l-note">Pick a solution to open its dashboard. You can switch solutions or come back here at any time from the sidebar.</div>', unsafe_allow_html=True)

