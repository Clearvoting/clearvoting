/* ============================================
   ClearVoting — Landing Page
   ============================================ */

const STATES = [
    { code: 'AL', name: 'Alabama' }, { code: 'AK', name: 'Alaska' },
    { code: 'AZ', name: 'Arizona' }, { code: 'AR', name: 'Arkansas' },
    { code: 'CA', name: 'California' }, { code: 'CO', name: 'Colorado' },
    { code: 'CT', name: 'Connecticut' }, { code: 'DE', name: 'Delaware' },
    { code: 'FL', name: 'Florida' }, { code: 'GA', name: 'Georgia' },
    { code: 'HI', name: 'Hawaii' }, { code: 'ID', name: 'Idaho' },
    { code: 'IL', name: 'Illinois' }, { code: 'IN', name: 'Indiana' },
    { code: 'IA', name: 'Iowa' }, { code: 'KS', name: 'Kansas' },
    { code: 'KY', name: 'Kentucky' }, { code: 'LA', name: 'Louisiana' },
    { code: 'ME', name: 'Maine' }, { code: 'MD', name: 'Maryland' },
    { code: 'MA', name: 'Massachusetts' }, { code: 'MI', name: 'Michigan' },
    { code: 'MN', name: 'Minnesota' }, { code: 'MS', name: 'Mississippi' },
    { code: 'MO', name: 'Missouri' }, { code: 'MT', name: 'Montana' },
    { code: 'NE', name: 'Nebraska' }, { code: 'NV', name: 'Nevada' },
    { code: 'NH', name: 'New Hampshire' }, { code: 'NJ', name: 'New Jersey' },
    { code: 'NM', name: 'New Mexico' }, { code: 'NY', name: 'New York' },
    { code: 'NC', name: 'North Carolina' }, { code: 'ND', name: 'North Dakota' },
    { code: 'OH', name: 'Ohio' }, { code: 'OK', name: 'Oklahoma' },
    { code: 'OR', name: 'Oregon' }, { code: 'PA', name: 'Pennsylvania' },
    { code: 'RI', name: 'Rhode Island' }, { code: 'SC', name: 'South Carolina' },
    { code: 'SD', name: 'South Dakota' }, { code: 'TN', name: 'Tennessee' },
    { code: 'TX', name: 'Texas' }, { code: 'UT', name: 'Utah' },
    { code: 'VT', name: 'Vermont' }, { code: 'VA', name: 'Virginia' },
    { code: 'WA', name: 'Washington' }, { code: 'WV', name: 'West Virginia' },
    { code: 'WI', name: 'Wisconsin' }, { code: 'WY', name: 'Wyoming' },
    { code: 'DC', name: 'District of Columbia' },
    { code: 'AS', name: 'American Samoa' }, { code: 'GU', name: 'Guam' },
    { code: 'MP', name: 'Northern Mariana Islands' },
    { code: 'PR', name: 'Puerto Rico' }, { code: 'VI', name: 'U.S. Virgin Islands' },
];

const IMPACT_CATEGORIES = [
    'Wages & Income', 'Healthcare', 'Small Business', 'Housing', 'Education',
    'Taxes', 'Military & Veterans', 'Agriculture', 'Environment', 'Immigration',
    'Criminal Justice', 'Technology', 'Infrastructure', 'Social Security & Medicare',
    'Government Operations',
];

let showParty = false;
let billOffset = 0;
const BILL_LIMIT = 20;

// --- Initialize ---
document.addEventListener('DOMContentLoaded', () => {
    checkDemoMode();
    populateStates();
    populateCategories();
    loadRecentBills();
    setupEventListeners();
});

async function checkDemoMode() {
    try {
        const resp = await fetch('/api/health');
        const data = await resp.json();
        if (data.demo_mode) {
            const banner = document.getElementById('demo-banner');
            if (banner) banner.hidden = false;
        }
    } catch { /* ignore */ }
}

function setupEventListeners() {
    const stateSelect = document.getElementById('state-select');
    const lookupBtn = document.getElementById('lookup-btn');
    const partyToggle = document.getElementById('party-toggle');
    const searchBtn = document.getElementById('search-btn');
    const billSearch = document.getElementById('bill-search');
    const loadMoreBtn = document.getElementById('load-more-btn');
    const hamburger = document.querySelector('.hamburger');

    stateSelect.addEventListener('change', () => {
        lookupBtn.disabled = !stateSelect.value;
    });

    lookupBtn.addEventListener('click', lookupMembers);

    partyToggle.addEventListener('click', () => {
        showParty = !showParty;
        const container = document.getElementById('results');
        container.classList.toggle('show-party', showParty);
        partyToggle.textContent = showParty ? 'Hide Party Affiliations' : 'Reveal Party Affiliations';

        if (showParty) {
            reloadMembersWithParty();
        }
    });

    searchBtn.addEventListener('click', () => searchBills());
    billSearch.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') searchBills();
    });

    loadMoreBtn.addEventListener('click', () => {
        billOffset += BILL_LIMIT;
        loadRecentBills(true);
    });

    hamburger.addEventListener('click', () => {
        const nav = document.querySelector('nav');
        nav.classList.toggle('open');
        hamburger.setAttribute('aria-expanded', nav.classList.contains('open'));
    });
}

