"""Unit tests for the pure formatters in app/render.py (spec §7.1-§7.5)."""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app import render
from app.render import (
    QUESTION_CLASSES,
    bill_status,
    format_date,
    outcome_sentence,
    parse_threshold,
    plain_question,
    position_chip,
    question_class,
    result_phrase,
)

FIXTURES = Path(__file__).parent / "fixtures" / "synced"
REAL_VOTES = Path(__file__).parent.parent / "data" / "synced" / "votes"
FORBIDDEN = ("blocked", "let the veto stand", "taken up")


def _rc(question, result, counts, iso_date="2026-09-03"):
    """A votes_index.json roll_calls entry (the fields the formatters read)."""
    return {"question": question, "plain": plain_question(question), "class": question_class(question),
            "result": result, "counts": counts, "date": iso_date, "threshold": None}


def _phrase(question, result, counts, chamber="House"):
    return result_phrase(_rc(question, result, counts), chamber)


def _sentence(question, result, counts, chamber, iso_date):
    return outcome_sentence(_rc(question, result, counts, iso_date), chamber)


# --- §7.1 question classes: every table row, real question strings ---

@pytest.mark.parametrize("question, cls, plain", [
    ("On Passage", "D", "Final vote to pass"),
    ("On Passage of the Bill H.R. 6500", "D", "Final vote to pass"),
    ("On Motion to Suspend the Rules and Pass, as Amended", "D", "Vote to pass (fast-track, needed two-thirds)"),
    ("On Motion to Suspend the Rules and Pass Certain Bills", "D", "Vote to pass (fast-track, needed two-thirds)"),
    ("On Agreeing to the Resolution, as Amended", "D", "Vote to adopt"),
    ("On the Resolution S.Res. 817", "D", "Vote to adopt"),
    ("On the Joint Resolution S.J.Res. 10", "D", "Vote to adopt"),
    ("On the Concurrent Resolution H.Con.Res. 86", "D", "Vote to adopt"),
    ("On Motion to Suspend the Rules and Agree to the Resolution", "D",
     "Vote to adopt (fast-track, needed two-thirds)"),
    ("On Motion to Concur in the Senate Amendment", "D", "Vote to accept the other chamber's changes"),
    ("On Motion to Suspend the Rules and Concur in the Senate Amendment", "D",
     "Vote to accept the other chamber's changes"),
    ("On the Motion (Motion to Concur in the House Amendment to the Senate Amendment to H.R. 6644)", "D",
     "Vote to accept the other chamber's changes"),
    # Named Senate concurrences: the final Senate votes on two omnibus laws (real strings).
    ("On the Motion (Schumer Motion to Concur in the House Amendment to the Senate Amendment to H.R. 4366)",
     "D", "Vote to accept the other chamber's changes"),
    ("On the Motion (Senate Concurs in the House Amendment to the Senate Amendment to H.R. 2471)", "D",
     "Vote to accept the other chamber's changes"),
    # A named senator's concur-with-an-amendment stays procedural (real string).
    ("On the Motion (Hagerty Motion to Concur in the House Amendment to the Senate Amendment to H.R. 4366 "
     "with an Amendment No. 1634)", "P", "Procedural vote"),
    ("Passage, Objections of the President To The Contrary Notwithstanding", "D",
     "Vote to override the veto (needed two-thirds)"),
    ("On Overriding the Veto S.J.Res. 32", "D", "Vote to override the veto (needed two-thirds)"),
    ("On the Resolution of Ratification Treaty Doc. 117-1", "D", "Vote to ratify a treaty (needed two-thirds)"),
    ("Guilty or Not Guilty H.Res. 24", "D", "Verdict on an article of impeachment (needed two-thirds)"),
    ("On Agreeing to the Amendment", "P", "Vote on an amendment"),
    ("On the Amendment S.Amdt. 6715 to S.Amdt. 6711 to H.R. 5334 (No short title on file)", "P",
     "Vote on an amendment"),
    ("On Cloture on the Motion to Proceed S. 5271", "P", "Vote to end debate (needed 60)"),
    ("On the Cloture Motion H.R. 6644", "P", "Vote to end debate (needed 60)"),
    ("On the Motion to Proceed S. 1071", "P", "Vote to take it up"),
    ("On the Motion (Motion to Proceed to S.J.Res. 10)", "P", "Vote to take it up"),
    ("On Motion to Recommit", "P", "Vote to send it back to committee"),
    ("On Motion to Commit with Instructions", "P", "Vote to send it back to committee"),
    ("On Motion to Refer", "P", "Vote to send it back to committee"),
    ("On the Motion (Scott (FL) Motion to Commit H.R. 1319 to Committee on Homeland Security)", "P",
     "Vote to send it back to committee"),
    ("On Motion to Table", "P", "Vote to set it aside"),
    ("Table Motion to Reconsider", "P", "Vote to set it aside"),
    ("On Ordering the Previous Question", "P", "Vote to end debate on the rule"),
    ("On the Motion to Discharge S.J.Res. 181", "P", "Vote to bring it to the floor"),
    ("On the Motion (Motion to Waive All Applicable Budgetary Discipline Re: S. 2)", "P",
     "Vote to waive a budget rule (needed 60)"),
    ("On the Point of Order S.J.Res. 124", "P", "Vote on a point of order"),
    ("On the Nomination PN12-1", "P", "Vote to confirm"),
    ("Election of the Speaker", "P", "Election of the Speaker"),
    ("On Motion to Adjourn", "P", "Vote to adjourn"),
    ("Call of the House", "P", "Attendance call"),
    ("On the Motion for Attendance H.R. 3935", "P", "Attendance call"),
    ("On Retaining Title V", "P", "Procedural vote"),
    ("On the Motion (Motion to Recess for Ten Minutes)", "P", "Procedural vote"),
    ("", "P", "Procedural vote"),
    (None, "P", "Procedural vote"),
])
def test_question_class_table(question, cls, plain):
    assert question_class(question) == cls
    assert plain_question(question) == plain


