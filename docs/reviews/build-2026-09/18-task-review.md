# T4.1 review: delegation renderers and overview render-ready fields

Commit: `899c8a3` (on `6fc84d4`). Reviewer run: 2026-09-25.

## Summary

The commit is additive. It touches `app/render.py` (+368), `tests/test_state_render.py` (new) and `tests/test_render_escaping.py` (+53), and no route calls the new renderers yet.

**Matches the plan.** I pulled the step 4 and step 8 code blocks from the plan and diffed them against the new render.py section. Apart from the added `import json` line (`re` and `quote` were already imported), they are identical. The test file matches steps 2 and 6 except for one line, the deviation below. The escaping block matches step 10 plus the one import line.

**Deviation is correct.** The test now expects `Didn&#x27;t vote` instead of a raw `'`. The renderer runs chip text through `h()`, which is `html.escape(quote=True)`, so the escaped form is what it has to print. The browser still shows "Didn't vote". The implementer changed the expected string and left the escaping alone, which is the right call.

**Spec check (§4.2, §5.3, §5.5, §6.4, §7.4).** I read the copy against the spec and rendered real data:
- **Split ZIP 11201.** "ZIP 11201 spans two House districts — about 72 % … District 10 and 28 % in District 7. Both are shown; …", then the house.gov link. There are 2 split rows, each with "This is my district →". The senators come first, the U.S. Senate section is left out, and the roster sits in a closed `<details>`.
- **Partial ZIP 73949.** "About 86 % of ZIP 73949's land area is outside California, Florida, New York and Texas; …", then the house.gov link.
- **FL District 20.** The row reads "District 20 — vacant in our data · Tell us if this is wrong", and the button carries `data-feedback-open`.
- **No-match ZIP.** The message matches §5.3 word for word. The four state links follow, then the notify disclosure.
- **District header.** It has `data-context-label="New York, District 4"`, the district line with "Change ZIP" and a hidden Remember button. The action row holds the party toggle (no `aria-pressed`, no `aria-label`) and Share. Both `role=status` nodes are present and empty. The meta line and the `<noscript>` copy match the spec. The share URL carries no `district` and no `#mine`.
- **Structure checks, CA/FL/NY/TX.** I ran plain, `district=1` and `district=99` for each state: no link sits inside another, no id repeats, and no party word appears.
- **Ballot copy.** The `\b(On|Not on) the ballot` grep over render.py, the shells and site.js finds nothing.

**Safety and quality.**
- **Escaping.** Every interpolated value goes through `h()`, is cast with `int()`, or is a constant. Photos are allow-listed to `https://www.congress.gov/`. The new escaping test covers all four renderers against the four hostile payloads (16 cases).
- **No banned constructs.** The commit adds no innerHTML, no inline script and no inline handler.
- **No circular import.** `app.dependencies` is imported lazily inside the function, not at module level.
- **Speed.** A CA render takes 0.6 ms.

## Verification I ran

- Full suite: `1004 passed`.
- `scope_check.py static/*.html`: exit 0.
- Plan step 12 on real data: `29 True True`, then `True`, then `0.6 ms per CA render`.
- I freed port 8011 and started uvicorn from the worktree. `/api/health`, `/`, `/state?code=NY`, `/state?code=NY&district=4` and `/member?id=G000602` all returned 200.
- `shoot.mjs` home and state: `ok scrollWidth=375` on mobile, 1280 on desktop, with no JSERROR or CSP lines. The server is stopped.

## Verdict

**pass.** The commit ships as is.

## Issues

| Severity | File | Problem | Fix |
|---|---|---|---|
| P2 | app/render.py:1016 | `_bill_title` caches titles by writing a private `_bill_title_memo` attribute onto the DataService (`vars(ds).setdefault`). The plan asked for this, and it is correct today: DataService only loads data in `__init__`, and the instance is `lru_cache`d. It would go stale if DataService ever reloaded data in place. | No action now. If an in-place reload is ever added, clear the memo there. |
