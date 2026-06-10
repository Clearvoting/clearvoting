# State-Scoped Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Modify `sync.py` to support `--states NY,FL` flag, scope bills to those referenced in Senate votes, add rate limiting, and skip AI summaries (generated in-session instead).

**Architecture:** Add argparse CLI, add `asyncio.sleep` rate limiting to API functions, replace the paginate-all-bills approach with a vote-referenced-bills-only approach, pass states filter through the pipeline.

**Tech Stack:** Python 3.13, asyncio, argparse, existing Congress.gov/Senate.gov clients

---

### Task 1: Add --states CLI argument and rate limiting to sync_members

**Files:**
- Modify: `sync.py:1-16` (imports), `sync.py:57-76` (sync_members), `sync.py:326-392` (main)
- Test: `tests/test_sync.py`

**Step 1: Write the failing test**

Add to `tests/test_sync.py`:

```python
@pytest.mark.asyncio
async def test_sync_members_rate_limiting(tmp_path):
    """Verify rate limiting delay is called between API requests."""
    mock_client = MagicMock()
    mock_client.get_members_by_state = AsyncMock(side_effect=[
        {"members": [{"bioguideId": "A1", "terms": {"item": [{"chamber": "Senate"}]}}]},
        {"members": [{"bioguideId": "B1", "terms": {"item": [{"chamber": "Senate"}]}}]},
    ])

    import unittest.mock
    with unittest.mock.patch("sync.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await sync_members(mock_client, tmp_path, states=["FL", "NY"], rate_limit=0.1)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(0.1)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/josephgarcia/Documents/Claude/Projects/clearvote && source .venv/bin/activate && pytest tests/test_sync.py::test_sync_members_rate_limiting -v`
Expected: FAIL — `sync_members` doesn't accept `rate_limit` param

**Step 3: Implement rate limiting in sync_members and add argparse to main**

In `sync.py`:

1. Add `import argparse` to imports
2. Add `rate_limit: float = 0.0` param to `sync_members`
3. Add `await asyncio.sleep(rate_limit)` after each API call in the loop
4. Replace the `main()` function to parse `--states` from CLI and pass states list through

```python
async def sync_members(client: CongressAPIClient, output_dir: Path, states: list[str] | None = None, rate_limit: float = 0.0) -> int:
    """Fetch all current members of Congress and save to members.json."""
    states = states or US_STATES
    all_members = []
    for i, state in enumerate(states):
        print(f"  Fetching members for {state}... ({i + 1}/{len(states)})")
        try:
            data = await client.get_members_by_state(state)
            for member in data.get("members", []):
                member["stateCode"] = state
                terms = member.get("terms", {}).get("item", [])
                if terms:
                    member["chamber"] = terms[0].get("chamber", "Unknown")
                all_members.append(member)
        except Exception as e:
            print(f"  WARNING: Failed to fetch {state}: {e}")
        await asyncio.sleep(rate_limit)

    _atomic_write_json(output_dir / "members.json", {"members": all_members})
    print(f"  Saved {len(all_members)} members")
    return len(all_members)
```

For `main()`:
```python
async def main() -> None:
    parser = argparse.ArgumentParser(description="ClearVote Data Sync")
    parser.add_argument("--states", type=str, default=None,
                        help="Comma-separated state codes (e.g., NY,FL). Default: all states.")
    args = parser.parse_args()

    states = [s.strip().upper() for s in args.states.split(",")] if args.states else None

    api_key = os.getenv("CONGRESS_API_KEY", "")
    if not api_key:
        print("ERROR: CONGRESS_API_KEY not set in .env")
        sys.exit(1)

    SYNC_DIR.mkdir(parents=True, exist_ok=True)
    cache = CacheService(cache_dir=CACHE_DIR, ttl_seconds=86400)
    client = CongressAPIClient(api_key=api_key, cache=cache)

    state_label = ", ".join(states) if states else "all states"
    print("=== ClearVote Data Sync ===")
    print(f"States: {state_label}")
    print(f"Output: {SYNC_DIR}")
    print()

    # Step 1: Members
    print("[1/4] Syncing members...")
    members_count = await sync_members(client, SYNC_DIR, states=states, rate_limit=0.5)

    # Step 2: Senate votes
    print()
    senate_service = SenateVoteService(cache=cache)
    print("[2/4] Syncing Senate votes...")
    senate_count = await sync_senate_votes(senate_service, SYNC_DIR, rate_limit=0.3)

    # Step 3: Bills (only those referenced in votes)
    print()
    print("[3/4] Syncing voted-on bills...")
    bills_count = await sync_bills_from_votes(client, SYNC_DIR, rate_limit=0.5)

    # Step 4: Member voting records
    print()
    print("[4/4] Building member voting records...")
    member_votes_count = await build_member_votes(SYNC_DIR)

    # Write metadata
    metadata = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "states_synced": states or US_STATES,
        "members_count": members_count,
        "bills_count": bills_count,
        "senate_votes_count": senate_count,
        "member_votes_count": member_votes_count,
    }
    _atomic_write_json(SYNC_DIR / "sync_metadata.json", metadata)
    print()
    print("=== Sync complete ===")
    print(f"  Members: {members_count}")
    print(f"  Bills: {bills_count}")
    print(f"  Senate votes: {senate_count}")
    print(f"  Member vote records: {member_votes_count}")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_sync.py::test_sync_members_rate_limiting -v`