def test_question_classes_are_js_mirrorable():
    # site.js builds new RegExp(row.pattern, "i") from these; no Python-only syntax.
    for row in QUESTION_CLASSES:
        source = row["pattern"].pattern
        for python_only in ("(?P<", "(?P=", "(?<", "\\A", "\\Z", "(?i", "(?x"):
            assert python_only not in source, source
        assert row["pattern"].flags & re.IGNORECASE
        assert row["class"] in ("D", "P")
    assert len({row["plain"] for row in QUESTION_CLASSES}) == len(QUESTION_CLASSES)


def test_question_class_over_fixture_roll_calls():
    for path in sorted((FIXTURES / "votes").glob("*/*.json")):
        vote = json.loads(path.read_text())
        assert question_class(vote.get("question")) in ("D", "P"), path.name
    rc = json.loads((FIXTURES / "votes" / "senate" / "119_2_00231.json").read_text())
    assert question_class(rc["question"]) == "P"
    rc = json.loads((FIXTURES / "votes" / "house" / "119_2_00295.json").read_text())
    assert question_class(rc["question"]) == "D"


@pytest.mark.skipif(not REAL_VOTES.exists(), reason="real data/synced/votes not present")
def test_every_real_bill_with_a_decisive_vote_gets_a_status_seal():
    from app.services.data_service import DataService, _parse_vote_date

    bills = {
        f"{b['congress']}-{b['type'].lower()}-{b['number']}": b
        for b in json.loads((REAL_VOTES.parent / "bills.json").read_text())["bills"]
    }
    latest: dict[str, dict] = {}
    outputs = []
    for path in REAL_VOTES.glob("*/*.json"):
        vote = json.loads(path.read_text())
        chamber = "Senate" if path.parent.name == "senate" else "House"
        rc = _rc(vote.get("question"), vote.get("result"), vote.get("counts"))
        outputs.append(result_phrase(rc, chamber))
        outputs.append(outcome_sentence(rc, chamber) or "")
        parsed = DataService._parse_bill_document(vote.get("document", ""))
        if rc["class"] != "D" or not parsed:
            continue
        key = f"{vote['congress']}-{parsed[0]}-{parsed[1]}"
        if key not in bills:
            continue
        when = _parse_vote_date(vote.get("vote_date", ""))
        rc["date"] = when.strftime("%Y-%m-%d") if when else ""
        rc["n"] = vote.get("vote_number") or 0
        current = latest.setdefault(key, {}).get(chamber)
        if current is None or (rc["date"], rc["n"]) > (current["date"], current["n"]):
            latest[key][chamber] = rc
    for key, per_chamber in latest.items():
        status = bill_status(bills[key].get("laws"), per_chamber, bills[key]["type"])
        assert status["text"] != "No final vote yet", key
    # "115 bills with no decisive vote" (spec §7.1) is approximate: the real
    # number is whatever this table yields, and it must stay a small minority.
    without_d = len(set(bills) - set(latest))
    assert 0 < without_d < len(bills) / 10
    joined = " ".join(outputs).lower()
    for word in FORBIDDEN:
        assert word not in joined


# --- §7.2 thresholds, seals and outcome phrases ---

def test_parse_threshold():
    assert parse_threshold("Cloture on the Motion to Proceed Rejected (52-46, 3/5 majority required)") == "3/5"
    assert parse_threshold("Veto Sustained (60-37, 2/3 majority required)") == "2/3"
    assert parse_threshold("Passed", "Vote to pass (fast-track, needed two-thirds)") == "2/3"
    assert parse_threshold("Passed", "Final vote to pass") is None
    # The concur row has no threshold, but a suspension question implies two-thirds (16 real
    # "On Motion to Suspend the Rules and Concur…" roll calls); same rule as site.js twoThirdsNeeded.
    concur = "Vote to accept the other chamber's changes"
    assert parse_threshold("Failed", concur, "On Motion to Suspend the Rules and Concur in the Senate Amendment") == "2/3"
    assert parse_threshold("Passed", concur, "On Motion to Concur in the Senate Amendment") is None
    assert parse_threshold("Passed", "Procedural vote", "On Motion to Refer the Veto Message") is None


