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

ISSUE_CATEGORIES = [
    "Cost of Living",
    "Healthcare",
    "Jobs & Workers",
    "Taxes",
    "Safety & Crime",
    "Education",
    "Money in Politics",
    "Housing",
    "Immigration",
    "Environment & Energy",
    "Veterans & Military",
    "Social Security & Retirement",
]

SYSTEM_PROMPT = """You are a nonpartisan legislative analyst. Your job is to explain what bills do in everyday English that any American can understand — written at a 7th-8th grade reading level.

STRICT RULES:
1. NO adjectives (no "sweeping", "controversial", "landmark", "modest", etc.)
2. NO value judgments (no "this would help/hurt", "beneficial", "harmful")
3. NO characterization of intent (no "aims to", "seeks to" — just state what the bill does)
4. NO political framing (no "progressive", "conservative", "bipartisan effort")
5. NO editorial characterizations (no "generally seen as", "made it easier/harder", "widely considered"). State only what the rule does, not how people feel about it.
6. ONLY state mechanisms: what changes, what numbers change, what rules are created or removed
7. Write at a 7th-8th grade reading level. Use short, common words. Say "cuts" not "rescinds", "makes illegal" not "classifies as Schedule I controlled substances", "stops" not "eliminates the provision", "lets" not "authorizes", "non-citizens" not "non-U.S. nationals", "break-ins" not "burglary" or "larceny"
8. NO policy jargon or legislative language. Replace terms like "appropriations", "fiscal year", "earmarks", "provisions", "amendments", "authorizes", "mandates", "directs", "enacts", "nationals", "reclassified", "eligibility" with plain alternatives. Say "the year starting October 2025" not "fiscal year 2026".
9. NO technical jargon without plain explanation. If a concept requires a technical term (like a government agency name), keep the surrounding sentence short and simple. Never stack multiple technical terms in one sentence.
10. Include specific numbers, dollar amounts, dates, and thresholds — but explain what they mean
11. When a bill changes a number (fee, cap, limit, threshold, tax rate), include both the old and new values so the reader can see the difference. When a bill affects a group of people, include how many people are in that group if the number is publicly known. Apply this consistently across all bills — the goal is to give readers enough facts to form their own opinion without needing to research further.
12. Write like you're explaining it to a neighbor, not to a lawyer
13. When a bill repeals, cancels, or overturns a previous rule, describe the RESULT — not the chain of actions. Instead of 'Cancel a rule that ended automatic approvals for bank mergers', say 'Bring back automatic approvals for some bank mergers'. Avoid stacking negatives. The reader should immediately understand what changes.

ACCURACY RULES (these protect against the most damaging errors — follow them as strictly as the style rules above):
14. MATCH THE SCOPE EXACTLY. If a bill blocks, affects, or changes ONE specific thing — a single arms sale, one rule, one agency, one program — say exactly that. Do NOT inflate it into a blanket or sweeping action. Write "Block one proposed sale of bombs to Israel", never "Stop selling weapons to Israel". A narrow action described as a broad one is a factual error.
15. NAME THE BILL'S SPECIFIC SUBJECT. Lead with the actual thing the bill is about — the commodity, agency, country, rule, or program — taken from the title and text. Do not swap a specific subject for a generic category. Say "critical minerals and rare earth elements", not "energy resources"; say "the CPSC", not "federal regulators", when the text names one.
16. USE ONLY WHAT IS IN THE SOURCE. Build the summary only from the title, official summary, and bill text provided. Do NOT add country names, counts, dollar figures, dates, or other specifics from your own knowledge — they may be wrong or may change over time. If the source does not say it, do not state it.
17. SUMMARIZE THE OPERATIVE VERSION. The official summary often describes an EARLIER version (as introduced, or as passed by one chamber). If the bill became law or was amended, describe what the FINAL text does — provisions are frequently stripped or changed before passage. If you cannot confirm a provision survived into the operative version, do not assert it. (Example failure: a continuing resolution's debt-limit suspension was removed by the Senate before enactment, yet the introduced-version summary still listed it.)
18. VARY YOUR SENTENCE OPENINGS. Do not start multiple provision bullets with the same word or phrase (e.g., three bullets all beginning "Removes updated..."). Rephrase so the list reads naturally.

Output valid JSON only. No markdown, no commentary."""


