# Review 34 — T10.2 In-place record pagination and filtering (cut-first)

Commit: `a4bc0ef` on `redesign/2026-09`. Reviewer: spec compliance + engineer standards.

## Summary

The commit does what the plan task and spec §4.3 m4 / §3.3 / §8 item 11 ask. The record section keeps
T6.2's order with two swap targets (`data-record-result`, `data-record-list`). The markup hooks are
`data-record-nav` on both pager links and `data-record-filter` on the GET form. `app/render.py` gains
`TREE_TAGS`/`TREE_ATTRS`/`N`/`tree_html`/`record_tree`, and the record helpers now build nodes.
`/api/members/{id}/page` returns `record_tree`, computed from the full page before the allowlist.
`site.js` gains `buildTree` (el() + text nodes + allowlist, no HTML sinks), `initRecordPaging`
(replaceState only, focusHeading, `cv:content-swapped`), and the Speaker-pick refill listener in
`initPartyToggle`. `member.js` is untouched (0 submit-on-change matches). The appended tests match
the plan text byte for byte.

Verified independently:
- Full suite: 1450 passed, 3 skipped. The node parity test ran and passed. It is not among the skips.
- `scope_check.py static/*.html` exits 0 (8 shells).
- Step 7 snapshot re-run against the step-2 snapshot prints `identical`.
- Fresh server on :8011:
  - the tree print gives `['list', 'result'] {'data-record-result': ''} 1 {'data-record-list': ''} 2`;
  - `data-record-nav` count is 2;
  - a GET of the page API returns `cache-control: public, max-age=300, s-maxage=3600, stale-while-revalidate=86400`;
  - CSP is unchanged (`script-src 'self'`), and the title stays literal and server-owned.
- `shoot.mjs` prints `scrollWidth=375` for member p2, G000602 p2 and the `position=nv` empty state, with no JSERROR or CSP lines.
- `gates.mjs` prints GATES PASSED.
- `paging-check.mjs` prints `older-votes: ok` and `filter: ok`: no navigation, `history.length` unchanged, focus on `#record`, and result `144 bills · Voted no`.
- The server was stopped afterwards.

I accept the implementer's deviations:
- The `data-record-nav` attribute comes first so existing substring tests still hold.
- The form-assertion update and the `PAGE_KEYS | {"record_tree"}` update both follow from the plan's own contract.
- The comment rewording is forced by the plan's own no-`pushState` test.
- The HEAD-vs-GET curl note is correct.

## Verdict: pass

No P0 or P1 issues. The two P2 notes below are follow-ups and do not block this task.

## Issues

| Severity | File | Problem | Fix |
|---|---|---|---|
| P2 | app/render.py (`render_vote_row` / `render_vote_row_node`) | The plan asked for the string helper to become a one-line wrapper over its node twin. Instead, the shared `.vote-row` markup (§6.4) now lives in two full copies: recent votes use the string one and the record uses the node one. A later edit to one will not reach the other, and no test pins them equal. The step-7 and 1,200-render checks were one-off. | Make `render_vote_row` accept either a node or `""` for chip/extra, switch the recent-votes caller to `_mp_chip_node`, and have `render_vote_row` return `tree_html(render_vote_row_node(...))`. At minimum, add a parity test asserting `render_vote_row(href, _mp_chip(v), ...) == tree_html(render_vote_row_node(href, _mp_chip_node(v), ...))` for displayable/official rows with and without href/extra. |
| P2 | static/js/site.js (`initRecordPaging` `load`) | While a fetch is in flight, a second pager click or a Filter submit is already `preventDefault`-ed and then dropped by the `busy` guard, so the reader's action silently does nothing. It rarely matters, because responses are cached and fast. | Either let the later request win (an attempt counter like `initPartyToggle`'s), or skip `preventDefault` when `busy` so the native link or form navigation runs. |
