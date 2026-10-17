# T3.2 review — Home block renderers: lead, Latest Vote card, the Record

Commit: `dadc562` (on `a5b3c6f`). Reviewer run: 2026-09-25.

## Summary

The commit is additive and matches the plan exactly. I pulled the plan's code blocks out and diffed them against the commit:
- `tests/test_home_render.py` is byte-identical to the plan's block.
- The `HOME_BLOCKS` registry appended to `tests/test_render_escaping.py` is the plan's block, placed after the T3.1 block.
- Every line added to `app/render.py` equals the plan's helper, seal/tally, card, lead, record and home blocks. The only extra line is the planned `from urllib.parse import quote` import (`re` was already imported).
- No duplicate top-level names in `render.py`, and no dead code.

Spec compliance (§4.1 m2/m3/m5, §6.4, §7.2, §7.6, §8 item 2, C-11):
- Copy is verbatim: the kicker, H1, "Or choose a state:", the coverage sentence, "The latest vote" as `h2.kicker`, the dateline format, the two conditional link texts, the pending seal, the stamp line with singular/plural/omitted clause, "Officially:", "Show full title", "Most recent plain-English summary · {date}", the unavailable states for both the card and the Record, and the AI attribution only where AI text rendered.
- The heading outline matches §8 item 2: h1, then h2 for "The latest vote", "What Congress voted on" and "Most recent plain-English summary".
- The tally is a `role=img` track with a spoken label and a sibling visible `<p>`. "didn't vote" appears only when the count is non-zero.
- The card's seal is `final` only for an `hres`/`sres` adoption.
- The 140-character caps and the `<details>` "Show full title" are in place. Summarized rows 2–7 carry no official title.

Safety: every data value goes through `h()`. Hrefs come from `int()` and `quote()`. There is no `innerHTML`, no script, and no shell or title change. The escaping registry adds 24 cases (6 renderers × 4 payloads), and all of them pass.

Verification (run by me):
- Full suite: **905 passed**.
- `scope_check.py static/*.html`: exit 0.
- Fresh server on 8011: `/api/health` returned 200. `curl / | grep -c 'id="record-h"'` returned `0`, as expected because nothing is wired yet.
- `shoot.mjs`: `r32-home-desktop: ok scrollWidth=1280` and `r32-home-mobile: ok scrollWidth=375`, with no JSERROR or CSP lines. The server was stopped and the port is free.
- Real data: `render_home` fed from the live `DataService` renders without errors. The HTML is balanced, has no duplicate ids, and gives the expected output:
  - Card: H.R. 4795 with the official title, the pending seal, "237 yes · 169 no · 27 didn't vote" and the seal "Passed the House 237–169".
  - Record stamp: "6 of the 7 bills below don't have a plain-English summary yet…".
  - H.Res. rows get `seal--final`.
  - The latest-summary block shows H.R. 6500.

## Verdict

**pass.** Ship as is. The two notes below are P2. Neither blocks the task, and neither needs a design decision.

## Issues

| Sev | File | Problem | Fix |
|---|---|---|---|
| P2 | `app/render.py:747` (`_month_year`) | A `since` value that is not an ISO date (for example `"2021"`) raises `IndexError`. `format_date` returns non-ISO text unchanged, and `rsplit(' ', 1)[1]` then fails. That would 500 the home page once T3.3 wires it in. Today the value comes from the index's earliest roll-call date, which is internal, so this is a hardening note only. | In `_month_year`, return `""` when `format_date` does not produce a three-part long date, and have `_coverage_sentence` and `render_record` add the " since …" clause only when the result is non-empty. Alternatively, T3.3 can pass `since` only after `date.fromisoformat` succeeds. |
| P2 | (forward note for T3.3) | The real sync metadata key is `ai_summaries_updated` (value `2026-07-07`). `render_home(..., ai_updated)` must be passed that value, or the AI line drops its "summaries last updated" date. Also, `.dateline`, `.row-seal`, `.vote-card--empty` and `.home-reps` have no rules in `site.css` yet. T3.3 step 9 owns them, including the 880px `.vote-card` min-height that C-11's same-size fallback depends on. | Check both points when reviewing T3.3. No change is needed in this commit. |
