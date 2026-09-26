"""Grep gates on the static assets (plan T2.1; spec §6.1–§6.7, §6.9 items 2, 5, 7).

Later tasks append their shell and script gates to this file.
"""
import re
from pathlib import Path

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
SITE_CSS = STATIC / "css" / "site.css"

TOKENS = {
    "--paper": "#F5F6FA", "--card": "#FFFFFF", "--ink": "#1B1B1B", "--ink-soft": "#5B616B",
    "--ink-meta": "#5F656D", "--navy": "#112E51", "--blue": "#0071BC", "--blue-dim": "#205493",
    "--yes": "#2E7D3A", "--yes-text": "#1F5E2D", "--yes-tint": "#DDE7E3", "--no": "#B3261E",
    "--no-text": "#8E1B21", "--no-tint": "#EDDDE0", "--error": "#8A1C1C", "--rule": "#D6D7D9",
    "--rule-soft": "#E8E8E8", "--tap": "44px", "--radius-chip": "4px", "--radius-ctl": "8px",
}
TYPE_TOKENS = {
    "--t-kicker": "0.8125rem", "--t-meta": "0.8rem", "--t-ui": "0.875rem", "--t-body": "1rem",
    "--t-official": "1.05rem", "--t-lede": "1.125rem", "--t-row": "1.15rem", "--t-h3": "1.35rem",
    "--t-h2": "clamp(1.45rem, 3vw, 2rem)", "--t-display": "clamp(2rem, 5vw, 3.2rem)",
    "--t-logo": "clamp(1.6rem, 4.5vw, 2.4rem)",
}
SPACING = {"--s1": "0.25rem", "--s2": "0.5rem", "--s3": "0.75rem", "--s4": "1rem", "--s6": "1.5rem",
           "--s8": "2rem", "--s10": "2.5rem", "--s12": "3rem", "--s16": "4rem"}
COMPONENTS = [
    ".masthead", ".masthead-nav", ".edition", ".edition-mid", ".site-footer", ".kicker", ".deck",
    ".seal", ".seal--final", ".seal--moving", ".seal--pending", ".seal--ballot", ".chip", ".chip--yes",
    ".chip--no", ".chip--nv", ".chip--present", ".chip--other", ".chip--absent", ".tally", ".vote-row",
    ".person", ".photo", ".rc", ".bill-row", ".btn", ".btn--secondary", ".party-toggle", ".note",
    ".state-link", ".vote-card", ".feedback-btn", ".party", ".speaker-pick", "#feedback-modal",
    ".field-error", ".visually-hidden", ".skip-link",
]
BREAKPOINT_560 = "@media (min-width: 560px) {"
BREAKPOINT_880 = "@media (min-width: 880px) {"


def _css() -> str:
    return re.sub(r"/\*.*?\*/", "", SITE_CSS.read_text(), flags=re.S)


def _root_block(css: str) -> str:
    start = css.index(":root {")
    return css[start:css.index("}", start)]


def _outside_root(css: str) -> str:
    start = css.index(":root {")
    return css[:start] + css[css.index("}", start) + 1:]


def _rules(css: str) -> list[tuple[str, str]]:
    """(selector, declarations) for every innermost rule, media wrappers ignored."""
    return [(m.group(1).strip(), m.group(2)) for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css)]


def _declarations(css: str, prop: str) -> list[tuple[str, str]]:
    found = []
    for selector, body in _rules(css):
        for m in re.finditer(rf"(?:^|;)\s*{re.escape(prop)}\s*:\s*([^;]+)", body):
            found.append((selector, m.group(1).strip()))
    return found


def _luminance(hex_colour: str) -> float:
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


# --- site.css (T2.1) ---

def test_site_css_exists_and_stays_under_30_kb():
    # The 30 KB budget bounds the stylesheet's rules. T8.3's fixed @font-face preamble
    # (ten web faces + six metric fallbacks, ~3.1 KB) sits above it and is not counted.
    css = SITE_CSS.read_text()
    rules = css[css.index("/* ClearVoting site.css"):]
    assert "@font-face" not in rules
    assert len(rules.encode()) <= 30 * 1024


