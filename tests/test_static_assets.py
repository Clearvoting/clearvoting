"""Grep gates on the static assets (plan T2.1; spec §6.1–§6.7, §6.9 items 2, 5, 7).

Later tasks append their shell and script gates to this file.
"""
import re
from pathlib import Path

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
    assert SITE_CSS.stat().st_size <= 30 * 1024


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
