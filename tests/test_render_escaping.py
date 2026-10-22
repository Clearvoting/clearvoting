"""SSR escaping registry (spec §9.1, §10 #22).

Every renderer that puts data into HTML is registered in RENDERERS with a
callable that embeds the hostile payload it is given somewhere in its output
(as a name, title, headline, …). Each later render task appends its block
renderers here, so one test covers every renderer against every payload."""
import re
from html.parser import HTMLParser

import pytest

from app import render
from app.render import N, display_name, format_bill_code, h, sponsor_name, tree_html
from app.render import render_bill_strip, render_member_strip, render_strip
from tests.test_state_render import FakeDS, member_raw

HOSTILE = [
    "<script>alert(1)</script>",
    '"><img src=x>',
    "&amp;",
    "javascript:alert(1)",
    # Attribute breakouts without '<' (F087): only a quote-unsafe attribute lets these through,
    # and the tag checks below cannot see them.
    'x" onmouseover="alert(1)',
    "x' style='display:none",
]


class _AttributeNames(HTMLParser):
    """Every attribute name on every start tag, as a browser's tokenizer reads them."""

    def __init__(self):
        super().__init__()
        self.names: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.names.extend(name for name, _ in attrs)


RENDERERS = {
    "h": lambda p: h(p),
    "h(display_name)": lambda p: h(display_name(f"{p}, {p}")),
    "h(format_bill_code)": lambda p: h(format_bill_code("hr", p)),
    "h(sponsor_name)": lambda p: h(sponsor_name(
        {"fullName": f"Rep. {p}", "firstName": p, "lastName": p, "state": "NY"})),
    "tree_html": lambda p: tree_html(N("p", {"class": p}, p)),
    "render_strip": lambda p: render_strip(p, [(p, p)], share=True),
    "render_member_strip": lambda p: render_member_strip(p, '<h2 id="record" tabindex="-1">'),
    "render_bill_strip": lambda p: render_bill_strip(p, f'<main><span class="seal seal--final">{h(p)}</span>'),
}


def assert_escaped(out: str, payload: str) -> None:
    lowered = out.lower()
    assert "<script" not in lowered
    assert "<img" not in lowered
    assert not re.search(r"""(href|src)\s*=\s*["']?\s*javascript:""", lowered)
    if payload == "&amp;":
        # The literal entity text was escaped, not passed through as markup.
        assert "&amp;amp;" in out
    if '"' in payload or "'" in payload:
        # An attribute-breaking payload never appears raw: h() turns both quotes into entities.
        # (Not '"><' in general: every block renderer's own markup, e.g.
        # class="page-error"><h1>, contains that.)
        assert payload not in out
    # No payload became an attribute of its own. (Not style=: some renderers set one themselves.)
    parser = _AttributeNames()
    parser.feed(out)
    parser.close()
    assert not [name for name in parser.names if name.startswith("on") or name == "formaction"]


@pytest.mark.parametrize("payload", HOSTILE)
@pytest.mark.parametrize("name", sorted(RENDERERS))
def test_renderer_escapes_hostile_input(name, payload):
    assert_escaped(RENDERERS[name](payload), payload)


def test_hostile_fixture_title_is_escaped():
    import json
    from pathlib import Path
    bills = json.loads((Path(__file__).parent / "fixtures" / "synced" / "bills.json").read_text())["bills"]
    title = next(b["title"] for b in bills if b["number"] == "99999")
    out = h(title)
    assert "<b>" not in out and "&lt;b&gt;" in out
    assert "&amp;" in out and "&quot;" in out and "&#x27;" in out


# --- Shared page blocks (plan T3.1) ---

# T1.3's test is parametrized over sorted(RENDERERS) when its decorator runs, so entries
# added down here would never be collected: this block has its own dict and test.
SHARED_BLOCKS = {
    "render_error": lambda p: render.render_error(p),
    "render_zip_form": lambda p: render.render_zip_form(value=p, error=p, label=p),
}


@pytest.mark.parametrize("payload", HOSTILE)
@pytest.mark.parametrize("name", sorted(SHARED_BLOCKS))
def test_shared_blocks_escape_hostile_input(name, payload):
    assert_escaped(SHARED_BLOCKS[name](payload), payload)


# --- Home blocks (plan T3.2) ---

