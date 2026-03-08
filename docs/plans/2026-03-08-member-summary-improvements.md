# Member Profile Summary Improvements — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix three issues with the member profile "At a Glance" section: misleading "most active on" text, duplicate bill names in supported/opposed lists, and incomprehensible raw bill titles used as one_liners.

**Architecture:** Add a `one_liner` field to AI summary output, use it in sync instead of raw Congress.gov titles, and fix frontend deduplication logic. Three layers touched: AI prompt, sync script, frontend JS.

**Tech Stack:** Python/FastAPI, vanilla JS, Claude API (for AI summary regeneration)

---

### Task 1: Add `one_liner` to AI Summary Prompt

**Files:**
- Modify: `app/services/ai_summary.py:56-71` (prompt) and `app/services/ai_summary.py:88-98` (parsing)
- Test: `tests/test_ai_summary.py`

**Step 1: Write the failing test**

Add to `tests/test_ai_summary.py`:

```python
def test_build_prompt_requests_one_liner():
    service = AISummaryService(api_key="test", cache=MagicMock())
    prompt = service._build_prompt(
        title="Test Bill",
        official_summary="A bill to do things.",
        bill_text_excerpt="Section 1."
    )
    assert "one_liner" in prompt


@pytest.mark.asyncio
async def test_generate_summary_includes_one_liner():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"provisions": ["Raises the minimum wage to $15"], "impact_categories": ["Wages & Income"], "one_liner": "Raise the federal minimum wage to $15 per hour"}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hr-1234",
            title="Minimum Wage Act",
            official_summary="A bill to raise the minimum wage.",
            bill_text_excerpt="The minimum wage shall be $15."
        )

    assert "one_liner" in result
    assert result["one_liner"] == "Raise the federal minimum wage to $15 per hour"


@pytest.mark.asyncio
async def test_generate_summary_fallback_when_no_one_liner():
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    service = AISummaryService(api_key="test", cache=mock_cache)

    mock_response = MagicMock()
    mock_response.content = [MagicMock(
        text='{"provisions": ["Does something"], "impact_categories": ["Taxes"]}'
    )]

    with patch.object(service, "client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        result = await service.generate_summary(
            bill_id="119-hr-999",
            title="Some Act",
            official_summary="Does things.",
            bill_text_excerpt="Text."
        )

    assert "one_liner" in result
    assert result["one_liner"] == "Does something"
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest tests/test_ai_summary.py -v`
Expected: 3 new tests FAIL

**Step 3: Update the prompt and parsing**

In `app/services/ai_summary.py`, update `_build_prompt` to request three fields:

```python
def _build_prompt(self, title: str, official_summary: str, bill_text_excerpt: str) -> str:
    categories_str = ", ".join(IMPACT_CATEGORIES)
    return f"""Analyze this bill and return JSON with three fields:

1. "one_liner": A single plain-English phrase (max 15 words) starting with a verb that says what this bill does. No period. No adjectives. Examples: "Cancel an EPA rule limiting methane fees on oil and gas companies", "Fund the military and set troop pay for 2026".

2. "provisions": An array of 3-7 strings. Each string is one short, everyday-English sentence describing what this bill does. Use words a middle schooler would know. Focus on: dollar amounts, timelines, and what changes for real people. No adjectives. No opinions. No jargon.

3. "impact_categories": An array of strings from this list — Impact Categories: [{categories_str}]. Only include categories that directly apply.

Bill Title: {title}

Official Summary: {official_summary}

Bill Text (excerpt): {bill_text_excerpt}

Return ONLY valid JSON. Example format:
{{"one_liner": "Raise the federal minimum wage to $15 per hour", "provisions": ["Raises the minimum wage from $7.25 to $15.00 per hour over 5 years", "Gives veterans a raise to keep up with the rising cost of living"], "impact_categories": ["Wages & Income"]}}"""
```

In `generate_summary`, add fallback if `one_liner` is missing from AI response:

```python
# After the existing impact_categories filtering:
if "one_liner" not in result or not result["one_liner"]:
    result["one_liner"] = result["provisions"][0] if result.get("provisions") else title
```

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && pytest tests/test_ai_summary.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add app/services/ai_summary.py tests/test_ai_summary.py
git commit -m "feat: add one_liner field to AI summary prompt and parsing"
```

---

### Task 2: Use AI `one_liner` in Sync Script

**Files:**
- Modify: `sync.py:271-406` (`build_member_votes` function)
- Test: `tests/test_sync.py`

**Step 1: Write the failing test**

Add to `tests/test_sync.py`:

```python
@pytest.mark.asyncio
async def test_build_member_votes_uses_ai_one_liner(tmp_path):
    """When AI summary has a one_liner, use it instead of raw bill title."""
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "stateCode": "FL", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Providing for congressional disapproval under chapter 8 of title 5",
         "policyArea": {"name": "Taxation"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    # AI summary with a good one_liner
    ai_summaries = {
        "119-hr-1": {
            "one_liner": "Cancel a tax rule on crypto trading platforms",
            "provisions": ["This cancels a rule..."],
            "impact_categories": ["Taxation"],
        }
    }
    _write_json(tmp_path / "ai_summaries.json", ai_summaries)

    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
        ],
    })

    count = await build_member_votes(tmp_path)

    data = json.loads((tmp_path / "member_votes" / "S001217.json").read_text())
    assert data["votes"][0]["one_liner"] == "Cancel a tax rule on crypto trading platforms"


@pytest.mark.asyncio
async def test_build_member_votes_falls_back_to_title(tmp_path):
    """When no AI summary exists, fall back to raw bill title."""
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "stateCode": "FL", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "1", "title": "Some Raw Title",
         "policyArea": {"name": "Taxation"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    # No ai_summaries.json file at all
    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
        ],
    })

    count = await build_member_votes(tmp_path)

    data = json.loads((tmp_path / "member_votes" / "S001217.json").read_text())
    assert data["votes"][0]["one_liner"] == "Some Raw Title"
