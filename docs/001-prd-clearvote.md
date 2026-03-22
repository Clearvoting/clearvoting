# ClearVote (ClearVoting) -- Product Requirements Document

**Version:** 1.2
**Created:** 2026-03-21
**Last Updated:** 2026-03-21
**Status:** Retroactive PRD -- documents what exists today. Updated with Joseph's vision review and expansion strategy.
**URL:** ClearVoting.org
**Target Milestone:** November 2026 midterm elections -- ClearVote must be a useful, complete, and discoverable tool that voters actually use when they go to vote.

---

## Mission

This is a democracy and we want people to feel empowered and informed, so that they are more likely to vote. ClearVote exists because transparency without accessibility is not real transparency -- and informed voters are the foundation of accountable government.

## Problem Statement

Most Americans cannot tell you how their congressional representative voted last week. Public trust in Congress is at historic lows -- just 17% of Americans say they trust the federal government to do what is right (Pew Research, December 2025), and 85% say elected officials don't care what people like them think. Around 7 in 10 Americans have an unfavorable view of Congress.

The information to change this already exists. Every congressional vote is a public record, published on Congress.gov and Senate.gov. But that data is buried in government-style interfaces, written in legal jargon, and scattered across multiple sites. The people who most need this information -- everyday voters trying to evaluate their representatives -- are the least equipped to find and understand it. The result is not just an information gap -- it is a participation gap. People who don't feel informed don't feel empowered, and people who don't feel empowered don't vote.

Existing tools that try to help (GovTrack, VoteSmart, Congress.gov itself) either overwhelm users with dense data, show party affiliations so prominently that they short-circuit independent evaluation, assign ideology "scores" that introduce editorial framing, or are built for professional audiences (lobbyists, government affairs teams) rather than regular citizens.

**ClearVote exists for the person in the middle** -- someone who cares enough to look something up but doesn't have the time, expertise, or patience to navigate government websites. They want a simple answer to: "What has my representative actually done?" And when they get that answer -- clearly, without spin -- they feel empowered to participate.

ClearVote solves the translation layer, not the data layer. The data is public. The problem is that nobody has made it genuinely accessible, genuinely unbiased, and genuinely understandable for the average American. The goal is not transparency for transparency's sake -- it is transparency that leads to action: more people voting, more people voting informed, and more representatives held accountable.

---

## Market Research

### Competitive Landscape

The congressional transparency space contains four tiers of tools, each serving different audiences with different trade-offs.

#### Tier 1: Established Government Transparency Platforms

**GovTrack.us** (founded 2004) is the most comprehensive open government website -- every bill, every vote, every member, 20+ years of history. But it is dense and information-heavy, not beginner-friendly. It assigns ideology and leadership "scores" (inherently opinionated framing), shows party affiliation prominently everywhere, and runs on a small team of 4 part-time staff funded by ads and Patreon. GovTrack ended its bulk data API in 2017 when Congress began publishing its own structured data.

**VoteSmart** (votesmart.org) is a nonpartisan resource that covers both federal and state legislators with human-curated "key votes." Its strengths are strict impartiality policies and issue-based filtering. Its weaknesses are a dated interface, limited coverage (only curated votes get summaries), and curation lag. It still shows party affiliation prominently.

**Congress.gov** is the authoritative source -- every bill, amendment, vote, and committee action. But it has a government-style interface, CRS summaries written in legal/policy jargon, no member voting profiles (you search by bill, not by person), and no visualizations. It is raw legislative data, not a transparency tool for voters.

#### Tier 2: Professional Tracking Tools (Not Direct Competitors)

**LegiScan** tracks 175,000+ bills per year across all jurisdictions. API-first, built for government affairs professionals and lobbyists. Paid tiers from $25-$3,000/year. No plain-language summaries, no anti-bias features.

**Quorum** is an enterprise government affairs platform with real-time monitoring, CRM integration, and analytics. Enterprise pricing ($10K+/year). Used by congressional offices. Serves organizations, not individual citizens.

**BillTrack50** covers legislation and regulations across all 50 states. Has AI-powered research tools but is primarily for advocacy organizations. Paid tracking starts at $1,000/state/year. Scorecards introduce bias.

**FastDemocracy** is a mobile-first bill tracker with real-time alerts. Clean app (4.7 stars on iOS) but still advocacy-focused with no AI summaries, no voting record visualization, and no anti-bias framing.

#### Tier 3: Citizen Engagement / Action Apps