def test_one_root_block_holds_the_spec_tokens():
    css = _css()
    assert len(re.findall(r"(?m)^:root \{", css)) == 1
    root = _root_block(css)
    for name, value in {**TOKENS, **TYPE_TOKENS, **SPACING}.items():
        assert f"{name}: {value};" in root, name


def test_kicker_token_is_0_75rem_from_560_up():
    css = _css()
    block = css[css.index(BREAKPOINT_560):css.index(BREAKPOINT_880)]
    assert ":root { --t-kicker: 0.75rem;" in block


def test_font_size_only_through_type_tokens():
    css = _css()
    outside = _outside_root(css)
    for selector, value in _declarations(outside, "font-size"):
        assert re.fullmatch(r"var\(--t-[a-z0-9-]+\)", value), f"{selector}: font-size {value}"
    assert re.search(r"(?:^|[;{\s])font\s*:", outside) is None, "no font shorthand"


def test_colours_only_through_tokens():
    outside = _outside_root(_css())
    assert re.search(r"#[0-9a-fA-F]{3,8}\b", outside) is None
    assert re.search(r"\b(?:rgb|rgba|hsl|hsla)\(", outside) is None


def test_box_shadow_only_on_the_two_interactive_cards():
    for selector, value in _declarations(_css(), "box-shadow"):
        for part in selector.split(","):
            assert re.fullmatch(r"\.(state-link|vote-card)(:[a-z-]+)?", part.strip()), f"{selector}: box-shadow"


def test_border_radius_only_4px_or_8px():
    allowed = {"4px", "8px", "var(--radius-chip)", "var(--radius-ctl)"}
    for selector, value in _declarations(_outside_root(_css()), "border-radius"):
        assert value in allowed, f"{selector}: border-radius {value}"


def test_no_outline_none_and_one_global_focus_ring():
    css = _css()
    assert re.search(r"outline\s*:\s*(none|0)\b", css) is None
    assert (":where(a, button, input, select, textarea, summary, [tabindex]):focus-visible "
            "{ outline: 2px solid var(--blue); outline-offset: 3px; }") in css


def test_nothing_defaults_to_opacity_zero():
    assert re.search(r"opacity\s*:\s*0(\.0+)?\s*[;}]", _css()) is None


def test_two_breakpoints_declared_once_at_the_end():
    css = _css()
    assert css.count(BREAKPOINT_560) == 1 and css.count(BREAKPOINT_880) == 1
    widths = re.findall(r"@media[^{]*\((?:min|max)-width:\s*([0-9.]+)px\)", css)
    assert sorted(widths) == ["560", "880"]
    tail = css[css.index(BREAKPOINT_560):]
    assert tail.count("@media") == 2
    assert css.index(BREAKPOINT_560) < css.index(BREAKPOINT_880)


def test_colour_scheme_reduced_motion_and_scroll_margin():
    css = _css()
    assert "color-scheme: light;" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "scroll-margin-top: 56px;" in css


def test_feedback_button_floats_only_from_880():
    css = _css()
    wide = css[css.index(BREAKPOINT_880):]
    assert re.search(r"\.feedback-btn \{[^}]*display: none;", css[:css.index(BREAKPOINT_560)])
    assert "bottom: calc(1rem + env(safe-area-inset-bottom));" in wide
    assert "main { padding-bottom: 72px; }" in wide
    assert "html { scroll-padding-bottom: 72px; }" in wide


def test_every_component_class_is_styled():
    css = _css()
    for selector in COMPONENTS:
        assert re.search(rf"{re.escape(selector)}(?![a-zA-Z0-9_-])", css), selector


def test_red_tokens_only_in_the_vote_component():
    for name in ("--no", "--no-text", "--no-tint"):
        for selector, _body in [(s, b) for s, b in _rules(_outside_root(_css())) if f"var({name})" in b]:
            assert re.search(r"chip--no|tally", selector), f"{selector} uses {name}"


