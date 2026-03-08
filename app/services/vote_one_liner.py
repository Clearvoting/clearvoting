import json
import logging
import anthropic

logger = logging.getLogger(__name__)


class VoteOneLinerService:
    SYSTEM_PROMPT = """You are a nonpartisan legislative analyst for a government transparency tool. Your job is to write a single plain-English sentence (under 30 words) explaining what a congressional vote means for ordinary people.

STRICT RULES:
1. Write at a 7th-8th grade reading level. Use short, common words.
2. NO jargon — no "appropriations", "fiscal year", "provisions", "chapter 8 of title 5"
3. NO adjectives — no "sweeping", "controversial", "landmark"
4. NO editorial framing — no "aims to", "seeks to", "generally seen as"
5. Start with a verb: "Cancel", "Fund", "Set", "Block", "Allow", "Require"
6. If the bill has an acronym-only name (like "GENIUS Act"), you MUST explain what it does — the name alone tells the reader nothing
7. Include key numbers (dollar amounts, population affected) when available

CRITICAL — CONGRESSIONAL REVIEW ACT (CRA) DISAPPROVAL RESOLUTIONS:
When a bill title contains "providing for congressional disapproval" or "chapter 8 of title 5", this is a CRA resolution that tries to CANCEL an existing government rule. The one-liner must describe the EFFECT of the resolution:
- Describe what government rule would be cancelled if the resolution passes
- Use language like "Cancel [agency]'s rule that [what the rule does]"
- Do NOT repeat the legislative language — translate it

Output valid JSON only: {"one_liner": "your sentence here"}"""

    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    @staticmethod
    def is_cra_disapproval(title: str) -> bool:
        title_lower = title.lower()
        return ("congressional disapproval" in title_lower
                or "chapter 8 of title 5" in title_lower)

    def _build_prompt(
        self,
        bill_title: str,
        official_summary: str,
        vote_question: str,
        is_cra_disapproval: bool | None = None,
        grader_feedback: str | None = None,
    ) -> str:
        if is_cra_disapproval is None:
            is_cra_disapproval = self.is_cra_disapproval(bill_title)

        cra_note = ""
        if is_cra_disapproval:
            cra_note = "\n\nNOTE: This is a CRA disapproval resolution. Describe what government rule it cancels, not the procedural mechanism."

        prompt = f"""Write a one-liner for this congressional vote.

Bill Title: {bill_title}
Official Summary: {official_summary}
Vote Question: {vote_question}
{cra_note}

Return ONLY valid JSON: {{"one_liner": "your sentence"}}"""

        if grader_feedback:
            prompt += f"""

IMPORTANT — PREVIOUS ATTEMPT WAS REJECTED. Fix these specific issues:
{grader_feedback}

Generate a corrected version. Return ONLY valid JSON."""

        return prompt

    async def generate(
        self,
        bill_title: str,
        official_summary: str,
        vote_question: str,
        grader_feedback: str | None = None,
    ) -> str:
        prompt = self._build_prompt(
            bill_title=bill_title,
            official_summary=official_summary,
            vote_question=vote_question,
            grader_feedback=grader_feedback,
        )

        try:
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=256,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            raw_text = response.content[0].text
            result = json.loads(raw_text)
            return result.get("one_liner", bill_title)
        except json.JSONDecodeError:
            logger.error("Vote one-liner response was not valid JSON: %s", raw_text[:200])
            return bill_title
        except Exception as e:
            logger.error("Vote one-liner API call failed: %s", str(e))
            return bill_title