**Resistbot** (text RESIST to 50409) helps citizens contact representatives via text. 40+ million messages sent. But it is action-focused, not information-focused -- it doesn't help you understand what your rep does, just helps you contact them.

**5 Calls** provides pre-written scripts for calling representatives. Simple and focused but inherently framed/opinionated. No voting records or bill analysis.

**VoteCheck** (votecheck.app) is a newer entrant providing nonpartisan congressional voting information with "easy-to-understand summaries." All data from official sources. Most directly comparable to ClearVote, though it does not appear to use AI-generated summaries or hide party affiliations by default.

**Congress Vote Tracker** (iOS app, 4.3 stars) has a clean mobile interface with member profiles, contact info, committees, and campaign contributions. Mobile-only, no AI summaries, shows party affiliation prominently.

#### Tier 4: AI-Powered Newcomers

**BringBackData Congressional Summaries** is a blog/experiment using multiple LLMs to summarize bills. Not a full product -- no voting records, no member profiles, no anti-bias design.

**ProPublica Represent** (SHUT DOWN, July 2024) was the closest mainstream competitor -- a well-funded nonprofit doing legislative transparency with a Congress API used by developers. Its shutdown creates a recognized gap in the civic tech landscape that ClearVote can fill.

### Market Trends

- **Public trust in government at historic lows.** 17% trust the federal government (Pew, Dec 2025). This creates both urgency and opportunity for transparency tools.
- **AI making plain-language translation viable.** LLMs can now summarize dense legislative text in everyday English at scale -- something human curation (VoteSmart's approach) cannot match for breadth.
- **ProPublica's exit leaves a gap.** The most recognized transparency tool for developers and civic tech shut down in 2024. No replacement has emerged with comparable reach.
- **2026 midterm elections.** Congressional races create natural demand for voting record data. Election cycles are the highest-leverage moment for voter education tools.
- **Partisan fatigue.** Growing segment of Americans want to evaluate representatives without party framing. ClearVote's hidden-party-labels design speaks directly to this.

### Gaps and Opportunities

No existing tool combines all three of ClearVote's core differentiators:

1. **AI-generated plain-language bill summaries** with strict neutrality guardrails (12 rules, no adjectives, no editorial framing)
2. **Party affiliation hidden by default** -- the only tool that asks "What if you saw the votes first?"
3. **Person-first, voter-first design** -- start with YOUR representative, see THEIR record, understand in plain English

The professional tools (Quorum, LegiScan, BillTrack50) are not competitors -- they serve a completely different market (organizations, not individual voters). The citizen tools (Resistbot, 5 Calls) focus on action without understanding. The established platforms (GovTrack, VoteSmart, Congress.gov) focus on data without translation.

---

## Target Users

### Primary: The Busy Informed Citizen

Not political junkies. Not lobbyists. Not activists with strong partisan identities.

ClearVote is for the **busy person who cares about their country but is too busy to look this up**. They have a job, kids, responsibilities. They WANT to be informed citizens -- they care about who represents them and how those representatives vote -- but they do not have time to research every candidate and bill. They are not apathetic; they are overwhelmed. When election day comes, they want to make a good decision, but the information is either buried, biased, or incomprehensible.

ClearVote respects their time by making the information instantly accessible. One visit, a few clicks, plain English -- that's all it should take to know what your representative has actually done.

**Characteristics:**
- Cares about their country and wants to vote responsibly, but has limited time for political research
- Works full-time, may have kids or family obligations -- political research competes with everything else
- Votes in most elections but does not follow C-SPAN or read legislative text
- Gets political information from social media, news, and conversations -- not government websites
- Frustrated by partisan framing and wants to form their own opinion
- Has a smartphone and a browser but will not download a specialized app or create an account
- Reading level comfort: everyday English, not policy jargon
- May not know their congressional district number

**What they do today:** Mostly nothing. Some Google their representative's name and read whatever partisan news article comes up first. A few find Congress.gov but leave confused. Almost none use GovTrack or VoteSmart. Many go to the polls feeling underprepared and wish they had a simple way to check the record beforehand.

### Secondary: The Civic Educator

Teachers, librarians, and community organizers who want a tool they can point people to -- something simple, visual, and unbiased enough to use in non-partisan educational settings.

### Who This Is NOT For

| Audience | Why not | What they should use instead |
|----------|---------|------------------------------|
| Lobbyists / government affairs | Need 50-state coverage, alerts, CRM integration | Quorum, LegiScan |
| Journalists | Need raw data, FOIA tools, real-time alerts | Congress.gov, ProPublica data |
| Political operatives | Need opposition research, messaging tools | Paid political platforms |
| Strong partisans | Want confirmation, not neutral info | Cable news, partisan scorecards |

---

## Jobs to Be Done

| Job Type | Job Statement |
|----------|---------------|
| Functional | When I hear about a congressional vote on the news, I want to quickly see how my representative voted and what the bill actually does, so I can form my own opinion based on facts. |
| Functional | When it's election season, I want to see my representative's full voting record across issues I care about, so I can judge them on their actions rather than campaign promises. |
| Functional | When I'm curious about a bill, I want to read what it does in plain English -- not legal jargon -- so I can understand it without a law degree. |
| Functional | When I want to know who funds my representative, I want to see campaign finance data alongside their voting record, so I can decide for myself if there's a connection. |
| Emotional | When I look up political information, I want to feel informed rather than manipulated, so I can trust that I'm getting the real story. |
| Emotional | When I evaluate my representative, I want to feel like I'm making a fair, independent judgment, so I can be confident in my opinion. |
| Social | When I discuss politics with friends or family, I want to cite specific votes and facts, so I can be the person who actually checked the record instead of repeating what they heard on TV. |

---

## User Stories

These reflect what ClearVote actually does today -- each maps to shipped functionality.

1. **As a voter, when I visit the home page, I want to select my state and optionally my district, so I can see the representatives who represent me.** (Home page state/district lookup)

2. **As a voter, when I see my representatives listed, I want to view them without party labels by default, so I can evaluate them on their votes before knowing their party.** (Party toggle -- hidden by default, reveal on demand, persisted via localStorage)

3. **As a voter, when I click on a representative, I want to see a quick snapshot of their voting participation and patterns, so I can decide whether to dig deeper.** (Expandable member cards on home page with inline summary, participation rate, yea/nay ratio, and AI narrative snippet)

4. **As a voter, when I view a representative's full profile, I want to see their voting record organized by issue area with an AI-generated narrative summary, so I can understand their stances without reading hundreds of individual votes.** (Member detail page with "At a Glance" AI narrative, issue scorecards across 12 categories, tabbed interface with Voting Record / Sponsored Bills / Campaign Finance)

5. **As a voter, when I browse bills, I want to search by keyword or browse by topic, so I can find legislation about issues I care about.** (Bill search + 12 issue category tags on home page)

6. **As a voter, when I view a bill, I want to read an AI-generated plain-language summary alongside the official summary, so I can understand what the bill does in everyday English.** (Bill detail page with "What This Bill Does" AI provisions, issue categories, both-sides arguments, and collapsible official CRS summary)

7. **As a voter, when I view a bill's roll call vote, I want to see a visual breakdown of how senators voted (pie chart + table), so I can quickly grasp the outcome without reading raw data.** (Senate vote visualization with SVG donut charts, animated segments, vote table sorted by yea/nay/present/not voting)

---

## Success Criteria

### Real-World Impact (Primary Goals)

If ClearVote works, two things happen in the real world:

1. **Higher voter turnout, especially in local and midterm elections.** People vote when they feel informed. If ClearVote makes congressional voting records genuinely accessible, more people will feel confident enough to show up -- particularly in the lower-turnout elections where every vote matters most.

2. **Greater alignment between representatives' voting behavior and what their constituents actually care about.** When voters have transparent, easy-to-consume information about how their representatives vote, they can hold those representatives accountable. Representatives who know their constituents are watching vote differently than those who assume nobody is paying attention.

These two outcomes are the ultimate measure of whether ClearVote matters: (1) the information is transparent and easy enough to consume that people actually use it, and (2) that usage translates into accountability -- voters making decisions based on the record, not the party label or the campaign ad.

**The forcing function: November 2026 midterms.** ClearVote has a concrete deadline. By November 2026, it must be a useful, complete, and discoverable tool that real voters actually use when they go to vote. Everything -- feature development, data coverage, SEO, outreach -- should be oriented toward that milestone.

### Leading Indicators (Signals We're on Track)

These product metrics don't matter on their own -- they matter because they signal progress toward the real-world goals above.

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Monthly active users viewing at least one member profile | 1,000+ by Nov 2026 | People are finding and using the tool -- prerequisite for any real-world impact |
| Party toggle stays OFF for the majority of sessions | >60% of sessions never reveal party labels | Users are engaging with the information on its merits, not filtering by team |
| AI summary coverage | 90%+ of synced bills have AI summaries | Comprehensive coverage means users can find what they need -- incomplete data breaks trust |
| Campaign finance coverage | 90%+ of synced members have FEC data | Follow-the-money is a key accountability signal for voters |
| Data freshness | Voting data no more than 7 days old | Stale data erodes credibility; voters need current records, especially near elections |
| Feedback submissions | 5+ per week from real users | Real people are engaged enough to tell us what's working and what isn't |
| Page load time | <3 seconds to interactive on mobile | Busy people won't wait -- speed is respect for their time |
| AI summary neutrality | 0 flagged summaries per 100 | Trust is the product; one biased summary can undo all credibility |
| Test suite health | 180+ tests passing, 0 regressions | Reliability underpins everything -- the tool must work when voters need it |

### Anti-Metrics (deliberately NOT optimized)

- **Time on site** -- ClearVote wants users to understand quickly, not scroll endlessly
- **Pages per session** -- A voter who finds their rep's record in 2 clicks is well-served
- **Partisan engagement** -- No "red team vs. blue team" usage patterns

---

## Scope

### In Scope (shipped and working today)

- **Member lookup by state and district** -- Select state, optionally enter district, see representatives
- **Member profile pages** -- Photo, name, chamber, state/district, service history, AI narrative summary, issue scorecards (12 categories), voting record with pagination, sponsored bills list, campaign finance (FEC data)
- **Party toggle** -- Party affiliation hidden by default across all pages (member cards, member detail, vote tables). User can reveal/hide at any time. Preference persisted in localStorage.
- **AI bill summaries** -- Plain-language provisions (3-7 bullet points), one-liner, issue categories, direction classification (in_favor/against/neutral), both-sides arguments (supporters say / critics say). Generated by Claude Sonnet with 12 strict neutrality rules.
- **AI member narratives** -- 3-5 sentence factual summary of each member's voting patterns. Generated by Claude Sonnet with strict anti-bias rules and data constraint alignment.
- **Bill browsing and search** -- Recent bills list with pagination, keyword search, 12 issue category tags for topic browsing
- **Bill detail pages** -- Bill header with status, AI summary section, official CRS summary (collapsible), sponsors with links to member profiles, roll call votes with visual charts, link to Congress.gov
- **Senate vote visualization** -- SVG donut pie charts (animated), vote count legend, per-party breakdown charts (on reveal), sortable vote table with name/state/party/vote columns
- **Multi-congress data** -- Voting records across 117th, 118th, and 119th Congresses (2021-present)
- **Feedback system** -- Floating feedback button on every page, context-aware (captures page type, member/bill context), saves to Google Sheets with JSONL fallback
- **Mobile responsive design** -- Hamburger navigation, responsive tabs (short labels on mobile), sticky name bar on member pages, touch-friendly interactions
- **Security hardening** -- Rate limiting (slowapi), SSRF protection on bill URLs, security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy), input validation (bioguide ID format, state code, bill type), defusedxml for Senate XML parsing
- **Data freshness indicator** -- Footer shows "Data last updated [date]" from health endpoint
- **About page** -- Mission statement, "What We Do Differently," "How We Stay Unbiased" (12 AI guardrails explained), data sources, "What We Don't Do" list
- **Accessibility** -- Skip-to-content links, ARIA labels, keyboard navigation, semantic HTML, aria-live regions for async content
- **Cache-busting** -- Static asset versioning on server restart