def test_text_tokens_meet_4_5_to_1_on_paper_and_card():
    for name in ("--ink", "--ink-soft", "--ink-meta", "--navy", "--blue", "--blue-dim", "--yes",
                 "--yes-text", "--no", "--no-text", "--error"):
        for ground in ("--paper", "--card"):
            ratio = _contrast(TOKENS[name], TOKENS[ground])
            assert ratio >= 4.5, f"{name} on {ground}: {ratio:.2f}"
    assert _contrast(TOKENS["--yes-text"], TOKENS["--yes-tint"]) >= 4.5
    assert _contrast(TOKENS["--no-text"], TOKENS["--no-tint"]) >= 4.5
    assert _contrast(TOKENS["--card"], TOKENS["--navy"]) >= 4.5


# --- site.js behaviour hooks (plan T2.3; spec §5.4, §6.3, §6.4, §8 items 10–11) ---

SITE_JS = STATIC / "js" / "site.js"


def test_site_js_binds_the_shared_markup_contract():
    js = SITE_JS.read_text()
    for hook in (".party-toggle", ".party-status", "data-party-url", ".share-btn", "[data-share]",
                 "data-share-url", "data-share-title", "data-share-text", ".share-status",
                 "notify-form", "notify-fields", "notify-state", "notify-email", "notify-email-error",
                 "notify-submit", "notify-status", "nav-mine", ".photo img", ".speaker-pick[data-rc]",
                 ".member-header .party"):
        assert hook in js, hook


def test_site_js_storage_rules():
    js = SITE_JS.read_text()
    assert "const HOME_KEY = 'cv-home';" in js and "const PARTY_KEY = 'cv-show-party';" in js
    assert "storageSet('sessionStorage', PARTY_KEY, '1')" in js
    assert "storageSet('localStorage', PARTY_KEY" not in js       # the reveal never persists across visits
    assert "storageRemove('localStorage', PARTY_KEY)" in js        # legacy key removed on load
    assert "document.cookie" not in js
    assert "aria-pressed" not in js and "aria-live" not in js
    # A Hide pressed while a reveal is loading wins: stale reveals bail after every wait.
    assert "const mine = ++attempt;" in js and "attempt++;" in js
    assert js.count("if (mine !== attempt || !revealed)") >= 3
    # A second "Link copied" is announced; a 422 from /api/notify is the email, not an outage.
    assert "statusNode.textContent = '';" in js
    assert "response.status === 422" in js and "setEmailError(t('invalidEmail'))" in js
    for fn in ("initPartyToggle", "initShare", "initPhotos", "initHome", "rememberDistrict", "forgetHome",
               "rewriteMastheadLink", "initNotify", "focusHeading", "rememberedLine", "readHome"):
        assert re.search(rf"^(?:async )?function {fn}\(", js, re.M), fn


def test_site_js_copy_is_quoted_from_the_spec():
    js = SITE_JS.read_text()
    for copy in ("'Show party labels'", "'Hide party labels'", "'Party labels shown'", "'Party labels hidden'",
                 "'Link copied'", "\"Thanks — we'll email you when {state} is added.\"",
                 "\"We couldn't save that. Please try again in a few minutes.\"",
                 "\"That doesn't look like an email address.\"", "'Remembered: {place}'",
                 "'Remember District {district} as mine'", "'No final votes on bills in our record yet'"):
        assert copy in js, copy


# --- Shell gates and the native feedback dialog (plan T2.4; spec §2.2 #2–#5, §6.4 dialog, §6.9 item 7) ---

SHELLS = sorted(STATIC.glob("*.html"))
DIALOG_IDS = ["feedback-modal", "feedback-open", "feedback-cancel", "feedback-overlay", "feedback-form",
              "feedback-message", "feedback-submit", "feedback-status", "feedback-context"]


def _tag(html: str, tag: str, element_id: str) -> str:
    match = re.search(rf"<{tag}\b[^>]*\bid=\"{element_id}\"[^>]*>", html)
    assert match, f"<{tag} id={element_id}> missing"
    return match.group(0)


