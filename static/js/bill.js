/* ============================================
   ClearVoting — Bill page enhancer (spec §4.4)
   The server renders the page. This file adds only what needs a click or
   belongs to this reader: the official summary fill, the lazy roll-call
   lists, the party reveal and the "your representatives" slot.
   ============================================ */

const SAFE_TAGS = new Set(['P', 'EM', 'STRONG', 'B', 'I', 'BR', 'UL', 'OL', 'LI', 'A']);
function sanitizeHtml(html) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    doc.body.querySelectorAll('*').forEach(node => {
        if (!SAFE_TAGS.has(node.tagName)) {
            node.replaceWith(...node.childNodes);
        }
        for (const attr of [...node.attributes]) {
            if (attr.name !== 'href') node.removeAttribute(attr.name);
        }
    });
    return doc.body.innerHTML;
}

const BILL_RC_CACHE = new Map();
let billPartyShown = false;

function billFetchRollCall(url, withParty) {
    const full = withParty ? `${url}?show_party=true` : url;
    if (!BILL_RC_CACHE.has(full)) {
        const request = fetch(full)
            .then(res => {
                if (!res.ok) throw new Error('roll call');
                return res.json();
            })
            .catch(err => {
                BILL_RC_CACHE.delete(full);
                throw err;
            });
        BILL_RC_CACHE.set(full, request);
    }
    return BILL_RC_CACHE.get(full);
}

function billOpenHomeState(scope) {
    const home = readHome();
    if (!home) return;
    scope.querySelectorAll(`details.state-group[data-state="${home.state}"]`).forEach(group => { group.open = true; });
}

// The one sanctioned HTML sink. The four lines inside the if are byte-identical to baseline
// bill.js lines 165–168 (June plan constraint 4); only the source changed: T1.8's
// official_summary (Public Law first, else newest) instead of summaries[0] (the oldest).
function billFillOfficialSummary(summaryDiv, latestSummary) {
    if (latestSummary) {
        summaryDiv.textContent = '';
        // Content is sanitized — only safe tags (P, EM, STRONG, B, I, BR, UL, OL, LI, A) remain
        const sanitized = sanitizeHtml(latestSummary);
        summaryDiv.insertAdjacentHTML('afterbegin', sanitized);
    }
}

function billInitOfficialSummary(billId) {
    const slot = document.querySelector('details[data-summary-slot]');
    const summaryDiv = document.getElementById('official-summary-body');
    if (!slot || !summaryDiv) return;
    const [congress, type, number] = billId.split('-');
    let loaded = false;
    slot.addEventListener('toggle', async () => {
        if (!slot.open || loaded) return;
        loaded = true;
        summaryDiv.textContent = 'Loading summary…';
        try {
            const res = await fetch(`/api/bills/${encodeURIComponent(congress)}/${encodeURIComponent(type)}/${encodeURIComponent(number)}`);
            if (!res.ok) throw new Error('bill');
            const data = await res.json();
            billFillOfficialSummary(summaryDiv, data.official_summary || '');
        } catch (e) {
            loaded = false;
            summaryDiv.textContent = t('pageError');
        }
    });
}

function billInitAllVotes() {
    document.querySelectorAll('details.rc-all').forEach(details => {
        const list = details.querySelector('.rc-all-list');
        const query = details.querySelector('.rc-all-q');
        const show = details.querySelector('.rc-all-show');
        const block = details.closest('[data-chamber]');
        if (!list || !query || !show || !block) return;
        const apply = () => filterRcRows(list, query.value, show.value);
        let loaded = false;
        details.addEventListener('toggle', async () => {
            if (!details.open || loaded) return;
            loaded = true;
            try {
                const data = await billFetchRollCall(details.dataset.url, billPartyShown);
                const members = data.members || [];
                clear(list);
                // Every state in one table: sorted by name and each row shows its state, since
                // "District 4" alone is ambiguous across states (current = false).
                list.appendChild(buildRcTable(`Every state — ${details.dataset.caption}`, members, block.dataset.chamber, false));
                if (billPartyShown) fillPartySpans(list, members, block.dataset.chamber);
                apply();
            } catch (e) {
                loaded = false;
                list.textContent = t('pageError');
            }
        });
        query.addEventListener('input', apply);
        show.addEventListener('change', apply);
    });
}

function billInitExtraRollCalls() {
    document.querySelectorAll('details.rc-more').forEach(details => {
        const box = details.querySelector('.rc-groups');
        if (!box) return;
        let loaded = false;
        details.addEventListener('toggle', async () => {
            if (!details.open || loaded) return;
            loaded = true;
            const chamber = details.dataset.chamber;
            const current = details.dataset.current === '1';
            try {
                const data = await billFetchRollCall(details.dataset.url, billPartyShown);
                const members = data.members || [];
                clear(box);
                Object.keys(COVERED_STATES).forEach(code => {
                    const rows = members.filter(m => m.state === code);
                    if (!rows.length) return;
                    // The group summary is the block's own index tally line, so it reads exactly
                    // like the server's groups: "New York: 13 yes · 11 no · 2 didn't vote".
                    const tally = details.querySelector(`.state-tallies li[data-state="${code}"]`);
                    box.appendChild(el('details', { className: 'state-group', 'data-state': code },
                        el('summary', null, tally ? tally.textContent : COVERED_STATES[code]),
                        buildRcTable(`${COVERED_STATES[code]} — ${details.dataset.caption}`, rows, chamber, current)));
                });
                if (billPartyShown) fillPartySpans(box, members, chamber);
                billOpenHomeState(box);
            } catch (e) {
                loaded = false;
                box.textContent = t('pageError');
            }
        });
    });
}

// Fill callback for site.js initPartyToggle: one page-level toggle covers every list (spec §4.4 m3).
async function billSetParty(shown) {
    billPartyShown = shown;
    const containers = document.querySelectorAll('section.rc-block[data-url], details.rc-more[data-url]');
    for (const box of containers) {
        if (!shown) {
            clearPartySpans(box);
            continue;
        }
        if (!box.querySelector('tbody tr')) continue;
        try {
            const data = await billFetchRollCall(box.dataset.url, true);
            fillPartySpans(box, data.members || [], box.dataset.chamber);
        } catch (e) {
            /* names and positions stay; the party spans stay empty for this list */
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const root = document.querySelector('.bill-grid[data-bill]');
    if (!root) return;
    billInitOfficialSummary(root.dataset.bill);
    billInitAllVotes();
    billInitExtraRollCalls();
    billOpenHomeState(document);
    initPartyToggle(billSetParty);
    initShare();
    initZipInPlace();
    fillRepsSlot();
});
