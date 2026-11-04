"""
Call quality - upload a call recording; the AI works out what kind of call it was (sales, valuation,
progression, lettings...) and scores it against that call type's checklist. Recordings are matched to the
call log automatically from their file name, so the agent, branch and the caller's history are filled in.
"""
from __future__ import annotations

import html as html_lib
import os
import re

import pandas as pd
import streamlit as st

import brand as B
import call_records as cr
import qa_engine as qe
from cdr_engine import fmt_dur
from qa_pdf import build_qa_pdf
from ui import FULL_WIDTH, chip, render_html, section_header, show_df

B.brand_header("Call quality")


def esc(v):
    return html_lib.escape(str(v if v is not None else ""), quote=True)


ICONS = {
    "doc": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "wave": '<path d="M2 12h3l3-8 4 16 3-8h7"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "mic": '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/>',
}
TONES = {"good": (B.GOOD, "rgba(111,207,151,.14)"), "warn": (B.WARN, "rgba(242,181,68,.14)"),
         "bad": (B.BAD, "rgba(232,112,94,.14)"), "accent": (B.LIME, "rgba(180,203,3,.14)"),
         "gold": (B.GOLD, "rgba(217,190,92,.14)"), "neutral": ("#A6A898", "rgba(166,168,152,.14)")}
RESULT_CHIP = {"Yes": "good", "Partly": "warn", "No": "bad", "Not applicable": ""}


def icon(name, size=18):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def text_to_html(v):
    lines = [l.strip() for l in qe.to_text(v).splitlines() if l.strip()]
    if not lines:
        return '<span style="color:var(--faint)">Nothing noted.</span>'
    bullet = re.compile(r"^([-*•]|\d+[.)])\s+")
    out, items = [], []
    for l in lines:
        if bullet.match(l):
            items.append(f"<li>{esc(bullet.sub('', l))}</li>")
        else:
            if items:
                out.append("<ul>" + "".join(items) + "</ul>")
                items = []
            out.append(f"<p style='margin:0 0 8px'>{esc(l)}</p>")
    if items:
        out.append("<ul>" + "".join(items) + "</ul>")
    return "".join(out)


def panel(title, body, icon_name, tone="accent", extra=""):
    c, soft = TONES[tone]
    return (f'<div class="pe-panel {extra}" style="--tone:{c};--soft:{soft}"><div class="h"><div class="ic">'
            f'{icon(icon_name, 15)}</div>{esc(title)}</div><div class="b">{text_to_html(body)}</div></div>')


# --------------------------------------------------------------------------- #
# AI connection
# --------------------------------------------------------------------------- #
gemini_key = st.secrets.get("GEMINI_API_KEY")


@st.cache_resource(show_spinner=False)
def client_for(key):
    return qe.get_client(key)


@st.cache_data(show_spinner=False)
def calls_from(blobs):
    return cr.call_table(blobs)


calls = calls_from(st.session_state["cdr_blobs"]) if st.session_state.get("cdr_blobs") else None

with st.sidebar:
    st.markdown('<div class="pe-side-label">Status</div>', unsafe_allow_html=True)
    sidebar_status = st.empty()

hero = st.empty()

# --------------------------------------------------------------------------- #
# 01 Upload + match
# --------------------------------------------------------------------------- #
c_up, c_match = st.columns([1, 1], gap="medium")
with c_up:
    with st.container(key="card-upload"):
        section_header("01", "Upload a call recording", "MP3, WAV or M4A, straight from the phone system")
        up = st.file_uploader("Call recording", type=["mp3", "wav", "m4a"], label_visibility="collapsed")
        agent_override = st.text_input("Agent name", placeholder="Filled in from the call log when it can be",
                                       help="Leave blank to use the name from the call log.").strip()
        if not gemini_key:
            st.error("GEMINI_API_KEY isn't set. Add it under this app's Settings → Secrets on Streamlit.")

parsed = qe.parse_recording_name(up.name) if up else None
rec, matched = None, False
if up:
    rec = cr.match_recording(calls, parsed)
    matched = rec is not None
    if not matched:
        rec = cr.from_filename_only(parsed)
hist = cr.caller_history(calls, rec.get("customer")) if rec else pd.DataFrame()
hist_line = cr.history_summary(hist, rec.get("ts")) if rec and len(hist) else ""
view = cr.record_view(rec) if rec else {}
agent = agent_override or view.get("agent", "")

