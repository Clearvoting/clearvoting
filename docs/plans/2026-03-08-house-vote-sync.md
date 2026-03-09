# House Vote Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add House roll call vote syncing so all House reps get voting records, matching what Senators already have.

**Architecture:** New `sync_house_votes()` function calls Congress.gov `/house-vote` API, saves to `data/synced/votes/house/`. Expand `sync_bills_from_votes()` and `build_member_votes()` to read both chambers. Pipeline becomes 5 steps.

**Tech Stack:** Python 3.13, asyncio, existing CongressAPIClient (methods already built), pytest

---

### Task 1: Add `sync_house_votes()` with tests

**Files:**
- Modify: `sync.py` (add new function after `sync_senate_votes`)
- Test: `tests/test_sync.py`

**Step 1: Write the failing tests**

Add to `tests/test_sync.py` imports:

```python
from sync import sync_members, sync_senate_votes, sync_bills_from_votes, build_member_votes, _parse_bill_ref, sync_house_votes
```

Add tests:

```python
# --- sync_house_votes ---

@pytest.mark.asyncio
async def test_sync_house_votes(tmp_path):
    """Fetches House votes and saves as JSON files."""
    mock_client = MagicMock()
    mock_client.get_house_vote_detail = AsyncMock(side_effect=[
        {"houseRollCallVote": {
            "congress": 119, "sessionNumber": 1, "rollCallNumber": 1,
            "legislationType": "HR", "legislationNumber": "153",
            "voteQuestion": "On Motion to Suspend the Rules and Pass",
            "result": "Passed", "startDate": "2025-01-10T14:00:00-05:00",
            "votePartyTotal": [
                {"voteParty": "R", "yeaTotal": 200, "nayTotal": 10, "notVotingTotal": 5, "presentTotal": 0},
                {"voteParty": "D", "yeaTotal": 180, "nayTotal": 20, "notVotingTotal": 5, "presentTotal": 0},
            ],
        }},
        Exception("No more votes"),
    ])
    mock_client.get_house_vote_members = AsyncMock(return_value={
        "houseRollCallVoteMemberVotes": {
            "results": [
                {"bioguideID": "A000055", "firstName": "Robert", "lastName": "Aderholt",
                 "voteCast": "Yea", "voteParty": "R", "voteState": "AL"},
            ],
        },
    })

    count = await sync_house_votes(mock_client, tmp_path, congress=119, session=1, max_vote=2)

    vote_dir = tmp_path / "votes" / "house"
    assert vote_dir.exists()
    filepath = vote_dir / "119_1_00001.json"
    assert filepath.exists()
    assert count == 1

    data = json.loads(filepath.read_text())
    assert data["congress"] == 119
    assert data["vote_number"] == 1
    assert data["question"] == "On Motion to Suspend the Rules and Pass"
    assert data["document"] == "H.R. 153"
    assert len(data["members"]) == 1
    assert data["members"][0]["bioguide_id"] == "A000055"
    assert data["members"][0]["vote"] == "Yea"


@pytest.mark.asyncio
async def test_sync_house_votes_skips_existing(tmp_path):
    """Incremental sync skips votes that already have files."""
    vote_dir = tmp_path / "votes" / "house"
    vote_dir.mkdir(parents=True)
    _write_json(vote_dir / "119_1_00001.json", {"vote_number": 1})

    mock_client = MagicMock()
    mock_client.get_house_vote_detail = AsyncMock(side_effect=[
        {"houseRollCallVote": {
            "congress": 119, "sessionNumber": 1, "rollCallNumber": 2,
            "legislationType": "HR", "legislationNumber": "200",
            "voteQuestion": "On Passage", "result": "Failed",
            "startDate": "2025-01-11T10:00:00-05:00", "votePartyTotal": [],
        }},
        Exception("No more"),
    ])
    mock_client.get_house_vote_members = AsyncMock(return_value={
        "houseRollCallVoteMemberVotes": {"results": []},
    })

    count = await sync_house_votes(mock_client, tmp_path, congress=119, session=1, max_vote=3)

    assert count == 2  # 1 existing + 1 new
    assert (vote_dir / "119_1_00002.json").exists()


@pytest.mark.asyncio
async def test_sync_house_votes_rate_limiting(tmp_path):
    """Verify rate limiting between House vote fetches."""
    mock_client = MagicMock()
    mock_client.get_house_vote_detail = AsyncMock(side_effect=[
        {"houseRollCallVote": {
            "congress": 119, "sessionNumber": 1, "rollCallNumber": 1,
            "voteQuestion": "Test", "result": "Passed",
            "startDate": "2025-01-10T14:00:00-05:00", "votePartyTotal": [],
        }},
        Exception("No more"),
    ])
    mock_client.get_house_vote_members = AsyncMock(return_value={
        "houseRollCallVoteMemberVotes": {"results": []},
    })

    import unittest.mock
    with unittest.mock.patch("sync.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await sync_house_votes(mock_client, tmp_path, congress=119, session=1, max_vote=2, rate_limit=0.3)
        assert mock_sleep.call_count >= 1
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/josephgarcia/Documents/Claude/Projects/clearvote && source .venv/bin/activate && pytest tests/test_sync.py::test_sync_house_votes -v`
Expected: FAIL — `sync_house_votes` cannot be imported

