# ClearVote Product Strategy

**Date:** March 20, 2026
**Status:** Living document — update quarterly or after major shifts

---

## 1. Vision

**One sentence:** Every American can see exactly how their representatives vote — in plain language, without bias, for free.

**The world we're building toward:** Voters evaluate their elected officials on what they actually do in Congress, not on party labels, cable news soundbites, or campaign rhetoric. ClearVote makes the public record genuinely public — accessible, understandable, and neutral.

**The belief underneath:** Democracy works better when citizens can easily understand what their government is doing. The information already exists (Congress.gov, Senate.gov, FEC). The problem is that it's buried in jargon, scattered across sites, and presented in ways that reward partisan thinking. ClearVote solves the translation layer, not the data layer.

---

## 2. Who This Is For

### Primary User: The Curious Voter

**Not** political junkies. **Not** lobbyists. **Not** activists with strong partisan identities.

ClearVote serves the person in the middle — someone who cares enough to look something up but doesn't have the time, expertise, or patience to navigate Congress.gov. They want to know: *"What has my rep actually done?"*

### Jobs to Be Done (JTBD)

#### Job 1: "Help me understand what my representative actually votes for"
- **When** I hear about a vote on the news or see debate on social media
- **I want to** quickly see how my senator or House member voted and what the bill actually does
- **So I can** form my own opinion based on facts, not headlines

> **Functional:** Find voting records, read plain-language summaries
> **Emotional:** Feel informed, not manipulated; feel capable of understanding government
> **Social:** Be able to discuss politics with confidence ("Actually, here's what they voted for...")

#### Job 2: "Help me evaluate my rep without party bias"
- **When** it's election season or I'm deciding whether my representative deserves my vote
- **I want to** see their full record across issues I care about
- **So I can** judge them on their actions, not their party label

> **Functional:** Browse voting history by policy area, see patterns over time
> **Emotional:** Feel like I'm making a fair, independent judgment
> **Social:** Be the person who actually checked the record instead of voting by party line

#### Job 3: "Show me where the money comes from"
- **When** I'm suspicious about why a representative voted a certain way
- **I want to** see who's funding their campaigns
- **So I can** decide for myself if there's a connection between money and votes

> **Functional:** View donor data alongside voting records
> **Emotional:** Feel empowered by transparency, not cynical
> **Social:** Hold representatives accountable with real data

### Who This Is NOT For

| Audience | Why not | What they should use instead |
|----------|---------|------------------------------|
| Lobbyists / gov affairs | Need 50-state coverage, alerts, CRM integration | Quorum, LegiScan |
| Journalists | Need raw data, FOIA tools, real-time alerts | Congress.gov, ProPublica data |
| Political operatives | Need opposition research, messaging tools | Paid political platforms |
| Strong partisans | Want confirmation, not neutral info | Cable news, partisan scorecards |

---

## 3. Current State Assessment (March 2026)

### What's shipped and working

| Capability | Status | Notes |
|------------|--------|-------|
| Member lookup by state | Live | All 50 states + DC |
| Member voting profiles | Live | 117th–119th Congress, tabs for votes/bills/finance |
| AI bill summaries | Live | Plain-language with 12 neutrality guardrails |
| AI member narratives | Live | "At a Glance" voting pattern descriptions |
| Issue scorecards | Live | 12 policy categories with yea/nay counts |
| Campaign finance | Live | FEC data for ~51/80 initial members |
| Bill detail pages | Live | Summary, arguments (for/against), vote breakdown |
| Bill search + browse | Live | Keyword search + category filtering |
| Party toggle | Live | Hidden by default, persistent via localStorage |
| Mobile responsive UI | Live | Hamburger nav, responsive tabs, mobile-optimized |
| Feedback collection | Live | Google Sheets + JSONL fallback |
| Dark patriotic design | Live | Midnight blue + gold, Playfair Display + Inter |

### Development velocity

~30 meaningful commits in March 2026, covering: full member page redesign, campaign finance integration, mobile UX overhaul, 7-phase design review, animation system, and data sync improvements. The codebase is production-quality with security headers, rate limiting, and a comprehensive test suite.

### What's NOT shipped yet

- No real-time data sync (data is pre-built via sync script)
- No user accounts or personalization
- No bill/member alerts or notifications
- No state-level coverage (federal only)
- No action pathways ("contact your rep," "register to vote")
- No mobile app (web-only, though responsive)
- No SEO or public launch strategy
- Campaign finance data incomplete (~65% coverage, OpenSecrets application pending)

---

## 4. Opportunity Solution Tree

Using the Teresa Torres framework to map from desired outcome → opportunities → solutions.

### Desired Outcome
**More Americans evaluate their representatives based on voting records rather than party affiliation.**

