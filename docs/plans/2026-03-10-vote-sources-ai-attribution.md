# Vote Source Links & AI Attribution Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add roll call source links on each vote (linking to Senate.gov/House.gov) and an AI attribution note under narrative summaries.

**Architecture:** Carry `vote_number` and `session` from raw vote files through to member vote records during sync. Frontend constructs source URLs from these fields. AI attribution is a static text note appended after the narrative paragraph.

**Tech Stack:** Python (sync.py, data_service.py), vanilla JS (member.js), CSS (styles.css)

---

## Task 1: Add vote_number and session to member vote records

**Files:**
- Modify: `sync.py:528-540` (Senate vote entry)
- Modify: `sync.py:559-571` (House vote entry)
- Test: `tests/test_sync.py`

- [ ] **Step 1: Write failing test for Senate vote entry fields**

Add to `tests/test_sync.py`:

```python
def test_member_votes_include_vote_number_and_session(tmp_path, mocker):
    """Member vote records should carry vote_number and session from raw vote data."""
    # Create a minimal Senate vote file
    vote_dir = tmp_path / "votes" / "senate"
    vote_dir.mkdir(parents=True)
    vote_file = vote_dir / "119_1_00042.json"
    vote_file.write_text(json.dumps({
        "congress": 119,
        "session": 1,
        "vote_number": 42,
        "vote_date": "2025-03-15",
        "question": "On the Motion",
        "document": "S. 100",
        "result": "Passed (60-40)",
        "title": "Test Bill",
        "counts": {"yeas": 60, "nays": 40, "present": 0, "absent": 0},
        "members": [
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea", "lis_member_id": "S428"}
        ]
    }))

    # Create members.json with matching member
    members_file = tmp_path / "members.json"
    members_file.write_text(json.dumps({"members": [
        {"bioguideId": "S001217", "name": "Scott, Rick", "directOrderName": "Rick Scott",
         "state": "Florida", "stateCode": "FL", "chamber": "Senate",
         "terms": {"item": [{"chamber": "Senate"}]},
         "depiction": None}
    ]}))

    # Create empty bills and summaries
    (tmp_path / "bills.json").write_text('{"bills": []}')
    (tmp_path / "bill_summaries.json").write_text('{}')

    # Run build
    import asyncio
    from sync import build_member_votes
    asyncio.run(build_member_votes(tmp_path))

    # Check output
    mv_path = tmp_path / "member_votes" / "S001217.json"
    assert mv_path.exists()
    data = json.loads(mv_path.read_text())
    vote = data["votes"][0]
    assert vote["vote_number"] == 42
    assert vote["session"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && python -m pytest tests/test_sync.py::test_member_votes_include_vote_number_and_session -v`
Expected: FAIL — `KeyError: 'vote_number'`

- [ ] **Step 3: Add vote_number and session to Senate vote entries**

In `sync.py`, find the Senate `member_vote_list.append({` block (~line 528) and add two fields:

```python
member_vote_list.append({
    "bill_number": doc,
    "bill_id": f"{vote_congress}-{bill_ref}" if bill_ref else None,
    "one_liner": _get_one_liner(bill_ref, bill_info, doc, congress=vote_congress),
    "vote": matched.get("vote", ""),
    "date": vote.get("vote_date", ""),
    "result": vote.get("result", ""),
    "policy_area": bill_info.get("policyArea", {}).get("name", ""),
    "chamber": "Senate",
    "cbo_deficit_impact": None,
    "direction": _get_direction(bill_ref, congress=vote_congress),
    "congress": vote_congress,
    "session": vote.get("session", 1),           # NEW
    "vote_number": vote.get("vote_number", 0),    # NEW
})
```

- [ ] **Step 4: Add vote_number and session to House vote entries**

In `sync.py`, find the House `member_vote_list.append({` block (~line 559) and add the same two fields:

