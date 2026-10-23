/* ============================================
   ClearVoting — Delegation page enhancer (plan T4.2; spec §4.2, §5.4)
   The server renders the whole page (app/render.py render_state_page).
   This adds only what belongs to this reader: the party reveal, the
   "Remember District N as mine" button and Share. Every helper is a
   site.js global; the feedback buttons belong to feedback.js.
   ============================================ */
(function () {
    'use strict';

    // "Remember District 4 as mine": shown only when cv-home is not already this district.
    // A tap replaces it with the site-wide "Remembered: New York, District 4 · Change ·
    // Forget" line (§5.4), which takes focus so it is read out. Forget brings the button
    // back and focuses it. If storage refuses the write, nothing changes and nothing is said.
    function initRememberButton() {
        const button = document.getElementById('remember-district');
        if (!button) return;
        const state = button.getAttribute('data-state');
        const district = Number(button.getAttribute('data-district'));
        const home = readHome();
        if (home && home.state === state && home.district === district) return;
        const wrapper = button.parentNode;
        button.hidden = false;
        button.addEventListener('click', () => {
            const saved = rememberDistrict(state, district);
            if (!saved) return;
            rewriteMastheadLink();
            const line = rememberedLine(saved, (shown) => {
                shown.remove();
                button.hidden = false;
                return wrapper;
            });
            line.setAttribute('tabindex', '-1');
            button.hidden = true;
            wrapper.appendChild(line);
            line.focus();
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        initHome();          // writes cv-home from #mine and removes the fragment, before the Remember check
        initPhotos();
        initPartyToggle();   // fetches .party-toggle[data-party-url] once and fills the .party spans
        initShare();
        initRememberButton();
    });
})();