def test_every_shell_keeps_title_head_and_no_inline_script():
    assert len(SHELLS) >= 6
    for shell in SHELLS:
        html = shell.read_text()
        assert re.search(r"<title>[^<]+</title>", html), shell.name
        assert "</head>" in html, shell.name
        assert re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html) is None, shell.name
        assert re.search(r"\son[a-z]+\s*=", html, re.I) is None, shell.name


def test_every_shell_has_the_native_feedback_dialog():
    for shell in SHELLS:
        html = shell.read_text()
        for element_id in DIALOG_IDS:
            assert html.count(f'id="{element_id}"') == 1, f"{shell.name}: #{element_id}"
        dialog = _tag(html, "dialog", "feedback-modal")
        assert 'aria-labelledby="feedback-title"' in dialog and " hidden" not in dialog, shell.name
        assert re.search(r"<h2\b[^>]*\bid=\"feedback-title\"[^>]*>Send feedback</h2>", html), shell.name
        assert re.search(r"<label\b[^>]*\bfor=\"feedback-message\"[^>]*>What did you see\?</label>", html), shell.name
        assert "autofocus" in _tag(html, "textarea", "feedback-message"), shell.name
        status = _tag(html, "p", "feedback-status")
        assert 'role="status"' in status and " hidden" not in status, shell.name
        assert html[html.index(status) + len(status):].startswith("</p>"), f"{shell.name}: status not empty"
        assert '<div id="feedback-modal"' not in html, shell.name


def test_every_shell_has_an_empty_freshness_span_for_the_server():
    for shell in SHELLS:
        html = shell.read_text()
        assert html.count('<span id="data-freshness"></span>') == 1, shell.name
        assert re.search(r"·\s*<span id=\"data-freshness\">", html) is None, shell.name


# --- Home shell and app.js (plan T3.3) ---

def test_index_shell_contract():
    html = (STATIC / "index.html").read_text()
    assert re.search(r"<title>[^<]+</title>", html)
    assert "</head>" in html
    main = re.search(r'<main id="main-content" tabindex="-1">(.*?)</main>', html, re.S)
    assert main and "<!--content-->" in main.group(1)
    masthead = re.search(r'<header class="masthead">(.*?)</header>', html, re.S)
    assert masthead and "<!--edition-->" in masthead.group(1)
    assert re.search(r'href="/static/css/site\.css\?v=\d+"', html)
    assert "styles.css" not in html and "broadsheet.css" not in html
    scripts = re.findall(r'<script src="/static/js/([a-z]+)\.js\?v=\d+"></script>', html)
    assert scripts == ["site", "app", "feedback"]
    assert '<dialog id="feedback-modal"' in html
    for hook in ("feedback-modal", "feedback-open", "feedback-cancel", "feedback-overlay",
                 "feedback-form", "feedback-message", "feedback-submit", "feedback-status",
                 "feedback-context", "data-freshness"):
        assert f'id="{hook}"' in html
    assert '<a href="/#find" id="nav-mine">My representatives</a>' in html


def test_index_shell_has_no_inline_script_or_handler():
    html = (STATIC / "index.html").read_text()
    assert re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html) is None
    assert re.search(r"\son[a-z]+\s*=", html, re.I) is None
    assert "aria-live" not in html


def test_app_js_is_a_thin_enhancer():
    js = (STATIC / "js" / "app.js").read_text()
    for gone in ("loadDelegation", "selectState", "renderDelegation", "splitBar", "include_stats",
                 "cv-show-party", "innerHTML", "insertAdjacentHTML", "document.title",
                 "pushState", "role: 'link'", "billOffset += BILL_LIMIT", "style.color"):
        assert gone not in js
    assert "new URLSearchParams(window.location.search).get('q')" in js
    assert "history.replaceState" in js
    assert "billOffset = offset;" in js
    # §4.1 m3 / §4.4 m2: the absent chip names the vote's chamber, not chip()'s 'House' default.
    assert "chip(m.position, { chamber: vote.chamber })" in js
    assert "Adopted by the" not in js  # final-vs-moving comes from derived_status.variant


