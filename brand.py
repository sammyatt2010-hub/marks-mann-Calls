"""
brand.py - Marks & Mann look and feel, shared by every page (web) and used for chart colours.

Taken from marksandmann.co.uk: charcoal header, lime-olive gradient buttons
(#A3B04D -> #B4CB03), gold swooshes on the wordmark, Quattrocento headings and Roboto body text.
"""
from __future__ import annotations

import base64
import os

import streamlit as st

COMPANY = "Marks & Mann"
APP_NAME = "Call Hub"
TAGLINE = "Call handling & call quality for the Marks & Mann team"

# Branch numbers shown in the header strip (same order as the website)
BRANCH_PHONES = [("Ipswich", "01473 396296"), ("Stowmarket", "01449 867590"), ("Woodbridge", "01394 470590"),
                 ("Martlesham", "01473 396007"), ("Felixstowe", "01394 470590")]

# ---- colour tokens --------------------------------------------------------- #
LIME = "#B4CB03"
OLIVE = "#A3B04D"
GOLD = "#D9BE5C"
CHARCOAL = "#1B1C19"
GOOD, WARN, RISK, BAD = "#6FCF97", "#F2B544", "#EE8F4A", "#E8705E"

# chart series
C_ANSWERED = "#A9BD2E"
C_OVERFLOW = GOLD
C_MISSED = BAD
C_BUSY = RISK
C_VOICEMAIL = WARN
C_OUTBOUND = GOLD
CHART_FONT = "Roboto"
CHART_TEXT = "#CFD1C4"
HEAT = [[0, "#22231F"], [0.5, "#6F7A1F"], [1, "#C9DC3A"]]

LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")


def logo_bytes() -> bytes | None:
    """The real Marks & Mann logo, if it has been dropped into assets/logo.png."""
    try:
        with open(LOGO_PATH, "rb") as f:
            return f.read()
    except OSError:
        return None


class _Logo:
    """Looks like an uploaded file (has .getvalue()) so the report code can use it."""

    def __init__(self, data: bytes):
        self._d = data

    def getvalue(self) -> bytes:
        return self._d


def logo_file():
    data = logo_bytes()
    return _Logo(data) if data else None


