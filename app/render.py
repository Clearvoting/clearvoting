"""Pure formatters shared by the server-rendered pages and the API (spec §7, §9.1).

Every function here is pure: no I/O, no DataService access. site.js mirrors the
tables in this module (QUESTION_CLASSES here; the bill-type map arrives with the
naming formatters) and a parity test keeps the two in step, so the Python and JS
vocabularies can never drift apart.
"""
import html
import json
import re
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# ---------------------------------------------------------------------------
# §7.1 question classes. Ordered: the first matching pattern wins. Each pattern
# is compiled with re.IGNORECASE and uses no Python-only syntax, so site.js
# mirrors a row as {pattern: row["pattern"].pattern, flags: "i", …}.
# "threshold" is the threshold the question itself implies (House suspension,
# veto, treaty, impeachment); a Senate result's "(3/5 majority required)" /
# "(2/3 majority required)" overrides it (see parse_threshold).
# ---------------------------------------------------------------------------
QUESTION_CLASSES = [
    {"id": "pass", "class": "D", "plain": "Final vote to pass", "noun": None, "threshold": None,
     "pattern": re.compile(r"^On Passage\b", re.IGNORECASE)},
    {"id": "pass_fast", "class": "D", "plain": "Vote to pass (fast-track, needed two-thirds)", "noun": None,
     "threshold": "2/3",
     "pattern": re.compile(r"^On (the )?Motion to Suspend the Rules and Pass\b", re.IGNORECASE)},
    {"id": "adopt", "class": "D", "plain": "Vote to adopt", "noun": None, "threshold": None,
     "pattern": re.compile(
         r"^On Agreeing to the Resolution\b|^On the (Joint |Concurrent )?Resolution\b(?! of Ratification)",
         re.IGNORECASE)},
    {"id": "adopt_fast", "class": "D", "plain": "Vote to adopt (fast-track, needed two-thirds)", "noun": None,
     "threshold": "2/3",
     "pattern": re.compile(r"^On (the )?Motion to Suspend the Rules and Agree\b", re.IGNORECASE)},
    {"id": "concur", "class": "D", "plain": "Vote to accept the other chamber's changes", "noun": None,
     "threshold": None,
     "pattern": re.compile(
         r"^On (the )?Motion to (Suspend the Rules and )?Concur\b|^On the Motion \(Motion to Concur\b"
         # A named mover ("Schumer Motion to Concur …") is the same vote, unless that senator's
         # motion adds an amendment ("… with an Amendment No. 1634"), which stays procedural.
         r"|^On the Motion \([A-Z][\w ()]*? Motion to Concur\b(?!.*\bwith an Amendment\b)"
         r"|^On the Motion \(Senate Concurs\b|^On Concurring\b",
         re.IGNORECASE)},
    {"id": "veto", "class": "D", "plain": "Vote to override the veto (needed two-thirds)", "noun": None,
     "threshold": "2/3",
     "pattern": re.compile(r"^Passage, Objections of the President|^On Overriding the Veto\b|^On the Veto\b",
                           re.IGNORECASE)},
    {"id": "treaty", "class": "D", "plain": "Vote to ratify a treaty (needed two-thirds)", "noun": None,
     "threshold": "2/3",
     "pattern": re.compile(r"^On the Resolution of Ratification\b", re.IGNORECASE)},
    {"id": "impeach", "class": "D", "plain": "Verdict on an article of impeachment (needed two-thirds)",
     "noun": None, "threshold": "2/3",
     "pattern": re.compile(r"^Guilty or Not Guilty\b", re.IGNORECASE)},
    {"id": "amendment", "class": "P", "plain": "Vote on an amendment", "noun": "an amendment", "threshold": None,
     "pattern": re.compile(r"^On Agreeing to the Amendment\b|^On the Amendment\b", re.IGNORECASE)},
    {"id": "cloture", "class": "P", "plain": "Vote to end debate (needed 60)", "noun": "a motion to end debate",
     "threshold": None,
     "pattern": re.compile(r"^On Cloture on the Motion to Proceed\b|^On the Cloture Motion\b", re.IGNORECASE)},
    {"id": "proceed", "class": "P", "plain": "Vote to take it up", "noun": "a motion to take it up",
     "threshold": None,
     "pattern": re.compile(r"^On the Motion to Proceed\b|^Motion to Proceed\b|^On the Motion \(Motion to Proceed\b",
                           re.IGNORECASE)},
    {"id": "recommit", "class": "P", "plain": "Vote to send it back to committee",
     "noun": "a motion to send it back to committee", "threshold": None,
     "pattern": re.compile(
         r"^On (the )?Motion to (Recommit|Commit|Refer)\b"
         r"|^On the Motion \((?!Motion to Waive).*\bMotions? to (Recommit|Commit|Refer)\b",
         re.IGNORECASE)},
    {"id": "table", "class": "P", "plain": "Vote to set it aside", "noun": "a motion to set it aside",
     "threshold": None,
     "pattern": re.compile(r"^On (the )?Motion to Table\b|^Table Motion to Reconsider\b", re.IGNORECASE)},
    {"id": "previous_question", "class": "P", "plain": "Vote to end debate on the rule",
     "noun": "a motion to end debate on the rule", "threshold": None,
     "pattern": re.compile(r"^On Ordering the Previous Question\b", re.IGNORECASE)},
    {"id": "discharge", "class": "P", "plain": "Vote to bring it to the floor",
     "noun": "a motion to bring it to the floor", "threshold": None,
     "pattern": re.compile(r"^On (the )?Motion to Discharge\b|^On the Motion \(Motion to Discharge\b",
                           re.IGNORECASE)},
    {"id": "waive", "class": "P", "plain": "Vote to waive a budget rule (needed 60)",
     "noun": "a motion to waive a budget rule", "threshold": None,
     "pattern": re.compile(r"^On the Motion \(Motion to Waive\b", re.IGNORECASE)},
    {"id": "point_of_order", "class": "P", "plain": "Vote on a point of order", "noun": "a point of order",
     "threshold": None,
     "pattern": re.compile(r"^On the Point of Order\b", re.IGNORECASE)},
    {"id": "nomination", "class": "P", "plain": "Vote to confirm", "noun": None, "threshold": None,
     "pattern": re.compile(r"^On the Nomination\b", re.IGNORECASE)},
    {"id": "speaker", "class": "P", "plain": "Election of the Speaker", "noun": None, "threshold": None,
     "pattern": re.compile(r"^Election of the Speaker\b", re.IGNORECASE)},
    {"id": "adjourn", "class": "P", "plain": "Vote to adjourn", "noun": "a motion to adjourn", "threshold": None,
     "pattern": re.compile(r"^On (the )?Motion to Adjourn\b", re.IGNORECASE)},
    {"id": "attendance", "class": "P", "plain": "Attendance call", "noun": None, "threshold": None,
     "pattern": re.compile(r"^Call of the House\b|^Call by States\b|^(On the )?Motion for Attendance\b",
                           re.IGNORECASE)},
]

# Any question no row matches.
PROCEDURAL_FALLBACK = {"id": "procedural", "class": "P", "plain": "Procedural vote",
                       "noun": "a procedural motion", "threshold": None, "pattern": None}

_ROW_BY_PLAIN = {row["plain"]: row for row in QUESTION_CLASSES + [PROCEDURAL_FALLBACK]}


def classify(question: str | None) -> dict:
    """The §7.1 table row for a roll-call question (first match wins)."""
    text = re.sub(r"\s+", " ", (question or "").strip())
    for row in QUESTION_CLASSES:
        if row["pattern"].search(text):
            return row
    return PROCEDURAL_FALLBACK


def question_class(question: str | None) -> str:
    """'D' (decisive: the vote on the measure itself) or 'P' (procedural)."""
    return classify(question)["class"]


def plain_question(question: str | None) -> str:
    """The plain-English name of a roll-call question, e.g. 'Final vote to pass'."""
    return classify(question)["plain"]


def _row(rc: dict) -> dict:
    """The table row for a votes_index roll call: by its stored plain question,
    else by classifying its question string."""
    return _ROW_BY_PLAIN.get(rc.get("plain") or "") or classify(rc.get("question"))


# ---------------------------------------------------------------------------
# Dates (§7.3): long "September 3, 2026" in sentences, short "Sep 3, 2026" in meta.
# Month names are spelled out here so the output never depends on the locale.
# ---------------------------------------------------------------------------
_MONTHS_LONG = ("January", "February", "March", "April", "May", "June", "July",
                "August", "September", "October", "November", "December")
_MONTHS_SHORT = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def format_date(value: str | None, short: bool | str = False) -> str:
    """'2026-09-03' or '2026-09-03T00:00:00' -> 'September 3, 2026', or 'Sep 3, 2026'
    with short=True (a style string "short" / "long" is accepted too). Empty input
    -> ''. Input that is not an ISO date is returned stripped; never raises."""
    if isinstance(short, str):
        short = short == "short"
    text = (value or "").strip()
    if not text:
        return ""
    try:
        d = date.fromisoformat(text[:10])
    except ValueError:
        return text
    months = _MONTHS_SHORT if short else _MONTHS_LONG
    return f"{months[d.month - 1]} {d.day}, {d.year}"


# ---------------------------------------------------------------------------
# §7.2 result -> seal text; §7.3 outcome sentence. `rc` is one votes_index.json
# roll_calls entry (question, plain, class, result, counts {yeas, nays, present,
# absent}, date, threshold); `chamber` is "House" or "Senate" (any case, and
# "House of Representatives", are accepted).
# ---------------------------------------------------------------------------
_PASSED_RE = re.compile(r"(Passed|Agreed to|Veto Overridden)$", re.IGNORECASE)
_FAILED_RE = re.compile(r"(Failed|Defeated|Rejected|Not Sustained|Veto Sustained)$", re.IGNORECASE)
_THRESHOLD_RE = re.compile(r"\((?:[^)]*?,\s*)?(3/5|2/3) majority required\)")
_VP_RE = re.compile(r"Vice President", re.IGNORECASE)
_NEEDED = {"2/3": "two-thirds needed", "3/5": "60 needed"}
_NEEDED_SENTENCE = {"2/3": "two-thirds were needed", "3/5": "60 votes were needed"}


