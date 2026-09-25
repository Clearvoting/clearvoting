"""SSR escaping registry (spec §9.1, §10 #22).

Every renderer that puts data into HTML is registered in RENDERERS with a
callable that embeds the hostile payload it is given somewhere in its output
(as a name, title, headline, …). Each later render task appends its block
renderers here, so one test covers every renderer against every payload."""
import re

import pytest

from app import render
from app.render import display_name, format_bill_code, h, sponsor_name

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