def wordmark(height: int = 34) -> str:
    """The logo if present, otherwise a typographic Marks & Mann wordmark with the gold swooshes."""
    data = logo_bytes()
    if data:
        return (f'<img src="data:image/png;base64,{base64.b64encode(data).decode()}" alt="Marks &amp; Mann" '
                f'style="height:{height}px;width:auto;display:block">')
    w = int(height * 8.2)
    return (
        f'<svg width="{w}" height="{height}" viewBox="0 0 330 40" role="img" aria-label="Marks &amp; Mann">'
        f'<path d="M2 27 C 14 25, 24 20, 34 11" stroke="{GOLD}" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
        f'<path d="M7 30 C 18 28, 26 24, 33 17" stroke="{LIME}" stroke-width="1.1" fill="none" stroke-linecap="round"/>'
        f'<text x="165" y="29" text-anchor="middle" font-family="Quattrocento, Georgia, serif" font-size="27" '
        f'letter-spacing="1.5" fill="#F4F3EC">MARKS <tspan fill="{GOLD}">&amp;</tspan> MANN</text>'
        f'<path d="M328 13 C 316 15, 306 20, 296 29" stroke="{GOLD}" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
        f'<path d="M323 10 C 312 12, 304 16, 297 23" stroke="{LIME}" stroke-width="1.1" fill="none" stroke-linecap="round"/>'
        f'</svg>')


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Quattrocento:wght@400;700&family=Roboto:wght@400;500;700;900&display=swap');
:root{--bg:#161714;--surface:#1E1F1B;--surface-2:#242520;--surface-3:#2D2E28;--border:rgba(220,224,196,.12);--border-strong:rgba(220,224,196,.24);--text:#F1F1EA;--muted:#A6A898;--faint:#71736A;--accent:#B4CB03;--accent-2:#D9BE5C;--accent-soft:rgba(180,203,3,.13);--accent-ink:#D3E36B;--good:#6FCF97;--warn:#F2B544;--risk:#EE8F4A;--bad:#E8705E;--radius:12px;--grad:linear-gradient(30deg,#A3B04D 0%,#B4CB03 100%);--serif:'Quattrocento',Georgia,serif}
html,body,[class*="css"],.stApp,button,input,textarea,select{font-family:'Roboto',system-ui,-apple-system,'Segoe UI',sans-serif!important}
.stApp{background:radial-gradient(1100px 420px at 85% -10%,rgba(217,190,92,.06),transparent 60%),radial-gradient(900px 480px at 5% -20%,rgba(180,203,3,.07),transparent 60%),var(--bg)}
[data-testid="stHeader"]{background:transparent}[data-testid="stDecoration"]{display:none}footer{visibility:hidden}
.block-container{padding-top:1.2rem!important;padding-bottom:3rem!important;max-width:1500px}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#22231F 0%,#161714 100%);border-right:1px solid var(--border)}
[data-testid="stSidebarNav"] a span{font-weight:500}
[data-testid="stSidebarNav"] a[aria-current="page"]{background:var(--accent-soft)!important}
[data-testid="stWidgetLabel"] p{font-size:.76rem!important;font-weight:500!important;color:var(--muted)!important;text-transform:uppercase;letter-spacing:.06em}
[data-testid="stCaptionContainer"]{color:var(--muted)!important}

/* cards */
[class*="st-key-card-"]{background:linear-gradient(180deg,rgba(38,39,34,.92) 0%,rgba(30,31,27,.92) 100%);border:1px solid var(--border)!important;border-radius:var(--radius);padding:22px 22px 18px;box-shadow:0 1px 0 rgba(255,255,255,.03) inset,0 20px 40px -26px rgba(0,0,0,.7);margin-bottom:18px}
@media (min-width:900px){[data-testid="stColumn"]:has(.st-key-card-verdict){position:sticky;top:1rem;align-self:flex-start}}

/* inputs */
[data-baseweb="input"],[data-baseweb="select"]>div,[data-baseweb="textarea"]{background:var(--surface)!important;border:1px solid var(--border-strong)!important;border-radius:8px!important}
[data-baseweb="input"]:focus-within,[data-baseweb="select"]>div:focus-within,[data-baseweb="textarea"]:focus-within{border-color:var(--accent)!important;box-shadow:0 0 0 3px var(--accent-soft)!important}
[data-baseweb="input"]>div,[data-baseweb="base-input"]{background:transparent!important}
[data-testid="stFileUploaderDropzone"]{background:var(--surface)!important;border:1.5px dashed var(--border-strong)!important;border-radius:10px!important}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--accent)!important}

