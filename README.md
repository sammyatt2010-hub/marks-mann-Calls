# Marks & Mann – Call Hub

One password-protected Streamlit app, in Marks & Mann branding, that brings together:

| Page | What it does | Built from |
|---|---|---|
| **Call handling** | Upload the phone system's *call data* CSV and see what really happened to every call: true missed calls (voicemail, call-routing hang-ups, unanswered), un-returned callers, busiest hours, branch-by-branch answer rates, per-person assessment, 2-page PDF + user assessment PDF. | Call Insights |
| **Call quality** | Upload a call recording. The AI works out **what kind of call it was** and scores it against the right checklist. There's no call-type dropdown. You get a verdict, coaching, a CRM note and a PDF. | Call Quality Assessment |

The two are linked. Once the call log is loaded on *Call handling*, any recording uploaded on *Call quality* is matched
to its row in the log from its file name (`2026-10-31_15_44_10__447891917079_441449867590.mp3` = date, time, from, to).
That fills in the agent, branch, direction, call length and **the caller's history** (how often they rang, missed
calls, call-backs). The history is also passed to the AI as context.

## Call types the AI recognises

Edit the checklists in `qa_engine.py` → `CALL_TYPES` to change what "a good call" means.

- **Sales – buyer enquiry**: qualifying position and finance, mortgage adviser, viewing booked, valuation opportunity
- **Sales – valuation / vendor enquiry**: property details, reasons and timescales, valuation appointment booked
- **Sales progression**: status update, what's outstanding, actions and owner, managing expectations
- **Lettings – tenant applicant**: move date, household and pets, affordability, holding deposit / no banned fees, viewing
- **Lettings – landlord enquiry**: situation, service levels, compliance (gas, EICR, EPC, deposit, Right to Rent), valuation
- **Lettings – existing tenant / maintenance**: issue captured, urgency, safety advice, timescale, access
- **General / other**

Each call also gets flagged for **valuation leads, mortgage referrals, landlord leads and complaints/at-risk**, plus a
compliance check.

## How the Marks & Mann call log is read

The phone system logs almost every inbound call as "Answered", even ones that went to a branch voicemail or ended in
"Call Route". The app follows each call to where it actually ended:

- Answered by a person → answered
- *Day* voicemail → missed after ringing the branch; *Night* voicemail → missed, line closed
- "Call Route" → caller hung up in call routing (missed, unless shorter than the "ignore hang-ups under" setting)
- Unanswered → missed
- Internal calls and shortcodes are ignored

Branch names come from the numbers on marksandmann.co.uk (edit `MM_LINES` in `cdr_engine.py` if one changes):
Ipswich 01473 396296 · Stowmarket 01449 867590 · Martlesham 01473 396007 · Woodbridge & Felixstowe 01394 470590 ·
Sales Progression line 01449 700826.

The export has no ring time, so "time to answer" isn't shown. Average call length is shown in its place.

## Deploy on Streamlit Community Cloud

1. Push this folder to a new GitHub repo (e.g. `marks-mann-call-hub`).
2. On share.streamlit.io choose **New app** → the repo → branch `main` → main file `app.py`.
3. In **Settings → Secrets** add (see `.streamlit/secrets.toml.example`):
   ```toml
   APP_PASSWORD = "team-password"
   GEMINI_API_KEY = "your-google-ai-studio-key"
   ```
4. `packages.txt` installs ffmpeg (needed for audio). Uploaded files are processed in memory and not stored.
   Recordings are sent to Google Gemini for analysis and deleted from Google straight after.

## Logo

Drop the real logo into `assets/logo.png` to replace the typographic wordmark in the header, login screen and
call-handling PDF.

## Files

| File | Purpose |
|---|---|
| `app.py` | Login, navigation, sidebar |
| `views/insights.py` | Call handling page |
| `views/quality.py` | Call quality page |
| `brand.py` | Marks & Mann colours, fonts, wordmark, header (all styling) |
| `cdr_engine.py` | Call log reading (`load_marksmann`), call stitching, missed-call tracking, insights |
| `users.py` | Per-person assessment |
| `ui.py` | Call handling results dashboard |
| `report_pdf.py` | Call handling PDFs (dark "portal" or print-friendly) |
| `call_records.py` | Matches recordings to the call log and builds caller history |
| `qa_engine.py` | Call types, checklists, Gemini prompt/schema, scoring |
| `qa_pdf.py` | Call quality PDF |
