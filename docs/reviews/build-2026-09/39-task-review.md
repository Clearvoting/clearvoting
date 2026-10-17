# T11.2 review: pytest, grep gates and TTFB budget

**Commit:** b581437 `test(perf): no page route scans roll-call files (plan T11.2)`
**Verdict:** pass

## Summary
The commit changes one file, `tests/test_votes_index.py`, adding 34 lines. It appends the guard test `test_page_routes_never_scan_roll_call_files` exactly as the plan writes it. That covers the 5 parametrized cases, the limits (1/0/0/0/2), the startup load kept outside the count, the patches on both `builtins.open` and `io.open`, and the `cache_clear` before and after. The import block already had every required import. The commit message matches step 10 word for word and ends with the Co-Authored-By line.

I re-ran every check independently:
- **Full suite:** 1487 passed, 3 skipped. The guard test alone: 5 passed.
- **The counter really sees file reads.** I ran a scratch copy of the test and printed the files each route opens (fixture data):
  - `/` opens 1 house roll call.
  - `/state` (both URLs) opens only `state_overview/NY.json`.
  - `/member` opens only `member_votes/S000148.json`.
  - `/bill 119-hjres-20` opens 2 roll calls.
  - Each route also opens its own shell HTML.

  The guard therefore measures behaviour and would fail on a regression.
- **Grep gates:** extracted verbatim from plan step 5 and run against a fresh server on 8011. 42/42 PASS, `GREP GATES PASSED`.
- **Warm median TTFB:** `/` 2 ms, `/state?code=CA` 2 ms, `/member?id=S000148` 8 ms, `/bill?congress=118&type=hr&number=21` 3 ms. All return 200 and all PASS.
- **Startup:** 0.25 s, with 5423 roll calls loaded. PASS.
- **scope_check.py** on `static/*.html`: exit 0.
- **shoot.mjs** on home, member, bill and state: all `ok`, mobile scrollWidth=375, desktop 1280, no JSERROR or CSP lines.
- **`git fetch origin main`:** nothing new since the branch head.
- **Evidence files** in `tools/qa/` (pytest, grep, ttfb, startup, regen) all hold the expected final lines. The regen file reads `REGEN IDENTICAL (ignoring generated_at)`.
- **Scope:** the worktree is clean apart from the untracked T11.1 review. No app/, static/ or data/ change, so T11.1's gates.json stays current.

## Deviations assessed
- **3 skips:** these are not the node-parity or real-data skips the plan anticipates. One is `test_og_cards`, where PIL is absent on purpose (§10.2). The other two are `test_feedback` cases that T2.4 (581596a) deliberately skipped because the headers are server-rendered. All three pre-date this task and none hides a failure. Accepted.
- **Step 8 run as separate commands** instead of the `rm -rf` block: the operations are the same and the outcome is identical. Accepted.
- **Step 9 skipped:** correct, since REGEN was identical and no fix was committed.

## Issues
None.
