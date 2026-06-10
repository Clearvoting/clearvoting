# Multi-Congress Sync + AI Member Summaries Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expand ClearVote's sync pipeline to pull 3 congresses (117th-119th, ~5 years) and generate AI narrative summaries per member using Sonnet.

**Architecture:** The sync pipeline loops over configurable congress/session pairs for vote fetching, aggregates votes across congresses into per-member files, then generates narrative summaries via the existing writer-grader loop. Frontend displays the narrative at the top of the "At a Glance" card.

**Tech Stack:** Python/FastAPI, Anthropic SDK (Sonnet), vanilla JS frontend

**References:**
- [Design doc](2026-03-09-multi-congress-member-summaries-design.md)

---

## Overview

**Current behavior:**
- Sync pipeline fetches only 119th Congress, Session 1 (`sync.py:82`, `sync.py:132`)
- Member vote files hardcode `congress: 119` (`sync.py:556`)
- Bill ID keys hardcode `119-` prefix (`sync.py:447-448`, `sync.py:453-454`, `sync.py:506-507`)
- No AI member summaries exist — only bill summaries

**New behavior:**
- Sync loops over 117th, 118th, and 119th Congress (both sessions each)
- Member vote files aggregate across all congresses, each vote tagged with its congress
- AI-generated 3-5 sentence narrative summary per member, stored in `member_summaries.json`
- Frontend displays narrative at top of "At a Glance" card

---

## Design Decisions

**Configurable congress list at top of sync.py.** A single constant `CONGRESSES` makes it a one-line change to add older congresses later. Each entry is a `(congress, session)` tuple.

**Congress parsed from vote data, not filenames.** Vote JSON already includes a `congress` field. Using this is more robust than parsing filenames.

**Member summary as separate file, not embedded in member_votes.** Keeps the concerns separated — vote data is raw facts, summaries are AI-generated. Different cache/regeneration lifecycles.

**Grader reused for member summaries via `summary_type="member_summary"`.** The grader already accepts arbitrary summary types. We add member-specific checks to the grading prompt.

---

## Phase 1: Multi-Congress Vote Sync

**Completion gate:** Senate and House votes sync across 117/118/119 congresses. Existing 119 data is skipped (incremental). Tests pass.

### Task 1: Add CONGRESSES constant and update main()

**Files:**
- Modify: `sync.py:36-43` (add constant after US_STATES)
- Modify: `sync.py:944-953` (loop over congresses in main)

**Step 1: Add the CONGRESSES constant**

Add after `US_STATES` (line 43):

```python
# Congress/session pairs to sync — add older congresses to expand history
# Each congress has 2 sessions (odd year = session 1, even year = session 2)
CONGRESSES = [
    (117, 1), (117, 2),
    (118, 1), (118, 2),
    (119, 1), (119, 2),
]
```

**Step 2: Update main() vote sync loops**

Replace the single Senate vote sync call (lines 944-947):

```python
# Step 2: Senate votes (all congresses)
print()
senate_service = SenateVoteService(cache=cache)
print("[2/9] Syncing Senate votes...")
senate_count = 0
for congress, session in CONGRESSES:
    print(f"  Congress {congress}, Session {session}...")
    count = await sync_senate_votes(senate_service, SYNC_DIR, congress=congress, session=session, rate_limit=0.3)
    senate_count += count
```

Replace the single House vote sync call (lines 950-951):

```python
# Step 3: House votes (all congresses)
print()
print("[3/9] Syncing House votes...")
house_count = 0
for congress, session in CONGRESSES:
    print(f"  Congress {congress}, Session {session}...")
    count = await sync_house_votes(client, SYNC_DIR, congress=congress, session=session, rate_limit=0.3)
    house_count += count
```

**Step 3: Update step numbers in main()**

Renumber steps from 7 to 9 (adding member summaries + grading steps later). Update all `[N/7]` labels to `[N/9]`.

**Step 4: Run existing tests to verify no regressions**

Run: `cd ~/Documents/Claude/Projects/clearvote && source .venv/bin/activate && pytest tests/test_sync.py -v`
Expected: All existing tests pass (they use explicit congress params, unaffected by constant)

**Step 5: Commit**

```bash
git add sync.py
git commit -m "feat: add multi-congress sync support (117, 118, 119)"
```

---

## Phase 2: Multi-Congress Bill Sync

**Completion gate:** `sync_bills_from_votes` fetches bills from correct congress. Bill refs tracked as `(congress, ref)` tuples. Tests pass.

### Task 2: Update sync_bills_from_votes for multi-congress

**Files:**
- Modify: `sync.py:207-269` (sync_bills_from_votes)
- Test: `tests/test_sync.py`

**Step 1: Write test for multi-congress bill sync**

Add to `tests/test_sync.py`:

