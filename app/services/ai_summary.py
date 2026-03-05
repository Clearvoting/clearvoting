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

SYSTEM_PROMPT = """You are a nonpartisan legislative analyst. Your job is to extract factual information from bills and present it in plain language that any working American can understand.

STRICT RULES:
1. NO adjectives (no "sweeping", "controversial", "landmark", "modest", etc.)
2. NO value judgments (no "this would help/hurt", "beneficial", "harmful")
3. NO characterization of intent (no "aims to", "seeks to" — just state what the bill does)
4. NO political framing (no "progressive", "conservative", "bipartisan effort")
5. ONLY state mechanisms: what changes, what numbers change, what rules are created or removed
6. Use plain language a high school graduate would understand
7. Include specific numbers, dollar amounts, dates, and thresholds from the bill text

Output valid JSON only. No markdown, no commentary."""


class AISummaryService:
    def __init__(self, api_key: str, cache: CacheService):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.cache = cache

    def _build_prompt(self, title: str, official_summary: str, bill_text_excerpt: str) -> str:
        categories_str = ", ".join(IMPACT_CATEGORIES)
        return f"""Analyze this bill and return JSON with two fields:

1. "provisions": An array of 3-7 strings. Each string is one plain-language sentence describing what this bill would do. Focus on mechanisms: dollar amounts, thresholds, timelines, rules created or removed. No adjectives. No opinions.

2. "impact_categories": An array of strings from this list — Impact Categories: [{categories_str}]. Only include categories that directly apply.

Bill Title: {title}

Official Summary: {official_summary}

Bill Text (excerpt): {bill_text_excerpt}

Return ONLY valid JSON. Example format:
{{"provisions": ["Changes X from $Y to $Z", "Creates a new program that does X"], "impact_categories": ["Wages & Income"]}}"""

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
