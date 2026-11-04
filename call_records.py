"""
call_records.py - links a call recording to its row in the Marks & Mann call log, and pulls the caller's
history (how often they rang, missed calls, call-backs) so the quality assessment has the full picture.
"""
from __future__ import annotations

import io
from datetime import datetime, timedelta

import numpy as np
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
    # transfers (exports with transfers switched on): internal call whose ParentCallID is the customer's call
    tr = {}
    if "ParentCallID" in t:
        parent_of = {c: p for c, p in zip(t["CallID"], t["ParentCallID"]) if p}
        it = t[(t["Call Type"].str.lower() == "internal") & (t["ParentCallID"] != "")].sort_values("Call Date")
        for _, r in it.iterrows():
            cid, seen = r["ParentCallID"], set()
            while cid in parent_of and cid not in seen:  # chains: customer -> A -> B -> C
                seen.add(cid)
                cid = parent_of[cid]
            who = _mm_name(r["Answered By"] or r["To"])
            if who and who not in tr.get(cid, []):
                tr.setdefault(cid, []).append(who)
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
    t["transferred_to"] = t["CallID"].map(lambda c: ", ".join(x for x in tr.get(c, []) if x))
    keep = ["ts", "dir", "customer", "line", "branch", "agent", "outcome", "secs", "has_recording", "CallID",
            "Answered By", "transferred_to"]
    return t[keep].sort_values("ts").reset_index(drop=True)


def find_candidates(calls: pd.DataFrame, info: dict | None, duration_s: float | None = None) -> pd.DataFrame:
    """Rank the calls in the log that could be this recording, using whatever we know:
    phone number(s) and date/time from the file name, and the recording's length vs the call's talk time."""
    if calls is None or calls.empty:
        return pd.DataFrame()
    c = calls
    if c["has_recording"].any():
        c = c[c["has_recording"]]
    c = c.copy()
    c["score"] = 0.0
    nums = {norm_number(n) for n in (info or {}).get("numbers", [])} - {""}
    if nums:
        c["score"] += c["customer"].isin(nums) * 4
    ts, day = (info or {}).get("ts"), (info or {}).get("date")
    if ts is not None:
        gap = (c["ts"] - pd.Timestamp(ts)).abs().dt.total_seconds()
        c["score"] += (gap <= 90) * 4 + ((gap > 90) & (gap <= 600)) * 1.5
    elif day is not None:
        c["score"] += (c["ts"].dt.date == day) * 1.5
    if duration_s:
        diff = (c["secs"] - duration_s).abs()
        c["score"] += (diff <= 3) * 2.5 + ((diff > 3) & (diff <= 10)) * 1.5 + ((diff > 10) & (diff <= 30)) * 0.5
        c["len_diff"] = diff
    else:
        c["len_diff"] = np.nan
    c = c[c["score"] > 0] if (nums or ts is not None or day is not None) else c[c["score"] >= 2.5]
    return c.sort_values(["score", "len_diff"], ascending=[False, True]).head(40)


def best_match(cands: pd.DataFrame) -> dict | None:
    """A confident automatic match: a strong score that clearly beats the runner-up."""
    if cands is None or cands.empty:
        return None
    top = cands.iloc[0]
    second = cands.iloc[1]["score"] if len(cands) > 1 else 0
    if top["score"] >= 6 or (top["score"] >= 4 and top["score"] - second >= 2):
        return top.to_dict()
    return None


def match_recording(calls: pd.DataFrame, parsed: dict | None, window_s: int = 90) -> dict | None:
    """Automatic match from the file name alone."""
    return best_match(find_candidates(calls, parsed))


def candidate_label(r) -> str:
    who = r["agent"] or r["outcome"]
    return (f"{r['ts']:%a %d %b %H:%M} · {str(r['dir']).title()} · {r['branch'] or '-'} · "
            f"{pretty_number(r['customer'])} · {who} · {fmt_dur(r['secs'])}")


def from_filename_only(parsed: dict | None) -> dict | None:
    """Without a call log, the file name may still tell us when, which branch and the customer's number."""
    if not parsed:
        return None
    nums = [norm_number(n) for n in parsed.get("numbers", [])]
    line = next((n for n in nums if n in MM_LINES), "")
    cust = next((n for n in nums if n not in MM_LINES), "")
    direction = ""
    if line and cust:
        direction = "inbound" if nums.index(line) > nums.index(cust) else "outbound"
    return {"ts": parsed.get("ts"), "dir": direction, "customer": cust, "line": line,
            "branch": MM_LINES.get(line, ""), "agent": "", "outcome": "", "secs": None}


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
            "outcome": rec.get("outcome") or "", "transferred_to": rec.get("transferred_to") or ""}