def _hostile_home_bill(p: str) -> dict:
    return {"congress": 119, "type": "HR", "number": "1", "title": p, "one_liner": p,
            "provisions": [p], "derived_status": p, "activity_date": "2026-09-03"}


def _hostile_latest_vote(p: str, summarized: bool = True) -> dict:
    return {"chamber": "House", "date": "September 3, 2026", "date_iso": "2026-09-03", "plain_question": p, "outcome": p,
            "counts": {"yeas": 1, "nays": 2, "absent": 0},
            "one_liner": p if summarized else None, "has_summary": summarized,
            "bill": {"congress": 119, "type": "hr", "number": 1, "title": p}}


HOME_BLOCKS = {
    "render_seal": lambda p: render.render_seal(p, "final"),
    "render_tally": lambda p: render.render_tally({"yeas": 1, "nays": 1}, p),
    "render_latest_vote_card": lambda p: render.render_latest_vote_card(_hostile_latest_vote(p), "2026-07-07"),
    "render_latest_vote_card (official title)":
        lambda p: render.render_latest_vote_card(_hostile_latest_vote(p, summarized=False)),
    "render_record": lambda p: render.render_record(
        [_hostile_home_bill(p), dict(_hostile_home_bill(p), one_liner=None)],
        "2026-09-05", "2021-01-03", _hostile_home_bill(p), "2026-07-07"),
    "render_record (withheld lead)": lambda p: render.render_record(
        [dict(_hostile_home_bill(p), one_liner=None)], "2026-09-05", None, _hostile_home_bill(p), None),
}


@pytest.mark.parametrize("payload", HOSTILE)
@pytest.mark.parametrize("name", sorted(HOME_BLOCKS))
def test_home_blocks_escape_hostile_input(name, payload):
    assert_escaped(HOME_BLOCKS[name](payload), payload)


# --- Delegation renderers (plan T4.1) ---

def _delegation_ds(payload):
    return FakeDS(
        summaries={"119-hr-1": {"one_liner": payload}},
        bills={"119-hr-1": {"title": payload}, "119-hr-2": {"title": payload}},
        members={"G000602": {"terms": {"item": [{"chamber": "House of Representatives", "startYear": 2025}]}}},
    )


def _delegation_member(payload, bill_id="119-hr-1"):
    return member_raw("G000602", payload, district=4, photo=payload,
                      latest_vote={"rc": payload, "bill_id": bill_id, "position": payload,
                                   "date": "2026-09-03"})


def _render_person_rows_hostile(payload):
    ds = _delegation_ds(payload)
    rows = []
    for bill_id in ("119-hr-1", "119-hr-2"):  # a displayable headline, then the official-title fallback
        fields = render.overview_member_fields(_delegation_member(payload, bill_id), ds)
        rows.append(render.render_person_row(fields, fields["latest_vote"], state_code=payload))
        rows.append(render.render_person_row(fields, fields["latest_vote"], split=True, state_code=payload))
    return "".join(rows)


def _render_state_pages_hostile(payload):
    ds = _delegation_ds(payload)
    overview = {"state": "NY", "state_name": payload, "roster_as_of": "2026-09-05",
                "districts_expected": 5, "senators": [], "house": [_delegation_member(payload)]}
    partial = {"zip": payload, "kind": "partial", "covered_share": 0.5, "matches": [
        {"state": "NY", "district": 4, "share": 0.3}, {"state": "NY", "district": 5, "share": 0.2}]}
    return (render.render_state_page(overview, 4, None, payload, ds=ds, zip_value=payload)
            + render.render_state_page(overview, None, partial, payload, ds=ds, zip_value=payload)
            + render.render_state_page(overview, 40, None, "", ds=ds))


DELEGATION = {
    "render_person_row": _render_person_rows_hostile,
    "render_state_page": _render_state_pages_hostile,
    "render_zip_finder_page":
        lambda payload: render.render_zip_finder_page({"CA": 1}, value=payload, error=payload),
    "render_zip_not_found": lambda payload: render.render_zip_not_found(payload, {"CA": 1}),
}


@pytest.mark.parametrize("payload", HOSTILE)
@pytest.mark.parametrize("name", sorted(DELEGATION))
def test_delegation_renderer_escapes_hostile_input(name, payload):
    assert_escaped(DELEGATION[name](payload), payload)


# --- Trust-page renderers (plan Task T5.1) ---
import pytest  # noqa: E402,F811
from app import render as _trust_render  # noqa: E402