**Step 3: Implement `sync_house_votes()`**

Add to `sync.py` after `sync_senate_votes()`:

```python
def _house_leg_to_document(leg_type: str | None, leg_number: str | None) -> str:
    """Convert House API legislationType/Number to document string matching bill ref format.

    Examples: ('HR', '153') -> 'H.R. 153', ('S', '100') -> 'S. 100',
              ('HJRES', '42') -> 'H.J.Res. 42', ('HRES', '5') -> 'H.Res. 5'
    """
    if not leg_type or not leg_number:
        return ""
    mapping = {
        "HR": f"H.R. {leg_number}",
        "S": f"S. {leg_number}",
        "HJRES": f"H.J.Res. {leg_number}",
        "SJRES": f"S.J.Res. {leg_number}",
        "HRES": f"H.Res. {leg_number}",
        "SRES": f"S.Res. {leg_number}",
        "HCONRES": f"H.Con.Res. {leg_number}",
        "SCONRES": f"S.Con.Res. {leg_number}",
    }
    return mapping.get(leg_type.upper(), f"{leg_type} {leg_number}")


async def sync_house_votes(client: CongressAPIClient, output_dir: Path, congress: int = 119, session: int = 1, max_vote: int = 500, rate_limit: float = 0.0) -> int:
    """Fetch House roll call votes from Congress.gov API. Incremental — skips existing files."""
    vote_dir = output_dir / "votes" / "house"
    vote_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for vote_num in range(1, max_vote + 1):
        filename = f"{congress}_{session}_{vote_num:05d}.json"
        filepath = vote_dir / filename

        if filepath.exists():
            count += 1
            continue

        print(f"  Fetching House vote {vote_num}...")
        try:
            detail_resp = await client.get_house_vote_detail(congress, session, vote_num)
            vote_data = detail_resp.get("houseRollCallVote", {})

            members_resp = await client.get_house_vote_members(congress, session, vote_num)
            members_data = members_resp.get("houseRollCallVoteMemberVotes", {}).get("results", [])

            # Build counts from votePartyTotal
            party_totals = vote_data.get("votePartyTotal", [])
            yeas = sum(p.get("yeaTotal", 0) for p in party_totals)
            nays = sum(p.get("nayTotal", 0) for p in party_totals)
            not_voting = sum(p.get("notVotingTotal", 0) for p in party_totals)
            present = sum(p.get("presentTotal", 0) for p in party_totals)

            document = _house_leg_to_document(
                vote_data.get("legislationType"),
                vote_data.get("legislationNumber"),
            )

            # Normalize to same schema as Senate votes
            normalized = {
                "congress": vote_data.get("congress", congress),
                "session": vote_data.get("sessionNumber", session),
                "vote_number": vote_data.get("rollCallNumber", vote_num),
                "vote_date": vote_data.get("startDate", "")[:10],
                "question": vote_data.get("voteQuestion", ""),
                "document": document,
                "result": vote_data.get("result", ""),
                "title": "",
                "counts": {
                    "yeas": yeas,
                    "nays": nays,
                    "present": present,
                    "absent": not_voting,
                },
                "members": [
                    {
                        "bioguide_id": m.get("bioguideID", ""),
                        "first_name": m.get("firstName", ""),
                        "last_name": m.get("lastName", ""),
                        "party": m.get("voteParty", ""),
                        "state": m.get("voteState", ""),
                        "vote": m.get("voteCast", ""),
                    }
                    for m in members_data
                ],
                "chamber": "House",
            }

            _atomic_write_json(filepath, normalized)
            count += 1
            await asyncio.sleep(rate_limit)
        except Exception:
            print(f"  No more House votes after {vote_num - 1}")
            break

    print(f"  Saved {count} House votes")
    return count
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sync.py -k "house_votes" -v`
Expected: All 3 PASS

