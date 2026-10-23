# T1.3 review: Python naming, date and escaping formatters (+ strip_tags)

Commit reviewed: fe67e85 (branch redesign/2026-09)

## Summary
The commit matches the plan task exactly.
- `app/render.py`: the import block is extended, and `h`, `_BILL_TYPE_LABELS`, `format_bill_code`, `ordinal`, `display_name`, `tenure_line`, `_SEAT_SEALS`/`seat_seal`, `_SPONSOR_FULLNAME_RE`/`sponsor_name` and `_TextOnly`/`strip_tags` are appended word for word from plan Step 4.
- `app/main.py`: it imports the shared map and `display_name`, the local `_BILL_TYPE_LABELS` block is deleted, and `_member_meta` builds the name with `display_name`.
- `tests/fixtures/synced/members.json`: the two `directOrderName` lines are removed and nothing else changes.
- Tests: `test_render_formatters.py` is identical to the plan block after a line-by-line diff that ignored blank lines. `test_render_escaping.py`, `test_seo.py` and `test_data_service.py` are verbatim too.

## Verification (run by the reviewer)
- Full suite: 576 passed. The touched files: 237 passed. Both match the plan's expected counts.
- The real-data sponsor test ran against data/synced/bills.json and was not skipped.
- `display_name` gives a clean result for all 150 real member names: each has exactly one comma and no quoted nicknames. `tenure_line` is non-empty for every real member.
- Local server on port 8011 (freed first, and confirmed free after the check):
  - /api/health, /, /state?code=NY, /member?id=S000148, /member?id=S001217 and the H.R. 4795 bill page all returned 200.
  - The member title is `Charles E. Schumer (NY) — Voting Record | ClearVoting`. The bill title is unchanged. An unknown member falls back to `Representative — ClearVoting`.
  - The old member shell still loads member.js once.
- Safety: the title stays escaped through `_inject_meta` in main.py. No new innerHTML, inline scripts or shell/CSS/JS changes, so the mobile scroll-width smoke is not applicable.

## Verdict: pass

## Issues
None blocking. Two notes that need no action in this task:
- P2 (out of scope, already known): static/js/member.js:60,71 and static/js/state.js:199 still read `directOrderName`. The JS fallbacks cover it, so there is no functional change, and the planned page rewrites replace those scripts. The implementer flagged this correctly.
- P2 (pre-existing, not introduced here): `_inject_meta` calls `_title_re.sub` with an f-string replacement, so a backslash in a title would be read as a regex escape. No real data contains one. Worth a lambda replacement when T8.1 reworks titles.
