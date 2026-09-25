# T1.4 review: votes index (sync step, committed file, startup loader, validation)

Commit: `eecd625`. Reviewer ran every check below independently on 2026-09-25.

## Summary

The commit matches the plan exactly.
- `sync.py`, `data_service.py`, `data_validator.py`, the workflow YAML, `test_sync.py` and `test_data_validator.py` match the plan's code blocks line for line.
- `tests/test_votes_index.py` matches the plan's three test blocks verbatim (checked with a whitespace-insensitive diff against the plan text).
- The commit message is the plan's text, and it ends with the Co-Authored-By line.
- No markup, template, CSS, JS, `.env` or other synced data changed. The only data files are the two the task creates: `data/synced/votes_index.json` and `tests/fixtures/synced/votes_index.json`.

Verification, all run by the reviewer:
- Full suite: **596 passed**. `tests/test_votes_index.py`: **17 passed**, and it printed `bills with no decisive roll call: 113 of 1610`.
- Rebuilding with `CONGRESS_API_KEY` unset printed `5369 roll calls, 1610 bills, latest house/119_2_00295 (unchanged)`. The sha256 was `ebc1ede7…` before and after, so the rebuild is byte-identical. `git status` stayed clean.
- `run_validation(data/synced)`: `0 failure(s), 1 warning(s)`, the pre-existing orphan C001127. Exit 0.
- Spot check: `house/119_2_00295 2026-09-03 D Final vote to pass 119-hr-4795 2026-09-03`. Also `senate/119_1_00372` → `2025-07-01 {'CA': [0, 2, 0], 'FL': [2, 0, 0], 'NY': [0, 2, 0], 'TX': [2, 0, 0]}`. Both match the plan.
- The workflow order check printed `True`: index → member votes → validate.
- Server on 8011 (port freed first, killed after): `/`, `/state?code=NY`, `/member?id=S000148` and `/bill?congress=119&type=hr&number=4795` each returned `200 1` and still link styles.css. `/api/votes/latest` keys are unchanged. No warnings in the server log.
- The mobile scroll-width smoke was skipped because this task changes no markup.

Other checks:
- The four other `build_member_votes` call sites (backfill, regrade, reset, regenerate) only rebuild from vote files already on disk. They add no roll calls, so the committed index cannot go stale through them.
- The full sync does not call validation. The only CI validation runs after the new index step.

Implementer deviations are acceptable:
- The file is 2,187,773 bytes against the plan's estimate of ~2,138,238. The counts match exactly, and the plan only asked for "about 2.1 MB".
- Edits were placed by anchor text rather than line number.

## Verdict

**pass**. Ship as is.

## Issues

None blocking. Notes for later tasks (P2, no action needed in T1.4):

| Severity | File | Problem | Fix |
|---|---|---|---|
| P2 | sync.py (full-sync main, ~line 2490) | The new line reuses the `[7/12]` label, so the full sync prints `[7/12]` twice. This is cosmetic, and it is the plan's own wording. | Leave it, or relabel it `[7b/12]` whenever the step list is next renumbered. |
| P2 | tests/test_votes_index.py | The loader tests read the private `DataService._votes_index`, as the plan dictates. | When T1.5+ add public accessors that read the index, move these assertions onto those accessors. |
| P2 | sync.py `votes_index_payload` | If a vote file lacks `congress`, `session` or `vote_number`, `roll_call_key` raises and the whole index build stops. Real data has no such file, and failing loudly at sync time is defensible. | None now. If Senate/House feeds ever emit partial files, skip the file and log it instead. |