This is the behavior change ClearVote exists to create. It's measurable (surveys, usage patterns, party toggle usage) and directly connected to the mission.

```
OUTCOME: More Americans evaluate reps based on voting records
│
├── OPPORTUNITY 1: People can't find or understand voting records
│   ├── Solution: AI plain-language bill summaries ✅ SHIPPED
│   ├── Solution: Member voting profiles with issue breakdown ✅ SHIPPED
│   ├── Solution: "At a Glance" AI narratives ✅ SHIPPED
│   └── Solution: Bill search by keyword + category ✅ SHIPPED
│
├── OPPORTUNITY 2: Party labels short-circuit critical thinking
│   ├── Solution: Hide party affiliation by default ✅ SHIPPED
│   ├── Solution: Show party only on explicit opt-in ✅ SHIPPED
│   └── Solution: Present both sides of bill arguments ✅ SHIPPED
│
├── OPPORTUNITY 3: People don't know what their specific rep has done
│   ├── Solution: State → member lookup ✅ SHIPPED
│   ├── Solution: Issue scorecards per member ✅ SHIPPED
│   ├── Solution: Campaign finance tab ✅ SHIPPED (partial)
│   └── Solution: Multi-congress historical records ✅ SHIPPED
│
├── OPPORTUNITY 4: People don't come back — no reason to return
│   ├── Solution: "Your rep just voted" email/push alerts 🔲 NOT STARTED
│   ├── Solution: "Bills in your issue areas" digest 🔲 NOT STARTED
│   └── Solution: Bookmarked members / followed issues 🔲 NOT STARTED
│
├── OPPORTUNITY 5: People want to DO something after learning
│   ├── Solution: "Contact your rep" links 🔲 NOT STARTED
│   ├── Solution: Voter registration links 🔲 NOT STARTED
│   └── Solution: Share a member's record (social cards) 🔲 NOT STARTED
│
├── OPPORTUNITY 6: People don't know ClearVote exists
│   ├── Solution: SEO-optimized member/bill pages 🔲 NOT STARTED
│   ├── Solution: Embeddable vote widgets for news/blogs 🔲 NOT STARTED
│   ├── Solution: Civic tech partnerships 🔲 NOT STARTED
│   └── Solution: "How did your rep vote on [trending bill]?" social content 🔲 NOT STARTED
│
└── OPPORTUNITY 7: State and local politics affect daily life more
    ├── Solution: State legislature coverage 🔲 NOT STARTED
    └── Solution: Governor / executive action tracking 🔲 NOT STARTED
```

**Key insight:** Opportunities 1–3 are well-covered. ClearVote's next strategic moves live in Opportunities 4–6 (retention, action, distribution). Opportunity 7 (state coverage) is high-impact but high-effort — it's a future horizon, not a near-term priority.

---

## 5. Strategic Priorities

### Kano Classification

Before prioritizing, classify what matters:

**Must-Haves (table stakes — absence frustrates)**
- Accurate, up-to-date voting data *(partially met — sync is manual)*
- Fast page loads *(met)*
- Mobile-friendly *(met)*
- Working search *(met)*

**Performance Features (more = proportionally better)**
- More states with data → ✅ now all 50 states
- More bills with AI summaries → ongoing
- Better campaign finance coverage → in progress (OpenSecrets pending)
- More congresses of historical data → 117th–119th shipped

**Delighters (unexpected, create disproportionate satisfaction)**
- Party hidden by default → ✅ this is THE differentiator
- AI plain-language summaries → ✅ unique in the market
- "At a Glance" narratives → ✅ no competitor does this
- Both-sides bill arguments → ✅ unique neutral framing

**Takeaway:** The delighters are shipped. The next wave of delight comes from Opportunities 4–6: bringing people back, giving them something to do, and getting ClearVote in front of them in the first place.

### RICE-Scored Backlog

| Initiative | Reach | Impact | Confidence | Effort | Score | Priority |
|------------|-------|--------|------------|--------|-------|----------|
| **Automated data sync** | 3 (all users) | 2 (high — enables freshness) | 90% | 3 weeks | 1.8 | **P0** |
| **SEO optimization** (meta tags, structured data, canonical URLs) | 3 (potential new users) | 2 (high — organic discovery) | 80% | 1 week | 4.8 | **P0** |
| **Social share cards** (OG images, "share this record") | 2 (sharing users) | 2 (high — viral loop) | 80% | 1 week | 3.2 | **P1** |
| **OpenSecrets data integration** | 2 (finance-curious users) | 2 (high — richer finance) | 70% | 2 weeks | 1.4 | **P1** |
| **"Contact your rep" links** | 2 (action-oriented users) | 1 (medium — utility) | 90% | 0.5 weeks | 3.6 | **P1** |
| **Email alerts — "your rep just voted"** | 1 (subscribed users) | 3 (massive — retention) | 60% | 4 weeks | 0.45 | **P2** |
| **Embeddable vote widgets** | 1 (partner sites) | 2 (high — distribution) | 50% | 3 weeks | 0.33 | **P2** |
| **State legislature expansion** | 3 (all users) | 3 (massive — 50x officials) | 40% | 12+ weeks | 0.3 | **P3 (future)** |

