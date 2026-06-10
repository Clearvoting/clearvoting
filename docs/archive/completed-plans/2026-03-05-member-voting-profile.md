# Member Voting Profile Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a full voting profile (stats, recent key votes, issue filtering) to the member detail page so users can see how their congressman votes.

**Architecture:** New `/api/members/{id}/votes` endpoint returns voting stats + recent votes with AI one-liners. Mock data for demo mode covers 4 FL members with 15-20 real votes each. Frontend renders stats as donut charts (reusing vote.js), vote list as styled cards, and issue chips for client-side filtering.

**Tech Stack:** Python/FastAPI backend, vanilla HTML/CSS/JS frontend, existing ClearVote design system (midnight blue + gold), existing vote.js chart components.

---

### Task 1: Mock Voting Data for FL Members

**Files:**
- Modify: `app/services/mock_data.py`

**Step 1: Add mock member votes data**

Add a new `MOCK_MEMBER_VOTES` dictionary at the end of the file (before the accessor functions). This contains voting records for each FL demo member. Each entry has stats and a list of 15-20 votes based on real 119th Congress votes.

```python
# --- Member Voting Records (119th Congress) ---

MOCK_MEMBER_VOTES = {
    "S001217": {  # Rick Scott
        "member_id": "S001217",
        "congress": 119,
        "stats": {
            "total_votes": 187,
            "yea_count": 112,
            "nay_count": 67,
            "not_voting_count": 8,
            "participation_rate": 95.7,
        },
        "votes": [
            {
                "bill_number": "H.R. 1",
                "bill_title": "One Big Beautiful Bill Act",
                "one_liner": "Combines tax cut extensions, border security funding, defense spending increases, and changes to Medicaid and social safety net programs into one package.",
                "vote": "Yea",
                "date": "2025-07-01",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1,
            },
            {
                "bill_number": "H.R. 4",
                "bill_title": "Rescissions Package",
                "one_liner": "Rescinds $8 billion from State Department and USAID programs and $1.1 billion from the Corporation for Public Broadcasting which funds NPR and PBS.",
                "vote": "Yea",
                "date": "2025-07-17",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 4,
            },
            {
                "bill_number": "H.R. 6938",
                "bill_title": "Commerce, Justice, Science Appropriations Act, 2026",
                "one_liner": "Funds the Departments of Commerce, Justice, and Science programs, plus Energy, Water, Interior, and Environment agencies for fiscal year 2026.",
                "vote": "Nay",
                "date": "2026-01-15",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6938,
            },
            {
                "bill_number": "S.Amdt. 4236",
                "bill_title": "Lee Amendment to Strike Earmarks",
                "one_liner": "Amendment to remove all earmarks from the FY2026 government funding bill.",
                "vote": "Yea",
                "date": "2026-01-30",
                "result": "Failed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "SAMDT",
                "bill_number_raw": 4236,
            },
            {
                "bill_number": "H.R. 4494",
                "bill_title": "National Flood Insurance Program Extension Act of 2025",
                "one_liner": "Extends the National Flood Insurance Program authorization through September 2029 and increases maximum coverage limits from $250,000 to $500,000 for residential properties.",
                "vote": "Yea",
                "date": "2025-06-12",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Housing",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 4494,
            },
            {
                "bill_number": "S. 770",
                "bill_title": "Social Security Fairness Act",
                "one_liner": "Eliminates the Windfall Elimination Provision and the Government Pension Offset, which currently reduce Social Security benefits for people who also receive public pensions.",
                "vote": "Yea",
                "date": "2025-03-18",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Social Security & Medicare",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 770,
            },
            {
                "bill_number": "S. 219",
                "bill_title": "Veterans' COLA Act of 2025",
                "one_liner": "Increases veterans' disability compensation and survivor benefits by the same percentage as the Social Security cost-of-living adjustment for 2026.",
                "vote": "Yea",
                "date": "2025-05-08",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Military & Veterans",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 219,
            },
            {
                "bill_number": "H.R. 152",
                "bill_title": "Disaster Relief Supplemental Appropriations Act",
                "one_liner": "Provides $100 billion in emergency funding for communities affected by Hurricanes Helene and Milton, including FEMA assistance, SBA loans, and infrastructure repair.",
                "vote": "Yea",
                "date": "2025-03-28",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Infrastructure",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 152,
            },
            {
                "bill_number": "H.R. 1040",
                "bill_title": "REAL ID Modernization Act",
                "one_liner": "Extends the REAL ID enforcement deadline to May 2027 and allows states to issue mobile driver's licenses that meet federal identification standards.",
                "vote": "Yea",
                "date": "2025-04-22",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1040,
            },
            {
                "bill_number": "S. 1182",
                "bill_title": "HALT Fentanyl Act",
                "one_liner": "Permanently classifies fentanyl-related substances as Schedule I controlled substances and increases penalties for trafficking fentanyl analogs.",
                "vote": "Yea",
                "date": "2025-05-22",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Criminal Justice",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 1182,
            },
            {
                "bill_number": "S. 2341",
                "bill_title": "Laken Riley Act",
                "one_liner": "Requires federal immigration authorities to detain undocumented immigrants charged with theft or violent crimes and allows state attorneys general to sue the federal government over immigration enforcement.",
                "vote": "Yea",
                "date": "2025-01-29",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Immigration",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 2341,
            },
            {
                "bill_number": "S. 3100",
                "bill_title": "NDAA FY2026",
                "one_liner": "Authorizes $923 billion for defense programs, a 3.8% military pay raise, and bans the Department of Defense from buying computers and solar panels made in China.",
                "vote": "Yea",
                "date": "2025-12-10",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Defense",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 3100,
            },
            {
                "bill_number": "S. 890",
                "bill_title": "TikTok Ban Extension Act",
                "one_liner": "Extends the deadline for ByteDance to divest TikTok's US operations by 270 days, from April 2025 to January 2026.",
                "vote": "Yea",
                "date": "2025-04-05",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Technology",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 890,
            },
            {
                "bill_number": "S. 1455",
                "bill_title": "No Taxpayer Funding for Abortion Act",
                "one_liner": "Prohibits the use of federal funds for abortion services except in cases of rape, incest, or when the life of the mother is at risk.",
                "vote": "Yea",
                "date": "2025-06-04",
                "result": "Failed",
                "chamber": "Senate",
                "policy_area": "Healthcare",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 1455,
            },
            {
                "bill_number": "S. 2012",
                "bill_title": "Federal Debt Transparency Act",
                "one_liner": "Requires the Treasury Department to publish a daily public dashboard showing the national debt, interest payments, and projected debt trajectory for the next 10 years.",
                "vote": "Yea",
                "date": "2025-08-14",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Economy",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 2012,
            },
            {
                "bill_number": "H.R. 318",
                "bill_title": "No Tax on Tips Act",
                "one_liner": "Exempts cash tips from federal income tax for workers in occupations that customarily receive tips, with an annual cap of $25,000.",
                "vote": "Yea",
                "date": "2025-05-15",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 318,
            },
        ],
        "policy_areas": ["Taxes", "Government Operations", "Defense", "Immigration", "Healthcare", "Housing", "Social Security & Medicare", "Military & Veterans", "Infrastructure", "Criminal Justice", "Technology", "Economy"],
    },
    "M001244": {  # Ashley Moody
        "member_id": "M001244",
        "congress": 119,
        "stats": {
            "total_votes": 187,
            "yea_count": 118,
            "nay_count": 63,
            "not_voting_count": 6,
            "participation_rate": 96.8,
        },
        "votes": [
            {
                "bill_number": "H.R. 1",
                "bill_title": "One Big Beautiful Bill Act",
                "one_liner": "Combines tax cut extensions, border security funding, defense spending increases, and changes to Medicaid and social safety net programs into one package.",
                "vote": "Yea",
                "date": "2025-07-01",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1,
            },
            {
                "bill_number": "S. 2341",
                "bill_title": "Laken Riley Act",
                "one_liner": "Requires federal immigration authorities to detain undocumented immigrants charged with theft or violent crimes and allows state attorneys general to sue the federal government over immigration enforcement.",
                "vote": "Yea",
                "date": "2025-01-29",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Immigration",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 2341,
            },
            {
                "bill_number": "S. 770",
                "bill_title": "Social Security Fairness Act",
                "one_liner": "Eliminates the Windfall Elimination Provision and the Government Pension Offset, which currently reduce Social Security benefits for people who also receive public pensions.",
                "vote": "Yea",
                "date": "2025-03-18",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Social Security & Medicare",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 770,
            },
            {
                "bill_number": "H.R. 4",
                "bill_title": "Rescissions Package",
                "one_liner": "Rescinds $8 billion from State Department and USAID programs and $1.1 billion from the Corporation for Public Broadcasting which funds NPR and PBS.",
                "vote": "Yea",
                "date": "2025-07-17",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 4,
            },
            {
                "bill_number": "H.R. 6938",
                "bill_title": "Commerce, Justice, Science Appropriations Act, 2026",
                "one_liner": "Funds the Departments of Commerce, Justice, and Science programs, plus Energy, Water, Interior, and Environment agencies for fiscal year 2026.",
                "vote": "Yea",
                "date": "2026-01-15",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6938,
            },
            {
                "bill_number": "S. 3100",
                "bill_title": "NDAA FY2026",
                "one_liner": "Authorizes $923 billion for defense programs, a 3.8% military pay raise, and bans the Department of Defense from buying computers and solar panels made in China.",
                "vote": "Yea",
                "date": "2025-12-10",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Defense",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 3100,
            },
            {
                "bill_number": "H.R. 152",
                "bill_title": "Disaster Relief Supplemental Appropriations Act",
                "one_liner": "Provides $100 billion in emergency funding for communities affected by Hurricanes Helene and Milton, including FEMA assistance, SBA loans, and infrastructure repair.",
                "vote": "Yea",
                "date": "2025-03-28",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Infrastructure",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 152,
            },
            {
                "bill_number": "H.R. 318",
                "bill_title": "No Tax on Tips Act",
                "one_liner": "Exempts cash tips from federal income tax for workers in occupations that customarily receive tips, with an annual cap of $25,000.",
                "vote": "Yea",
                "date": "2025-05-15",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 318,
            },
            {
                "bill_number": "S. 1182",
                "bill_title": "HALT Fentanyl Act",
                "one_liner": "Permanently classifies fentanyl-related substances as Schedule I controlled substances and increases penalties for trafficking fentanyl analogs.",
                "vote": "Yea",
                "date": "2025-05-22",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Criminal Justice",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 1182,
            },
            {
                "bill_number": "S. 219",
                "bill_title": "Veterans' COLA Act of 2025",
                "one_liner": "Increases veterans' disability compensation and survivor benefits by the same percentage as the Social Security cost-of-living adjustment for 2026.",
                "vote": "Yea",
                "date": "2025-05-08",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Military & Veterans",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 219,
            },
        ],
        "policy_areas": ["Taxes", "Government Operations", "Defense", "Immigration", "Social Security & Medicare", "Military & Veterans", "Infrastructure", "Criminal Justice"],
    },
    "D000032": {  # Byron Donalds
        "member_id": "D000032",
        "congress": 119,
        "stats": {
            "total_votes": 234,
            "yea_count": 155,
            "nay_count": 71,
            "not_voting_count": 8,
            "participation_rate": 96.6,
        },
        "votes": [
            {
                "bill_number": "H.R. 1",
                "bill_title": "One Big Beautiful Bill Act",
                "one_liner": "Combines tax cut extensions, border security funding, defense spending increases, and changes to Medicaid and social safety net programs into one package.",
                "vote": "Yea",
                "date": "2025-05-22",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1,
            },
            {
                "bill_number": "H.R. 4494",
                "bill_title": "National Flood Insurance Program Extension Act of 2025",
                "one_liner": "Extends the National Flood Insurance Program authorization through September 2029 and increases maximum coverage limits from $250,000 to $500,000 for residential properties.",
                "vote": "Yea",
                "date": "2025-06-12",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Housing",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 4494,
            },
            {
                "bill_number": "H.R. 152",
                "bill_title": "Disaster Relief Supplemental Appropriations Act",
                "one_liner": "Provides $100 billion in emergency funding for communities affected by Hurricanes Helene and Milton, including FEMA assistance, SBA loans, and infrastructure repair.",
                "vote": "Yea",
                "date": "2025-03-14",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Infrastructure",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 152,
            },
            {
                "bill_number": "H.R. 318",
                "bill_title": "No Tax on Tips Act",
                "one_liner": "Exempts cash tips from federal income tax for workers in occupations that customarily receive tips, with an annual cap of $25,000.",
                "vote": "Yea",
                "date": "2025-04-30",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 318,
            },
            {
                "bill_number": "H.R. 5484",
                "bill_title": "Securing the Border for America Act",
                "one_liner": "Adds 22,000 Border Patrol agents over 5 years, requires completion of border wall construction, and mandates the Remain in Mexico policy for asylum seekers.",
                "vote": "Yea",
                "date": "2025-02-04",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Immigration",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 5484,
            },
            {
                "bill_number": "H.R. 1040",
                "bill_title": "REAL ID Modernization Act",
                "one_liner": "Extends the REAL ID enforcement deadline to May 2027 and allows states to issue mobile driver's licenses that meet federal identification standards.",
                "vote": "Yea",
                "date": "2025-04-10",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1040,
            },
            {
                "bill_number": "H.R. 6017",
                "bill_title": "SAVE Act",
                "one_liner": "Requires proof of US citizenship to register to vote in federal elections and directs states to remove noncitizens from voter rolls within 90 days.",
                "vote": "Yea",
                "date": "2025-02-27",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6017,
            },
            {
                "bill_number": "H.R. 6934",
                "bill_title": "Parents Bill of Rights Act",
                "one_liner": "Requires schools to publish curricula and reading lists, notify parents of violent incidents, and obtain consent before surveys collecting personal information from students.",
                "vote": "Yea",
                "date": "2025-03-06",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Education",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6934,
            },
        ],
        "policy_areas": ["Taxes", "Government Operations", "Immigration", "Housing", "Infrastructure", "Education"],
    },
    "W000823": {  # Michael Waltz
        "member_id": "W000823",
        "congress": 119,
        "stats": {
            "total_votes": 234,
            "yea_count": 148,
            "nay_count": 76,
            "not_voting_count": 10,
            "participation_rate": 95.7,
        },
        "votes": [
            {
                "bill_number": "H.R. 1",
                "bill_title": "One Big Beautiful Bill Act",
                "one_liner": "Combines tax cut extensions, border security funding, defense spending increases, and changes to Medicaid and social safety net programs into one package.",
                "vote": "Yea",
                "date": "2025-05-22",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1,
            },
            {
                "bill_number": "H.R. 5484",
                "bill_title": "Securing the Border for America Act",
                "one_liner": "Adds 22,000 Border Patrol agents over 5 years, requires completion of border wall construction, and mandates the Remain in Mexico policy for asylum seekers.",
                "vote": "Yea",
                "date": "2025-02-04",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Immigration",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 5484,
            },
            {
                "bill_number": "H.R. 152",
                "bill_title": "Disaster Relief Supplemental Appropriations Act",
                "one_liner": "Provides $100 billion in emergency funding for communities affected by Hurricanes Helene and Milton, including FEMA assistance, SBA loans, and infrastructure repair.",
                "vote": "Yea",
                "date": "2025-03-14",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Infrastructure",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 152,
            },
            {
                "bill_number": "H.R. 318",
                "bill_title": "No Tax on Tips Act",
                "one_liner": "Exempts cash tips from federal income tax for workers in occupations that customarily receive tips, with an annual cap of $25,000.",
                "vote": "Yea",
                "date": "2025-04-30",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 318,
            },
            {
                "bill_number": "H.R. 6934",
                "bill_title": "Parents Bill of Rights Act",
                "one_liner": "Requires schools to publish curricula and reading lists, notify parents of violent incidents, and obtain consent before surveys collecting personal information from students.",
                "vote": "Yea",
                "date": "2025-03-06",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Education",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6934,
            },
            {
                "bill_number": "H.R. 1040",
                "bill_title": "REAL ID Modernization Act",
                "one_liner": "Extends the REAL ID enforcement deadline to May 2027 and allows states to issue mobile driver's licenses that meet federal identification standards.",
                "vote": "Yea",
                "date": "2025-04-10",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1040,
            },
            {
                "bill_number": "H.R. 6017",
                "bill_title": "SAVE Act",
                "one_liner": "Requires proof of US citizenship to register to vote in federal elections and directs states to remove noncitizens from voter rolls within 90 days.",
                "vote": "Yea",
                "date": "2025-02-27",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6017,
            },
        ],
        "policy_areas": ["Taxes", "Government Operations", "Immigration", "Infrastructure", "Education"],
    },
}
```