def test_site_js_binds_the_home_markup_contract():
    js = (STATIC / "js" / "site.js").read_text()
    for hook in ("notify-form", "notify-state", "notify-email", "notify-status", "notify-fields", "nav-mine"):
        assert hook in js


def test_person_row_rules_are_declared_once():
    # T2.1 owns the person row; page tasks add deltas, never a second .person rule (plan T4.2).
    assert len(re.findall(r"(?m)^\s*\.person \{", _css())) == 1


# --- Self-hosted fonts (T8.3, spec §6.2 / §9.6) ---

FONT_STATIC = Path(__file__).parent.parent / "static"
FONT_SHELLS = [
    "index.html", "state.html", "member.html", "bill.html",
    "about.html", "methodology.html", "privacy.html", "404.html",
]
FONT_FILES = [
    "playfair-display-700.woff2", "playfair-display-800.woff2", "playfair-display-600-italic.woff2",
    "lora-400.woff2", "lora-400-italic.woff2", "lora-500.woff2",
    "inter-400.woff2", "inter-500.woff2", "inter-600.woff2", "inter-700.woff2",
]
PRELOADED_FONTS = ["playfair-display-700.woff2", "lora-400.woff2", "inter-400.woff2"]
FONT_STACKS = {
    '"Playfair Display"': '"Playfair Display", "Playfair Display Fallback", Georgia, serif',
    '"Lora"': '"Lora", "Lora Fallback", Georgia, serif',
    '"Inter"': '"Inter", "Inter Fallback", Arial, sans-serif',
}


def _font_css() -> str:
    return (FONT_STATIC / "css" / "site.css").read_text()


def test_font_files_are_committed_woff2_with_the_licence():
    for name in FONT_FILES:
        data = (FONT_STATIC / "fonts" / name).read_bytes()
        assert data[:4] == b"wOF2", name
        assert len(data) > 5000, name
    licence = (FONT_STATIC / "fonts" / "OFL.txt").read_text()
    assert "SIL Open Font License" in licence
    for family in ("Playfair Display", "Lora", "Inter"):
        assert family in licence


def test_no_google_fonts_reference_anywhere_in_static():
    for path in FONT_STATIC.rglob("*"):
        if path.suffix in {".html", ".css", ".js"}:
            text = path.read_text()
            assert "fonts.googleapis.com" not in text, path
            assert "fonts.gstatic.com" not in text, path


def test_every_shell_preloads_the_three_first_paint_fonts_before_the_stylesheet():
    for shell in FONT_SHELLS:
        html = (FONT_STATIC / shell).read_text()
        stylesheet_at = html.index("/static/css/site.css")
        for font in PRELOADED_FONTS:
            link = f'<link rel="preload" href="/static/fonts/{font}" as="font" type="font/woff2" crossorigin>'
            assert html.count(link) == 1, (shell, font)
            assert html.index(link) < stylesheet_at, (shell, font)
        assert html.count('rel="preload"') == 3, shell


def test_site_css_declares_ten_swapped_faces_and_three_fallbacks_first():
    css = _font_css()
    assert css.index("@font-face") < css.index(":root")
    faces = re.findall(r"@font-face\s*\{(.*?)\}", css, re.S)
    web = [f for f in faces if "url(" in f]
    fallback = [f for f in faces if "local(" in f]
    urls = sorted(re.search(r'url\("/static/fonts/([^"]+)"\)', f).group(1) for f in web)
    assert urls == sorted(FONT_FILES)
    for face in web:
        assert "font-display: swap" in face
        assert 'format("woff2")' in face
    faces_by_weight = sorted(
        (re.search(r'font-family:\s*"([^"]+)"', f).group(1), int(re.search(r"font-weight:\s*(\d+)", f).group(1)))
        for f in fallback
    )
    # One fallback per weight the site sets (Inter 600/700 carry kickers, nav, seals,
    # chips and buttons; Lora 500 the deck), so no swap relies on synthetic bold (F55).
    assert faces_by_weight == [
        ("Inter Fallback", 400), ("Inter Fallback", 600), ("Inter Fallback", 700),
        ("Lora Fallback", 400), ("Lora Fallback", 500),
        ("Playfair Display Fallback", 700),
    ]
    for face in fallback:
        assert "size-adjust:" in face
        assert "ascent-override:" in face
        assert "descent-override:" in face
        weight = int(re.search(r"font-weight:\s*(\d+)", face).group(1))
        if '"Inter Fallback"' in face:
            assert ('local("Arial Bold")' in face) == (weight >= 600), face


