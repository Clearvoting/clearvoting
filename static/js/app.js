/* ============================================
   ClearVoting — Homepage (v4 broadsheet)
   One page, one action: pick a state, see its delegation,
   read the record — all wired to real synced data.
   ============================================ */

const PLACEHOLDER_SUMMARY = "Plain-language summary is not available";

// Party labels are hidden by default; the existing app uses this localStorage key.
let showParty = localStorage.getItem('cv-show-party') === 'true';

// The state currently revealed in the delegation section (so the party toggle
// knows which overview to re-fetch).
let currentStateCode = null;
let currentStateName = null;

// --- Initialize ---
document.addEventListener('DOMContentLoaded', () => {
    if (showParty) document.body.classList.add('show-party');
    setupStateCards();
    setupPartyToggle();
    setupNotify();
    loadRecord();
});

// --- DOM Helpers (build nodes via textContent / appendChild — never innerHTML) ---
function el(tag, attrs, ...children) {
    const element = document.createElement(tag);
    if (attrs) {
        for (const [key, value] of Object.entries(attrs)) {
            if (value == null) continue;
            if (key === 'className') element.className = value;
            else if (key.startsWith('data')) element.setAttribute(key.replace(/([A-Z])/g, '-$1').toLowerCase(), value);
            else element.setAttribute(key, value);
        }
    }
    children.forEach(child => {
        if (child == null || child === false) return;
        if (typeof child === 'string') element.appendChild(document.createTextNode(child));
        else element.appendChild(child);
    });
    return element;
}

function clearChildren(parent) {
    while (parent.firstChild) parent.removeChild(parent.firstChild);
}

/**
 * Member names are stored "Last, First Middle" (e.g. "Schumer, Charles E.").
 * The broadsheet displays them in natural order ("Charles E. Schumer").
 */
function displayName(member) {
    if (member.directOrderName) return member.directOrderName;
    const raw = (member.name || '').trim();
    if (!raw) return 'Unknown';
    const comma = raw.indexOf(',');
    if (comma === -1) return raw;
    const last = raw.slice(0, comma).trim();
    const first = raw.slice(comma + 1).trim();
    return first ? `${first} ${last}` : last;
}

/** Plain-language status seal derived from the bill's latest action. */
function billStatus(bill) {
    const text = ((bill.latestAction && bill.latestAction.text) || '').toLowerCase();
    if (text.includes('became public law') || text.includes('became law') || text.includes('signed by president')) {
        return { label: 'Became Law', moving: false };
    }
    return { label: 'Still in Congress', moving: true };
}

function billUrl(bill) {
    const type = (bill.type || '').toLowerCase();
    return `/bill?congress=${bill.congress}&type=${type}&number=${bill.number}`;
}

function memberUrl(member) {
    return `/member?id=${encodeURIComponent(member.bioguideId || '')}`;
}

function formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso + 'T00:00:00');
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
}

// ============================================
//  STATE CARDS → DELEGATION
// ============================================
function setupStateCards() {
    document.querySelectorAll('.cv-state-card').forEach(card => {
        card.addEventListener('click', () => selectState(card));
    });
}

async function selectState(card) {
    const stateName = card.dataset.state;
    const stateCode = card.dataset.code;
    currentStateCode = stateCode;
    currentStateName = stateName;

    document.querySelectorAll('.cv-state-card').forEach(c => {
        c.classList.remove('active');
        c.removeAttribute('aria-pressed');
    });
    card.classList.add('active');
    card.setAttribute('aria-pressed', 'true');

    const section = document.getElementById('cv-delegation');
    const body = document.getElementById('cv-delegation-body');
    const heading = document.getElementById('cv-delegation-heading');
    const sub = document.getElementById('cv-delegation-sub');
    const foot = document.getElementById('cv-roster-foot');

    heading.textContent = `${stateName}’s delegation in Washington`;
    sub.textContent = '';
    foot.hidden = true;
    section.classList.add('visible');
    clearChildren(body);
    body.appendChild(el('div', { className: 'cv-loading' }, 'Loading your delegation…'));

    // Reveal and bring into view as the mockup does.
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    section.focus({ preventScroll: true });

    try {
        const overview = await fetchOverview(stateCode);
        renderDelegation(overview, stateName, stateCode);
    } catch (err) {
        clearChildren(body);
        body.appendChild(el('div', { className: 'cv-loading' },
            'We could not load this delegation right now. Please try again in a moment.'));
    }
}