def _chamber_name(chamber: str | None) -> str:
    return "Senate" if (chamber or "").strip().lower().startswith("senate") else "House"


def _other_chamber(chamber: str | None) -> str:
    return "House" if _chamber_name(chamber) == "Senate" else "Senate"


def _result_text(result: str | None) -> str:
    """The result string before its parenthesis: 'Bill Passed (90-6, …)' -> 'Bill Passed'."""
    return (result or "").split("(", 1)[0].strip()


# A question that implies two-thirds whatever its table row says (a suspension-concur row
# has none of its own). site.js twoThirdsNeeded (G2) tests the same alternation.
_TWO_THIRDS_QUESTION_RE = re.compile(
    r"Suspend the Rules|Objections of the President|Overriding the Veto|^On the Veto\b", re.IGNORECASE)


def parse_threshold(result: str | None, plain: str | None = None, question: str | None = None) -> str | None:
    """'2/3' or '3/5' from a Senate result's '(… majority required)', else the
    threshold the plain question implies (suspension, veto, treaty, impeachment),
    else '2/3' when the raw question names a suspension or a veto, else None.
    sync.py's votes index stores exactly this as `threshold` (one formatter, §7.2)."""
    match = _THRESHOLD_RE.search(result or "")
    if match:
        return match.group(1)
    implied = _ROW_BY_PLAIN.get(plain or "", PROCEDURAL_FALLBACK)["threshold"]
    if implied:
        return implied
    return "2/3" if _TWO_THIRDS_QUESTION_RE.search(re.sub(r"\s+", " ", (question or "").strip())) else None


def _outcome(result: str | None) -> str:
    """'passed', 'failed' or 'other' for a result string."""
    text = _result_text(result)
    if _FAILED_RE.search(text):
        return "failed"
    if _PASSED_RE.search(text):
        return "passed"
    return "other"


def _counts(rc: dict) -> tuple[int, int]:
    counts = rc.get("counts") or {}
    return int(counts.get("yeas") or 0), int(counts.get("nays") or 0)


def result_phrase(rc: dict, chamber: str | None) -> str:
    """Seal text for one roll call (§7.2), e.g. 'Passed the House 237–169'."""
    row = _row(rc)
    cls = rc.get("class") or row["class"]
    result = rc.get("result")
    ch = _chamber_name(chamber)
    yeas, nays = _counts(rc)
    tally = f"{yeas}–{nays}"
    threshold = rc.get("threshold") or parse_threshold(result, row["plain"], rc.get("question"))
    needed = f" ({_NEEDED[threshold]})" if threshold in _NEEDED else ""
    outcome = _outcome(result)
    text = _result_text(result)

    if row["id"] == "speaker":
        return "Speaker elected"
    if row["id"] == "nomination":
        return text
    if yeas > 0 and yeas == nays and outcome in ("passed", "failed"):
        if outcome == "passed" and _VP_RE.search(result or ""):
            return f"Tied {tally} — agreed to on the Vice President's vote"
        return f"Tied {tally} — motion failed"

    if cls == "D":
        if row["id"] == "impeach":
            verdict = {"not guilty": "Not guilty", "guilty": "Guilty"}.get(text.lower(), text)
            return f"{verdict} {tally} ({_NEEDED['2/3']})"
        if row["id"] == "veto":
            if outcome == "passed":
                return f"Veto overridden in the {ch} {tally}"
            if outcome == "failed":
                return f"Veto override failed {tally} ({_NEEDED['2/3']})"
            return text
        if outcome == "passed":
            if row["id"] in ("adopt", "adopt_fast", "treaty"):
                return f"Adopted by the {ch} {tally}"
            return f"Passed the {ch} {tally}"
        if outcome == "failed":
            return f"Rejected by the {ch} {tally}{needed}"
        return text

    if row["id"] == "cloture":
        if outcome == "passed":
            return f"Debate ended {tally}"
        if outcome == "failed":
            return f"Debate not ended {tally} ({_NEEDED.get(threshold or '3/5', _NEEDED['3/5'])})"
        return text
    if row["id"] == "amendment":
        if outcome == "passed":
            return f"Amendment adopted {tally}"
        if outcome == "failed":
            return f"Amendment rejected {tally}{needed}"
        return text
    if outcome == "passed":
        return f"Motion agreed to {tally}"
    if outcome == "failed":
        return f"Motion rejected {tally}{needed}"
    return text


def outcome_sentence(rc: dict, chamber: str | None) -> str | None:
    """One-sentence outcome (§7.3) dated from rc['date']. None for Speaker
    elections and nominations (records and seals never show those sentences)."""
    row = _row(rc)
    if row["id"] in ("speaker", "nomination"):
        return None
    cls = rc.get("class") or row["class"]
    result = rc.get("result")
    ch = _chamber_name(chamber)
    yeas, nays = _counts(rc)
    when = format_date(rc.get("date"))
    threshold = rc.get("threshold") or parse_threshold(result, row["plain"], rc.get("question"))
    outcome = _outcome(result)
    text = _result_text(result)

    if yeas > 0 and yeas == nays and outcome in ("passed", "failed"):
        how = ("passed on the Vice President's vote"
               if outcome == "passed" and _VP_RE.search(result or "") else "failed")
        return f"The {ch} tied, {yeas} to {nays}, on {when}; the motion {how}."
    if row["id"] == "impeach":
        return f"On {when}, the {ch} voted {yeas} to {nays}; two-thirds were needed to convict."
    if outcome == "other":
        return f"On {when}, the {ch} voted {yeas} to {nays}: {text}."

    if cls == "D":
        if row["id"] == "veto":
            verb = "voted to override the veto" if outcome == "passed" else "did not override the veto"
            return f"The {ch} {verb}, {yeas} to {nays}, on {when}."
        if outcome == "passed":
            if row["id"] in ("adopt", "adopt_fast", "treaty"):
                verb = "adopted it"
            elif row["id"] == "concur":
                verb = f"accepted the {_other_chamber(chamber)}'s changes"
            else:
                verb = "passed it"
            return f"The {ch} {verb}, {yeas} to {nays}, on {when}."
        sentence = f"The {ch} rejected it, {yeas} to {nays}, on {when}"
        if threshold in _NEEDED_SENTENCE:
            sentence += f"; {_NEEDED_SENTENCE[threshold]}"
        return sentence + "."

    if row["id"] == "cloture":
        if outcome == "passed":
            return f"On {when}, the {ch} voted to end debate, {yeas} to {nays}."
        need = _NEEDED_SENTENCE.get(threshold or "3/5", _NEEDED_SENTENCE["3/5"])
        return f"On {when}, the {ch} voted {yeas} to {nays} to end debate; {need}, so debate did not end."
    if row["id"] == "amendment":
        verb = "adopted an amendment" if outcome == "passed" else "rejected an amendment"
    else:
        noun = row["noun"] or PROCEDURAL_FALLBACK["noun"]
        verb = f"agreed to {noun}" if outcome == "passed" else f"rejected {noun}"
    return f"On {when}, the {ch} {verb}, {yeas} to {nays}."


def bill_status(laws: list | None, latest_by_chamber: dict | None, bill_type: str | None = None) -> dict:
    """Bill status seal (§7.2): {'text': ..., 'variant': 'final' | 'moving'}.

    latest_by_chamber maps 'House' / 'Senate' (any case) to that chamber's newest
    class-D votes_index roll call, or None. Impeachment verdicts are never a bill
    seal. A simple resolution (H.Res./S.Res.) is recognised from bill_type or, when
    that is omitted, from the roll call's `bill` key ("119-hres-8")."""
    if laws:
        return {"text": "Became law", "variant": "final"}
    votes = {}
    for chamber, rc in (latest_by_chamber or {}).items():
        if not rc or _row(rc)["id"] == "impeach":
            continue
        votes[_chamber_name(chamber)] = rc
    if not votes:
        return {"text": "No final vote yet", "variant": "moving"}
    passed = {ch: _outcome(rc.get("result")) == "passed" for ch, rc in votes.items()}
    if len(votes) == 2 and all(passed.values()):
        return {"text": "Passed both chambers", "variant": "final"}
    # One chamber voted, or the chambers differ / both rejected: state the newer.
    ch, rc = max(votes.items(), key=lambda item: (item[1].get("date") or "", item[0]))
    kind = (bill_type or "").lower() or ((rc.get("bill") or "").split("-") + ["", ""])[1]
    variant = "final" if passed[ch] and kind in ("hres", "sres") else "moving"
    return {"text": result_phrase(rc, ch), "variant": variant}


# §7.1 positions -> chip text, variant (the .chip--{variant} class) and the
# short form printed inside roll-call tables. Guilty / Not Guilty are verbatim.
_POSITIONS = {
    "yea": ("Voted yes", "yes", "Yes"),
    "aye": ("Voted yes", "yes", "Yes"),
    "nay": ("Voted no", "no", "No"),
    "no": ("Voted no", "no", "No"),
    "not voting": ("Didn't vote", "nv", "Didn't vote"),
    "present": ("Present", "present", "Present"),
    "present, giving live pair": ("Present", "present", "Present"),
    "guilty": ("Guilty", "other", "Guilty"),
    "not guilty": ("Not Guilty", "other", "Not Guilty"),
}


def position_chip(vote: str | None) -> dict:
    """{'text', 'variant', 'short'} for a member's recorded position. Any other
    string (a Speaker-election candidate name) is 'Voted' — the name itself is
    shown only with the party reveal (§4.3)."""
    text, variant, short = _POSITIONS.get((vote or "").strip().lower(), ("Voted", "other", "Voted"))
    return {"text": text, "variant": variant, "short": short}


