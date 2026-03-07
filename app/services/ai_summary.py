import json
import anthropic
from app.services.cache import CacheService

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
]

SYSTEM_PROMPT = """You are a nonpartisan legislative analyst. Your job is to explain what bills do in everyday English that any American can understand — written at a 7th-8th grade reading level.

STRICT RULES:
1. NO adjectives (no "sweeping", "controversial", "landmark", "modest", etc.)
2. NO value judgments (no "this would help/hurt", "beneficial", "harmful")
3. NO characterization of intent (no "aims to", "seeks to" — just state what the bill does)
4. NO political framing (no "progressive", "conservative", "bipartisan effort")
5. ONLY state mechanisms: what changes, what numbers change, what rules are created or removed
6. Write at a 7th-8th grade reading level. Use short, common words. Say "cuts" not "rescinds", "makes illegal" not "classifies as Schedule I controlled substances", "stops" not "eliminates the provision", "lets" not "authorizes"
7. NO policy jargon or legislative language. Replace terms like "appropriations", "fiscal year", "earmarks", "provisions", "amendments", "authorizes", "mandates", "directs", "enacts" with plain alternatives
8. Include specific numbers, dollar amounts, dates, and thresholds — but explain what they mean
9. Write like you're explaining it to a neighbor, not to a lawyer

Output valid JSON only. No markdown, no commentary."""


class AISummaryService:
    def __init__(self, api_key: str, cache: CacheService):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.cache = cache

    def _build_prompt(self, title: str, official_summary: str, bill_text_excerpt: str) -> str:
        categories_str = ", ".join(IMPACT_CATEGORIES)
        return f"""Analyze this bill and return JSON with two fields:

1. "provisions": An array of 3-7 strings. Each string is one short, everyday-English sentence describing what this bill does. Use words a middle schooler would know. Focus on: dollar amounts, timelines, and what changes for real people. No adjectives. No opinions. No jargon.

2. "impact_categories": An array of strings from this list — Impact Categories: [{categories_str}]. Only include categories that directly apply.

Bill Title: {title}

Official Summary: {official_summary}

Bill Text (excerpt): {bill_text_excerpt}

Return ONLY valid JSON. Example format:
{{"provisions": ["Cuts taxes on tips for workers like servers and bartenders, up to $25,000 a year", "Gives veterans a raise to keep up with the rising cost of living"], "impact_categories": ["Wages & Income"]}}"""

    async def generate_summary(self, bill_id: str, title: str, official_summary: str, bill_text_excerpt: str) -> dict:
        cache_key = f"ai_summary:{bill_id}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        prompt = self._build_prompt(title, official_summary, bill_text_excerpt)

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_text = response.content[0].text
        result = json.loads(raw_text)

        valid_categories = [c for c in result.get("impact_categories", []) if c in IMPACT_CATEGORIES]
        result["impact_categories"] = valid_categories

        self.cache.set(cache_key, result)
        return result