@pytest.mark.parametrize("question, result, counts, chamber, seal", [
    ("On Passage", "Passed", {"yeas": 237, "nays": 169}, "House", "Passed the House 237–169"),
    ("On Passage of the Bill H.R. 6500", "Bill Passed (90-6, 3/5 majority required)",
     {"yeas": 90, "nays": 6}, "Senate", "Passed the Senate 90–6"),
    ("On Agreeing to the Resolution", "Passed", {"yeas": 220, "nays": 210}, "House",
     "Adopted by the House 220–210"),
    ("On the Joint Resolution S.J.Res. 10", "Joint Resolution Defeated (49-51)", {"yeas": 49, "nays": 51},
     "Senate", "Rejected by the Senate 49–51"),
    ("On Passage", "Failed", {"yeas": 189, "nays": 235}, "House", "Rejected by the House 189–235"),
    ("On Motion to Suspend the Rules and Pass", "Failed", {"yeas": 250, "nays": 170}, "House",
     "Rejected by the House 250–170 (two-thirds needed)"),
    ("Passage, Objections of the President To The Contrary Notwithstanding", "Passed",
     {"yeas": 290, "nays": 130}, "House", "Veto overridden in the House 290–130"),
    ("Passage, Objections of the President To The Contrary Notwithstanding", "Failed",
     {"yeas": 250, "nays": 170}, "House", "Veto override failed 250–170 (two-thirds needed)"),
    ("On Overriding the Veto S.J.Res. 32", "Veto Sustained (60-37, 2/3 majority required)",
     {"yeas": 60, "nays": 37}, "Senate", "Veto override failed 60–37 (two-thirds needed)"),
    ("Guilty or Not Guilty H.Res. 24", "Not Guilty", {"yeas": 57, "nays": 43}, "Senate",
     "Not guilty 57–43 (two-thirds needed)"),
    ("On the Cloture Motion H.R. 6644", "Cloture Motion Agreed to (89-4, 3/5 majority required)",
     {"yeas": 89, "nays": 4}, "Senate", "Debate ended 89–4"),
    ("On Cloture on the Motion to Proceed S. 5271",
     "Cloture on the Motion to Proceed Rejected (52-46, 3/5 majority required)",
     {"yeas": 52, "nays": 46}, "Senate", "Debate not ended 52–46 (60 needed)"),
    ("On the Amendment S.Amdt. 1", "Amendment Agreed to (60-38)", {"yeas": 60, "nays": 38}, "Senate",
     "Amendment adopted 60–38"),
    ("On Agreeing to the Amendment", "Failed", {"yeas": 45, "nays": 53}, "House",
     "Amendment rejected 45–53"),
    ("On the Motion to Proceed S. 1071", "Motion to Proceed Agreed to (55-44)", {"yeas": 55, "nays": 44},
     "Senate", "Motion agreed to 55–44"),
    ("On Motion to Recommit", "Failed", {"yeas": 189, "nays": 235}, "House", "Motion rejected 189–235"),
    ("On the Motion (Motion to Waive All Applicable Budgetary Discipline Re: S. 2)",
     "Motion Rejected (52-47, 3/5 majority required)", {"yeas": 52, "nays": 47}, "Senate",
     "Motion rejected 52–47 (60 needed)"),
    ("Election of the Speaker", "Johnson (LA)", {"yeas": 0, "nays": 0}, "House", "Speaker elected"),
    ("On the Motion to Proceed H.R. 1319",
     "Motion to Proceed Agreed to (50-50, Vice President of the United States, voted Yea)",
     {"yeas": 50, "nays": 50}, "Senate", "Tied 50–50 — agreed to on the Vice President's vote"),
    ("On the Amendment S.Amdt. 889", "Amendment Rejected (50-50)", {"yeas": 50, "nays": 50}, "Senate",
     "Tied 50–50 — motion failed"),
    ("On the Point of Order S.J.Res. 124", "Point of Order Well Taken (51-47)", {"yeas": 51, "nays": 47},
     "Senate", "Point of Order Well Taken"),
])
def test_result_phrase(question, result, counts, chamber, seal):
    assert _phrase(question, result, counts, chamber) == seal


def test_result_phrase_reads_the_index_threshold_and_any_chamber_spelling():
    rc = _rc("On Passage", "Failed", {"yeas": 250, "nays": 170})
    rc["threshold"] = "2/3"
    assert result_phrase(rc, "house") == "Rejected by the House 250–170 (two-thirds needed)"
    rc = _rc("On Passage", "Passed", {"yeas": 237, "nays": 169})
    del rc["plain"], rc["class"]  # classified from the question string
    assert result_phrase(rc, "House of Representatives") == "Passed the House 237–169"