async function fetchOverview(stateCode) {
    const qs = showParty ? '?show_party=true' : '';
    const resp = await fetch(`/api/members/${stateCode}/overview${qs}`);
    if (!resp.ok) throw new Error('overview failed');
    return resp.json();
}

function renderDelegation(overview, stateName, stateCode) {
    const body = document.getElementById('cv-delegation-body');
    const sub = document.getElementById('cv-delegation-sub');
    const foot = document.getElementById('cv-roster-foot');
    const footAll = document.getElementById('cv-roster-foot-all');
    clearChildren(body);

    const members = overview.members || [];
    const senators = members.filter(m => m.chamber === 'Senate');
    const house = members.filter(m => m.chamber === 'House of Representatives');

    sub.textContent =
        `${senators.length} senator${senators.length === 1 ? '' : 's'} for the whole state · ` +
        `${house.length} House member${house.length === 1 ? '' : 's'}, one per district`;

    // --- The Senate ---
    if (senators.length) {
        body.appendChild(el('h3', { className: 'cv-roster-label cv-first' }, 'The Senate'));
        senators.forEach(m => body.appendChild(senatorRow(m, stateName)));
    }

    // --- The House ---
    if (house.length) {
        body.appendChild(el('h3', { className: 'cv-roster-label' }, 'The House — by district'));
        const roster = el('div', { className: 'cv-roster' });
        house
            .slice()
            .sort((a, b) => (a.district || 0) - (b.district || 0))
            .forEach(m => roster.appendChild(rosterRow(m)));
        body.appendChild(roster);
    }

    clearChildren(footAll);
    footAll.appendChild(el('a', { href: `/state?code=${stateCode}` },
        `Compare all ${members.length} representatives →`));
    foot.hidden = false;
}

function partyTag(member) {
    const party = member.partyName;
    if (!party) return null;
    return el('span', { className: 'cv-party-tag' }, ` · ${party}`);
}

/** Vote-split visual from support_rate; degrades gracefully with no votes. */
function splitVisual(member, opts) {
    const opts2 = opts || {};
    const total = (member.yea_count || 0) + (member.nay_count || 0);
    if (total <= 0) {
        return el('span', { className: 'cv-no-votes' }, 'No floor votes yet');
    }
    const yes = Math.max(0, Math.min(100, Math.round(member.support_rate || 0)));
    const no = 100 - yes;
    const labelsClass = opts2.micro ? 'cv-micro-labels' : 'cv-split-labels';
    const labels = el('div', { className: labelsClass },
        el('span', { className: 'cv-yes' }, opts2.micro ? `yes ${yes}%` : `Voted yes ${yes}%`),
        el('span', { className: 'cv-no' }, `no ${no}%`)
    );
    const bar = el('div', {
        className: 'cv-split-bar',
        role: 'img',
        'aria-label': `${yes} percent yes, ${no} percent no`,
    },
        el('span', { className: 'cv-split-yes', style: `width:${yes}%` }),
        el('span', { className: 'cv-split-no', style: `width:${no}%` })
    );
    return opts2.micro
        ? el('span', null, bar, labels)
        : el('div', null, labels, bar);
}

function memberPhoto(member, klass, name) {
    const imageUrl = member.depiction && member.depiction.imageUrl;
    if (!imageUrl) {
        return el('span', { className: klass, 'aria-hidden': 'true', style: 'background:var(--cv-rule-soft)' });
    }
    const img = el('img', { className: klass, src: imageUrl, alt: name ? `Portrait of ${name}` : '', loading: 'lazy' });
    img.addEventListener('error', () => { img.style.visibility = 'hidden'; });
    return img;
}

