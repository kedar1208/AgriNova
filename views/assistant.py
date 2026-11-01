import streamlit as st
from assistant.context import build_facts
from assistant.i18n import LANGS, UI
from assistant.service import respond, status
from utils import ui

KEY = "assistant_chat"


def _ask(q):
    st.session_state["assistant_pending"] = q


def render(ctx):
    lang = st.session_state.get("assistant_lang", "en")
    u = UI[lang]
    ui.page_head(u["title"], u["sub"], eyebrow=u["eyebrow"])
    lang = st.radio(u["lang"], list(LANGS), format_func=LANGS.get, horizontal=True, key="assistant_lang")
    u = UI[lang]
    prov = status()["external"]
    allow = False
    if prov is None:
        ui.callout("info", u["offline_t"], u["offline_d"])
    else:
        ui.callout("warn", u["llm_t"], u["llm_d"])
        allow = st.checkbox(u["allow"], value=False, key="assistant_allow")

    facts = build_facts(ctx, st.session_state)
    chat = st.session_state.setdefault(KEY, [])
    typed = st.chat_input(u["placeholder"])
    q = st.session_state.pop("assistant_pending", None) or typed
    if q:
        chat.append({"role": "user", "content": q})
        with st.spinner("..."):
            res = respond(q, facts, lang, chat[:-1], allow_external=allow)
        chat.append({"role": "assistant", "content": res["text"], "mode": res["mode"], "provider": res.get("provider", "")})

    ui.section(u["suggest"])
    cols = st.columns(4)
    for i, q_ in enumerate(u["s"]):
        ui._stretch(cols[i % 4].button, q_, key=f"asst_s{i}", on_click=_ask, args=(q_,))

    if not chat:
        ui.empty_state(u["empty"], u["empty_text"], "💬")
    for m in chat:
        with st.chat_message(m["role"], avatar="🧑‍🌾" if m["role"] == "user" else "🌾"):
            st.markdown(m["content"])
            if m["role"] == "assistant":
                st.caption({"offline": u["mode_off"], "llm": u["mode_llm"], "fallback": u["fail"]}.get(m.get("mode"), ""))
    if chat:
        st.button(u["clear"], key="asst_clear", on_click=lambda: st.session_state.__setitem__(KEY, []))
    ui.footer()