# --- §7.3 outcome sentences ---

@pytest.mark.parametrize("question, result, counts, chamber, iso_date, sentence", [
    ("On Passage", "Passed", {"yeas": 237, "nays": 169}, "House", "2026-09-03",
     "The House passed it, 237 to 169, on September 3, 2026."),
    ("On Agreeing to the Resolution", "Passed", {"yeas": 220, "nays": 210}, "House", "2026-06-10",
     "The House adopted it, 220 to 210, on June 10, 2026."),
    ("On the Motion (Motion to Concur in the House Amendment to the Senate Amendment to H.R. 6644)",
     "Motion Agreed to (85-5)", {"yeas": 85, "nays": 5}, "Senate", "2026-06-22",
     "The Senate accepted the House's changes, 85 to 5, on June 22, 2026."),
    ("On Passage", "Failed", {"yeas": 189, "nays": 235}, "House", "2026-02-04",
     "The House rejected it, 189 to 235, on February 4, 2026."),
    ("On Motion to Suspend the Rules and Pass", "Failed", {"yeas": 250, "nays": 170}, "House", "2026-02-04",
     "The House rejected it, 250 to 170, on February 4, 2026; two-thirds were needed."),
    ("Passage, Objections of the President To The Contrary Notwithstanding", "Failed",
     {"yeas": 250, "nays": 170}, "House", "2026-02-04",
     "The House did not override the veto, 250 to 170, on February 4, 2026."),
    ("On the Motion (Wyden Motion to Commit S. 2 to the Committee on Finance)", "Motion Rejected (45-53)",
     {"yeas": 45, "nays": 53}, "Senate", "2026-08-08",
     "On August 8, 2026, the Senate rejected a motion to send it back to committee, 45 to 53."),
    ("On Cloture on the Motion to Proceed S. 5271",
     "Cloture on the Motion to Proceed Rejected (52-46, 3/5 majority required)",
     {"yeas": 52, "nays": 46}, "Senate", "2026-08-08",
     "On August 8, 2026, the Senate voted 52 to 46 to end debate; 60 votes were needed, so debate did not end."),
    ("On the Cloture Motion H.R. 6644", "Cloture Motion Agreed to (84-8, 3/5 majority required)",
     {"yeas": 84, "nays": 8}, "Senate", "2026-06-18",
     "On June 18, 2026, the Senate voted to end debate, 84 to 8."),
    ("On the Amendment S.Amdt. 6715", "Amendment Rejected (32-64)", {"yeas": 32, "nays": 64}, "Senate",
     "2026-08-07", "On August 7, 2026, the Senate rejected an amendment, 32 to 64."),
    ("On the Motion to Proceed H.R. 1319",
     "Motion to Proceed Agreed to (50-50, Vice President of the United States, voted Yea)",
     {"yeas": 50, "nays": 50}, "Senate", "2021-03-06",
     "The Senate tied, 50 to 50, on March 6, 2021; the motion passed on the Vice President's vote."),
    ("On the Amendment S.Amdt. 889", "Amendment Rejected (50-50)", {"yeas": 50, "nays": 50}, "Senate",
     "2021-03-25", "The Senate tied, 50 to 50, on March 25, 2021; the motion failed."),
    ("Guilty or Not Guilty H.Res. 24", "Not Guilty", {"yeas": 57, "nays": 43}, "Senate", "2021-02-13",
     "On February 13, 2021, the Senate voted 57 to 43; two-thirds were needed to convict."),
    ("On the Point of Order S.J.Res. 124", "Point of Order Well Taken (51-47)", {"yeas": 51, "nays": 47},
     "Senate", "2026-04-28", "On April 28, 2026, the Senate voted 51 to 47: Point of Order Well Taken."),
])
def test_outcome_sentence(question, result, counts, chamber, iso_date, sentence):
    assert _sentence(question, result, counts, chamber, iso_date) == sentence


def test_outcome_sentence_none_for_speaker_and_nomination():
    assert _sentence("Election of the Speaker", "Johnson (LA)", {}, "House", "2025-01-03") is None
    assert _sentence("On the Nomination PN12-1", "Nomination Confirmed (50-35)",
                     {"yeas": 50, "nays": 35}, "Senate", "2026-01-05") is None


def test_no_forbidden_words_over_fixture_roll_calls():
    outputs = []
    for path in sorted((FIXTURES / "votes").glob("*/*.json")):
        vote = json.loads(path.read_text())
        chamber = "Senate" if path.parent.name == "senate" else "House"
        rc = _rc(vote.get("question"), vote.get("result"), vote.get("counts"))
        outputs += [rc["plain"], result_phrase(rc, chamber), outcome_sentence(rc, chamber) or ""]
    joined = " ".join(outputs).lower()
    for word in FORBIDDEN:
        assert word not in joined