### Not in Scope (deliberately excluded today)

- **User accounts or personalization** -- Adds complexity and privacy obligations without clear user demand yet
- **Real-time data sync** -- Data is pre-built via manual sync script. Automated sync is a Phase 1 priority but not shipped.
- **Bill or member alerts/notifications** -- No email, push, or in-app notifications. Browse-only.
- **State legislature coverage** -- Federal Congress only. State expansion is high-impact but high-effort (Phase 4 future).
- **Native mobile app** -- Web-only (responsive). PWA or native app is a future consideration.
- **Action pathways** -- No "contact your rep," "register to vote," or letter-writing features. ClearVote is about understanding, not advocacy.
- **Scoring or ranking** -- ClearVote does not score, rank, or rate representatives. No ideology scores, no report cards, no "grades."
- **Editorial content** -- No blog posts, no opinion pieces, no "bill of the week" picks. Data only.
- **House vote visualization** -- House votes are synced and stored but the bill detail page currently only renders Senate vote charts. House vote display is a known gap.
- **SEO optimization** -- No meta tags for individual member/bill pages, no structured data, no canonical URLs. SEO is a Phase 1 priority.
- **Advertising or monetization** -- ClearVote is free with no revenue model. Sustainability through low infrastructure costs and potential future grants.

---

