# ClearVote Full Project & UI Review — 2026-07-01

**Scope:** Live site (clearvoting.org, desktop + 375px mobile) walked through by hand; code reviewed
from a fresh worktree at `origin/main` (6f4aa0b) — not the stale local branch. 8 review dimensions
(backend, date/sort pipeline, frontend JS, design/CSS, accessibility, security/privacy, SEO,
AI content quality), 53 findings, every one independently re-verified against the code AND the
live site before making this report. Zero findings were refuted in verification.

**Verdict in one line:** The product's design and plain-language content are genuinely strong —
the weaknesses are almost all in the seams: data plumbing (dates, emails, categories), the
fallbacks when AI content is missing, and the gap between what the footer promises and what
exists.

---

## What's working well (keep this)

- **The broadsheet design is distinctive and credible.** Calm serif hierarchy, restrained
  palette, one dominant action per screen. It reads like a serious civic institution, not a
  startup. The v4 redesign achieved its goal.
- **The plain-language summaries are excellent when present.** "Order the President to pull
  U.S. troops out of Lebanon within seven days" vs. the official title below it is exactly the
  product promise, delivered.
- **Party-hidden-by-default is executed consistently** — homepage delegation, member pages, and
  per-roll-call reveal buttons. It's the site's signature and it works.
- **Accessibility foundation is above average:** skip links, landmarks, `aria-pressed` state
  cards, text-labeled vote bars, real `<table>` semantics for roll calls.
- **Honesty affordances:** AI disclaimer on summaries, data-freshness date in every footer,
  feedback button on every page, "View on Congress.gov" escape hatches, ZIP lookup for districts.
- **Engineering hygiene exists:** 30 test files, server-side meta injection, health endpoint,
  writer/grader loops for AI content.

---

## P0 — Fix before anything else

