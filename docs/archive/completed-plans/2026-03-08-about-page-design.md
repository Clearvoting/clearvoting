# About Page & Mission Statement — Design

## Context

ClearVote's homepage has a hero section ("See how your representatives vote. Facts only. No opinions. No spin.") but no explanation of the project's mission, what makes it different, or how visitors can help. First-time visitors have no way to understand the purpose behind the tool.

## What We're Adding

### 1. Homepage — Mission Link

A small text link below the existing tagline: "Learn about our mission and how you can help →" linking to `/about`. Plus an "About" link in the site nav across all pages.

### 2. About Page (`/about`)

Static content page with three sections:

**Why We Built This** — Personal/civic origin story. We couldn't find a simple way to see how representatives vote. Congressional records are public but buried in jargon. Democracy works better when everyone can understand what's happening.

**What We Do Differently** — Scannable bullet points:
- Plain language — no jargon, accessible to everyone
- No party bias — affiliations hidden by default
- Just the facts — no editorials, no ratings, no spin
- Real data — sourced from Congress.gov and Senate.gov

**Help Us Improve** — Short ask + button linking to a Google Form for feedback. Opens in new tab.

## Technical Approach

- New `static/about.html` — same header/footer pattern as existing pages
- New `/about` route in `app/main.py`
- About page styles added to `static/css/styles.css`
- Nav updated in all HTML files (index, member, bill, about)
- No JavaScript needed — pure static content
- Feedback form: placeholder Google Form URL, swappable later
