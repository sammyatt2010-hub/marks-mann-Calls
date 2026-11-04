"""
qa_engine.py - estate agency call quality assessment (Gemini).

There is no "call type" dropdown: the AI listens to the recording, decides which kind of Marks & Mann
call it is (sales buyer enquiry, valuation, sales progression, lettings applicant, landlord, tenant...)
and scores it against that call type's checklist. The checklists live in CALL_TYPES below - edit them
to change what "a good call" means for the team.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime

# --------------------------------------------------------------------------- #
# Call types and their checklists
# --------------------------------------------------------------------------- #
CALL_TYPES = {
    "sales_buyer": {
        "label": "Sales - buyer enquiry", "dept": "Sales",
        "about": "Someone enquiring about buying: a listed property, a viewing, or what is available.",
        "criteria": [
            "Warm, professional greeting with branch and own name",
            "Took the caller's name and contact details (or confirmed them)",
            "Identified the property or area and requirements (budget, bedrooms, must-haves)",
            "Qualified the buying position (property to sell, chain, first-time buyer)",
            "Asked how the purchase is funded and offered the mortgage adviser",
            "Gave accurate key information about the property (price, tenure, key features)",
            "Offered or booked a viewing",
            "Asked whether they have a property to sell or let (valuation opportunity)",
            "Registered them for or suggested other suitable properties",
            "Agreed clear next steps before ending the call",
        ],
    },
    "sales_vendor": {
        "label": "Sales - valuation / vendor enquiry", "dept": "Sales",
        "about": "A homeowner thinking of selling, asking for a valuation, or a current vendor discussing their sale.",
        "criteria": [
            "Warm, professional greeting with branch and own name",
            "Took the caller's name, contact details and property address",
            "Asked about the property (type, bedrooms, condition, improvements)",
            "Explored reason for moving and timescales",
            "Asked if they are already on the market with another agent",
            "Explained why Marks & Mann (local knowledge, marketing, service) without haggling on fees by phone",
            "Booked a valuation appointment with a date and time",
            "Offered help with their onward purchase or mortgage",
            "Agreed clear next steps before ending the call",
        ],
    },
    "sales_progression": {
        "label": "Sales progression", "dept": "Sales",
        "about": "A buyer, vendor, solicitor or broker chasing or updating an agreed sale (searches, mortgage, survey, exchange, completion).",
        "criteria": [
            "Identified the caller, their role and the property/sale",
            "Gave a clear, accurate status update",
            "Identified what is outstanding and who is holding things up",
            "Managed expectations on timescales honestly",
            "Agreed specific actions, an owner and when they will hear back",
            "Kept the caller reassured and handled any frustration well",
            "Avoided promising things outside the agent's control",
        ],
    },
    "lettings_applicant": {
        "label": "Lettings - tenant applicant enquiry", "dept": "Lettings",
        "about": "Someone looking to rent: a listed rental, a viewing, availability or the application process.",
        "criteria": [
            "Warm, professional greeting with branch and own name",
            "Took the caller's name and contact details",
            "Identified the property or area and requirements",
            "Qualified move date, who will live there, pets and parking needs",
            "Checked affordability / referencing (income, guarantor) sensitively",
            "Explained the holding deposit and costs correctly (no banned fees)",
            "Offered or booked a viewing",
            "Asked whether they have a property to sell (valuation / mortgage opportunity)",
            "Agreed clear next steps before ending the call",
        ],
    },
    "lettings_landlord": {
        "label": "Lettings - landlord enquiry", "dept": "Lettings",
        "about": "A landlord or would-be landlord asking about letting or management, or an existing landlord discussing their property.",
        "criteria": [
            "Warm, professional greeting with branch and own name",
            "Took the landlord's name, contact details and property address",
            "Understood the property and current situation (vacant, tenanted, self-managed, other agent)",
            "Explained the service options (let only, rent collection, fully managed)",
            "Mentioned compliance responsibilities (gas safety, EICR, EPC, deposit protection, Right to Rent)",
            "Booked a rental valuation or follow-up appointment",
            "Agreed clear next steps before ending the call",
        ],
    },
    "lettings_tenant": {
        "label": "Lettings - existing tenant / maintenance", "dept": "Lettings",
        "about": "A current tenant reporting a repair or maintenance issue, or asking about their tenancy, rent or deposit.",
        "criteria": [
            "Identified the tenant and the property",
            "Captured the issue clearly (what, where, since when)",
            "Assessed urgency (e.g. no heating/hot water, leak, gas, electrics, security)",
            "Gave safety advice where needed",
            "Explained what happens next and a realistic timescale",
            "Confirmed access arrangements and best contact number",
            "Showed empathy and kept the tenant reassured",
        ],
    },
    "general": {
        "label": "General / other", "dept": "Other",
        "about": "Anything else: suppliers, contractors, other agents, admin, wrong numbers, or calls too short to classify.",
        "criteria": [
            "Warm, professional greeting with branch and own name",
            "Understood the reason for the call quickly",
            "Resolved it or routed it to the right person",
            "Took a clear message with contact details when needed",
            "Agreed clear next steps before ending the call",
        ],
    },
}

OUTCOMES = ["Viewing booked", "Valuation booked", "Offer / sale progressed", "Maintenance logged",
            "Call-back arranged", "Information given", "Message taken", "No clear outcome"]
ROLES = ["Buyer", "Vendor", "Landlord", "Tenant", "Rental applicant", "Solicitor / conveyancer",
         "Mortgage broker", "Contractor / supplier", "Other"]
RESULTS = ["Yes", "Partly", "No", "Not applicable"]

# --------------------------------------------------------------------------- #
# Gemini settings (same approach as the original Call QA Engine)
# --------------------------------------------------------------------------- #
GEMINI_MODEL = "gemini-2.5-flash"
THINKING_BUDGET = 1024
RETRY_THINKING_BUDGET = 3072
MAX_OUTPUT_TOKENS = 12000
REQUEST_TIMEOUT_MS = 600_000
MAX_ATTEMPTS = 3


def _s(desc, enum=None):
    d = {"type": "STRING", "description": desc}
    if enum:
        d["enum"] = enum
    return d


RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "call_type": _s("Which call type this is", list(CALL_TYPES)),
        "call_direction": _s("Did the customer ring in, or did the agent ring out?", ["Inbound", "Outbound"]),
        "agent_name": _s("Name of the Marks & Mann staff member"),
        "caller_name": _s("Name of the customer / other party, or 'Not given'"),
        "caller_role": _s("Who the other party is", ROLES),
        "property_discussed": _s("Property address or area discussed, or 'Not specified'"),
        "outcome": _s("The main outcome of the call", OUTCOMES),
        "next_step": _s("The agreed next step: what, who and when - or 'None agreed'"),
        "customer_sentiment_score": {"type": "INTEGER", "description": "1-10, how positive the customer felt"},
        "friction_level": {"type": "INTEGER", "description": "1-10, how much resistance, frustration or confusion"},
        "summary": _s("Clear chronological summary of the call, 1-2 short paragraphs"),
        "what_went_well": _s("2-4 bullet points ('- ' prefix) on what the agent did well"),
        "friction_points": _s("Bullet points ('- ' prefix) on objections, complaints, confusion or delays"),
        "coaching": _s("2-4 specific, practical coaching points ('- ' prefix) for this agent, with example wording"),
        "pacing_and_tone": _s("Agent's tone, clarity, pace, listening and control of the call"),
        "checklist": {
            "type": "ARRAY",
            "description": "One entry for EVERY criterion of the chosen call type, in the same order",
            "items": {"type": "OBJECT", "properties": {
                "criterion": _s("The criterion text, exactly as given"),
                "result": _s("Was it done?", RESULTS),
                "evidence": _s("Short reason or quote from the call"),
            }, "required": ["criterion", "result", "evidence"], "propertyOrdering": ["criterion", "result", "evidence"]},
        },
        "details_captured": {
            "type": "ARRAY",
            "description": "Useful facts captured on the call for the CRM (budget, position, move date, issue...)",
            "items": {"type": "OBJECT", "properties": {"item": _s("What"), "value": _s("Detail")},
                      "required": ["item", "value"], "propertyOrdering": ["item", "value"]},
        },
        "valuation_lead": {"type": "BOOLEAN", "description": "Caller has (or hinted at) a property to sell or let"},
        "mortgage_lead": {"type": "BOOLEAN", "description": "Caller may need mortgage / financial advice"},
        "landlord_lead": {"type": "BOOLEAN", "description": "Caller is or could become a lettings landlord client"},
        "complaint_or_risk": {"type": "BOOLEAN", "description": "Complaint, unhappy customer or a sale/tenancy at risk"},
        "opportunity_notes": _s("One or two sentences on any business opportunity or risk, or 'None'"),
        "compliance_flags": _s("Anything that could be a compliance concern (data protection, misdescribing a "
                               "property, banned tenant fees, safety). 'None' if nothing."),
    },
}
RESPONSE_SCHEMA["required"] = list(RESPONSE_SCHEMA["properties"])
RESPONSE_SCHEMA["propertyOrdering"] = list(RESPONSE_SCHEMA["properties"])


def build_prompt(context: dict) -> str:
    types = "\n\n".join(
        f"[{k}] {v['label']} ({v['dept']}): {v['about']}\nChecklist:\n" + "\n".join(f"  - {c}" for c in v["criteria"])
        for k, v in CALL_TYPES.items())
    ctx = ""
    if context:
        lines = [f"- {k}: {v}" for k, v in context.items() if v]
        ctx = ("\nKNOWN FROM THE PHONE SYSTEM'S CALL RECORD (trust these over guesses):\n" + "\n".join(lines) + "\n"
               "If an agent name is given above, that is the Marks & Mann staff member on this call - use it as "
               "agent_name and attribute the company side of the conversation to them.\n")
    return f"""You are a senior quality and sales coach for Marks & Mann, an independent estate and letting agent in
