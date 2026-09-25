"""Python ↔ site.js formatter parity (plan T2.2; spec §7.1–§7.5, §10 #12, §10 #21).

app/render.py is the source of truth. The tables site.js mirrors are compared
structurally on every run (CI has no node). The formatter outputs are compared by
running static/js/site.js under node when node is on PATH; otherwise those tests skip.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app import render

ROOT = Path(__file__).resolve().parent.parent
_SITE_JS = ROOT / "static" / "js" / "site.js"
_NODE = shutil.which("node")
needs_node = pytest.mark.skipif(_NODE is None, reason="node is not installed (CI runs without it)")

FIXTURE_INDEX = ROOT / "tests" / "fixtures" / "synced" / "votes_index.json"
REAL_INDEX = ROOT / "data" / "synced" / "votes_index.json"


def _js_block(name: str) -> str:
    text = _SITE_JS.read_text()
    start = text.index(f"/* {name}:start */")
    end = text.index(f"/* {name}:end */")
    return text[start:end]


def _js_literal(block: str, const: str):
    match = re.search(rf"const {const} = (.*?);\n", block, re.S)
    assert match, f"{const} literal not found"
    return json.loads(match.group(1))


def _py_question_rows() -> list[dict]:
    """render.QUESTION_CLASSES as the JSON rows site.js holds: pattern, flags, plain, noun, class."""
    rows = []
    for entry in render.QUESTION_CLASSES:
        if isinstance(entry, dict):
            pattern, plain, noun, cls = entry["pattern"], entry["plain"], entry.get("noun"), entry["class"]
        else:
            pattern, plain, noun, cls = entry
        flags = ""
        if isinstance(pattern, re.Pattern):
            flags = "i" if pattern.flags & re.IGNORECASE else ""
            pattern = pattern.pattern
        if pattern.startswith("(?i)"):
            pattern, flags = pattern[4:], "i"
        rows.append({"pattern": pattern, "flags": flags, "plain": plain, "noun": noun, "class": cls})
    return rows


# --- Structural parity (always runs) ---

def test_bill_type_labels_match_python():
    labels = _js_literal(_js_block("bill-type-labels"), "BILL_TYPE_LABELS")
    assert labels == render._BILL_TYPE_LABELS


def test_question_class_table_matches_python():
    rows = _js_literal(_js_block("question-classes"), "QUESTION_CLASSES")
    assert rows == _py_question_rows()


def test_question_patterns_are_portable_to_javascript():
    for row in _js_literal(_js_block("question-classes"), "QUESTION_CLASSES"):
        assert row["class"] in ("D", "P")
        assert row["flags"] in ("", "i")
        for python_only in ("(?P<", "(?P=", "\\A", "\\Z", "(?#", "(?i", "(?x"):
            assert python_only not in row["pattern"], row["pattern"]
        re.compile(row["pattern"], re.IGNORECASE if row["flags"] == "i" else 0)


def test_position_labels_follow_the_glossary():
    block = _js_block("positions")
    assert _js_literal(block, "POSITIONS") == {
        "Yea": ["yes", "Voted yes"], "Aye": ["yes", "Voted yes"],
        "Nay": ["no", "Voted no"], "No": ["no", "Voted no"],
        "Not Voting": ["nv", "Didn't vote"],
        "Present": ["present", "Present"], "Present, Giving Live Pair": ["present", "Present"],
        "Guilty": ["other", "Guilty"], "Not Guilty": ["other", "Not Guilty"],
    }
    assert _js_literal(block, "SHORT_LABELS") == {"yes": "Yes", "no": "No", "nv": "Didn't vote", "present": "Present"}
    # Python is the source of truth: every JS row equals render.position_chip (T1.2), and the
    # JS fallback for an unknown string (a Speaker candidate) equals Python's.
    positions, shorts = _js_literal(block, "POSITIONS"), _js_literal(block, "SHORT_LABELS")
    for raw, (kind, label) in positions.items():
        assert render.position_chip(raw) == {"text": label, "variant": kind, "short": shorts.get(kind, label)}, raw
    assert render.position_chip("Jeffries") == {"text": "Voted", "variant": "other", "short": "Voted"}
    assert set(positions) == {"Yea", "Aye", "Nay", "No", "Not Voting", "Present", "Present, Giving Live Pair",
                              "Guilty", "Not Guilty"}


def test_site_js_builds_dom_without_html_parsing():
    js = _SITE_JS.read_text()
    for banned in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "document.title =",
                   ".style.color", ".style.background", "pushState", "eval(", "new Function"):
        assert banned not in js, banned
    assert re.search(r"^\s*export\s", js, re.M) is None  # a classic script, not a module
    assert re.search(r"\b(On|Not on) the ballot", js) is None


# --- Output parity through node (skipped without node) ---

def _run_node(calls: list) -> list:
    script = (
        "const s = require(process.argv[1]);"
        "const calls = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "process.stdout.write(JSON.stringify(calls.map(([name, args]) => s[name](...args))));"
    )
    done = subprocess.run([_NODE, "-e", script, str(_SITE_JS)], input=json.dumps(calls),
                          capture_output=True, text=True, check=True, timeout=120)
    return json.loads(done.stdout)


def _assert_same(calls: list, expected: list):
    got = _run_node(calls)
    misses = [(call, want, have) for call, want, have in zip(calls, expected, got) if want != have]
    assert not misses, "first mismatches (call, python, js):\n" + "\n".join(map(repr, misses[:10]))


def _rc(question: str, result: str, yeas: int, nays: int, absent: int = 0, date: str = "2026-09-03") -> dict:
    return {
        "question": question, "plain": render.plain_question(question), "class": render.question_class(question),
        "result": result, "counts": {"yeas": yeas, "nays": nays, "present": 0, "absent": absent},
        "date": date, "document": "", "bill": None, "parent": None, "threshold": None, "tallies": {},
    }


# (chamber, question, result, yeas, nays[, absent[, date]]) — one row per §7.2 branch.
SYNTHETIC = [
    ("House", "On Passage", "Passed", 237, 169, 27),
    ("House", "On Motion to Suspend the Rules and Pass, as Amended", "Failed", 250, 170),
    ("House", "On Agreeing to the Resolution", "Passed", 220, 210),
    ("House", "On Motion to Concur in the Senate Amendment", "Agreed to", 300, 100),
    ("House", "Passage, Objections of the President To The Contrary Notwithstanding", "Failed", 250, 170),
    ("Senate", "On Overriding the Veto", "Veto Sustained", 55, 44),
    ("Senate", "On Passage of the Bill H.R. 6500", "Bill Passed (90-6)", 90, 6),
    ("Senate", "On the Joint Resolution S.J.Res. 11", "Joint Resolution Defeated (45-53)", 45, 53),
    ("Senate", "On the Resolution of Ratification Treaty Doc. 117-3", "Resolution of Ratification Agreed to (95-1)", 95, 1),
    ("Senate", "Guilty or Not Guilty", "Not Guilty", 57, 43),
    ("Senate", "On the Cloture Motion H.R. 3967", "Cloture Motion Agreed to (89-4)", 89, 4),
    ("Senate", "On Cloture on the Motion to Proceed H.R. 5371",
     "Cloture on the Motion to Proceed Rejected (52-46, 3/5 majority required)", 52, 46, 0, "2026-08-08"),
    ("Senate", "On the Amendment S.Amdt. 678 to S.Con.Res. 5", "Amendment Agreed to (60-38)", 60, 38),
    ("House", "On Agreeing to the Amendment", "Failed", 189, 235),
    ("Senate", "On the Motion to Recommit H.R. 4", "Motion to Recommit Rejected (45-53)", 45, 53, 0, "2026-08-08"),
    ("Senate", "On the Motion to Proceed S. 2882", "Motion to Proceed Agreed to (55-44)", 55, 44),
    ("Senate", "On the Motion (Motion to Waive All Applicable Budgetary Discipline Re: Amdt. No. 1)",
     "Motion Rejected (50-50)", 50, 50),
    ("Senate", "On the Motion to Proceed PN1827",
     "Motion to Proceed Agreed to (50-50, Vice President of the United States, voted Yea)", 50, 50),
    ("House", "Election of the Speaker", "Johnson", 218, 215),
    ("House", "Call by States", "Passed", 0, 0),
    ("Senate", "On the Nomination PN80", "Nomination Confirmed (52-45)", 52, 45),
    ("Senate", "On the Point of Order", "Point of Order Well Taken (51-49)", 51, 49),
]


def _synthetic_pairs() -> list[tuple[str, dict]]:
    return [(row[0], _rc(*row[1:])) for row in SYNTHETIC]


def _index_roll_calls(path: Path) -> list[tuple[str, dict]]:
    data = json.loads(path.read_text())
    return [("House" if key.startswith("house/") else "Senate", rc) for key, rc in sorted(data["roll_calls"].items())]


def _py_result(rc: dict, chamber: str) -> str:
    """render.result_phrase(rc, chamber) (T1.2). The only place this test knows its signature."""
    return render.result_phrase(rc, chamber) or ""


def _py_outcome(rc: dict, chamber: str) -> str:
    """render.outcome_sentence(rc, chamber) (T1.2); '' where Python returns None (Speaker rows)."""
    return render.outcome_sentence(rc, chamber) or ""


def _formatter_calls(pairs: list[tuple[str, dict]]) -> tuple[list, list]:
    calls, expected = [], []
    for chamber, rc in pairs:
        question = rc.get("question") or ""
        calls += [["questionClass", [question]], ["plainQuestion", [question]],
                  ["resultPhrase", [rc, chamber]], ["outcomeSentence", [rc, chamber]]]
        expected += [render.question_class(question), render.plain_question(question),
                     _py_result(rc, chamber), _py_outcome(rc, chamber)]
    return calls, expected


@needs_node
def test_names_codes_ordinals_and_dates_match_python():
    members = json.loads((ROOT / "data" / "synced" / "members.json").read_text())["members"]
    names = [m["name"] for m in members] + ["Schumer, Charles E.", "Gillen, Laura"]
    codes = [(t, n) for t in render._BILL_TYPE_LABELS for n in (1, 21, 4795)]
    dates = ["2026-09-03", "2026-01-01", "2021-12-31", "2026-11-03"]
    calls = ([["displayName", [n]] for n in names]
             + [["formatBillCode", [t, n]] for t, n in codes]
             + [["ordinal", [n]] for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 101, 111, 112, 113, 117, 118, 119)]
             + [["formatDate", [d, False]] for d in dates] + [["formatDate", [d, True]] for d in dates])
    expected = ([render.display_name(n) for n in names]
                + [render.format_bill_code(t, n) for t, n in codes]
                + [render.ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 101, 111, 112, 113, 117, 118, 119)]
                + [render.format_date(d) for d in dates] + [render.format_date(d, short=True) for d in dates])
    _assert_same(calls, expected)


@needs_node
def test_vote_vocabulary_matches_python_on_synthetic_rows():
    _assert_same(*_formatter_calls(_synthetic_pairs()))


@needs_node
def test_vote_vocabulary_matches_python_on_the_fixture_index():
    if not FIXTURE_INDEX.exists():
        pytest.skip("tests/fixtures/synced/votes_index.json not built")
    _assert_same(*_formatter_calls(_index_roll_calls(FIXTURE_INDEX)))


@needs_node
def test_vote_vocabulary_matches_python_on_every_real_roll_call():
    if not REAL_INDEX.exists():
        pytest.skip("data/synced/votes_index.json not present")
    _assert_same(*_formatter_calls(_index_roll_calls(REAL_INDEX)))


@needs_node
def test_js_vocabulary_never_uses_the_banned_verbs():
    calls, _ = _formatter_calls(_synthetic_pairs())
    for text in _run_node(calls):
        assert not re.search(r"blocked|let the veto stand|taken up", str(text)), text


# --- cv-home rules under node (plan T2.3; spec §5.4, C-13) ---

_HOME_SCRIPT = r"""
function memoryStorage() {
  const data = {};
  return { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = String(v); },
           removeItem: (k) => { delete data[k]; }, data };
}
const local = memoryStorage();
globalThis.window = { localStorage: local, sessionStorage: memoryStorage(),
  location: { hash: '#mine', search: '?code=NY&district=4', pathname: '/state' } };