### Recommended Sequence

**Phase 1: "Make it real" (next 2–4 weeks)**
- Automated data sync (freshness is a must-have)
- SEO optimization (be discoverable)
- Complete campaign finance coverage (FEC name fix + OpenSecrets when approved)

**Phase 2: "Give people a reason to share" (weeks 4–8)**
- Social share cards / OG images for member and bill pages
- "Contact your rep" outbound links
- "How did [state] reps vote on [trending bill]?" landing pages

**Phase 3: "Bring people back" (weeks 8–14)**
- Email digest — weekly "your rep voted on..." summary
- Followed issues / bookmarked members
- Push notifications (if PWA path)

**Phase 4: "Expand the map" (future horizon)**
- State legislature data (dependent on data source evaluation)
- Governor / executive tracking
- Local ballot measures

---

## 6. Competitive Position

### ClearVote's Moat

Three things no competitor combines:

1. **AI summaries with anti-bias guardrails** — 12 neutrality rules, no adjectives, no editorial framing. GovTrack doesn't summarize. Vote Smart summarizes selectively with humans. Congress.gov uses CRS jargon. Nobody else has AI + neutrality discipline.

2. **Party hidden by default** — This is philosophically unique. Every other platform shows party prominently. ClearVote is the only tool that asks: "What if you saw the votes first?"

3. **Person-first, voter-first design** — Start with YOUR representative. See THEIR record. Understand in plain English. Competitors are bill-first (Congress.gov), data-first (GovTrack), or action-first (Resistbot). ClearVote is understanding-first.

### The ProPublica Gap

ProPublica Represent shut down. It was the closest mainstream competitor — a well-funded nonprofit doing legislative transparency. Its absence creates a recognized gap in the civic tech landscape. ClearVote can fill this gap with a fundamentally better approach (AI + anti-bias).

### Where Competitors Win (and that's fine)

| Competitor strength | ClearVote's response |
|--------------------|-----------------------|
| GovTrack has 20+ years of data | ClearVote covers 117th–119th (6 years). Enough to show patterns. |
| Vote Smart covers state legislatures | Federal focus first. State is Phase 4. |
| LegiScan has real-time alerts | Automated sync (Phase 1) + email alerts (Phase 3) close this gap. |
| FastDemocracy has a native mobile app | Responsive web-first. PWA before native app. |
| Resistbot has action pathways | "Contact your rep" links (Phase 2). Understand first, act second. |

---

## 7. Product Principles

These guide every feature decision:

### 1. Neutrality is the product
ClearVote's value disappears the moment it becomes biased. Every feature must pass the test: "Would a voter from either party trust this?" If the answer is no, don't ship it.

### 2. Understanding before action
ClearVote helps people understand. It is not an advocacy tool. Action pathways (contact your rep, share) are secondary to comprehension. Never push users toward a conclusion.

### 3. Less is more
A voter who understands 3 things clearly is better served than one overwhelmed by 30 data points. ClearVote summarizes, simplifies, and reduces — it doesn't dump raw data.

### 4. Meet people where they are
Most Americans don't know their representative's name, let alone their voting record. Design for the person who's looking for the first time, not the person who already follows C-SPAN.

### 5. Earn trust through transparency
Show data sources. Explain how AI summaries work. Present both sides. Let users toggle party labels on their own terms. Trust is built by giving users control, not by telling them what to think.

---

## 8. Success Metrics

### North Star Metric
**Monthly active users who view at least one member voting profile.**

This captures the core behavior ClearVote exists to enable: someone looking at how their representative votes.

### Supporting Metrics

| Category | Metric | Why it matters |
|----------|--------|---------------|
| **Reach** | Unique visitors / month | Are people finding ClearVote? |
| **Engagement** | Member profiles viewed / session | Are people exploring their reps? |
| **Depth** | Bills viewed per session | Are people going deeper than surface? |
| **Neutrality signal** | % of sessions where party toggle stays OFF | Is the party-blind design working? |
| **Return** | 7-day return rate | Are people coming back? |
| **Sharing** | Social share clicks / month | Is ClearVote spreading organically? |
| **Feedback** | Feedback submissions / week | Are users engaged enough to respond? |
| **Data quality** | AI summary coverage (% of bills) | Is the content layer keeping up? |
| **Finance** | Campaign finance coverage (% of members) | Is the money transparency complete? |