# ---------------------------------------------------------------------------
# §9.1 escaping, §7.5 codes / names / tenure, §7.4 seat seals, §4.4 sponsor,
# §10 #10 tag stripping.
# ---------------------------------------------------------------------------
def h(value) -> str:
    """The one escape helper: every interpolated data value in rendered HTML goes
    through this. None renders as an empty string."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


# Title-case bill abbreviations, e.g. "hr" -> "H.R." (moved from app/main.py;
# site.js carries the same map and test_formatter_parity keeps them equal).
_BILL_TYPE_LABELS = {
    "hr": "H.R.",
    "s": "S.",
    "hjres": "H.J.Res.",
    "sjres": "S.J.Res.",
    "hconres": "H.Con.Res.",
    "sconres": "S.Con.Res.",
    "hres": "H.Res.",
    "sres": "S.Res.",
}


def format_bill_code(bill_type: str | None, number) -> str:
    """('hr', 4795) -> 'H.R. 4795'; unknown types fall back to the upper-cased type."""
    raw = (bill_type or "").strip()
    label = _BILL_TYPE_LABELS.get(raw.lower(), raw.upper())
    return f"{label} {str(number).strip()}".strip()


def ordinal(n) -> str:
    """119 -> '119th', 1 -> '1st', 112 -> '112th' (11–13 always take 'th')."""
    n = int(n)
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def display_name(name: str | None) -> str:
    """'Schumer, Charles E.' -> 'Charles E. Schumer'. members.json has no
    directOrderName, so this is the only path from the stored name to a display name."""
    text = (name or "").strip()
    if "," not in text:
        return text
    last, first = text.split(",", 1)
    return f"{first.strip()} {last.strip()}".strip()


def _term_chamber(term: dict) -> str:
    return "Senate" if (term.get("chamber") or "").lower().startswith("senate") else "House"


def tenure_line(terms) -> str:
    """'In Congress since 2025' for one chamber; 'In Congress since 1981 — House
    1981–1999, Senate since 1999' for two. Accepts members.json `terms` ({'item': [...]})
    or the bare list."""
    items = terms.get("item", []) if isinstance(terms, dict) else list(terms or [])
    spans: dict[str, dict] = {}
    for term in items:
        start = term.get("startYear")
        if not start:
            continue
        span = spans.setdefault(_term_chamber(term), {"start": start, "end": None, "current": False})
        span["start"] = min(span["start"], start)
        if term.get("endYear"):
            span["end"] = max(span["end"] or 0, term["endYear"])
        else:
            span["current"] = True
    if not spans:
        return ""
    first = min(span["start"] for span in spans.values())
    if len(spans) == 1:
        return f"In Congress since {first}"
    parts = []
    for chamber, span in sorted(spans.items(), key=lambda item: item[1]["start"]):
        if span["current"] or not span["end"]:
            parts.append(f"{chamber} since {span['start']}")
        else:
            parts.append(f"{chamber} {span['start']}–{span['end']}")
    return f"In Congress since {first} — " + ", ".join(parts)


# §7.4: ballot copy describes the SEAT, never the person.
_SEAT_SEALS = {
    ("regular", "row"): "Seat up Nov 3",
    ("regular", "header"): "This seat is on the ballot Nov 3, 2026",
    ("special", "row"): "Special election Nov 3",
    ("special", "header"): "Special election for this seat Nov 3, 2026",
}


def seat_seal(kind: str | None, context: str = "row", header: bool = False) -> str:
    """Seat seal text for data_service.seat_up_2026(member) ('regular' | 'special' | None):
    the row form by default, the member-header form with context="header" or
    header=True. '' when the seat is not up (no negative ballot copy exists)."""
    where = "header" if header or context == "header" else "row"
    return _SEAT_SEALS.get((kind or "", where), "")


_SPONSOR_PREFIXES = r"(Rep\.|Sen\.|Del\.|Rescom\.|Resident Commissioner)"
# The [R-AL-6] suffix is optional: T1.8's page sponsor already carries fullName
# without it ("Rep. Smith, Jason"), and G7 renders that dict through sponsor_name.
_SPONSOR_FULLNAME_RE = re.compile(rf"^{_SPONSOR_PREFIXES}\s+(.+?)\s*(?:\[[^\]]*\])?\s*$")
_SPONSOR_PREFIX_RE = re.compile(rf"^{_SPONSOR_PREFIXES}\s")


def _name_part(part: str | None) -> str:
    """Fallback only: 176 real sponsors carry ALL-CAPS firstName/lastName ('STENY')."""
    part = (part or "").strip()
    return part.title() if part.isupper() else part


def sponsor_name(sponsor: dict | None) -> str:
    """'Rep. Gary J. Palmer (AL)' from 'Rep. Palmer, Gary J. [R-AL-6]' + state: the
    prefix is kept, the 'Last, First M.' part goes through display_name, and the
    [R-AL-6] suffix (party letter) is dropped. fullName is the primary source
    because firstName/lastName are ALL CAPS on 176 real bills and lastName halves
    compound surnames ('Rodgers' for McMorris Rodgers). Falls back to
    firstName + lastName only when fullName does not parse."""
    sponsor = sponsor or {}
    full = (sponsor.get("fullName") or "").strip()
    match = _SPONSOR_FULLNAME_RE.match(full)
    if match and "," in match.group(2):
        prefix, person = match.group(1), display_name(match.group(2))
    else:
        prefix_match = _SPONSOR_PREFIX_RE.match(full)
        prefix = prefix_match.group(1) if prefix_match else ""
        person = " ".join(p for p in (_name_part(sponsor.get("firstName")),
                                      _name_part(sponsor.get("lastName"))) if p)
    if not person:
        return ""
    state = (sponsor.get("state") or "").strip()
    text = " ".join(p for p in (prefix, person) if p)
    return f"{text} ({state})" if state else text


class _TextOnly(HTMLParser):
    """Collects text nodes only; drops every tag, attribute and the contents of
    <script>/<style>. Entities are decoded (convert_charrefs), so callers must
    still pass the result through h() before it reaches HTML."""

    _SKIP = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in ("p", "br", "li", "div"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth:
            self.parts.append(data)


def strip_tags(markup: str | None) -> str:
    """Plain text from an HTML fragment, whitespace collapsed (§10 #10)."""
    parser = _TextOnly()
    parser.feed(markup or "")
    parser.close()
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


# ---------------------------------------------------------------------------
# Shared page blocks (plan T3.1). Pure functions: every data value goes through
# h(); hrefs use only fixed state codes. Constant copy that contains an
# apostrophe is written literally (h() would turn ' into &#x27;).
# ---------------------------------------------------------------------------

# Same date as data/synced/senate_2026.json "election_day" (a test asserts it).
ELECTION_DAY = date(2026, 11, 3)

COVERED_STATES = (("CA", "California"), ("FL", "Florida"), ("NY", "New York"), ("TX", "Texas"))

# The notify form's only options: the 46 states ClearVoting does not cover, plus DC.
NOTIFY_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CO": "Colorado",
    "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}

# Spec §3.2: the browser check mirrors the server rule ^\s*(\d{5})(?:[-\s]?\d{4})?\s*$.
ZIP_INPUT_PATTERN = r"\s*[0-9]{5}([\-\s]?[0-9]{4})?\s*"

PAGE_ERROR_SENTENCE = (
    "We couldn't load this page right now. Please try again in a moment, "
    "or use <em>Report an error</em> below to tell us."
)


def _pacific_today(now: datetime) -> date:
    """Today's date in America/Los_Angeles, so "Election Day is today" lasts until
    California polls close (spec §7.4). Falls back to the US DST rule when the host
    has no tz database (python:3.12-slim may ship without one; no new dependency)."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    try:
        return now.astimezone(ZoneInfo("America/Los_Angeles")).date()
    except ZoneInfoNotFoundError:
        utc = now.astimezone(timezone.utc)
        # PDT runs from the second Sunday in March, 10:00 UTC, to the first Sunday in November, 09:00 UTC.
        march_8 = datetime(utc.year, 3, 8, 10, tzinfo=timezone.utc)
        dst_start = march_8 + timedelta(days=(6 - march_8.weekday()) % 7)
        nov_1 = datetime(utc.year, 11, 1, 9, tzinfo=timezone.utc)
        dst_end = nov_1 + timedelta(days=(6 - nov_1.weekday()) % 7)
        offset = -7 if dst_start <= utc < dst_end else -8
        return (utc + timedelta(hours=offset)).date()


def render_edition(last_sync: str | None, latest_roll_call: str | None, now: datetime) -> str:
    """The one-line edition under the masthead nav (spec §7.4, §6.4)."""
    parts: list[tuple[str, str]] = []
    if last_sync:
        parts.append(("", f"Data synced {format_date(last_sync[:10])}"))
    if latest_roll_call:
        month_day = format_date(latest_roll_call[:10]).rsplit(",", 1)[0]
        parts.append(("edition-mid", f"Latest roll call {month_day}"))
    days = (ELECTION_DAY - _pacific_today(now)).days
    if days == 0:
        parts.append(("", "Election Day is today"))
    elif days > 0:
        weekday = ELECTION_DAY.strftime("%A")
        month_day = format_date(ELECTION_DAY.isoformat()).rsplit(",", 1)[0]
        unit = "day" if days == 1 else "days"
        parts.append(("", f"Election Day is {weekday}, {month_day} — {days} {unit} away"))
    if not parts:
        return ""
    spans = []
    for i, (cls, text) in enumerate(parts):
        class_attr = f' class="{cls}"' if cls else ""
        separator = " · " if i else ""
        spans.append(f"<span{class_attr}>{h(separator + text)}</span>")
    return f'<p class="edition">{"".join(spans)}</p>'


def render_error(h1: str) -> str:
    """Spec §4 common: shown when the server cannot render a page's content."""
    return f'<section class="page-error"><h1>{h(h1)}</h1><p class="deck">{PAGE_ERROR_SENTENCE}</p></section>'


def render_zip_form(compact: bool = False, value: str = "", error: str | None = None,
                    form_id: str = "find", label: str = "Where do you live?") -> str:
    """The ZIP finder (spec §3.2). A plain GET to /state that JavaScript never intercepts."""
    input_id = "zip" if form_id == "find" else f"{form_id}-field"
    error_id = f"{input_id}-error"
    form_class = "zip-form zip-form--compact" if compact else "zip-form"
    value_attr = f' value="{h(value)}"' if value else ""
    described = f' aria-describedby="{h(error_id)}" aria-invalid="true"' if error else ""
    error_html = f'<p class="field-error" id="{h(error_id)}">{h(error)}</p>' if error else ""
    return (
        f'<form class="{form_class}" id="{h(form_id)}" method="get" action="/state">'
        f'<label class="zip-label" for="{h(input_id)}">{h(label)}</label>'
        '<div class="zip-row">'
        f'<input id="{h(input_id)}" name="zip" type="text" inputmode="numeric" autocomplete="postal-code" '
        f'maxlength="10" pattern="{h(ZIP_INPUT_PATTERN)}" required{value_attr}{described}>'
        '<button class="btn" type="submit">Find my representatives</button>'
        "</div>"
        f"{error_html}</form>"
    )


def render_state_links(counts: dict) -> str:
    """Four 44px state chips with real member counts ("New York · 28")."""
    items = []
    for code, name in COVERED_STATES:
        count = counts.get(code)
        label = f"{name} · {int(count)}" if count else name
        items.append(f'<li><a class="state-link" href="/state?code={code}">{h(label)}</a></li>')
    return f'<ul class="state-links">{"".join(items)}</ul>'


def render_notify_disclosure() -> str:
    """"Somewhere else?" (spec §4.1 m2). No action/method, and the fields start disabled,
    so without JavaScript nothing can be typed or submitted (an email must never end up in
    a GET query string); site.js initNotify enables the fieldset and POSTs JSON."""
    options = "".join(f'<option value="{code}">{h(name)}</option>' for code, name in NOTIFY_STATES.items())
    return (
        '<details class="notify-disclosure">'
        "<summary>Somewhere else?</summary>"
        '<form class="notify" id="notify-form">'
        '<fieldset class="notify-fields" disabled>'
        '<label for="notify-state">Your state</label>'
        '<select id="notify-state" name="state" required>'
        f'<option value="">Choose your state</option>{options}</select>'
        '<label for="notify-email">Email address</label>'
        '<input id="notify-email" name="email" type="email" autocomplete="email" maxlength="254" '
        'required aria-describedby="notify-email-error">'
        '<p class="field-error" id="notify-email-error"></p>'
        '<button class="btn" type="submit" id="notify-submit">Notify me</button>'
        "</fieldset>"
        '<p class="meta">We store your email, your state and the time you signed up. '
        '<a href="/privacy">Privacy →</a></p>'
        '<p class="notify-status" id="notify-status" role="status" tabindex="-1"></p>'
        "</form>"
        '<noscript><p class="meta">Signing up needs JavaScript.</p></noscript>'
        "</details>"
    )


# ---------------------------------------------------------------------------
# Home blocks (plan T3.2, spec §4.1): lead, Latest Vote card, the Record.
# ---------------------------------------------------------------------------

SUMMARY_ATTRIBUTION = "Summarized by AI from the bill's title, official summary and text excerpt"
_SEAL_VARIANTS = ("final", "moving", "pending", "ballot")
# Only texts that are final whatever the bill type. "Adopted by the …" is final only for
# hres/sres, which the text alone cannot tell (T1.2 bill_status decides it from the type).
_FINAL_SEAL_PREFIXES = ("Became law", "Passed both chambers")
_SIMPLE_RESOLUTIONS = ("hres", "sres")
_PENDING_SEAL_TEXT = "No plain-English summary yet"


def _record_href(congress, bill_type, number) -> str:
    """Bill URL from validated parts only (spec §3.3 canonical form, lowercase type)."""
    return f"/bill?congress={int(congress)}&type={quote(str(bill_type).lower(), safe='')}&number={int(number)}"


def _cap(text: str, limit: int) -> tuple[str, bool]:
    """Cap official text on a word boundary with an ellipsis; returns (text, was_capped)."""
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text, False
    head = text[: limit + 1]
    cut = head.rsplit(" ", 1)[0] if " " in head else text[:limit]
    return cut.rstrip(" ,;:") + "…", True


def _status_parts(status) -> tuple[str, str]:
    """A bill's derived_status -> (seal text, variant). T1.2's bill_status always returns
    {"text", "variant"}, and its variant is trusted (anything else reads as moving). The
    text-prefix guess is only for a bare string."""
    if isinstance(status, dict):
        text = status.get("text") or "No final vote yet"
        variant = status.get("variant")
        return text, variant if variant in ("final", "moving") else "moving"
    text = status or "No final vote yet"
    return text, "final" if text.startswith(_FINAL_SEAL_PREFIXES) else "moving"


def _activity_date(bill: dict) -> str:
    return bill.get("activity_date") or (bill.get("latestAction") or {}).get("actionDate") or ""


def _bill_code(bill: dict) -> str:
    return format_bill_code(str(bill.get("type", "")).lower(), bill.get("number"))


def _month_year(iso: str) -> str:
    long_form = format_date(iso[:10])  # "January 3, 2021"
    if " " not in long_form:  # not an ISO date: format_date returned it unchanged ("2021")
        return long_form
    return f"{long_form.split(' ', 1)[0]} {long_form.rsplit(' ', 1)[1]}"


def _ai_line(ai_updated: str | None) -> str:
    dated = f" · summaries last updated {h(format_date(ai_updated[:10]))}" if ai_updated else ""
    return f'<p class="meta ai-line">{SUMMARY_ATTRIBUTION}{dated}</p>'


def _provisions(provisions) -> str:
    items = "".join(f"<li>{h(p)}</li>" for p in (provisions or [])[:4])
    return f'<ul class="provisions">{items}</ul>' if items else ""


def _full_title(title: str) -> str:
    return f'<details class="full-title"><summary>Show full title</summary><p>{h(title)}</p></details>'


def _tally_label(seal_text: str, chamber: str) -> str:
    """"Passed the House 237–169" -> "Passed the House" for the tally's aria-label."""
    label = re.sub(r"\s*\d+[–-]\d+.*$", "", seal_text or "").strip()
    return label or (f"{chamber} vote" if chamber else "Vote")


def render_seal(text: str, variant: str) -> str:
    """Status seal (spec §6.4). Variants: final, moving, pending, ballot."""
    if variant not in _SEAL_VARIANTS:
        variant = "moving"
    return f'<span class="seal seal--{variant}">{h(text)}</span>'


def render_tally(counts: dict, label: str) -> str:
    """Tally bar (spec §6.4): a role=img track with a spoken summary, and the visible
    numbers in a sibling paragraph. Segment widths are server style= (style-src allows it)."""
    yeas = int(counts.get("yeas") or 0)
    nays = int(counts.get("nays") or 0)
    absent = int(counts.get("absent") or 0)
    total = yeas + nays
    yes_pct = round(yeas * 100 / total, 1) if total else 0
    no_pct = round(100 - yes_pct, 1) if total else 0
    spoken = f"{label}: {yeas} voted yes, {nays} voted no" + (f", {absent} did not vote" if absent else "")
    didnt = f'<span class="meta"> · {absent} didn\'t vote</span>' if absent else ""
    return (
        '<div class="tally">'
        f'<div class="tally-track" role="img" aria-label="{h(spoken)}">'
        f'<span class="tally-seg tally-seg--yes" style="width:{yes_pct}%" data-yes="{yeas}"></span>'
        f'<span class="tally-seg tally-seg--no" style="width:{no_pct}%" data-no="{nays}"></span>'
        "</div>"
        f'<p class="tally-text"><span class="tally-yes">{yeas}</span> yes · '
        f'<span class="tally-no">{nays}</span> no{didnt}</p>'
        "</div>"
    )


def render_latest_vote_card(vote: dict | None, ai_updated: str | None = None) -> str:
    """The Latest Vote (spec §4.1 m3): a structured card, never a sentence template.
    'The latest vote' is an h2 styled as a kicker (§8 item 2). Without data the card
    keeps its place and says so (C-11)."""
    heading = '<h2 class="kicker" id="latest-vote-h">The latest vote</h2>'
    if not vote or not vote.get("bill"):
        return (
            '<aside class="vote-card vote-card--empty" aria-labelledby="latest-vote-h" data-ssr="1">'
            f"{heading}<p class=\"deck\">The latest vote isn't available right now.</p></aside>"
        )
    bill = vote["bill"]
    href = _record_href(bill["congress"], bill["type"], bill["number"])
    chamber = vote.get("chamber") or ""
    dateline = " · ".join(part for part in (
        f"U.S. {chamber}" if chamber else "",
        format_date(vote["date_iso"]) if vote.get("date_iso") else "",
        vote.get("plain_question") or "",
    ) if part)
    if vote.get("has_summary") and vote.get("one_liner"):
        headline = f'<p class="card-headline">{h(vote["one_liner"])}</p>'
        link_text = "What this bill does, in plain English →"
        attribution = _ai_line(ai_updated)
    else:
        title = bill.get("title") or format_bill_code(str(bill["type"]).lower(), bill["number"])
        headline = (f'<p class="card-headline official clamp2">{h(title)}</p>'
                    f'<p class="card-seal">{render_seal(_PENDING_SEAL_TEXT, "pending")}</p>')
        link_text = "See the vote and the official summary →"
        attribution = ""
    seal_text = vote.get("outcome") or ""
    # One roll call's outcome is final only for a simple resolution's adoption (§6.4/§7.2);
    # result_phrase also says "Adopted by the …" for joint and concurrent resolutions.
    simple = str(bill.get("type", "")).lower() in _SIMPLE_RESOLUTIONS
    variant = "final" if simple and seal_text.startswith("Adopted by the") else "moving"
    seal = f'<p class="card-seal">{render_seal(seal_text, variant)}</p>' if seal_text else ""
    return (
        '<aside class="vote-card" aria-labelledby="latest-vote-h" data-ssr="1">'
        f"{heading}"
        f'<p class="dateline meta">{h(dateline)}</p>'
        f"{headline}"
        f"{render_tally(vote.get('counts') or {}, _tally_label(seal_text, chamber))}"
        f"{seal}"
        f'<a class="arrow-link" href="{h(href)}">{link_text}</a>'
        f"{attribution}"
        "</aside>"
    )


def _coverage_sentence(coverage: dict) -> str:
    members = int(coverage.get("members") or 0)
    since = coverage.get("since")
    tail = f" since {h(_month_year(since))}" if since else ""
    return (f"ClearVoting covers California, Florida, New York and Texas today — {members} members "
            f"and every bill that has had a roll-call vote{tail}.")


def render_home_lead(counts: dict, coverage: dict) -> str:
    """Left column of the home lead (spec §4.1 m2): everything a first visit needs, in
    fold order. Module 4's mount is not here: render_home places it after the card."""
    return (
        '<div class="lead-main">'
        '<p class="kicker">An independent record of Congress</p>'
        '<h1 id="home-h1">See how your representatives vote.</h1>'
        '<p class="deck">Dated votes, party labels hidden until you ask.</p>'
        f"{render_zip_form()}"
        '<p class="state-links-label">Or choose a state:</p>'
        f"{render_state_links(counts)}"
        f'<p class="coverage">{_coverage_sentence(coverage)}</p>'
        f"{render_notify_disclosure()}"
        "</div>"
    )


def _record_lead(bill: dict) -> str:
    href = _record_href(bill["congress"], bill["type"], bill["number"])
    code = _bill_code(bill)
    seal_text, variant = _status_parts(bill.get("derived_status"))
    date = _activity_date(bill)
    date_html = f' <span class="meta">{h(format_date(date[:10], short=True))}</span>' if date else ""
    title = bill.get("title") or code
    parts = [
        f'<p class="kicker">{h(code)} · {h(ordinal(int(bill["congress"])))} Congress</p>',
        f'<p class="row-meta">{render_seal(seal_text, variant)}{date_html}</p>',
    ]
    if bill.get("one_liner"):
        official, capped = _cap(title, 140)
        parts += [
            f'<p class="lead-headline"><a href="{h(href)}">{h(bill["one_liner"])}</a></p>',
            _provisions(bill.get("provisions")),
            f'<p class="official-line">Officially: {h(official)}</p>',
            _full_title(title) if capped else "",
            f'<a class="arrow-link" href="{h(href)}">See who voted →</a>',
        ]
    else:
        headline, capped = _cap(title, 140)
        parts += [
            f'<p class="lead-headline official"><a href="{h(href)}">{h(headline)}</a></p>',
            _full_title(title) if capped else "",
            f"<p>{render_seal(_PENDING_SEAL_TEXT, 'pending')}</p>",
        ]
    return f'<article class="record-lead">{"".join(parts)}</article>'


def _record_row(bill: dict) -> str:
    href = _record_href(bill["congress"], bill["type"], bill["number"])
    code = _bill_code(bill)
    seal_text, variant = _status_parts(bill.get("derived_status"))
    date = _activity_date(bill)
    date_html = f'<span class="meta">{h(format_date(date[:10], short=True))}</span>' if date else ""
    if bill.get("one_liner"):
        headline = f'<span class="row-headline">{h(bill["one_liner"])}</span>'
    else:
        headline = (f'<span class="row-headline row-headline--official">{h(bill.get("title") or code)}</span>'
                    f'<span class="row-seal">{render_seal(_PENDING_SEAL_TEXT, "pending")}</span>')
    return (
        f'<li><a class="bill-row" href="{h(href)}">'
        f'<span class="row-meta"><span class="kicker">{h(code)}</span>'
        f"{render_seal(seal_text, variant)}{date_html}</span>"
        f"{headline}</a></li>"
    )


def _latest_summary_block(bill: dict) -> str:
    href = _record_href(bill["congress"], bill["type"], bill["number"])
    date = _activity_date(bill)
    heading = "Most recent plain-English summary" + (f" · {format_date(date[:10], short=True)}" if date else "")
    return (
        '<section class="latest-summary" aria-labelledby="latest-summary-h">'
        f'<h2 id="latest-summary-h">{h(heading)}</h2>'
        f'<p class="kicker">{h(_bill_code(bill))}</p>'
        f'<p class="lead-headline"><a href="{h(href)}">{h(bill["one_liner"])}</a></p>'
        f"{_provisions(bill.get('provisions'))}"
        f'<a class="arrow-link" href="{h(href)}">See who voted →</a>'
        "</section>"
    )


def render_record(bills: list | None, last_sync: str | None, since: str | None = None,
                  latest_summary: dict | None = None, ai_updated: str | None = None) -> str:
    """The Record (spec §4.1 m5): the seven newest bills by activity date, regardless
    of summary; the stamp counts the rows that show an official title."""
    opening = '<section class="record" id="record" aria-labelledby="record-h" data-ssr="1">'
    head = '<p class="kicker">The Record</p><h2 id="record-h">What Congress voted on</h2>'
    if not bills:
        return f"{opening}{head}<p class=\"note\">We couldn't load recent bills right now.</p></section>"
    rows = bills[:7]
    missing = sum(1 for b in rows if not b.get("one_liner"))
    scope = "every bill that has had a roll-call vote"
    if since:
        scope += f" since {h(_month_year(since))}"
    stamp = f"As of {h(format_date(last_sync[:10]))} · {scope}" if last_sync else scope[0].upper() + scope[1:]
    stamp += ", newest activity first"
    if missing == 1:
        stamp += f" · 1 of the {len(rows)} bills below doesn't have a plain-English summary yet and shows its official title"
    elif missing:
        stamp += f" · {missing} of the {len(rows)} bills below don't have a plain-English summary yet and show their official title"
    parts = [opening, head, f'<p class="stamp meta">{stamp}.</p>', _record_lead(rows[0])]
    if len(rows) > 1:
        parts.append(f'<ul class="record-list">{"".join(_record_row(b) for b in rows[1:])}</ul>')
    show_latest = not rows[0].get("one_liner") and latest_summary and latest_summary.get("one_liner")
    if show_latest:
        parts.append(_latest_summary_block(latest_summary))
    if any(b.get("one_liner") for b in rows) or show_latest:
        parts.append(_ai_line(ai_updated))
    parts.append("</section>")
    return "".join(parts)


def render_home(counts: dict, coverage: dict, vote: dict | None, bills: list | None,
                latest_summary: dict | None, last_sync: str | None, ai_updated: str | None) -> str:
    """Home content for <!--content--> (spec §4.1 order): lead + card (m2, m3), the empty
    module-4 mount T4.2 fills for a remembered reader, then the Record (m5). The mount is
    below the finder, so filling it never moves the fold (§9.6). section.lead has no
    aria-label: a named section is a region landmark, and the spec's aside.vote-card
    would then be a complementary landmark nested two deep."""
    return (
        '<section class="lead">'
        f"{render_home_lead(counts, coverage)}{render_latest_vote_card(vote, ai_updated)}"
        "</section>"
        '<div class="home-reps" id="home-reps"></div>'
        f"{render_record(bills, last_sync, coverage.get('since'), latest_summary, ai_updated)}"
    )


# ---------------------------------------------------------------------------
# Delegation page (T4.1): person rows, the state page, the ZIP finder and the
# not-found page (spec §4.2, §5.3, §6.4 person row, §7.4 ballot copy)
# ---------------------------------------------------------------------------

# A lookup view of T3.1's COVERED_STATES tuple (one list of covered states in render.py).
COVERED_STATE_NAMES = dict(COVERED_STATES)
HOUSE_LOOKUP_URL = "https://www.house.gov/representatives/find-your-representative"
_DELEGATION_SITE_URL = "https://clearvoting.org"
_PENDING_SEAL = "No plain-English summary yet"
_COUNT_WORDS = {2: "two", 3: "three", 4: "four"}
_NAME_SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}
_BILL_ID_RE = re.compile(r"^(\d+)-([a-z]+)-(\d+)$")


