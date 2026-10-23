"""Shared types and utilities for grader services."""

from dataclasses import dataclass, field
from typing import Protocol

# Single source of truth for the Claude model used by all AI services.
# Use the undated alias — date-suffixed snapshot IDs retire and break every call site.
CLAUDE_MODEL = "claude-sonnet-4-6"


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else len(text)
        text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


GRADE_ORDER = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
PASSING_GRADES = ("A", "B")


@dataclass
class GradeResult:
    grade: str
    passed: bool
    feedback: str
    checks: dict = field(default_factory=dict)


def grade_from_reply(result) -> GradeResult:
    """Turn a grader model's parsed JSON reply into a GradeResult.

    `passed` follows the letter alone (every rubric says A or B = pass); the
    model's own "passed" field is ignored, so a self-contradicting reply
    ({"grade": "C", "passed": true}, or "passed": "false") can't publish.
    "a" or "B+" normalise to their letter; anything else outside A-F, or a
    reply that isn't a JSON object, is an F.
    """
    if not isinstance(result, dict):
        return GradeResult(grade="F", passed=False, feedback="Grader returned a non-object reply.", checks={})
    grade = str(result.get("grade", "F")).strip().upper().rstrip("+-")
    if grade not in GRADE_ORDER:
        grade = "F"
    return GradeResult(
        grade=grade,
        passed=grade in PASSING_GRADES,
        feedback=result.get("feedback", "No feedback provided."),
        checks=result.get("checks", {}),
    )


class Grader(Protocol):
    """Protocol for grader classes used by WriterGraderLoop."""

    async def grade(self, summary_type: str, summary_text: str, context: dict) -> GradeResult: ...