_TRUST_HOSTILE = HOSTILE   # one payload list for every block (F087)


def _trust_outputs(s: str) -> dict[str, str]:
    counts = {"members": 150, "senators": 8, "bills": 1610, "shown": 1435, "missing": 60,
              "withheld": 115, "audited": 1200, "nominations": 1469,
              "since": s, "ai_summaries_updated": s}
    sources = {"name": s, "url": s, "retrieved": s, "licence": s, "share": s}
    senate = {"_source": {"url": s, "retrieved": s, "method": s}, "election_day": "2026-11-03",
              "seats": [{"state": "TX", "bioguideId": "C001056", "name": s, "kind": "regular", "class": 2}]}
    return {
        "render_about_counts": _trust_render.render_about_counts(counts),
        "render_methodology": _trust_render.render_methodology(
            counts, sources, {"neutrality": [s], "accuracy": [s]}, senate),
    }


@pytest.mark.parametrize("hostile", _TRUST_HOSTILE)
def test_trust_renderers_escape_hostile_input(hostile):
    outputs = _trust_outputs(hostile)
    for name, out in outputs.items():
        assert "<script>alert(1)</script>" not in out, name
        assert '"><img src=x>' not in out, name
        assert 'href="javascript:' not in out, name
        if '"' in hostile or "'" in hostile:
            assert hostile not in out, name
    if hostile == "&amp;":
        assert "&amp;amp;" in outputs["render_methodology"]


# --- Member page blocks (plan T6.1/T6.2) — self-contained hostile-input checks ---
import re as _re_member

import pytest as _pytest_member

from app import render as _render_member

MEMBER_HOSTILE = HOSTILE   # one payload list for every block (F087)


def _hostile_member_page(s: str) -> dict:
    """A get_member_page()-shaped dict with every free-text field set to one hostile string."""
    rc = {"question": s, "plain": s, "class": "P", "result": s,
          "counts": {"yeas": 1, "nays": 2, "present": 0, "absent": 0}, "date": "2026-08-08",
          "document": s, "bill": None, "parent": None, "threshold": None, "tallies": {}}
    vote = {"rc": s, "roll_call": rc, "chamber": "Senate", "vote": "Yea",
            "date": "2026-08-08T00:00:00", "result": s, "text": s, "parent": None}
    return {
        "member": {"bioguideId": s, "name": f"{s}, {s}", "state": s, "stateCode": s,
                   "district": None, "chamber": "Senate",
                   "terms": {"item": [{"chamber": "Senate", "startYear": 1999}]},
                   "depiction": {"imageUrl": s}},
        "seat": None,
        "has_record": True,
        "stats": {"total_votes": 3, "yea_count": 1, "nay_count": 1, "not_voting_count": 0},
        "first_vote_date": "2021-01-06",
        "last_vote_date": "2026-08-08",
        "nominations_count": 3,
        "recent_votes": [{"rc": s, "roll_call": rc, "chamber": "Senate", "bill_id": "119-hr-1",
                          "congress": 119, "bill_type": "hr", "bill_number": 1, "one_liner": s,
                          "position": "yes", "date": "2026-08-08T00:00:00", "policy_area": s}],
        "record": {
            "groups": [
                {"kind": "bill", "bill_id": "119-hr-1", "congress": 119, "bill_type": "hr",
                 "bill_number": 1, "headline": s, "displayable": False, "lead": vote, "more": [vote]},
                {"kind": "other", "date": "2026-08-08", "votes": [vote]},
                {"kind": "speaker", "vote": dict(vote, vote=s)},
            ],
            "page": 2, "pages": 3, "per_page": 15, "total_groups": 40, "matching_bills": 7,
            "topic": s, "position": None, "plain": True, "policy_areas": [s],
            "plain_bills": 1, "total_bills": 2,
        },
        "sponsored": [{"congress": 119, "type": "hr", "number": 1, "title": s, "introduced_date": s,
                       "one_liner": s, "status": {"text": s, "variant": "moving"}}],
        "sponsored_count": 1,
        "donation": {"fec_candidate_id": s, "cycle": s, "last_updated": s,
                     "totals": {"total_receipts": 1, "total_individual": 1, "total_pac": 1,
                                "total_disbursements": 1}},
    }