### Anti-Metrics (what we deliberately DON'T optimize)

- **Time on site** — We want people to understand quickly, not scroll endlessly
- **Pages per session** — A voter who finds their rep's record in 2 clicks is better served than one who browses 10 pages
- **Partisan engagement** — We don't want "red team vs. blue team" usage patterns

---

## 9. Growth Strategy (High Level)

ClearVote's growth comes from being useful at the right moment — not from marketing campaigns.

### Organic Discovery (Phase 1–2 focus)

- **SEO:** Optimize member and bill pages for searches like "[representative name] voting record" and "how did [name] vote on [bill]." These searches spike during election season and after major votes.
- **Social sharing:** When a major vote happens, make it dead simple to share "Here's how your rep voted" with a clean preview card.
- **Trending bill pages:** Create lightweight landing pages for bills that are in the news. These have natural search volume.

### Civic Tech Network (Phase 2–3 focus)

- **Partnerships:** Libraries, voter registration orgs, civic education nonprofits. ClearVote is a tool they'd want to recommend.
- **Embeddable widgets:** Let news sites and blogs embed a "how did [rep] vote?" widget. Distribution through others' audiences.

### Election Cycle Spikes (Ongoing)

- Congressional races create natural demand for voting record data
- Prepare for traffic spikes around primaries and general elections
- "Know before you vote" positioning during election season

### What We DON'T Do

- No paid advertising (at least not yet — organic first)
- No dark patterns or engagement tricks
- No data harvesting or email list building without clear value exchange
- No partisan content or hot-take social media

---

## 10. Risks & Mitigations

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **AI bias slips through** — a summary contains loaded language | High | Medium | 12 guardrails in prompt, grader loop, human spot-checks. Feedback system for user reports. |
| **Data freshness** — users see stale voting data | High | High (currently) | Phase 1 priority: automated sync pipeline. |
| **Congress.gov API rate limits or downtime** | Medium | Medium | Pre-synced data model means runtime doesn't depend on Congress.gov. Sync failures are recoverable. |
| **Scale under traffic spike** (election season) | Medium | Medium | Static JSON architecture handles reads well. May need CDN for static assets. |
| **Perception of bias** — despite neutrality, accused of being partisan | High | Medium | Transparent methodology (About page), both-sides arguments, party-hidden-by-default as proof point. |
| **Sustainability** — no revenue model, depends on volunteer effort | Medium | High | Keep infrastructure costs near zero (flat files, single process). Explore grants (Knight Foundation, Democracy Fund). |
| **OpenSecrets application denied** | Low | Low | FEC data remains as fallback. Fix name matching to maximize coverage. |
| **Competitor copies the approach** | Low | Low | Execution and trust are the moat, not the idea. Being first and principled matters. |

---

## 11. What Success Looks Like

### In 3 months (June 2026)
- Automated data sync running — data is always current
- SEO-optimized pages ranking for "[rep name] voting record" searches
- Campaign finance data at 90%+ coverage (OpenSecrets or improved FEC)
- Social share cards generating organic traffic after major votes
- First feedback from real users outside the development team

### In 6 months (September 2026)
- Measurable organic search traffic (target: 5,000+ monthly visitors)
- Email digest with engaged subscriber base
- At least one civic org partnership (library system, voter registration org)
- Clear signal on whether party-blind design resonates (via toggle analytics)

### In 12 months (March 2027)
- ClearVote is a recognized resource in the civic tech space
- Consistent monthly traffic with election-season spikes
- Community of users who share ClearVote links during votes
- Clear data on whether the product changes how people evaluate representatives
- Decision made on state-level expansion based on user demand

---

## 12. Open Questions

These need answers before they become strategic decisions:

1. **Revenue model** — Is ClearVote always free? If so, how is it sustained? Grants? Donations? Or is cost kept so low it doesn't matter?

2. **User accounts** — Do we want people to create accounts? This enables alerts, bookmarks, and personalization — but adds complexity and privacy obligations.

3. **State expansion data source** — If we go state-level, what's the data source? LegiScan API? OpenStates? Direct scraping? Each has trade-offs.

4. **Action pathways depth** — How far does ClearVote go toward "do something"? Link to contact info? Pre-written letter templates? Integration with Resistbot? The further we go, the more we risk looking like an advocacy tool.

5. **AI model dependency** — Summaries currently use Claude. What happens if API costs rise or the model changes behavior? Is there a fallback strategy?

---

*This is a living document. Revisit after each major phase completion or when new user data changes our understanding of what matters.*
