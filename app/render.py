"""Pure formatters shared by the server-rendered pages and the API (spec §7, §9.1).

Every function here is pure: no I/O, no DataService access. site.js mirrors the
tables in this module (QUESTION_CLASSES here; the bill-type map arrives with the
naming formatters) and a parity test keeps the two in step, so the Python and JS
vocabularies can never drift apart.
"""
import re
from datetime import date

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