**Step 2: Add accessor function for member votes**

Add after the existing accessor functions:

```python
def get_mock_member_votes(bioguide_id: str) -> dict | None:
    """Return mock voting record for a member in demo mode."""
    return MOCK_MEMBER_VOTES.get(bioguide_id)
```

**Step 3: Run existing tests to make sure nothing breaks**

Run: `cd ~/Documents/Claude/Projects/clearvote && /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest tests/ -v`
Expected: All existing tests PASS

**Step 4: Commit**

```bash
git add app/services/mock_data.py
git commit -m "feat(votes): add mock member voting records for FL demo members"
```

---

### Task 2: Member Votes API Endpoint

**Files:**
- Modify: `app/routers/members.py`
- Create: `tests/test_member_votes.py`

**Step 1: Write the failing test**

```python
# tests/test_member_votes.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_get_member_votes_demo_mode():
    """Demo mode returns mock voting data for known FL members."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/S001217/votes")

    assert response.status_code == 200
    data = response.json()
    assert data["member_id"] == "S001217"
    assert "stats" in data
    assert data["stats"]["total_votes"] > 0
    assert data["stats"]["participation_rate"] > 0
    assert "votes" in data
    assert len(data["votes"]) > 0
    assert "policy_areas" in data

    # Verify vote structure
    vote = data["votes"][0]
    assert "bill_number" in vote
    assert "one_liner" in vote
    assert "vote" in vote
    assert vote["vote"] in ("Yea", "Nay", "Not Voting")
    assert "date" in vote
    assert "result" in vote
    assert "policy_area" in vote


@pytest.mark.asyncio
async def test_get_member_votes_unknown_member():
    """Unknown member returns 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/UNKNOWN123/votes")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_member_votes_sorted_by_date():
    """Votes should be returned in reverse chronological order."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/S001217/votes")

    data = response.json()
    dates = [v["date"] for v in data["votes"]]
    assert dates == sorted(dates, reverse=True), "Votes should be sorted newest first"
```

