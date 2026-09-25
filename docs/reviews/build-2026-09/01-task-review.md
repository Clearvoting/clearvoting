# T1.1 review — Sanctioned data files, SOURCES.md and real-data test fixtures

Commit: `fbe8132` (parent `4a9bd36`). Reviewer run: 2026-09-25.

## Summary

The commit matches the plan task exactly. Checked independently:

- `tests/test_data_files.py`, `scripts/build_zip_crosswalk.py` and `data/SOURCES.md` match the plan's code blocks line for line.
- Script vs. the tools-folder builder: the only differences are the `Usage:` docstring line, the `SOURCE` block with its two comment lines, and the `OUT.write_text({"_source": SOURCE, **final}, …)` line. Trimming and share logic are unchanged (spec §5.1).
- Rebuilding the crosswalk from `tools/data/raw` gives CA 52 / FL 28 / NY 26 / TX 38, 6,639 ZCTAs, 413,196 bytes. The output is byte-identical to the committed `data/synced/zip_districts.json`. With `_source` removed it equals the verified 2026-09-11 build, and `_source` is the last key.
- `data/synced/senate_2026.json` is a byte-for-byte copy of the tools file (`cmp` is clean).
- Fixtures: the plan's Step 7 script was re-run against the parent commit's fixtures plus the real `data/synced`. `diff -r` against the committed `tests/fixtures/synced` shows no differences, so every slice is real data cut as specified. Inventory checks: 22 bills (20 in the 119th); 16 AI summaries; `119-hr-7148` has `needs_review: true`; `4795`, `s-5271` and `hr-5334` are unsummarised. Members are FL 2 / NY 4 / TX 1, with Moody absent. Donations have S000148, G000602 and R000579 only. Size is 1.4M.
- Shifted assertions in `test_data_service.py`, `test_health.py`, `test_homepage.py` and `test_routers.py` match Step 10 exactly. The health test's `0 < covered < len` guard stops the fixture-derived expectations from passing trivially.
- `git grep zip_districts|senate_2026 -- app static sync.py` returns nothing. `app/`, `static/`, `sync.py` and `.env` are untouched, and no other `data/synced` content changed.
- Full suite: **387 passed**. The working tree is clean.
- No server or scroll-width smoke test was run: this is not a UI task, and no app or static code changed. CSP, innerHTML and title-injection rules are therefore not affected. The hostile-title fixture bill is in place for the later escaping tests.

## Verdict

**pass** — ship as is.

## Issues

None.