### 1. Waitlist emails are silently destroyed on every deploy
`app/routers/notify.py` appends signups to `data/notify_signups.jsonl` on Render's **ephemeral
filesystem** — no persistent disk in `render.yaml`, no Sheets path (feedback.py has one; notify
doesn't), file not in git, email not even logged. Weekly sync commits auto-deploy `main`, so the
file is wiped at least weekly. Users get a success message; the list they joined does not exist.
**Fix:** reuse the existing `SheetsService` for notify signups (small change, pattern already
in the codebase).

### 2. The voting record is sorted alphabetically, not chronologically
Vote dates are stored as display strings (`"September 9, 2025,  06:46 PM"`) and sorted as
strings. Verified live: Schumer's record page 1 shows September votes from 2021/2022/2023/2025
interleaved ("September 9" > "September 4" > "September 30"), and the June 2026 votes — the ones
a visitor actually came for — are buried hundreds of positions deep. On a site whose pitch is
"see how your representatives vote," the flagship list is effectively shuffled.

Downstream damage (all verified):
- AI member narratives and issue scorecards are built from "top N" slices of this mis-sorted
  list — so they characterize an arbitrary alphabetical-month sample, not the recent record.
- House votes store ISO dates while Senate votes store display strings — the same `date` field
  has two formats, both rendered raw (`2026-06-04` shows verbatim on member pages).
- Bill-page roll-call headers render the raw strings, double spaces and all.

**Fix (root):** normalize to ISO 8601 at sync time in `sync.py`, format at render (a
`formatISODate` helper already exists in `app.js`), regenerate `member_votes/*.json`, then
regenerate narratives/scorecards. Stopgap: parse-then-sort in `app/routers/members.py`.

### 3. Homepage hero renders garbled legalese in display type
"The Latest Vote" jams the raw official title into a sentence template: *"The Senate rejected
the A joint resolution to direct the removal of United States Armed Forces… by Congress., 47–50"*
— broken grammar, double punctuation, and on mobile it fills the entire first screen, pushing
"Where do you live?" below the fold. The bill (S.J.Res. 185) **has** a plain-language AI headline;
the endpoint that feeds the hero just doesn't join to it. First impression, worst surface.

---

## Trust & brand (the "facts only" promise)

- **Footer "Privacy" and "Methodology & Corrections" links both point to `/about`, which
  contains neither.** A privacy link with no privacy policy — while the homepage collects email
  addresses — is worse than no link. The About page also never explains "how we keep it neutral"
  even though the homepage links to it with exactly that promise. Write a real `/privacy` and a
  methodology section (this was already open item #5 in STATUS.md; the misleading links make it
  urgent).
- **~44% of a senator's vote one-liners are raw legalese** (amendments, motions, older bills) —
  the known "60% gap," now quantified. `vote_one_liner.py` was built for this but is dead code,
  referenced only by tests (and has a latent code-fence parsing bug for when it is wired in).
- **The 12-item issue taxonomy has no foreign-policy bucket**, so all 174 International Affairs
  bills get force-fit into wrong categories — the Iran war-powers resolution is tagged
  "Veterans & Military" directly under an "International Affairs" policy tag on the same page.
  Self-contradicting labels on the two features voters use to filter.
- **6 bill pages ship grader-rejected placeholder summaries** ("AI summary temporarily
  unavailable" — permanent, it's baked into synced data), and the 58 `needs_review` flags are
  consumed by nothing.
- **The 4 newest bills (June 17–24) have no summaries and sit at the top of the browse panel as
  walls of legalese.** This compounds weekly until the `ANTHROPIC_API_KEY` GitHub secret is added
  (STATUS.md item #1 — this review confirms it's now user-visible). The fallback message for them
  is also wrong: it claims the bill is "procedural" (an Iran war-powers resolution is not) and
  slaps the "generated by AI" disclaimer on a hardcoded apology.
- **"Yea/Nay" jargon** in vote pills and roll-call tables violates the project's own
  plain-language principle (homepage says "voted yes"). Small, everywhere.
- **Bill codes render in four formats** ("HCONRES. 84", "HCONRES.84", "HR.2860", "H.Con.Res. 84")
  with no shared formatter. For a legislation site, citing bills wrong reads as a data glitch.
- **Stats disagree on the same screen:** header says 1,044 total votes, donut says 1,043
  (a "Present" vote is dropped from the buckets); `/api/health` rounds 1521/1525 to
  `summary_coverage: 1.0`, defeating the endpoint's stated purpose.
- **Member narratives are templated:** half the corpus opens identically, 10 contain raw
  vote tallies the prompt explicitly bans, and the most common "insight" is that a member of
  Congress votes on congressional procedure.
- **"Supporters say/Critics say" prefixes all 8,539 argument bullets** by prompt mandate,
  duplicating the UI's own column headers up to 4× per column.

---

## Reach (SEO & sharing) — the growth loop is mostly dark

- **~1,675 sitemap URLs serve zero indexable body content** — member/bill/state pages are
  client-fetched after load. Google queues JS rendering; Bing/DuckDuckGo/AI crawlers see a
  spinner. The `_inject_meta` pipeline already exists server-side — extend it to inject a basic
  content block.
- **Client JS overwrites the carefully crafted server `<title>`** with a weaker one on every
  content page (drops bill number, state, "Voting Record" — the tokens people search).
  Delete three lines of JS.
- **No `og:image` anywhere** — every share on iMessage/X/Facebook/Slack is a bare text card.
  For a project that grew via LinkedIn, share cards are the growth surface.
- Bill `<title>`/og:title emitted untruncated (up to 1,955 chars of legalese); canonicals echo
  raw query params (duplicate-content variants self-canonicalize); soft 404s return 200;
  `/favicon.ico` 404s (SVG-only reference); raw `/static/*.html` shells are crawlable duplicates.
- **Render cold start:** first visitor after idle sees Render's "Application loading" splash
  (observed ~30s, with a 503 in console). If traffic matters, the free/starter tier is the
  bottleneck — or add an uptime pinger.

---

## Accessibility — good bones, unfinished rooms

- **Member pages horizontally overflow by 72px at 375px** — the mobile media-query overrides are
  dead due to CSS source order (verified by reproduction). The one real responsive break, on a
  core page.
- **`--text-dim` (#8D9297) fails WCAG AA (2.9–3.1:1) on ~40 live selectors** — vote results, AI
  disclaimers, pagination. The half-done `--ink-meta` remediation shows this was already known;
  finish it (darken one token).
- **The feedback widget isn't an accessible dialog:** no `role="dialog"`, no focus trap, focus
  dropped on close, unlabeled textarea, status changes unannounced. It floats on every page.
- Pagination destroys keyboard focus each page-change; "Get notified" lacks
  `aria-expanded`/`autocomplete="email"`/focus handling on success; PAC-vs-individual donation
  split is color-only; the member-page party toggle announces the opposite of its state;
  aria-live regions read entire roll-call tables aloud; `<th>` lacks `scope`; homepage focus
  styles target a dead class.

---

## Engineering robustness

- **Rate limiting is fully inert in production** (verified: 25 rapid requests to a 10/min
  endpoint, all 200). Uvicorn never trusts Render/Cloudflare forwarded headers, so the limiter
  keys on the proxy IP. Notify and feedback — the two write endpoints — have zero abuse
  protection. Fix: `--forwarded-allow-ips` or a CF-Connecting-IP key func.
- **State overview re-reads every member's ~1.3MB vote file per request** (~2s TTFB live),
  synchronously, inside an async handler on a single worker — a small burst serializes the whole
  site. Cache it; the data only changes on deploy.
- Feedback handler makes a blocking Google Sheets HTTP call on the event loop.
- `GET /bill?congress=119&number=1` (missing `type`) → raw 500 (uncaught `AttributeError`).
- "Load more" increments its offset before the fetch — a transient failure silently skips 20
  bills forever.
- Party toggle state desyncs when a bill has votes from both chambers (first click is a no-op).
- ~120 of 359 class selectors in styles.css (~33%) are dead legacy code shipped to every page —
  and the dead-mobile-override bug above is a direct symptom. broadsheet.css ignores the type
  tokens with 20 ad-hoc font sizes.
- Minor security hardening: CSP `unsafe-inline` styles + missing `form-action`/`base-uri`;
  spreadsheet formula injection possible via feedback text; a tested-but-never-called SSRF guard
  gives false assurance; `sanitizeHtml` allows `javascript:` hrefs (currently blocked by CSP).

---

## Product observations (PM-hat, not bugs)

1. **"Voted yes 69% / no 31%" is the only differentiator shown per House member** — and it's
   low-signal: yes-rate mostly reflects who controls the floor agenda, not what the member
   stands for. Consider surfacing each member's top topic or a recent key vote on the card
   instead.
2. **State selection has no URL.** You can't share "New York's delegation," back-button loses the
   selection, and the server-rendered `/state` pages sit orphaned. Same for topic chips and
   browse state. Small `history.pushState` work, big shareability gain.
3. **The red "NOTIFY ME" button** uses the same red that means "voted No" everywhere else in the
   design language. The one conversion action reads as a warning.
4. **Two identical-looking S.Res. 377 rows** (different procedural votes, same plain headline)
   look like a duplicate-data bug — consider grouping votes by bill.
5. **Senator cards truncate the narrative mid-word** ("On armed f...").
6. **The About page is one-third content, two-thirds empty space** — and it's carrying the load
   of three footer links.

---

## Recommended order of attack

**Week 1 (small fixes, big trust):**
1. Notify signups → Google Sheets (P0, ~1 file).
2. ISO dates at sync + regenerate member_votes (P0 root fix); parse-sort stopgap in the router
   same day.
3. Homepage hero: use the AI one-liner (it exists) with a neutral fallback template.
4. Real `/privacy` + methodology section; repoint footer links.
5. Rate-limit key fix (one flag in render.yaml); favicon.ico route; delete the 3
   `document.title` overwrites.

**Week 2 (content quality at scale):**
6. Add the `ANTHROPIC_API_KEY` GitHub secret (STATUS #1 — unblocks everything downstream).
7. Add "Foreign Policy & National Security" to the taxonomy; regenerate categories.
8. Wire `vote_one_liner.py` into sync for amendments/motions (fix its fence-stripping first).
9. Purge placeholder summaries; honor `needs_review`.
10. Regenerate narratives/scorecards after the date fix (they're built from mis-sorted input).

**Week 3+ (reach & polish):**
11. Server-render a content block for member/bill/state pages; og:image; canonical/title
    truncation fixes.
12. Accessibility batch: contrast token, feedback dialog semantics, mobile overflow, focus
    management.
13. State-overview caching; CSS dead-code purge.

---

*Full machine-readable findings (53 confirmed, 0 refuted, with file/line evidence and verifier
notes): workflow output archived at time of review; each finding above was verified against
origin/main and the live site on 2026-07-01.*