def test_every_font_stack_names_its_metric_fallback():
    css = re.sub(r"@font-face\s*\{.*?\}", "", _font_css(), flags=re.S)
    values = re.findall(r"(?:font-family|--font[\w-]*)\s*:\s*([^;]+);", css)
    assert values, "site.css declares no font-family"
    for family, stack in FONT_STACKS.items():
        assert stack in css, family
    for value in values:
        for family, stack in FONT_STACKS.items():
            if value.strip().startswith(family):
                assert value.strip() == stack, value


# --- Retired assets (plan T9.1; spec §6.7 and §10.3 commit 9) ---

_REPO = Path(__file__).resolve().parent.parent
_RETIRED_ASSETS = ("static/css/styles.css", "static/css/broadsheet.css", "static/js/viz.js")
_RETIRED_NAMES = ("styles.css", "broadsheet.css", "viz.js")
_SHELLS = {
    "index.html", "state.html", "member.html", "bill.html",
    "about.html", "methodology.html", "privacy.html", "404.html",
}


def _retired_scan_files():
    """Every file that could link or load an asset: static HTML/JS/CSS, app code, sync and scripts."""
    files = [p for p in (_REPO / "static").rglob("*") if p.is_file() and p.suffix in {".html", ".js", ".css"}]
    files += list((_REPO / "app").rglob("*.py"))
    files += list((_REPO / "scripts").glob("*.py"))
    files.append(_REPO / "sync.py")
    # The retired files themselves name each other in comments; they are what this guard protects against,
    # not something it scans, so the test passes before and after the deletion.
    return sorted(p for p in files if p.relative_to(_REPO).as_posix() not in _RETIRED_ASSETS)


@pytest.mark.parametrize("rel", _RETIRED_ASSETS)
def test_retired_asset_is_deleted(rel):
    assert not (_REPO / rel).exists(), f"retired asset still on disk: {rel}"


def test_no_file_references_retired_assets():
    offenders = []
    for path in _retired_scan_files():
        text = path.read_text(encoding="utf-8")
        for name in _RETIRED_NAMES:
            if name in text:
                offenders.append(f"{path.relative_to(_REPO)} mentions {name}")
    assert offenders == []


def test_no_js_calls_the_retired_viz_global():
    offenders = [
        str(p.relative_to(_REPO))
        for p in sorted((_REPO / "static" / "js").glob("*.js"))
        # viz.js exports window.ClearVoteViz; callers either use it directly or alias it to a local Viz.
        if p.relative_to(_REPO).as_posix() not in _RETIRED_ASSETS
        and re.search(r"ClearVoteViz|\bViz\.", p.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_every_shell_links_only_site_css():
    shells = sorted((_REPO / "static").glob("*.html"))
    assert {p.name for p in shells} == _SHELLS
    for shell in shells:
        text = shell.read_text(encoding="utf-8")
        tags = re.findall(r"<link\b[^>]*\brel=\"stylesheet\"[^>]*>", text)
        hrefs = [re.search(r"\bhref=\"([^\"?]+)", tag).group(1) for tag in tags]
        assert hrefs == ["/static/css/site.css"], f"{shell.name} links {hrefs}"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", [
    "/static/css/styles.css",
    "/static/css/broadsheet.css",
    "/static/js/viz.js",
])
async def test_retired_asset_urls_are_not_served(url):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(url)
    assert response.status_code == 404
    assert response.headers["cache-control"] == "public, max-age=60"