## Key Assumptions and Risks

| Assumption | Risk if Wrong | How to Validate |
|------------|---------------|-----------------|
| Everyday voters want to see voting records if presented in plain language | Product solves a problem people don't actually have (they never look up this info regardless of format) | Track organic traffic growth after SEO optimization; monitor feedback for "I never knew I could see this" signals |
| Hiding party labels changes how people evaluate representatives | Users immediately toggle party on and never engage with the party-blind view | Track party toggle usage rate -- if >50% of sessions reveal party within 10 seconds, the hypothesis is weak |
| AI-generated summaries with strict guardrails are perceived as unbiased | Users perceive AI summaries as biased regardless of guardrails, eroding trust | Monitor feedback for bias complaints; conduct spot-check audits; compare user trust signals between AI and CRS summaries |
| Congress.gov API and Senate.gov XML remain freely available and stable | Government data sources change format, rate limit, or shut down | Pre-synced data model insulates runtime from API changes; sync failures are logged and recoverable |
| Pre-synced flat-file JSON architecture scales adequately | Traffic spikes (election season) overwhelm a single-process server | Static JSON architecture handles reads well; monitor response times; add CDN for static assets if needed |
| Claude API costs remain manageable for summary generation | API costs rise significantly, making AI summaries unsustainable | Summaries are generated once per bill during sync (not on every page view); fallback to CLI mode exists; monitor per-bill cost |
| ClearVote will not be co-opted by partisan actors | A political campaign or partisan group uses ClearVote selectively to support their narrative, associating ClearVote with a side | Maintain strict neutrality in all public communications; About page clearly states non-partisan position; refuse all endorsement requests |