**Step 5: Run all sync tests**

Run: `pytest tests/test_sync.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: add sync_house_votes() for House roll call vote syncing"
```

---

### Task 2: Add `_house_leg_to_document` tests and expand `_parse_bill_ref` for House resolution types

**Files:**
- Modify: `sync.py:275-286` (`_parse_bill_ref`)
- Test: `tests/test_sync.py`

**Step 1: Write the failing tests**

Add to `tests/test_sync.py` imports:

```python
from sync import sync_members, sync_senate_votes, sync_bills_from_votes, build_member_votes, _parse_bill_ref, sync_house_votes, _house_leg_to_document
```

Add tests:

```python
# --- _house_leg_to_document ---

def test_house_leg_to_document():
    assert _house_leg_to_document("HR", "153") == "H.R. 153"
    assert _house_leg_to_document("S", "100") == "S. 100"
    assert _house_leg_to_document("HJRES", "42") == "H.J.Res. 42"
    assert _house_leg_to_document("HRES", "5") == "H.Res. 5"
    assert _house_leg_to_document("HCONRES", "14") == "H.Con.Res. 14"
    assert _house_leg_to_document(None, None) == ""
    assert _house_leg_to_document("", "") == ""


# --- _parse_bill_ref (House resolution types) ---

def test_parse_bill_ref_house_resolutions():
    assert _parse_bill_ref("H.Res. 5") == "hres-5"
    assert _parse_bill_ref("H.Con.Res. 14") == "hconres-14"
    assert _parse_bill_ref("S.Res. 50") == "sres-50"
    assert _parse_bill_ref("S.Con.Res. 10") == "sconres-10"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sync.py::test_parse_bill_ref_house_resolutions -v`
Expected: FAIL — `_parse_bill_ref` doesn't handle these types

**Step 3: Expand `_parse_bill_ref`**

Replace `_parse_bill_ref` in `sync.py`:

```python
def _parse_bill_ref(document: str) -> str | None:
    """Parse bill document strings into normalized refs.

    Examples: 'H.R. 1' -> 'hr-1', 'S. 100' -> 's-100',
              'H.J.Res. 42' -> 'hjres-42', 'H.Res. 5' -> 'hres-5',
              'H.Con.Res. 14' -> 'hconres-14'
    """
    doc = document.strip()
    prefixes = [
        ("H.Con.Res. ", "hconres-"),
        ("S.Con.Res. ", "sconres-"),
        ("H.J.Res. ", "hjres-"),
        ("S.J.Res. ", "sjres-"),
        ("H.Res. ", "hres-"),
        ("S.Res. ", "sres-"),
        ("H.R. ", "hr-"),
        ("S. ", "s-"),
    ]
    for prefix, ref_prefix in prefixes:
        if doc.startswith(prefix):
            return f"{ref_prefix}{doc[len(prefix):]}"
    return None
```

