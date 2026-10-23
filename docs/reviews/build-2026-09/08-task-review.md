# T1.8 review: Bill page payload and additive roll-call fields (commit 3743ad8)

## Summary
The commit does what the plan asks. `data_service.py` and `routers/bills.py` match plan steps 4, 5 and 7 word for word. They are inserted where the plan says: the helpers after `_status_dict`, `_members_by_id` above `self._load()`, and the methods after `get_speaker_votes`. The commit message is the plan's text, with the Co-Authored-By line.

- **Additive only.** `/api/bills/{c}/{t}/{n}` keeps `bill`, including `sponsors`, and `subjects`, and gains `official_summary`. `/votes` keeps every old key and gains `plain_question`, `seal`, `outcome`, `state_tallies` and `covered`. `/ai-summary` is untouched.
- **Scope.** No pages, shells or JS changed, so CSP, innerHTML and title injection are not affected. No data, `.env` or `sync.py` changes.
- **Test file.** `tests/test_bill_page.py` is the plan's file with one change. It is the deviation the implementer reported, covered below.

Verification by the reviewer:
- Full suite: 742 passed.
- All 1,610 real bills go through `get_bill_page` with 0 exceptions and at most 2 rendered roll calls each. Heads: 1,497 class D, 113 class P. Every head is rendered. `rendered_roll_call_keys` matches the page's rendered set on 119-hr-4795, 118-hr-21, 117-hres-8, 119-hres-1499, 119-hjres-20 and 118-hr-2882.
- **Status and head sentence:**
  - 119-hr-4795: "Passed the House 237–169" (moving); "The House passed it, 237 to 169, on September 3, 2026."
  - 119-hjres-20: "Became law". Both chambers are rendered.
  - 118-hr-2882: "The Senate accepted the House's changes, 74 to 24, on March 23, 2024."
- **Server smoke on :8011.** The port was freed first and is free again afterwards.
  - health 200.
  - Bill keys are `['bill', 'official_summary', 'subjects']` and `sponsors` is still present.
  - `/votes`, as (roll calls, roll calls with `covered`, size):

    | Bill | Roll calls | With `covered` | Size |
    |---|---|---|---|
    | 4795 | 1 | 1 | 17.5 KB |
    | 118-hr-21 | 57 | 1 | 42 KB |
    | hjres-20 | 3 | 2 | 19.5 KB |

  - Unknown bill returns `{"senate":[],"house":[]}`. `HR` in upper case is normalized. A bad type returns 400 and an unknown bill detail returns 404.
  - `/`, `/state?code=NY`, `/member?id=S000148` and `/bill?...4795` all return 200. The old bill shell is still served (`bill-content` count 1).
- No mobile shoot, because nothing in the UI changed.

## Deviation (accepted)
The plan's second assertion in `test_other_chamber_falls_back_to_its_newest_roll_call` could not pass under the plan's own `_pick_rendered` rule. When senate/40 becomes decisive, it is the newest decisive roll call, so it becomes the head and the order flips. Comparing sorted keys is the right correction. The implementation was not bent to fit the test.

## Verdict
**pass.** Ship as is. The two notes below are P2 and can be picked up in T7.1, where the bill page first shows these fields.

## Issues
1. **P2, `tests/test_bill_page.py:246-249`: the patched assertion no longer tests what its comment says.**
   - **Problem:** The comment says "a decisive vote in the other chamber still wins over a newer procedural one". After the change, senate/40 is the head and the House has only one roll call. Nothing in the file now checks the case where the head is in one chamber and the other chamber has a newer procedural vote plus an older decisive one. The synthetic 119-hr-50 fixture doesn't reach it either, because its newest House roll call is already the decisive one.
   - **Fix:** Put the House decisive vote first, so it is newest: `views = [house/12 D, senate/41 P, senate/40 D]`. Then assert the picked keys are `["house/119_1_00012", "senate/119_1_00040"]` in that order.
2. **P2, `app/services/data_service.py` `first_paragraph_text`: bad output on a few real official summaries with malformed Congress.gov HTML.**
   - **Scope:** Among the 159 bills with no displayable AI summary, where this text is the page's summary, these came out wrong:
     - **117-hr-963:** the title paragraph is `<b>…</b><strong> of 2022</strong>`. `_TITLE_ONLY_RE` needs the same tag at both ends, so the paragraph is not skipped. Result: the bill title "Forced Arbitration Injustice Repeal Act of 2022 or the FAIR Act of 2022" shows as the summary.
     - **119-hr-2913:** the title and the body sit in one `<p>` split by `<br/>`. Result: "Ukraine Support Act This bill addresses…".
     - **117-hr-4373:** it uses `<p />` separators, so the non-greedy regex runs to a distant `</p>`. Result: an 1,839-character run of several paragraphs, ending "TITLE II--BUDGETARY EFFECTS".
     - **119-hres-1490:** the first paragraph is a lead-in to a `<ul>`. Result: "This resolution states that the House of Representatives", which stops mid-sentence.
   - **Fix:**
     - Treat `<p />` and `<br>` runs as paragraph breaks before splitting.
     - Let the title test accept a paragraph made only of bold/strong elements, in any mix.
     - When a paragraph ends without terminal punctuation and a `<ul>` follows it, append the first list item, or fall back to the next paragraph.
     - Add these four real shapes as test cases.
