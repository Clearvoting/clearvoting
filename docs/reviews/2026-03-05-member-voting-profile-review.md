# Code Review: Member Voting Profile

**Reviewer:** Staff Engineer (automated)
**Date:** 2026-03-05
**Branch:** feat/member-voting-profile
**Commits reviewed:** 6 (9e0bcbf through 518bd5d)
**Files changed:** 6 (992 insertions, 1 deletion)

## Summary

This branch adds a voting record feature to the member profile page. It introduces mock voting data for all 4 FL demo members, a new API endpoint (`GET /api/members/{id}/votes`) with pagination and sorting, a frontend voting statistics display with donut charts reusing the existing `ClearVoteUI` library, and client-side issue filtering. The implementation is well-structured, follows existing patterns closely, and all 37 tests pass with no regressions. There are a few items worth addressing before merge, primarily around data consistency and a minor security concern in the CSS selector interpolation.

## What Was Done Well

- **Pattern consistency.** The new endpoint follows the exact same `_is_demo()` guard pattern used in bills.py and votes.py. The test file matches the existing httpx/ASGITransport test style.
- **ClearVoteUI reuse.** The voting stats section reuses the existing `renderVotePieChart` from vote.js rather than creating new chart code. This is good architectural discipline.
- **Accessibility.** Vote items that link to bill details include `role="link"`, `tabindex="0"`, and keyboard event handlers for Enter/Space. The issue filter chips are buttons (not divs), which is correct semantics.
- **Responsive design.** The CSS handles mobile gracefully -- stats grid stacks to single column, issue filters become horizontally scrollable. The `prefers-reduced-motion` media query is already present.
- **Route ordering.** The `/{bioguide_id}/votes` endpoint is correctly placed before `/{state_code}` to avoid the catch-all matching vote requests.
- **Commit granularity.** Six focused commits, each covering one logical task. Easy to bisect.

## Findings

### P0 -- Blockers

None. The code is functional, tests pass, and there are no correctness errors that would prevent merging.

### P1 -- Should Fix

**1. CSS selector injection in `filterVotes()` (Security)**

In `static/js/member.js` line 324:
```javascript
const active = document.querySelector(`.issue-filters .category-tag[data-area="${area}"]`);
```

The `area` parameter comes from the `policy_area` strings in the API response and is interpolated directly into a CSS selector. If any policy area contains characters like `"`, `]`, or `\`, this would break the selector or could be exploited. Currently the demo data contains only safe strings (e.g., "Taxes", "Government Operations", "Social Security & Medicare"), but in real mode these strings would come from Congress.gov data that the system does not control.

**Recommendation:** Use `CSS.escape()` or attribute comparison via `querySelectorAll` with a filter:
```javascript
const active = document.querySelector(`.issue-filters .category-tag[data-area="${CSS.escape(area)}"]`);
```

**2. `congress` query parameter is accepted but ignored in demo mode (Correctness)**

The endpoint signature accepts `congress: int = 119` but in demo mode, the mock data is always for congress 119 regardless of what value is passed. Passing `?congress=118` would silently return 119th Congress data. This is not a bug per se (real mode will use it), but it could be confusing.

**Recommendation:** Either validate and reject non-119 values in demo mode with a clear message, or include the `congress` value in the response so the client can verify it matches what was requested.

**3. Pagination response lacks `total_count` (API Design)**

The endpoint returns paginated votes but does not include a `total_count` or `has_more` field. The frontend currently loads all votes in a single request (default limit=20), but if the client needs to implement pagination UI or "load more" behavior, it has no way to know how many total votes exist.

**Recommendation:** Add `total_count` to the response:
```python
return {
    "member_id": mock["member_id"],
    "congress": mock["congress"],
    "stats": mock["stats"],
    "votes": paginated,
    "total_count": len(sorted_votes),
    "policy_areas": mock["policy_areas"],
}
```

**4. `limit` and `offset` lack validation constraints (API Design)**

In `app/routers/members.py`, the `limit` and `offset` parameters are plain `int` with defaults but no bounds. The existing `bills.py` router uses `Query(0, ge=0)` and `Query(20, ge=1, le=50)` for the same purpose. This is an inconsistency with the established pattern.

**Recommendation:** Apply the same constraints:
```python
async def get_member_votes(
    bioguide_id: str,
    congress: int = 119,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
```

### P2 -- Suggestions

**5. Mock vote list length vs. stats totals (Data Quality)**

The stats report total_votes of 187 (senators) and 234 (House members), but the vote lists contain only 7-16 items. This is intentional (the mock data is a representative sample, not exhaustive), but it means the frontend's vote list count will never match the stats. The participation donut chart is accurate because it uses the stats, but a user scrolling the list might notice the discrepancy.

This is acceptable for a demo, but a brief comment in the mock data explaining the intentional gap would help future developers.

**6. `resultText` in `_renderVoteItems` only handles two states (Completeness)**

In `static/js/member.js` line 362:
```javascript
const resultText = vote.result === 'Passed' ? 'Bill Passed' : 'Bill Failed';
```

This treats any result that is not "Passed" as "Bill Failed". In the mock data, only "Passed" and "Failed" are used, but real congressional data may include other results such as "Agreed to", "Rejected", "Tabled", or "Vetoed". This binary mapping could be misleading.

**Recommendation:** Display the raw result value, or handle at least 3-4 common result types.

**7. `loadSponsoredLegislation` makes a redundant API call (Performance)**

In `static/js/member.js` line 203, `loadSponsoredLegislation` fetches `/api/members/detail/{bioguideId}` again, even though the same data was already fetched in `loadMember()` and is stored in `memberData`. This is a pre-existing issue (not introduced by this branch) but worth noting since the member page now makes 3 API calls on load instead of the theoretical minimum of 2.

**8. `allVotes` is a module-level mutable variable (Code Quality)**

`allVotes` (line 235) is declared at module scope and mutated by `renderVoteFilters`. This works because there is only one member page at a time, but it creates implicit coupling between `renderVoteFilters` and `filterVotes`. A cleaner pattern would be to use a closure or pass the votes array through the filter function's event handler. This is minor and consistent with the existing `showParty` and `memberData` globals in the same file.

## Test Coverage

**Current state:** 5 tests covering the new endpoint. All pass.

**What is tested:**
- Happy path: demo mode returns correct data structure (fields, vote values)
- 404 for unknown member
- Reverse chronological sort order
- Pagination with limit/offset
- Stats structure validation

**What is not tested:**
- Negative offset or limit values (if validation is added per P1-4, this should have tests)
- The `congress` parameter behavior
- Edge case: member with zero votes (not currently in mock data)
- Multiple members (tests only exercise S001217; at least one test for a House member would verify the different chamber data)
- No frontend tests exist (expected for this project)

**Assessment:** Test coverage is adequate for demo-mode functionality. The tests follow the same pattern as the existing test_routers.py file. Adding a negative-input validation test and a second-member test would strengthen coverage meaningfully.

## Architecture Notes

The implementation correctly places business logic (sorting, pagination) in the router rather than adding unnecessary service abstractions, which aligns with the project's "don't over-engineer" principle from CLAUDE.md. The mock data accessor function (`get_mock_member_votes`) follows the same pattern as the 5 other accessor functions in mock_data.py. The frontend correctly separates concerns: stats rendering, filter rendering, and vote list rendering are separate functions.

## Verdict

**APPROVE WITH CHANGES**

The P1 items (CSS.escape for selector injection, Query parameter validation for consistency, and total_count in pagination response) should be addressed before merge. None of these require architectural changes -- they are small, focused fixes. The P0 section is clear, and the feature is demo-ready.