with c_match:
    with st.container(key="card-match"):
        section_header("02", "Call record", "Matched to the call log automatically")
        if not up:
            render_html('<div class="pe-match miss"><div class="ic">' + icon("link", 14) + '</div><div>Upload a '
                        'recording and it will be matched to its row in the call log by its time and phone number - '
                        'filling in the agent, branch and the caller\'s history.</div></div>')
        elif matched:
            render_html(chip(view["direction"] or "Call", "accent") + chip(view["branch"] or "Unknown line", "gold")
                        + chip(view["when"]) + (chip(view["length"]) if view["length"] else ""))
            render_html(f'<div class="pe-match"><div class="ic">{icon("link", 14)}</div><div><b>Matched to the call '
                        f'log.</b> {esc(view["direction"])} call with {esc(view["customer"])}, handled by '
                        f'<b>{esc(view["agent"] or "-")}</b>.<br><span style="color:var(--muted)">{esc(hist_line)}</span>'
                        f'</div></div>')
        else:
            msg = ("No call log loaded yet - load it on the <b>Call handling</b> page to fill in the agent and the "
                   "caller's history." if calls is None else
                   "Couldn't find this recording in the loaded call log (the file name's time and number didn't "
                   "match a call).")
            if view.get("branch"):
                render_html(chip(view["direction"] or "Call", "accent") + chip(view["branch"], "gold")
                            + chip(view["when"]))
            elif parsed is None:
                msg = ("This file name doesn't follow the phone system's pattern (date_time__from_to), so it can't be "
                       "matched - the assessment will still work.")
            render_html(f'<div class="pe-match miss"><div class="ic">{icon("link", 14)}</div><div>{msg}</div></div>')

        if len(hist) > 1:
            with st.expander(f"Caller history - {len(hist)} calls in the log"):
                show_df(pd.DataFrame({
                    "When": hist["ts"].dt.strftime("%a %d %b %H:%M"), "Direction": hist["dir"].str.title(),
                    "Branch": hist["branch"], "Handled by": hist["agent"], "Outcome": hist["outcome"],
                    "Length": hist["secs"].map(fmt_dur)}).iloc[::-1])

# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #
file_key = f"{up.name}_{up.size}_{agent}" if up else None
done = up is not None and st.session_state.get("qa_key") == file_key and "qa_result" in st.session_state
if up and st.session_state.get("qa_file") not in (None, up.name):
    for k in ("qa_result", "qa_key", "qa_file", "qa_record"):
        st.session_state.pop(k, None)

with c_up:
    go = st.button("Re-assess call" if done else "Assess call", type="secondary" if done else "primary",
                   disabled=not (up and gemini_key), **FULL_WIDTH)

if up and gemini_key and go:
    context = {
        "Agent": agent,
        "Branch / line": view.get("branch"),
        "Direction": view.get("direction"),
        "Call time": view.get("when"),
        "Call length": view.get("length"),
        "Caller history": hist_line,
    }
    try:
        with st.status("Assessing the call…", expanded=True) as status:
            result = qe.assess(client_for(gemini_key), up.getvalue(), os.path.splitext(up.name)[1] or ".mp3",
                               context, log=st.write)
            status.update(label="Assessment complete", state="complete", expanded=False)
        st.session_state.update(qa_result=result, qa_key=file_key, qa_file=up.name, qa_record=view)
        log = st.session_state.setdefault("qa_log", [])
        log.append({"Assessed": result["_assessed"], "Recording": up.name, "Agent": result.get("agent_name", ""),
                    "Branch": view.get("branch", ""), "Call type": qe.CALL_TYPES[result["call_type"]]["label"],
                    "Outcome": result.get("outcome", ""), "Score %": result["_score"]["pct"],
                    "Verdict": result["_score"]["verdict"]})
        st.rerun()
    except Exception as e:  # noqa: BLE001
        for k in ("qa_result", "qa_key"):
            st.session_state.pop(k, None)
        st.error(f"Something went wrong assessing this call: {e}")
elif not up:
    for k in ("qa_result", "qa_key", "qa_file", "qa_record"):
        st.session_state.pop(k, None)

# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
result = st.session_state.get("qa_result") if up else None
if result:
    sc = result["_score"]
    ctype = qe.CALL_TYPES[result["call_type"]]
    tone_c, _ = TONES.get(sc["tone"], TONES["neutral"])
    sent, fric = qe.to_int(result.get("customer_sentiment_score")), qe.to_int(result.get("friction_level"))
    s_c = TONES["good" if sent >= 7 else "warn" if sent >= 4 else "bad"][0]
    f_c = TONES["bad" if fric >= 7 else "warn" if fric >= 4 else "good"][0]
    rec_v = st.session_state.get("qa_record") or {}

    left, right = st.columns([1, 2], gap="medium")
    with left:
        with st.container(key="card-verdict"):
            section_header("03", "Verdict", rec_v.get("when") or "Call recording")
            pct = sc["pct"] if sc["pct"] is not None else 0
            render_html(f"""
                <div class="pe-verdict" style="--tone:{tone_c}">
                  <div class="pe-ring" style="--p:{pct}"><div>{sc['pct'] if sc['pct'] is not None else '-'}</div></div>
                  <div><div class="l">Call score</div><div class="v">{esc(sc['verdict'])}</div>
                  <div class="p">{sc['done']} done · {sc['partly']} partly · {sc['missed']} missed on the {ctype['label'].split(' - ')[-1].lower()} checklist</div></div>
                </div>
                <div class="pe-scores">
                  <div class="pe-kpi"><div class="l">Sentiment</div><div class="v">{sent}<small>/10</small></div>
                    <div class="pe-meter" style="--tone:{s_c}"><i style="width:{sent * 10}%"></i></div></div>
                  <div class="pe-kpi"><div class="l">Friction</div><div class="v">{fric}<small>/10</small></div>
                    <div class="pe-meter" style="--tone:{f_c}"><i style="width:{fric * 10}%"></i></div></div>
                </div>
                <div class="pe-people">
                  <div class="pe-person"><span class="k">Call type</span>{chip(ctype['label'], 'accent')}</div>
                  <div class="pe-person"><span class="k">Outcome</span>{chip(result.get('outcome', '-'), 'gold')}</div>
                  <div class="pe-person"><span class="k">Agent</span>{chip(result.get('agent_name') or '-')}</div>
                  <div class="pe-person"><span class="k">Caller</span>{chip(f"{result.get('caller_name', '-')} · {result.get('caller_role', '')}")}</div>
                  <div class="pe-person"><span class="k">Branch</span>{chip(rec_v.get('branch') or '-')}</div>
                </div>""")
            flags = [(k, lab, t) for k, lab, t in (("valuation_lead", "Valuation lead", "good"),
                                                   ("mortgage_lead", "Mortgage referral", "good"),
                                                   ("landlord_lead", "Landlord lead", "good"),
                                                   ("complaint_or_risk", "Complaint / at risk", "bad"))
                     if result.get(k)]
            if flags:
                render_html('<div class="pe-h">Opportunities</div>' + "".join(chip(l, t) for _, l, t in flags))
            pdf = build_qa_pdf(result, rec_v, up.name)
            safe = re.sub(r"[^A-Za-z0-9_-]+", "_", os.path.splitext(up.name)[0])[-60:]
            st.download_button("Download PDF report", pdf, f"MM_call_report_{safe}.pdf", "application/pdf",
                               type="primary", **FULL_WIDTH)

    with right:
        with st.container(key="card-insights"):
            section_header("04", "What happened", "Summary, strengths and coaching")
            render_html(
                panel("Call summary", result.get("summary"), "doc", "accent")
                + panel("Next step agreed", result.get("next_step"), "target", "gold")
                + panel("What went well", result.get("what_went_well"), "star", "good")
                + panel("Coaching for next time", result.get("coaching"), "target", "accent", "coach")
                + panel("Friction & obstacles", result.get("friction_points"), "shield", "warn"))

    with st.container(key="card-detail"):
        section_header("05", "Checklist & detail", f"Scored against the {ctype['label']} checklist")
        t1, t2, t3, t4 = st.tabs(["Checklist", "Details for the CRM", "Tone & compliance", "CRM note"])
        with t1:
            rows = "".join(
                f"<tr><td class='k'>{esc(c['criterion'])}</td><td>{chip(c['result'], RESULT_CHIP.get(c['result'], ''))}"
                f"</td><td class='ev'>{esc(c['evidence'])}</td></tr>" for c in result["checklist"])
            render_html('<table class="pe-table"><thead><tr><th>What good looks like</th><th>Done?</th>'
                        f'<th>Evidence from the call</th></tr></thead><tbody>{rows}</tbody></table>')
        with t2:
            det = [d for d in result.get("details_captured", []) if isinstance(d, dict)]
            base = [("Caller", f"{result.get('caller_name', '-')} ({result.get('caller_role', '-')})"),
                    ("Property", result.get("property_discussed", "-")), ("Outcome", result.get("outcome", "-")),
                    ("Next step", result.get("next_step", "-"))]
            rows = "".join(f"<tr><td class='k'>{esc(k)}</td><td>{esc(v)}</td></tr>"
                           for k, v in base + [(d.get("item"), d.get("value")) for d in det])
            render_html(f'<table class="pe-table"><tbody>{rows}</tbody></table>')
            if result.get("opportunity_notes") and str(result["opportunity_notes"]).lower() != "none":
                st.caption(f"Opportunity: {result['opportunity_notes']}")
        with t3:
            render_html(panel("Tone & delivery", result.get("pacing_and_tone"), "wave", "accent")
                        + panel("Compliance check", result.get("compliance_flags") or "None", "shield",
                                "bad" if str(result.get("compliance_flags", "none")).strip().lower() not in
                                ("none", "", "n/a") else "good"))
        with t4:
            st.caption("Copy the block below (copy icon, top right) and paste it into the CRM notes.")
            crm = (f"--- CALL QUALITY NOTE ---\n{ctype['label']} | {rec_v.get('branch', '')} | {rec_v.get('when', '')}\n"
                   f"Agent: {result.get('agent_name', '-')} | Caller: {result.get('caller_name', '-')} "
                   f"({result.get('caller_role', '-')})\nProperty: {result.get('property_discussed', '-')}\n"
                   f"Outcome: {result.get('outcome', '-')} | Score: {sc['pct']}% ({sc['verdict']})\n"
                   f"Next step: {result.get('next_step', '-')}\n\nSUMMARY:\n{qe.to_text(result.get('summary'))}\n\n"
                   "DETAILS:\n" + "".join(f"- {d.get('item')}: {d.get('value')}\n"
                                          for d in result.get("details_captured", []) if isinstance(d, dict))
                   + (f"\nOPPORTUNITY: {result.get('opportunity_notes')}\n" if flags else ""))
            try:
                st.code(crm, language="text", wrap_lines=True)
            except TypeError:
                st.code(crm, language="text")

