"""Copy rules that span files (spec §4.6, §4.7, §7.4, §7.6, §7.7, §12.3) — plan Task T5.1."""
import re
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.ai_summary import SYSTEM_PROMPT

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures" / "synced"
SHELLS = sorted((ROOT / "static").glob("*.html"))
JS_FILES = sorted((ROOT / "static" / "js").glob("*.js"))
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})")
EXAMPLE_DOMAINS = {"example.com", "example.org"}   # input placeholders, not contact addresses
ASSET_SUFFIXES = {"png", "jpg", "jpeg", "gif", "svg", "webp", "css", "js"}   # "icon@2x.png" is not an address
BALLOT_PERSON_RE = re.compile(r"\b(On|Not on) the ballot")
PLACEHOLDER_RE = re.compile(r"\{[a-z_][a-z0-9_]*\}")


def _patch_data_dir():
    return patch("app.dependencies.get_data_dir", return_value=FIXTURES)


def _clear_data_service_cache():
    from app.dependencies import get_data_service
    get_data_service.cache_clear()


async def _get(path: str):
    with _patch_data_dir():
        _clear_data_service_cache()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
    _clear_data_service_cache()
    return response


class _ListItems(HTMLParser):
    """Text of each top-level <li> of the <ol> whose id is list_id."""

    def __init__(self, list_id: str):
        super().__init__()
        self.list_id = list_id
        self.depth = 0
        self.item = None
        self.items: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "ol" and dict(attrs).get("id") == self.list_id:
            self.depth = 1
        elif self.depth and tag == "ol":
            self.depth += 1
        elif self.depth == 1 and tag == "li":
            self.item = ""

    def handle_endtag(self, tag):
        if self.depth and tag == "ol":
            self.depth -= 1
        elif self.depth == 1 and tag == "li" and self.item is not None:
            self.items.append(self.item.strip())
            self.item = None

    def handle_data(self, data):
        if self.item is not None:
            self.item += data


def _list_items(html: str, list_id: str) -> list[str]:
    parser = _ListItems(list_id)
    parser.feed(html)
    return parser.items


def _prompt_list(heading: str) -> list[str]:
    """Parse the prompt independently of app.render.prompt_rules."""
    block = re.search(rf"^{heading}[^\n]*\n(.*?)\n\n", SYSTEM_PROMPT, re.S | re.M).group(1)
    return re.findall(r"^\d+\.\s+(.+)$", block, re.M)


def _emails(text: str) -> list[str]:
    return [
        m.group(0) for m in EMAIL_RE.finditer(text)
        if m.group(1).lower() not in EXAMPLE_DOMAINS
        and m.group(1).lower().rsplit(".", 1)[-1] not in ASSET_SUFFIXES
    ]


# --- The neutrality rules on /methodology equal the prompt ---

async def test_methodology_rule_lists_equal_the_prompt():
    html = (await _get("/methodology")).text
    neutrality = _prompt_list("STRICT RULES")
    accuracy = _prompt_list("ACCURACY RULES")
    assert neutrality and accuracy
    assert "Our rules for neutrality" in html
    assert _list_items(html, "neutrality-rules") == neutrality
    assert _list_items(html, "accuracy-rules") == accuracy
    assert not re.search(r"\b\d+ (strict )?rules\b", html, re.I), "no rule count in prose"


# --- No email address is published (§12.3 decision 1) ---

def test_no_email_address_in_shells_scripts_or_render_code():
    found = []
    for path in [*SHELLS, *JS_FILES, ROOT / "app" / "render.py"]:
        found += [f"{path.name}: {e}" for e in _emails(path.read_text())]
    assert found == []


@pytest.mark.parametrize("path", ["/about", "/methodology", "/privacy", "/no-such-page"])
async def test_trust_pages_publish_no_email_address(path):
    html = (await _get(path)).text
    assert "mailto:" not in html
    assert _emails(html) == []


# --- Ballot copy describes the seat, never the person (§7.4) ---

def test_ballot_copy_never_describes_the_person():
    files = [ROOT / "app" / "render.py", ROOT / "static" / "js" / "site.js", *SHELLS]
    hits = [
        f"{path.name}:{n}"
        for path in files if path.exists()
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if BALLOT_PERSON_RE.search(line)
    ]
    assert hits == []


# --- No {placeholder} survives in shipped copy (§7.7) ---

@pytest.mark.parametrize("path", ["/", "/state?code=NY", "/about", "/methodology", "/privacy", "/no-such-page"])
async def test_no_placeholder_survives_in_rendered_copy(path):
    response = await _get(path)
    assert PLACEHOLDER_RE.findall(response.text) == []


# --- /privacy matches the code (§4.7) ---

def test_privacy_storage_claims_match_the_scripts():
    text = "\n".join(path.read_text() for path in JS_FILES)
    assert "document.cookie" not in text
    assert set(re.findall(r"""['"](cv-[a-z-]+)['"]""", text)) <= {"cv-home", "cv-show-party"}


def test_privacy_never_claims_the_reveal_stays_local():
    # The party reveal asks our server for ?show_party=true, so it is in the request logs (§4.7).
    if any("show_party=true" in path.read_text() for path in JS_FILES):
        assert "never sent to us" not in (ROOT / "static" / "privacy.html").read_text()


# Self-scoping checks: a legacy file is exempt only while it still carries its legacy marker,
# so each check passes at every commit and tightens by itself when T6.3 / T7.4 rewrite
# member.js / bill.js (the marker goes) and when T8.3 creates static/fonts/ (every shell and
# stylesheet is then checked). No later task has to remove a marker.
LEGACY_PARTY_MARKER = "let showParty = localStorage"


def test_party_reveal_is_never_persisted_in_local_storage():
    offenders = [
        f"{path.name}:{n}"
        for path in JS_FILES
        if LEGACY_PARTY_MARKER not in path.read_text()
        for n, line in enumerate(path.read_text().splitlines(), 1)
        if "localStorage" in line and "cv-show-party" in line and "removeItem" not in line
    ]
    assert offenders == []


def test_privacy_third_party_claim_holds_no_font_hosts():
    if not (ROOT / "static" / "fonts").is_dir():
        pytest.skip("fonts are self-hosted from T8.3; until then every shell loads Google Fonts")
    files = [*SHELLS, *sorted((ROOT / "static" / "css").glob("*.css"))]
    assert [p.name for p in files if re.search(r"fonts\.(googleapis|gstatic)\.com", p.read_text())] == []