---

## Competitive Alternatives

What do people do today instead of using ClearVote? Applying April Dunford's positioning framework:

**Most common alternative: Nothing.** The vast majority of Americans do not look up their representative's voting record at all. They absorb political information passively through social media, cable news, and conversations. ClearVote's real competition is apathy and information friction, not other transparency tools.

**Second alternative: Google search.** A voter who is curious enough to look something up Googles their representative's name. They land on a news article (partisan framing), a Wikipedia page (generic), or Congress.gov (confusing). None of these answer the question "What has my rep done on issues I care about?" in plain language.

**Third alternative: Partisan sources.** Voters who do engage with voting records often find them through partisan lenses -- interest group scorecards (NRA rating, League of Conservation Voters score, Heritage Action scorecard). These are explicitly framed to support a conclusion. ClearVote is the anti-scorecard.

**Fourth alternative: Existing transparency tools.** A small percentage of highly engaged citizens use GovTrack, VoteSmart, or similar platforms. These users are not ClearVote's primary audience -- they are comfortable with data-dense interfaces. However, ClearVote may attract users who tried these tools and found them overwhelming.

**ClearVote's positioning:** For the curious American voter who wants to understand what their representative actually does in Congress, ClearVote is the only tool that presents voting records in plain language, without party labels, and without telling you what to think. Unlike GovTrack (data-dense), VoteSmart (curated/limited), or partisan scorecards (biased by design), ClearVote uses AI with strict neutrality guardrails to translate every vote into everyday English and lets you evaluate your representative on their actions, not their team jersey.

---

## Recommended Approach (Current Architecture)

ClearVote uses an **offline-first data pipeline** architecture, chosen for simplicity, cost, and resilience:

1. **Sync script** (`sync.py`) pulls data from Congress.gov API and Senate.gov XML, runs AI summary generation via Claude API, and saves everything as flat JSON files to `data/synced/`. This is a 9-step pipeline covering members, Senate votes, House votes, bills, bill text, AI summaries, member vote profiles, bill-vote linkage, and AI member narratives. The sync runs manually and targets specific states and congresses.

2. **FastAPI backend** loads all synced JSON into memory at startup via a `DataService` singleton. API routers serve data from memory -- no database queries, no external API calls at request time. This makes the app fast, simple, and resilient to upstream API outages.

3. **Vanilla HTML/CSS/JS frontend** -- four pages (home, member, bill, about) with no build tools, no framework, no dependencies beyond Google Fonts. JavaScript is organized into focused modules (app.js, member.js, bill.js, vote.js, feedback.js). CSS uses custom properties for theming.

