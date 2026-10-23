# Review: ClearVoting Redesign Implementation Plan

**Review type:** `/Users/josephgarcia/.clearvote-worktrees/redesign-2026-09/docs/superpowers/plans/2026-09-18-clearvoting-redesign.md` (plan doc, 40 tasks in 11 phases, about 27,260 lines)
**Scope:** The whole assembled plan: phases 1–11, the Global Constraints, the Design Decisions, and the Spec and Finding coverage tables. It is checked against the spec (`docs/superpowers/specs/2026-09-18-clearvoting-redesign-design.md`), the brief, the F01–F63 review, and Joseph's 2026-09-22 confirmations.
**Reviewer:** Three review passes: (1) a per-group adversarial review of each of the 11 groups through three lenses (correctness, test-qa, traceability), after which each group's author revised and logged changes, rejections and cross-group requests; (2) a cross-group consistency check that applied those requests across fragments and to map.json; (3) this independent readiness check of the assembled plan.
**Local verification:** Static review only, with no code changed in the worktree. I ran `index_tasks.py` on the plan (exit 0, 40 tasks) and used scripted greps for placeholders, task-id references, dependency direction, commit trailers and finding coverage. Every P0 and P1 fix was checked by grepping the plan text for it.

**Implementation plan:** the file above
**Technical design:** `/Users/josephgarcia/.clearvote-worktrees/redesign-2026-09/docs/superpowers/specs/2026-09-18-clearvoting-redesign-design.md`

## Summary

The plan turns the Spine spec into 40 test-first tasks in the spec's §10.3 commit order. Commit 1 only adds things. Each page switches over in one commit. The old stylesheets are retired only behind the §6.9 gates, and a scripted final verification closes the plan. The per-group reviews raised 141 issues (2 P0, 54 P1, 85 P2). Both P0s and all 54 P1s are fixed in the plan text or were rejected for a reason that holds. This check found one more P1-level defect: T10.4's `serve_bill` edit targeted a line T7.4 no longer writes, and following it would have dropped the 503 error state. I fixed it in place. What remains is P2 only: two landmark and link-behaviour details, and some small cosmetic or stale text.

**Readiness:** Ready. No P0 or P1 is unresolved. The task index is valid, every task id and dependency points backwards, every plan commit carries the trailer, and F01–F63 are all accounted for.

---

## Strengths

- **The schedule is built into the task structure.** The plan puts the minimum shippable scope, the 2026-10-06 checkpoint and the cut-first order into the tasks themselves. The Design Decisions name the minimum scope (Phases 1–7 plus T8.1–T8.3, Phase 9 and Phase 11). A checkpoint gate opens Phase 8. Every cut-first task (T10.1–T10.5, T8.4) is additive and says what happens if it is skipped. T11.1 no longer depends on a cut-first task.
- **It is anchored in real data.** The tests assert against the real question-class table, never a hard-coded 115. The sponsor names, first-paragraph rule and other-chamber fallback were each checked against the real `bills.json` and roll calls.
- **One vocabulary.** Positions, chips, seals, person rows and cv-home rules each have one Python owner and one JS twin. The reviews removed five parallel re-implementations (chip_parts, RC_SHORT_CHIP, slot* helpers, homePersonRow, the second `_og_image`), and tests assert they stay gone.
- **Every server-rendered route has an error state.** home, /state, /about, /methodology, /member and /bill all render through `_page_content` or a guarded equivalent, so they return the §4 error state with a 503 instead of a bare 500. The 404 handler is guarded as well.
- **The completeness-check residuals are absorbed.** T11.3 scripts the cv-home write and `#mine` removal, including a replay of the cached 302. The Latest Vote heading is `h2.kicker#latest-vote-h`. The seat-not-person ballot copy is covered by a copy-rules test.

---

## Fixed during this check

- **T10.4 step 5, the `serve_bill` strip edit (P1 level).** The step told the builder to replace `return _serve_html("bill.html", _bill_meta(page), content)`. After G7's error-state fix, T7.4 renders through `_page_content(...)` and returns `_serve_html("bill.html", meta, content, status_code=status)`, so that line does not exist. Building from the stale snippet would have silently dropped `status_code`, and a render failure on a bill page would then return the error body with a 200 status and cacheable headers. The step now replaces T7.4's real return line. It passes `status_code=status` and adds the strip only when `status == 200`, the same way the member route does.
- **The plan's Status line** now reads `Reviewed — Ready`, and the review path is on its own line.

