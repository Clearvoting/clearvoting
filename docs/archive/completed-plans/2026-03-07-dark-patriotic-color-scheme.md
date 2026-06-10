# Dark Patriotic Color Scheme Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace ClearVote's midnight blue + gold color scheme with a Dark Patriotic palette (deep navy + patriotic blue accent + American red CTA + cool white text).

**Architecture:** CSS custom property value swap + variable rename (`--accent-gold` → `--accent`, `--accent-gold-dim` → `--accent-dim`), plus a new `--accent-red` token. One JS file update for hardcoded vote colors. Favicon SVG update.

**Tech Stack:** CSS, vanilla JS, SVG

---

### Task 1: Update CSS design tokens and rename accent variables

**Files:**
- Modify: `static/css/styles.css` (`:root` block lines 4-28, plus all 40 references to `--accent-gold`/`--accent-gold-dim`)

**Step 1: Update `:root` design tokens**

Replace the `:root` block (lines 4-28) with:

```css
:root {
    --bg-primary: #0A1628;
    --bg-secondary: #122241;
    --bg-card: #1A2E52;
    --bg-card-hover: #223A63;
    --text-primary: #F0F4F8;
    --text-secondary: #B8C4D4;
    --text-dim: #6B7D94;
    --accent: #4A90D9;
    --accent-dim: #3670B3;
    --accent-red: #C5283D;
    --vote-yea: #4CAF6A;
    --vote-nay: #D64550;
    --vote-absent: #6B7B8B;
    --vote-present: #5B8FB8;
    --border: #243B5E;
    --border-light: #2E4A72;
    --font-body: 'Inter', system-ui, -apple-system, sans-serif;
    --font-heading: 'Playfair Display', Georgia, serif;
    --radius: 8px;
    --radius-lg: 12px;
    --shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 4px 16px rgba(0, 0, 0, 0.4);
    --max-width: 1100px;
    --transition: 0.2s ease;
}
```

**Step 2: Rename all `--accent-gold` references to `--accent`**

Find-and-replace throughout `styles.css`:
- `var(--accent-gold-dim)` → `var(--accent-dim)` (6 occurrences)
- `var(--accent-gold)` → `var(--accent)` (34 occurrences)

**Step 3: Update button styling to use `--accent-red`**

Change `.btn-primary` (lines 254-258) to use red for the CTA button:

```css
.btn-primary {
    background: var(--accent-red);
    color: #fff;
    width: 100%;
}
```

Change `.btn-primary:hover` (lines 260-262):

```css
.btn-primary:hover {
    background: #9E2033;
}
```

Change `.btn-secondary` (lines 269-273) — keep blue outline style:

```css
.btn-secondary {
    background: transparent;
    color: var(--accent);
    border: 1px solid var(--accent);
}
```

Change `.btn-secondary:hover` (lines 275-278):

```css
.btn-secondary:hover {
    background: var(--accent);
    color: #fff;
}
```

**Step 4: Update demo banner to use `--accent-red`**

Change `.demo-banner` (lines 65-72):

```css
.demo-banner {
    background: var(--accent-red);
    color: #fff;
    text-align: center;
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
    font-weight: 600;
}
```

**Step 5: Update skip-link to use `--accent-red`**

Change `.skip-link` background (line 81):

```css
.skip-link {
    position: absolute;
    top: -100%;
    left: 0;
    background: var(--accent-red);
    color: #fff;
    padding: 0.5rem 1rem;
    z-index: 1000;
    font-weight: 600;
}
```

**Step 6: Update party toggle active state to use `--accent-red`**

Change `.party-toggle-inline.active` (lines 396-400):

```css
.party-toggle-inline.active {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
}
```

**Step 7: Update hardcoded rgba vote-color values**

The old vote colors are hardcoded as rgba in several places. Update:

- `rgba(91, 138, 114, ...)` (old vote-yea #5B8A72) → `rgba(76, 175, 106, ...)` (new #4CAF6A)
  - Line 994: `rgba(91, 138, 114, 0.1)` → `rgba(76, 175, 106, 0.1)`
  - Line 995: `3px solid var(--vote-yea)` (already uses variable — no change)
  - Line 1029: `rgba(91, 138, 114, 0.15)` → `rgba(76, 175, 106, 0.15)`
  - Line 1097: `rgba(91, 138, 114, 0.1)` → `rgba(76, 175, 106, 0.1)`
  - Line 1132: `rgba(91, 138, 114, 0.2)` → `rgba(76, 175, 106, 0.2)`

- `rgba(138, 91, 91, ...)` (old vote-nay #8A5B5B) → `rgba(214, 69, 80, ...)` (new #D64550)
  - Line 1137: `rgba(138, 91, 91, 0.2)` → `rgba(214, 69, 80, 0.2)`

- `rgba(42, 64, 96, 0.4)` in scorecard border (line 1113) → `rgba(36, 59, 94, 0.4)` (matches new --border #243B5E)

**Step 8: Commit**

```bash
git add static/css/styles.css
git commit -m "feat: apply Dark Patriotic color scheme to CSS tokens and rename accent-gold to accent"
```

---

### Task 2: Update JavaScript vote colors and favicon

**Files:**
- Modify: `static/js/vote.js` (lines 6-11 VOTE_COLORS, line 131 center text fill)
- Modify: `static/favicon.svg`

**Step 1: Update VOTE_COLORS object in vote.js**

Replace lines 6-11:

```javascript
const VOTE_COLORS = {
    yea: '#4CAF6A',
    nay: '#D64550',
    present: '#5B8FB8',
    absent: '#6B7B8B',
};
```

**Step 2: Update SVG center text color in vote.js**

Line 131 — change `#E8E0D4` to `#F0F4F8`:

```javascript
text.setAttribute('fill', '#F0F4F8');
```

**Step 3: Update favicon.svg**

Replace contents with:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="6" fill="#0A1628"/>
  <path d="M8 16l5 5 11-11" stroke="#4A90D9" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

**Step 4: Commit**

```bash
git add static/js/vote.js static/favicon.svg
git commit -m "feat: update vote colors in JS and favicon to match Dark Patriotic palette"
```

---

### Task 3: Visual verification

**Step 1: Start the server and verify all pages**

```bash
cd ~/Documents/Claude/Projects/clearvote && python app.py
```

**Step 2: Check each page visually**

Open in browser and verify:
- Home page (index.html): Navy backgrounds, blue headings, red "Look Up" button, cool white text
- Bill detail (bill.html): Blue bill numbers, vote pie charts with new colors, red deficit tags
- Member detail (member.html): Blue section headings, vote bars with new colors, red CTA buttons
- Verify no remnants of gold (#D4A853) or warm beige (#E8E0D4) text

**Step 3: Check accessibility contrast**

Verify key contrast ratios meet WCAG AA (4.5:1 for text):
- `#F0F4F8` on `#0A1628` → ~15.8:1 (excellent)
- `#4A90D9` on `#0A1628` → ~5.4:1 (passes AA)
- `#C5283D` on `#0A1628` → ~3.5:1 (use only for large text/buttons, not body text)
- `#B8C4D4` on `#0A1628` → ~9.3:1 (excellent)

**Step 4: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: address any visual issues from color scheme update"
```
