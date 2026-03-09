import json
import logging
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


MEMBER_SUMMARY_SYSTEM_PROMPT = """You are a nonpartisan legislative analyst. Your job is to summarize a member of Congress's voting record using only observable facts — written at a 7th-8th grade reading level.

STRICT RULES:
1. NO adjectives ("strong advocate", "champion of", "notable", "consistent", "key", "major")
2. NO value judgments ("beneficial", "harmful", "impressive", "disappointing")
3. NO characterization of intent ("cares about", "fights for", "committed to", "seeks to", "aims to")
4. NO political framing ("progressive", "conservative", "moderate", "bipartisan")
5. ONLY describe observable voting patterns — what they voted for, what they voted against, how often they showed up
6. Write at a 7th-8th grade reading level. Use short, common words.
7. Include specific numbers (vote counts, percentages)
8. The narrative MUST be 3-5 sentences. Facts only. No opinions. No framing.
9. top_areas should list 2-5 policy area names the member voted on most, ordered by total votes

Output valid JSON only: {"narrative": "...", "top_areas": ["...", "..."]}
No markdown, no commentary."""


class MemberSummaryService:
    def __init__(self, api_key: str | None):
        if api_key:
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            self.client = None

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

    def _build_prompt(
        self,
        member_name: str,
        chamber: str,
        state: str,
        congresses: list[int],
        stats: dict,
        top_areas: list[dict],
        top_supported: list[str],
        top_opposed: list[str],
        grader_feedback: str | None = None,
    ) -> str:
        congress_str = ", ".join(str(c) for c in congresses)

        areas_lines = []
        for area in top_areas:
            areas_lines.append(
                f"  - {area['name']}: {area['total']} votes "
                f"({area['strengthen']} to strengthen, {area['weaken']} to weaken)"
            )
        areas_block = "\n".join(areas_lines) if areas_lines else "  (no policy area data)"

        supported_block = "\n".join(f"  - {s}" for s in top_supported[:8]) if top_supported else "  (none)"
        opposed_block = "\n".join(f"  - {s}" for s in top_opposed[:6]) if top_opposed else "  (none)"

        prompt = f"""Summarize this member's voting record.

Member: {member_name}
Chamber: {chamber}
State: {state}
Congresses: {congress_str}

Vote Stats:
  Total votes cast: {stats['total_votes']}
  Yea: {stats['yea_count']}
  Nay: {stats['nay_count']}
  Participation rate: {stats['participation_rate']}%

Top Policy Areas (by vote count):
{areas_block}

Bills they voted YES on (sample):
{supported_block}

Bills they voted NO on (sample):
{opposed_block}

Write a 3-5 sentence narrative summarizing this member's voting record. Include specific numbers. Return ONLY valid JSON: {{"narrative": "...", "top_areas": ["...", "..."]}}"""

        if grader_feedback:
            prompt += f"""

IMPORTANT — PREVIOUS ATTEMPT WAS REJECTED. Fix these specific issues:
{grader_feedback}

Generate a corrected version. Return ONLY valid JSON."""

        return prompt

    async def generate_member_summary(
        self,
        member_name: str,
        chamber: str,
        state: str,
        congresses: list[int],
        stats: dict,
        top_areas: list[dict],
        top_supported: list[str],
        top_opposed: list[str],
        grader_feedback: str | None = None,
    ) -> dict:
        prompt = self._build_prompt(
            member_name=member_name,
            chamber=chamber,
            state=state,
            congresses=congresses,
            stats=stats,
            top_areas=top_areas,
            top_supported=top_supported,
            top_opposed=top_opposed,
            grader_feedback=grader_feedback,
        )

        raw_text = await self._call_llm(MEMBER_SUMMARY_SYSTEM_PROMPT, prompt)
        raw_text = _strip_code_fences(raw_text)

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("AI member summary was not valid JSON: %s", raw_text[:200])
            area_names = [a["name"] for a in top_areas[:5]] if top_areas else []
            return {
                "narrative": (
                    f"{member_name} represents {state} in the {chamber}. "
                    f"They cast {stats['total_votes']} votes with a "
                    f"{stats['participation_rate']}% participation rate."
                ),
                "top_areas": area_names,
            }

        if "narrative" not in result or not result["narrative"]:
            result["narrative"] = (
                f"{member_name} represents {state} in the {chamber}."
            )
        if "top_areas" not in result:
            result["top_areas"] = [a["name"] for a in top_areas[:5]] if top_areas else []

        return result
