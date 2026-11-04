"""
Marks & Mann Call Hub - call handling (call log analysis) and call quality (AI recording assessment) in one app.
"""
from __future__ import annotations

import hmac

import streamlit as st

import brand as B

st.set_page_config(page_title="Marks & Mann · Call Hub", page_icon="📞", layout="wide")
B.inject_css()


def check_password() -> bool:
    """Team password lives in Streamlit Secrets (APP_PASSWORD) only."""
    if st.session_state.get("password_correct"):
        return True
    target = st.secrets.get("APP_PASSWORD")
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.markdown(f'<div class="pe-login-head"><div class="wm">{B.wordmark(40)}</div>'
                    f'<div class="t">{B.APP_NAME}</div><div class="s">{B.TAGLINE}</div></div>',
                    unsafe_allow_html=True)
        with st.container(key="card-login"):
            if not target:
                st.error("APP_PASSWORD isn't set. Add it under this app's Settings → Secrets on Streamlit.")
                return False
            with st.form("login", border=False):
                pw = st.text_input("Team password", type="password", placeholder="Enter password")
                ok = st.form_submit_button("Sign in", type="primary")
            if ok:
                if hmac.compare_digest(pw.encode(), str(target).encode()):
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("Incorrect password")
    return False


if not check_password():
    st.stop()

pages = [
    st.Page("views/insights.py", title="Call handling", icon=":material/call:", default=True),
    st.Page("views/quality.py", title="Call quality", icon=":material/graphic_eq:"),
]
nav = st.navigation(pages)

with st.sidebar:
    st.markdown(f'<div class="pe-brand">{B.wordmark(26)}<div class="tg">{B.APP_NAME} · {B.TAGLINE}</div></div>',
                unsafe_allow_html=True)

nav.run()

with st.sidebar:
    st.write("")
    if st.button("Log out", use_container_width=True):
        st.session_state.clear()
        st.rerun()