4. **AI layer** uses Claude Sonnet to generate two types of content: bill summaries (provisions, one-liner, issue categories, direction, both-sides arguments) and member narratives (3-5 sentence voting pattern description). Both services use strict system prompts with explicit neutrality rules. A writer/grader loop during sync catches and corrects bias or jargon violations.

5. **Security** includes rate limiting (slowapi), SSRF protection (allowlisted domains for bill URL fetching), security headers (CSP, X-Frame-Options, etc.), input validation, and defusedxml for XML parsing.

6. **Deployment** is a single-process Dockerized app on Render, auto-deploying from `main`. Infrastructure cost is near zero.

**Why this approach was chosen:**

- **Flat files over databases:** The dataset is small enough (thousands of records, not millions) that in-memory JSON is faster and simpler than any database. No ORM, no migrations, no connection pooling.
- **Pre-synced over real-time:** Eliminates runtime dependency on government APIs. The app works even if Congress.gov is down. AI summaries are generated once per bill, not on every page view, keeping costs predictable.
- **Vanilla JS over frameworks:** Four pages with moderate interactivity do not justify React's complexity. No build step means faster development and simpler deployment.
- **Single-process over microservices:** One binary serves everything. Easy to reason about, easy to deploy, easy to monitor.

---

## Future Opportunities

The following are not part of the current product but represent validated directions based on competitive analysis, user research signals, and the existing Opportunity Solution Tree (documented in `docs/product-strategy.md`).

### Expansion Philosophy

ClearVote's deliberate strategy is to **perfect the experience before expanding**. The product currently covers 4 states (NY, FL, CA, TX) -- enough to build, test, and refine the core experience with real users across diverse political contexts. Expanding prematurely means every future improvement (new visualizations, better summaries, UX changes) has to be rolled out across more data, more edge cases, and more surface area. That makes iteration slower and more expensive.

The sequence is intentional:
1. **Phase 1: Perfect the core experience** with the current 4 states. Get real user feedback. Iterate on digestibility, comprehension, and trust until the product genuinely serves the busy voter it's built for.
2. **Phase 2: Expand to purple/swing states** (see Strategic Note below). This serves both the mission and the fundraising model.
3. **Phase 3: Broader national, local, and multilingual expansion** once the experience is proven and the organization has resources to maintain quality at scale.

This is not a limitation -- it is a strategic choice. Doing fewer states well is more valuable than doing 50 states poorly.

### Strategic Note: Purple States and Fundraising

A key insight for ClearVote's expansion and fundraising strategy: **expand to purple/swing states first when raising money.** People who care about future elections -- donors, foundations, civic-minded individuals -- are most motivated to fund tools that could inform voters in competitive states where outcomes are uncertain and every informed voter matters.

Target purple states for Phase 2 expansion: **Arizona, Georgia, Nevada, Pennsylvania, Wisconsin, Michigan, North Carolina.**

This reframes expansion as a fundraising narrative: "Help us bring transparent voting records to the states where informed voters can have the greatest impact on election outcomes." It aligns mission (voter empowerment) with donor motivation (competitive elections) without compromising neutrality -- ClearVote doesn't tell anyone how to vote, it just ensures they can see the record.

The expansion sequence becomes:
1. Perfect the experience (4 current states)
2. Purple states (fundraising-aligned, 7 swing states)
3. Remaining states + local government + multilingual support

### Data Visualization and Digestibility

The current product is text-heavy. A key design direction for the next phase of development is to **make voting data more digestible through graphs and data visualizations** -- enabling users to grasp patterns at a glance rather than reading through tables and text.

Planned visualization types:
- **Voting alignment charts** -- How often does a member vote with/against their party? With/against the other party?
- **Attendance/participation rates** -- Visual progress bars showing how often a member shows up to vote
- **Bill topic breakdowns** -- Pie or donut charts showing the distribution of bills a member has voted on by issue category
- **Party-line voting percentages** -- Simple bar graphics showing what percentage of votes follow party line vs. independent
- **Vote outcome visualizations** -- Extending the existing Senate donut charts to House votes and adding trend-over-time views

This is not cosmetic polish -- it directly serves ClearVote's mission. The target user is busy and time-constrained. A well-designed chart communicates in 3 seconds what a paragraph takes 30 seconds to read. Graphs turn ClearVote from "a place to look up votes" into "a place to understand your representative's patterns."

### Prioritized Opportunities

1. **Automated data sync** (P0) -- Replace manual sync with a scheduled pipeline so voting data stays current without human intervention. This is a table-stakes capability that every competitor has.

2. **SEO optimization** (P0) -- Member and bill pages should be optimized for searches like "[representative name] voting record." These searches spike during election season and represent the highest-leverage organic discovery channel.