**Step 4: Run all parse tests**

Run: `pytest tests/test_sync.py -k "parse_bill_ref" -v`
Expected: All PASS (old tests + new tests)

**Step 5: Run all tests**

Run: `pytest tests/test_sync.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: expand _parse_bill_ref for House resolution types, add _house_leg_to_document tests"
```

---

### Task 3: Expand `sync_bills_from_votes()` to scan House votes too

**Files:**
- Modify: `sync.py:110-169` (`sync_bills_from_votes`)
- Test: `tests/test_sync.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_sync_bills_from_votes_includes_house(tmp_path):
    """Scans both Senate and House vote directories for bill references."""
    # Senate vote referencing H.R. 1
    senate_dir = tmp_path / "votes" / "senate"
    senate_dir.mkdir(parents=True)
    _write_json(senate_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "document": "H.R. 1", "vote_date": "2025-01-15",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [],
    })

    # House vote referencing H.R. 200 (different bill)
    house_dir = tmp_path / "votes" / "house"
    house_dir.mkdir(parents=True)
    _write_json(house_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "document": "H.R. 200", "vote_date": "2025-01-16",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [], "chamber": "House",
    })

    mock_client = MagicMock()
    mock_client.get_bill = AsyncMock(side_effect=[
        {"bill": {"number": "1", "type": "HR", "congress": 119, "title": "Bill One", "policyArea": {"name": "Taxation"}}},
        {"bill": {"number": "200", "type": "HR", "congress": 119, "title": "Bill Two", "policyArea": {"name": "Defense"}}},
    ])
    mock_client.get_bill_summary = AsyncMock(return_value={"summaries": []})

    count = await sync_bills_from_votes(mock_client, tmp_path)

    data = json.loads((tmp_path / "bills.json").read_text())
    assert len(data["bills"]) == 2
    assert count == 2
    assert mock_client.get_bill.call_count == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_sync.py::test_sync_bills_from_votes_includes_house -v`
Expected: FAIL — only finds H.R. 1 from Senate dir (count == 1)

**Step 3: Update `sync_bills_from_votes()` to scan both directories**

In `sync.py`, modify `sync_bills_from_votes()` — replace the section that collects bill refs:

```python
async def sync_bills_from_votes(client: CongressAPIClient, output_dir: Path, congress: int = 119, rate_limit: float = 0.0) -> int:
    """Fetch only bills referenced in Senate and House vote documents. Incremental."""
    bills_path = output_dir / "bills.json"

    # Collect unique bill references from both Senate and House vote files
    bill_refs: set[str] = set()
    for chamber_dir in ["senate", "house"]:
        vote_dir = output_dir / "votes" / chamber_dir
        if not vote_dir.exists():
            continue
        for vote_file in sorted(vote_dir.glob("*.json")):
            with open(vote_file) as f:
                vote = json.load(f)
            ref = _parse_bill_ref(vote.get("document", ""))
            if ref:
                bill_refs.add(ref)

    if not bill_refs:
        print("  No bill references found in votes — skipping")
        return 0

    print(f"  Found {len(bill_refs)} unique bills referenced in votes")

    # Rest of function unchanged — load existing, fetch new, save
    existing_bills: list[dict] = []
    existing_keys: set[str] = set()
    if bills_path.exists():
        with open(bills_path) as f:
            existing_bills = json.load(f).get("bills", [])
        for b in existing_bills:
            key = f"{b.get('type', '').lower()}-{b.get('number', '')}"
            existing_keys.add(key)

    new_bills = []
    refs_to_fetch = sorted(bill_refs - existing_keys)
    for i, ref in enumerate(refs_to_fetch):
        parts = ref.rsplit("-", 1)
        if len(parts) != 2:
            continue
        bill_type, bill_number_str = parts

        print(f"  Fetching {bill_type.upper()} {bill_number_str}... ({i + 1}/{len(refs_to_fetch)})")
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
            print(f"  WARNING: Failed to fetch {ref}: {e}")
        await asyncio.sleep(rate_limit)

    all_bills = existing_bills + new_bills
    _atomic_write_json(bills_path, {"bills": all_bills})
    print(f"  Saved {len(all_bills)} bills ({len(new_bills)} new)")
    return len(all_bills)
```

