import json
import logging
import anthropic
from app.services.grader_common import CLAUDE_MODEL
from app.services.cache import CacheService

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


SYSTEM_PROMPT = """You are a nonpartisan legislative analyst. Your job is to present what real people and groups are saying for and against a bill — written at a 7th-8th grade reading level.

STRICT RULES:
1. Every bullet MUST be attributed: start with "Supporters say..." or "Critics say..."
2. Arguments must reference SPECIFIC provisions, numbers, or affected groups from the bill — no generic claims like "this costs too much" or "this helps people"
3. NO adjectives (no "sweeping", "controversial", "landmark")
4. NO value judgments — present each side's argument as they state it
5. NO editorial framing (no "however", "on the other hand", "despite")
6. Write at a 7th-8th grade reading level. Use short, common words
7. 2-3 bullets per side. Each bullet is 1-2 sentences max
8. Ground arguments in facts: dollar amounts, number of people affected, specific rules that change
9. Both sides must be present — never omit one side
10. If the bill is purely procedural (naming a post office, setting a meeting date), return empty arrays for both sides

Output valid JSON only. No markdown, no commentary."""


class BillArgumentsService:
    def __init__(self, api_key: str | None, cache: CacheService):
        self.cache = cache
        if api_key:
            self.client = anthropic.AsyncAnthropic(api_key=api_key)
        else:
            self.client = None

    async def _call_llm(self, system: str, user_prompt: str) -> str:
        if self.client:
            response = await self.client.messages.create(
                model=CLAUDE_MODEL,
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
        title: str,
        official_summary: str,
        provisions: list[str],
        grader_feedback: str | None = None,
    ) -> str:
        provisions_text = "\n".join(f"- {p}" for p in provisions) if provisions else "No AI provisions available."

        prompt = f"""Generate the arguments for and against this bill.

Bill Title: {title}

Official Summary: {official_summary}

AI-Generated Provisions (reference these facts in your arguments):
{provisions_text}

Return ONLY valid JSON with this format:
{{"supporters": ["Supporters say this would...", "Supporters say..."], "critics": ["Critics say the $X cost...", "Critics say..."]}}

Rules:
- Every bullet starts with "Supporters say" or "Critics say"
- Reference specific provisions, numbers, or groups from above
- 2-3 bullets per side
- If this is purely procedural, return {{"supporters": [], "critics": []}}"""

        if grader_feedback:
            prompt += f"""

IMPORTANT — PREVIOUS ATTEMPT WAS REJECTED. Fix these specific issues:
{grader_feedback}

Generate a corrected version. Return ONLY valid JSON."""

        return prompt

    async def generate_arguments(
        self,
        bill_id: str,
        title: str,
        official_summary: str,
        provisions: list[str],
        grader_feedback: str | None = None,
    ) -> dict:
        if not grader_feedback:
            cache_key = f"bill_arguments:{bill_id}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        prompt = self._build_prompt(title, official_summary, provisions, grader_feedback=grader_feedback)

        raw_text = await self._call_llm(SYSTEM_PROMPT, prompt)
        raw_text = _strip_code_fences(raw_text)
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("AI arguments response was not valid JSON: %s", raw_text[:200])
            return {"supporters": [], "critics": []}

        # Validate structure
        if not isinstance(result.get("supporters"), list):
            result["supporters"] = []
        if not isinstance(result.get("critics"), list):
            result["critics"] = []

        if not grader_feedback:
            self.cache.set(cache_key, result)

        return result