# --- Print block (plan T10.3, spec §6.8) ---
_G10_ROOT = Path(__file__).parent.parent
_G10_CSS = _G10_ROOT / "static" / "css" / "site.css"
_G10_JS = _G10_ROOT / "static" / "js" / "site.js"
_PRINT_HIDDEN = (".masthead-nav", ".edition", ".actions", ".strip", "dialog", ".feedback-btn", ".site-footer nav")


def _print_block(css: str) -> str:
    start = css.find("@media print")
    assert start != -1, "site.css has no @media print block"
    depth = 0
    for i in range(css.index("{", start), len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[start:i + 1]
    raise AssertionError("unterminated @media print block")


def test_print_block_hides_chrome_and_prints_on_white():
    block = _print_block(_G10_CSS.read_text())
    for selector in _PRINT_HIDDEN:
        assert selector in block, selector
    assert "display: none" in block
    assert "background: var(--card)" in block
    assert "a::after" in block and "content: none" in block


def test_print_block_has_no_font_size_literals():
    assert "font-size" not in _print_block(_G10_CSS.read_text())


def test_print_block_selectors_match_real_markup():
    """Every class the print block hides exists in a shell or in a server renderer (the strip is T10.4's)."""
    sources = "".join(p.read_text() for p in (_G10_ROOT / "static").glob("*.html"))
    sources += (_G10_ROOT / "app" / "render.py").read_text()
    for cls in ("masthead-nav", "edition", "actions", "feedback-btn", "site-footer"):
        assert re.search(rf'class="[^"]*\b{cls}\b', sources), f"no element carries class {cls}"


def test_site_js_opens_details_for_print_and_restores_them():
    source = _G10_JS.read_text()
    assert "beforeprint" in source and "afterprint" in source
    # The call inside initSite(), not the declaration: `function initPrint() {` also contains "initPrint()".
    init_site = source[source.index("function initSite()"):]
    init_site = init_site[: init_site.index("\n}\n") + 3]
    assert re.search(r"^\s+initPrint\(\);", init_site, re.M), "initPrint(); is not called from initSite()"


def test_print_skips_lazy_and_form_details():
    """Review T10.3: printing must not open a fetch-on-toggle <details> (rc-all, rc-more,
    official-full) or one holding a form (the notify signup)."""
    source = _G10_JS.read_text()
    body = source[source.index("function initPrint()"):]
    body = body[: body.index("\n}\n")]
    for marker in (":not([data-url])", ":not([data-summary-slot])", "querySelector('form')"):
        assert marker in body, marker
    render = (_G10_ROOT / "app" / "render.py").read_text()
    for cls in ("rc-all", "rc-more"):
        assert re.search(rf'<details class="{cls}"[^>]*data-url=', render), f"{cls} lost its data-url marker"
    assert '<details class="official-full" data-summary-slot>' in render
    assert re.search(r'<details class="notify-disclosure">.{0,80}<form', render, re.S)


# --- Sticky strip (plan T10.4) ---
def test_member_and_bill_shells_carry_the_strip_marker():
    root = Path(__file__).parent.parent / "static"
    for shell in ("member.html", "bill.html"):
        text = (root / shell).read_text()
        assert text.count("<!--strip-->") == 1
        assert text.index("<!--strip-->") < text.index("<header")


def test_strip_css_shows_without_layout_shift():
    css = (Path(__file__).parent.parent / "static" / "css" / "site.css").read_text()
    rule = css[css.index(".strip {"): css.index("}", css.index(".strip {"))]
    for decl in ("position: fixed", "top: 0", "transform: translateY(-100%)", "visibility: hidden"):
        assert decl in rule, decl
    assert ".strip.is-shown" in css
    assert "scroll-padding-top: 56px" in css
    assert "box-shadow" not in rule


def test_site_js_starts_the_strip_from_init_site():
    source = (Path(__file__).parent.parent / "static" / "js" / "site.js").read_text()
    init_site = source[source.index("function initSite()"):]
    init_site = init_site[: init_site.index("\n}\n") + 3]
    # The call, not the declaration: `function initStrip() {` also contains "initStrip()".
    assert re.search(r"^\s+initStrip\(\);", init_site, re.M), "initStrip(); is not called from initSite()"
