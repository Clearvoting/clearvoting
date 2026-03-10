"""Shared types and utilities for grader services."""

from dataclasses import dataclass, field
from typing import Protocol


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


@dataclass
class GradeResult:
    grade: str
    passed: bool
    feedback: str
    checks: dict = field(default_factory=dict)


class Grader(Protocol):
    """Protocol for grader classes used by WriterGraderLoop."""

    async def grade(self, summary_type: str, summary_text: str, context: dict) -> GradeResult: ...