Suffolk (branches in Ipswich, Stowmarket, Martlesham, Woodbridge and Felixstowe) handling property sales and lettings.
Listen to the attached call recording between a Marks & Mann team member and a caller.
{ctx}
1. Decide which ONE of these call types it is, based on what is actually discussed:

{types}

2. Score the call against THAT call type's checklist only. Return one checklist entry per criterion, in order, with
   the criterion text copied exactly. Use "Not applicable" only when a criterion genuinely could not apply on this call
   (e.g. the caller already gave their details, or ended the call early) - not to excuse something the agent missed.
   "Partly" means attempted but incomplete.
3. Be fair, specific and practical. Coaching should give example wording the agent could use next time.
4. Use UK English. Keep each text field focused (no more than about 200 words). Do not pad or repeat.
"""


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #
@dataclass
class Score:
    pct: int | None
    verdict: str
    tone: str  # good / accent / warn / bad / neutral
    done: int
    partly: int
    missed: int
    na: int


def to_int(v, default=5):
    try:
        return max(0, min(10, int(round(float(str(v).split("/")[0].strip())))))
    except (ValueError, TypeError):
        return default


def tidy_checklist(result: dict) -> list[dict]:
    """Line the AI's checklist up with the official criteria for the chosen call type."""
    ctype = result.get("call_type") if result.get("call_type") in CALL_TYPES else "general"
    got = result.get("checklist") or []
    norm = lambda s: re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()  # noqa: E731
    by_text = {norm(g.get("criterion", "")): g for g in got if isinstance(g, dict)}
    out = []
    for i, crit in enumerate(CALL_TYPES[ctype]["criteria"]):
        g = by_text.get(norm(crit)) or (got[i] if i < len(got) and isinstance(got[i], dict) else {})
        res = g.get("result") if g.get("result") in RESULTS else "No"
        out.append({"criterion": crit, "result": res, "evidence": str(g.get("evidence", "") or "")})
    return out


