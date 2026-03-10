import json
import logging
from dataclasses import dataclass, field
import anthropic
from app.services.grader_common import strip_code_fences

logger = logging.getLogger(__name__)


@dataclass
class CoherenceResult:
    is_coherent: bool
    contradictions: list[str] = field(default_factory=list)
    guidance: str = ""


COHERENCE_SYSTEM_PROMPT = """You are a consistency checker for a government transparency tool called ClearVoting. Your job is to check whether the different sections of a member's profile page tell a consistent story.

A member's profile page has these sections:
1. NARRATIVE SUMMARY — a 3-5 sentence AI-generated description of the member's voting record
2. OVERVIEW STATS — total votes, yea/nay counts, participation rate
3. WHERE THEY FOCUS — policy areas with strengthen/weaken direction bars showing vote counts
4. WHAT THEY SUPPORTED — list of bills the member voted YES on
5. WHAT THEY OPPOSED — list of bills the member voted NO on

Your task: compare the NARRATIVE against sections 2-5. Identify any contradictions where the narrative says something that conflicts with the actual data.

Examples of contradictions:
- Narrative says "voted to strengthen environmental rules" but direction data shows mostly weakening on environment
- Narrative emphasizes healthcare but the top policy areas show it's a minor area
- Narrative says "voted on 500 bills" but stats show 200 total votes
- Narrative says member supported a bill that appears in their "opposed" list

Return valid JSON only:
{"is_coherent": true|false, "contradictions": ["specific contradiction 1", "..."], "guidance": "Instructions for fixing the narrative if not coherent, empty string if coherent"}"""


class PageCoherenceChecker:
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
        if self.learnings:
            items = "\n".join(f"- {l}" for l in self.learnings)
            return COHERENCE_SYSTEM_PROMPT + f"""

LEARNED PATTERNS (from previous coherence checks — pay extra attention):
{items}"""
        return COHERENCE_SYSTEM_PROMPT

    async def check(
        self,
        narrative: str,
        stats: dict,
        top_areas: list[dict],
        top_supported: list[str],
        top_opposed: list[str],
    ) -> CoherenceResult:
        page_data = {
            "narrative_summary": narrative,
            "overview_stats": stats,
            "where_they_focus": top_areas,
            "what_they_supported": top_supported[:8],
            "what_they_opposed": top_opposed[:6],
        }

        user_prompt = f"""Check this member profile page for consistency.

PAGE DATA:
{json.dumps(page_data, indent=2)}

Compare the narrative against the data sections. Are there contradictions? Return JSON only."""

        try:
            raw_text = await self._call_llm(self._build_system_prompt(), user_prompt)
            raw_text = strip_code_fences(raw_text)
            result = json.loads(raw_text)

            return CoherenceResult(
                is_coherent=result.get("is_coherent", False),
                contradictions=result.get("contradictions", []),
                guidance=result.get("guidance", ""),
            )
        except json.JSONDecodeError:
            logger.error("Coherence checker returned invalid JSON: %s", raw_text[:200])
            return CoherenceResult(
                is_coherent=False,
                contradictions=["Coherence checker returned invalid response"],
                guidance="Re-run coherence check",
            )
        except Exception as e:
            logger.error("Coherence checker failed: %s", str(e))
            return CoherenceResult(
                is_coherent=True,
                contradictions=[],
                guidance="",
            )
