# ClearVote — Dark Patriotic Color Scheme Design

**Date:** 2026-03-07
**Status:** Approved

## Overview

Redesign ClearVote's color scheme from midnight blue + gold to an American-themed "Dark Patriotic" palette featuring deep navy backgrounds, cool white text, and dual accents (patriotic blue for links/headings + American red for buttons/CTAs).

## Design Rationale

- **Trust & credibility**: Blue is associated with trust, confidence, and sincerity per USWDS guidance
- **American identity**: Red, white, and blue palette directly evokes civic/government context
- **Dual-accent approach**: Prevents confusion between red accent and red "Nay" vote indicators
- **Dark theme retained**: Keeps the modern, app-like feel of the current design
- **Accessibility**: All color combinations maintain WCAG 2.1 AA contrast ratios

## Color Palette

### Background Colors (Deep Navy Spectrum)

| Token | Old Value | New Value | Description |
|-------|-----------|-----------|-------------|
| `--bg-primary` | `#0C1B33` | `#0A1628` | Page background |
| `--bg-secondary` | `#132744` | `#122241` | Header, inputs |
| `--bg-card` | `#1A3055` | `#1A2E52` | Card backgrounds |
| `--bg-card-hover` | `#213A62` | `#223A63` | Card hover states |

### Text Colors (Cool Whites)

| Token | Old Value | New Value | Description |
|-------|-----------|-----------|-------------|
| `--text-primary` | `#E8E0D4` (warm beige) | `#F0F4F8` (cool white) | Main text |
| `--text-secondary` | `#B0A898` | `#B8C4D4` | Secondary text |
| `--text-dim` | `#7A7268` | `#6B7D94` | Dim/hint text |

### Accent Colors (Dual: Blue + Red)

| Token | Old Value | New Value | Description |
|-------|-----------|-----------|-------------|
| `--accent` (was `--accent-gold`) | `#D4A853` | `#4A90D9` | Links, headings, bill numbers |
| `--accent-dim` (was `--accent-gold-dim`) | `#A8863F` | `#3670B3` | Hover states, secondary accent |
| `--accent-red` (NEW) | — | `#C5283D` | Buttons, CTAs, important highlights |

### Vote Colors

| Token | Old Value | New Value | Description |
|-------|-----------|-----------|-------------|
| `--vote-yea` | `#5B8A72` | `#4CAF6A` | Affirmative votes |
| `--vote-nay` | `#8A5B5B` | `#D64550` | Negative votes |
| `--vote-absent` | `#6B6B6B` | `#6B7B8B` | Absent/not voting |
| `--vote-present` | `#5B6F8A` | `#5B8FB8` | Present votes |

### Border Colors

| Token | Old Value | New Value |
|-------|-----------|-----------|
| `--border` | `#2A4060` | `#243B5E` |
| `--border-light` | `#3A5070` | `#2E4A72` |

## Changes Required

1. **CSS custom properties** in `styles.css` `:root` block
2. **CSS variable references**: Rename `--accent-gold` → `--accent` and `--accent-gold-dim` → `--accent-dim` throughout
3. **Add `--accent-red`** and apply to primary buttons
4. **`VOTE_COLORS` object** in `vote.js` — update hardcoded hex values
5. **SVG text color** in `vote.js` — update `#E8E0D4` → `#F0F4F8`
6. **Hardcoded colors** in CSS (deficit impact, vote labels) — verify compatibility

## Unchanged

- Fonts (Inter + Playfair Display)
- Layout, spacing, border-radius, shadows, transitions
- Component structure and HTML
- Party badge behavior
- Deficit impact color (`#E07A5F`) — remains compatible
