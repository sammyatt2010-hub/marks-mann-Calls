"""
call_records.py - links a call recording to its row in the Marks & Mann call log, and pulls the caller's
history (how often they rang, missed calls, call-backs) so the quality assessment has the full picture.
"""
from __future__ import annotations

import io
from datetime import datetime, timedelta

import pandas as pd

from cdr_engine import MM_LINES, MM_NEED, _decode, _mm_name, expand_archives, fmt_dur, norm_number, pretty_number

MISSED_WORDS = ("voicemail", "call route", "unanswered")


def call_table(blobs: tuple[bytes, ...]) -> pd.DataFrame:
    """One tidy row per external call: when, direction, customer number, branch, who handled it, outcome."""
    frames = []
    for b in expand_archives(list(blobs)):
        t = pd.read_csv(io.StringIO(_decode(b)), dtype=str, keep_default_na=False)
        t.columns = [c.strip() for c in t.columns]
        if all(c in t.columns for c in MM_NEED):
            frames.append(t)
    if not frames:
        return pd.DataFrame()
    t = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["CallID"])
    t = t.apply(lambda c: c.str.strip())
    t["ts"] = pd.to_datetime(t["Call Date"], format="%d %b %Y %H:%M:%S", errors="coerce")
    t = t.dropna(subset=["ts"])
    t["secs"] = pd.to_numeric(t["Duration (Seconds)"], errors="coerce").fillna(0).astype(int)
    t["dir"] = t["Call Type"].str.lower()
    t = t[t["dir"].isin(["inbound", "outbound"])].copy()
    inb = t["dir"] == "inbound"
    t["customer"] = (t["From"].where(inb, t["To"])).map(norm_number)
    t["line"] = t["To"].where(inb, "").map(norm_number)
    t["branch"] = t["line"].map(lambda n: MM_LINES.get(n, pretty_number(n) if n else ""))
    ab = t["Answered By"].str.lower()
    t["agent"] = t["Answered By"].where(inb, t["From"]).map(_mm_name)
    t.loc[inb & (ab.str.contains("|".join(MISSED_WORDS)) | (ab == "")), "agent"] = ""
    t["outcome"] = "Answered"
    t.loc[inb & ab.str.contains("voicemail"), "outcome"] = "Voicemail"
    t.loc[inb & (ab == "call route"), "outcome"] = "Hung up in call routing"
    t.loc[inb & ((ab == "unanswered") | (ab == "")), "outcome"] = "Missed"
    t.loc[~inb & ((t["Call Result"].str.lower() != "answered") | (t["secs"] == 0)), "outcome"] = "No answer"
    t["has_recording"] = t["Has Recording"].str.lower().eq("true")
    keep = ["ts", "dir", "customer", "line", "branch", "agent", "outcome", "secs", "has_recording", "CallID",
            "Answered By"]
    return t[keep].sort_values("ts").reset_index(drop=True)


def match_recording(calls: pd.DataFrame, parsed: dict | None, window_s: int = 90) -> dict | None:
    """Find the call-log row for a recording named <date>_<time>__<from>_<to>."""
    if calls is None or calls.empty or not parsed:
        return None
    nums = {norm_number(parsed["from"]), norm_number(parsed["to"])} - {""}
    cand = calls[calls["customer"].isin(nums)].copy()
    if cand.empty:
        return None
    cand["gap"] = (cand["ts"] - pd.Timestamp(parsed["ts"])).abs().dt.total_seconds()
    cand = cand[cand["gap"] <= window_s].sort_values("gap")
    return cand.iloc[0].to_dict() if len(cand) else None


def from_filename_only(parsed: dict | None) -> dict | None:
    """Without a call log, the file name still tells us when, which branch and the customer's number."""
    if not parsed:
        return None
    a, b = norm_number(parsed["from"]), norm_number(parsed["to"])
    if b in MM_LINES:
        return {"ts": parsed["ts"], "dir": "inbound", "customer": a, "line": b, "branch": MM_LINES[b],
                "agent": "", "outcome": "", "secs": None}
    if a in MM_LINES:
        return {"ts": parsed["ts"], "dir": "outbound", "customer": b, "line": a, "branch": MM_LINES[a],
                "agent": "", "outcome": "", "secs": None}
    return {"ts": parsed["ts"], "dir": "", "customer": a, "line": b, "branch": "", "agent": "", "outcome": "",
            "secs": None}


def caller_history(calls: pd.DataFrame, number: str, ts=None) -> pd.DataFrame:
    if calls is None or calls.empty or not number:
        return pd.DataFrame()
    return calls[calls["customer"] == number].sort_values("ts")


def history_summary(hist: pd.DataFrame, ts=None) -> str:
    """Plain-English one-liner for the AI and the screen, e.g. 'Rang 5 times (1 missed); team rang them 4 times'."""
    if hist is None or hist.empty:
        return ""
    inb = hist[hist["dir"] == "inbound"]
    out = hist[hist["dir"] == "outbound"]
    missed = inb[inb["outcome"] != "Answered"]
    span = f"{hist['ts'].min():%d %b} - {hist['ts'].max():%d %b %Y}"
    parts = [f"{len(inb)} inbound call{'s' if len(inb) != 1 else ''}"
             + (f" ({len(missed)} not answered by a person)" if len(missed) else "")]
    if len(out):
        conn = out[out["outcome"] == "Answered"]
        parts.append(f"{len(out)} call{'s' if len(out) != 1 else ''} from the team ({len(conn)} connected)")
    agents = [a for a in hist["agent"] if a]
    if agents:
        top = pd.Series(agents).value_counts()
        parts.append("spoke mostly with " + ", ".join(top.index[:2]))
    if ts is not None:
        before = hist[hist["ts"] < pd.Timestamp(ts) - timedelta(seconds=60)]
        if len(before):
            last = before.iloc[-1]
            parts.append(f"previous contact {last['ts']:%a %d %b %H:%M} ({last['dir']}, {last['outcome'].lower()})")
    return f"In the call log ({span}): " + "; ".join(parts) + "."


def record_view(rec: dict) -> dict:
    """Short labels for the screen / PDF."""
    if not rec:
        return {}
    ts = rec.get("ts")
    when = ts.strftime("%a %d %b %Y, %H:%M") if isinstance(ts, (datetime, pd.Timestamp)) else ""
    return {"when": when, "direction": (rec.get("dir") or "").title(), "branch": rec.get("branch") or "",
            "length": fmt_dur(rec["secs"]) if rec.get("secs") is not None else "",
            "customer": pretty_number(rec.get("customer") or ""), "agent": rec.get("agent") or "",
            "outcome": rec.get("outcome") or ""}
