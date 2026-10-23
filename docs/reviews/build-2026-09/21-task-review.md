# T6.1 review — Member header, recent votes, sponsored and money renderers

**Commit:** ecbef07 (app/render.py, tests/test_member_render.py new, tests/test_render_escaping.py appended)
**Verdict:** pass

## Summary
The commit does what the plan task says, word for word. `app/render.py` gains the "Member page (T6.1)" section exactly as plan Steps 4 to 6 give it. `tests/test_member_render.py` is identical to the Step 2 block (diffed). The member escaping block in `tests/test_render_escaping.py` is identical to the Step 8 block (diffed). The only imports added are `unicodedata` and `urllib.parse`; `re` and `date` were already there.

Spec §4.3 copy checked against the code and tests, all verbatim:
- the breadcrumb, the Senator and Representative kickers, and both forms of the fact line
- the seat-seal copy, which describes the seat and never the person
- the Recent votes kicker h2, the caption, and the short-record and empty states
- the sponsored heading and its n = 0 state, the Congress.gov link and its accent-folded slug
- the money sentence, the meta line, and no bars or contributor rows (C-4)

The party toggle has no `aria-pressed`, and both `role=status` nodes are present and empty (§6.4).

Safety:
- Every interpolated value goes through `h()`.
- Hrefs are built only from parsed integers, bill types on the known list, `urllib.parse`, or regex-checked ids (FEC id, roll-call key).
- A photo URL from any host other than www.congress.gov is dropped, which fits CSP img-src.
- Seal variants are allow-listed in `render_seal`.
- No innerHTML, inline script or `<title>` change.

## Verification (run by the reviewer)
- Full suite: 1140 passed, 1 skipped.
- `scope_check.py static/*.html`: exit 0.
- `\b(On|Not on) the ballot` grep in app/render.py: no hits.
- Step 10 real-data smoke:
  - S000148: 8 rows, h1 "Charles E. Schumer", FEC link S8NY00082.
  - G000602: 8 rows, h1 "Laura Gillen", FEC link H2NY04244.
  - W000832: 0 rows, h1 "Aisha Wahab", and the meta line.
- All 150 members: every block renders with no exception. The FEC sentence appears for 70 members. The spec says 71; the 71st, C001127, has a donations entry but no members.json row, so it has no page. That is not a renderer gap.
- Server boot: /api/health 200. /member?id=S000148 still serves the old page (200, one `<title>`), as it should until T6.3.
- No mobile shoot was run: nothing routes to these renderers yet. The task's only visual check is the Step 10 Python smoke.

## Implementer deviation
The meta line's apostrophe prints as a plain `'` rather than `&#x27;`. This is correct. The line is a fixed literal, so it needs no escaping, and the plan's Step 10 expectation was simply wrong about the output. Accepted.

## Issues
| Severity | File | Problem | Fix |
|---|---|---|---|
| P2 | app/render.py (lines 1722, 1822) | `render_vote_row` and `render_recent_votes` each have only one blank line above them, because the plan's step blocks were joined without the second one. These are the only two top-level `def`s in the file that break the two-blank-line convention (PEP 8 E302). | Add one blank line before each. This can go into the T6.2 commit, which touches this section next. |
| P2 | app/render.py | `_mp_source_anchor` and `_mp_is_speaker` have no callers in this commit. | None needed. The plan names them as helpers T6.2 consumes. Confirm T6.2 uses them, otherwise they become dead code. |
