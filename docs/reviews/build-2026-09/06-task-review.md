# T1.6 review: state overview sync step and committed per-state files

Commit: 4db4f13 (branch redesign/2026-09). Reviewer run: 2026-09-25.

## Summary

The commit matches the plan task line for line: the `data_service.py` helpers, the loader and the cache attribute; the `sync.py` import, the builders, the `--step` choice, the offline branch and the full-sync call; the two workflow steps, with the same gate as `Commit member votes`; the tests; the fixture; and the four committed state files. The commit message is the plan's text. It meets spec §10 #7 and §4.2: the files hold raw fields only, `latest_vote` is the member's newest class-D bill vote, `districts_expected` comes from the crosswalk, `roster_as_of` is the newest `updateDate`, and a missing file falls back to `members.json`. No page markup, CSP, title handling or innerHTML changed. The files contain only data derived from `data/synced/`.

What I checked myself:
- Full suite: 666 passed. `test_state_overview.py` plus `test_votes_index.py`: 42 passed, 0 skipped. The committed-files test ran, so it was not skipped.
- Reproducibility: I rebuilt the votes index, the four state files and the fixture. Every line printed `(unchanged)`, `shasum -c` gave OK for all 6 files, and the working tree stayed clean.
- NY data row: `2026-09-05 26 ['G000555', 'S000148']`. G000602 is district 4, with a House term starting 2025, and its `latest_vote` is `house/119_2_00295` / `119-hr-4795` / `Yea` / `2026-09-03`. House counts: NY 26/26, FL 27/28, CA 52/52, TX 37/38. The FL and TX gaps are the real vacancies.
- Server on port 8011, freed first and stopped afterwards: the four pages each returned `200 1` (still the old styles.css markup). `/api/members/NY/overview` keeps its old shape. `/summary` returned 200, and `include_stats` still carries `participation_rate`.
- Workflow: the overview steps run after `Commit member votes` and before `Write sync metadata`, with the same `if:` gate.

## Verdict

**pass**: ship as is. The notes below are advisory. None of them blocks this task.

## Issues

| Sev | File | Problem | Fix |
|---|---|---|---|
| P2 | app/services/data_service.py (`get_state_overview`) | The method returns the cached dict itself. T4.2 will strip `partyName` unless `show_party=true`. If it strips in place, it corrupts the cache for every later request, so party could leak into, or vanish from, other responses. | In T4.2, build new member dicts or copy before stripping (for example `{k: v for k, v in m.items() if k != "partyName"}`), and add a test that calls the endpoint twice with different `show_party` values. |
| P2 | .github/workflows/weekly-sync.yml | `Commit members` runs unconditionally. When member-vote validation fails, `members.json` is still committed but the overviews are not rebuilt. `roster_as_of` and the roster in the committed overview then differ from the builder's output, and `test_committed_overviews_match_the_builder` fails on the next PR. That is the same "fails CI for a data reason" case the new comment says it avoids, just on a different input. | Leave it for now, because it only happens in a run that is already red. Possible later fix: when validation fails, run `git checkout -- data/synced/member_votes` and then build the overviews anyway. |
| P2 | app/services/data_service.py (`get_state_overview`) | Any two-letter code outside the covered states (for example `AK`) logs a "missing … run sync" warning once per process and caches None. That warning is misleading for states that are not covered. | In T4.2, check `COVERED_STATE_NAMES` before calling, or log only for covered codes. |