**Step 4: Run all bill-related tests**

Run: `pytest tests/test_sync.py -k "bills" -v`
Expected: All PASS (old tests still work since Senate dir still gets scanned)

**Step 5: Run all tests**

Run: `pytest tests/test_sync.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: sync_bills_from_votes scans both Senate and House vote dirs"
```

---

### Task 4: Expand `build_member_votes()` for House members

**Files:**
- Modify: `sync.py:172-272` (`build_member_votes`)
- Test: `tests/test_sync.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_build_member_votes_house(tmp_path):
    """House members get vote records from House vote files."""
    members = {"members": [
        {"bioguideId": "A000055", "name": "Aderholt, Robert", "directOrderName": "Robert Aderholt",
         "stateCode": "AL", "chamber": "House of Representatives"},
    ]}
    _write_json(tmp_path / "members.json", members)

    bills = {"bills": [
        {"congress": 119, "type": "HR", "number": "153", "title": "Test House Bill",
         "policyArea": {"name": "Defense"}, "summaries": []},
    ]}
    _write_json(tmp_path / "bills.json", bills)

    vote_dir = tmp_path / "votes" / "house"
    vote_dir.mkdir(parents=True)
    vote = {
        "congress": 119, "session": 1, "vote_number": 10,
        "vote_date": "2025-01-10", "document": "H.R. 153",
        "question": "On Motion to Suspend the Rules and Pass",
        "result": "Passed", "chamber": "House",
        "counts": {"yeas": 380, "nays": 30, "present": 0, "absent": 24},
        "members": [
            {"bioguide_id": "A000055", "first_name": "Robert", "last_name": "Aderholt",
             "party": "R", "state": "AL", "vote": "Yea"},
        ],
    }
    _write_json(vote_dir / "119_1_00010.json", vote)

    count = await build_member_votes(tmp_path)

    member_file = tmp_path / "member_votes" / "A000055.json"
    assert member_file.exists()
    data = json.loads(member_file.read_text())
    assert data["member_id"] == "A000055"
    assert data["stats"]["total_votes"] == 1
    assert data["stats"]["yea_count"] == 1
    assert data["votes"][0]["chamber"] == "House"
    assert data["votes"][0]["bill_id"] == "119-hr-153"
    assert count == 1


@pytest.mark.asyncio
async def test_build_member_votes_both_chambers(tmp_path):
    """Both Senate and House members get records when both vote dirs exist."""
    members = {"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "stateCode": "FL", "chamber": "Senate"},
        {"bioguideId": "B001257", "name": "Bilirakis, Gus", "directOrderName": "Gus Bilirakis",
         "stateCode": "FL", "chamber": "House of Representatives"},
    ]}
    _write_json(tmp_path / "members.json", members)
    _write_json(tmp_path / "bills.json", {"bills": []})

    # Senate vote
    senate_dir = tmp_path / "votes" / "senate"
    senate_dir.mkdir(parents=True)
    _write_json(senate_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-15", "document": "S. 1",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
        ],
    })

    # House vote
    house_dir = tmp_path / "votes" / "house"
    house_dir.mkdir(parents=True)
    _write_json(house_dir / "119_1_00001.json", {
        "congress": 119, "session": 1, "vote_number": 1,
        "vote_date": "2025-01-16", "document": "H.R. 10",
        "question": "On Passage", "result": "Passed",
        "counts": {}, "chamber": "House",
        "members": [
            {"bioguide_id": "B001257", "first_name": "Gus", "last_name": "Bilirakis",
             "party": "R", "state": "FL", "vote": "Nay"},
        ],
    })

    count = await build_member_votes(tmp_path)

    assert count == 2
    assert (tmp_path / "member_votes" / "S001217.json").exists()
    assert (tmp_path / "member_votes" / "B001257.json").exists()

    house_data = json.loads((tmp_path / "member_votes" / "B001257.json").read_text())
    assert house_data["stats"]["nay_count"] == 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sync.py::test_build_member_votes_house -v`
