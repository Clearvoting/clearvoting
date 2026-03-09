import json
import logging
from dataclasses import dataclass, field
import anthropic

logger = logging.getLogger(__name__)


def _strip_code_fences(text: str) -> str:
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


class SummaryGrader:
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

        return f"""You are a nonpartisan quality grader for a government transparency tool called ClearVoting. Your job is to evaluate AI-generated summaries of congressional bills and votes for accuracy, clarity, and neutrality.

You grade against this checklist:

READING LEVEL
- Flesch-Kincaid grade level must be 8th grade or below
- No sentences over 25 words
- Use common words: "cuts" not "rescinds", "stops" not "eliminates the provision", "lets" not "authorizes"

NO JARGON / LEGISLATIVE LANGUAGE
- No "chapter 8 of title 5", "appropriations", "fiscal year", "provisions", "authorizes", "mandates", "eligibility"
- Acronym-only bill names are NOT acceptable. "GENIUS Act" must be expanded and explained. The reader must understand what the bill does from the summary alone.
- Government agency names are OK but must be in short, simple sentences

VOTE CONTEXT ACCURACY (for vote one-liners)
- Congressional Review Act (CRA) disapproval resolutions: voting NAY on a disapproval resolution means the member SUPPORTS the underlying regulation. Voting YEA means they want to REMOVE it. The one-liner must reflect this correctly.
- The one-liner must describe what the vote MEANS for the reader, not just restate the procedural title

NO BIAS OR EDITORIAL LANGUAGE
- No adjectives: "sweeping", "controversial", "landmark", "modest"
- No intent characterization: "aims to", "seeks to"
- No framing: "generally seen as", "made it easier/harder", "widely considered"
- No value judgments: "this would help/hurt", "beneficial", "harmful"

FACTUAL CONTEXT
- When a bill changes a number (fee, cap, limit, threshold), include both old and new values
- When a bill affects a group, include how many people are affected if publicly known
- Include scale references where helpful

DIRECTION ACCURACY
- The "direction" field must be one of: "strengthens", "weakens", "neutral"
- "strengthens" = creates, funds, expands, or tightens rules in the policy area
- "weakens" = cancels, blocks, repeals, defunds, or loosens rules
- Congressional Review Act (CRA) disapproval resolutions that cancel rules = "weakens"
- "neutral" = procedural, unclear, or genuinely mixed

STRUCTURE
- Bill summaries: one_liner (single phrase, max 15 words, starts with verb, no period), provisions (3-7 items, each a single sentence), impact_categories (from allowed list), direction (strengthens/weakens/neutral)
- Vote one-liners: single sentence, under 30 words, describes what the vote means
{learnings_block}

GRADING SCALE:
- A: Passes all checks, excellent clarity and accuracy
- B: Minor issues (e.g., one slightly long sentence), still accurate and readable
- C: Moderate issues — accuracy concerns, jargon present, or misleading framing
- D: Significant issues — misleading, confusing, or factually wrong in places
- F: Critical failure — biased, factually wrong, or completely unreadable

A or B = pass. C, D, or F = fail.

Return valid JSON only:
{{"grade": "A|B|C|D|F", "passed": true|false, "feedback": "Specific actionable feedback for the writer", "checks": {{"reading_level": "pass|fail: detail", "no_jargon": "pass|fail: detail", "no_bias": "pass|fail: detail", "vote_context": "pass|fail|n/a: detail", "factual_context": "pass|fail: detail", "structure": "pass|fail: detail", "direction_accuracy": "pass|fail|n/a: detail"}}}}"""

    def _build_grade_prompt(self, summary_type: str, summary_text: str, context: dict) -> str:
        context_str = json.dumps(context, indent=2)
        return f"""Grade this {summary_type}.

ORIGINAL CONTEXT (what the summary is describing):
{context_str}

SUMMARY TO GRADE:
{summary_text}

Evaluate against every check in your checklist. Be strict — this tool exists to prevent misinformation. Return JSON only."""

    async def grade(self, summary_type: str, summary_text: str, context: dict) -> GradeResult:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_grade_prompt(summary_type, summary_text, context)

        try:
            raw_text = await self._call_llm(system_prompt, user_prompt)
            raw_text = _strip_code_fences(raw_text)
            result = json.loads(raw_text)

            return GradeResult(
                grade=result.get("grade", "F"),
                passed=result.get("passed", False),
                feedback=result.get("feedback", "No feedback provided."),
                checks=result.get("checks", {}),
            )
        except json.JSONDecodeError:
            logger.error("Grader response was not valid JSON: %s", raw_text[:200])
            return GradeResult(grade="F", passed=False, feedback="Grader returned invalid JSON.", checks={})
        except Exception as e:
            logger.error("Grader API call failed: %s", str(e))
            return GradeResult(grade="F", passed=False, feedback=f"Grader error: {str(e)}", checks={})