function senatorRow(member, stateName) {
    const name = displayName(member);
    const nameLink = el('a', { href: memberUrl(member) }, name);
    const tag = partyTag(member);
    if (tag) nameLink.appendChild(tag);

    const stats = el('div', { className: 'cv-member-stats' }, splitVisual(member));
    const total = (member.yea_count || 0) + (member.nay_count || 0);
    if (total > 0) {
        stats.appendChild(el('p', { className: 'cv-participation' },
            'Present for ', el('strong', null, `${Math.round(member.participation_rate || 0)}%`), ' of all floor votes'));
    }

    return el('article', { className: 'cv-senator-row' },
        memberPhoto(member, 'cv-senator-photo', name),
        el('div', null,
            el('h4', { className: 'cv-senator-name' }, nameLink),
            el('p', { className: 'cv-senator-seat' }, `U.S. Senator · ${stateName}`),
            member.narrative_snippet
                ? el('p', { className: 'cv-senator-narrative' }, member.narrative_snippet)
                : null
        ),
        stats
    );
}

function rosterRow(member) {
    const name = displayName(member);
    const district = member.district ? `District ${member.district}` : 'At large';
    const total = (member.yea_count || 0) + (member.nay_count || 0);
    const yes = Math.max(0, Math.min(100, Math.round(member.support_rate || 0)));
    const ariaVotes = total > 0 ? `, voted yes ${yes} percent, no ${100 - yes} percent` : ', no floor votes yet';

    const nameSpan = el('span', { className: 'cv-roster-name' }, name);
    const tag = partyTag(member);
    if (tag) nameSpan.appendChild(tag);

    return el('a', {
        className: 'cv-roster-row',
        href: memberUrl(member),
        'aria-label': `${name}, ${district}${ariaVotes}`,
    },
        memberPhoto(member, 'cv-roster-photo', name),
        el('span', null, nameSpan, el('br'), el('span', { className: 'cv-roster-district' }, district)),
        el('span', { className: 'cv-roster-split' }, splitVisual(member, { micro: true }))
    );
}

// ============================================
//  PARTY TOGGLE
// ============================================
function setupPartyToggle() {
    const toggle = document.getElementById('cv-party-toggle');
    toggle.setAttribute('aria-pressed', String(showParty));
    toggle.textContent = showParty ? 'Hide party labels' : 'Show party labels';

    toggle.addEventListener('click', async () => {
        showParty = !showParty;
        localStorage.setItem('cv-show-party', String(showParty));
        document.body.classList.toggle('show-party', showParty);
        toggle.setAttribute('aria-pressed', String(showParty));
        toggle.textContent = showParty ? 'Hide party labels' : 'Show party labels';

        // Re-fetch the current state's overview so partyName is populated
        // (it is stripped from the response unless show_party=true is sent).
        if (currentStateCode) {
            try {
                const overview = await fetchOverview(currentStateCode);
                renderDelegation(overview, currentStateName, currentStateCode);
            } catch { /* keep current render if the refresh fails */ }
        }
    });
}

// ============================================
//  NOTIFY FORM
// ============================================
function setupNotify() {
    const reveal = document.getElementById('cv-notify-reveal');
    const form = document.getElementById('cv-notify-form');
    const email = document.getElementById('cv-notify-email');
    const btn = document.getElementById('cv-notify-btn');
    const msg = document.getElementById('cv-notify-msg');

    reveal.addEventListener('click', () => {
        form.classList.add('open');
        email.focus();
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const value = email.value.trim();
        if (!value) { email.focus(); return; }

        btn.disabled = true;
        msg.hidden = true;
        msg.className = 'cv-notify-msg';

        try {
            const resp = await fetch('/api/notify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: value, state: '' }),
            });
            if (!resp.ok) throw new Error('notify failed');
            btn.textContent = '✓ On the list';
            email.disabled = true;
            msg.textContent = 'We will email you when your state arrives.';
            msg.classList.add('cv-ok');
            msg.hidden = false;
        } catch {
            btn.disabled = false;
            msg.textContent = 'Something went wrong. Please try again.';
            msg.classList.add('cv-err');
            msg.hidden = false;
        }
    });
}

// ============================================
//  THE RECORD + THE LATEST VOTE
// ============================================
async function loadRecord() {
    const grid = document.getElementById('cv-record-grid');
    try {
        const resp = await fetch('/api/bills?offset=0&limit=12');
        if (!resp.ok) throw new Error('bills failed');
        const data = await resp.json();
        const bills = data.bills || [];

        if (!bills.length) {
            clearChildren(grid);
            grid.appendChild(el('div', { className: 'cv-loading' }, 'No recent bills available yet.'));
            return;
        }

        renderTicker(bills[0]);
        await renderRecord(bills);
    } catch (err) {
        clearChildren(grid);
        grid.appendChild(el('div', { className: 'cv-loading' },
            'We could not load the latest bills right now.'));
    }
}

