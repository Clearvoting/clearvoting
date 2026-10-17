# T1.7 review, round 2: Member page payload, grouped record and /page endpoint (fix commit ba1f7d0, on top of 5d42fc3)

## Summary
Round 1 found one P1: a Speaker-election "Not Voting" row was shown as "Voted", and the party reveal printed it as "Voted for Not Voting". Commit ba1f7d0 fixes this the way the round-1 review asked, and changes nothing else.

- **`_record_vote`:** every Speaker row still gets the result "Speaker elected", an empty `text` and a copied `roll_call` with the result "Speaker elected". Only a candidate-name position (one not in `_KNOWN_POSITIONS`) becomes "Voted". Real positions such as "Not Voting" and "Present" stay as recorded. The `kind "speaker"` grouping is unchanged.
- **`get_speaker_votes`:** it now returns candidate-name picks only.
- **`pick_recent_votes`:** unaffected. It only takes yes/no bill votes, so a candidate name can never reach it.
- **Docstring:** updated, and no dead code is left behind.
- **Frontend:** `render.py`'s position mapping still turns any unknown string into "Voted".

Verification by the reviewer:
- Full suite: 710 passed.
- The 3 new tests were run in a temporary worktree against the old `data_service.py` (5d42fc3): all 3 fail. With the fix they pass, so they test behaviour, not wiring.
- Server smoke on :8011: the port was freed first and is free again afterwards.
  - health 200
  - `/api/members/detail/H001095?show_party=true` returns 17 picks, and every value is a candidate name (Johnson (LA), Jordan, McCarthy). No "Not Voting" appears.
  - Without `show_party`, there is no `speaker_votes` key.
  - `/api/members/H001095/page?position=nv` has 14 pages. The speaker groups on them are `house/118_1_00525`, `_00016` and `_00015`. Each reads vote "Not Voting", result "Speaker elected", and `roll_call.result` "Speaker elected".
  - Across all 62 default pages for H001095, the strings "Voted for Not Voting", "Johnson (LA)", "McCarthy", "Jordan" and "Jeffries" appear zero times.
  - `/member?id=S000148` returns 200.
- No mobile shoot, because nothing in the UI changed.

## Verdict
**pass.** Ship as is.

## Issues
None blocking.

- (Note, no action) `test_get_speaker_votes_leaves_out_real_positions` patches the private `_index_roll_calls`. This couples the test a little to the implementation, but it keeps the test synthetic. The real-data H001095 test covers the same behaviour end to end.
- (Carried from round 1, no action for this task) The default flat `/votes` still returns raw Speaker candidate names. Make sure T6.3's member-payload trim covers the flat `/votes` rows.
