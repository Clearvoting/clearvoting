import json
import logging
import anthropic
from app.services.cache import CacheService

logger = logging.getLogger(__name__)

IMPACT_CATEGORIES = [
    "Wages & Income",
    "Healthcare",
    "Small Business",
    "Housing",
    "Education",
    "Taxes",
    "Military & Veterans",
    "Agriculture",
    "Environment",
    "Immigration",
    "Criminal Justice",
    "Technology",
    "Infrastructure",
    "Social Security & Medicare",
    "Government Operations",
    "Energy",
    "Foreign Affairs",
    "Civil Rights",
    "Economy",
    "Defense",
    "Labor",
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

Output valid JSON only. No markdown, no commentary."""


class AISummaryService:
    def __init__(self, api_key: str, cache: CacheService):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.cache = cache

    def _build_prompt(self, title: str, official_summary: str, bill_text_excerpt: str, grader_feedback: str | None = None) -> str:
        categories_str = ", ".join(IMPACT_CATEGORIES)
        prompt = f"""Analyze this bill and return JSON with three fields:

1. "one_liner": A single plain-English phrase (max 15 words) starting with a verb that says what this bill does. No period. No adjectives. Examples: "Cancel an EPA rule limiting methane fees on oil and gas companies", "Fund the military and set troop pay for 2026".

2. "provisions": An array of 3-7 strings. Each string is one short, everyday-English sentence describing what this bill does. Use words a middle schooler would know. Focus on: dollar amounts, timelines, and what changes for real people. No adjectives. No opinions. No jargon.

3. "impact_categories": An array of strings from this list — Impact Categories: [{categories_str}]. Only include categories that directly apply.

Bill Title: {title}

Official Summary: {official_summary}

Bill Text (excerpt): {bill_text_excerpt}

Return ONLY valid JSON. Example format:
{{"one_liner": "Raise the federal minimum wage to $15 per hour", "provisions": ["Raises the minimum wage from $7.25 to $15.00 per hour over 5 years", "Gives veterans a raise to keep up with the rising cost of living"], "impact_categories": ["Wages & Income"]}}"""

        if grader_feedback:
            prompt += f"""

IMPORTANT — PREVIOUS ATTEMPT WAS REJECTED. Fix these specific issues:
{grader_feedback}

Generate a corrected version. Return ONLY valid JSON."""

        return prompt

    async def generate_summary(self, bill_id: str, title: str, official_summary: str, bill_text_excerpt: str, grader_feedback: str | None = None) -> dict:
        # Skip cache when grader_feedback is present (this is a retry)
        if not grader_feedback:
            cache_key = f"ai_summary:{bill_id}"
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        prompt = self._build_prompt(title, official_summary, bill_text_excerpt, grader_feedback=grader_feedback)

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = response.content[0].text
        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("AI response was not valid JSON: %s", raw_text[:200])
            return {"provisions": ["AI summary temporarily unavailable"], "impact_categories": [], "one_liner": title}

        valid_categories = [c for c in result.get("impact_categories", []) if c in IMPACT_CATEGORIES]
        result["impact_categories"] = valid_categories

        if "one_liner" not in result or not result["one_liner"]:
            result["one_liner"] = result["provisions"][0] if result.get("provisions") else title

        # Only cache final results (no grader_feedback = final or first pass)
        if not grader_feedback:
            self.cache.set(cache_key, result)

        return result