Expected: FAIL — House members are not processed

**Step 3: Rewrite `build_member_votes()` to handle both chambers**

Replace `build_member_votes()` in `sync.py`:

```python
async def build_member_votes(output_dir: Path) -> int:
    """Cross-reference votes with members to build per-member voting records."""
    members_path = output_dir / "members.json"
    bills_path = output_dir / "bills.json"
    member_votes_dir = output_dir / "member_votes"
    member_votes_dir.mkdir(parents=True, exist_ok=True)

    if not members_path.exists():
        print("  No members.json — skipping")
        return 0

    with open(members_path) as f:
        members_data = json.load(f)

    # Build bill lookup for policy areas and titles
    bill_lookup: dict[str, dict] = {}
    if bills_path.exists():
        with open(bills_path) as f:
            bills_data = json.load(f)
        for bill in bills_data.get("bills", []):
            bill_type = bill.get("type", "").lower()
            bill_number = bill.get("number", "")
            key = f"{bill_type}-{bill_number}"
            bill_lookup[key] = bill

    # Load all votes from both chambers
    senate_votes: list[dict] = []
    senate_dir = output_dir / "votes" / "senate"
    if senate_dir.exists():
        for vote_file in sorted(senate_dir.glob("*.json")):
            with open(vote_file) as f:
                senate_votes.append(json.load(f))

    house_votes: list[dict] = []
    house_dir = output_dir / "votes" / "house"
    if house_dir.exists():
        for vote_file in sorted(house_dir.glob("*.json")):
            with open(vote_file) as f:
                house_votes.append(json.load(f))

    all_members = members_data.get("members", [])
    count = 0

    for member in all_members:
        bioguide_id = member["bioguideId"]
        chamber = member.get("chamber", "")
        member_last = member.get("name", "").split(",")[0].strip().lower()
        member_state = member.get("stateCode", "").upper()

        print(f"  Building votes for {member.get('directOrderName', bioguide_id)}...")

        member_vote_list = []

        if chamber == "Senate":
            # Match Senate votes by last name + state (Senate XML uses names, not bioguide IDs)
            for vote in senate_votes:
                matched = None
                for mv in vote.get("members", []):
                    if (mv.get("last_name", "").lower() == member_last
                            and mv.get("state", "").upper() == member_state):
                        matched = mv
                        break
                if not matched:
                    continue

                doc = vote.get("document", "")
                bill_ref = _parse_bill_ref(doc)
                bill_info = bill_lookup.get(bill_ref, {}) if bill_ref else {}

                member_vote_list.append({
                    "bill_number": doc,
                    "bill_id": f"119-{bill_ref}" if bill_ref else None,
                    "one_liner": bill_info.get("title", doc),
                    "vote": matched.get("vote", ""),
                    "date": vote.get("vote_date", ""),
                    "result": vote.get("result", ""),
                    "policy_area": bill_info.get("policyArea", {}).get("name", ""),
                    "chamber": "Senate",
                    "cbo_deficit_impact": None,
                })

        elif chamber == "House of Representatives":
            # Match House votes by bioguide ID (Congress.gov API provides bioguide IDs)
            for vote in house_votes:
                matched = None
                for mv in vote.get("members", []):
                    if mv.get("bioguide_id", "") == bioguide_id:
                        matched = mv
                        break
                if not matched:
                    continue

                doc = vote.get("document", "")
                bill_ref = _parse_bill_ref(doc)
                bill_info = bill_lookup.get(bill_ref, {}) if bill_ref else {}

                member_vote_list.append({
                    "bill_number": doc,
                    "bill_id": f"119-{bill_ref}" if bill_ref else None,
                    "one_liner": bill_info.get("title", doc),
                    "vote": matched.get("vote", ""),
                    "date": vote.get("vote_date", ""),
                    "result": vote.get("result", ""),
                    "policy_area": bill_info.get("policyArea", {}).get("name", ""),
                    "chamber": "House",
                    "cbo_deficit_impact": None,
                })

        # Compute stats
        yea = sum(1 for v in member_vote_list if v["vote"] in ("Yea", "Aye"))
        nay = sum(1 for v in member_vote_list if v["vote"] in ("Nay", "No"))
        not_voting = sum(1 for v in member_vote_list if v["vote"] == "Not Voting")
        total = len(member_vote_list)
        participation = round((yea + nay) / total * 100, 1) if total > 0 else 0

        policy_areas = sorted(set(v["policy_area"] for v in member_vote_list if v["policy_area"]))

        record = {
            "member_id": bioguide_id,
            "congress": 119,
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
        _atomic_write_json(member_votes_dir / f"{bioguide_id}.json", record)
        count += 1

    print(f"  Built voting records for {count} members")
    return count
```

