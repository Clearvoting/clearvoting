/* ============================================
   ClearVoting — Homepage ("Civic Broadsheet")
   ============================================ */

const STATE_NAMES = { CA: 'California', FL: 'Florida', NY: 'New York', TX: 'Texas' };

const ISSUE_CATEGORIES = [
    'Cost of Living', 'Healthcare', 'Jobs & Workers', 'Taxes',
    'Safety & Crime', 'Education', 'Money in Politics', 'Housing',
    'Immigration', 'Environment & Energy', 'Veterans & Military',
    'Social Security & Retirement',
];

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];

let currentState = null;
let showParty = localStorage.getItem('cv-show-party') === 'true';
let browseReady = false;
let billOffset = 0;
const BILL_LIMIT = 20;

document.addEventListener('DOMContentLoaded', () => {
    loadStateCounts();
    loadLatestVote();
    loadRecord();
    setupStateCards();
    setupPartyToggle();
    setupNotify();
    setupBrowse();
});

/* ---- DOM helpers ---- */
function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
        for (const [key, value] of Object.entries(attrs)) {
            if (value === null || value === undefined) continue;
            if (key === 'className') node.className = value;
            else node.setAttribute(key, value);
        }
    }
    for (const child of children) {
        if (child === null || child === undefined || child === false) continue;
        node.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
    }
    return node;
}

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

/* ---- Formatting ---- */
// "Schumer, Charles E." -> "Charles E. Schumer"
function humanizeName(name) {
    if (!name || !name.includes(',')) return name || '';
    const idx = name.indexOf(',');
    const last = name.slice(0, idx).trim();
    const rest = name.slice(idx + 1).trim();
    return rest ? `${rest} ${last}` : last;
}

function formatISODate(iso) {
    if (!iso) return '';
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
    if (!m) return iso;
    return `${MONTHS[parseInt(m[2], 10) - 1]} ${parseInt(m[3], 10)}, ${m[1]}`;
}

