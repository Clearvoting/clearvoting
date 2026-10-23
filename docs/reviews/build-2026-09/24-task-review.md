# T7.1 review — Bill story head, what-it-does, official summary slot, fact box

Commit: 0f30727 (on 23829fa). Reviewer run: 2026-09-25.

## Summary

The commit matches the plan word for word. The `app/render.py` block, `tests/test_bill_render.py` and the
`BILL_RENDERERS` escaping block are the Step 2/4/6 text with no changes. `data_service.py` was
correctly left alone, because both contract tests already passed. Three files changed, nothing else touched.

Verified by the reviewer:
- The full suite shows 1259 passed and 2 skipped. `test_bill_render.py` plus `test_render_escaping.py` show 127 passed, with 24 hostile-input cases for the bill renderers.
- `scope_check.py static/*.html` exits 0.
- I freed port 8011, started the server fresh from the worktree and got 200 from `/api/health` and from `/bill?...hr&number=4795`. The shoot.mjs run printed `scrollWidth=375` for mobile and 1280 for desktop on the bill and home pages, with no JSERROR or CSP lines. The server was killed afterwards.
- All four renderers ran over **all 1,610 real bills** in `data/synced` with 0 exceptions. 1,435 bills are displayable and 175 are not, which matches the spec's 60 missing + 115 withheld. 113 bills have a non-decisive head. 16 bills have neither summary. No bill has an official summary without a first paragraph. I also spot-checked 119-s-6 (cloture-only: "The latest recorded vote: on January 22, 2025, …"), 119-hjres-20 (Became law, deck capped with a "Show full title" disclosure, Public Law 119-6) and 119-hres-1499 (1,063-character title cut at 200 on a word boundary, with the pending seal).

Safety:
- Every data value goes through `h()` or `render_seal`.
- Links are limited to `https://www.congress.gov/` URLs.
- A sponsor link is built only from a bioguide id that fully matches `[A-Z]\d{6}`.
- There is no inline script or handler and no new innerHTML (these are server-side strings).
- The share-status `role="status"` node is present and empty.

Tests check rendered output (behaviour), not implementation details. The unused `escape` and `ROOT` names in the test
file are consumed by the T7.2/T7.4 tests the plan appends there. That is transient, not dead code.

## Verdict: pass

## Issues (none blocking; P2 notes for the orchestrator or spec owner)

| Sev | File | Problem | Fix |
|---|---|---|---|
| P2 | app/render.py `render_what_it_does` | For the 16 bills with no official summary either (e.g. 119-hres-1499), the note still says "…the official summary is below.", but there is no official summary. The spec's §4.4 m4 prescribes "the note plus 'Congress.gov has the bill text →'", so the code follows the spec. The copy is still untrue on those pages. | This is a spec copy decision. If wanted, end the note with "…yet." when `official_summary` is empty, and update the test. |
| P2 | app/render.py `render_fact_box` / `render_bill_head` (via T3.2 `_tally_label`) | `_tally_label` removes everything after the vote count. So "Tied 50–50 — motion failed" becomes "Latest floor vote: Tied · date", which drops the result (17 bills), and the tally aria-label reads "Tied: …". "Motion agreed to" / "Motion rejected" also carry no chamber. | Optional follow-up in T3.2's helper: keep the text after "—" for tied seals. Not a T7.1 defect: the plan reuses the helper by design. |