**Step 4: Run all member vote tests**

Run: `pytest tests/test_sync.py -k "build_member" -v`
Expected: All PASS (old Senate test + new House tests)

**Step 5: Run all tests**

Run: `pytest tests/test_sync.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: build_member_votes handles both Senate and House chambers"
```

---

### Task 5: Update `main()` pipeline to include House votes

**Files:**
- Modify: `sync.py:289-351` (main function)
- Test: `tests/test_sync.py`

**Step 1: Update `main()` to 5-step pipeline**

Replace `main()` in `sync.py`:

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
    print("[1/5] Syncing members...")
    members_count = await sync_members(client, SYNC_DIR, states=states, rate_limit=0.5)

    # Step 2: Senate votes
    print()
    senate_service = SenateVoteService(cache=cache)
    print("[2/5] Syncing Senate votes...")
    senate_count = await sync_senate_votes(senate_service, SYNC_DIR, rate_limit=0.3)

    # Step 3: House votes
    print()
    print("[3/5] Syncing House votes...")
    house_count = await sync_house_votes(client, SYNC_DIR, rate_limit=0.3)

    # Step 4: Bills (only those referenced in votes from both chambers)
    print()
    print("[4/5] Syncing voted-on bills...")
    bills_count = await sync_bills_from_votes(client, SYNC_DIR, rate_limit=0.5)

    # Step 5: Member voting records (both chambers)
    print()
    print("[5/5] Building member voting records...")
    member_votes_count = await build_member_votes(SYNC_DIR)

    # Write metadata
    metadata = {
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "states_synced": states or US_STATES,
        "members_count": members_count,
        "bills_count": bills_count,
        "senate_votes_count": senate_count,
        "house_votes_count": house_count,
        "member_votes_count": member_votes_count,
    }
    _atomic_write_json(SYNC_DIR / "sync_metadata.json", metadata)
    print()
    print("=== Sync complete ===")
    print(f"  Members: {members_count}")
    print(f"  Bills: {bills_count}")
    print(f"  Senate votes: {senate_count}")
    print(f"  House votes: {house_count}")
    print(f"  Member vote records: {member_votes_count}")
```

**Step 2: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 3: Commit**

```bash
git add sync.py
git commit -m "feat: update main() to 5-step pipeline with House votes"
```

---

### Task 6: Run sync and verify House data

**Step 1: Run the sync**

```bash
cd /Users/josephgarcia/Documents/Claude/Projects/clearvote
source .venv/bin/activate
python sync.py --states NY,FL,CA,TX
```

Expected: 5-step pipeline runs, House votes are fetched (incremental — Senate votes already exist).

**Step 2: Verify synced data**

```bash
cat data/synced/sync_metadata.json
ls data/synced/votes/house/ | head -10
ls data/synced/votes/house/ | wc -l
ls data/synced/member_votes/ | wc -l
```

Expected:
- `sync_metadata.json` shows `house_votes_count` > 0
- `votes/house/` has vote JSON files
- `member_votes/` has 80 files (8 senators + 72 house reps)

**Step 3: Spot-check a House member's vote record**

```bash
python3 -c "
import json
# Pick a known House member and check their votes
import os
for f in sorted(os.listdir('data/synced/member_votes/'))[:3]:
    data = json.load(open(f'data/synced/member_votes/{f}'))
    print(f'{f}: {data[\"stats\"][\"total_votes\"]} votes, {data[\"stats\"][\"participation_rate\"]}% participation')