Expected: PASS

**Step 5: Run all existing tests**

Run: `pytest tests/test_sync.py -v`
Expected: All pass (existing tests still work since `rate_limit` defaults to 0.0)

**Step 6: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: add --states CLI flag and rate limiting to sync_members"
```

---

### Task 2: Add rate limiting to sync_senate_votes

**Files:**
- Modify: `sync.py:114-139` (sync_senate_votes)
- Test: `tests/test_sync.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_sync_senate_votes_rate_limiting(tmp_path):
    """Verify rate limiting between Senate vote fetches."""
    mock_service = MagicMock()
    mock_service.get_vote = AsyncMock(side_effect=[
        {"congress": 119, "session": 1, "vote_number": 1, "vote_date": "2025-01-15",
         "question": "Test", "result": "Passed", "counts": {}, "members": []},
        Exception("No more"),
    ])

    import unittest.mock
    with unittest.mock.patch("sync.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await sync_senate_votes(mock_service, tmp_path, congress=119, session=1, max_vote=2, rate_limit=0.3)
        assert mock_sleep.call_count >= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sync.py::test_sync_senate_votes_rate_limiting -v`
Expected: FAIL

**Step 3: Add rate_limit param to sync_senate_votes**

```python
async def sync_senate_votes(senate_service: SenateVoteService, output_dir: Path, congress: int = 119, session: int = 1, max_vote: int = 500, rate_limit: float = 0.0) -> int:
```

Add `await asyncio.sleep(rate_limit)` after each fetch (not for skipped/cached votes).

**Step 4: Run all sync tests**

Run: `pytest tests/test_sync.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: add rate limiting to sync_senate_votes"
```

---

### Task 3: Replace sync_bills with sync_bills_from_votes

**Files:**
- Modify: `sync.py` — add new `sync_bills_from_votes` function, keep old `sync_bills` for reference
- Test: `tests/test_sync.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_sync_bills_from_votes(tmp_path):
    """Only fetches bills that appear in Senate vote documents."""
    # Set up Senate vote files with bill references
    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "document": "H.R. 1", "vote_date": "2025-01-15",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [],
    })
    _write_json(vote_dir / "119_1_00002.json", {
        "congress": 119, "session": 1, "vote_number": 2,
        "document": "S. 100", "vote_date": "2025-01-16",
        "question": "On Passage", "result": "Failed",
        "counts": {}, "members": [],
    })
    # Duplicate bill ref — should only fetch once
    _write_json(vote_dir / "119_1_00003.json", {
        "congress": 119, "session": 1, "vote_number": 3,
        "document": "H.R. 1", "vote_date": "2025-01-17",
        "question": "On the Motion", "result": "Passed",
        "counts": {}, "members": [],
    })

    mock_client = MagicMock()
    mock_client.get_bill = AsyncMock(side_effect=[
        {"bill": {"number": "1", "type": "HR", "congress": 119, "title": "Test Bill", "policyArea": {"name": "Taxation"}}},
        {"bill": {"number": "100", "type": "S", "congress": 119, "title": "Senate Bill", "policyArea": {"name": "Healthcare"}}},
    ])
    mock_client.get_bill_summary = AsyncMock(return_value={"summaries": [{"text": "Summary"}]})

    count = await sync_bills_from_votes(mock_client, tmp_path)

    bills_file = tmp_path / "bills.json"
    assert bills_file.exists()
    data = json.loads(bills_file.read_text())
    assert len(data["bills"]) == 2
    assert count == 2
    # Should have fetched exactly 2 unique bills
    assert mock_client.get_bill.call_count == 2


@pytest.mark.asyncio
async def test_sync_bills_from_votes_no_votes(tmp_path):
    """Handles missing vote directory gracefully."""
    mock_client = MagicMock()
    count = await sync_bills_from_votes(mock_client, tmp_path)
    assert count == 0