```python
member_vote_list.append({
    "bill_number": doc,
    "bill_id": f"{vote_congress}-{bill_ref}" if bill_ref else None,
    "one_liner": _get_one_liner(bill_ref, bill_info, doc, congress=vote_congress),
    "vote": matched.get("vote", ""),
    "date": vote.get("vote_date", ""),
    "result": vote.get("result", ""),
    "policy_area": bill_info.get("policyArea", {}).get("name", ""),
    "chamber": "House",
    "cbo_deficit_impact": None,
    "direction": _get_direction(bill_ref, congress=vote_congress),
    "congress": vote_congress,
    "session": vote.get("session", 1),           # NEW
    "vote_number": vote.get("vote_number", 0),    # NEW
})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `source .venv/bin/activate && python -m pytest tests/test_sync.py -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add sync.py tests/test_sync.py
git commit -m "feat: carry vote_number and session through to member vote records"
```

---

## Task 2: Re-sync member votes to populate new fields

- [ ] **Step 1: Delete existing member_votes to force rebuild**

```bash
rm -rf data/synced/member_votes/
```

- [ ] **Step 2: Run sync step 5 only (build member votes)**

```bash
source .venv/bin/activate && python sync.py --states NY,FL,CA,TX --skip-to 5 --stop-after 5
```

Note: If `--skip-to` / `--stop-after` flags don't exist, run the full sync. The raw vote data is already downloaded so steps 1-4 will be fast (incremental skips).

- [ ] **Step 3: Verify new fields in output**

```bash
python3 -c "import json; d=json.load(open('data/synced/member_votes/S001217.json')); v=d['votes'][0]; print(v.get('vote_number'), v.get('session'))"
```

Expected: Two numbers (e.g., `42 1`)

- [ ] **Step 4: Commit synced data**

```bash
git add data/synced/member_votes/
git commit -m "data: re-sync member votes with vote_number and session fields"
```

---

## Task 3: Render source links on votes in the frontend

**Files:**
- Modify: `static/js/member.js:630-681` (`_renderVoteItems` function)
- Modify: `static/css/styles.css` (add `.vote-source-link` style)

- [ ] **Step 1: Add source link construction helper to member.js**

Add before `_renderVoteItems`:

```javascript
function getSourceUrl(vote) {
    if (!vote.vote_number || !vote.session) return null;
    const c = vote.congress || 119;
    const s = vote.session;
    const vn = vote.vote_number;
    if (vote.chamber === 'Senate') {
        const pad = String(vn).padStart(5, '0');
        return `https://www.senate.gov/legislative/LIS/roll_call_votes/vote${c}${s}/vote_${c}_${s}_${pad}.htm`;
    }
    if (vote.chamber === 'House') {
        const year = vote.date ? vote.date.slice(0, 4) : '2025';
        return `https://clerk.house.gov/Votes/${year}${vn}`;
    }
    return null;
}
```

- [ ] **Step 2: Add source link to each vote item in `_renderVoteItems`**

In `_renderVoteItems`, after `item.appendChild(bottomRow)` and before the bill detail link block, add:

```javascript
        const sourceUrl = getSourceUrl(vote);
        if (sourceUrl) {
            const sourceLink = el('a', {
                className: 'vote-source-link',
                href: sourceUrl,
                target: '_blank',
                rel: 'noopener',
            }, 'Roll call source →');
            sourceLink.addEventListener('click', (e) => e.stopPropagation());
            item.appendChild(sourceLink);
        }
```

- [ ] **Step 3: Add CSS for the source link**

Add to `static/css/styles.css` after the `.vote-item-bottom` styles:

```css
.vote-source-link {
    display: inline-block;
    margin-top: 0.4rem;
    font-size: 0.75rem;
    color: var(--text-dim);
    text-decoration: none;
}

.vote-source-link:hover {
    color: var(--accent);
    text-decoration: underline;
}
```

- [ ] **Step 4: Verify locally**

Run the app and check that Senate votes show links to senate.gov and House votes show links to clerk.house.gov.

- [ ] **Step 5: Commit**

```bash
git add static/js/member.js static/css/styles.css
git commit -m "feat: add roll call source links to vote items"
```

---

## Task 4: Add AI attribution to narrative summaries

**Files:**
- Modify: `static/js/member.js:388-392` (narrative rendering)
- Modify: `static/css/styles.css` (add `.ai-attribution` style)

- [ ] **Step 1: Add attribution note after narrative in member.js**

Replace the narrative rendering block (~line 388-392):

```javascript
    // AI narrative (if available)
    if (summaryData && summaryData.narrative) {
        const narrative = el('p', { className: 'summary-narrative' }, summaryData.narrative);
        card.appendChild(narrative);
        card.appendChild(el('p', { className: 'ai-attribution' },
            'Summary generated by AI from official voting record data.'));
    }
```

- [ ] **Step 2: Add CSS for the attribution note**

Add to `static/css/styles.css`:

```css
.ai-attribution {
    font-size: 0.75rem;
    color: var(--text-dim);
    font-style: italic;
    margin-top: -0.25rem;
    margin-bottom: 0.75rem;
}
```

- [ ] **Step 3: Verify locally**

Run the app, navigate to a member profile, confirm the note appears below the narrative.

- [ ] **Step 4: Commit**

```bash
git add static/js/member.js static/css/styles.css
git commit -m "feat: add AI attribution note under narrative summaries"
```

---

## Task 5: Final verification and push

- [ ] **Step 1: Run all tests**

```bash
source .venv/bin/activate && python -m pytest tests/ -x -q
```

Expected: All pass

- [ ] **Step 2: Push to main**

```bash
git push
```

Render auto-deploys from main.
