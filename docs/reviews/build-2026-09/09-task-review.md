# T1.9 review — Latest vote and bills order from the index (commit 5dfa51f)

## Summary
The commit matches plan T1.9 step for step. The code blocks in (b)–(f) and the search fix in step 8 are applied exactly as written, and every test block in steps 2–5 is present. The implementer's four stated deviations are all harmless: `json` was already imported, a test name matches the step 7(g) grep, T1.7's `bill_status` has a third optional parameter, and the server was stopped with lsof/kill.

- `_clean_vote_date`, `_build_latest_vote`, `_build_bill_votes_index` and the lazy scan attributes are removed. Nothing still references them. Each of the six T1.7/T1.8 helpers is defined exactly once.
- `_index_bills()` runs in `_load` directly after `_votes_index` is assigned, so it runs once per construction with both `_bills` and the index set. It only works on dicts. It computes activity date as max(index activity_date, latestAction) and gets status from T1.7's `_bill_status_for`, which is the one status path.
- `get_latest_vote` reads the index `latest` key. It reads one roll-call file for `covered` through T1.8's `covered_positions`, then caches the result. It keeps all the old app.js keys and adds `rc`, `date_iso`, `plain_question`, `seal`/`outcome`, `state_tallies`, `one_liner`, `has_summary` and `covered`. `date` is now the long display form, as the commit body says.
- `get_bill_votes` opens no file. It returns the same 7 keys as before, oldest first per chamber, with an ISO `vote_date`. The only caller is `get_bill_votes_payload`, and bill.js reads only congress/session/vote_number from the refs, so it is unaffected.
- `one_liner` is nullable and set only when the summary is displayable. The old app.js already falls back with `bill.one_liner || bill.title`, and search now handles `None`.

## Verification (run by reviewer)
- Full suite: 753 passed (baseline 742 + 11).
- I freed port 8011, started uvicorn and got /api/health 200. The latest-vote line matches the plan's expected output exactly: `house/119_2_00295 2026-09-03 House H.R. 4795 | Final vote to pass | Passed the House 237–169 | False 142 ['CA','FL','NY','TX'] | September 3, 2026 True`.
- The party grep returns 0.
- `/api/bills?limit=7` has non-increasing activity dates, and 119-hr-6500 sits at 2026-09-01.
- The summarized_only check returns True.
- The four pages each return 200. The old `id="latest-vote"` grep returns 1.
- Warm TTFB is about 0.0015s.
- `/api/bills/119/hr/4795/votes` returns `[(295,'2026-09-03')]`. Search `q=act` returns 1149 results.
- Checked through the service on the real data: all 1610 bills are sorted by activity date, 0 have a null activity_date, 0 have an empty derived_status, and 175 have a null one_liner (unsummarized or withheld). Every bill has an entry in the index.
- I killed the server and confirmed the port is free. I skipped the scroll-width smoke because the task changes no page markup, as the plan says.
- There are no template, CSP, innerHTML or title changes.

## Verdict: pass

## Issues
- P2 · app/services/data_service.py · `_bill_id_of` is a new copy of the bill-id f-string. Near-identical copies already exist in `_bill_lookup`, `_sponsored_row` and elsewhere. They also differ at the edge: when `type` is None, `_bill_id_of` gives "none" and `_bill_lookup` gives "". Real data always has `type`, so nothing breaks today. · Fix (optional, later task such as T1.10 that already reuses `_bill_id_of`): have the other builders call `_bill_id_of`, and make it use `str(bill.get('type') or '')`.