def _district_int(member: dict) -> int | None:
    district = member.get("district")
    return district if isinstance(district, int) and not isinstance(district, bool) else None


def _initials(full_name: str) -> str:
    words = [w for w in full_name.split() if w.strip(".,").lower() not in _NAME_SUFFIXES]
    letters = [w[0] for w in words if w[:1].isalpha()]
    if not letters:
        return ""
    return (letters[0] + letters[-1]).upper() if len(letters) > 1 else letters[0].upper()


def _bill_title(ds, congress: int, bill_type: str, number: int) -> str:
    # Most roster rows share one bill and get_bill_detail scans, so titles are memoized on
    # the DataService itself: the memo lives and dies with the data it caches, and a new
    # DataService (tests' cache_clear, a reload) starts with an empty one.
    memo = vars(ds).setdefault("_bill_title_memo", {})
    key = (congress, bill_type, number)
    if key not in memo:
        detail = ds.get_bill_detail(congress, bill_type, number)
        memo[key] = str(((detail or {}).get("bill") or {}).get("title") or "")
    return memo[key]


def _latest_vote_fields(latest: dict | None, ds) -> dict | None:
    if not latest:
        return None
    match = _BILL_ID_RE.match(str(latest.get("bill_id") or ""))
    if not match:
        return None
    congress, bill_type, number = int(match.group(1)), match.group(2), int(match.group(3))
    summary = ds.displayable_summary(latest["bill_id"]) or {}
    one_liner = str(summary.get("one_liner") or "")
    code = format_bill_code(bill_type, number)
    chip = position_chip(latest.get("position"))  # T1.2: the one §7.1 table
    date = str(latest.get("date") or "")[:10]
    return {
        **latest,
        "bill_code": code,
        "bill_url": f"/bill?congress={congress}&type={quote(bill_type)}&number={number}",
        "headline": one_liner or _bill_title(ds, congress, bill_type, number) or code,
        "displayable": bool(one_liner),
        "seal": "" if one_liner else _PENDING_SEAL,
        "chip": chip["text"],
        "chip_class": f"chip--{chip['variant']}",
        "date_short": format_date(date, short=True) if date else "",
    }


