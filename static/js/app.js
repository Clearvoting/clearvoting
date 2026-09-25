/* ============================================
   ClearVoting — home enhancer (plan T3.3, spec §4.1)
   The server renders the lead, the Latest Vote card and the Record.
   This file adds only what belongs to this reader (the Latest Vote
   per-state line, from cv-home) and the browse panel at the foot.
   site.js loads first and provides el, displayName, chip,
   formatBillCode and formatDate, and runs the shared page inits.
   ============================================ */
(function () {
    'use strict';

    const STATE_NAMES = { CA: 'California', FL: 'Florida', NY: 'New York', TX: 'Texas' };
    const ISSUE_CATEGORIES = [
        'Cost of Living', 'Healthcare', 'Jobs & Workers', 'Taxes',
        'Safety & Crime', 'Education', 'Money in Politics', 'Housing',
        'Immigration', 'Environment & Energy', 'Veterans & Military',
        'Social Security & Retirement',
    ];
    // Bare-string fallback only. A one-chamber adoption is final only for hres/sres,
    // which bill_status (T1.2) already decided in derived_status.variant.
    const FINAL_SEALS = /^(Became law|Passed both chambers)/;
    const BILL_LIMIT = 20;
    let billOffset = 0;
    let browseReady = false;

    document.addEventListener('DOMContentLoaded', () => {
        addLatestVoteStateLine();
        initBrowsePanel();
    });

    function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

    // Read-only here: cv-home is written only by site.js on the reader's own act (spec §5.4).
    function readHome() {
        try {
            const raw = localStorage.getItem('cv-home');
            const home = raw ? JSON.parse(raw) : null;
            if (home && STATE_NAMES[home.state]) return home;
        } catch (e) { /* storage blocked or malformed: behave as a first visit */ }
        return null;
    }

    function billHref(bill) {
        return `/bill?congress=${encodeURIComponent(bill.congress)}` +
            `&type=${encodeURIComponent(String(bill.type || '').toLowerCase())}` +
            `&number=${encodeURIComponent(bill.number)}`;
    }

    /* ---- Latest Vote: "New York: 15 yes · 11 no · 0 didn't vote · Your rep, … — Voted yes" ---- */
    async function addLatestVoteStateLine() {
        const card = document.querySelector('aside.vote-card[data-ssr="1"]');
        const home = readHome();
        if (!card || card.classList.contains('vote-card--empty') || !home) return;
        let vote;
        try {
            const res = await fetch('/api/votes/latest');
            if (!res.ok) return;
            vote = await res.json();
        } catch (e) {
            return; // the server-rendered card is complete without this line
        }
        const tally = (vote.state_tallies || {})[home.state];
        if (!Array.isArray(tally)) return;
        const line = el('p', { className: 'meta latest-state' },
            `${STATE_NAMES[home.state]}: ${tally[0]} yes · ${tally[1]} no · ${tally[2]} didn't vote`);
        const covered = Object.values(vote.covered || {}).filter(m => m && m.state === home.state);
        const senate = vote.chamber === 'Senate';
        const reps = senate ? covered : covered.filter(m => Number(m.district) === Number(home.district));
        reps.forEach(m => {
            const who = senate ? displayName(m.name) : `Your rep, ${displayName(m.name)}`;
            line.appendChild(document.createTextNode(` · ${who} — `));
            // §4.4 m2 reader relation: a senator missing from the roll call reads
            // "Not in the Senate for this vote", never the chip's 'House' default.
            line.appendChild(chip(m.position, { chamber: vote.chamber }));
        });
        card.appendChild(line);
    }

    /* ---- Browse panel (collapsed; spec §3.1 /bills row, F38) ---- */
    function initBrowsePanel() {
        const toggle = document.getElementById('browse-toggle');
        const panel = document.getElementById('browse-panel');
        if (!toggle || !panel) return;
        toggle.addEventListener('click', () => setPanelOpen(toggle, panel, panel.hidden, ''));
        const q = (new URLSearchParams(window.location.search).get('q') || '').trim();
        if (q) {
            setPanelOpen(toggle, panel, true, q);
            toggle.scrollIntoView({ block: 'start', behavior: 'auto' });
        }
    }

    function setPanelOpen(toggle, panel, open, query) {
        panel.hidden = !open;
        toggle.setAttribute('aria-expanded', String(open));
        if (!open) { reflectQuery(''); return; }
        if (!browseReady) { browseReady = true; buildBrowse(); }
        if (query) {
            document.getElementById('bill-search').value = query;
            searchBills(query);
        } else if (!panel.dataset.loaded) {
            panel.dataset.loaded = '1';
            loadBrowseBills(false);
        }
    }

    // history.replaceState use #1 of 3 (spec §3.3): the panel's query lives in ?q=.
    function reflectQuery(q) {
        const url = new URL(window.location.href);
        if (q) url.searchParams.set('q', q); else url.searchParams.delete('q');
        history.replaceState(null, '', url.pathname + url.search + url.hash);
    }

    function buildBrowse() {
        const categoryGrid = document.getElementById('category-grid');
        ISSUE_CATEGORIES.forEach(cat => {
            const chipBtn = el('button', { className: 'category-chip', type: 'button', 'aria-pressed': 'false' }, cat);
            chipBtn.addEventListener('click', () => {
                categoryGrid.querySelectorAll('.category-chip').forEach(c => c.setAttribute('aria-pressed', 'false'));
                chipBtn.setAttribute('aria-pressed', 'true');
                document.getElementById('bill-search').value = cat;
                searchBills(cat);
            });
            categoryGrid.appendChild(chipBtn);
        });
        document.getElementById('bill-search-form').addEventListener('submit', (e) => {
            e.preventDefault();
            const q = document.getElementById('bill-search').value.trim();
            if (q) { searchBills(q); } else { reflectQuery(''); loadBrowseBills(false); }
        });
        document.getElementById('load-more-btn').addEventListener('click', () => loadBrowseBills(true));
    }

    function statusSeal(bill) {
        const s = bill.derived_status;
        const text = typeof s === 'string' ? s : ((s && s.text) || 'No final vote yet');
        const variant = s && typeof s === 'object'
            ? (s.variant === 'final' ? 'final' : 'moving')   // trust bill_status (T1.2)
            : (FINAL_SEALS.test(text) ? 'final' : 'moving');
        return el('span', { className: `seal seal--${variant}` }, text);
    }

    function createBillRow(bill) {
        const code = formatBillCode(String(bill.type || '').toLowerCase(), bill.number);
        const date = bill.activity_date || (bill.latestAction && bill.latestAction.actionDate) || '';
        const meta = el('span', { className: 'row-meta' },
            el('span', { className: 'kicker' }, code),
            statusSeal(bill),
            date ? el('span', { className: 'meta' }, formatDate(date, true)) : null);
        const headline = bill.one_liner
            ? el('span', { className: 'row-headline' }, bill.one_liner)
            : el('span', { className: 'row-headline row-headline--official' }, bill.title || code);
        const pending = bill.one_liner ? null
            : el('span', { className: 'row-seal' }, el('span', { className: 'seal seal--pending' }, 'No plain-English summary yet'));
        return el('li', null, el('a', { className: 'bill-row', href: billHref(bill) }, meta, headline, pending));
    }

    async function loadBrowseBills(append) {
        const list = document.getElementById('bill-list');
        const results = document.getElementById('bill-results');
        const loadMore = document.getElementById('load-more-btn');
        const offset = append ? billOffset + BILL_LIMIT : 0;
        if (!append) { clear(list); results.textContent = 'Loading bills…'; }
        loadMore.disabled = true;
        try {
            const res = await fetch(`/api/bills?offset=${offset}&limit=${BILL_LIMIT}`);
            if (!res.ok) throw new Error(String(res.status));
            const bills = (await res.json()).bills || [];
            billOffset = offset; // advance only after a page actually arrived (F38)
            if (!append) results.textContent = '';
            bills.forEach(b => list.appendChild(createBillRow(b)));
            loadMore.hidden = bills.length < BILL_LIMIT;
        } catch (e) {
            results.textContent = "We couldn't load bills right now.";
        } finally {
            loadMore.disabled = false;
        }
    }

    async function searchBills(query) {
        const list = document.getElementById('bill-list');
        const results = document.getElementById('bill-results');
        document.getElementById('load-more-btn').hidden = true;
        reflectQuery(query);
        clear(list);
        results.textContent = 'Searching…';
        try {
            const res = await fetch(`/api/search/bills?q=${encodeURIComponent(query)}&limit=50`);
            if (!res.ok) throw new Error(String(res.status));
            const bills = (await res.json()).bills || [];
            results.textContent = bills.length
                ? `${bills.length} bill${bills.length !== 1 ? 's' : ''} found for “${query}”`
                : `No bills found for “${query}”. Try a broader term or pick a topic above.`;
            bills.forEach(b => list.appendChild(createBillRow(b)));
        } catch (e) {
            results.textContent = "We couldn't search the record right now. Please try again in a moment.";
        }
    }
})();
