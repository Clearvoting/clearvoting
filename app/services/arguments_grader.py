import json
import logging
import anthropic
from app.services.grader_common import GradeResult, strip_code_fences

logger = logging.getLogger(__name__)


class ArgumentsGrader:
    def __init__(self, api_key: str | None = None):
        if api_key:
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            self.client = None
        self.learnings: list[str] = []

    async def _call_llm(self, system: str, user_prompt: str) -> str:
        if self.client:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        else:
            from app.services.claude_cli import call_claude_cli
            return await call_claude_cli(system, user_prompt)

    def load_learnings(self, learnings: list[str]) -> None:
        self.learnings = learnings

    def _build_system_prompt(self) -> str:
        learnings_block = ""
        if self.learnings:
            items = "\n".join(f"- {l}" for l in self.learnings)
            learnings_block = f"""

LEARNED PATTERNS (from previous grading runs — pay extra attention to these):
{items}"""

        return f"""You are a nonpartisan quality grader for a government transparency tool called ClearVoting. Your job is to evaluate AI-generated "both sides" arguments about congressional bills.

You grade against this checklist:

ATTRIBUTION
- Every bullet MUST start with "Supporters say" or "Critics say"
- No unattributed claims or assertions

SPECIFICITY
- Arguments must reference specific provisions, dollar amounts, affected groups, or rule changes from the bill
- Generic arguments like "this costs too much" or "this helps families" are NOT acceptable
- Each argument should be traceable to a specific part of the bill

BALANCE
- Both sides must be present (unless bill is purely procedural)
- 2-3 bullets per side
- Neither side should be presented more favorably than the other

NO BIAS OR EDITORIAL LANGUAGE
- No adjectives: "sweeping", "controversial", "landmark"
- No editorial framing: "however", "on the other hand", "despite"
- No value judgments about which side is correct

READING LEVEL
- 7th-8th grade reading level
- No jargon, no legislative language
- Short, clear sentences

STRUCTURE
- Valid JSON with "supporters" and "critics" arrays
- Each array contains 2-3 string items
- Each string is 1-2 sentences max
{learnings_block}

GRADING SCALE:
- A: Passes all checks, excellent balance and specificity
- B: Minor issues (e.g., one slightly generic argument), still balanced and accurate
- C: Moderate issues — missing attribution, generic arguments, or imbalanced
- D: Significant issues — biased framing, missing one side, or factually wrong
- F: Critical failure — editorial language, one-sided, or unreadable

A or B = pass. C, D, or F = fail.

Return valid JSON only:
{{"grade": "A|B|C|D|F", "passed": true|false, "feedback": "Specific actionable feedback for the writer", "checks": {{"attribution": "pass|fail: detail", "specificity": "pass|fail: detail", "balance": "pass|fail: detail", "no_bias": "pass|fail: detail", "reading_level": "pass|fail: detail", "structure": "pass|fail: detail"}}}}"""

    def _build_grade_prompt(self, summary_type: str, summary_text: str, context: dict) -> str:
        context_str = json.dumps(context, indent=2)
        return f"""Grade these {summary_type}.

ORIGINAL CONTEXT (the bill being discussed):
{context_str}

ARGUMENTS TO GRADE:
{summary_text}

Evaluate against every check in your checklist. Be strict — this tool exists to prevent misinformation and bias. Return JSON only."""

    async def grade(self, summary_type: str, summary_text: str, context: dict) -> GradeResult:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_grade_prompt(summary_type, summary_text, context)

        try:
            raw_text = await self._call_llm(system_prompt, user_prompt)
            raw_text = strip_code_fences(raw_text)
            result = json.loads(raw_text)

            return GradeResult(
                grade=result.get("grade", "F"),
                passed=result.get("passed", False),
                feedback=result.get("feedback", "No feedback provided."),
                checks=result.get("checks", {}),
            )
        except json.JSONDecodeError:
            logger.error("Arguments grader response was not valid JSON: %s", raw_text[:200])
            return GradeResult(grade="F", passed=False, feedback="Grader returned invalid JSON.", checks={})
        except Exception as e:
            logger.error("Arguments grader API call failed: %s", str(e))
            return GradeResult(grade="F", passed=False, feedback=f"Grader error: {str(e)}", checks={})
