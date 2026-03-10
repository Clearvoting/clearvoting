import json
import logging
import anthropic
from app.services.grader_common import GradeResult, strip_code_fences

logger = logging.getLogger(__name__)


class MemberNarrativeGrader:
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

        return f"""You are a nonpartisan quality grader for a government transparency tool called ClearVoting. Your job is to evaluate AI-generated narrative summaries of congressional members' voting records for accuracy, clarity, neutrality, and data alignment.

You grade against this checklist:

READING LEVEL
- Must be written at 7th-8th grade reading level
- No sentences over 25 words
- Use common words: "voted for" not "supported legislation", "cuts" not "rescinds"

NO BIAS OR EDITORIAL LANGUAGE
- No adjectives: "strong advocate", "champion", "notable", "consistent", "key", "major"
- No intent characterization: "cares about", "fights for", "committed to", "seeks to", "aims to"
- No political framing: "progressive", "conservative", "moderate", "bipartisan"
- No value judgments: "impressive", "disappointing", "beneficial", "harmful"
- ONLY describe observable voting patterns — what they voted for, what they voted against, how often they showed up

DATA ALIGNMENT (CRITICAL)
- The narrative MUST match the strengthen/weaken ratios provided in the grading context
- If a policy area shows mostly weakening votes, the narrative CANNOT imply the member supports strengthening in that area
- Example: If Environment is 3 strengthen / 12 weaken, the narrative must NOT say the member "voted to protect the environment" or similar
- Check EVERY policy area mentioned in the narrative against the provided data

NO CHERRY-PICKING
- The narrative must NOT highlight exceptions as if they represent the overall pattern
- If a member voted to weaken environmental rules 12 times and strengthen 3 times, the narrative cannot lead with or emphasize the 3 strengthening votes
- The dominant pattern must be presented as the dominant pattern

STRUCTURE
- Must be 3-5 sentences
- Must include specific numbers (vote counts, participation rate)
- Must be factual and descriptive, not interpretive

COMPLETENESS
- Must mention the top 2-3 policy areas by vote count
- Must include participation rate or total vote count
{learnings_block}

GRADING SCALE:
- A: Passes all checks, excellent clarity and accuracy
- B: Minor issues (e.g., one slightly long sentence), still accurate and data-aligned
- C: Moderate issues — data misalignment, cherry-picking, or bias present
- D: Significant issues — narrative contradicts the data, or contains clear bias
- F: Critical failure — completely misrepresents the voting record

A or B = pass. C, D, or F = fail.

Return valid JSON only:
{{"grade": "A|B|C|D|F", "passed": true|false, "feedback": "Specific actionable feedback for the writer", "checks": {{"reading_level": "pass|fail: detail", "no_bias": "pass|fail: detail", "data_alignment": "pass|fail: detail", "no_cherry_picking": "pass|fail: detail", "structure": "pass|fail: detail", "completeness": "pass|fail: detail"}}}}"""

    def _build_grade_prompt(self, summary_type: str, summary_text: str, context: dict) -> str:
        context_str = json.dumps(context, indent=2)
        return f"""Grade this {summary_type}.

MEMBER DATA (ground truth — the narrative must align with this):
{context_str}

NARRATIVE TO GRADE:
{summary_text}

Evaluate against every check in your checklist. Pay special attention to DATA ALIGNMENT — compare every claim in the narrative against the actual strengthen/weaken ratios above. Return JSON only."""

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
            logger.error("Grader response was not valid JSON: %s", raw_text[:200])
            return GradeResult(grade="F", passed=False, feedback="Grader returned invalid JSON.", checks={})
        except Exception as e:
            logger.error("Grader API call failed: %s", str(e))
            return GradeResult(grade="F", passed=False, feedback=f"Grader error: {str(e)}", checks={})