3. **Data visualization / graphs** (P0) -- Implement voting pattern charts, participation bars, topic breakdowns, and alignment visualizations to make the data instantly digestible. See "Data Visualization and Digestibility" above.

4. **Complete House vote visualization** (P1) -- House votes are synced but not yet rendered on bill detail pages. This is a known gap in the current bill view.

5. **Social share cards** (P1) -- OG images and "share this record" functionality for member and bill pages. Enables organic viral distribution when major votes happen.

6. **"Contact your rep" links** (P1) -- Simple outbound links to official contact pages. Low effort, adds utility without crossing into advocacy.

7. **Non-profit incorporation** (P1) -- 501(c)(3) or 501(c)(4) status would enable grant applications (Knight Foundation, Democracy Fund) and establish organizational credibility. Prerequisite for the purple-states fundraising strategy.

8. **Email alerts** (P2) -- "Your rep just voted on something you care about" notifications. High-impact for retention but requires user accounts and email infrastructure.

9. **Embeddable vote widgets** (P2) -- Let news sites and blogs embed a "how did [rep] vote?" widget. Distribution through others' audiences.

10. **Purple state expansion** (P2) -- Add AZ, GA, NV, PA, WI, MI, NC once the core experience is proven. Fundraising-aligned milestone.

11. **State legislature expansion** (P3/future) -- State politics affects daily life more than federal for most Americans. High-impact but high-effort. Requires evaluating new data sources (OpenStates, LegiScan API, direct scraping).

12. **Multilingual support** (P3/future) -- Spanish-language summaries as a starting point, given ClearVote's initial coverage of states with large Spanish-speaking populations (FL, CA, TX).

13. **Bill page UX improvements** (P1) -- Two issues found during QA:
    - Category tags on bill detail pages look clickable but are display-only. Make them link to a filtered bill search by category.
    - "Back to results" link disappears on mobile after scrolling. Add a sticky back button on mobile so users can always navigate back.

---

*This is a retroactive PRD documenting ClearVote as it exists on March 21, 2026. It reflects shipped reality, not aspirations. Future opportunities are separated from the core product description. Update this document when major new capabilities ship.*

---

## Design Specs

### Design Audit Findings (March 2026)

**Current state:** The shipped UI is functional and well-structured but has significant design system gaps and missed opportunities for data visualization. Key findings:

**What works well:**
- Solid semantic HTML structure with skip links, ARIA labels, and keyboard navigation
- Clean information hierarchy on member cards and bill items
- Party toggle mechanism is well-implemented and clever
- Mobile hamburger menu and responsive tab labels
- Skeleton loading states and proper error handling

**What needs improvement:**

1. **Off-brand design system.** The current CSS uses a light theme (white backgrounds, blue accents, red primary buttons) that does not match the project design system (midnight blue + gold palette, Lora/Playfair Display/Inter typography). The current palette reads as "government website" rather than the calm, premium aesthetic defined in the design system. The font `Lora` is not loaded at all -- only Inter and Playfair Display are imported.

2. **Text-heavy, visualization-light.** The member profile page is almost entirely text and lists. The "At a Glance" card presents participation rate and yea/nay ratio as text strings. Issue scorecards are expandable text lists. There are no charts for voting patterns, no visual representation of topic breakdown, no attendance progress bars. The PRD explicitly identifies data visualization as P0.

3. **Weak hero/landing experience.** The hero section is a single heading with a subtitle. There is no explanation of what ClearVote does, no visual guide for the user journey, no trust signals. A first-time visitor has to guess what to do. The "How It Works" concept is entirely missing.

4. **No state-level comparison view.** Representatives are shown as individual cards. There is no way to visually compare participation rates, voting patterns, or support rates across a state's delegation. A busy voter wants to scan and compare -- the current design forces them to open each profile individually.

5. **Missing visual hierarchy on member cards.** The home page member cards show name, chamber, and state as text. There is no visual indicator of voting participation or patterns. The snapshot (expandable) helps but requires a click to see any data.

6. **Mobile responsiveness gaps.** The category grid uses CSS grid with fixed minimums that can overflow. The comparison table (if built) would need a mobile-specific layout. Touch targets on category tags are at the minimum but not generous.

### Mockup Files

Three HTML/CSS mockup files are saved at `mockups/` in the project directory. Each is self-contained and can be opened by double-clicking in a browser.