function ordinal(n) {
    const s = ['th', 'st', 'nd', 'rd'];
    const v = n % 100;
    return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

function billHref(bill) {
    return `/bill?congress=${bill.congress}&type=${(bill.type || '').toLowerCase()}&number=${bill.number}`;
}

function billStatus(bill) {
    const text = (bill.latestAction && bill.latestAction.text) || '';
    const date = formatISODate(bill.latestAction && bill.latestAction.actionDate);
    if (/became public law/i.test(text)) return { label: 'Became Law', moving: false, date };
    return { label: 'Still in Congress', moving: true, date };
}

function splitPct(stats) {
    const yea = (stats && stats.yea_count) || 0;
    const nay = (stats && stats.nay_count) || 0;
    const total = yea + nay;
    if (!total) return null;
    const yes = Math.round((yea / total) * 100);
    return { yes, no: 100 - yes };
}

function verbFromResult(result) {
    const r = (result || '').toLowerCase();
    if (r.includes('passed')) return 'passed';
    if (r.includes('agreed to')) return 'agreed to';
    if (r.includes('defeated') || r.includes('rejected') || r.includes('failed')) return 'rejected';
    if (r.includes('confirmed')) return 'confirmed';
    return 'voted on';
}

/* ---- State card counts ---- */
async function loadStateCounts() {
    try {
        const res = await fetch('/api/members/counts');
        if (!res.ok) return;
        const { counts } = await res.json();
        document.querySelectorAll('.state-count').forEach(elm => {
            const code = elm.dataset.countFor;
            if (counts[code]) elm.textContent = `${counts[code]} members`;
        });
    } catch { /* counts are a nicety; cards work without them */ }
}

/* ---- Latest vote ---- */
async function loadLatestVote() {
    const card = document.getElementById('latest-vote');
    try {
        const res = await fetch('/api/votes/latest');
        if (!res.ok) return;
        const v = await res.json();
        const counts = v.counts || {};
        const yeas = counts.yeas || 0;
        const nays = counts.nays || 0;
        const title = v.bill.title || v.document;

        document.getElementById('latest-vote-dateline').textContent =
            `${v.date} · U.S. ${v.chamber} · ${v.document}`;

        const headline = document.getElementById('latest-vote-headline');
        clear(headline);
        headline.appendChild(el('a', { href: billHref(v.bill) },
            `The ${v.chamber} ${verbFromResult(v.result)} the ${title}, ${yeas}–${nays}`));

        const total = yeas + nays;
        const yesPct = total ? Math.round((yeas / total) * 100) : 50;
        const tally = document.getElementById('latest-vote-tally');
        clear(tally);
        tally.setAttribute('role', 'img');
        tally.setAttribute('aria-label', `${yeas} voted yes, ${nays} voted no`);
        tally.appendChild(el('div', { className: 'tally-bar' },
            el('span', { className: 'tally-yes', style: `width:${yesPct}%` }),
            el('span', { className: 'tally-no', style: `width:${100 - yesPct}%` })
        ));
        tally.appendChild(el('div', { className: 'tally-labels' },
            el('span', { className: 'yes' }, `${yeas} voted yes`),
            el('span', { className: 'no' }, `${nays} voted no`)
        ));

        document.getElementById('latest-vote-link').href = billHref(v.bill);
        card.hidden = false;
    } catch { /* hero still reads fine without the card */ }
}

/* ---- The Record ---- */
async function loadRecord() {
    const grid = document.getElementById('record-grid');
    try {
        const res = await fetch('/api/bills?summarized_only=true&limit=6');
        if (!res.ok) throw new Error('failed');
        const bills = (await res.json()).bills || [];
        clear(grid);
        if (!bills.length) { grid.appendChild(el('p', { className: 'empty-note' }, 'No bills available yet.')); return; }
        grid.appendChild(renderRecordLead(bills[0]));
        grid.appendChild(renderRecordList(bills.slice(1)));
    } catch {
        clear(grid);
        grid.appendChild(el('p', { className: 'empty-note' }, 'Unable to load recent bills right now.'));
    }
}

function renderRecordLead(bill) {
    const status = billStatus(bill);
    const provisions = (bill.provisions || []).slice(0, 4);
    const allCount = (bill.provisions || []).length;

    const seal = el('span', { className: status.moving ? 'law-seal moving' : 'law-seal' },
        status.moving ? status.label : `${status.label} · ${status.date}`);
    const kicker = el('div', { className: 'story-kicker' }, seal,
        el('span', { className: 'meta' }, `${(bill.type || '').toUpperCase()}. ${bill.number} · ${ordinal(bill.congress)} Congress`));

    const provisionList = el('ul', { className: 'record-provisions' },
        ...provisions.map(p => el('li', null, p)));

    const children = [
        kicker,
        el('h3', null, el('a', { href: billHref(bill) }, bill.one_liner || bill.title)),
        provisionList,
        el('a', { className: 'arrow-link', href: billHref(bill) },
            allCount > provisions.length
                ? `Read all ${allCount} provisions and who voted for it →`
                : 'See who voted for it →'),
    ];
    if (bill.title) {
        children.push(el('p', { className: 'official-line' }, `Officially: “${bill.title}”`));
    }
    return el('article', { className: 'record-lead' }, ...children);
}

function renderRecordList(bills) {
    const list = el('ul', { className: 'record-list' });
    bills.forEach(bill => {
        const status = billStatus(bill);
        const metaBits = [status.date, bill.title ? `Officially the “${bill.title}”` : null]
            .filter(Boolean).join(' · ');
        list.appendChild(el('li', { className: 'record-item' },
            el('div', { className: 'record-item-meta' },
                el('span', { className: 'bill-no' }, `${(bill.type || '').toUpperCase()}. ${bill.number}`),
                el('span', { className: status.moving ? 'law-seal moving' : 'law-seal' }, status.label)
            ),
            el('h4', null, el('a', { href: billHref(bill) }, bill.one_liner || bill.title)),
            el('p', { className: 'meta' }, metaBits)
        ));
    });
    return list;
}

/* ---- State selection → delegation ---- */
function setupStateCards() {
    document.querySelectorAll('.state-card').forEach(card => {
        card.addEventListener('click', () => selectState(card.dataset.state));
    });
}

function selectState(code) {
    currentState = code;
    document.querySelectorAll('.state-card').forEach(c => {
        const active = c.dataset.state === code;
        c.classList.toggle('active', active);
        c.setAttribute('aria-pressed', String(active));
    });
    const section = document.getElementById('delegation');
    section.hidden = false;
    loadDelegation(code);
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function loadDelegation(code) {
    const body = document.getElementById('delegation-body');
    const heading = document.getElementById('delegation-heading');
    const sub = document.getElementById('delegation-sub');
    heading.textContent = `${STATE_NAMES[code] || code}’s delegation`;
    sub.textContent = '';
    clear(body);
    body.appendChild(el('div', { className: 'loading' }, el('span', { className: 'spinner' }), ' Loading representatives…'));

    try {
        let url = `/api/members/${code}?include_stats=true`;
        if (showParty) url += '&show_party=true';
        const res = await fetch(url);
        if (!res.ok) throw new Error('failed');
        const members = (await res.json()).members || [];
        renderDelegation(body, heading, sub, members, code);
        document.getElementById('delegation-foot').hidden = false;
    } catch {
        clear(body);
        body.appendChild(el('p', { className: 'empty-note' }, 'Unable to load representatives right now. Please try again.'));
    }
}

function isSenate(member) { return (member.chamber || '').includes('Senate'); }

function renderDelegation(body, heading, sub, members, code) {
    clear(body);
    const senators = members.filter(isSenate);
    const house = members.filter(m => !isSenate(m))
        .sort((a, b) => (a.district || 0) - (b.district || 0));

    heading.textContent = `${STATE_NAMES[code] || code}’s ${members.length} voices in Washington`;
    sub.textContent =
        `${senators.length} senator${senators.length !== 1 ? 's' : ''} for the whole state · ` +
        `${house.length} House member${house.length !== 1 ? 's' : ''}, one per district`;

    if (senators.length) {
        body.appendChild(el('h3', { className: 'roster-label' }, 'The Senate'));
        senators.forEach(m => body.appendChild(renderSenatorRow(m)));
    }
    if (house.length) {
        body.appendChild(el('h3', { className: 'roster-label' }, 'The House — by district'));
        const roster = el('div', { className: 'roster' });
        house.forEach(m => roster.appendChild(renderRosterRow(m)));
        body.appendChild(roster);
    }
}

function memberPhoto(member, className) {
    const url = member.depiction && member.depiction.imageUrl;
    if (url) return el('img', { className, src: url, alt: '', loading: 'lazy' });
    return el('div', { className: className + ' photo-fallback', 'aria-hidden': 'true' });
}

function partyTag(member) {
    return member.partyName ? el('span', { className: 'party-tag' }, `· ${member.partyName}`) : null;
}

function splitBar(stats) {
    const s = splitPct(stats);
    const stack = el('div', { className: 'member-stats' });
    if (!s) {
        stack.appendChild(el('p', { className: 'meta' }, 'Voting record not yet available'));
        return stack;
    }
    stack.appendChild(el('div', { className: 'split-labels' },
        el('span', { className: 'yes' }, `Voted yes ${s.yes}%`),
        el('span', { className: 'no' }, `no ${s.no}%`)
    ));
    stack.appendChild(el('div', { className: 'split-bar', role: 'img', 'aria-label': `${s.yes} percent yes, ${s.no} percent no` },
        el('span', { className: 'split-yes', style: `width:${s.yes}%` }),
        el('span', { className: 'split-no', style: `width:${s.no}%` })
    ));
    const rate = stats.participation_rate;
    if (rate || rate === 0) {
        stack.appendChild(el('p', { className: 'participation' },
            'Present for ', el('strong', null, `${rate}%`), ' of all floor votes'));
    }
    return stack;
}

function renderSenatorRow(m) {
    const info = el('div', {},
        el('h4', { className: 'senator-name' }, humanizeName(m.name), partyTag(m)),
        el('p', { className: 'senator-seat' }, `U.S. Senate · ${m.state || STATE_NAMES[currentState] || ''}`),
        m.narrative_snippet ? el('p', { className: 'senator-narrative' }, m.narrative_snippet) : null
    );
    return el('a', { className: 'senator-row', href: `/member?id=${m.bioguideId}` },
        memberPhoto(m, 'senator-photo'), info, splitBar(m.stats));
}

function renderRosterRow(m) {
    const s = splitPct(m.stats);
    const splitWrap = el('span', { className: 'roster-split' });
    if (s) {
        splitWrap.appendChild(el('span', { className: 'split-bar' },
            el('span', { className: 'split-yes', style: `width:${s.yes}%` }),
            el('span', { className: 'split-no', style: `width:${s.no}%` })
        ));
        splitWrap.appendChild(el('span', { className: 'micro-labels' },
            el('span', { className: 'yes' }, `yes ${s.yes}%`),
            el('span', { className: 'no' }, `no ${s.no}%`)
        ));
    }
    const labelBits = s ? `Voted yes ${s.yes}%, no ${s.no}%` : 'Voting record not yet available';
    return el('a', {
        className: 'roster-row',
        href: `/member?id=${m.bioguideId}`,
        'aria-label': `${humanizeName(m.name)}, ${m.district ? 'District ' + m.district : 'At large'}. ${labelBits}`,
    },
        memberPhoto(m, 'roster-photo'),
        el('span', { className: 'roster-id' },
            el('span', { className: 'roster-name' }, humanizeName(m.name), partyTag(m)),
            el('br'),
            el('span', { className: 'roster-district' }, m.district ? `District ${m.district}` : 'At large')
        ),
        splitWrap
    );
}

/* ---- Party toggle ---- */
function setupPartyToggle() {
    const toggle = document.getElementById('party-toggle');
    toggle.setAttribute('aria-pressed', String(showParty));
    toggle.textContent = showParty ? 'Hide party labels' : 'Show party labels';
    toggle.addEventListener('click', () => {
        showParty = !showParty;
        localStorage.setItem('cv-show-party', String(showParty));
        toggle.setAttribute('aria-pressed', String(showParty));
        toggle.textContent = showParty ? 'Hide party labels' : 'Show party labels';
        if (currentState) loadDelegation(currentState);
    });
}

/* ---- Notify signup ---- */
function setupNotify() {
    const form = document.getElementById('notify-form');
    const reveal = document.getElementById('notify-reveal');
    const status = document.getElementById('notify-status');

    reveal.addEventListener('click', () => {
        form.classList.add('open');
        document.getElementById('notify-email').focus();
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('notify-email').value.trim();
        const btn = document.getElementById('notify-btn');
        btn.disabled = true;
        try {
            const res = await fetch('/api/notify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, state: currentState || '' }),
            });
            if (!res.ok) throw new Error('failed');
            form.classList.remove('open');
            status.hidden = false;
            status.textContent = '✓ You’re on the list — we’ll email you when your state is added.';
        } catch {
            btn.disabled = false;
            status.hidden = false;
            status.style.color = 'var(--no)';
            status.textContent = 'Something went wrong. Please check your email and try again.';
        }
    });
}

/* ---- Browse panel (progressive disclosure) ---- */
function setupBrowse() {
    const toggle = document.getElementById('browse-toggle');
    const panel = document.getElementById('browse-panel');
    toggle.addEventListener('click', () => {
        const open = panel.hidden;
        panel.hidden = !open;
        toggle.setAttribute('aria-expanded', String(open));
        toggle.textContent = open ? 'Hide bill browser ↑' : 'Browse all bills by topic →';
        if (open && !browseReady) {
            browseReady = true;
            initBrowse();
            panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    });
}

function initBrowse() {
    const categoryGrid = document.getElementById('category-grid');
    ISSUE_CATEGORIES.forEach(cat => {
        const chip = el('button', { className: 'category-chip', type: 'button', 'aria-label': `Browse ${cat} bills` }, cat);
        chip.addEventListener('click', () => {
            document.querySelectorAll('.category-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            document.getElementById('bill-search').value = cat;
            searchBills(cat);
        });
        categoryGrid.appendChild(chip);
    });

    document.getElementById('bill-search-form').addEventListener('submit', (e) => {
        e.preventDefault();
        const q = document.getElementById('bill-search').value.trim();
        if (q) searchBills(q);
    });

    document.getElementById('load-more-btn').addEventListener('click', () => {
        billOffset += BILL_LIMIT;
        loadBrowseBills(true);
    });

    loadBrowseBills(false);
}

function createBillRow(bill) {
    const status = billStatus(bill);
    const headline = bill.one_liner || bill.title || 'Untitled bill';
    const metaBits = [status.date, (bill.one_liner && bill.title) ? `Officially the “${bill.title}”` : null]
        .filter(Boolean).join(' · ');
    const row = el('div', { className: 'record-item', tabindex: '0', role: 'link' },
        el('div', { className: 'record-item-meta' },
            el('span', { className: 'bill-no' }, `${(bill.type || '').toUpperCase()}. ${bill.number}`),
            el('span', { className: status.moving ? 'law-seal moving' : 'law-seal' }, status.label)
        ),
        el('h4', null, headline),
        metaBits ? el('p', { className: 'meta' }, metaBits) : null
    );
    const go = () => { window.location.href = billHref(bill); };
    row.addEventListener('click', go);
    row.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    return row;
}

async function loadBrowseBills(append) {
    const list = document.getElementById('bill-list');
    const loadMore = document.getElementById('load-more-btn');
    if (!append) {
        billOffset = 0;
        clear(list);
        list.appendChild(el('div', { className: 'loading' }, el('span', { className: 'spinner' }), ' Loading bills…'));
    }
    try {
        const res = await fetch(`/api/bills?offset=${billOffset}&limit=${BILL_LIMIT}`);
        if (!res.ok) throw new Error('failed');
        const bills = (await res.json()).bills || [];
        if (!append) clear(list);
        bills.forEach(b => list.appendChild(createBillRow(b)));
        loadMore.hidden = bills.length < BILL_LIMIT;
    } catch {
        if (!append) { clear(list); list.appendChild(el('p', { className: 'empty-note' }, 'Unable to load bills right now.')); }
    }
}

async function searchBills(query) {
    const list = document.getElementById('bill-list');
    const loadMore = document.getElementById('load-more-btn');
    loadMore.hidden = true;
    clear(list);
    list.appendChild(el('div', { className: 'loading' }, el('span', { className: 'spinner' }), ' Searching…'));
    try {
        const res = await fetch(`/api/search/bills?q=${encodeURIComponent(query)}&limit=50`);
        if (!res.ok) throw new Error('failed');
        const bills = (await res.json()).bills || [];
        clear(list);
        list.appendChild(el('p', { className: 'results-count' },
            `${bills.length} bill${bills.length !== 1 ? 's' : ''} found for “${query}”`));
        if (!bills.length) {
            list.appendChild(el('p', { className: 'empty-note' }, 'Try a broader term or pick a topic above.'));
            return;
        }
        bills.forEach(b => list.appendChild(createBillRow(b)));
    } catch {
        clear(list);
        list.appendChild(el('p', { className: 'empty-note' }, 'Search failed. Please try again.'));
    }
}