**Step 2: Run test to verify it fails**

Run: `cd ~/Documents/Claude/Projects/clearvote && /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest tests/test_member_votes.py -v`
Expected: FAIL (endpoint doesn't exist yet)

**Step 3: Write the endpoint**

Add to `app/routers/members.py`:

```python
from app.services.mock_data import get_mock_members, get_mock_member_detail, get_mock_member_votes
```

And add the new endpoint (MUST be placed BEFORE the `/{state_code}` catch-all route):

```python
@router.get("/{bioguide_id}/votes")
async def get_member_votes(bioguide_id: str, congress: int = 119, limit: int = 20, offset: int = 0):
    if _is_demo():
        mock = get_mock_member_votes(bioguide_id)
        if not mock:
            raise HTTPException(status_code=404, detail="Member not found")
        # Sort votes by date descending
        sorted_votes = sorted(mock["votes"], key=lambda v: v["date"], reverse=True)
        paginated = sorted_votes[offset:offset + limit]
        return {
            "member_id": mock["member_id"],
            "congress": mock["congress"],
            "stats": mock["stats"],
            "votes": paginated,
            "policy_areas": mock["policy_areas"],
        }

    # Real mode: TODO — fetch from Congress API + Senate XML
    raise HTTPException(status_code=501, detail="Real-mode voting records not yet implemented")
```

**Important:** This endpoint path `/{bioguide_id}/votes` will conflict with `/{state_code}` if not ordered correctly. Place it BEFORE `/{state_code}` in the router, OR use a more specific path. The safest approach: reorder routes so `/{bioguide_id}/votes` is declared before `/{state_code}`.

**Step 4: Run test to verify it passes**

Run: `cd ~/Documents/Claude/Projects/clearvote && /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest tests/test_member_votes.py -v`
Expected: All 3 tests PASS

**Step 5: Run all tests**

Run: `cd ~/Documents/Claude/Projects/clearvote && /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add app/routers/members.py tests/test_member_votes.py
git commit -m "feat(votes): add GET /api/members/{id}/votes endpoint with demo mode"
```

---

### Task 3: Frontend — Voting Stats Section

**Files:**
- Modify: `static/member.html` (add vote.js script tag)
- Modify: `static/js/member.js` (add voting stats rendering)

**Step 1: Add vote.js to member.html**

In `static/member.html`, add the vote.js script BEFORE member.js:

```html
    <script src="/static/js/vote.js"></script>
    <script src="/static/js/member.js"></script>
```

**Step 2: Add voting stats rendering to member.js**

Add a new function `loadVotingRecord` and a renderer `renderVotingStats`. Call `loadVotingRecord(bioguideId)` at the end of `renderMember()`, before the source link.

```javascript
// --- Voting Record ---

async function loadVotingRecord(bioguideId) {
    const container = document.getElementById('voting-record');
    if (!container) return;

    try {
        const response = await fetch(`/api/members/${bioguideId}/votes`);
        if (!response.ok) throw new Error('Failed to load votes');
        const data = await response.json();

        clearEl(container);
        renderVotingStats(container, data.stats);
        renderVoteFilters(container, data.policy_areas, data.votes);
        renderVoteList(container, data.votes);
    } catch (err) {
        clearEl(container);
        container.appendChild(el('div', { className: 'empty-state' }, 'Voting record unavailable.'));
    }
}

function renderVotingStats(container, stats) {
    const section = el('section', { className: 'bill-section' });
    section.appendChild(el('h3', null, 'Voting Statistics'));

    const statsGrid = el('div', { className: 'stats-grid' });

    // Participation donut
    const participationWrapper = el('div', { className: 'stat-card' });
    participationWrapper.appendChild(el('div', { className: 'stat-label' }, 'Participation'));
    const participationChart = window.ClearVoteUI.renderVotePieChart({
        yeas: Math.round(stats.participation_rate),
        nays: Math.round(100 - stats.participation_rate),
    }, 100);
    if (participationChart) participationWrapper.appendChild(participationChart);
    participationWrapper.appendChild(el('div', { className: 'stat-value' }, `${stats.participation_rate}%`));
    statsGrid.appendChild(participationWrapper);

    // Yea/Nay donut
    const voteWrapper = el('div', { className: 'stat-card' });
    voteWrapper.appendChild(el('div', { className: 'stat-label' }, 'Vote Breakdown'));
    const voteChart = window.ClearVoteUI.renderVotePieChart({
        yeas: stats.yea_count,
        nays: stats.nay_count,
        absent: stats.not_voting_count,
    }, 100);
    if (voteChart) voteWrapper.appendChild(voteChart);
    const legend = el('div', { className: 'stat-legend' },
        el('span', null, `Yea: ${stats.yea_count}`),
        el('span', null, ` · Nay: ${stats.nay_count}`),
        el('span', null, ` · Missed: ${stats.not_voting_count}`)
    );
    voteWrapper.appendChild(legend);
    statsGrid.appendChild(voteWrapper);

    // Total votes
    const totalWrapper = el('div', { className: 'stat-card' });
    totalWrapper.appendChild(el('div', { className: 'stat-label' }, 'Total Votes'));
    totalWrapper.appendChild(el('div', { className: 'stat-big-number' }, String(stats.total_votes)));
    totalWrapper.appendChild(el('div', { className: 'stat-sublabel' }, '119th Congress'));
    statsGrid.appendChild(totalWrapper);

    section.appendChild(statsGrid);
    container.appendChild(section);
}
```

**Step 3: Add the voting-record container in renderMember()**

In the `renderMember` function, before the source link, add:

```javascript
    // Voting record (loaded async)
    const votingSection = el('div', { id: 'voting-record' });
    votingSection.appendChild(el('div', { className: 'loading' },
        el('span', { className: 'spinner' }),
        ' Loading voting record...'
    ));
    container.appendChild(votingSection);

    loadVotingRecord(bioguideId);
```

**Step 4: Test manually in browser**

Run: Open `http://localhost:8000` in Safari → select Florida → click Rick Scott
Expected: See voting stats with two donut charts and total votes number below the service history

**Step 5: Commit**

```bash
git add static/member.html static/js/member.js
git commit -m "feat(votes): add voting stats section to member profile page"
```

---

### Task 4: Frontend — Vote List and Issue Filters

**Files:**
- Modify: `static/js/member.js` (add vote list + filter rendering)

**Step 1: Add vote filter rendering**

```javascript
let allVotes = [];  // Module-level variable for filtering

function renderVoteFilters(container, policyAreas, votes) {
    allVotes = votes;
    const section = el('section', { className: 'bill-section' });
    section.appendChild(el('h3', null, 'Voting Record'));

    const filterRow = el('div', { className: 'issue-filters' });

    const allChip = el('button', { className: 'category-tag active', 'data-area': 'all' }, 'All');
    allChip.addEventListener('click', () => filterVotes('all'));
    filterRow.appendChild(allChip);

    policyAreas.forEach(area => {
        const chip = el('button', { className: 'category-tag', 'data-area': area }, area);
        chip.addEventListener('click', () => filterVotes(area));
        filterRow.appendChild(chip);
    });

    section.appendChild(filterRow);
    container.appendChild(section);
}

function filterVotes(area) {
    // Update active chip
    document.querySelectorAll('.issue-filters .category-tag').forEach(c => c.classList.remove('active'));
    const active = document.querySelector(`.issue-filters .category-tag[data-area="${area}"]`);
    if (active) active.classList.add('active');

    const filtered = area === 'all' ? allVotes : allVotes.filter(v => v.policy_area === area);
    const listEl = document.getElementById('vote-list');
    if (listEl) {
        clearEl(listEl);
        _renderVoteItems(listEl, filtered);
    }
}
```

**Step 2: Add vote list rendering**

```javascript
function renderVoteList(container, votes) {
    const listEl = el('div', { id: 'vote-list', className: 'bill-list' });
    _renderVoteItems(listEl, votes);
    container.appendChild(listEl);
}

function _renderVoteItems(listEl, votes) {
    if (votes.length === 0) {
        listEl.appendChild(el('div', { className: 'empty-state' }, 'No votes found for this category.'));
        return;
    }

    votes.forEach(vote => {
        const item = el('div', { className: 'vote-item' });

        const topRow = el('div', { className: 'vote-item-top' });
        topRow.appendChild(el('span', { className: 'bill-number' }, vote.bill_number));
        topRow.appendChild(el('span', { className: 'bill-date' }, vote.date));
        item.appendChild(topRow);

        item.appendChild(el('div', { className: 'vote-item-title' }, vote.bill_title));
        item.appendChild(el('div', { className: 'vote-item-oneliner' }, vote.one_liner));

        const bottomRow = el('div', { className: 'vote-item-bottom' });
        const voteBadge = el('span', { className: 'vote-label ' + vote.vote.toLowerCase().replace(/\s+/g, '-') }, vote.vote);
        bottomRow.appendChild(voteBadge);

        const resultText = vote.result === 'Passed' ? 'Bill Passed' : 'Bill Failed';
        bottomRow.appendChild(el('span', { className: 'vote-item-result' }, resultText));

        const policyTag = el('span', { className: 'impact-tag' }, vote.policy_area);
        bottomRow.appendChild(policyTag);
        item.appendChild(bottomRow);

        // Link to bill detail if it's a standard bill type
        if (vote.bill_type === 'HR' || vote.bill_type === 'S') {
            item.style.cursor = 'pointer';
            item.addEventListener('click', () => {
                window.location.href = `/bill?congress=${vote.congress}&type=${vote.bill_type}&number=${vote.bill_number_raw}`;
            });
            item.setAttribute('role', 'link');
            item.setAttribute('tabindex', '0');
            item.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    window.location.href = `/bill?congress=${vote.congress}&type=${vote.bill_type}&number=${vote.bill_number_raw}`;
                }
            });
        }

        listEl.appendChild(item);
    });
}
```

**Step 3: Test manually in browser**

Run: Refresh Rick Scott's member page in Safari
Expected: See issue filter chips (All, Taxes, Defense, etc.) and vote list cards with bill number, title, one-liner, vote badge, result, and policy tag. Clicking "Taxes" filters to only tax votes. Clicking a vote card navigates to the bill detail.

**Step 4: Commit**

```bash
git add static/js/member.js
git commit -m "feat(votes): add vote list with issue filtering to member profile"
```

---

### Task 5: CSS Styles for Voting Profile

**Files:**
- Modify: `static/css/styles.css`

**Step 1: Add voting profile styles**

Add before the Mobile Responsive section:

```css
/* ============================================
   Member Voting Profile
   ============================================ */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.25rem;
    margin-top: 1rem;
}

.stat-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 1rem;
    background: var(--bg-secondary);
    border-radius: var(--radius);
    border: 1px solid var(--border);
}

.stat-label {
    font-size: 0.8rem;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    font-weight: 600;
}

.stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--accent-gold);
    font-family: var(--font-heading);
}

.stat-big-number {
    font-size: 2.5rem;
    font-weight: 700;
    color: var(--text-primary);
    font-family: var(--font-heading);
    line-height: 1;
}

.stat-sublabel {
    font-size: 0.8rem;
    color: var(--text-dim);
}

.stat-legend {
    font-size: 0.8rem;
    color: var(--text-secondary);
    text-align: center;
}

.issue-filters {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1.25rem;
}

.vote-item {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem 1.25rem;
    transition: all var(--transition);
}

.vote-item:hover {
    border-color: var(--accent-gold-dim);
    background: var(--bg-card-hover);
}

.vote-item-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.3rem;
}

.vote-item-title {
    font-weight: 600;
    font-size: 0.95rem;
    margin-bottom: 0.25rem;
}

.vote-item-oneliner {
    color: var(--text-secondary);
    font-size: 0.88rem;
    line-height: 1.5;
    margin-bottom: 0.6rem;
}

.vote-item-bottom {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}

.vote-item-result {
    font-size: 0.8rem;
    color: var(--text-dim);
    font-weight: 500;
}
```

**Step 2: Add mobile responsive styles for voting profile**

In the `@media (max-width: 768px)` block, add:

```css
    .stats-grid {
        grid-template-columns: 1fr;
    }

    .issue-filters {
        overflow-x: auto;
        flex-wrap: nowrap;
        padding-bottom: 0.5rem;
    }

    .issue-filters .category-tag {
        white-space: nowrap;
        flex-shrink: 0;
    }
```

**Step 3: Test in browser**

Run: Refresh Rick Scott's member page
Expected: Stats cards in a 3-column grid, issue chips in a horizontal row, vote items as styled cards. On mobile (resize narrow), stats stack to 1 column, chips scroll horizontally.

**Step 4: Commit**

```bash
git add static/css/styles.css
git commit -m "feat(votes): add CSS styles for member voting profile"
```

---

### Task 6: Integration Testing and Polish

**Files:**
- Modify: `tests/test_member_votes.py` (add edge case tests)
- Possibly tweak: `static/js/member.js`, `static/css/styles.css`

**Step 1: Add edge case tests**

```python
@pytest.mark.asyncio
async def test_get_member_votes_pagination():
    """Pagination with limit and offset works."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/S001217/votes?limit=3&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert len(data["votes"]) == 3


@pytest.mark.asyncio
async def test_get_member_votes_stats_structure():
    """Stats include all required fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/members/S001217/votes")

    data = response.json()
    stats = data["stats"]
    assert "total_votes" in stats
    assert "yea_count" in stats
    assert "nay_count" in stats
    assert "not_voting_count" in stats
    assert "participation_rate" in stats
    assert isinstance(stats["participation_rate"], (int, float))
```

**Step 2: Run all tests**

Run: `cd ~/Documents/Claude/Projects/clearvote && /Library/Developer/CommandLineTools/usr/bin/python3 -m pytest tests/ -v`
Expected: All tests PASS

**Step 3: Manual testing checklist**

Open Safari to `http://localhost:8000`:
- [ ] Select Florida → 4 members appear
- [ ] Click Rick Scott → stats section with 3 cards (Participation, Vote Breakdown, Total Votes)
- [ ] Donut charts render correctly (green/red slices)
- [ ] Vote list shows 16 votes, newest first
- [ ] Issue chips: click "Taxes" → only tax votes shown. Click "All" → all votes
- [ ] Click a vote card → navigates to bill detail page (for HR/S types)
- [ ] Click Ashley Moody → similar layout, 10 votes
- [ ] Click Byron Donalds → House member, 8 votes
- [ ] Mobile: resize browser narrow → stats stack, chips scroll horizontally
- [ ] Party toggle still works (does not interfere with voting section)

**Step 4: Commit**

```bash
git add tests/test_member_votes.py
git commit -m "test(votes): add edge case tests for member voting endpoint"
```

---

## Summary

| Task | What It Does | Key Files | Status |
|------|-------------|-----------|--------|
| 1 | Mock voting data for 4 FL members | `mock_data.py` | DONE |
| 2 | API endpoint `/api/members/{id}/votes` | `members.py`, `test_member_votes.py` | DONE |
| 3 | Voting stats section with donut charts | `member.html`, `member.js` | DONE |
| 4 | Vote list + issue filter chips | `member.js` | DONE |
| 5 | CSS styles for the voting profile | `styles.css` | DONE |
| 6 | Integration tests + manual QA | `test_member_votes.py` | DONE |
