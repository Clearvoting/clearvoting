"""Build the four Phase A share cards (1200x630) into static/og/ (spec §9.3).

Dev-time only. Runs with the out-of-repo tools venv (Pillow, fontTools, brotli);
Pillow is never added to requirements.txt and nothing renders on the request path.

    /Users/josephgarcia/.clearvote-worktrees/tools/venv-og/bin/python scripts/build_og_cards.py
"""
import io
import json
import re
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "static" / "fonts"
OUT = ROOT / "static" / "og"

WIDTH, HEIGHT = 1200, 630
MARGIN = 80

# §6.1 tokens
PAPER = "#F5F6FA"
INK = "#1B1B1B"
INK_META = "#5F656D"
NAVY = "#112E51"
BLUE = "#0071BC"
BLUE_DIM = "#205493"
RULE = "#D6D7D9"

TAGLINE = "Facts only · No opinions · No spin"
DOMAIN = "clearvoting.org"
# card name -> one-line descriptor (§9.3); the default card carries the tagline only
CARDS = {
    "default": None,
    "member": "Voting record",
    "bill": "How Congress voted",
    "state": "Your representatives",
}


def load_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    """Open a committed woff2 face: decompress to TrueType in memory for FreeType."""
    font = TTFont(FONTS / filename)
    font.flavor = None
    buffer = io.BytesIO()
    font.save(buffer)
    buffer.seek(0)
    return ImageFont.truetype(buffer, size)


def double_rule(draw: ImageDraw.ImageDraw, y: int) -> None:
    """The masthead's 3px + 1px navy double rule across the margins."""
    draw.rectangle([MARGIN, y, WIDTH - MARGIN, y + 2], fill=NAVY)
    draw.rectangle([MARGIN, y + 6, WIDTH - MARGIN, y + 6], fill=NAVY)


def draw_tracked_centered(draw, y, text, font, fill, tracking) -> None:
    """Centre `text` on the card with extra letter spacing (kicker style)."""
    widths = [draw.textlength(ch, font=font) for ch in text]
    x = (WIDTH - (sum(widths) + tracking * (len(text) - 1))) / 2
    for ch, width in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill, anchor="ls")
        x += width + tracking


def build_card(descriptor: str | None) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)

    double_rule(draw, 72)

    # Wordmark: "Clear" Playfair 800 navy + "Voting" Playfair 600 italic blue, one baseline.
    clear_font = load_font("playfair-display-800.woff2", 128)
    voting_font = load_font("playfair-display-600-italic.woff2", 128)
    clear_width = draw.textlength("Clear", font=clear_font)
    voting_width = draw.textlength("Voting", font=voting_font)
    x = (WIDTH - (clear_width + voting_width)) / 2
    draw.text((x, 236), "Clear", font=clear_font, fill=NAVY, anchor="ls")
    draw.text((x + clear_width, 236), "Voting", font=voting_font, fill=BLUE, anchor="ls")

    draw_tracked_centered(draw, 292, TAGLINE.upper(), load_font("inter-700.woff2", 24), INK_META, 3.4)

    draw.rectangle([MARGIN, 336, WIDTH - MARGIN, 336], fill=RULE)

    if descriptor:
        draw.text((WIDTH / 2, 456), descriptor, font=load_font("playfair-display-700.woff2", 76),
                  fill=INK, anchor="ms")

    draw.text((WIDTH / 2, 536), DOMAIN, font=load_font("inter-600.woff2", 30), fill=BLUE_DIM, anchor="ms")
    double_rule(draw, 556)
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, descriptor in CARDS.items():
        path = OUT / f"{name}.png"
        build_card(descriptor).save(path, optimize=True)
        print(f"{path.relative_to(ROOT)}  {path.stat().st_size // 1024} KB")


# ---------------------------------------------------------------------------
# Phase B (cut-first, spec §9.3): one card per member and per state, rebuilt by
# the weekly sync (`python scripts/build_og_cards.py --entities`). It is the
# Phase A card (build_card(None): rules, wordmark, tagline, domain) with the
# descriptor slot holding a kicker line and the member's or state's name.
# app/main.py _og_image points at these files only when they exist at startup;
# nothing renders per request.
# ---------------------------------------------------------------------------
KICKER_BASELINE = 396
NAME_BASELINE = 476
NAME_SIZES = range(76, 43, -4)      # Playfair 700, largest size that fits one line
_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def cached_font(filename: str, size: int) -> ImageFont.FreeTypeFont:
    """load_font, decompressed once per (face, size) for the 150-card run."""
    if (filename, size) not in _font_cache:
        _font_cache[(filename, size)] = load_font(filename, size)
    return _font_cache[(filename, size)]


def fit_name(draw: ImageDraw.ImageDraw, text: str) -> tuple[ImageFont.FreeTypeFont, bool]:
    """Largest Playfair 700 size that sets `text` on one line inside the margins; (font, fits)."""
    for size in NAME_SIZES:
        font = cached_font("playfair-display-700.woff2", size)
        if draw.textlength(text, font=font) <= WIDTH - 2 * MARGIN:
            return font, True
    return font, False


def entity_card(headline: str, kicker: str) -> Image.Image:
    """Phase A's card with the descriptor line replaced by a tracked kicker and the name."""
    image = build_card(None)
    draw = ImageDraw.Draw(image)
    draw_tracked_centered(draw, KICKER_BASELINE, kicker.upper(), cached_font("inter-700.woff2", 24), INK_META, 3.4)
    font, _fits = fit_name(draw, headline)
    draw.text((WIDTH / 2, NAME_BASELINE), headline, font=font, fill=INK, anchor="ms")
    return image


def build_entity_cards(data_dir: Path, out_dir: Path) -> dict[str, int]:
    """Write member/{id}.png and state/{code}.png for the current roster; delete cards for anyone who left."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from app.render import display_name  # stdlib-only module, importable from venv-og

    members = json.loads((data_dir / "members.json").read_text())["members"]
    member_dir, state_dir = out_dir / "member", out_dir / "state"
    member_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)

    kept: set[str] = set()
    states: dict[str, str] = {}
    for member in members:
        bioguide = (member.get("bioguideId") or "").upper()
        code = (member.get("stateCode") or "").upper()
        if not re.fullmatch(r"[A-Z]\d{6}", bioguide) or not member.get("name") or not re.fullmatch(r"[A-Z]{2}", code):
            continue
        state_name = member.get("state") or code
        name = display_name(member["name"])
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        if not fit_name(probe, name)[1]:
            print(f"og Phase B: {bioguide} name is wider than the card at 44px: {name}")
        entity_card(name, f"{state_name} · Voting record").save(member_dir / f"{bioguide}.png", optimize=True)
        kept.add(bioguide)
        states[code] = state_name
    for code, state_name in sorted(states.items()):
        entity_card(state_name, "Voting record").save(state_dir / f"{code}.png", optimize=True)

    for stale in member_dir.glob("*.png"):
        if stale.stem not in kept:
            stale.unlink()
    for stale in state_dir.glob("*.png"):
        if stale.stem not in states:
            stale.unlink()
    return {"members": len(kept), "states": len(states)}


def build_entity_cards_cli() -> int:
    counts = build_entity_cards(ROOT / "data" / "synced", OUT)
    print(f"og Phase B: {counts['members']} member cards, {counts['states']} state cards")
    return 0


if __name__ == "__main__":
    if "--entities" in sys.argv[1:]:
        sys.exit(build_entity_cards_cli())
    main()