---

## Production readiness blockers (P0) and high priority (P1): every item and how it was resolved

Two P0s (G3 #1, G7 #1) and 54 P1s. I checked every row against the plan text by grepping for the fix: the named test, helper or string, or the absence of the removed one.

| Log | Sev | Task | Problem (first sentence) | Resolution in the plan |
|---|---|---|---|---|
| G1 #1 | P1 | T1.8 | get_bill_page sets `has_summary = self.displayable_summary(bill_id)`, but T1.5 defines displayable_summary as returning the summary dict or None, not a bool. | Fixed: T1.8 `has_summary = bool(self.displayable_summary(bill_id))`; Interfaces give `-> dict \| None`. |
| G1 #2 | P1 | T1.3 | sponsor_name builds the name from firstName + lastName, and on real bills.json that gives wrong public names. | Fixed: T1.3 sponsor_name parses fullName; tests expect `Rep. Cathy McMorris Rodgers (WA)` and cover 117-hres-8 and Rescom. |
| G1 #3 | P1 | T1.8 | The new /api/bills/{c}/{t}/{n}/votes calls roll_call_extras for every roll call on the bill. | Fixed: T1.8 `_pick_rendered` limits file reads; `_vote_file_reads` tests assert `len(reads) <= 2`. |
| G2 #1 | P1 | T2.2 | test_names_codes_ordinals_and_dates_match_python does `members = json.loads(members.json)` and then `[m["name"] for m in members]`. | Fixed: T2.2 parity test reads `...read_text())["members"]`. |
| G2 #2 | P1 | T2.4 | The task-map dependencies don't match what the tasks actually need. | Fixed: T2.3 and T2.4 Depends-on lines and map.json now [T2.1, T2.2] / [T1.3, T1.10, T2.1, T2.3]. |
| G3 #1 | P0 | T3.3 | The browse panel's search goes to GET /api/search/bills. | Fixed: T3.3 step 5 applies `bills.LIST_FIELDS` to /api/search/bills too; `/api/search/bills?q=act` is in CHECKED_ENDPOINTS. |
| G3 #2 | P1 | T3.3 | In app.js, addLatestVoteStateLine calls `chip(m.position)` without options. | Fixed: app.js uses `chip(m.position, { chamber: vote.chamber })`, and a test asserts it. |
| G3 #3 | P1 | T3.2 | The card's outcome seal takes its variant from a text-prefix guess: `_status_parts(seal_text)` treats any text starting with 'Adopted by the' as final. | Fixed: `_SIMPLE_RESOLUTIONS = ("hres", "sres")` decides final; parametrized card tests cover the joint/simple cases. |
| G3 #4 | P1 | T3.3 | Step 13 verifies server-rendered content with `grep -c`. | Fixed: T3.3 step 13 uses `grep -o ... \| wc -l`. |
| G3 #5 | P1 | T3.3 | test_other_pages_keep_their_old_shells asserts that /state?code=FL, /member?id=S001217, /bill?… and /about link /static/css/styles.css and not site.css. | Fixed: replaced by self-updating `test_other_pages_serve_their_own_shell`. |
| G3 #6 | P1 | T3.3 | Step 9's CSS block redefines many rules T2.1 already owns, with different values: .state-links (flex instead of T2.1's 2/4-column grid, which also cancels the ≥880 grid rule), .bill-row (T2.1 already puts a border-top on it, so… | Fixed: T3.3 step 9 limited to selectors T2.1 does not define, with a `wc -c` budget check. |
| G4 #1 | P1 | T4.2 | Home module 4 is mounted with `document.getElementById('find').after(block)`. | Fixed: T4.2 mounts into `getElementById('home-reps')`; a test asserts it. |
| G4 #2 | P1 | T4.2 | app.js re-implements the person row as homePersonRow/homeSignalLine/homeVacantRow, and re-implements readRememberedHome, HOME_STATE_NAMES and focusHomeFinder. | Fixed: app.js uses site.js `personRow`; a test asserts `homePersonRow`/`readRememberedHome` are absent. |
| G4 #3 | P1 | T4.1 | `chip_parts` and `_CHIPS` duplicate T1.2's `render.position_chip(vote) -> {text, variant, short}` and disagree with it. | Fixed: `chip_parts`/`_CHIPS` gone; `_latest_vote_fields` calls `position_chip`. |
| G4 #4 | P1 | T4.2 | Step 2 says 'Replace the whole of tests/test_state_overview.py'. | Fixed: T4.2 step 2 replaces only the baseline endpoint block and keeps T1.6's section. |
| G4 #5 | P1 | T4.1 | The escaping-registry step does not work against T1.3's file. | Fixed: standalone `DELEGATION` parametrized escaping test. |
| G4 #6 | P1 | T4.2 | serve_state calls the renderers directly, not through T3.1's `_page_content(build, meta)`. | Fixed: serve_state renders every 200 branch through `_page_content`; a 503 test is added. |
| G4 #7 | P1 | T4.2 | The Step 12 CSS block redefines rules that T2.1's site.css already styles. | Fixed: step 12 is an exact delta; T2.1 owns the only `.person {` rule. |
| G5 #1 | P1 | T5.1 | The /privacy copy in step 11 (and the matching test_privacy_page expectation) says "Whether you revealed party labels is kept only for this browsing session in this tab and is never sent to us." The code does not do that. | Fixed: privacy copy departs from the spec sentence (flagged for the PR body under 'Copy changed from the spec'); tests assert 'never sent to us' is absent. |
| G5 #2 | P1 | T5.1 | Step 17 adds two `@pytest.mark.xfail(strict=True)` tests: test_party_reveal_is_never_persisted_in_local_storage and test_privacy_third_party_claim_holds_no_font_hosts. | Fixed: both tests are self-scoping (legacy-marker exemption; pytest.skip until static/fonts exists) — no xfail markers remain. |
| G5 #3 | P1 | T5.1 | The task claims §7.6 "error copy" and F61, but /about and /methodology call `_trust_counts()` directly and never use T3.1's `_page_content`. | Fixed: `_trust_counts` failures render PAGE_ERROR_SENTENCE with 503; the 404 handler guards get_member_counts; tests added. |
| G6 #1 | P1 | T6.1 | Step 8's escaping test `test_member_t61_blocks_escape_hostile_strings` fails for s="&amp;". | Fixed: `_assert_member_safe(out, s, echoes)`, plus a separate hostile FEC-id money case. |
| G6 #2 | P1 | T6.3 | Step 5.4 says to replace `return data if show_party else _strip_party(data)` in `get_member_detail`, but T1.7 step 9 already rewrote that function to `if not show_party: return _strip_party(data)` followed by `return {**data, "… | Fixed: T6.3 step 5.4 is written against T1.7's code and keeps `speaker_votes` on the reveal path. |
| G6 #3 | P1 | T6.3 | T1.7's `tests/test_member_page.py::test_votes_default_shape_is_unchanged_for_the_old_member_page` asserts `set(data) == OLD_VOTES_KEYS`, which includes "scorecard". | Fixed: T1.7's test becomes `test_votes_default_flat_shape_after_member_switch`; the file is in the git add. |
| G6 #4 | P1 | T6.3 | The new `serve_member` calls `_serve_html("member.html", meta, render_member_page(page))` directly and bypasses T3.1's `_page_content`. | Fixed: serve_member uses `_page_content(build, meta)`; a 503 test is added. |
| G6 #5 | P1 | T6.3 | `member.js initFilters` submits the record form on every `change` of the topic/position selects and the checkbox, which navigates away. | Fixed: no submit-on-change; the test asserts `requestSubmit`/`.submit()` are absent. |
| G7 #1 | P0 | T7.4 | Step 9 adds `.your-reps, .vote-by-state, .what-it-does, .official, .fact-box { border-top: 3px double var(--navy); margin-top: var(--s10); padding-top: var(--s6); }`. | Fixed: the module wrapper is `section.section.official-summary-section`; there is no new double-rule rule; a test asserts `3px double` is not in the bill CSS block. |
| G7 #2 | P1 | T7.1 | Step 6 calls `RENDERERS.extend([...])` and says RENDERERS is a list of (name, fn) pairs. | Fixed: self-contained `BILL_RENDERERS` parametrized test. |
| G7 #3 | P1 | T7.2 | Two registry entries can never pass T1.3's `assert_escaped`. | Fixed: `render_your_reps_slot` is tested for constancy, not by the escaping registry. |
| G7 #4 | P1 | T7.4 | Step 9 CSS contains `.linklike { … font: inherit; … }`. | Fixed: `.linklike` removed; Forget comes from `rememberedLine()` (.btn--secondary). |
| G7 #5 | P1 | T7.3 | The slot decides 'The {House\|Senate} has no recorded vote on this bill in our data.' with `repRelation(null, label, Boolean(slotRenderedBlock(chamber)))`, which only looks for a rendered block. | Fixed: T1.8 falls back to the other chamber's newest roll call (`test_other_chamber_falls_back_to_its_newest_roll_call`); T7.3 checks `[data-chamber]`. |
| G7 #6 | P1 | T7.3 | `slotPersonRow` builds `a.person > span.photo + span.person-name + span.person-seat + span.chip` with no `span.person-body`. | Fixed: slot rows use `personRow(member, home.state, slotSignal(...))`. |
| G7 #7 | P1 | T7.3 | T7.3 re-implements the cv-home rules already in T2.3: `slotReadHome`/`slotWriteHome`/its own Forget/`slotRememberedLine` in place of `readHome`/`rememberDistrict`/`forgetHome`/`rememberedLine`. | Fixed: T7.3 uses readHome/rememberDistrict/rewriteMastheadLink/rememberedLine; a test asserts the slot* duplicates are gone. |
| G7 #8 | P1 | T7.2 | Spec §7.1 says one glossary table is shared by the Python and JS formatters, positions included. | Fixed: `RC_SHORT_CHIP`, `RC_SHORT` and `rcRow(` asserted absent; rows use `position_chip`/`rcTableRow`. |
| G7 #9 | P1 | T7.1 | The fact box renders `<button … data-share>Share</button>` with no status node. | Fixed: the fact box renders `<p class="share-status" role="status"></p>`; asserted. |
| G7 #10 | P1 | T7.4 | The new `serve_bill` calls `render_bill_page(...)` directly. | Fixed: serve_bill uses `_page_content` with the bill code as H1 and returns the status. |
| G7 #11 | P1 | T7.1 | `_first_paragraph` takes the text before the first `</p>`. | Fixed: `first_paragraph_text` skips title-only paragraphs; the 119-hr-4795-shaped test expects 'This bill prohibits'. |
| G8 #1 | P1 | T8.3 | T5.1 adds `test_privacy_third_party_claim_holds_no_font_hosts` to tests/test_copy_rules.py as `@pytest.mark.xfail(strict=True)`, with the reason text "...all shells until T8.3 self-hosts the fonts); remove this marker in the ta… | Rejected, and the rejection holds: T5.1's font-host test uses pytest.skip until static/fonts exists; the plan has no xfail markers. |
| G8 #2 | P1 | T8.4 | T8.4 defines `_og_image(kind: str) -> dict` (returns `{path: "/static/og/{kind}.png", width, height, alt}`, placed below `_zip_finder_meta`) and passes it as the `image` key. | Fixed: one `_og_image(kind, key=None) -> dict` with a site-relative path; T10.1 extends it. |
| G8 #3 | P1 | T8.1 | T8.1 rewrites work that T6.3 and T7.4 already landed and tested. | Fixed: T8.1 leaves serve_member/serve_bill and their meta builders untouched; `_truncate_on_word` gone; `_og_title` uses cut_words. |
| G8 #4 | P1 | T8.3 | The step-11 scroll-width smoke passes unquoted URLs: `node shoot.mjs … fonts-member=http://127.0.0.1:8011/member?id=S000148 fonts-bill=http://127.0.0.1:8011/bill?congress=119&type=hr&number=4795`. | Fixed: every name=url pair is quoted. |
| G9 #1 | P1 | T9.1 | gates.mjs does not accept the shoot.mjs-style `name=url` arguments that group 10 relies on. | Fixed: T9.1's gates.mjs parses `name=http://…` pairs (PAIRS). |
| G9 #2 | P1 | T9.1 | The `targets` check puts `.site-footer a` in REQUIRED and tests it before the inline-text exemption. | Fixed: REQUIRED lists `.footer-links a` and `.site-footer button`. |
| G9 #3 | P1 | T9.1 | Gated axe failures are certain here but not planned, and the one triage fix given contradicts earlier groups. | Fixed: T9.1 step 4 changes the card and fact box to `<section>` and moves .feedback-btn into the footer before the first gate run (see residual R2 for the pre-T9.1 window). |
| G10 #1 | P1 | T10.1 | Step 5 adds a second module-level `def _og_image(kind, key) -> str` that returns an absolute URL string. | Fixed: T10.1 extends T8.4's single `_og_image`. |
| G10 #2 | P1 | T10.1 | `_og_entities` is scanned when `app.main` is imported. | Fixed: T8.4 cases run under `patch.object(main_module, "_og_entities", frozenset())`. |
| G10 #3 | P1 | T10.2 | Step 1 says to wrap the result line, the group list and the pager in one `<div data-record-list>` while the count line, nominations line and form stay outside, with 'no visual change'. | Fixed: two swap targets, `data-record-result` and `data-record-list`. |
| G10 #4 | P1 | T10.4 | Step 4 changes Recent votes' h2 to `id="recent-votes"`. | Fixed: the strip links `#recent`; no rename. |
| G10 #5 | P1 | T10.4 | Step 5's route code does not match the T6.3/T7.4 routes it edits. | Fixed in part by the G10 author; the serve_bill half was fixed inline in this check (see 'Fixed during this check'). |
| G10 #6 | P1 | T10.5 | Step 5 tells the builder to call `render_member_fact_strip(voted, total, ...)` right after the fact line in `render_member_header`. | Fixed: `total`/`voted` are set before the branch in T10.5. |
| G11 #1 | P1 | T11.2 | The step 5 grep gate "§6.1 exactly one :root block in site.css" counts every `:root {…}` match. | Fixed: the gate counts `(?m)^:root\s*\{` only. |
| G11 #2 | P1 | T11.2 | The step 5 gate "§3.3 no pushState" runs `git grep pushState -- static`. | Fixed: the gate matches `pushState\s*\(`. |
| G11 #3 | P1 | T11.1 | T11.1 step 3(b)/(c) adds the shoot.mjs-style `name=http://…` argument form to gates.mjs, but T10.2 (10-G10.md line 953), T10.4 (line 1520) and T10.5 (line 1762) already call `node gates.mjs 'member=http://…' …` during group 10,… | Fixed: the pair parser moved into T9.1; T11.1 only extends PAGES. |
| G11 #4 | P1 | T11.2 | The step 8 rebase conflict fix for data/synced/sync_metadata.json takes main's file and re-adds only `ai_summaries_updated`, which it computes from the git commit date of ai_summaries.json. | Fixed: the conflict resolution keeps `ai_summaries_digest` through T1.10's helper. |
| G11 #5 | P1 | T11.2 | The step 8 rebase onto origin/main (new roll calls, member_votes, regenerated index and overviews) happens after T11.1 has already produced gates.json, precheck.txt and gates-summary.txt. | Fixed: the rebase moved to T11.1 step 0, before any evidence; T11.2 step 8 sends a mid-group sync back to step 0. |
| G11 #6 | P1 | T11.3 | Spec §8 item 13 makes "a keyboard-only pass and a VoiceOver/NVDA pass" part of the definition of done before the PR. | Fixed: the VoiceOver row is 'Pending (Joseph, before merge)', excluded from green; the PR body lists it under 'Before merging'. |

---

## Medium priority (P2)

The group authors addressed all 85 per-group P2s. Each group's log has at least as many changes as issues. Here is how they were handled:

- **Duplicate helpers were collapsed** (G1 #4, #5; G3 #11; G4 #8, #9; G6 #7, #8, #15; G7 #13, #14, #17). T1.4's `roll_call_key` and `render.parse_threshold` are now single definitions. The escaping and privacy harnesses are shared, and the ZIP form comes from T3.1.
- **Wrong expected counts and grep shapes were corrected** (G3 #10; G4 #12; G6 #10; G9 #4; G10 #10, #11; G1 #10). Every count check on server-rendered content uses `grep -o … | wc -l`.
- **Workflow gating** (G1 #9, G10 #12). The state-overview build/commit steps are gated on `steps.validate_member_votes.outcome == 'success'` (the same gate 'Commit member votes' uses), and the share-card steps are gated on `steps.validate_all.outcome == 'success'`.
- **Copy and spec fidelity** (G4 #17, G5 #4/#6/#8/#9, G6 #6, G7 #15, G11 #9, G11 #13). The vacancy separator, methodology sentences, the §4.3 m4 'Motion' label, the split-ZIP land-area note and the report wording all now match the spec.
- **Cross-group dependencies** (G3 #12, G9 #8/#9, G11 #7). The footer links are repointed in T5.1. T9.1 keeps the earlier dialog check, the retired shell test is self-updating, and the cut-first detector matches the real commit bodies.

**Deferred P2s.** These carry no risk to correctness or to the schedule.

- **R1 — T3.2 / T7.1 / T3.3: landmarks are wrong until T9.1.** From commit 3 to commit 9, the Latest Vote card and the bill fact box are named `<aside>`s inside `<main>`, and the desktop `.feedback-btn` sits outside any landmark. axe would flag both, but no gate runs axe before T9.1. T9.1 step 4 fixes both with an idempotent edit before its first gate run, so the merged PR is correct.
- **R2 — T4.1: partial-ZIP rows still link with `#mine`.** On a partial ZIP such as 73949, the 'This is my district →' link keeps `#mine`. The plan reads spec §5.1's 'never a cv-home write' as covering only the landing page and the 302. With that reading, tapping the link is an explicit choice, which matches the Global Constraints list of allowed writes. If Joseph wants the literal reading, T4.1's renderer and test must change, and T11.3 must assert zero `main a[href$="#mine"]` on `/state?code=TX&zip=73949`.
- **R3 — T7.1 Step 3: a stale fallback remains.** The step still carries a defensive fallback for a title-paragraph rule that T1.8 now implements. It does nothing, and its contract test still pins the rule.
- **R4 — Phases 10 and 11 have duplicate headings.** Each has both a `## Phase N` heading and a `## Group N` heading, a leftover from assembly. The indexer handles this correctly: the ranges hold one `### Task` each, and the last range stops before `## Spec coverage`.
- **R5 — Workflow bot commits have no trailer.** Three `git commit -m "data: rebuild … [automated]"` lines (T1.4, T1.6, T10.1) sit inside `.github/workflows/weekly-sync.yml` content. These are CI bot commits, not plan commits, and match the existing workflow's style, so they correctly carry no Co-Authored-By trailer. All 44 plan commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

The cross-group check listed one more residual: the 'Checkpoint 2026-10-06' note that existed only in map.json. It is **resolved in the assembled plan**. The note is the gate text at the top of Phase 8, and it also appears in Design Decisions and Execution notes.

---

## Rejected feedback

Every rejection below was checked against the plan, the code or the spec, and each holds.

- **G8 #1 (P1, T8.3 must remove T5.1's strict xfail marker).** Holds. In the assembled plan, `test_privacy_third_party_claim_holds_no_font_hosts` calls `pytest.skip` while `static/fonts/` is absent, and T5.1 step 18 expects 'no xfailed'. T8.3 creates `static/fonts/` and removes the Google links, so the test starts running and passes. I also confirmed that only the eight shells reference Google Fonts in the baseline. `styles.css` and `broadsheet.css` have no `@import`, so the CSS glob cannot fail between T8.3 and T9.1.
- **G4 #9 (P2, part rejected: import `COVERED_STATE_NAMES` from data_service into render.py).** Holds. T1.7 imports render at the top of data_service, so the reverse import would be circular. The duplication dropped from three sources to two.
- **G4 #11 (P2, partly applied: the `.remember-status` live region).** Holds. Focus moves to the remembered line, so a live region there would announce the same thing twice.
- **G7 P2 `_bill_meta` competing contracts.** Holds. T8.1 now leaves T7.4's `_bill_meta(page)` untouched. Its Interfaces line says 'Not touched'.
- **G7 #13 (P2, part rejected: reuse `_ai_line` on the bill page).** Holds. The spec's §4.4 m4 bill line is one sentence ending in a period, with two links in the same paragraph. The shared `SUMMARY_ATTRIBUTION` constant prevents the wording from drifting.
- **G7 #14 (P2, part rejected: add `aria-describedby` for `#reps-zip-status`).** Holds. The status node is `role=status`, so its text is announced. A describedby parameter would be an optional improvement.
- **G10 T10.5 P2 (part rejected: add `record_last_date`).** Holds. T1.7's `get_member_page` already returns `last_vote_date`.
- **G10 T10.2 P2 (part rejected: expect one `requestSubmit` hit).** Holds. After G6 #5, member.js has no submit-on-change handler, so the check expects 0 hits.
- **G10 #5 (P1, part rejected: the literal serve_member edit).** Holds for the member route. Its edit keeps `_page_content(build, meta)` and `status_code=status` and adds the strip only when the status is 200. The serve_bill half had the stale-target defect described under 'Fixed during this check', and I fixed it the same way.

---

## Residuals (open after this check)

| Sev | Task | Problem |
|---|---|---|
| P2 | T3.2 / T7.1 / T3.3 | R1. Named `<aside>` inside `<main>` and the feedback button outside a landmark from commit 3 to commit 9. T9.1 step 4 fixes both before any axe gate runs. |
| P2 | T4.1 | R2. Partial-ZIP rows keep 'This is my district →' with `#mine`. This is an explicit tap, but if Joseph reads spec §5.1 literally, T4.1 and T11.3 need a change. |
| P2 | T7.1 | R3. The inert defensive fallback in Step 3 duplicates T1.8's first-paragraph rule. |
| P2 | Phases 10–11 | R4. Duplicate `## Phase N` / `## Group N` headings (cosmetic; the index is valid). |

---

## Readiness checklist

**Mechanical checks**
- [x] `index_tasks.py` exits 0. There are 40 tasks (T1.1–T11.3), each range holds exactly one `### Task` heading, no range is empty, and the last range (T11.3) ends before `## Spec coverage`. I re-ran it after this check's edits.
- [x] No TBD, TODO, 'add validation', 'similar to Task' or FIXME placeholders.
- [x] Every task id referenced in the plan exists. Every map.json `depends_on` and every plan `Depends on`/`Consumes` line points to an earlier task.
- [x] All 44 plan commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. The 3 CI bot commit lines are exempt (R5).
- [x] The Finding coverage table lists all of F01–F63. 59 are resolved by named tasks. 4 are partial with a stated deferral: F38 `/bills` page, F53 Cloudflare Cache Rule, F62 narrative regeneration, F63 Render plan.

**P0 blockers**
- [x] G3 #1: /api/search/bills rows are allowlisted and party-leak tested (T3.3).
- [x] G7 #1: no double rule on `.official`; the wrapper is `.official-summary-section` (T7.2/T7.4).

**P1 recommended**
- [x] All 54 per-group P1s are resolved or rejected with a reason that holds (see the table).
- [x] T10.4's serve_bill edit keeps the 503 error state (fixed during this check).

**Constraints and PM decisions**
- [x] Joseph's confirmations A–D are in the Global Constraints and tasks: narratives withdrawn and `/summary` deleted, Recent votes as the eight most recent decisive votes, needs_review summaries withheld, merge-by 2026-10-13 with the checkpoint and the cut order.
- [x] PM decisions: About names 'Joseph Garcia, an independent volunteer' and uses the feedback form only. There is no Render plan change. The arguments module is removed. The 2024-cycle FEC sentence is included. Ballot copy describes the seat.
- [x] Hard constraints are carried as Global Constraints and grep gates: literal `<title>`/`</head>`, CSP, no new innerHTML, feedback.js hooks, only the two sanctioned data files, no URL-shape changes, no framework.
- [ ] Before merge, not a plan defect: Joseph's VoiceOver pass (§8 item 13) and the two §12.4 ops steps listed in the PR body.