```python
@pytest.mark.asyncio
async def test_sync_bills_from_votes_multi_congress(tmp_path):
    """Bills from different congresses are fetched with correct congress number."""
    senate_dir = tmp_path / "votes" / "senate"
    senate_dir.mkdir(parents=True)
    _write_json(senate_dir / "117_1_00001.json", {
        "congress": 117, "session": 1, "vote_number": 1,
        "document": "H.R. 1", "vote_date": "2021-03-03",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [],
    })
    _write_json(senate_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "document": "H.R. 1", "vote_date": "2025-01-15",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [],
    })

    mock_client = MagicMock()
    mock_client.get_bill = AsyncMock(side_effect=[
        {"bill": {"number": "1", "type": "HR", "congress": 117, "title": "117th Bill"}},
        {"bill": {"number": "1", "type": "HR", "congress": 119, "title": "119th Bill"}},
    ])
    mock_client.get_bill_summary = AsyncMock(return_value={"summaries": []})

    count = await sync_bills_from_votes(mock_client, tmp_path)

    data = json.loads((tmp_path / "bills.json").read_text())
    assert len(data["bills"]) == 2
    congresses = {b["congress"] for b in data["bills"]}
    assert congresses == {117, 119}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sync.py::test_sync_bills_from_votes_multi_congress -v`
Expected: FAIL (currently only fetches with congress=119)

**Step 3: Update sync_bills_from_votes**

Change the function signature to remove the `congress` parameter (it's now derived from vote data):

```python
async def sync_bills_from_votes(client: CongressAPIClient, output_dir: Path, rate_limit: float = 0.0) -> int:
    """Fetch only bills referenced in Senate and House vote documents. Incremental."""
    bills_path = output_dir / "bills.json"

    # Collect unique (congress, bill_ref) pairs from both chambers
    bill_refs: set[tuple[int, str]] = set()
    for chamber_dir in ["senate", "house"]:
        vote_dir = output_dir / "votes" / chamber_dir
        if not vote_dir.exists():
            continue
        for vote_file in sorted(vote_dir.glob("*.json")):
            with open(vote_file) as f:
                vote = json.load(f)
            ref = _parse_bill_ref(vote.get("document", ""))
            if ref:
                congress = vote.get("congress", 119)
                bill_refs.add((congress, ref))

    if not bill_refs:
        print("  No bill references found in votes — skipping")
        return 0

    print(f"  Found {len(bill_refs)} unique bills referenced in votes")

    # Load existing bills to skip already-fetched ones
    existing_bills: list[dict] = []
    existing_keys: set[str] = set()
    if bills_path.exists():
        with open(bills_path) as f:
            existing_bills = json.load(f).get("bills", [])
        for b in existing_bills:
            congress = b.get("congress", 119)
            key = f"{congress}-{b.get('type', '').lower()}-{b.get('number', '')}"
            existing_keys.add(key)

    # Fetch new bills
    new_bills = []
    refs_to_fetch = sorted(bill_refs - {(c, r) for c, r in bill_refs if f"{c}-{r}" in existing_keys})
    for i, (congress, ref) in enumerate(refs_to_fetch):
        parts = ref.rsplit("-", 1)
        if len(parts) != 2:
            continue
        bill_type, bill_number_str = parts

        # Check if already exists with congress-aware key
        full_key = f"{congress}-{ref}"
        if full_key in existing_keys:
            continue

        print(f"  Fetching {bill_type.upper()} {bill_number_str} (Congress {congress})... ({i + 1}/{len(refs_to_fetch)})")
        try:
            data = await client.get_bill(congress, bill_type, int(bill_number_str))
            bill = data.get("bill", {})

            try:
                summary_data = await client.get_bill_summary(congress, bill_type, int(bill_number_str))
                bill["summaries"] = summary_data.get("summaries", [])
            except Exception:
                bill["summaries"] = []

            new_bills.append(bill)
        except Exception as e:
            print(f"  WARNING: Failed to fetch {ref} (Congress {congress}): {e}")
        await asyncio.sleep(rate_limit)

    all_bills = existing_bills + new_bills
    _atomic_write_json(bills_path, {"bills": all_bills})
    print(f"  Saved {len(all_bills)} bills ({len(new_bills)} new)")
    return len(all_bills)
```

**Step 4: Update the main() call to remove congress param**

In `main()`, the call `await sync_bills_from_votes(client, SYNC_DIR, rate_limit=0.5)` already doesn't pass congress explicitly (uses default). But remove the default from the signature since congress now comes from vote data.

**Step 5: Fix existing tests that pass congress param**

Check `test_sync_bills_from_votes` — if it relied on the default `congress=119` parameter, it still works because vote files contain `"congress": 119`.

**Step 6: Run all tests**

Run: `pytest tests/test_sync.py -v`
Expected: All pass

**Step 7: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: multi-congress bill sync — track congress per bill ref"
```

---

## Phase 3: Multi-Congress Member Votes

**Completion gate:** `build_member_votes` aggregates votes across all congresses. Bill IDs use correct congress prefix. Member vote files store `congresses` array. Tests pass.

### Task 3: Update build_member_votes for multi-congress

**Files:**
- Modify: `sync.py:405-572` (build_member_votes)
- Test: `tests/test_sync.py`

**Step 1: Write test for multi-congress member votes**

```python
@pytest.mark.asyncio
async def test_build_member_votes_multi_congress(tmp_path):
    """Member votes aggregate across multiple congresses."""
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "stateCode": "FL", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 117, "type": "HR", "number": "1", "title": "117th Bill",
         "policyArea": {"name": "Taxation"}, "summaries": []},
        {"congress": 119, "type": "HR", "number": "1", "title": "119th Bill",
         "policyArea": {"name": "Healthcare"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)
    _write_json(tmp_path / "ai_summaries.json", {
        "117-hr-1": {"one_liner": "117th Congress bill", "direction": "strengthens"},
        "119-hr-1": {"one_liner": "119th Congress bill", "direction": "weakens"},
    })

    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "117_1_00001.json", {
        "congress": 117, "session": 1, "vote_number": 1,
        "vote_date": "2021-03-03", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
        ],
    })
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "H.R. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Nay"},
        ],
    })

    count = await build_member_votes(tmp_path)

    data = json.loads((tmp_path / "member_votes" / "S001217.json").read_text())
    assert data["stats"]["total_votes"] == 2
    assert data["stats"]["yea_count"] == 1
    assert data["stats"]["nay_count"] == 1
    assert set(data["congresses"]) == {117, 119}

    # Check bill_ids use correct congress
    bill_ids = {v["bill_id"] for v in data["votes"]}
    assert "117-hr-1" in bill_ids
    assert "119-hr-1" in bill_ids

    # Check one_liners come from correct congress summaries
    one_liners = {v["one_liner"] for v in data["votes"]}
    assert "117th Congress bill" in one_liners
    assert "119th Congress bill" in one_liners
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sync.py::test_build_member_votes_multi_congress -v`
Expected: FAIL

**Step 3: Update build_member_votes**

Key changes to `build_member_votes` in `sync.py`:

a) Update `_get_one_liner` and `_get_direction` to accept congress parameter:

```python
def _get_one_liner(bill_ref: str | None, bill_info: dict, doc: str, congress: int = 119) -> str:
    if bill_ref:
        summary_key = f"{congress}-{bill_ref}"
        ai_summary = ai_summaries.get(summary_key, {})
        if ai_summary.get("one_liner"):
            return ai_summary["one_liner"]
    return bill_info.get("title", doc)

