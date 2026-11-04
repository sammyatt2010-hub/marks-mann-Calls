"""
qa_pdf.py - A4 call quality report for one recording, in Marks & Mann colours.
"""
from __future__ import annotations

from datetime import datetime

from fpdf import FPDF
from fpdf.fonts import FontFace

from qa_engine import CALL_TYPES, to_text

INK = (34, 35, 31)
MUTED = (100, 102, 92)
CHAR = (44, 45, 41)
LIME = (180, 203, 3)
OLIVE = (138, 154, 28)
GOLD = (196, 160, 60)
LINE = (226, 227, 216)
SOFT = (247, 247, 242)
TONES = {"good": (46, 139, 87), "accent": (110, 123, 18), "warn": (201, 138, 11), "bad": (192, 71, 58),
         "neutral": (110, 112, 104)}
RESULT_TONE = {"Yes": TONES["good"], "Partly": TONES["warn"], "No": TONES["bad"], "Not applicable": MUTED}


def safe(txt) -> str:
    s = to_text(txt)
    for a, b in (("“", '"'), ("”", '"'), ("‘", "'"), ("’", "'"), ("–", "-"), ("—", "-"),
                 ("•", "-"), ("…", "..."), ("·", "-"), ("→", "->"), ("£", "GBP ")):
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def build_qa_pdf(result: dict, record: dict | None = None, file_name: str = "") -> bytes:
    sc = result.get("_score", {})
    ctype = CALL_TYPES.get(result.get("call_type"), CALL_TYPES["general"])
    tone = TONES.get(sc.get("tone", "neutral"), TONES["neutral"])

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_title(f"Call quality report - {result.get('agent_name', '')}")
    pdf.set_author("Marks & Mann")
    pdf.add_page()
    W = pdf.w - pdf.l_margin - pdf.r_margin

    # header band: charcoal with the lime rule, like the website header
    pdf.set_fill_color(*CHAR)
    pdf.rect(0, 0, pdf.w, 34, "F")
    pdf.set_fill_color(*LIME)
    pdf.rect(0, 34, pdf.w, 1.3, "F")
    pdf.set_xy(pdf.l_margin, 9)
    pdf.set_font("Times", "", 19)
    pdf.set_text_color(244, 243, 236)
    pdf.cell(pdf.get_string_width("MARKS "), 9, "MARKS ")
    pdf.set_text_color(*GOLD)
    pdf.cell(pdf.get_string_width("& "), 9, "& ")
    pdf.set_text_color(244, 243, 236)
    pdf.cell(60, 9, "MANN")
    pdf.set_xy(pdf.l_margin, 20)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(200, 202, 190)
    pdf.cell(W, 5, safe(f"Call quality report   |   {ctype['label']}   |   generated {datetime.now():%d %b %Y, %H:%M}"))
    pdf.set_xy(pdf.l_margin, 9.5)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(*LIME)
    pdf.cell(W, 5, "CALL HUB", align="R")

    # verdict strip
    y = 42
    pdf.set_fill_color(*SOFT)
    pdf.set_draw_color(*LINE)
    pdf.rect(pdf.l_margin, y, W, 24, "DF")
    pdf.set_fill_color(*tone)
    pdf.rect(pdf.l_margin, y, 2.2, 24, "F")
    pdf.set_xy(pdf.l_margin + 6, y + 3.5)
    pdf.set_font("Helvetica", "B", 7.2)
    pdf.set_text_color(*MUTED)
    pdf.cell(80, 4, "VERDICT")
    pdf.set_xy(pdf.l_margin + 6, y + 8.5)
    pdf.set_font("Helvetica", "B", 13.5)
    pdf.set_text_color(*tone)
    pdf.cell(95, 8, safe(sc.get("verdict", "")))
    pdf.set_xy(pdf.l_margin + 6, y + 16.5)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.cell(95, 5, safe(f"Outcome: {result.get('outcome', '-')}"))
    tiles = [("CALL SCORE", f"{sc['pct']}%" if sc.get("pct") is not None else "-"),
             ("SENTIMENT", f"{result.get('customer_sentiment_score', '-')}/10"),
             ("FRICTION", f"{result.get('friction_level', '-')}/10")]
    for i, (lab, val) in enumerate(tiles):
        x = pdf.l_margin + W - 84 + i * 28
        pdf.set_xy(x, y + 3.5)
        pdf.set_font("Helvetica", "B", 7.2)
        pdf.set_text_color(*MUTED)
        pdf.cell(26, 4, lab)
        pdf.set_xy(x, y + 9)
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(*INK)
        pdf.cell(26, 8, safe(val))

    # who / when
    pdf.set_y(y + 28)
    rows = [("Agent", result.get("agent_name", "-")), ("Caller", f"{result.get('caller_name', '-')} "
                                                               f"({result.get('caller_role', '-')})"),
            ("Property", result.get("property_discussed", "-")), ("Next step", result.get("next_step", "-"))]
    if record:
        rows.insert(2, ("Call record", f"{record.get('when', '')}  |  {record.get('direction', '')}  |  "
                                       f"{record.get('branch', '')}  |  {record.get('length', '')}"))
    _kv(pdf, rows, W)
    pdf.ln(2)

    def heading(t):
        if pdf.get_y() > 255:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 11.5)
        pdf.set_text_color(*INK)
        pdf.cell(W, 7, t, new_x="LMARGIN", new_y="NEXT")
        pdf.set_fill_color(*LIME)
        pdf.rect(pdf.l_margin, pdf.get_y(), 14, 0.8, "F")
        pdf.ln(3)

    def body(t):
        pdf.set_font("Helvetica", "", 9.6)
        pdf.set_text_color(52, 54, 48)
        pdf.multi_cell(W, 5, safe(t or "-"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3.5)

    heading("Call summary")
    body(result.get("summary"))
    heading("What went well")
    body(result.get("what_went_well"))
    heading("Coaching for next time")
    body(result.get("coaching"))
    heading("Friction & obstacles")
    body(result.get("friction_points"))

    heading(f"Checklist - {ctype['label']}")
    pdf.set_font("Helvetica", "", 8.8)
    pdf.set_draw_color(*LINE)
    pdf.set_fill_color(*SOFT)
    with pdf.table(col_widths=(44, 13, 43), line_height=5, padding=2, first_row_as_headings=True,
                   headings_style=FontFace(emphasis="B", color=MUTED, fill_color=(236, 237, 228)),
                   borders_layout="HORIZONTAL_LINES", cell_fill_color=SOFT, cell_fill_mode="ROWS") as table:
        h = table.row()
        for t in ("Criterion", "Result", "Evidence"):
            h.cell(t)
        for c in result.get("checklist", []):
            r = table.row()
            r.cell(safe(c["criterion"]), style=FontFace(color=INK))
            r.cell(safe(c["result"]), style=FontFace(emphasis="B", color=RESULT_TONE.get(c["result"], MUTED)))
            r.cell(safe(c["evidence"]), style=FontFace(color=(80, 82, 74)))
    pdf.ln(4)

    details = [(d.get("item", ""), d.get("value", "")) for d in result.get("details_captured", []) if isinstance(d, dict)]
    if details:
        heading("Details captured")
        _kv(pdf, details, W)
        pdf.ln(2)

    flags = [lab for key, lab in (("valuation_lead", "Valuation lead"), ("mortgage_lead", "Mortgage referral"),
                                  ("landlord_lead", "Landlord lead"), ("complaint_or_risk", "Complaint / at risk"))
             if result.get(key)]
    heading("Opportunities & compliance")
    body(f"Flags: {', '.join(flags) if flags else 'None'}\n{to_text(result.get('opportunity_notes'))}\n"
         f"Compliance: {to_text(result.get('compliance_flags')) or 'None'}")
    heading("Tone & delivery")
    body(result.get("pacing_and_tone"))

    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*MUTED)
    pdf.cell(W, 5, safe(f"Marks & Mann - Call Hub   |   {file_name}   |   AI-assisted assessment: "
                        f"use as a coaching aid alongside your own judgement."), align="C")
    return bytes(pdf.output())


def _kv(pdf, rows, W):
    pdf.set_font("Helvetica", "", 9)
    pdf.set_fill_color(*SOFT)
    with pdf.table(col_widths=(22, 78), line_height=5, padding=1.8, first_row_as_headings=False,
                   borders_layout="NONE", cell_fill_color=SOFT, cell_fill_mode="ROWS") as t:
        for k, v in rows:
            r = t.row()
            r.cell(safe(k), style=FontFace(emphasis="B", color=MUTED))
            r.cell(safe(v), style=FontFace(color=INK))
