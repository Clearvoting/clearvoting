# T8.4 review — og:image Phase A (commit 2eab658)

## Summary
The commit matches the plan task line for line: `scripts/build_og_cards.py` is the plan's script unchanged, the four committed PNGs are 1200x630 and between 33 KB and 46 KB, and `_OG_CARD_ALT` / `_og_image` sit directly below `_zip_finder_meta` with the exact contract that T10.1 will extend (a site-relative `path`, the 1200/630 dimensions, and `key` accepted but ignored). The `image` key is added to `_member_meta` (bioguide id), `_bill_meta`, `_state_meta` (code), `_zip_finder_meta`, and to the index/about/methodology/privacy meta dicts. The 404 handler gets none. The test changes are exactly what the plan specified.

Spec check (§9.3, C-9): default.png covers home, about and the trust pages; the descriptors "Voting record", "How Congress voted" and "Your representatives" are verbatim; Pillow is not in `requirements.txt`; nothing renders on the request path.

## Verification (run by reviewer)
- Full suite: 1412 passed, 2 skipped.
- scope_check.py: exit 0 on all eight shells.
- `grep -ci pillow requirements.txt` printed 0.
- Local server :8011: /, /about, /methodology and /privacy point at default.png. /member?id=S000148 points at member.png, /bill?congress=119&type=hr&number=4795 at bill.png, and both /state?code=TX and the bare /state finder at state.png. Every URL is an absolute https://clearvoting.org/static/og/*.png with width, height, alt and `summary_large_image`. /no-such-page has 0 og:image. /static/og/member.png is served as image/png with `public, max-age=86400`. The page still has one `<title>`.
- shoot.mjs on home and member: ok, scrollWidth 1280 on desktop and 375 on mobile, with no JSERROR or CSP lines. The server is stopped and port 8011 is free.
- Viewed bill.png and state.png (the implementer checked member and default): paper background, navy double rules, the wordmark, the tagline and the descriptor. Nothing is clipped or overlapping.
- Safety: the alt text and path go through `escape()` in `_inject_meta`. No innerHTML, no inline script, no CSP change, no URL-shape change.

## Verdict
pass

## Issues
None blocking.
- (Note, no action) I could not rebuild the PNGs to confirm the script reproduces them byte for byte, because the sandbox denied the command. The committed images match what the script is written to draw.