```

**Step 2: Run tests to verify they fail**

Run: `source .venv/bin/activate && pytest tests/test_sync.py::test_build_member_votes_uses_ai_one_liner tests/test_sync.py::test_build_member_votes_falls_back_to_title -v`
Expected: Both FAIL

**Step 3: Update `build_member_votes` in `sync.py`**

At the top of `build_member_votes` (around line 286, after loading `bill_lookup`), load AI summaries:

```python
# Load AI summaries for one_liner lookup
ai_summaries: dict[str, dict] = {}
ai_summaries_path = output_dir / "ai_summaries.json"
if ai_summaries_path.exists():
    with open(ai_summaries_path) as f:
        ai_summaries = json.load(f)
```

Then add a helper function to resolve the one_liner (before the member loop):

```python
def _get_one_liner(bill_ref: str | None, bill_info: dict, doc: str) -> str:
    if bill_ref:
        summary_key = f"119-{bill_ref}"
        ai_summary = ai_summaries.get(summary_key, {})
        if ai_summary.get("one_liner"):
            return ai_summary["one_liner"]
    return bill_info.get("title", doc)
```

Replace both occurrences of `"one_liner": bill_info.get("title", doc)` (lines 343 and 370) with:

```python
"one_liner": _get_one_liner(bill_ref, bill_info, doc),
```

**Step 4: Run tests to verify they pass**

Run: `source .venv/bin/activate && pytest tests/test_sync.py -v`
Expected: All tests PASS (including existing ones — the fallback behavior is unchanged when no AI summaries exist)

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: use AI one_liner in member vote records instead of raw titles"
```

---

### Task 3: Fix Frontend "At a Glance" Section

**Files:**
- Modify: `static/js/member.js:273-355` (`renderVotingSummary` function)

**Step 1: Fix "Most active on" wording**

In `renderVotingSummary` (line 304), change:

```js
`Most active on ${topAreas.slice(0, 3).map(a => a[0].toLowerCase()).join(', ')}.`
```

to:

```js
`Most votes in ${topAreas.slice(0, 3).map(a => a[0].toLowerCase()).join(', ')}.`
```

**Step 2: Deduplicate supported/opposed lists by final vote**

Replace the block at lines 294-352 (from `// Separate yea and nay votes` through the end of the against section) with logic that:

1. Groups all votes by `bill_id` (falling back to `one_liner` for non-bill votes like nominations)
2. For each bill, keeps only the last vote chronologically (votes are already sorted newest-first, so take the first occurrence per bill)
3. Puts the bill in "supported" or "opposed" based on that final vote
4. Shows each bill's `one_liner` once

```js
// Deduplicate votes by bill — keep final (most recent) vote per bill
const seenBills = new Set();
const uniqueYea = [];
const uniqueNay = [];
votes.forEach(v => {
    const key = v.bill_id || v.one_liner;
    if (!key || seenBills.has(key)) return;
    seenBills.add(key);
    if (v.vote === 'Yea') uniqueYea.push(v);
    else if (v.vote === 'Nay') uniqueNay.push(v);
});
```

Then use `uniqueYea` and `uniqueNay` instead of `yeaVotes` and `nayVotes` for the "What They Supported" / "What They Opposed" sections.

**Step 3: Verify manually**

Run: `source .venv/bin/activate && python -m uvicorn app.main:app --reload`
Navigate to a member profile and check:
- "Most votes in" text instead of "Most active on"
- No duplicate bill titles in supported/opposed
- GENIUS Act appears in only one list

**Step 4: Commit**

```bash
git add static/js/member.js
git commit -m "fix: deduplicate vote lists and fix misleading 'most active' text"
```

---

### Task 4: Regenerate AI Summaries and Rebuild Member Votes

**Files:**
- Modify: `data/synced/ai_summaries.json` (regenerated)
- Modify: `data/synced/member_votes/*.json` (rebuilt)

**Step 1: Check API key**

```bash
grep ANTHROPIC_API_KEY .env
```

If placeholder, Joseph needs to set a real key before regeneration.

**Step 2: Regenerate AI summaries**

This requires adding a `--summaries-only` flag to sync.py, OR running a one-off script. The simplest approach: write a small script that reads existing `bills.json`, calls the AI for each bill, and writes `ai_summaries.json`.

Alternatively, if the ANTHROPIC_API_KEY is not available, we can generate one_liners locally by extracting the key phrase from `provisions[0]` for each existing summary. This is a viable fallback that doesn't require API calls.

**Step 3: Rebuild member votes**

After AI summaries have `one_liner` fields, run `build_member_votes` to rebuild all member vote records:

```bash
python -c "
import asyncio, json
from pathlib import Path
from sync import build_member_votes
asyncio.run(build_member_votes(Path('data/synced')))
"
```

**Step 4: Spot-check results**

```bash
python -c "
import json
with open('data/synced/member_votes/G000555.json') as f:
    data = json.load(f)
for v in data['votes'][:5]:
    print(v['one_liner'][:80])
"
```

Verify: No "chapter 8 of title 5" text. All one_liners are plain English.

**Step 5: Commit**

```bash
git add data/synced/ai_summaries.json data/synced/member_votes/
git commit -m "data: regenerate AI summaries with one_liner, rebuild member votes"
```

---

### Task 5: Run Full Test Suite

**Step 1: Run all tests**

```bash
source .venv/bin/activate && pytest -v
```

Expected: All 100+ tests pass (including new ones from Tasks 1-2).

**Step 2: Fix any failures, commit fixes**

If any tests fail, fix and commit.
