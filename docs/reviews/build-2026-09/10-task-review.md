# T1.10 review: ai_summaries_updated persistence, health counts, notify log fix

Commit: `a8c4025` on `redesign/2026-09`. Reviewed 2026-09-25.

## Summary

The commit follows plan T1.10 step for step, and every code block matches the plan's text exactly.

- **sync.py.** Adds `import hashlib`. `_ai_summaries_digest` and `_ai_summaries_stamp` sit directly after `_atomic_write_json`. All three `sync_metadata.json` writers now call `metadata.update(_ai_summaries_stamp(...))` right before their write: `--step metadata`, `--ai-only` and the full sync. The two AI paths take a digest after `SYNC_DIR.mkdir`, so a rewrite dates the field today. A grep finds no fourth writer.
- **DataService.** `_audit_grades` is loaded. `coverage_counts()` is computed once and returns a copy. `latest_roll_call_date()` reuses `_bill_id_of`, `displayable_summary` and `_index_roll_calls`, as the plan's interface list says.
- **/api/health.** Keeps every existing key and adds only `latest_roll_call`, `ai_summaries_updated` and `coverage`, as §10 #11 requires.
- **notify.** The fallback log line is now `signup saved to fallback, state=%s`, with no email (§10 #16, §4.7). State validation is correctly left for T3.3.
- **sync_metadata.json seed.** `2026-07-07` matches `git log -1 --format=%cs` of `ai_summaries.json`. The digest `149d7e50…3585` matches `shasum -a 256` of the file. The diff is +3/-1 because of the trailing comma, which is expected and harmless.
- **Scope.** No markup, CSP, title or innerHTML surface is touched. The data change is limited to the sanctioned metadata seed.

## Verification (run by the reviewer)

- **Full suite.** `766 passed`.
- **Server smoke.** Freed port 8011 first, then started the server. `/api/health` returned 200 with `2026-09-03 2026-07-07 {'bills': 1610, 'shown': 1435, 'missing': 60, 'withheld': 115, 'audited': 177, 'nominations_excluded': 1469} 2026-09-05T13:05:50.549225+00:00 60`, which is exactly the plan's expected line. All old keys are still present. `GET /` returned 200. The server was stopped and the port is free.
- **Test fixture.** `tests/fixtures/synced/sync_metadata.json` already carries `ai_summaries_updated` (from T1.1), so the health test compares a real value and never passes on `None == None`.

## Deviations

Both deviations the implementer reported are acceptable:

- The metadata smoke ran on a scratchpad copy instead of `/tmp/cv-meta`. The outcome was the same.
- The seed diff is +3/-1 instead of +2, because of the trailing comma.

## Verdict: pass

## Issues

None blocking. Two notes that need no fix:

- **P2, tests/test_sync.py.** `test_all_three_metadata_writers_stamp` is a source-text count, so it checks the implementation, not behaviour. The plan prescribes it, and the behavioural tests for `--step metadata` and both `--ai-only` outcomes cover the real behaviour. The full-sync writer is covered only by this grep. It is acceptable because a full-sync test would need the whole network pipeline mocked.
- **P2, carried from T1.9.** `health_check` still builds bill ids with its own f-string, while `coverage_counts` uses `_bill_id_of`. The two agree on real data. Unify them in a later cleanup if desired.
