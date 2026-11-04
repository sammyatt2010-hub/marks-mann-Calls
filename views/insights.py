"""
Call handling - upload the Marks & Mann call log export, get the true picture of missed calls and the PDF.
(Built on the Call Insights app, fixed to the Marks & Mann phone system - no phone-system dropdown.)
"""
from __future__ import annotations

from datetime import time

import streamlit as st

import brand as B
import cdr_engine as ce
from ui import ICON_UPLOAD, chip, load_files, render_html, render_results, run_analysis, section_header

PROVIDER = "marksmann"
B.brand_header("Call handling")

# --------------------------------------------------------------------------- #
# Sidebar - settings
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown('<div class="pe-side-label">Opening hours</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    slots = [time(h, m) for h in range(24) for m in (0, 15, 30, 45)]
    open_t = c1.selectbox("Open", slots, index=slots.index(time(9, 0)), format_func=lambda t: t.strftime("%H:%M"))
    close_t = c2.selectbox("Close", slots, index=slots.index(time(17, 30)), format_func=lambda t: t.strftime("%H:%M"))
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    open_days = st.multiselect("Open days", day_names, default=day_names[:6])
    st.markdown('<div class="pe-side-label">Targets & rules</div>', unsafe_allow_html=True)
    target = st.slider("Answer-rate target %", 70, 100, 90)
    cb_target = st.select_slider("Call-back target", options=[15, 30, 60, 120, 240, 480], value=60,
                                 format_func=lambda m: f"{m} min" if m < 60 else f"{m // 60} hr")
    short_ab = st.number_input("Ignore hang-ups under (seconds)", 0, 30, 5,
                               help="Callers who hang up in call routing this quickly never gave the team a fair "
                                    "chance to answer.")
    with st.expander("Exclude callers"):
        excl_int = st.checkbox("Exclude international numbers", value=False)
        excl_txt = st.text_area("Numbers to exclude (one per line)", placeholder="07700 900123",
                                help="e.g. known spam, test calls, or staff mobiles.")
    st.markdown('<div class="pe-side-label">Report</div>', unsafe_allow_html=True)
    brand_by = st.text_input("Prepared by", "SY Communications")
    pdf_style = st.radio("PDF style", ["Portal (dark)", "Print-friendly (light)"],
                         help="Portal matches this web app. Print-friendly is the same layout on white paper.")

settings_tuple = (
    open_t, close_t, tuple(day_names.index(d) for d in open_days), int(short_ab), float(target), int(cb_target), 4,
    tuple(x.strip() for x in excl_txt.splitlines() if x.strip()), bool(excl_int),
)

hero = st.empty()
stage = 1

# --------------------------------------------------------------------------- #
# 01 Upload (kept in the session so the Call quality page can use it too)
# --------------------------------------------------------------------------- #
df = None
with st.container(key="card-upload"):
    section_header("01", "Upload the call log", "The call data export from the phone system (CSV) - any date range")
    files = st.file_uploader("Call log export", type=["csv", "zip"], accept_multiple_files=True,
                             label_visibility="collapsed")
    if files:
        st.session_state["cdr_blobs"] = tuple(f.getvalue() for f in files)
        st.session_state["cdr_names"] = [f.name for f in files]
    blobs = st.session_state.get("cdr_blobs")
    if blobs:
        try:
            with st.spinner("Reading call records..."):
                df = load_files(blobs, PROVIDER)
            dmin, dmax = ce.detect_range(df)
            dropped = df.attrs.get("dropped", {})
            render_html(chip(f"{df['uid'].astype(str).str.split('.').str[0].nunique():,} calls", "accent")
                        + chip(f"{dmin:%d %b %Y} → {dmax:%d %b %Y}") + chip(f"{(dmax - dmin).days + 1} days of data")
                        + chip(", ".join(st.session_state.get("cdr_names", [])) or "call log", "good")
                        + (chip(f"{dropped['internal']} internal calls ignored") if dropped.get("internal") else ""))
            if not files:
                if st.button("Clear call log"):
                    for k in ("cdr_blobs", "cdr_names"):
                        st.session_state.pop(k, None)
                    st.rerun()
                st.caption("Using the call log loaded earlier in this session.")
            stage = 2
        except Exception as e:  # noqa: BLE001
            st.error(f"Couldn't read that file as a Marks & Mann call log export. ({e})")
            df = None
    else:
        render_html(f'<div class="pe-empty"><div class="ic">{ICON_UPLOAD}</div><div>'
                    f'<div class="t">Drop in the call data export to get started</div><ol>'
                    f'<li>Export the <b>call data</b> CSV from the phone system for any period</li>'
                    f'<li>Upload it here - branches, staff and the date range are picked up automatically</li>'
                    f'<li>Pick the reporting period and download the 2-page PDF</li></ol></div></div>')

# --------------------------------------------------------------------------- #
# 02 Period
# --------------------------------------------------------------------------- #
a = None
if df is not None:
    with st.container(key="card-period"):
        section_header("02", "Reporting period", "Periods are relative to the latest call in the file")
        c1, c2 = st.columns([1, 1.4])
        customer = c1.text_input("Report title", "Marks & Mann")
        presets = ["Whole file", "This month", "Last month", "Last 30 days", "Last 7 days", "Custom"]
        preset = c2.radio("Period", presets, horizontal=True)
        if preset == "Custom":
            rng = st.date_input("Custom range", (dmin, dmax), min_value=dmin, max_value=dmax, format="DD/MM/YYYY")
            p_start, p_end = (rng if isinstance(rng, (list, tuple)) and len(rng) == 2 else (dmin, dmax))
        else:
            p_start, p_end = ce.preset_range(preset, dmin, dmax)
        render_html(chip(f"Reporting {p_start:%d %b %Y} → {p_end:%d %b %Y}", "accent")
                    + chip("Call-backs are searched across the whole file"))
        if p_start > p_end:
            st.warning("That period has no data in this file - pick another.")
        else:
            with st.spinner("Following every call to where it ended and tracking call-backs..."):
                a = run_analysis(df, p_start, p_end, settings_tuple)
            stage = 3

# --------------------------------------------------------------------------- #
# 03 / 04 Results + report
# --------------------------------------------------------------------------- #
if a is not None:
    stage = render_results(df, a, p_start, p_end, settings_tuple, customer, brand_by, None, B.logo_file(),
                           pdf_style, portal=False)

steps = ["Upload", "Period", "Review", "Report"]
step_html = '<span class="pe-step-sep"></span>'.join(
    f'<div class="pe-step {"done" if i + 1 < stage else ("active" if i + 1 == stage else "")}">'
    f'<span class="num">{"&#10003;" if i + 1 < stage else i + 1}</span>{s_}</div>'
    for i, s_ in enumerate(steps))
render_html(f'<div class="pe-hero"><div><div class="pe-eyebrow"><span class="dot"></span>Call handling</div>'
            f'<div class="pe-title">What really happened to <span>every call</span></div>'
            f'<div class="pe-sub">Which callers genuinely never reached a person - voicemail, call routing hang-ups, '
            f'unanswered - how quickly they were rung back, and who is still waiting, branch by branch.</div></div>'
            f'<div class="pe-stepper">{step_html}</div></div>', hero)
