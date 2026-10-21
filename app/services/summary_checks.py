"""Deterministic structural checks for bill summaries.

Prompt rules get ~1-6% violation rates (July 2026 audit); code gets zero.
These run before the AI grader — a structural failure is graded F for free
and the writer-grader loop retries with the specific violations as feedback.
"""
import re

# Word-boundary matched, lowercase. Style rules 7-8 name these; the audit
# confirmed the prompt nearly eliminates them — this makes "nearly" exact.
BANNED_JARGON = (
    "appropriations",
    "fiscal year",
    "pursuant",
    "notwithstanding",
    "promulgate",
    "promulgated",
    "rescind",
    "rescinds",
    "rescission",
    "hereinafter",
)

PLACEHOLDER_MARKERS = ("temporarily unavailable",)

ONE_LINER_MAX_WORDS = 15
PROVISION_MAX_WORDS = 30
PROVISIONS_MIN = 3
PROVISIONS_MAX = 7

# Reader-facing text never needs a link, a number to call or text, or code
# characters; one that appears was steered in by the inputs or hallucinated.
# Bare .gov names stay allowed: bills name official sites (USAspending.gov),
# and .gov registration is restricted to government bodies.
WEB_ADDRESS_RE = re.compile(r"https?://|www\.|\b[a-z0-9-]{2,}\.(?!gov\b)[a-z]{2,}\b(?!\.[a-z0-9])", re.I)
PHONE_RE = re.compile(r"(?:\(\d{3}\)\s?|\b\d{3}[-.\s])\d{3}[-.\s]\d{4}\b|\btext\s+\S+\s+to\s+\d{5,6}\b", re.I)
MARKUP_RE = re.compile(r"[<>{}]")


def structural_violations(summary: dict, title: str = "") -> list[str]:
    """Return a list of objective rule violations (empty = structurally clean)."""
    violations: list[str] = []

    one_liner = summary.get("one_liner") or ""
    provisions = summary.get("provisions") or []
    # Types first: a string of provisions renders one letter per bullet, and
    # a non-string one_liner would crash the checks below.
    if not isinstance(one_liner, str):
        violations.append("one_liner must be a string")
        one_liner = ""
    if not (isinstance(provisions, list) and all(isinstance(p, str) for p in provisions)):
        violations.append("provisions must be a list of strings")
        provisions = []
    one_liner = one_liner.strip()

    if not one_liner:
        violations.append("one_liner is empty")
    else:
        words = len(one_liner.split())
        if words > ONE_LINER_MAX_WORDS:
            violations.append(f"one_liner is {words} words; max is {ONE_LINER_MAX_WORDS}")
        if one_liner.endswith("."):
            violations.append("one_liner must not end with a period")
        if title and one_liner.strip().lower() == title.strip().lower():
            violations.append("one_liner must not repeat the official title verbatim")

    if not provisions:
        violations.append("provisions is empty")
    elif not PROVISIONS_MIN <= len(provisions) <= PROVISIONS_MAX:
        violations.append(f"provisions must have {PROVISIONS_MIN} to {PROVISIONS_MAX} items (has {len(provisions)})")

    for i, p in enumerate(provisions):
        words = len(p.split())
        if words > PROVISION_MAX_WORDS:
            violations.append(f"provision {i + 1} is {words} words; keep each under {PROVISION_MAX_WORDS}")

    text = " ".join([one_liner] + provisions).lower()
    for term in BANNED_JARGON:
        if re.search(rf"\b{re.escape(term)}\b", text):
            violations.append(f'banned jargon: "{term}" — use a plain-language alternative')
    for marker in PLACEHOLDER_MARKERS:
        if marker in text:
            violations.append("placeholder text present in reader-facing content")
    for rx, what in ((WEB_ADDRESS_RE, "web address"), (PHONE_RE, "phone or text number"),
                     (MARKUP_RE, "markup character")):
        m = rx.search(text)
        if m:
            violations.append(f'{what} "{m.group(0)}" in reader-facing content — remove it')

    return violations