// --- State Dropdown ---
function populateStates() {
    const select = document.getElementById('state-select');
    STATES.forEach(state => {
        const option = document.createElement('option');
        option.value = state.code;
        option.textContent = state.name;
        select.appendChild(option);
    });
}

// --- Category Grid ---
function populateCategories() {
    const grid = document.getElementById('category-grid');
    IMPACT_CATEGORIES.forEach(cat => {
        const tag = document.createElement('button');
        tag.className = 'category-tag';
        tag.textContent = cat;
        tag.setAttribute('aria-label', `Browse ${cat} bills`);
        tag.addEventListener('click', () => {
            document.querySelectorAll('.category-tag').forEach(t => t.classList.remove('active'));
            tag.classList.toggle('active');
            document.getElementById('bill-search').value = cat;
            searchBills();
        });
        grid.appendChild(tag);
    });
}

// --- DOM Helpers ---
function el(tag, attrs, ...children) {
    const element = document.createElement(tag);
    if (attrs) {
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'className') element.className = value;
            else if (key.startsWith('data')) element.setAttribute(key.replace(/([A-Z])/g, '-$1').toLowerCase(), value);
            else element.setAttribute(key, value);
        }
    }
    children.forEach(child => {
        if (typeof child === 'string') element.appendChild(document.createTextNode(child));
        else if (child) element.appendChild(child);
    });
    return element;
}

function clearChildren(parent) {
    while (parent.firstChild) parent.removeChild(parent.firstChild);
}

function showLoading(container, message) {
    clearChildren(container);
    const spinner = el('span', { className: 'spinner' });
    const wrapper = el('div', { className: 'loading' }, spinner, ` ${message}`);
    container.appendChild(wrapper);
}

function showError(container, message) {
    clearChildren(container);
    container.appendChild(el('div', { className: 'error-message' }, message));
}

function showEmpty(container, message) {
    clearChildren(container);
    container.appendChild(el('div', { className: 'empty-state' }, message));
}

// --- Member Lookup ---
async function lookupMembers() {
    const state = document.getElementById('state-select').value;
    const district = document.getElementById('district-input').value;
    if (!state) return;

    const resultsSection = document.getElementById('results');
    const grid = document.getElementById('member-grid');
    resultsSection.hidden = false;
    showLoading(grid, 'Loading representatives...');

    try {
        let url = `/api/members/${state}`;
        if (district) url = `/api/members/${state}/${district}`;

        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load members');
        const data = await response.json();

        const members = data.members || [];
        if (members.length === 0) {
            showEmpty(grid, 'No representatives found for this selection.');
            return;
        }

        renderMembers(grid, members);
    } catch (err) {
        showError(grid, 'Unable to load representatives. Congress.gov may be temporarily unavailable.');
    }
}

function renderMembers(grid, members) {
    clearChildren(grid);

    members.forEach(member => {
        const bioguideId = member.bioguideId || '';
        const name = member.name || member.directOrderName || 'Unknown';
        const depiction = member.depiction;
        const imageUrl = depiction ? depiction.imageUrl : '';
        const stateText = member.state || '';
        const district = member.district ? `District ${member.district}` : '';
        const terms = member.terms || { item: [] };
        const latestTerm = Array.isArray(terms.item) ? terms.item[terms.item.length - 1] : terms.item;
        const chamber = latestTerm ? latestTerm.chamber || '' : '';

        const photoEl = imageUrl
            ? el('img', { className: 'member-photo', src: imageUrl, alt: `Photo of ${name}`, loading: 'lazy' })
            : el('div', { className: 'member-photo-placeholder', 'aria-hidden': 'true' }, '?');

        const infoEl = el('div', { className: 'member-info' },
            el('h4', null, name),
            el('div', { className: 'chamber' }, chamber),
            el('div', { className: 'state-district' }, `${stateText} ${district}`.trim())
        );

        const card = el('article', {
            className: 'member-card',
            role: 'link',
            tabindex: '0',
            'aria-label': `View voting record for ${name}`,
        }, photoEl, infoEl);

        const navigate = () => { window.location.href = `/member?id=${bioguideId}`; };
        card.addEventListener('click', navigate);
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(); }
        });

        grid.appendChild(card);
    });
}