def overview_member_fields(member: dict, ds=None) -> dict:
    """One state_overview member plus the render-ready fields that the delegation page, the
    home "Your representatives" block and the bill slot use (§10 #7). Raw fields are kept,
    so the router's party strip still decides whether partyName leaves the server."""
    if ds is None:
        from app.dependencies import get_data_service
        ds = get_data_service()
    bioguide = str(member.get("bioguideId") or "")
    name = display_name(str(member.get("name") or ""))
    record = ((ds.get_member_detail(bioguide) if bioguide else None) or {}).get("member") or {}
    tenure = tenure_line(record["terms"]) if record.get("terms") else ""
    senate = "Senate" in str(member.get("chamber") or "")
    district = _district_int(member)
    if senate:
        seat = "U.S. Senator"
    elif district is not None:
        seat = f"District {district}"
    else:
        seat = "U.S. Representative"
    photo = str(member.get("photo") or (record.get("depiction") or {}).get("imageUrl") or "")
    return {
        **member,
        "display_name": name,
        "initials": _initials(name),
        "seat_line": f"{seat} · {tenure}" if tenure else seat,
        "seat_seal": seat_seal(ds.seat_up_2026(member), "row"),
        "url": f"/member?id={quote(bioguide)}",
        "photo": photo if photo.startswith("https://www.congress.gov/") else "",
        "latest_vote": _latest_vote_fields(member.get("latest_vote"), ds),
    }