def score(checklist: list[dict]) -> Score:
    pts = {"Yes": 1.0, "Partly": 0.5, "No": 0.0}
    applicable = [c for c in checklist if c["result"] in pts]
    n = {r: sum(1 for c in checklist if c["result"] == r) for r in RESULTS}
    if not applicable:
        return Score(None, "Too short to score", "neutral", 0, 0, 0, n["Not applicable"])
    pct = round(100 * sum(pts[c["result"]] for c in applicable) / len(applicable))
    if pct >= 80:
        v, t = "Excellent call", "good"
    elif pct >= 65:
        v, t = "Good call - minor gaps", "accent"
    elif pct >= 45:
        v, t = "Needs improvement", "warn"
    else:
        v, t = "Poor - review with agent", "bad"
    return Score(pct, v, t, n["Yes"], n["Partly"], n["No"], n["Not applicable"])


def to_text(v) -> str:
    if isinstance(v, list):
        return "\n".join(f"- {x}" for x in v)
    return "" if v is None else str(v)


# --------------------------------------------------------------------------- #
# Recording file names, e.g. 2026-10-31_15_44_10__447891917079_441449867590.mp3
# --------------------------------------------------------------------------- #
FNAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})_(\d{2})_(\d{2})_(\d{2})__\+?(\d+)_\+?(\d+)")


def parse_recording_name(name: str) -> dict | None:
    m = FNAME_RE.search(os.path.basename(name))
    if not m:
        return None
    d, hh, mm, ss, a, b = m.groups()
    try:
        ts = datetime.strptime(f"{d} {hh}:{mm}:{ss}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return {"ts": ts, "from": a, "to": b}


# --------------------------------------------------------------------------- #
# Gemini call
# --------------------------------------------------------------------------- #
def resilient_json_parse(text: str) -> dict:
    raw = text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:-1]).strip()
    for attempt in (raw, re.sub(r",\s*([\]}])", r"\1", raw)):
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            pass
    raise ValueError("could not read the AI's report")