# --- §7.2 bill status seal ---

def _d(plain, result, yeas, nays, iso_date, bill=None):
    return {"plain": plain, "class": "D", "result": result, "counts": {"yeas": yeas, "nays": nays},
            "date": iso_date, "bill": bill}


PASS = "Final vote to pass"
ADOPT = "Vote to adopt"


def test_bill_status_became_law_wins():
    laws = [{"number": "119-6", "type": "Public Law"}]
    assert bill_status(laws, {"House": _d(PASS, "Failed", 1, 2, "2026-01-01")}, "hr") == {
        "text": "Became law", "variant": "final"}


def test_bill_status_both_chambers():
    latest = {"House": _d(PASS, "Passed", 237, 169, "2026-09-03"),
              "Senate": _d(PASS, "Bill Passed (90-6)", 90, 6, "2026-09-10")}
    assert bill_status(None, latest, "hr") == {"text": "Passed both chambers", "variant": "final"}


def test_bill_status_one_chamber_is_moving_unless_simple_resolution():
    assert bill_status([], {"House": _d(PASS, "Passed", 237, 169, "2026-09-03"), "Senate": None}, "hr") == {
        "text": "Passed the House 237–169", "variant": "moving"}
    assert bill_status([], {"House": _d(ADOPT, "Passed", 220, 210, "2026-09-03")}, "hres") == {
        "text": "Adopted by the House 220–210", "variant": "final"}
    assert bill_status([], {"Senate": _d(ADOPT, "Joint Resolution Passed (51-47)", 51, 47, "2026-05-01")},
                       "sjres") == {"text": "Adopted by the Senate 51–47", "variant": "moving"}
    # Without bill_type, the simple resolution is recognised from the roll call's bill key.
    latest = {"House": _d(ADOPT, "Passed", 217, 204, "2021-01-04", "117-hres-8")}
    assert bill_status([], latest)["variant"] == "final"


def test_bill_status_chambers_differ_states_the_newer():
    latest = {"House": _d(PASS, "Passed", 237, 169, "2026-03-01"),
              "Senate": _d(PASS, "Bill Defeated (45-55)", 45, 55, "2026-04-01")}
    assert bill_status(None, latest, "hr") == {"text": "Rejected by the Senate 45–55", "variant": "moving"}


def test_bill_status_no_decisive_vote():
    assert bill_status(None, {}, "s") == {"text": "No final vote yet", "variant": "moving"}
    assert bill_status(None, {"House": None, "Senate": None}, "s")["text"] == "No final vote yet"


def test_bill_status_ignores_impeachment_verdicts():
    verdict = _d("Verdict on an article of impeachment (needed two-thirds)", "Not Guilty", 57, 43, "2021-02-13")
    assert bill_status(None, {"Senate": verdict}, "hres")["text"] == "No final vote yet"


# --- §7.1 positions ---

@pytest.mark.parametrize("vote, text, variant, short", [
    ("Yea", "Voted yes", "yes", "Yes"),
    ("Aye", "Voted yes", "yes", "Yes"),
    ("Nay", "Voted no", "no", "No"),
    ("No", "Voted no", "no", "No"),
    ("Not Voting", "Didn't vote", "nv", "Didn't vote"),
    ("Present", "Present", "present", "Present"),
    ("Present, Giving Live Pair", "Present", "present", "Present"),
    ("Guilty", "Guilty", "other", "Guilty"),
    ("Not Guilty", "Not Guilty", "other", "Not Guilty"),
    ("Jeffries", "Voted", "other", "Voted"),
    ("Johnson (LA)", "Voted", "other", "Voted"),
])
def test_position_chip(vote, text, variant, short):
    assert position_chip(vote) == {"text": text, "variant": variant, "short": short}


def test_position_chip_never_returns_candidate_name():
    assert "Jeffries" not in json.dumps(position_chip("Jeffries"))


# --- Dates ---

@pytest.mark.parametrize("value, short, expected", [
    ("2026-09-03", False, "September 3, 2026"),
    ("2026-09-03T00:00:00", False, "September 3, 2026"),
    ("2026-08-08T04:36:00", True, "Aug 8, 2026"),
    ("2026-09-03", True, "Sep 3, 2026"),
    ("", False, ""),
    (None, True, ""),
    ("not a date", False, "not a date"),
])
def test_format_date(value, short, expected):
    assert format_date(value, short=short) == expected


def test_format_date_default_is_long_and_accepts_a_style_string():
    assert format_date("2026-11-03") == "November 3, 2026"
    assert format_date("2026-11-03", "short") == "Nov 3, 2026"
    assert format_date("2026-11-03", "long") == "November 3, 2026"


def test_format_date_has_no_zero_padding_or_time():
    assert not re.search(r"\b0\d\b|:\d\d", format_date("2026-01-05T17:31:00"))