def _get_direction(bill_ref: str | None, congress: int = 119) -> str | None:
    if bill_ref:
        summary_key = f"{congress}-{bill_ref}"
        summary = ai_summaries.get(summary_key, {})
        return summary.get("direction")
    return None
```

b) Update bill_lookup to be keyed by `(congress, ref)`:

```python
bill_lookup: dict[str, dict] = {}
if bills_path.exists():
    with open(bills_path) as f:
        bills_data = json.load(f)
    for bill in bills_data.get("bills", []):
        bill_type = bill.get("type", "").lower()
        bill_number = bill.get("number", "")
        congress = bill.get("congress", 119)
        key = f"{congress}-{bill_type}-{bill_number}"
        bill_lookup[key] = bill
```

c) In the vote loop (both Senate and House), use vote's congress:

```python
vote_congress = vote.get("congress", 119)
bill_ref = _parse_bill_ref(doc)
bill_key = f"{vote_congress}-{bill_ref}" if bill_ref else None
bill_info = bill_lookup.get(bill_key, {}) if bill_key else {}

member_vote_list.append({
    "bill_number": doc,
    "bill_id": f"{vote_congress}-{bill_ref}" if bill_ref else None,
    "one_liner": _get_one_liner(bill_ref, bill_info, doc, congress=vote_congress),
    "vote": matched.get("vote", ""),
    "date": vote.get("vote_date", ""),
    "result": vote.get("result", ""),
    "policy_area": bill_info.get("policyArea", {}).get("name", ""),
    "chamber": "Senate",  # or "House"
    "cbo_deficit_impact": None,
    "direction": _get_direction(bill_ref, congress=vote_congress),
    "congress": vote_congress,
})
```

d) Update the record structure to use `congresses` array:

```python
congresses_seen = sorted(set(v["congress"] for v in member_vote_list if v.get("congress")))