def _photo(member: dict) -> str:
    src = str(member.get("photo") or "")
    img = (f'<img src="{h(src)}" alt="" loading="lazy" width="56" height="56">'
           if src.startswith("https://www.congress.gov/") else "")
    return f'<span class="photo" data-initials="{h(member.get("initials") or "")}">{img}</span>'


def _signal_line(signal: dict | None) -> str:
    if not signal:
        return '<span class="person-signal">No final votes on bills in our record yet</span>'
    if signal.get("displayable"):
        headline = h(signal.get("headline") or "")
    else:
        headline = (f'<span class="official">{h(signal.get("headline") or "")}</span> '
                    f'<span class="seal seal--pending">{h(signal.get("seal") or _PENDING_SEAL)}</span>')
    dated = f' · {h(signal["date_short"])}' if signal.get("date_short") else ""
    chip_class = h(signal.get("chip_class") or "chip--other")
    return (f'<span class="person-signal">Latest final vote{dated} · {headline} — '
            f'<span class="chip {chip_class}">{h(signal.get("chip") or "")}</span></span>')


def render_person_row(member: dict, signal: dict | None, split: bool = False,
                      state_code: str = "") -> str:
    """The §6.4 person row. By default the whole row is one <a>. With split=True (split and
    partial ZIP pages) the row is a <div> whose name is the link, with a sibling
    "This is my district →" link, so no link sits inside another (F60). Every row carries
    an empty .party span that the reveal fills."""
    bioguide = str(member.get("bioguideId") or "")
    district = _district_int(member)
    district_attr = "" if district is None else str(district)
    href = f"/member?id={quote(bioguide)}"
    attrs = (f' data-bioguide="{h(bioguide)}" data-state="{h(state_code)}"'
             f' data-district="{district_attr}"')
    seal = (f' <span class="seal seal--ballot">{h(member["seat_seal"])}</span>'
            if member.get("seat_seal") else "")
    details = (f' <span class="person-seat">{h(member.get("seat_line") or "")}</span>{seal}'
               f' {_signal_line(signal)} <span class="party"></span>')
    name = h(member.get("display_name") or "")
    if not split:
        return (f'<a class="person" href="{h(href)}"{attrs}>{_photo(member)} '
                f'<span class="person-body"><span class="person-name">{name}</span>{details}</span></a>')
    mine = f"/state?code={quote(state_code)}&district={district_attr}#mine"
    return (f'<div class="person person--split"{attrs}>{_photo(member)} '
            f'<span class="person-body"><a class="person-name" href="{h(href)}">{name}</a>{details}</span> '
            f'<a class="btn btn--secondary" href="{h(mine)}">This is my district →</a></div>')


def _row_list(rows: list[str], css: str) -> str:
    return f'<ul class="{css}">' + "".join(f"<li>{row}</li>" for row in rows) + "</ul>"


def _vacant_row(state_code: str, district: int, *, report: bool = False, mine: bool = False) -> str:
    """A district with no member in members.json. In "Your representatives" (report=True) it
    reads "District 7 — vacant in our data · Tell us if this is wrong" (§4.2, §5.3) as one
    wrapping line: the inline .person-vacancy wrapper keeps the separator out of the row's
    grid. The roster's vacancies (report=False) are the name alone (§4.2 "Vacant districts")."""
    d = int(district)
    body = f'<span class="person-name">District {d} — vacant in our data</span>'
    if report:
        body = (f'<span class="person-vacancy">{body} · <button type="button" class="btn btn--secondary" '
                'data-feedback-open>Tell us if this is wrong</button></span>')
    mine_link = ""
    if mine:
        target = f"/state?code={quote(state_code)}&district={d}#mine"
        mine_link = f' <a class="btn btn--secondary" href="{h(target)}">This is my district →</a>'
    return (f'<div class="person person--vacant" data-state="{h(state_code)}" data-district="{d}">'
            f'<span class="person-body">{body}</span>{mine_link}</div>')


def _zip_note(zip_result: dict, matches: list[dict]) -> str:
    zip5 = h(zip_result.get("zip") or "")
    paras = []
    if len(matches) >= 2:
        word = _COUNT_WORDS.get(len(matches), str(len(matches)))
        first = (f"about {round(float(matches[0]['share']) * 100)} % of the ZIP's land area "
                 f"(not its residents) is in District {int(matches[0]['district'])}")
        others = [f"{round(float(m['share']) * 100)} % in District {int(m['district'])}"
                  for m in matches[1:]]
        if len(others) == 1:
            shares = f"{first} and {others[0]}"
        else:
            shares = f"{first}, " + ", ".join(others[:-1]) + f" and {others[-1]}"
        shown = "Both are shown" if len(matches) == 2 else f"All {word} are shown"
        paras.append(f"<p>ZIP {zip5} spans {word} House districts — {shares}. "
                     f"{shown}; your street address decides which is yours.</p>")
    if zip_result.get("kind") == "partial":
        outside = round((1 - float(zip_result.get("covered_share") or 0)) * 100)
        paras.append(f"<p>About {outside} % of ZIP {zip5}'s land area is outside California, Florida, "
                     "New York and Texas; if you live in that part, we don't cover your state yet.</p>")
    paras.append(f'<p><a class="source-link" href="{HOUSE_LOOKUP_URL}" rel="noopener">'
                 "Not sure? Look up your district by street address on house.gov →</a></p>")
    return '<div class="note">' + "".join(paras) + "</div>"


def _state_header(code: str, state_name: str, count: int, roster_as_of, district: int | None,
                  personal: bool, zip_value: str, error: str) -> str:
    kicker = f"{h(state_name)} · {int(count)} members"
    if roster_as_of:
        kicker += f" · roster as of {h(format_date(str(roster_as_of)[:10]))}"
    title = "Your representatives" if personal else f"{h(state_name)}'s representatives"
    if district is not None:
        where = (f'<p class="district-line">{h(state_name)}, District {int(district)} · '
                 '<a href="/#find">Change ZIP</a></p>'
                 # state.js unhides the button, and after a tap puts site.js's "Remembered: … ·
                 # Change · Forget" line in this wrapper, whose first control Forget refocuses.
                 '<div class="remember">'
                 f'<button type="button" class="btn btn--secondary" id="remember-district" '
                 f'data-state="{h(code)}" data-state-name="{h(state_name)}" '
                 f'data-district="{int(district)}" hidden>Remember District {int(district)} as mine</button>'
                 '</div>')
    else:
        # T3.1's compact ZIP form: the same component as home, one row (§4.2 header).
        where = render_zip_form(compact=True, value=zip_value, error=error or None,
                                form_id="zip-top", label="Where do you live?")
    # The place this page is about, for the feedback dialog's "About: …" line (T2.4): the h1
    # on district and ZIP pages is "Your representatives", which names no state.
    context_label = f"{state_name}, District {int(district)}" if district is not None else state_name
    party_url = f"/api/members/{quote(code)}/overview?show_party=true"
    share_url = f"{_DELEGATION_SITE_URL}/state?code={quote(code)}"
    share_title = f"{state_name}'s Representatives — Voting Records"
    share_text = f"How {state_name}'s members of Congress vote"
    return (f'<section class="state-header" data-state="{h(code)}" data-context-label="{h(context_label)}">'
            f'<p class="kicker">{kicker}</p>'
            f'<h1>{title}</h1>'
            f'{where}'
            '<div class="actions">'
            f'<button class="party-toggle" type="button" data-party-url="{h(party_url)}">Show party labels</button>'
            f'<button class="btn btn--secondary share-btn" type="button" data-share-url="{h(share_url)}" '
            f'data-share-title="{h(share_title)}" data-share-text="{h(share_text)}">Share</button>'
            '</div>'
            '<p class="party-status" role="status"></p>'
            '<p class="share-status" role="status"></p>'
            '<p class="meta">Party labels are hidden so the record speaks first.</p>'
            '<noscript><p class="meta">Party labels and remembering your district need JavaScript'
            '</p></noscript>'
            '</section>')