# --- §9.1 escape helper ---

def test_h_escapes_markup_and_quotes():
    from app.render import h
    assert h('<b>&"\'') == "&lt;b&gt;&amp;&quot;&#x27;"
    assert h(4795) == "4795"
    assert h(None) == ""


# G1-021: bidi controls (embeddings, overrides, isolates, directional marks) and zero-width or
# invisible format characters, written as escapes so this file shows each one.
_BIDI_AND_INVISIBLE = ["\u061c", "\u200b", "\u200c", "\u200d", "\u200e", "\u200f", "\u202a", "\u202b",
                       "\u202c", "\u202d", "\u202e", "\u2060", "\u2061", "\u2062", "\u2063", "\u2064",
                       "\u2066", "\u2067", "\u2068", "\u2069", "\ufeff"]


@pytest.mark.parametrize("char", _BIDI_AND_INVISIBLE)
def test_h_drops_bidi_controls_and_invisible_characters(char):
    # An override in a title would reverse the site's own text after it; a zero-width space
    # makes "Ken Pax\u200bton" look like "Ken Paxton" while it is stored differently.
    from app.render import h
    assert h(f"Ken Pax{char}ton") == "Ken Paxton"
    assert h(f"{char}Set the rules <b>{char}") == "Set the rules &lt;b&gt;"


def test_h_leaves_ordinary_text_unchanged():
    from app.render import h
    for text in ("Nydia Velázquez", "Jenniffer González-Colón", "Raúl Grijalva — District 7 · ½ § 3",
                 "non\u00a0breaking\u2011hyphen", "line\nbreak\ttab", "שלום", "日本語"):
        assert h(text) == text


def test_person_row_drops_a_right_to_left_override():
    row = render.render_person_row({"bioguideId": "S001217", "display_name": "\u202eRick Scott",
                                    "seat_line": "U.S. Senator\u2067", "seat_seal": ""}, None)
    assert "Rick Scott" in row and "\u202e" not in row and "\u2067" not in row


# --- §7.5 bill codes, ordinals, names, tenure ---

@pytest.mark.parametrize("bill_type, number, code", [
    ("hr", 4795, "H.R. 4795"),
    ("s", "5271", "S. 5271"),
    ("hjres", 20, "H.J.Res. 20"),
    ("sjres", 11, "S.J.Res. 11"),
    ("hconres", 108, "H.Con.Res. 108"),
    ("sconres", 5, "S.Con.Res. 5"),
    ("hres", 1398, "H.Res. 1398"),
    ("sres", 417, "S.Res. 417"),
    ("HJRES", "20", "H.J.Res. 20"),
    ("xyz", 5, "XYZ 5"),
])
def test_format_bill_code(bill_type, number, code):
    from app.render import format_bill_code
    assert format_bill_code(bill_type, number) == code


def test_main_uses_the_shared_bill_type_map():
    from app import main
    assert main._BILL_TYPE_LABELS is render._BILL_TYPE_LABELS


@pytest.mark.parametrize("n, text", [
    (1, "1st"), (2, "2nd"), (3, "3rd"), (4, "4th"), (11, "11th"), (12, "12th"), (13, "13th"),
    (21, "21st"), (22, "22nd"), (101, "101st"), (111, "111th"), (112, "112th"), (113, "113th"),
    (117, "117th"), (118, "118th"), (119, "119th"), ("119", "119th"),
])
def test_ordinal(n, text):
    from app.render import ordinal
    assert ordinal(n) == text


@pytest.mark.parametrize("name, shown", [
    ("Schumer, Charles E.", "Charles E. Schumer"),
    ("Scott, Rick", "Rick Scott"),
    ("McMorris Rodgers, Cathy", "Cathy McMorris Rodgers"),
    ("Madonna", "Madonna"),
    ("", ""),
    (None, ""),
])
def test_display_name(name, shown):
    from app.render import display_name
    assert display_name(name) == shown


def test_display_name_over_fixture_members():
    from app.render import display_name
    members = json.loads((FIXTURES / "members.json").read_text())["members"]
    for member in members:
        shown = display_name(member["name"])
        assert "," not in shown and shown == shown.strip()


def test_tenure_line_from_real_members():
    from app.render import tenure_line
    members = {m["bioguideId"]: m for m in json.loads((FIXTURES / "members.json").read_text())["members"]}
    assert tenure_line(members["S000148"]["terms"]) == (
        "In Congress since 1981 — House 1981–1999, Senate since 1999")
    assert tenure_line(members["G000555"]["terms"]) == (
        "In Congress since 2007 — House 2007–2009, Senate since 2009")
    assert tenure_line(members["G000602"]["terms"]) == "In Congress since 2025"
    assert tenure_line(members["S001217"]["terms"]) == "In Congress since 2025"