def _assert_member_safe(out: str, s: str, echoes: bool = True) -> None:
    """echoes=False for an output that rightly drops the hostile value instead of printing it
    (render_money falls back to its fixed meta line when the cycle or FEC id is not valid)."""
    if s == "<script>alert(1)</script>" or '"' in s or "'" in s:
        assert s not in out
    if s == "&amp;" and echoes:
        assert "&amp;amp;" in out
    assert not _re_member.search(r'(?:href|src)="\s*javascript:', out, _re_member.I)


@_pytest_member.mark.parametrize("s", MEMBER_HOSTILE)
def test_member_t61_blocks_escape_hostile_strings(s):
    page = _hostile_member_page(s)
    outputs = [
        (_render_member.render_member_header(page), True),
        (_render_member.render_recent_votes(page["recent_votes"]), True),
        (_render_member.render_sponsored(page["sponsored"], s, s, total=1), True),
        (_render_member.render_money(page["donation"]), False),   # hostile cycle -> the meta line
        (_render_member.render_vote_row("/bill?congress=119&type=hr&number=1", "", s, False, [s]), True),
    ]
    for out, echoes in outputs:
        _assert_member_safe(out, s, echoes)


@_pytest_member.mark.parametrize("s", MEMBER_HOSTILE)
def test_member_t61_money_omits_the_fec_link_for_a_hostile_candidate_id(s):
    """Valid cycle, totals and retrieval date; only fec_candidate_id is hostile. The id never
    reaches an href: the entry fails the id check and gets the one meta line."""
    donation = {"fec_candidate_id": s, "cycle": "2024", "last_updated": "2026-03-20T00:10:39.880084+00:00",
                "totals": {"total_receipts": 2790888, "total_individual": 2345346, "total_pac": 202800,
                           "total_disbursements": 3349300}}
    out = _render_member.render_money(donation)
    assert "fec.gov" not in out
    assert "Campaign finance isn't in our data for this member yet." in out
    _assert_member_safe(out, s, echoes=False)


@_pytest_member.mark.parametrize("s", MEMBER_HOSTILE)
def test_member_t62_record_and_page_escape_hostile_strings(s):
    page = _hostile_member_page(s)
    for out in (_render_member.render_record_section(page), _render_member.render_member_page(page)):
        _assert_member_safe(out, s)
        assert "<select" in out  # the form rendered, so the hostile topic went through an attribute


# --- Bill page renderers (plan T7.1; T7.2 adds its entries to BILL_RENDERERS) ---

def _hostile_bill_page(s: str) -> dict:
    """A get_bill_page()-shaped dict with a hostile string in every data slot."""
    rc = {
        "key": "house/119_2_00295", "chamber": "house", "congress": 119, "session": 2,
        "vote_number": 295, "date": "2026-09-03", "question": s, "plain": s, "class": "D",
        "result": s, "counts": {"yeas": 1, "nays": 1, "present": 0, "absent": 0},
        "seal": s, "outcome": s, "state_tallies": {"NY": [1, 1, 0]}, "rendered": True,
        "members": [{"first_name": s, "last_name": s, "state": "NY", "vote": s,
                     "bioguide_id": s, "covered_id": s, "district": None}],
    }
    return {
        "bill_id": "119-hr-1", "congress": 119, "bill_type": "hr", "number": 1, "title": s,
        "has_summary": {"one_liner": s}, "one_liner": s, "provisions": [s], "official_summary": s,
        "official_first_paragraph": s,
        "status": {"text": s, "variant": s}, "head": rc, "roll_calls": [rc],
        "sponsor": {"bioguideId": s, "firstName": s, "lastName": s, "state": s, "fullName": s},
        "sponsor_covered": True, "cosponsors_count": s, "policy_area": s,
        "introduced_date": "2025-07-29", "laws": [{"type": s, "number": s}],
        "legislation_url": s,
    }