| File | Screen | Key Changes |
|------|--------|-------------|
| `mockups/home.html` | Home / Landing | Midnight blue + gold theme, "How It Works" section, data visualization on member cards (participation rings, yea/nay bars), improved hero with clear value proposition |
| `mockups/member.html` | Member Profile | Full data visualization suite: vote breakdown donut chart, attendance progress bar, topic-by-topic horizontal bar charts showing support vs. opposition, stat dashboard cards, redesigned vote list with issue tags |
| `mockups/state-overview.html` | State Overview (new page) | Comparison table with inline participation bars and vote-split bars, aggregate state stats, participation ranking visualization, filter/sort controls, mobile card layout |

### Design Decisions

**Dark theme adoption:** The mockups apply the full midnight blue + gold design system. This is not just cosmetic -- the dark palette creates a distinct, premium feel that differentiates ClearVote from the bright, cluttered look of government websites. It signals "this is different."

**Data visualization approach:** All charts are pure CSS and inline SVG -- no JavaScript charting libraries. This keeps the zero-dependency philosophy intact. Visualization types used:
- **Participation rings** (SVG circle with stroke-dashoffset) on member cards for instant readability
- **Yea/nay split bars** (CSS flexbox) for vote breakdown at a glance
- **Donut charts** (SVG stroke-dasharray) for the full vote breakdown on member profiles
- **Horizontal bar charts** (CSS grid + flexbox) for topic-by-topic voting patterns
- **Progress bars** (CSS width transitions) for attendance rate
- **Ranking bars** (CSS) for state-level participation comparison

**Typography:** Three-font system from the design system:
- Playfair Display for display headings (h1, section titles)
- Lora for body text (narratives, descriptions, bill titles)
- Inter for UI elements (labels, stats, navigation, buttons, metadata)

**Comparison table:** The state overview introduces a desktop comparison table that shows all representatives side by side with inline visualizations. On mobile, this collapses to cards with the same data. This directly serves the "scan and compare" need of a busy voter.

**"How It Works" section:** Added to the landing page between the lookup card and results. Three steps (Pick your state, See the record, Form your own opinion) in plain language. Reduces the "What is this?" friction for first-time visitors.

### Accessibility Considerations

- All mockups maintain WCAG AA contrast ratios. The design system's `--text-primary` (#E8E0D4) on `--midnight` (#0C1B33) achieves 12.5:1 ratio (AAA). Gold on midnight achieves approximately 7:1 (AAA for large text).
- SVG visualizations include text labels so the information is not color-dependent.
- Semantic HTML throughout: `<nav>`, `<main>`, `<section>`, `<article>`, `<table>` with proper scoping.
- All interactive elements have focus-visible styles and meet the 44px minimum touch target.
- The comparison table hides on mobile in favor of cards -- not just shrunk, but redesigned for the form factor.

### Layout Rationale

The mockups follow a mobile-first progressive enhancement approach:
- **480px (phone):** Single-column, stacked cards, simplified stats, touch-optimized
- **768px (tablet):** Two-column grids for stats, table still hidden, cards expand
- **1024px (desktop):** Full comparison table visible, three-column stat dashboards, side-by-side donut + legend

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-21 | Initial retroactive PRD documenting shipped product |
| 1.1 | 2026-03-21 | Joseph's vision review: Added Mission section with empowerment framing. Reframed Success Criteria around real-world impact (voter turnout, representative accountability) with product metrics repositioned as leading indicators. Sharpened target user from "curious voter" to "busy person who cares but doesn't have time." Added November 2026 midterm deadline as forcing function in metadata and success criteria. Wove empowerment-leads-to-action theme through Problem Statement. |
| 1.2 | 2026-03-21 | Joseph's second feedback round: (1) Restructured Future Opportunities around phased expansion strategy -- perfect the experience first with 4 current states before scaling, explicit philosophy section. (2) Added "Data Visualization and Digestibility" as a key design direction with specific chart types (alignment, participation, topic breakdown, party-line voting). Elevated to P0 in prioritized opportunities. (3) Added "Purple States and Fundraising" strategic note -- expand to swing states (AZ, GA, NV, PA, WI, MI, NC) as Phase 2 to align mission with donor motivation. (4) Renumbered and re-prioritized all future opportunities to reflect new phasing. |
| 1.3 | 2026-03-22 | Design audit and mockups: Added "Design Specs" section with audit findings, three HTML/CSS mockup files (home, member profile, state overview), design decisions documenting the shift to midnight blue + gold theme, CSS/SVG data visualization approach, and accessibility considerations. |