function renderTicker(bill) {
    const ticker = document.getElementById('cv-ticker');
    const body = document.getElementById('cv-ticker-body');
    const status = billStatus(bill);
    const plain = (bill.one_liner && bill.one_liner.trim()) || bill.title || '';
    if (!plain) return;

    clearChildren(body);
    const date = (bill.latestAction && formatDate(bill.latestAction.actionDate)) || '';
    const lead = date ? `${date} — ` : '';
    body.appendChild(document.createTextNode(`${lead}${status.label}: ${plain}. `));
    body.appendChild(el('a', { href: billUrl(bill) }, 'What it does, in plain English →'));
    ticker.hidden = false;
}

async function renderRecord(bills) {
    const grid = document.getElementById('cv-record-grid');
    clearChildren(grid);

    const featured = bills[0];
    const rest = bills.slice(1, 4);

    grid.appendChild(await featuredArticle(featured));

    const list = el('ul', { className: 'cv-record-list' });
    rest.forEach(bill => list.appendChild(recordListItem(bill)));
    grid.appendChild(list);
}

async function featuredArticle(bill) {
    const status = billStatus(bill);
    const seal = el('span', { className: status.moving ? 'cv-law-seal cv-moving' : 'cv-law-seal' }, status.label);
    const billNo = `${bill.type}. ${bill.number} · ${bill.congress}th Congress`;

    const article = el('article', { className: 'cv-record-lead' },
        el('div', { className: 'cv-story-kicker' }, seal, el('span', { className: 'cv-meta' }, billNo))
    );

    // Fetch the AI summary for the plain-language headline + provisions.
    let summary = null;
    try {
        const t = (bill.type || '').toLowerCase();
        const resp = await fetch(`/api/bills/${bill.congress}/${t}/${bill.number}/ai-summary`);
        if (resp.ok) summary = await resp.json();
    } catch { /* fall back to official title */ }

    const oneLiner = summary && summary.one_liner && summary.one_liner.trim();
    const headline = oneLiner || (bill.one_liner && bill.one_liner.trim()) || bill.title || 'Untitled measure';
    article.appendChild(el('h3', null, el('a', { href: billUrl(bill) }, headline)));

    // Provisions — skip the not-available placeholder gracefully.
    const provisions = (summary && summary.provisions) || [];
    const realProvisions = provisions.filter(p => p && !p.startsWith(PLACEHOLDER_SUMMARY));
    if (realProvisions.length) {
        const ul = el('ul', { className: 'cv-provision-list' });
        realProvisions.slice(0, 3).forEach(p => ul.appendChild(el('li', null, p)));
        article.appendChild(ul);
        if (realProvisions.length > 3) {
            article.appendChild(el('a', { className: 'cv-arrow-link', href: billUrl(bill) },
                `Read all ${realProvisions.length} provisions and who voted for it →`));
        } else {
            article.appendChild(el('a', { className: 'cv-arrow-link', href: billUrl(bill) },
                'See the full record and who voted for it →'));
        }
    } else {
        article.appendChild(el('a', { className: 'cv-arrow-link', href: billUrl(bill) },
            'See the full record and who voted for it →'));
    }

    // Official title footnote, only when we have a plain-language headline to contrast it.
    if (oneLiner && bill.title) {
        article.appendChild(el('p', { className: 'cv-official-line' }, `Officially: “${bill.title}”`));
    }

    return article;
}

function recordListItem(bill) {
    const status = billStatus(bill);
    const seal = el('span', { className: status.moving ? 'cv-law-seal cv-moving' : 'cv-law-seal' }, status.label);
    const plain = (bill.one_liner && bill.one_liner.trim()) || bill.title || 'Untitled measure';
    const date = (bill.latestAction && formatDate(bill.latestAction.actionDate)) || '';

    return el('li', { className: 'cv-record-item' },
        el('div', { className: 'cv-record-item-meta' },
            el('span', { className: 'cv-bill-no' }, `${bill.type}. ${bill.number}`),
            seal
        ),
        el('h4', null, el('a', { href: billUrl(bill) }, plain)),
        date ? el('p', { className: 'cv-meta' }, `Last action ${date}`) : null
    );
}