def _retryable(err) -> bool:
    msg = str(err).lower()
    return any(k in msg for k in ("504", "503", "500", "429", "timed out", "timeout", "deadline", "unavailable",
                                  "overloaded", "resource_exhausted"))


def get_client(api_key: str):
    from google import genai
    from google.genai import types as gtypes
    return genai.Client(api_key=api_key, http_options=gtypes.HttpOptions(timeout=REQUEST_TIMEOUT_MS))


def assess(client, audio_bytes: bytes, suffix: str, context: dict, log=lambda m: None) -> dict:
    """Upload the recording to Gemini and return the parsed, tidied assessment."""
    from google.genai import types as gtypes
    from pydub import AudioSegment

    src = comp = None
    ref = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(audio_bytes)
            src = f.name
        log("Optimising audio…")
        sound = AudioSegment.from_file(src).set_channels(1).set_frame_rate(16000)
        duration_s = len(sound) / 1000
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.close()
        comp = tmp.name
        sound.export(comp, format="mp3", bitrate="32k")

        log("Uploading recording securely…")
        ref = client.files.upload(file=comp, config={"mime_type": "audio/mpeg"})
        while ref.state and ref.state.name == "PROCESSING":
            time.sleep(1)
            ref = client.files.get(name=ref.name)
        if ref.state and ref.state.name == "FAILED":
            raise RuntimeError("Google couldn't process the audio file.")

        log("Listening to the call and scoring it…")
        prompt = build_prompt(context)
        safety = [gtypes.SafetySetting(category=c, threshold="BLOCK_NONE") for c in (
            "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "HARM_CATEGORY_DANGEROUS_CONTENT")]
        result, problem, bad = None, "", False
        for attempt in range(1, MAX_ATTEMPTS + 1):
            thinking, temp = (RETRY_THINKING_BUDGET, 0.6) if bad else (THINKING_BUDGET, 0.2)
            cfg = gtypes.GenerateContentConfig(
                response_mime_type="application/json", response_schema=RESPONSE_SCHEMA,
                max_output_tokens=MAX_OUTPUT_TOKENS, temperature=temp,
                thinking_config=gtypes.ThinkingConfig(thinking_budget=thinking), safety_settings=safety)
            try:
                resp = client.models.generate_content(model=GEMINI_MODEL, contents=[prompt, ref], config=cfg)
            except Exception as e:  # noqa: BLE001
                if not _retryable(e):
                    raise
                problem = "timeout"
                if attempt < MAX_ATTEMPTS:
                    log(f"AI service was slow - retrying (attempt {attempt + 1} of {MAX_ATTEMPTS})…")
                    time.sleep(5 * attempt)
                continue
            text = resp.text or ""
            finish = str(getattr(resp.candidates[0], "finish_reason", "")) if resp.candidates else ""
            try:
                if "MAX_TOKENS" in finish:
                    raise ValueError("report was cut off")
                parsed = resilient_json_parse(text)
                missing = [k for k in ("call_type", "summary", "checklist") if k not in parsed]
                if missing:
                    raise ValueError(f"missing {', '.join(missing)}")
                result = parsed
                break
            except Exception as e:  # noqa: BLE001
                bad, problem = True, str(e)
                if attempt < MAX_ATTEMPTS:
                    log(f"The report came back incomplete - re-running (attempt {attempt + 1} of {MAX_ATTEMPTS})…")
        if result is None:
            if problem == "timeout":
                raise RuntimeError("Google's AI service timed out after several attempts - please try again shortly.")
            raise RuntimeError(f"The AI couldn't produce a complete report ({problem}). Please try again.")
        return finalise(result, context, duration_s)
    finally:
        for p in (src, comp):
            if p and os.path.exists(p):
                os.remove(p)
        try:
            if ref is not None:
                client.files.delete(name=ref.name)
        except Exception:  # noqa: BLE001
            pass


def finalise(result: dict, context: dict, duration_s: float | None = None) -> dict:
    """Normalise an AI result: valid call type, official checklist, score, agent name from the call record."""
    if result.get("call_type") not in CALL_TYPES:
        result["call_type"] = "general"
    if context.get("Agent"):
        result["agent_name"] = context["Agent"]
    result["checklist"] = tidy_checklist(result)
    sc = score(result["checklist"])
    result["_score"] = sc.__dict__
    result["_duration_s"] = duration_s
    result["_assessed"] = datetime.now().strftime("%d %b %Y %H:%M")
    return result
