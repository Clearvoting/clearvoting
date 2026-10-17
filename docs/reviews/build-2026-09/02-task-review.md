# T1.2 review — Python vocabulary formatters (commit ec89b1d)

## Summary
The commit adds `app/render.py` and `tests/test_render_formatters.py`, and both match the plan's code blocks exactly (plan lines 1309-1680 and 901-1295, compared with `diff`; no differences). The commit message is the task's message, with the Co-Authored-By line. The only other change in the working tree is the untracked `docs/reviews/build-2026-09/` folder, which has nothing to do with this commit.

What I checked myself:
- Full test suite: **500 passed**. `tests/test_render_formatters.py` on its own: **113 passed** in 0.9 s.
- Step 5 class counts over all 5,369 real roll calls: an exact match with the plan (amendment 1173 … impeach 1).
- Step 6 grep: `app/`, `static/` and `sync.py` never import `app.render`, so the site is unchanged. I did not run a server or the mobile smoke because nothing renders this module yet.
- Spec §7.1–§7.3 compliance: every table row, plain question, motion noun and class matches §7.1, including the plan's recorded readings (`On Concurring`, parentheticals, named movers). The §7.2 seals (class D, class P, ties, "Speaker elected", unmatched → verbatim) and the bill status seal (Became law → both chambers → the newer vote; `final` only for a simple resolution; impeachment excluded) match. So do the §7.3 sentences and the single date helper. The position map matches §7.1.
- Real-data sweep through `result_phrase`: every seal shape is legitimate (Passed/Adopted/Rejected/Debate ended/Amendment…/Motion…/Tied…/Speaker elected/Veto override failed/Not guilty, plus the verbatim "Point of Order Well Taken", "Decision of Chair Sustained" and "Nomination Confirmed/Rejected"). No output contains "blocked", "let the veto stand" or "taken up". Every real position string is covered: Yea, Nay, Aye, No, Not Voting and Present each have a mapping, Guilty and Not Guilty are shown as recorded, and candidate names become "Voted".
- Safety: pure functions with no I/O and no HTML. The patterns are anchored and linear, and they use nothing JS lacks (lookaheads only), so site.js can mirror them.

## Verdict
**pass** — ship as is. The notes below are optional follow-ups; none blocks this task.

## Issues
| Sev | File | Problem | Fix |
|---|---|---|---|
| P2 | app/render.py (`result_phrase`/`outcome_sentence`) | The 10 House quorum calls ("Call of the House" / "Call by States") have `yeas: 0, nays: 0` and result "Passed". They render as "Motion agreed to 0–0" and "…agreed to a procedural motion, 0 to 0." None of them is linked to a bill, so no planned page shows them today. | When a later task renders non-bill roll calls, give the `attendance` row its own seal (e.g. "Attendance call — 432 present") or skip it. |
| P2 | app/render.py (`outcome_sentence`) | An empty or missing `rc["date"]` gives "…, on ." The index always stores an ISO date, so this should never happen. | Optional: drop the "on {date}" clause when `format_date` returns "". |
| P2 | app/render.py (`bill_status`) | "Resolutions → Adopted" follows the question row, not the bill type. A House "On Passage" of an H.J.Res. reads "Passed the House", while the Senate's "On the Joint Resolution" reads "Adopted by the Senate". A tied decisive vote's seal ("Tied 50–50 — …") doesn't name the chamber. Both follow the spec's table as written. | Leave as is unless the designer wants seals keyed on bill type. |
| P2 | tests/test_render_formatters.py:7 | `from app import render` is imported but never used (it is in the plan verbatim). T1.3 may use it. | Use it in T1.3 or remove it then. |