/* buttons - the website's lime gradient */
.stButton button,.stDownloadButton button,.stFormSubmitButton button{border-radius:6px!important;font-weight:500!important;border:1px solid var(--border-strong)!important;background:var(--surface-2)!important;color:var(--text)!important;transition:all .15s ease}
.stButton button:hover,.stDownloadButton button:hover{border-color:var(--accent)!important;transform:translateY(-1px)}
.stButton button[kind="primary"],.stDownloadButton button[kind="primary"],[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"],.stFormSubmitButton button,[data-testid="stBaseLinkButton-primary"]{background:var(--grad)!important;border:none!important;color:#1B1C19!important;box-shadow:0 8px 22px -12px rgba(180,203,3,.75)}
.stButton button[kind="primary"] p,.stDownloadButton button[kind="primary"] p,[data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-primaryFormSubmit"] p,.stFormSubmitButton button p,[data-testid="stBaseLinkButton-primary"] p{color:#1B1C19!important;font-weight:700!important}

/* tabs, tables, misc */
[data-testid="stTabs"] [role="tablist"],[data-baseweb="tab-list"]{gap:4px;background:var(--surface);padding:4px;border-radius:10px;border:1px solid var(--border);width:fit-content;max-width:100%;overflow-x:auto}
[data-testid="stTabs"] [role="tab"],[data-baseweb="tab"]{border-radius:7px!important;padding:8px 16px!important;color:var(--muted)!important;background:transparent!important}
[data-testid="stTabs"] [role="tab"][aria-selected="true"],[data-baseweb="tab"][aria-selected="true"]{background:var(--surface-3)!important;color:var(--text)!important;box-shadow:inset 0 -2px 0 var(--accent)}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"],[data-testid="stTabs"] .react-aria-SelectionIndicator{display:none!important}
[data-testid="stDataFrame"]{border:1px solid var(--border);border-radius:10px;overflow:hidden}
[data-testid="stExpander"] details{background:var(--surface);border:1px solid var(--border)!important;border-radius:10px!important}
[data-testid="stAlert"]{border-radius:10px!important}
[data-testid="stCode"] pre,.stCode pre{background:var(--surface)!important;border:1px solid var(--border)!important;border-radius:10px!important}

/* brand header (mirrors the website: black strip with branch numbers, then the wordmark bar) */
.mm-strip{display:flex;justify-content:flex-end;flex-wrap:wrap;gap:4px 18px;background:#0B0B0A;border:1px solid var(--border);border-bottom:none;border-radius:12px 12px 0 0;padding:7px 18px;font-size:.74rem;color:#E9E9E2}
.mm-strip b{font-weight:700}.mm-strip span{color:var(--accent-ink);text-decoration:underline;text-underline-offset:2px}
.mm-bar{display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap;padding:16px 18px;border:1px solid var(--border);border-radius:0 0 12px 12px;background:repeating-radial-gradient(circle at 0 0,rgba(255,255,255,.018) 0 2px,transparent 2px 9px),linear-gradient(180deg,#3A3B36,#2C2D29);border-bottom:2px solid var(--accent);margin-bottom:20px}
.mm-bar .app{font-family:var(--serif);color:#EDEDE4;font-size:1.05rem;letter-spacing:.06em;text-transform:uppercase}
.mm-bar .app b{color:var(--accent-ink);font-weight:700}

/* hero + stepper */
.pe-hero{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;padding:2px 2px 20px;margin-bottom:18px;border-bottom:1px solid var(--border)}
.pe-eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--accent-2);margin-bottom:8px}
.pe-eyebrow .dot{width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px rgba(180,203,3,.16)}
.pe-title{font-family:var(--serif)!important;font-size:2.15rem;font-weight:700;letter-spacing:-.01em;line-height:1.12;color:var(--text)}
.pe-title span{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.pe-sub{color:var(--muted);font-size:.95rem;margin-top:8px;max-width:660px}
.pe-stepper{display:flex;align-items:center;gap:6px;background:var(--surface);border:1px solid var(--border);border-radius:999px;padding:6px;flex-wrap:wrap}
.pe-step{display:flex;align-items:center;gap:8px;padding:7px 14px 7px 7px;border-radius:999px;font-size:.82rem;font-weight:500;color:var(--faint);white-space:nowrap}
.pe-step .num{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;font-size:.72rem;font-weight:700;border:1px solid var(--border-strong)}
.pe-step.done{color:var(--muted)}.pe-step.done .num{background:rgba(111,207,151,.14);border-color:rgba(111,207,151,.45);color:var(--good)}
.pe-step.active{background:var(--surface-3);color:var(--text)}.pe-step.active .num{background:var(--grad);border:none;color:#1B1C19}
.pe-step-sep{width:14px;height:1px;background:var(--border-strong)}

/* section header */
.pe-section{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.pe-section .badge{width:34px;height:34px;border-radius:8px;display:grid;place-items:center;background:var(--accent-soft);color:var(--accent-ink);font-weight:700;font-size:.85rem;border:1px solid rgba(180,203,3,.32)}
.pe-section .t{font-family:var(--serif);font-size:1.18rem;font-weight:700;color:var(--text)}.pe-section .s{font-size:.82rem;color:var(--muted);margin-top:2px}

/* chips */
.pe-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;font-size:.76rem;font-weight:500;background:var(--surface-3);color:var(--text);border:1px solid var(--border);white-space:nowrap;margin:0 6px 6px 0}
.pe-chip.accent{background:var(--accent-soft);color:var(--accent-ink);border-color:rgba(180,203,3,.32)}
.pe-chip.gold{background:rgba(217,190,92,.12);color:var(--accent-2);border-color:rgba(217,190,92,.32)}
.pe-chip.good{background:rgba(111,207,151,.12);color:var(--good);border-color:rgba(111,207,151,.3)}
.pe-chip.warn{background:rgba(242,181,68,.12);color:var(--warn);border-color:rgba(242,181,68,.3)}
.pe-chip.risk{background:rgba(238,143,74,.12);color:var(--risk);border-color:rgba(238,143,74,.3)}
.pe-chip.bad{background:rgba(232,112,94,.12);color:var(--bad);border-color:rgba(232,112,94,.3)}

/* KPI tiles */
.pe-kpis{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin-bottom:18px}
@media(max-width:1100px){.pe-kpis{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:640px){.pe-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}}
.pe-kpi{background:var(--surface);border:1px solid var(--border);border-top:2px solid var(--accent);border-radius:12px;padding:16px 18px}
.pe-kpi.good{border-top-color:var(--good)}.pe-kpi.warn{border-top-color:var(--warn)}.pe-kpi.bad{border-top-color:var(--bad)}.pe-kpi.cyan{border-top-color:var(--accent-2)}
.pe-kpi .l{font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.pe-kpi .v{font-size:1.75rem;font-weight:700;letter-spacing:-.02em;color:var(--text);margin-top:6px}
.pe-kpi .v small{font-size:.85rem;color:var(--faint);font-weight:500}
.pe-kpi .s{font-size:.78rem;color:var(--muted);margin-top:2px}
.pe-meter{height:6px;border-radius:99px;background:var(--surface-3);margin-top:8px;overflow:hidden}
.pe-meter i{display:block;height:100%;border-radius:99px;background:var(--tone)}

/* lists, summaries, panels */
.pe-empty{display:flex;gap:18px;align-items:flex-start;padding:6px 2px}
.pe-empty .ic{width:52px;height:52px;border-radius:12px;background:var(--accent-soft);color:var(--accent-ink);display:grid;place-items:center;flex:none;border:1px solid rgba(180,203,3,.3)}
.pe-empty .t{font-weight:700;color:var(--text);font-size:1rem}
.pe-empty ol{color:var(--muted);font-size:.88rem;margin:8px 0 0 18px;padding:0;line-height:1.8}
.pe-empty ol b{color:var(--text);font-weight:500}
.pe-summary{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:10px;padding:16px 18px;color:var(--text);line-height:1.6;font-size:.95rem;margin-bottom:16px}
.pe-list{margin:0;padding:0;list-style:none}
.pe-list li{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--border);color:var(--text);font-size:.9rem;line-height:1.5}
.pe-list li:last-child{border-bottom:none}
.pe-list .b{flex:none;width:22px;height:22px;border-radius:6px;display:grid;place-items:center;font-size:.72rem;font-weight:700;background:var(--accent-soft);color:var(--accent-ink);margin-top:1px}
.pe-list.rec .b{background:rgba(217,190,92,.15);color:var(--accent-2)}
.pe-h{font-size:.78rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:4px 0 8px}
.pe-panel{border-radius:10px;background:var(--surface);border:1px solid var(--border);padding:16px 18px;margin-bottom:12px}
.pe-panel .h{display:flex;align-items:center;gap:10px;font-weight:700;font-size:.92rem;color:var(--text);margin-bottom:10px}
.pe-panel .ic{width:28px;height:28px;border-radius:7px;display:grid;place-items:center;background:var(--soft);color:var(--tone)}
.pe-panel .b{color:#D5D6CB;font-size:.9rem;line-height:1.6}
.pe-panel .b ul{margin:0;padding-left:1.1rem}.pe-panel .b li{margin-bottom:4px}
.pe-panel.coach{background:linear-gradient(180deg,rgba(180,203,3,.07),rgba(217,190,92,.04));border-color:rgba(180,203,3,.28)}

/* verdict + score ring */
.pe-verdict{border-radius:12px;padding:18px;border:1px solid var(--border);background:var(--surface);margin-bottom:14px;position:relative;overflow:hidden;display:flex;gap:16px;align-items:center}
.pe-verdict::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--tone)}
.pe-ring{flex:none;width:78px;height:78px;border-radius:50%;display:grid;place-items:center;background:conic-gradient(var(--tone) calc(var(--p)*1%),var(--surface-3) 0)}
.pe-ring div{width:62px;height:62px;border-radius:50%;background:var(--surface);display:grid;place-items:center;font-size:1.35rem;font-weight:700;color:var(--text)}
.pe-verdict .l{font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.pe-verdict .v{font-family:var(--serif);font-size:1.3rem;font-weight:700;color:var(--tone);margin-top:4px;line-height:1.2}
.pe-verdict .p{font-size:.8rem;color:var(--muted);margin-top:6px}
.pe-scores{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
.pe-people{display:flex;flex-direction:column;gap:8px;margin-bottom:16px}
.pe-person{display:flex;align-items:center;gap:10px;font-size:.86rem;color:var(--text)}
.pe-person .pe-chip{white-space:normal;line-height:1.35;margin:0}
.pe-person .k{flex:none;color:var(--muted);font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;width:78px}

/* checklist + tables */
.pe-table{width:100%;border-collapse:separate;border-spacing:0;border:1px solid var(--border);border-radius:10px;overflow:hidden;font-size:.88rem}
.pe-table th{text-align:left;background:var(--surface-3);color:var(--muted);font-size:.7rem;letter-spacing:.08em;text-transform:uppercase;font-weight:700;padding:10px 14px}
.pe-table td{padding:11px 14px;border-top:1px solid var(--border);color:var(--text);vertical-align:top;line-height:1.5}
.pe-table td.k{color:var(--muted);font-weight:500;width:34%}
.pe-table td.ev{color:#C9CABD;font-size:.84rem}
.pe-table tr:nth-child(even) td{background:rgba(255,255,255,.015)}

/* login + sidebar brand */
.pe-login-head{text-align:center;margin:7vh 0 22px}
.pe-login-head .wm{display:flex;justify-content:center;margin-bottom:14px}
.pe-login-head .t{font-family:var(--serif);font-size:1.5rem;font-weight:700;color:var(--text)}.pe-login-head .s{color:var(--muted);font-size:.92rem;margin-top:6px}
.pe-brand{padding:4px 0 14px;border-bottom:1px solid var(--border);margin-bottom:12px}
.pe-brand .tg{font-size:.76rem;color:var(--muted);margin-top:6px;letter-spacing:.04em}
.pe-status{display:flex;align-items:center;justify-content:space-between;padding:8px 0;font-size:.84rem;color:var(--muted);border-bottom:1px dashed var(--border)}
.pe-status b{color:var(--text);font-weight:500;text-align:right;max-width:60%}
.pe-status .d{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px}
.pe-side-label{font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--faint);margin:18px 0 6px}
.pe-match{display:flex;gap:12px;align-items:flex-start;background:var(--surface);border:1px solid rgba(180,203,3,.28);border-radius:10px;padding:12px 14px;margin-top:10px;font-size:.86rem;color:var(--text);line-height:1.5}
.pe-match .ic{flex:none;width:26px;height:26px;border-radius:7px;display:grid;place-items:center;background:var(--accent-soft);color:var(--accent-ink)}
.pe-match.miss{border-color:var(--border)}.pe-match.miss .ic{background:var(--surface-3);color:var(--muted)}
"""


def inject_css():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def brand_header(page_label: str):
    """Website-style header: branch number strip + charcoal bar with the wordmark."""
    nums = "".join(f"<div><b>{n}:</b> <span>{p}</span></div>" for n, p in BRANCH_PHONES)
    st.markdown(
        f'<div class="mm-strip">{nums}</div>'
        f'<div class="mm-bar">{wordmark(34)}<div class="app">{APP_NAME} · <b>{page_label}</b></div></div>',
        unsafe_allow_html=True)