# Every entry embeds the payload in its output (assert_escaped requires "&amp;amp;" for "&amp;").
BILL_RENDERERS = {
    "render_bill_head": lambda s: render.render_bill_head(_hostile_bill_page(s)),
    "render_bill_head (official title)":
        lambda s: render.render_bill_head({**_hostile_bill_page(s), "has_summary": None, "one_liner": None}),
    "render_what_it_does": lambda s: render.render_what_it_does(_hostile_bill_page(s), "2026-07-07"),
    "render_what_it_does (no summary)":
        lambda s: render.render_what_it_does({**_hostile_bill_page(s), "has_summary": None}, "2026-07-07"),
    # The slot interpolates only legislation_url, and _safe_congress_url drops every bare hostile
    # string, so the payload is embedded inside a Congress.gov URL here.
    "render_official_summary_slot": lambda s: render.render_official_summary_slot(
        {**_hostile_bill_page(s), "legislation_url": "https://www.congress.gov/bill/" + s}),
    "render_fact_box": lambda s: render.render_fact_box(_hostile_bill_page(s)),
    "render_vote_by_state": lambda s: render.render_vote_by_state(_hostile_bill_page(s)),
    "render_vote_by_state (collapsed)": lambda s: render.render_vote_by_state(
        {**_hostile_bill_page(s), "roll_calls": [{**_hostile_bill_page(s)["head"], "rendered": False}]}),
    "render_bill_page": lambda s: render.render_bill_page(_hostile_bill_page(s), "2026-07-07"),
}


@pytest.mark.parametrize("payload", HOSTILE)
@pytest.mark.parametrize("name", sorted(BILL_RENDERERS))
def test_bill_renderer_escapes_hostile_input(name, payload):
    assert_escaped(BILL_RENDERERS[name](payload), payload)


def test_vote_by_state_escapes_data_bioguide_even_past_a_looser_id_check(monkeypatch):
    """F084: the data-bioguide attribute goes through h() itself, not only through _BIOGUIDE_RE."""
    monkeypatch.setattr(render, "_BIOGUIDE_RE", re.compile(r".+", re.S))
    payload = 'x" onmouseover="alert(1)'
    out = render.render_vote_by_state(_hostile_bill_page(payload))
    assert 'data-bioguide="x&quot; onmouseover=&quot;alert(1)"' in out
    assert_escaped(out, payload)


# --- Render-tree href guard (F040): render.N and site.js safeTreeHref ---
import json as _json  # noqa: E402
import shutil as _shutil  # noqa: E402
import subprocess as _subprocess  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_NODE = _shutil.which("node")
_SITE_JS = _Path(__file__).resolve().parent.parent / "static" / "js" / "site.js"

# Browsers drop tabs and newlines and read '\' as '/', so each of these leaves the site.
_OFF_SITE_HREFS = [
    "//evil.example/x", "/\\evil.example/x", "/\t/evil.example/x", "/\n/evil.example",
    "/\r/evil.example", "/\\/evil", "\\\\evil.example", " //evil.example", "/ /evil.example",
    "https://evil.example\\@clearvoting.org/", "/x\x00", "/x\x7f", "javascript:alert(1)",
    "http://evil.example/", "",
]
_SITE_HREFS = [
    "/member?id=S000148&page=2#record", "/bill?congress=119&type=hr&number=1",
    "https://www.senate.gov/legislative/LIS/roll_call_votes/vote1192/vote_119_2_00295.htm",
    "https://clerk.house.gov/Votes/2026295",
]


@pytest.mark.parametrize("href", _OFF_SITE_HREFS)
def test_tree_href_guard_refuses_what_a_browser_resolves_off_site(href):
    with pytest.raises(ValueError):
        N("a", {"href": href}, "x")


@pytest.mark.parametrize("href", _SITE_HREFS)
def test_tree_href_guard_keeps_site_paths_and_https_links(href):
    assert N("a", {"href": href}, "x")["a"]["href"] == href


@pytest.mark.skipif(_NODE is None, reason="node is not installed (CI runs without it)")
def test_site_js_safe_tree_href_matches_the_server_guard():
    hrefs = _OFF_SITE_HREFS + _SITE_HREFS
    script = ("const s = require(process.argv[1]);"
              "const hrefs = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
              "process.stdout.write(JSON.stringify(hrefs.map((href) => s.safeTreeHref(href))));")
    done = _subprocess.run([_NODE, "-e", script, str(_SITE_JS)], input=_json.dumps(hrefs),
                           capture_output=True, text=True, check=True, timeout=120)
    assert _json.loads(done.stdout) == [render._safe_tree_href(href) for href in hrefs]


def test_person_row_builds_its_href_from_the_bioguide_id():
    # F040: the row never links to whatever url the overview payload carries.
    source = _SITE_JS.read_text()
    row = source[source.index("function personRow("):]
    row = row[: row.index("\n}\n")]
    assert "member.url" not in row
    assert "href: `/member?id=${encodeURIComponent(bioguide)}`," in row