elif not up:
    with st.container(key="card-empty"):
        render_html(f"""
            <div class="pe-empty"><div class="ic">{icon('mic', 24)}</div><div>
              <div class="t">Ready to assess a call</div>
              <ol>
                <li><b>Load the call log</b> on the Call handling page (optional) so recordings match up</li>
                <li><b>Upload a recording</b> - no need to pick a call type</li>
                <li>The AI works out whether it's a <b>buyer, vendor, progression, applicant, landlord or tenant</b>
                    call and scores it against the right checklist</li>
              </ol></div></div>""")

# session log
if st.session_state.get("qa_log"):
    with st.container(key="card-log"):
        section_header("06", "Assessed this session", "Every call you've assessed since signing in")
        lg = pd.DataFrame(st.session_state["qa_log"]).iloc[::-1]
        show_df(lg)
        st.download_button("Download log (CSV)", lg.to_csv(index=False).encode(), "call_quality_log.csv", "text/csv")

# --------------------------------------------------------------------------- #
# Hero + status
# --------------------------------------------------------------------------- #
has = bool(result)
steps = [("Upload", bool(up)), ("Match", bool(up)), ("Assess", has), ("Coach", has)]
first_open = next((i for i, (_, d) in enumerate(steps) if not d), None)
parts = []
for i, (label, d) in enumerate(steps):
    if d and not (has and i == len(steps) - 1):
        cls, num = "done", "&#10003;"
    elif i == first_open or (has and i == len(steps) - 1):
        cls, num = "active", str(i + 1)
    else:
        cls, num = "", str(i + 1)
    parts.append(f'<div class="pe-step {cls}"><span class="num">{num}</span>{label}</div>')
render_html(f'<div class="pe-hero"><div><div class="pe-eyebrow"><span class="dot"></span>Call quality</div>'
            f'<div class="pe-title">Coach every <span>conversation</span></div>'
            f'<div class="pe-sub">Upload a recording and the AI works out what kind of call it was - sales, valuation, '
            f'progression or lettings - then scores it against what good looks like for that call.</div></div>'
            f'<div class="pe-stepper">{"<span class=pe-step-sep></span>".join(parts)}</div></div>', hero)

g = B.GOOD if gemini_key else B.BAD
render_html(f'<div class="pe-status"><span><span class="d" style="background:{g}"></span>AI engine</span>'
            f'<b>{"Connected" if gemini_key else "No API key"}</b></div>'
            f'<div class="pe-status"><span><span class="d" style="background:{B.GOOD if calls is not None else "#71736A"}">'
            f'</span>Call log</span><b>{f"{len(calls):,} calls" if calls is not None else "Not loaded"}</b></div>'
            f'<div class="pe-status"><span><span class="d" style="background:{B.GOOD if has else "#71736A"}"></span>'
            f'Report</span><b>{"Ready" if has else "Waiting"}</b></div>', sidebar_status)