def _yours_section(code: str, senators: list[dict], by_district: dict[int, list[dict]],
                   district: int | None, zip_result: dict | None, matches: list[dict]) -> str:
    parts = ['<section class="yours" aria-labelledby="yours-h"><h2 id="yours-h">Your representatives</h2>']
    senator_rows = [render_person_row(m, m.get("latest_vote"), state_code=code) for m in senators]
    if district is not None:
        house_rows = [render_person_row(m, m.get("latest_vote"), state_code=code)
                      for m in by_district.get(district, [])]
        rows = senator_rows + (house_rows or [_vacant_row(code, district, report=True)])
        parts.append(_row_list(rows, "reps reps--yours"))
    else:
        parts.append(_row_list(senator_rows, "reps"))
        parts.append(_zip_note(zip_result or {}, matches))
        house_rows = []
        for match in matches:
            d = int(match["district"])
            members = by_district.get(d, [])
            house_rows += ([render_person_row(m, m.get("latest_vote"), split=True, state_code=code)
                            for m in members]
                           or [_vacant_row(code, d, report=True, mine=True)])
        parts.append(_row_list(house_rows, "reps"))
    parts.append("</section>")
    return "".join(parts)


def _senate_section(code: str, state_name: str, senators: list[dict]) -> str:
    rows = [render_person_row(m, m.get("latest_vote"), state_code=code) for m in senators]
    return ('<section class="senate" aria-labelledby="senate-h"><h2 id="senate-h">U.S. Senate</h2>'
            f'<p class="kicker">Both represent all of {h(state_name)}</p>{_row_list(rows, "reps")}</section>')


def _house_section(code: str, state_name: str, house: list[dict], by_district: dict[int, list[dict]],
                   expected: int, personal: bool) -> str:
    rows = []
    for d in range(1, expected + 1):
        members = by_district.get(d)
        if members:
            rows += [render_person_row(m, m.get("latest_vote"), state_code=code) for m in members]
        else:
            rows.append(_vacant_row(code, d))
    rows += [render_person_row(m, m.get("latest_vote"), state_code=code) for m in house
             if not (_district_int(m) is not None and 1 <= _district_int(m) <= expected)]
    listing = _row_list(rows, "roster")
    if personal:
        body = f"<details><summary>All {expected} {h(state_name)} House districts</summary>{listing}</details>"
    else:
        body = f'<p class="kicker">By district, 1–{expected}</p>{listing}'
    return ('<section class="house" id="house" aria-labelledby="house-h">'
            f'<h2 id="house-h">The House, by district</h2>{body}</section>')


def _state_foot(state_name: str, roster_as_of) -> str:
    roster = "Roster from Congress.gov"
    if roster_as_of:
        roster += f", as of {h(format_date(str(roster_as_of)[:10]))}"
    query = json.dumps({"congress": 119, "member-state": state_name}, separators=(",", ":"))
    congress_url = f"https://www.congress.gov/members?q={quote(query)}"
    foot_form = render_zip_form(compact=True, form_id="zip-foot",
                                label="Don't know your district? Enter your ZIP")
    return ('<div class="state-foot">'
            f'{foot_form}'
            f'<p class="meta">{roster} · Wrong person? '
            '<button type="button" class="btn btn--secondary" data-feedback-open>Report an error</button></p>'
            f'<p class="meta"><a class="source-link" href="{h(congress_url)}" rel="noopener">'
            f"{h(state_name)}'s delegation on Congress.gov →</a></p>"
            f'{render_notify_disclosure()}'
            '</div>')


def render_state_page(overview: dict, district: int | None = None, zip_result: dict | None = None,
                      error: str = "", *, ds=None, zip_value: str = "") -> str:
    """The delegation page body (§4.2): header, Your representatives (district or ZIP URLs
    only), U.S. Senate (plain URLs only), The House by district, foot. `district` is an int
    from the query string or None. `zip_result` is a lookup_zip result of kind split or
    partial for this state, or None."""
    code = str(overview.get("state") or "").upper()
    state_name = str(overview.get("state_name") or COVERED_STATE_NAMES.get(code, code))
    senators = sorted((overview_member_fields(m, ds) for m in overview.get("senators") or []),
                      key=lambda m: str(m.get("name") or ""))
    house = sorted((overview_member_fields(m, ds) for m in overview.get("house") or []),
                   key=lambda m: (_district_int(m) or 0, str(m.get("name") or "")))
    by_district: dict[int, list[dict]] = {}
    for member in house:
        d = _district_int(member)
        if d is not None:
            by_district.setdefault(d, []).append(member)
    expected = int(overview.get("districts_expected") or 0) or max(by_district, default=0)
    missing_district = None
    if district is not None and not 1 <= district <= expected:
        missing_district, district = district, None
    matches = [m for m in (zip_result or {}).get("matches") or [] if m.get("state") == code]
    personal = district is not None or bool(matches)

    blocks = [_state_header(code, state_name, len(senators) + len(house), overview.get("roster_as_of"),
                            district, personal, zip_value, error)]
    if missing_district is not None:
        blocks.append(f"<p class=\"note\">We don't have a District {int(missing_district)} in {h(state_name)}</p>")
    if personal:
        blocks.append(_yours_section(code, senators, by_district, district, zip_result, matches))
    else:
        blocks.append(_senate_section(code, state_name, senators))
    blocks.append(_house_section(code, state_name, house, by_district, expected, personal))
    blocks.append(_state_foot(state_name, overview.get("roster_as_of")))
    return '<div class="delegation">' + "".join(blocks) + "</div>"


def render_zip_finder_page(counts: dict, value: str = "", error: str = "") -> str:
    """/state with no code (§4.2 states): the finder H1, the ZIP form, the four state links."""
    return ('<div class="delegation"><section class="finder-page">'
            '<h1>Find your representatives</h1>'
            f'{render_zip_form(value=value, error=error or None, form_id="zip-top")}'
            f'<p class="meta">Or choose a state:</p>{render_state_links(counts)}'
            '</section></div>')


def render_zip_not_found(zip5: str, counts: dict) -> str:
    """/state?zip= with no district at ≥5 % in a covered state (§5.3): the one not-found
    message, the form, the four state links, then the notify disclosure."""
    z = h(zip5)
    message = (f"We couldn't match ZIP {z} to a congressional district in California, Florida, New York or "
               "Texas — the four states ClearVoting covers. If you live in one of them, your ZIP may be a "
               "PO-box or business ZIP: choose your state below, or "
               f'<a href="{HOUSE_LOOKUP_URL}" rel="noopener">look up your district by street address on '
               "house.gov →</a>. Somewhere else? Tell us your state and we'll email you when we add it.")
    return ('<div class="delegation"><section class="finder-page">'
            '<h1>Find your representatives</h1>'
            f'<div class="note"><p>{message}</p></div>'
            f'{render_zip_form(value=zip5, form_id="zip-top")}'
            f'<p class="meta">Or choose a state:</p>{render_state_links(counts)}'
            f'{render_notify_disclosure()}'
            '</section></div>')


# ---------------------------------------------------------------------------
# Trust pages: About counts, Methodology blocks, the 404 body (plan Task T5.1)
# ---------------------------------------------------------------------------

_TRUST_STATE_NAMES = {"CA": "California", "FL": "Florida", "NY": "New York", "TX": "Texas"}
_TRUST_NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten")
_PROMPT_RULE_RE = re.compile(r"^(\d+)\.\s+(.+)$")
_TRUST_CROSSWALK_PREFIX = "https://www2.census.gov/"
_TRUST_SENATE_PREFIX = "https://www.senate.gov/"


def prompt_rules(prompt: str) -> dict[str, list[str]]:
    """The two numbered rule lists of the bill-summary prompt, verbatim.

    "STRICT RULES:" opens the neutrality list and "ACCURACY RULES" the accuracy list;
    a blank line after a list's items ends it. /methodology prints both, and a test
    checks the page equals the prompt, so the page can never drift from the prompt."""
    lists: dict[str, list[str]] = {"neutrality": [], "accuracy": []}
    current = None
    for line in prompt.splitlines():
        stripped = line.strip()
        if stripped.startswith("STRICT RULES"):
            current = "neutrality"
            continue
        if stripped.startswith("ACCURACY RULES"):
            current = "accuracy"
            continue
        if not stripped:
            if current and lists[current]:
                current = None
            continue
        match = _PROMPT_RULE_RE.match(stripped)
        if current and match:
            lists[current].append(match.group(2))
    return lists


def _trust_count(n) -> str:
    return f"{int(n):,}"


def _trust_number_word(n: int) -> str:
    return _TRUST_NUMBER_WORDS[n] if 0 <= n < len(_TRUST_NUMBER_WORDS) else f"{n:,}"


def _trust_iso(value) -> str | None:
    """The YYYY-MM-DD prefix of value when it is a real date, else None."""
    if not value:
        return None
    text = str(value)[:10]
    try:
        date.fromisoformat(text)
    except ValueError:
        return None
    return text


def _trust_month_year(value) -> str | None:
    iso = _trust_iso(value)
    return date.fromisoformat(iso).strftime("%B %Y") if iso else None


def _trust_long_date(value) -> str | None:
    iso = _trust_iso(value)
    return format_date(iso) if iso else None