"
```

**Step 4: Commit synced data**

```bash
git add data/synced/
git commit -m "data: sync House votes for NY, FL, CA, TX — all 80 members now have vote records"
```

---

### Task 7: Generate AI summaries for new bills

**Step 1: Check for bills without AI summaries**

```bash
python3 -c "
import json
bills = json.load(open('data/synced/bills.json'))['bills']
ai = json.load(open('data/synced/ai_summaries.json'))
missing = []
for b in bills:
    key = f\"{b.get('congress', 119)}-{b.get('type','').lower()}-{b.get('number','')}\"
    if key not in ai:
        missing.append((key, b.get('title', 'Unknown')))
print(f'{len(missing)} bills need AI summaries')
for key, title in missing[:10]:
    print(f'  {key}: {title}')
"
```

**Step 2: Generate summaries**

For each bill missing an AI summary, generate a plain-language summary following the existing format in `ai_summaries.json`:
- Read the bill title and official CRS summary
- Write 3-7 provisions per bill
- No adjectives, no value judgments, no political framing
- 7th-8th grade reading level
- Specific numbers and dates
- Use impact categories from: Taxation, Healthcare, Defense, Immigration, Economy, Environment, Education, Government Operations, Social Policy, Infrastructure, Foreign Affairs, Criminal Justice, Civil Rights, Agriculture, Technology, Labor, Housing, Veterans, Energy

**Step 3: Write to `ai_summaries.json`**

Merge new summaries into existing file (read, merge, write).

**Step 4: Commit**

```bash
git add data/synced/ai_summaries.json
git commit -m "data: AI summaries for House-referenced bills"
```

---

## Files Touched

| File | Change |
|------|--------|
| `sync.py` | Add `sync_house_votes()`, `_house_leg_to_document()`, expand `_parse_bill_ref()`, expand `sync_bills_from_votes()`, rewrite `build_member_votes()`, update `main()` |
| `tests/test_sync.py` | Add tests for House vote sync, House bill ref parsing, both-chamber member votes |
| `data/synced/votes/house/` | New directory with House vote JSON files |
| `data/synced/member_votes/` | Grows from 8 to 80 files |
| `data/synced/bills.json` | May grow with House-only bill references |
| `data/synced/ai_summaries.json` | Summaries for any new bills |

## Tests

| Type | Scope | Validates |
|------|-------|-----------|
| Unit | `test_sync_house_votes` | House votes are fetched, normalized, saved as JSON |
| Unit | `test_sync_house_votes_skips_existing` | Incremental sync skips existing files |
| Unit | `test_sync_house_votes_rate_limiting` | Rate limiting works |
| Unit | `test_house_leg_to_document` | Legislation type conversion |
| Unit | `test_parse_bill_ref_house_resolutions` | Parsing of H.Res., H.Con.Res., etc. |
| Unit | `test_sync_bills_from_votes_includes_house` | Bills scanned from both chambers |
| Unit | `test_build_member_votes_house` | House members get vote records |
| Unit | `test_build_member_votes_both_chambers` | Both chambers produce records simultaneously |

## Not In Scope

- **Frontend changes** — member profile page already displays vote records regardless of chamber
- **House-specific vote parsing service** — using Congress.gov API directly (no XML parsing needed)
- **Expanding beyond 4 states** — separate task
- **Historical congresses** — only syncing 119th Congress