record = {
    "member_id": bioguide_id,
    "congresses": congresses_seen if congresses_seen else [119],
    "stats": {
        "total_votes": total,
        "yea_count": yea,
        "nay_count": nay,
        "not_voting_count": not_voting,
        "participation_rate": participation,
    },
    "scorecard": [],
    "votes": sorted(member_vote_list, key=lambda v: v["date"], reverse=True),
    "policy_areas": policy_areas,
}
```

**Step 4: Run tests**

Run: `pytest tests/test_sync.py -v`
Expected: All pass (including the new multi-congress test)

**Step 5: Update existing tests that check `data["congress"]`**

Some existing tests check `data["congress"]` — update them to check `data["congresses"]` instead. For single-congress test data, expect `[119]`.

**Step 6: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: multi-congress member votes — aggregate across 117/118/119"
```

---

## Phase 4: AI Member Summary Service

**Completion gate:** New service generates narrative member summaries from vote data. System prompt enforces facts-only, 7th-8th grade reading level. Tests pass with mocked LLM.

### Task 4: Create member summary service

**Files:**
- Create: `app/services/member_summary.py`
- Test: `tests/test_member_summary.py`

**Step 1: Write the test**

Create `tests/test_member_summary.py`:

```python
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.member_summary import MemberSummaryService, MEMBER_SUMMARY_SYSTEM_PROMPT


def test_system_prompt_has_no_bias_rules():
    """System prompt enforces facts-only, no editorializing."""
    assert "NO adjectives" in MEMBER_SUMMARY_SYSTEM_PROMPT
    assert "7th-8th grade" in MEMBER_SUMMARY_SYSTEM_PROMPT
    assert "facts" in MEMBER_SUMMARY_SYSTEM_PROMPT.lower()


def test_build_prompt_includes_vote_data():
    """Prompt includes member's policy areas, vote counts, and top bills."""
    service = MemberSummaryService(api_key=None)
    prompt = service._build_prompt(
        member_name="Kirsten E. Gillibrand",
        chamber="Senate",
        state="New York",
        congresses=[117, 118, 119],
        stats={"total_votes": 500, "yea_count": 200, "nay_count": 295, "participation_rate": 99.0},
        top_areas=[
            {"name": "Environmental Protection", "strengthen": 8, "weaken": 0, "total": 8},
            {"name": "Finance and Financial Sector", "strengthen": 3, "weaken": 1, "total": 4},
        ],
        top_supported=["Set military spending limits for 2026", "Fund clean energy research"],
        top_opposed=["Cancel an EPA rule on methane fees"],
    )
    assert "Gillibrand" in prompt
    assert "Environmental Protection" in prompt
    assert "8 strengthening" in prompt or "strengthen" in prompt.lower()
    assert "Set military spending limits" in prompt


@pytest.mark.asyncio
async def test_generate_member_summary_returns_narrative():
    """generate_member_summary returns a dict with narrative field."""
    mock_response = json.dumps({
        "narrative": "Over the past 5 years, Gillibrand has focused on environmental protection and financial regulation.",
        "top_areas": ["Environmental Protection", "Finance and Financial Sector"],
    })

    service = MemberSummaryService(api_key="test-key")
    service._call_llm = AsyncMock(return_value=mock_response)

    result = await service.generate_member_summary(
        member_name="Kirsten E. Gillibrand",
        chamber="Senate",
        state="New York",
        congresses=[117, 118, 119],
        stats={"total_votes": 500, "yea_count": 200, "nay_count": 295, "participation_rate": 99.0},
        top_areas=[{"name": "Environmental Protection", "strengthen": 8, "weaken": 0, "total": 8}],
        top_supported=["Set military spending limits for 2026"],
        top_opposed=["Cancel an EPA rule on methane fees"],
    )

    assert "narrative" in result
    assert "Gillibrand" in result["narrative"]
    assert "top_areas" in result


@pytest.mark.asyncio
async def test_generate_member_summary_handles_invalid_json():
    """Returns fallback when LLM returns invalid JSON."""
    service = MemberSummaryService(api_key="test-key")
    service._call_llm = AsyncMock(return_value="Not valid JSON")

    result = await service.generate_member_summary(
        member_name="Test Member",
        chamber="Senate",
        state="New York",
        congresses=[119],
        stats={"total_votes": 10, "yea_count": 5, "nay_count": 5, "participation_rate": 100.0},
        top_areas=[],
        top_supported=[],
        top_opposed=[],
    )

    assert "narrative" in result
    assert result["narrative"] != ""
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_member_summary.py -v`
Expected: FAIL (module doesn't exist)

**Step 3: Create the service**

Create `app/services/member_summary.py`:

```python
import json
import logging
import anthropic

logger = logging.getLogger(__name__)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from LLM output."""
    text = text.strip()
    if text.startswith("```"):
        first_newline = text.index("\n") if "\n" in text else len(text)
        text = text[first_newline + 1:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


MEMBER_SUMMARY_SYSTEM_PROMPT = """You are a nonpartisan legislative analyst for a government transparency tool. Your job is to write a brief voting profile for a member of Congress based entirely on their voting record data.

STRICT RULES:
1. NO adjectives (no "strong advocate", "champion of", "notable", "consistent")
2. NO value judgments (no "this helped/hurt", "positive record", "controversial")
3. NO characterization of intent (no "cares about", "fights for", "committed to")
4. NO political framing (no "progressive", "conservative", "moderate")
5. ONLY describe observable voting patterns — what they voted for, what they voted against, which policy areas they voted on most
6. Write at a 7th-8th grade reading level. Short sentences. Common words.
7. Include specific numbers where available (vote counts, participation rates)
8. The narrative should be 3-5 sentences. Facts only, no framing.

Output valid JSON only:
{"narrative": "3-5 sentence summary", "top_areas": ["Area 1", "Area 2", "Area 3"]}"""


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
                max_tokens=512,
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
    ) -> str:
        congress_range = f"{min(congresses)}th-{max(congresses)}th Congress" if len(congresses) > 1 else f"{congresses[0]}th Congress"

        areas_text = ""
        for area in top_areas:
            parts = []
            if area.get("strengthen", 0) > 0:
                parts.append(f"{area['strengthen']} strengthening")
            if area.get("weaken", 0) > 0:
                parts.append(f"{area['weaken']} weakening")
            count_text = ", ".join(parts) if parts else f"{area.get('total', 0)} votes"
            areas_text += f"  - {area['name']}: {count_text} ({area.get('total', 0)} total votes)\n"

        supported_text = "\n".join(f"  - {s}" for s in top_supported[:8]) if top_supported else "  (none with bill data)"
        opposed_text = "\n".join(f"  - s" for s in top_opposed[:6]) if top_opposed else "  (none with bill data)"

        return f"""Write a 3-5 sentence voting profile for this member of Congress based on the data below. Describe their voting patterns — what policy areas they focus on, whether they tend to strengthen or weaken rules in those areas, and notable bills they supported or opposed.

Member: {member_name}
Chamber: {chamber}
State: {state}
Period: {congress_range}

Voting Stats:
  Total votes: {stats.get('total_votes', 0)}
  Voted yes: {stats.get('yea_count', 0)}
  Voted no: {stats.get('nay_count', 0)}
  Participation rate: {stats.get('participation_rate', 0)}%

Top Policy Areas:
{areas_text}
Notable Bills Supported:
{supported_text}

Notable Bills Opposed:
{opposed_text}

Return ONLY valid JSON: {{"narrative": "...", "top_areas": [...]}}"""

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
        )

        if grader_feedback:
            prompt += f"\n\nIMPORTANT — PREVIOUS ATTEMPT REJECTED. Fix these issues:\n{grader_feedback}\n\nReturn ONLY valid JSON."

        raw_text = await self._call_llm(MEMBER_SUMMARY_SYSTEM_PROMPT, prompt)
        raw_text = _strip_code_fences(raw_text)

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.error("Member summary response was not valid JSON: %s", raw_text[:200])
            return {
                "narrative": f"{member_name} has voted {stats.get('total_votes', 0)} times with a {stats.get('participation_rate', 0)}% participation rate.",
                "top_areas": [a["name"] for a in top_areas[:3]],
            }

        if "narrative" not in result or not result["narrative"]:
            result["narrative"] = f"{member_name} has voted {stats.get('total_votes', 0)} times."

        if "top_areas" not in result:
            result["top_areas"] = [a["name"] for a in top_areas[:3]]

        return result
