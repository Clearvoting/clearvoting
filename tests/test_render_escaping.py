"""SSR escaping registry (spec §9.1, §10 #22).

Every renderer that puts data into HTML is registered in RENDERERS with a
callable that embeds the hostile payload it is given somewhere in its output
(as a name, title, headline, …). Each later render task appends its block
renderers here, so one test covers every renderer against every payload."""
import re

import pytest

from app import render
from app.render import display_name, format_bill_code, h, sponsor_name
from tests.test_state_render import FakeDS, member_raw

HOSTILE = [
    "<script>alert(1)</script>",
    '"><img src=x>',
    "&amp;",
    "javascript:alert(1)",
]

RENDERERS = {
    "h": lambda p: h(p),
    "h(display_name)": lambda p: h(display_name(f"{p}, {p}")),
    "h(format_bill_code)": lambda p: h(format_bill_code("hr", p)),
    "h(sponsor_name)": lambda p: h(sponsor_name(
        {"fullName": f"Rep. {p}", "firstName": p, "lastName": p, "state": "NY"})),
}


def assert_escaped(out: str, payload: str) -> None:
    lowered = out.lower()
    assert "<script" not in lowered
    assert "<img" not in lowered
    assert not re.search(r"""(href|src)\s*=\s*["']?\s*javascript:""", lowered)
    if payload == "&amp;":
        # The literal entity text was escaped, not passed through as markup.
        assert "&amp;amp;" in out
    if payload.startswith('"'):
        # The attribute-breaking payload never appears raw. (Not '"><' in general: every
        # block renderer's own markup, e.g. class="page-error"><h1>, contains that.)
        assert payload not in out


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
