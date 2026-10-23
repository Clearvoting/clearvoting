# T10.1 review — og:image Phase B (commit 276760c)

## Summary
The commit does what plan T10.1 and spec §9.3 Phase B ask for. `_og_image` is extended in place: there is still exactly one definition, it takes the new `alt=` argument, and `path` stays site-relative. The startup scan (`_og_entities`) is the only way a per-entity path gets chosen, so a key that does not match a scanned file (including `../../etc/passwd`) falls back to the Phase A card. The member and state alt text matches the plan word for word. `_inject_meta` escapes it. Bill, zip-finder and static-route calls are unchanged. The builder reuses Phase A's helpers and adds no copies of them. It prunes cards for members who have left and produces the same bytes on every run. The two new sync steps use the same gate as "Final commit" (`validate_all`), and only the build step has `continue-on-error`. Pillow, fontTools and brotli are added only to the sync job's install line, never to `requirements.txt`. The cards show name, state and "Voting record" and nothing else: no party, no chamber, no score.

## Verification (run by the reviewer)
- Project venv pytest: 1429 passed, 3 skipped (`test_og_cards.py` skips because Pillow is not installed there).
- Under venv-og (pytest installed into the scratchpad with --target): `tests/test_og_cards.py` 3 passed.
- Rebuilt every card from `data/synced` into a temp dir: 150 members + 4 states, byte-identical to the committed PNGs. The set of card ids matches `members.json` exactly. Phase A cards are untouched. The largest card is 53.8 KB (O000172).
- `grep -c "def _og_image"` = 1. `scope_check.py static/*.html` exits 0.
- Server on :8011, started fresh:
  - member S000148 gets its own card, with alt "ClearVoting — Charles E. Schumer · New York · Voting record".
  - `/state?code=TX&district=7` gets `state/TX.png`, with alt "ClearVoting — Texas · Voting record".
  - `/state` (no code) gets `state.png`. The bill page gets `bill.png`. Home gets `default.png`.
  - `HEAD` on a card returns 200, `image/png`, `public, max-age=86400`. A missing card returns 404.
- `weekly-sync.yml` parses as YAML.
- shoot.mjs on the member and state pages: all ok, mobile scrollWidth=375, no JSERROR or CSP lines. Server stopped afterwards.
- Viewed O000172.png, the longest name. The layout matches Phase A, the name sits inside the margins, and nothing overlaps.

## Deviations assessed
- Pins set to Pillow 12.3.0 / fonttools 4.66.0 / brotli 1.2.0 instead of the plan's 11.0.0 / 4.54.1 / 1.1.0. Accepted. These are the versions that built the committed cards, so the sync avoids a pointless rewrite.
- pytest installed into the scratchpad instead of venv-og. Accepted, because the hard constraints forbid changes outside the worktree.
- Total size 7.2 MB against the plan's "under 6 MB" estimate. Accepted. Every card is under the 60 KB per-card check, `optimize=True` is on, and the Phase A template alone is about 43 KB.

## Verdict
pass

## Issues
- P2, `.github/workflows/weekly-sync.yml`. The cards were built on macOS and the sync runs on ubuntu-latest. Even with matching Pillow pins, the Linux wheel's zlib/FreeType might give slightly different bytes, so the first sync could rewrite all 154 cards once (about 7 MB of churn). This is not a correctness problem. Fix: after the first scheduled sync, check the size of the "rebuild share cards" commit. No code change is needed now.