async function reloadMembersWithParty() {
    const state = document.getElementById('state-select').value;
    const district = document.getElementById('district-input').value;
    if (!state) return;

    try {
        let url = `/api/members/${state}`;
        if (district) url = `/api/members/${state}/${district}`;

        const response = await fetch(url);
        if (!response.ok) return;
        const data = await response.json();
        const members = data.members || [];

        const detailedMembers = await Promise.all(
            members.map(async (m) => {
                try {
                    const resp = await fetch(`/api/members/detail/${m.bioguideId}?show_party=true`);
                    if (resp.ok) {
                        const detail = await resp.json();
                        return detail.member || m;
                    }
                } catch { /* fall through */ }
                return m;
            })
        );

        const grid = document.getElementById('member-grid');
        clearChildren(grid);

        detailedMembers.forEach(member => {
            const bioguideId = member.bioguideId || '';
            const name = member.directOrderName || member.name || 'Unknown';
            const depiction = member.depiction;
            const imageUrl = depiction ? depiction.imageUrl : '';
            const stateText = member.state || '';
            const party = member.partyName || '';
            const terms = member.terms || { item: [] };
            const latestTerm = Array.isArray(terms.item) ? terms.item[terms.item.length - 1] : terms.item;
            const chamber = latestTerm ? latestTerm.chamber || '' : '';

            const photoEl = imageUrl
                ? el('img', { className: 'member-photo', src: imageUrl, alt: `Photo of ${name}`, loading: 'lazy' })
                : el('div', { className: 'member-photo-placeholder', 'aria-hidden': 'true' }, '?');

            const infoChildren = [
                el('h4', null, name),
                el('div', { className: 'chamber' }, chamber),
                el('div', { className: 'state-district' }, stateText),
            ];

            if (party) {
                const badge = el('span', { className: 'party-badge', style: 'display:inline-block;background:var(--bg-secondary);color:var(--text-secondary);border:1px solid var(--border);' }, party);
                infoChildren.push(badge);
            }

            const infoEl = el('div', { className: 'member-info' }, ...infoChildren);
            const card = el('article', { className: 'member-card', tabindex: '0' }, photoEl, infoEl);

            const navigate = () => { window.location.href = `/member?id=${bioguideId}`; };
            card.addEventListener('click', navigate);
            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(); }
            });

            grid.appendChild(card);
        });
    } catch { /* silently fail — party reveal is optional */ }
}

// --- Bills ---
async function loadRecentBills(append = false) {
    const billList = document.getElementById('bill-list');
    const loadMoreBtn = document.getElementById('load-more-btn');

    if (!append) showLoading(billList, 'Loading recent bills...');

    try {
        const response = await fetch(`/api/bills?offset=${billOffset}&limit=${BILL_LIMIT}`);
        if (!response.ok) throw new Error('Failed to load bills');
        const data = await response.json();

        const bills = data.bills || [];
        if (!append) clearChildren(billList);

        if (bills.length === 0 && !append) {
            showEmpty(billList, 'No bills found.');
            loadMoreBtn.hidden = true;
            return;
        }

        bills.forEach(bill => billList.appendChild(createBillItem(bill)));
        loadMoreBtn.hidden = bills.length < BILL_LIMIT;
    } catch (err) {
        if (!append) showError(billList, 'Unable to load bills. Please try again later.');
    }
}

async function searchBills() {
    const query = document.getElementById('bill-search').value.trim();
    if (!query) return;

    const billList = document.getElementById('bill-list');
    const loadMoreBtn = document.getElementById('load-more-btn');
    showLoading(billList, 'Searching...');
    loadMoreBtn.hidden = true;

    try {
        const response = await fetch(`/api/bills?limit=50`);
        if (!response.ok) throw new Error('Search failed');
        const data = await response.json();

        const queryLower = query.toLowerCase();
        const bills = (data.bills || []).filter(b => {
            const title = (b.title || b.latestTitle || '').toLowerCase();
            return title.includes(queryLower);
        });

        clearChildren(billList);
        if (bills.length === 0) {
            showEmpty(billList, 'No bills found matching your search.');
            return;
        }

        bills.forEach(bill => billList.appendChild(createBillItem(bill)));
    } catch {
        showError(billList, 'Search failed. Please try again.');
    }
}

function createBillItem(bill) {
    const number = bill.number || '';
    const type = bill.type || '';
    const congress = bill.congress || '';
    const title = bill.title || bill.latestTitle || 'Untitled Bill';
    const action = bill.latestAction ? bill.latestAction.text || '' : '';
    const actionDate = bill.latestAction ? bill.latestAction.actionDate || '' : '';

    const children = [
        el('span', { className: 'bill-number' }, `${type}.${number}`),
        document.createTextNode(' '),
        el('span', { className: 'bill-date' }, actionDate),
        el('h4', null, title),
    ];

    if (action) {
        children.push(el('div', { className: 'bill-action' }, action));
    }

    const item = el('article', { className: 'bill-item', tabindex: '0' }, ...children);

    const navigate = () => {
        window.location.href = `/bill?congress=${congress}&type=${type.toLowerCase()}&number=${number}`;
    };
    item.addEventListener('click', navigate);
    item.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(); }
    });

    return item;
}
