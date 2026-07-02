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


def structural_violations(summary: dict, title: str = "") -> list[str]:
    """Return a list of objective rule violations (empty = structurally clean)."""
    violations: list[str] = []

    one_liner = (summary.get("one_liner") or "").strip()
    provisions = [str(p) for p in (summary.get("provisions") or [])]

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

    return violations
