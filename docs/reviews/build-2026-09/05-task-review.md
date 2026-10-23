# T1.5 review: core data helpers and the ZIP lookup endpoint (commit b34761f)

## Summary
The commit does what T1.5 asks, and the code is word for word what the plan gives. All eight named files match: I pulled each plan code block out and compared it with the commit. The two new test files are identical to the plan. The appended data-service tests match. `app/limiter.py` and `app/routers/districts.py` are identical. Every data-service insertion and the new `sync.py` import line appear verbatim. `_latest_official_summary` was deleted from `sync.py`, and both call sites resolve through the import. `sync._latest_official_summary is data_service._latest_official_summary` holds, and the old `from sync import ...` tests still pass. The removed `get_remote_address` import has no users left.

The implementer's three deviations are only moved line anchors (the files grew in T1.4), and they are correct.

## Verification (run by the reviewer)
- Full suite: **649 passed**. `test_districts.py` + `test_payload_privacy.py`: **44 passed** (36 + 8, as the plan expects).
- I freed port 8011, started a fresh uvicorn and ran the Step 12 checks:
  - The 11570 response has `cache-control: public, max-age=86400, s-maxage=86400`, and its body is exactly the plan's expected body (NY-4, `["G000602"]`, `["G000555","S000148"]`).
  - 11201 returns `split [(10, 0.7216), (7, 0.2784)]`.
  - 73949 returns `partial 0.1367`.
  - 44101 returns `{"zip":"44101","kind":"none","matches":[]}`.
  - `abc` returns a 400 with `cache-control: no-store`.
  - `11570-1234` normalizes to 11570.
  - The 11570 body has 0 party words.
  - `/`, `/state?code=NY`, `/member?id=S000148` and `/bill?...4795` all printed `200 1`.
  - The CSP is unchanged (`script-src 'self'`, `img-src 'self' https://www.congress.gov`).
  - The server was killed afterwards and the port is free.
- The task has no UI change: no HTML, no innerHTML, no title and no shell edits. So the scroll-width smoke does not apply.

## Spec compliance
- §5.1 rule: a district matches at a share of 5 % or more. `covered_share` is the sum of all listed shares, rounded to 4 places. The precedence is none → partial (<0.95) → single → split. `_source` is skipped.
- §5.2 contract: the 200 and 400 bodies and headers, and the `60/minute` limit.
- §3.2: ZIP+4 input and surrounding whitespace are accepted.
- §7.4: `seat_up_2026` returns "regular" for every House seat and the listed kind for senators.
- §2.5 C: `displayable_summary` now gates `_bill_summary` (the list surfaces). The other raw readers are `get_ai_summary` (`/ai-summary` and the bill page), `get_member_votes` issue categories, and the `main.py` health counts. The plan gives each of them to a later task (T1.8, T7.4 and the member-page rewrite), so leaving them unchanged here is correct scoping, not a gap.
- §10 #18: the limiter key is CF-Connecting-IP, then the first X-Forwarded-For entry, then the peer. The feedback and notify limits still pass.

## Verdict
**pass**. Ship as is.

## Issues
| Severity | File | Problem | Fix |
|---|---|---|---|
| P2 (non-blocking, optional) | app/services/data_service.py:45 | `ZIP_INPUT_RE` uses `\d` without `re.ASCII`, so non-ASCII digits such as `١١٥٧٠` pass `normalize_zip`. The input then gets a 200 `kind: none` with those digits echoed back, not a 400. It is harmless (JSON-encoded, no match possible), but the input check is looser than "five digits" says. | If a later task touches this line, add `re.ASCII` or use `[0-9]`. Not worth a fix round on its own. |