globalThis.history = { state: null, replaced: null, replaceState(state, title, url) { this.replaced = url; } };
const s = require(process.argv[1]);
const out = {};
out.home = s.initHome();
out.replaced = history.replaced;
out.stored = JSON.parse(local.data['cv-home']);
out.place = s.homePlace(out.home);
out.href = s.homeHref(out.home);
out.second = s.initHome();
out.refusedState = s.rememberDistrict('OH', 3);
out.refusedDistrict = s.rememberDistrict('NY', 0);
out.lower = s.rememberDistrict('tx', '7');
s.forgetHome();
out.afterForget = s.readHome();
local.setItem('cv-home', '{not json');
out.corrupt = s.readHome();
window.localStorage = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); },
                        removeItem() { throw new Error('blocked'); } };
out.blockedRead = s.readHome();
out.blockedWrite = s.rememberDistrict('NY', 4);
process.stdout.write(JSON.stringify(out));
"""


@needs_node
def test_cv_home_is_written_from_mine_and_only_for_covered_districts():
    done = subprocess.run([_NODE, "-e", _HOME_SCRIPT, str(_SITE_JS)], capture_output=True, text=True,
                          check=True, timeout=60)
    out = json.loads(done.stdout)
    saved = out["home"]["savedAt"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", saved)
    assert out["home"] == out["stored"] == out["second"] == {"state": "NY", "district": 4, "savedAt": saved}
    assert out["replaced"] == "/state?code=NY&district=4"  # the #mine fragment is dropped
    assert out["place"] == "New York, District 4"
    assert out["href"] == "/state?code=NY&district=4"
    assert out["refusedState"] is None and out["refusedDistrict"] is None
    assert out["lower"] == {"state": "TX", "district": 7, "savedAt": saved}
    assert out["afterForget"] is None and out["corrupt"] is None
    assert out["blockedRead"] is None and out["blockedWrite"] is None
