"""Build the four Phase A share cards (1200x630) into static/og/ (spec §9.3).

Dev-time only. Runs with the out-of-repo tools venv (Pillow, fontTools, brotli);
Pillow is never added to requirements.txt and nothing renders on the request path.

    /Users/josephgarcia/.clearvote-worktrees/tools/venv-og/bin/python scripts/build_og_cards.py
"""
import io
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


if __name__ == "__main__":
    main()