def test_tenure_line_one_chamber_several_terms_and_empty():
    from app.render import tenure_line
    terms = {"item": [{"chamber": "House of Representatives", "startYear": 2013, "endYear": 2015},
                      {"chamber": "House of Representatives", "startYear": 2019}]}
    assert tenure_line(terms) == "In Congress since 2013"
    assert tenure_line({"item": []}) == ""
    assert tenure_line(None) == ""


# --- §7.4 seat seals: the seat, never the person ---

def test_seat_seal():
    from app.render import seat_seal
    assert seat_seal("regular") == "Seat up Nov 3"
    assert seat_seal("regular", "row") == "Seat up Nov 3"
    assert seat_seal("regular", "header") == "This seat is on the ballot Nov 3, 2026"
    assert seat_seal("regular", header=True) == "This seat is on the ballot Nov 3, 2026"
    assert seat_seal("regular_new_map") == "Seat up Nov 3 · new district lines"
    assert seat_seal("regular_new_map", header=True) == (
        "This seat is on the ballot Nov 3, 2026, with new district lines")
    assert seat_seal("special", "row") == "Special election Nov 3"
    assert seat_seal("special", header=True) == "Special election for this seat Nov 3, 2026"
    assert seat_seal(None, "row") == ""
    assert seat_seal(None, header=True) == ""


def test_house_seats_in_the_new_map_states_say_the_lines_are_new():
    # G1-013: CA, FL and TX elect their House members on new district lines on Nov 3, 2026 (the
    # cheat-sheet research sets house.map_same_as_119th false for exactly these), so a ZIP's
    # 119th-Congress district may not be the reader's 2026 one. New York keeps its map.
    assert render.NEW_MAP_STATES == {"CA", "FL", "TX"}
    assert render.NEW_MAP_STATES < set(render.COVERED_STATE_NAMES)
    for code in ("CA", "FL", "TX", "tx"):
        assert render.house_seat_2026(code) == "regular_new_map"
    for code in ("NY", "OH", "", None):
        assert render.house_seat_2026(code) == "regular"


_LA = ZoneInfo("America/Los_Angeles")


@pytest.mark.parametrize("now, shown", [
    (datetime(2026, 10, 22, 12, 0, tzinfo=_LA), True),
    (datetime(2026, 11, 2, 12, 0, tzinfo=_LA), True),
    (datetime(2026, 11, 3, 0, 0, tzinfo=_LA), True),
    (datetime(2026, 11, 3, 23, 59, tzinfo=_LA), True),
    (datetime(2026, 11, 4, 7, 59, tzinfo=timezone.utc), True),   # 23:59 PST, still Nov 3 in California
    (datetime(2026, 11, 4, 8, 0, tzinfo=timezone.utc), False),   # midnight Pacific, Nov 4
    (datetime(2026, 11, 20, 12, 0, tzinfo=_LA), False),
    (datetime(2027, 1, 2, 12, 0, tzinfo=_LA), False),
])
def test_seat_seal_is_gone_after_election_day(now, shown):
    # F066: from Nov 4 (Pacific) no seal says a seat is up on Nov 3.
    from app.render import seat_seal
    for kind, header, text in (("regular", False, "Seat up Nov 3"),
                               ("regular", True, "This seat is on the ballot Nov 3, 2026"),
                               ("regular_new_map", False, "Seat up Nov 3 · new district lines"),
                               ("regular_new_map", True,
                                "This seat is on the ballot Nov 3, 2026, with new district lines"),
                               ("special", False, "Special election Nov 3"),
                               ("special", True, "Special election for this seat Nov 3, 2026")):
        assert seat_seal(kind, header=header, now=now) == (text if shown else "")
    assert seat_seal(None, now=now) == ""


def test_seat_seal_copy_never_names_a_person():
    from app.render import _SEAT_SEALS
    for text in _SEAT_SEALS.values():
        assert not re.search(r"\b(On|Not on) the ballot", text)


# --- §4.4 sponsor name: never the fullName string ---

def test_sponsor_name_real_sponsor():
    from app.render import sponsor_name
    bills = {f"{b['congress']}-{b['type'].lower()}-{b['number']}": b
             for b in json.loads((FIXTURES / "bills.json").read_text())["bills"]}
    sponsor = bills["118-hr-21"]["sponsors"][0]
    assert sponsor["fullName"] == "Rep. McMorris Rodgers, Cathy [R-WA-5]"
    assert (sponsor["firstName"], sponsor["lastName"]) == ("Cathy", "Rodgers")
    # The person comes from fullName, so the compound surname survives.
    assert sponsor_name(sponsor) == "Rep. Cathy McMorris Rodgers (WA)"


def test_sponsor_name_all_caps_parts_in_real_data():
    from app.render import sponsor_name
    bills = {f"{b['congress']}-{b['type'].lower()}-{b['number']}": b
             for b in json.loads((FIXTURES / "bills.json").read_text())["bills"]}
    sponsor = bills["117-hres-8"]["sponsors"][0]
    # 176 real sponsors carry ALL-CAPS firstName/lastName; fullName is cased normally.
    assert (sponsor["firstName"], sponsor["lastName"]) == ("STENY", "HOYER")
    assert sponsor_name(sponsor) == "Rep. Steny H. Hoyer (MD)"