@pytest.mark.asyncio
async def test_sync_bills_from_votes_skips_existing(tmp_path):
    """Skips bills already in bills.json (incremental)."""
    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "document": "H.R. 1", "vote_date": "2025-01-15",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [],
    })

    # Pre-existing bills.json with HR 1 already synced
    _write_json(tmp_path / "bills.json", {"bills": [
        {"number": "1", "type": "HR", "congress": 119, "title": "Already Here", "summaries": []},
    ]})

    mock_client = MagicMock()
    mock_client.get_bill = AsyncMock()  # Should not be called

    count = await sync_bills_from_votes(mock_client, tmp_path)

    assert count == 1  # 1 bill total (the existing one)
    assert mock_client.get_bill.call_count == 0  # No new fetches
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sync.py::test_sync_bills_from_votes -v`
Expected: FAIL — `sync_bills_from_votes` doesn't exist

**Step 3: Implement sync_bills_from_votes**

```python
async def sync_bills_from_votes(client: CongressAPIClient, output_dir: Path, congress: int = 119, rate_limit: float = 0.0) -> int:
    """Fetch only bills referenced in Senate vote documents."""
    senate_dir = output_dir / "votes" / "senate"
    bills_path = output_dir / "bills.json"

    if not senate_dir.exists():
        print("  No Senate votes found — skipping bills")
        return 0

    # Collect unique bill references from vote files
    bill_refs: set[str] = set()
    for vote_file in sorted(senate_dir.glob("*.json")):
        with open(vote_file) as f:
            vote = json.load(f)
        ref = _parse_bill_ref(vote.get("document", ""))
        if ref:
            bill_refs.add(ref)

    print(f"  Found {len(bill_refs)} unique bills referenced in votes")

    # Load existing bills to skip already-fetched ones
    existing_bills: list[dict] = []
    existing_keys: set[str] = set()
    if bills_path.exists():
        with open(bills_path) as f:
            existing_bills = json.load(f).get("bills", [])
        for b in existing_bills:
            key = f"{b.get('type', '').lower()}-{b.get('number', '')}"
            existing_keys.add(key)

    # Fetch new bills
    new_bills = []
    for i, ref in enumerate(sorted(bill_refs)):
        if ref in existing_keys:
            continue

        # Parse ref like "hr-1" into type="hr", number=1
        parts = ref.rsplit("-", 1)
        if len(parts) != 2:
            continue
        bill_type, bill_number_str = parts

        print(f"  Fetching {bill_type.upper()} {bill_number_str}... ({i + 1}/{len(bill_refs)})")
        try:
            data = await client.get_bill(congress, bill_type, int(bill_number_str))
            bill = data.get("bill", {})

            # Also fetch summary
            try:
                summary_data = await client.get_bill_summary(congress, bill_type, int(bill_number_str))
                bill["summaries"] = summary_data.get("summaries", [])
            except Exception:
                bill["summaries"] = []

            new_bills.append(bill)
        except Exception as e:
            print(f"  WARNING: Failed to fetch {ref}: {e}")
        await asyncio.sleep(rate_limit)

    all_bills = existing_bills + new_bills
    _atomic_write_json(bills_path, {"bills": all_bills})
    print(f"  Saved {len(all_bills)} bills ({len(new_bills)} new)")
    return len(all_bills)
```

**Step 4: Run all sync tests**

Run: `pytest tests/test_sync.py -v`
Expected: All pass

**Step 5: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: add sync_bills_from_votes — only fetch voted-on bills"
```

---

### Task 4: Remove AI summary step from main, update old sync_bills tests, clean up

**Files:**
- Modify: `sync.py` (main function, remove AISummaryService import usage from main)
- Modify: `tests/test_sync.py` (update tests for removed old sync_bills from main flow)

**Step 1: Update main() to use new pipeline**

The `main()` function from Task 1 already has the new 4-step pipeline. Ensure:
- `AISummaryService` import stays (the function still exists for future use)
- `sync_bills` function stays (can be used if someone wants all bills)
- `main()` calls `sync_bills_from_votes` instead of `sync_bills`
- Pipeline is 4 steps, not 5

**Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: All 86+ tests pass

**Step 3: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "refactor: remove AI summary step from sync pipeline, clean up"
```

---

### Task 5: Run sync for NY + FL and verify

**Step 1: Run the sync**

```bash
cd /Users/josephgarcia/Documents/Claude/Projects/clearvote
source .venv/bin/activate
python sync.py --states NY,FL
```

Expected output:
```
=== ClearVote Data Sync ===
States: NY, FL
Output: .../data/synced
[1/4] Syncing members...
[2/4] Syncing Senate votes...
[3/4] Syncing voted-on bills...
[4/4] Building member voting records...
=== Sync complete ===
```

**Step 2: Verify synced data**

```bash
cat data/synced/sync_metadata.json
ls data/synced/member_votes/
wc -l data/synced/members.json data/synced/bills.json
ls data/synced/votes/senate/ | wc -l
```

**Step 3: Commit synced data**

```bash
git add data/synced/
git commit -m "data: initial sync for NY and FL"
```

---

### Task 6: Generate AI summaries in-session

**Step 1: Read bills.json**

Read `data/synced/bills.json` to get all bill titles and official summaries.

**Step 2: Generate summaries**

For each bill, generate a plain-language summary following the format in `ai_summaries.json`:
```json
{
  "119-hr-1": {
    "provisions": ["One sentence per provision..."],
    "impact_categories": ["Category from the approved list"]
  }
}
```

Use the same rules from `app/services/ai_summary.py` SYSTEM_PROMPT:
- No adjectives, no value judgments, no political framing
- 7th-8th grade reading level
- Specific numbers and dates
- 3-7 provisions per bill

**Step 3: Write to ai_summaries.json**

Write the complete summaries dict to `data/synced/ai_summaries.json`.

**Step 4: Commit**

```bash
git add data/synced/ai_summaries.json
git commit -m "data: AI summaries for NY/FL voted-on bills"
```
