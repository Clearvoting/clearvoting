# Review: T11.3 — Scripted QA walkthrough of the spine (§8 item 13)

**Commit:** c683a5a (docs only: `docs/reviews/2026-09-26-redesign-qa-report.md`, 242 lines)
**Verdict:** pass

## Summary

The commit adds only the QA report, as the plan requires (step 10). The out-of-repo files match the plan text, and I checked each one with diff. `build_qa_report.py` is byte-identical. `pr-body.md` is identical except for the "Build share cards" sentence. The plan's conditional required that sentence because `cutfirst.txt` shows T10.1 landed (276760c), and `grep -c` gives 1. `walk.mjs` has the two documented test-harness changes and no other differences.

I re-ran everything myself on a freshly started server (port freed first, then stopped, and 8011 is free now):
- pytest: 1487 passed, 3 skipped.
- scope_check.py on static/*.html: exit 0.
- Step 1 curl 302 evidence: byte-identical to `tools/qa/curl-302.txt`. All three 11570 variants give `location: /state?code=NY&district=4#mine`. 11201 and 73949 redirect to their `zip=` URLs. All five 302s carry `public, max-age=0, s-maxage=86400`. 44101 and abc give 200 with `s-maxage=600, stale-while-revalidate=3600`. `/api/districts` gives 200 with max-age=86400 for 11570 and 400 with no-store for abc.
- `node walk.mjs` (into the scratchpad): WALK PASSED, 375px 92/92 and 1280px 87/87, exit 0. The bfcache info line shows District 4 true and persisted=false, as expected.
- `node home-reps.mjs`: HOME-REPS PASSED.
- Step 4 keyboard-only / non-mutating grep: no matches (exit 1). There is no `pushState` anywhere in static/js.
- shoot.mjs on home, state-ny-d4 and bill 119-hr-6500: scrollWidth=375 mobile and 1280 desktop, with no JSERROR or CSP lines.
- The report has 51 table rows and no MISSING lines. The evidence is not stale: gates ran at 11:40Z and walk at 11:55Z, both after the last app/static/data commit 1539a7a (11:32Z). The report was rebuilt at 07:55:38 local, after the final walk run.

## Deviations assessed

1. **History-length check (walk.mjs).** A Playwright page starts on about:blank, so after `/` then `/state` the history holds 3 entries, not 2. The check now measures history.length after home and requires exactly one more entry. That still proves a push-free ZIP → 302 → replaceState flow, so the intent is kept. **Accepted.**
2. **Cached-302 replay (walk.mjs).** The walk was already on `/state?code=NY&district=4`, so `goto(...#mine)` was only a fragment change: no document load, and `initHome` never ran. A real followed 302 comes from a request to `/state?zip=…` and always loads a new document. Loading about:blank first reproduces that. No product code changed, and §3.3's "only on load" rule is kept. **Accepted.**
3. The PR body's share-cards sentence was appended as the plan's conditional requires. **Correct.**
4. The untracked 38/39 review files belong to the orchestrator. Leaving them alone was correct.

## Issues

None. The report says "at b581437" because the builder runs before the commit, as step 8/10 intend. That is not a defect.