```

**Step 4: Run tests**

Run: `pytest tests/test_member_summary.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add app/services/member_summary.py tests/test_member_summary.py
git commit -m "feat: add AI member summary service with Sonnet"
```

---

## Phase 5: Member Summary Sync Integration

**Completion gate:** `sync_member_summaries` generates and grades narratives during sync. Stored in `member_summaries.json`. Integrated into main pipeline. Tests pass.

### Task 5: Add sync_member_summaries to sync pipeline

**Files:**
- Modify: `sync.py` (add sync_member_summaries function + wire into main)
- Test: `tests/test_sync.py`

**Step 1: Write test**

```python
@pytest.mark.asyncio
async def test_sync_member_summaries_generates_narrative(tmp_path):
    """sync_member_summaries generates narrative for each member."""
    members = {"members": [
        {"bioguideId": "G000555", "name": "Gillibrand, Kirsten E.",
         "directOrderName": "Kirsten E. Gillibrand",
         "stateCode": "NY", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    member_votes_dir = tmp_path / "member_votes"
    member_votes_dir.mkdir()
    _write_json(member_votes_dir / "G000555.json", {
        "member_id": "G000555",
        "congresses": [119],
        "stats": {"total_votes": 10, "yea_count": 7, "nay_count": 3,
                  "not_voting_count": 0, "participation_rate": 100.0},
        "votes": [
            {"bill_id": "119-hr-1", "one_liner": "Fund the military", "vote": "Yea",
             "policy_area": "Armed Forces and National Security", "direction": "strengthens",
             "congress": 119, "date": "2025-01-15", "result": "Passed", "chamber": "Senate"},
        ],
        "policy_areas": ["Armed Forces and National Security"],
    })

    from sync import sync_member_summaries
    import unittest.mock

    mock_narrative = json.dumps({
        "narrative": "Gillibrand voted 10 times with 100% participation.",
        "top_areas": ["Armed Forces and National Security"],
    })

    with unittest.mock.patch("app.services.member_summary.MemberSummaryService") as MockService:
        mock_instance = MagicMock()
        mock_instance.generate_member_summary = AsyncMock(return_value={
            "narrative": "Gillibrand voted 10 times with 100% participation.",
            "top_areas": ["Armed Forces and National Security"],
        })
        MockService.return_value = mock_instance

        count = await sync_member_summaries(tmp_path, api_key="test")

    summaries_path = tmp_path / "member_summaries.json"
    assert summaries_path.exists()
    data = json.loads(summaries_path.read_text())
    assert "G000555" in data
    assert "narrative" in data["G000555"]
    assert count == 1


@pytest.mark.asyncio
async def test_sync_member_summaries_skips_existing(tmp_path):
    """Incremental: skips members who already have summaries."""
    members = {"members": [
        {"bioguideId": "G000555", "name": "Gillibrand, Kirsten E.",
         "stateCode": "NY", "chamber": "Senate"},
    ]}
    _write_json(tmp_path / "members.json", members)

    member_votes_dir = tmp_path / "member_votes"
    member_votes_dir.mkdir()
    _write_json(member_votes_dir / "G000555.json", {
        "member_id": "G000555", "congresses": [119],
        "stats": {"total_votes": 10, "yea_count": 7, "nay_count": 3,
                  "not_voting_count": 0, "participation_rate": 100.0},
        "votes": [], "policy_areas": [],
    })

    # Pre-existing summary
    _write_json(tmp_path / "member_summaries.json", {
        "G000555": {"narrative": "Already exists.", "top_areas": []},
    })

    from sync import sync_member_summaries
    count = await sync_member_summaries(tmp_path)

    assert count == 0  # No new summaries generated
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sync.py::test_sync_member_summaries_generates_narrative -v`
Expected: FAIL (function doesn't exist)

**Step 3: Implement sync_member_summaries**

Add to `sync.py`:

```python
async def sync_member_summaries(
    output_dir: Path,
    api_key: str | None = None,
    rate_limit: float = 1.0,
) -> int:
    """Generate AI narrative summaries for each member based on their voting record.

    Incremental — skips members who already have summaries.
    Returns count of new summaries generated.
    """
    from app.services.member_summary import MemberSummaryService

    members_path = output_dir / "members.json"
    member_votes_dir = output_dir / "member_votes"
    summaries_path = output_dir / "member_summaries.json"

    if not members_path.exists():
        print("  No members.json — skipping member summaries")
        return 0

    with open(members_path) as f:
        members = json.load(f).get("members", [])

    # Load existing summaries (incremental)
    existing: dict[str, dict] = {}
    if summaries_path.exists():
        with open(summaries_path) as f:
            existing = json.load(f)

    service = MemberSummaryService(api_key=api_key)
    count = 0

    for member in members:
        bioguide_id = member["bioguideId"]

        # Skip if already has summary
        if bioguide_id in existing:
            continue

        # Load member's voting record
        votes_path = member_votes_dir / f"{bioguide_id}.json"
        if not votes_path.exists():
            continue

        with open(votes_path) as f:
            vote_data = json.load(f)

        votes = vote_data.get("votes", [])
        if not votes:
            continue

        member_name = member.get("directOrderName") or member.get("name", bioguide_id)
        chamber = member.get("chamber", "")
        state = member.get("state", member.get("stateCode", ""))
        congresses = vote_data.get("congresses", [119])
        stats = vote_data.get("stats", {})

        # Compute top areas with direction counts
        area_counts: dict[str, dict] = {}
        for v in votes:
            area = v.get("policy_area", "")
            if not area:
                continue
            if area not in area_counts:
                area_counts[area] = {"name": area, "strengthen": 0, "weaken": 0, "neutral": 0, "total": 0}
            area_counts[area]["total"] += 1
            direction = v.get("direction")
            is_yea = v.get("vote", "").lower() in ("yea", "aye")
            is_nay = v.get("vote", "").lower() in ("nay", "no")
            if direction == "strengthens":
                if is_yea:
                    area_counts[area]["strengthen"] += 1
                elif is_nay:
                    area_counts[area]["weaken"] += 1
            elif direction == "weakens":
                if is_yea:
                    area_counts[area]["weaken"] += 1
                elif is_nay:
                    area_counts[area]["strengthen"] += 1
            else:
                area_counts[area]["neutral"] += 1

        top_areas = sorted(area_counts.values(), key=lambda x: x["total"], reverse=True)[:5]

        # Collect top supported/opposed one-liners (deduplicated by bill_id)
        seen_supported = set()
        seen_opposed = set()
        top_supported = []
        top_opposed = []
        for v in votes:
            bill_id = v.get("bill_id")
            one_liner = v.get("one_liner", "")
            if not one_liner or not bill_id:
                continue
            if v.get("vote", "").lower() in ("yea", "aye") and bill_id not in seen_supported:
                seen_supported.add(bill_id)
                top_supported.append(one_liner)
            elif v.get("vote", "").lower() in ("nay", "no") and bill_id not in seen_opposed:
                seen_opposed.add(bill_id)
                top_opposed.append(one_liner)

        print(f"  Generating summary for {member_name}...")

        try:
            result = await service.generate_member_summary(
                member_name=member_name,
                chamber=chamber,
                state=state,
                congresses=congresses,
                stats=stats,
                top_areas=top_areas,
                top_supported=top_supported[:8],
                top_opposed=top_opposed[:6],
            )

            from datetime import datetime, timezone
            result["generated_at"] = datetime.now(timezone.utc).isoformat()
            existing[bioguide_id] = result
            count += 1
        except Exception as e:
            print(f"  WARNING: Failed to generate summary for {member_name}: {e}")

        await asyncio.sleep(rate_limit)

        # Save after each member (crash-safe)
        _atomic_write_json(summaries_path, existing)

    print(f"  Generated {count} member summaries")
    return count
```

**Step 4: Wire into main()**

Add after step 6 (build member votes):

```python
# Step 7: Member summaries
print()
print(f"[7/9] Generating AI member summaries ({'API' if anthropic_key else 'Claude CLI'})...")
member_summary_count = await sync_member_summaries(SYNC_DIR, api_key=anthropic_key or None)
```

Update step numbering and metadata to include `member_summary_count`.

**Step 5: Run tests**

Run: `pytest tests/test_sync.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add sync.py app/services/member_summary.py tests/test_sync.py
git commit -m "feat: integrate member summary generation into sync pipeline"
```

---

## Phase 6: Backend — Serve Member Summaries

**Completion gate:** DataService loads `member_summaries.json`. API returns narrative in member votes response. Tests pass.

### Task 6: Update DataService and API

**Files:**
- Modify: `app/services/data_service.py:6-11` (add member_summaries loading)
- Modify: `app/routers/members.py:50-57` (include narrative in summary endpoint)
- Test: `tests/test_data_service.py`

**Step 1: Write test for DataService**

Add to `tests/test_data_service.py`:

```python
def test_get_member_narrative(tmp_path):
    """DataService loads and returns member narrative summaries."""
    _setup_basic_data(tmp_path)  # helper that creates members.json, bills.json, etc.
    _write_json(tmp_path / "member_summaries.json", {
        "S001217": {
            "narrative": "Scott voted 500 times in the past 5 years.",
            "top_areas": ["Taxation", "Defense"],
            "generated_at": "2026-03-09T00:00:00Z",
        }
    })
    service = DataService(tmp_path)
    result = service.get_member_narrative("S001217")
    assert result is not None
    assert result["narrative"] == "Scott voted 500 times in the past 5 years."


def test_get_member_narrative_missing(tmp_path):
    """Returns None for member with no narrative."""
    _setup_basic_data(tmp_path)
    service = DataService(tmp_path)
    result = service.get_member_narrative("UNKNOWN")
    assert result is None
```

**Step 2: Update DataService**

Add to `__init__` and `_load`:

```python
self._member_summaries: dict[str, dict] = {}
# In _load:
self._member_summaries = self._read_json("member_summaries.json")
```

Add method:

```python
def get_member_narrative(self, bioguide_id: str) -> dict | None:
    bioguide_id = bioguide_id.upper()
    return self._member_summaries.get(bioguide_id)
```

**Step 3: Update API endpoint**

In `app/routers/members.py`, update `get_member_summary` to include narrative:

```python
@router.get("/{bioguide_id}/summary")
async def get_member_summary(bioguide_id: str):
    _validate_bioguide_id(bioguide_id)
    data_service = get_data_service()
    summary = data_service.get_member_vote_summary(bioguide_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Member not found")

    # Include AI narrative if available
    narrative = data_service.get_member_narrative(bioguide_id)
    if narrative:
        summary["narrative"] = narrative.get("narrative", "")
        summary["narrative_top_areas"] = narrative.get("top_areas", [])

    return summary
```

**Step 4: Run tests**

Run: `pytest tests/test_data_service.py tests/test_routers.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add app/services/data_service.py app/routers/members.py tests/test_data_service.py
git commit -m "feat: serve member narratives via API"
```

---

## Phase 7: Frontend — Display Member Narrative

**Completion gate:** Member detail page shows AI narrative paragraph at top of "At a Glance" card. Graceful fallback when no narrative exists.

### Task 7: Update member.js to display narrative

**Files:**
- Modify: `static/js/member.js:345-354` (add narrative before overview)

**Step 1: Update renderVotingSummary**

In the `renderVotingSummary` function, after creating the card and `h3`, add the narrative paragraph before the overview stats:

```javascript
// AI narrative (if available)
if (summaryData && summaryData.narrative) {
    const narrative = el('p', { className: 'summary-narrative' }, summaryData.narrative);
    card.appendChild(narrative);
}
```

The `summaryData` comes from the `/api/members/{id}/summary` endpoint which now includes `narrative`.

**Step 2: Ensure the summary endpoint is called**

Check where `renderVotingSummary` is called — it needs to receive the summary data. If the page already fetches from `/summary`, pass that data through. If not, add a fetch.

Looking at the existing code: the page fetches member votes from `/api/members/{id}/votes` and passes that to `renderVotingSummary`. The `/summary` endpoint is separate. We need to either:
- Fetch `/summary` too and pass the narrative in, or
- Include narrative in the `/votes` response

Simplest approach: fetch `/summary` in `loadMember` and pass the narrative to `renderVotingSummary`.

**Step 3: Add minimal CSS**

Add to `static/css/styles.css`:

```css
.summary-narrative {
    font-size: 1.05rem;
    line-height: 1.6;
    color: var(--text-secondary);
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--border);
}
```

**Step 4: Test manually**

Run: `cd ~/Documents/Claude/Projects/clearvote && source .venv/bin/activate && python app.py`
Visit a member page and verify the narrative appears above "At a Glance" data.

**Step 5: Commit**

```bash
git add static/js/member.js static/css/styles.css
git commit -m "feat: display AI member narrative on profile page"
```

---

## Phase 8: Add --regenerate-member-summaries flag

**Completion gate:** CLI flag forces regeneration of all member summaries (overwriting existing). Useful after expanding congresses.

### Task 8: Add CLI flag

**Files:**
- Modify: `sync.py` (add argparse flag + logic)

**Step 1: Add the flag**

In `main()` argparse section:

```python
parser.add_argument("--regenerate-member-summaries", action="store_true",
                    help="Force regeneration of all AI member summaries.")
```

**Step 2: Add handler**

```python
if args.regenerate_member_summaries:
    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    print("=== ClearVote Member Summary Regeneration ===")
    # Clear existing summaries to force regeneration
    summaries_path = SYNC_DIR / "member_summaries.json"
    if summaries_path.exists():
        _atomic_write_json(summaries_path, {})
        print("  Cleared existing member summaries")
    await sync_member_summaries(SYNC_DIR, api_key=anthropic_key or None)
    print("=== Regeneration complete ===")
    return
```

**Step 3: Commit**

```bash
git add sync.py
git commit -m "feat: add --regenerate-member-summaries CLI flag"
```

---

## Files Touched

| File | Change |
|------|--------|
| `sync.py` | Add CONGRESSES constant, multi-congress vote/bill sync loops, multi-congress member votes, sync_member_summaries function, CLI flags |
| `app/services/member_summary.py` | NEW — AI member summary service with Sonnet |
| `app/services/data_service.py` | Load member_summaries.json, add get_member_narrative() |
| `app/routers/members.py` | Include narrative in /summary endpoint |
| `static/js/member.js` | Display narrative paragraph in At a Glance card |
| `static/css/styles.css` | Style for .summary-narrative |
| `tests/test_sync.py` | Tests for multi-congress bill sync, member votes, member summaries |
| `tests/test_member_summary.py` | NEW — Tests for member summary service |
| `tests/test_data_service.py` | Test for get_member_narrative |

## Tests

| Type | Scope | Validates |
|------|-------|-----------|
| Unit | `test_sync.py` | Multi-congress bill sync, member vote aggregation, member summary sync |
| Unit | `test_member_summary.py` | Prompt construction, narrative generation, error handling |
| Unit | `test_data_service.py` | Member narrative loading and retrieval |
| Integration | Manual | Full sync with 3 congresses, narrative visible on member page |

## Not In Scope

- **Writer-grader loop for member summaries** — Can be added later if quality needs tightening. First pass uses direct generation.
- **UI redesign of member profile** — Narrative is just a paragraph. Visual polish is a separate task.
- **Syncing members from older congresses** — Only current members; historical votes matched by name/bioguide ID.
- **Per-congress stats breakdown** — Stats are aggregated across all congresses. Per-congress breakdown is a future enhancement.