class AISummaryService:
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
                max_tokens=1536,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        else:
            from app.services.claude_cli import call_claude_cli
            return await call_claude_cli(system, user_prompt)

    def _build_prompt(self, title: str, official_summary: str, bill_text_excerpt: str, grader_feedback: str | None = None, policy_area: str | None = None, latest_action: str | None = None) -> str:
        categories_str = ", ".join(ISSUE_CATEGORIES)
        policy_area_line = f'\nPolicy Area (from Congress.gov): {policy_area}' if policy_area else ''
        # Tells the writer which version it is reading (accuracy rule 17): a
        # "Became Public Law" status paired with an introduced-era summary is
        # the wrong-version trap.
        latest_action_line = f'\nLatest Action (bill status): {latest_action}' if latest_action else ''
        prompt = f"""Analyze this bill and return JSON with four fields:

1. "one_liner": A single plain-English phrase (max 15 words) starting with a verb that says what this bill does. No period. No adjectives. Examples: "Cancel an EPA rule limiting methane fees on oil and gas companies", "Fund the military and set troop pay for 2026".

2. "provisions": An array of 3-7 strings. Each string is one short, everyday-English sentence describing what this bill does. Use words a middle schooler would know. Focus on: dollar amounts, timelines, and what changes for real people. No adjectives. No opinions. No jargon.

3. "issue_categories": An array of 1-2 strings from this list — Issue Categories: [{categories_str}]. Pick the 1-2 categories that best describe what this bill is about from the perspective of an everyday voter. Only include categories that directly apply.

4. "direction": One of "in_favor", "against", or "neutral". Does this bill create, fund, expand, or tighten rules within its issue area ("in_favor"), or cancel, block, repeal, defund, or loosen them ("against")? Use "neutral" if unclear or procedural. Example: A Congressional Review Act (CRA) disapproval resolution that cancels an EPA rule = "against" Environment & Energy.

Bill Title: {title}

Official Summary: {official_summary}

Bill Text (excerpt): {bill_text_excerpt}{policy_area_line}{latest_action_line}

Return ONLY valid JSON. Example format:
{{"one_liner": "Raise the federal minimum wage to $15 per hour", "provisions": ["Raises the minimum wage from $7.25 to $15.00 per hour over 5 years", "Gives veterans a raise to keep up with the rising cost of living"], "issue_categories": ["Jobs & Workers"], "direction": "in_favor"}}"""

        if grader_feedback:
            prompt += f"""

IMPORTANT — PREVIOUS ATTEMPT WAS REJECTED. Fix these specific issues:
{grader_feedback}

Generate a corrected version. Return ONLY valid JSON."""

        return prompt

    async def generate_summary(self, bill_id: str, title: str, official_summary: str, bill_text_excerpt: str, grader_feedback: str | None = None, policy_area: str | None = None, latest_action: str | None = None) -> dict:
        # Skip cache when grader_feedback is present (this is a retry)
        if not grader_feedback:
            cache_key = f"ai_summary:{bill_id}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        prompt = self._build_prompt(title, official_summary, bill_text_excerpt, grader_feedback=grader_feedback, policy_area=policy_area, latest_action=latest_action)

        result = None
        for attempt in range(2):
            raw_text = _strip_code_fences(await self._call_llm(SYSTEM_PROMPT, prompt))
            try:
                result = json.loads(raw_text)
                break
            except json.JSONDecodeError:
                logger.warning("AI response was not valid JSON (attempt %d): %s", attempt + 1, raw_text[:200])
        if result is None:
            # Never cache, never persist, never surface the raw official title
            # — titles can carry partisan framing straight onto the page.
            return {"provisions": ["AI summary temporarily unavailable"], "issue_categories": [],
                    "one_liner": "", "direction": "neutral", "generation_failed": True}

        valid_categories = [c for c in result.get("issue_categories", []) if c in ISSUE_CATEGORIES]
        result["issue_categories"] = valid_categories

        valid_directions = ["in_favor", "against", "neutral"]
        if result.get("direction") not in valid_directions:
            result["direction"] = "neutral"

        if "one_liner" not in result or not result["one_liner"]:
            result["one_liner"] = result["provisions"][0] if result.get("provisions") else ""

        # Only cache final results (no grader_feedback = final or first pass)
        if not grader_feedback:
            self.cache.set(cache_key, result)

        return result