def test_sponsor_name_resident_commissioner_prefixes():
    from app.render import sponsor_name
    # Copied from real bills.json (118-hr-359 and 117-hr-2020); neither is in the fixture slice.
    rescom = {"firstName": "Jenniffer", "lastName": "Gonzalez-Colon", "state": "PR",
              "fullName": "Rescom. González-Colón, Jenniffer [R-PR-At Large]"}
    assert sponsor_name(rescom) == "Rescom. Jenniffer González-Colón (PR)"
    long_form = dict(rescom, fullName="Resident Commissioner González-Colón, Jenniffer [R-PR-At Large]")
    assert sponsor_name(long_form) == "Resident Commissioner Jenniffer González-Colón (PR)"


def test_sponsor_name_never_leaks_party_over_fixture_bills():
    from app.render import sponsor_name
    for bill in json.loads((FIXTURES / "bills.json").read_text())["bills"]:
        for sponsor in bill.get("sponsors", []):
            shown = sponsor_name(sponsor)
            assert "[" not in shown and not re.search(r"\b[RDI]-[A-Z]{2}", shown)


def test_sponsor_name_senator_and_missing_parts():
    from app.render import sponsor_name
    assert sponsor_name({"fullName": "Sen. Schumer, Charles E. [D-NY]", "firstName": "Charles",
                         "lastName": "Schumer", "state": "NY"}) == "Sen. Charles E. Schumer (NY)"
    # fullName alone is enough; without a state there is no parenthetical.
    assert sponsor_name({"fullName": "Rep. Smith, Jason [R-MO-8]"}) == "Rep. Jason Smith"
    # T1.8's page sponsor has fullName without the suffix; it still parses.
    assert sponsor_name({"fullName": "Rep. McMorris Rodgers, Cathy", "firstName": "Cathy",
                         "lastName": "Rodgers", "state": "WA"}) == "Rep. Cathy McMorris Rodgers (WA)"
    # fullName that does not parse: prefix kept, first/last used, ALL CAPS title-cased.
    assert sponsor_name({"fullName": "Rep. HOYER", "firstName": "STENY", "lastName": "HOYER",
                         "state": "MD"}) == "Rep. Steny Hoyer (MD)"
    assert sponsor_name({"fullName": "", "firstName": "", "lastName": ""}) == ""
    assert sponsor_name(None) == ""


def test_sponsor_name_parses_every_real_sponsor():
    from app.render import _SPONSOR_FULLNAME_RE, sponsor_name
    real = Path(__file__).resolve().parent.parent / "data" / "synced" / "bills.json"
    if not real.exists():
        pytest.skip("real bills.json not present")
    for bill in json.loads(real.read_text())["bills"]:
        for sponsor in bill.get("sponsors", []):
            match = _SPONSOR_FULLNAME_RE.match(sponsor["fullName"])
            assert match and "," in match.group(2), sponsor["fullName"]
            shown = sponsor_name(sponsor)
            assert "[" not in shown and shown != shown.upper(), shown


# --- §10 #10 strip_tags ---

@pytest.mark.parametrize("markup, text", [
    ("<script>alert(1)</script>Safe", "Safe"),
    ('<a href="javascript:alert(1)">Click</a>', "Click"),
    ("<img src=x onerror=alert(1)>ok", "ok"),
    ("<style>p { color: red }</style>Body", "Body"),
    ("<script>alert(1)", ""),
    ("&lt;script&gt;alert(1)&lt;/script&gt;", "<script>alert(1)</script>"),
    ("Tom &amp; Jerry &#x27;s", "Tom & Jerry 's"),
    ("<p><b>Strategic Production Response Act</b></p> <p>This bill limits drawdowns.</p>",
     "Strategic Production Response Act This bill limits drawdowns."),
    ("", ""),
    (None, ""),
])
def test_strip_tags(markup, text):
    from app.render import strip_tags
    assert strip_tags(markup) == text


def test_strip_tags_then_h_never_yields_markup():
    from app.render import h, strip_tags
    out = h(strip_tags("&lt;script&gt;alert(1)&lt;/script&gt;<a href=\"javascript:x\">y</a>"))
    assert "<" not in out and "javascript" not in out


def test_strip_tags_real_official_summary():
    from app.render import strip_tags
    bills = {f"{b['congress']}-{b['type'].lower()}-{b['number']}": b
             for b in json.loads((FIXTURES / "bills.json").read_text())["bills"]}
    text = strip_tags(bills["118-hr-21"]["summaries"][0]["text"])
    assert text.startswith("Strategic Production Response Act This bill limits")
    assert "<" not in text
