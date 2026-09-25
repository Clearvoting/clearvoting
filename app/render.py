"""Pure formatters shared by the server-rendered pages and the API (spec §7, §9.1).

Every function here is pure: no I/O, no DataService access. site.js mirrors the
tables in this module (QUESTION_CLASSES here; the bill-type map arrives with the
naming formatters) and a parity test keeps the two in step, so the Python and JS
vocabularies can never drift apart.
"""
import html
import re
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
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
        '<a href="/about">Privacy →</a></p>'  # T5.1 repoints this to /privacy
        '<p class="notify-status" id="notify-status" role="status" tabindex="-1"></p>'
        "</form>"
        '<noscript><p class="meta">Signing up needs JavaScript.</p></noscript>'
        "</details>"
    )
