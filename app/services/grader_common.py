"""Shared types and utilities for grader services."""

import json
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


def parse_llm_json(text: str) -> dict:
    """Parse the JSON object in an LLM response.

    The `claude -p` path wraps otherwise-valid objects in junk at the edges:
    code fences, prose before the object (user-level output-style hooks leak
    into CLI calls), a stray quote after it (`...'."}}"`), or a dropped final
    brace (`...'."}`). Decode from the first "{" and ignore anything after
    the object; if the text ends right after a nested object closes, add the
    one missing brace. A response cut off anywhere else still raises
    json.JSONDecodeError — never guess at a truncated grade.
    """
    text = strip_code_fences(text)
    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("No JSON object found", text, 0)
    text = text[start:]
    decoder = json.JSONDecoder()
    try:
        return decoder.raw_decode(text)[0]
    except json.JSONDecodeError as e:
        if e.pos != len(text) or not text.endswith("}"):
            raise
        return decoder.raw_decode(text + "}")[0]


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
