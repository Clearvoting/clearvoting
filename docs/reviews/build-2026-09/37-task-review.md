# T10.5 review — Desktop fact strip in the member header (commit fe63c48)

## Summary

The commit does what the task asks. `render_member_fact_strip` returns the three-cell `<dl class="fact-strip">`:

- "Roll calls voted": `{voted} of {total}`
- "Record covers": `Mon YYYY – Mon D, YYYY`
- The Party cell: an empty `.party` span and a second `.party-toggle`

Each cell's copy matches the plan exactly. `render_member_header` now works out `total` and `voted` before the record branch, so a member with no record renders only the Party cell. The strip goes right after the fact line. The CSS hides the strip under 880px. At 880px and up it shows as a 3-column grid, and the action-row toggle and the kicker's `.party` are hidden. There is still only one `@media (min-width: 880px)` block. site.js is unchanged, as the plan says.

Checks I ran myself:

- **Tests:** `pytest -q` gave 1482 passed, 3 skipped.
- **Scope check:** `scope_check.py` exited 0.
- **Curl on S000148:** returns the three cells, "1,060 of 1,061" and "Jan 2021 – Aug 8, 2026".
- **Curl on G000602:** returns `<dd>641 of 657</dd>` and `<dd>Jan 2025 – Sep 3, 2026</dd>`.
- **Mobile smoke (shoot.mjs):** scrollWidth=375 on both mobile shots and 1280 on desktop. No JSERROR or CSP lines.
- **Desktop PNG:** shows the three-cell strip under the name and exactly one "Show party labels" control. Recent votes is still 4 + 4.
- **gates.mjs:** every gate passes except fold 4/6. The two failures are both member-nophoto (W000832) at 375, where `.vote-row` has top=1000px. The strip is `display:none` at 375, so it cannot cause this. The implementer showed the same failure on ffc296e, so it goes to T11.1.

## Deviations

I checked each one and accept them all:

- **`_fact_month_year` instead of `_month_year`.** The name `_month_year` is already taken at render.py:797 by a different long-form helper, and reusing it would have silently replaced that one. The new helper also avoids raising on non-ISO input.
- **CSS rules deleted to stay under the 30 KB budget.** I checked each one against the base rules:
  - `.reps`, `.roster`, `.vote-list`, `.record-list`, `.sponsored-list` and `.state-tallies` are all `<ul class>`, so `ul[class]` and the global ul margin reset cover them.
  - `.group > details > summary` and `.more-rcs > summary` are covered by the global `details > summary` rule, which sets the same props.
  - For `.bill-header h1`, the global `h1` sets identical values and no media query overrides `h1`.
  - `.record-filter select` gets its font-size from the global select rule.
  - `.record-filter .check` is covered by the global `.check` rule, which sets the same align, gap, min-height and font-size.

  Rendering should not change.
- **`.fact-strip .party { display: inline }`.** This is needed because the global `.party:empty { display:none }` would otherwise hide the empty span and its "hidden" text. Both rules have the same specificity and this one comes later, so it wins.
- **Kicker prefix rule narrowed to `.kicker .party`.** Without this, the party name revealed in the fact strip would get a stray "· " in front of it.

The site.js toggle still works because the member page passes the reveal URL itself through `initPartyToggle({url, ...})`. So when the fact-strip toggle comes first in `toggles`, the missing `data-party-url` on it does not matter.

## Verdict: pass

## Issues (none blocking)

| Sev | File | Problem | Fix |
|---|---|---|---|
| P2 | static/css/site.css | The CSS budget is at 30719 of 30720 bytes. Any later CSS change will fail `test_static_assets` unless something is deduplicated first. | Nothing to do now. Phase 11 should budget for another dedupe pass before any CSS fix. |
| P2 | static/css/site.css | The plan's `.fact-strip dd { color: var(--ink) }` and right-hand cell padding were dropped. The colour is still `--ink` because it inherits from `body`. The only visible change is no right padding on the cells. | None needed. |
| P2 | app/render.py | For a member with a very short record, "Record covers" reads "Sep 2026 – Sep 3, 2026" (W000832). This is what the spec's format produces from real data. | None for this task. If it matters, it's a copy decision for later. |