def _trust_links(url_field, prefix: str) -> str:
    """Anchors for a _source url field ("A and B" allowed); only https URLs under prefix."""
    urls = [u.strip() for u in str(url_field or "").split(" and ")]
    return " · ".join(f'<a href="{h(u)}">{h(u)}</a>' for u in urls if u.startswith(prefix))


def _trust_section(anchor: str, heading: str, body: str) -> str:
    # anchor and heading are literals from this module, never data.
    return (f'<section id="{anchor}" aria-labelledby="{anchor}-h">'
            f'<h2 id="{anchor}-h">{heading}</h2>{body}</section>')


def render_about_counts(counts: dict) -> str:
    """The "What we cover" sentence on /about (spec §4.5), from the /api/health counts."""
    since = _trust_month_year(counts.get("since"))
    scope = "every bill that has had a roll-call vote" + (f" since {h(since)}" if since else "")
    return (
        f"<p>California, Florida, New York and Texas today: {_trust_count(counts['members'])} members "
        f"and {_trust_count(counts['bills'])} bills — {scope}. The site is in English only for now.</p>"
    )


def _methodology_coverage(counts: dict) -> str:
    since = _trust_month_year(counts.get("since"))
    since_txt = f" since {h(since)}" if since else ""
    return _trust_section("coverage", "What we cover", (
        f"<p>ClearVoting holds {_trust_count(counts['bills'])} bills — every bill that has had a "
        f"roll-call vote{since_txt} in the House or Senate. Bills that never reached a roll-call vote "
        "are not in our data.</p>"
        "<p>Senate records on member pages include votes on bills, amendments and motions; the "
        f"{_trust_count(counts['nominations'])} Senate votes on nominations{since_txt} aren't included "
        "yet. House records include every House roll call.</p>"
    ))


def _methodology_ai(counts: dict, rules: dict) -> str:
    neutrality = rules.get("neutrality", [])
    accuracy = rules.get("accuracy", [])
    updated = _trust_long_date(counts.get("ai_summaries_updated"))
    updated_txt = f" Plain-English summaries were last updated {h(updated)}." if updated else ""
    return _trust_section("ai", "What AI writes, and what it never touches", (
        "<p>An AI model writes each bill's one-line summary and its list of provisions, from the "
        "bill's title, official summary and a text excerpt. It never touches votes, tallies, dates, "
        "names, outcomes or party.</p>"
        "<h3>Our rules for neutrality</h3>"
        "<p>The AI is given these rules, word for word, every time it writes a summary:</p>"
        '<ol class="rules" id="neutrality-rules">'
        + "".join(f"<li>{h(rule)}</li>" for rule in neutrality)
        + "</ol>"
        "<h3>Our rules for accuracy</h3>"
        f'<ol class="rules" id="accuracy-rules" start="{len(neutrality) + 1}">'
        + "".join(f"<li>{h(rule)}</li>" for rule in accuracy)
        + "</ol>"
        f"<p>{_trust_count(counts['shown'])} of {_trust_count(counts['bills'])} bills have a "
        f"plain-English summary. {_trust_count(counts['missing'])} have none yet, and "
        f"{_trust_count(counts['withheld'])} summaries are withheld because they did not pass our "
        f"automated accuracy check; those bills show their official title.{updated_txt}</p>"
        f"<p>{_trust_count(counts['audited'])} summaries were spot-checked by a second AI review.</p>"
        "<p>Member summaries are withdrawn until they can be rewritten without stance labels.</p>"
        "<p>We do not publish arguments for or against a bill. An earlier version showed AI-drafted "
        "'supporters say / critics say' bullets; they were unattributed and have been removed until "
        "they can be sourced.</p>"
    ))


def _methodology_recent_votes() -> str:
    # The rule exactly as DataService.get_member_page applies it (spec §4.3 m2).
    return _trust_section("recent-votes", "How “Recent votes” are chosen", (
        "<p>The “Recent votes” list on each member page is chosen by one rule, and the rule never "
        "looks at how the member voted:</p>"
        "<ol>"
        "<li>We consider the member's roll-call votes on a bill that has a plain-English summary we "
        "show and a policy area, where the vote was on the bill itself — a final vote to pass or "
        "adopt it, to accept the other chamber's changes, to override a veto or to ratify a treaty — "
        "and the member voted yes (Yea or Aye) or no (Nay or No).</li>"
        "<li>Going from newest to oldest, we keep the first such vote on each bill. A bill counts as "
        "used only once one of its votes is picked, so a vote the member missed never hides one they "
        "cast.</li>"
        "<li>We take one vote per policy area in turn, starting with the area whose newest vote is "
        "most recent, and go round the areas again until we have eight. So the first pick is always "
        "the newest qualifying vote.</li>"
        "<li>The eight are shown newest first. A member with fewer qualifying votes shows as many as "
        "qualify.</li>"
        "</ol>"
        "<p>Amendments, procedural motions and votes on nominations are never in this list. Every "
        "vote in our record is in the member's full record below it; Senate votes on nominations "
        "are not in our record yet (see What we cover).</p>"
    ))


def _methodology_counts() -> str:
    return _trust_section("counts", "Counts, never grades", (
        "<p>We show roll calls voted as a count, never as a grade, and never rank members by it.</p>"
        "<p>A member page says how many of the roll calls in our record the member voted in, and "
        "since when. It never turns that into a percentage, a colour or a score.</p>"
    ))


def _methodology_zip(sources: dict) -> str:
    source_p = ""
    if sources.get("name"):
        retrieved = _trust_long_date(sources.get("retrieved"))
        source_p = (
            f"<p>Source: {h(sources['name'])}"
            + (f" ({h(sources['licence'])})" if sources.get("licence") else "")
            + (f", retrieved {h(retrieved)}" if retrieved else "")
            + ".</p>"
        )
    links = _trust_links(sources.get("url"), _TRUST_CROSSWALK_PREFIX)
    return _trust_section("zip", "ZIP codes and districts", (
        "<p>To find your representatives from a ZIP code, we use the Census Bureau's table of which "
        "congressional districts each ZIP code area overlaps.</p>"
        + source_p
        + (f'<p class="meta">{links}</p>' if links else "")
        + "<p>Shares are land area, not population; PO-box-only and business ZIPs are not in the "
        "Census file; a ZIP that crosses a state line is shown with a note.</p>"
        "<p>A district counts as a match when it covers at least 5 % of the ZIP's land area. When one "
        "district matches and at least 95 % of the ZIP's land is in California, Florida, New York or "
        "Texas, we take you straight to that district. When two to four districts match, we show "
        "each one with its share and you choose. When less than 95 % of the ZIP's land is in our four "
        "states, we show the match with a note and remember it only if you choose it.</p>"
        # Same link and copy as T4.1's split/partial note (spec §5.5: rel=noopener, same tab).
        f'<p><a class="source-link" href="{HOUSE_LOOKUP_URL}" rel="noopener">'
        "Not sure? Look up your district by street address on house.gov →</a></p>"
    ))


def _methodology_ballot(counts: dict, senate: dict) -> str:
    day = _trust_long_date(senate.get("election_day"))
    if not day:
        return _trust_section("ballot", "Seats on the ballot",
                              "<p>Ballot details aren't available right now.</p>")
    clauses = []
    for seat in senate.get("seats", []):
        state = _TRUST_STATE_NAMES.get(seat.get("state"))
        if not state:
            continue
        name = h(display_name(seat.get("name") or ""))
        if seat.get("kind") == "special":
            clauses.append(f"the {state} seat held by {name} is up in a special election")
        else:
            clauses.append(f"the {state} seat held by {name} is up for its regular election")
    senators = _trust_number_word(int(counts.get("senators", 0)))
    if clauses:
        joined = clauses[0] if len(clauses) == 1 else ", ".join(clauses[:-1]) + " and " + clauses[-1]
        senate_txt = f"Of the {senators} senators we cover, {joined}."
    else:
        senate_txt = f"None of the Senate seats held by the {senators} senators we cover is up in this election."
    source = senate.get("_source") or {}
    retrieved = _trust_long_date(source.get("retrieved"))
    source_txt = " Source: senate.gov class lists" + (f", retrieved {h(retrieved)}" if retrieved else "") + "."
    links = _trust_links(source.get("url"), _TRUST_SENATE_PREFIX)
    # _source.method names party letters; it is never rendered.
    return _trust_section("ballot", "Seats on the ballot", (
        f"<p>Every House seat is on the ballot on {h(day)}. {senate_txt}{source_txt}</p>"
        + (f'<p class="meta">{links}</p>' if links else "")
        + "<p>These are facts about the seats, not about the people in them: our data does not say "
        "who is running.</p>"
    ))


def render_methodology(counts: dict, sources: dict, rules: dict[str, list[str]], senate_source: dict) -> str:
    """The server-filled run of /methodology, #coverage through #ballot (spec §4.6).

    counts: main._trust_counts(); sources: DataService._crosswalk_source (the _source block of
    zip_districts.json); rules: prompt_rules(SYSTEM_PROMPT); senate_source: DataService._senate_file
    (the whole senate_2026.json). All three data inputs were loaded at startup."""
    return "".join([
        _methodology_coverage(counts),
        _methodology_ai(counts, rules),
        _methodology_recent_votes(),
        _methodology_counts(),
        _methodology_zip(sources),
        _methodology_ballot(counts, senate_source),
    ])


def render_not_found(zip_form: str, state_links: str) -> str:
    """The 404 body (spec §4.8): kicker, the only heading, one sentence, the ZIP form, the four
    state links and a front-page link. Both arguments are HTML built by render_zip_form and
    render_state_links."""
    return (
        '<section class="notfound">'
        '<p class="kicker">Not in this edition</p>'
        "<h1>We don't have that page</h1>"
        '<p class="deck">The link may be old, or the bill or member may be outside our four-state '
        "coverage.</p>"
        f"{zip_form}{state_links}"
        '<p><a href="/">Go to the front page →</a></p>'
        "</section>"
    )
