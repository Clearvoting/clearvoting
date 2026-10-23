# T7.2 review — bill roll-call blocks and the "your representatives" slot (commit 79c11e2)

## Summary
The commit changes only the three files the task names. `app/render.py` and `tests/test_bill_render.py` match the plan's code blocks exactly: a line-by-line diff that ignores blank lines found no differences. The three `BILL_RENDERERS` entries sit inside the dict literal, directly after `render_fact_box`.

**Checks run by the reviewer**
- **Test suite:** the full suite gives 1287 passed, 2 skipped. `test_bill_renderer_escapes_hostile_input` collects 36 cases (9 renderers x 4 payloads), all passing.
- **scope_check:** `scope_check.py static/*.html` exits 0.
- **Real-data sweep of all 1,610 bills through `render_bill_page`:**
  - Every roll-call count uses the keys `{yeas, nays, present, absent}`, so the "All N votes" total is correct.
  - No caption result still names the chamber after `_CAPTION_CHAMBER_RE`.
  - No page has a duplicate `id`, and no empty or duplicate `data-key` appears in any table.
  - Every rendered roll call has `state_tallies`.
  - Collapsed blocks are newest first by date on every bill.
- **Server smoke:** I freed port 8011, started the server fresh and got 200 from `/api/health`. The smoke on `/bill?congress=117&type=hr&number=3233` gave desktop scrollWidth=1280 and mobile scrollWidth=375, with no JSERROR or CSP lines. I stopped the server afterwards.
- **117-hr-3233:** it renders a House block and a Senate cloture block. The Senate block has `data-current="0"`, its own outcome and tally, and the correct senate.gov source URL.

**Spec compliance (§4.4 m2–m3, §6.4, §8 item 2)**
- The slot is T3.1's ZIP form plus a `role=status` node that is present and empty. It is omitted only when there is no roll call: `head` is the newest decisive roll call, else the newest.
- The section has one party toggle and no `aria-pressed`.
- At most two roll calls render state groups, head first. Each group is a `<table class="rc">` with a caption, `scope="col"` headers and row-header name cells.
- Rows are in district order in the 119th House. Earlier Congresses and the Senate use last-name order and show the state only.
- Row chips come from `position_chip`, so there is no second positions table.
- Only covered members are linked and carry `data-bioguide`.
- The "All N votes" list is lazy and has the search box, the select and the `<noscript>` link.
- The heading outline matches §8 item 2.

**Safety:** no inline scripts or handlers were added. All data passes through `h()`, and every URL is built from integers or an escaped key.

## Verdict: pass

## Issues (non-blocking)
- **P2, `app/render.py` (`_rc_more`):** the collapsed block's caption is an `<h3>` inside `<summary>`. HTML allows this, but some screen readers (Safari/VoiceOver) treat `<summary>` as a button and drop the heading inside it. Fix: during the §8 item 13 VoiceOver pass in T7.4 QA, check that the heading is announced. If it is not, move the caption out of the summary into an `<h3>` before the `<details>`.
- **P2, `app/render.py` (`render_vote_by_state`):** "newest first" for collapsed blocks depends on the order `get_bill_page` returns. The renderer does not sort, and the test passes input that is already sorted. Real data is correct today (0 violations). Fix (optional): sort `others` by `(date, key)` descending in the renderer, or add a data-service test that pins the order.
- **Carried from the T7.1 review, not caused by this commit:** `_tally_label` still drops "motion failed" and the chamber in the tally aria-label on non-head blocks. The visible h3 caption keeps the full result text.
