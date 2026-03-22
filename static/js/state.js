/* ============================================
   ClearVoting — State Overview Page
   ============================================ */

const STATE_NAMES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
    'AS': 'American Samoa', 'GU': 'Guam', 'MP': 'Northern Mariana Islands',
    'PR': 'Puerto Rico', 'VI': 'U.S. Virgin Islands',
};

let allMembers = [];
let showParty = localStorage.getItem('cv-show-party') === 'true';
let currentSort = 'name-asc';
let currentChamber = 'all';

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const stateCode = params.get('code');

    if (!stateCode) {
        showError('No state specified. Go back to the home page and select a state.');
        return;
    }

    loadStateOverview(stateCode.toUpperCase());
});

// --- DOM Helpers ---
function el(tag, attrs, ...children) {
    const element = document.createElement(tag);
    if (attrs) {
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'className') element.className = value;
            else if (key === 'onclick') element.addEventListener('click', value);
            else element.setAttribute(key, value);
        }
    }
    children.forEach(child => {
        if (typeof child === 'string') element.appendChild(document.createTextNode(child));
        else if (child) element.appendChild(child);
    });
    return element;
}

function clearEl(parent) {
    while (parent.firstChild) parent.removeChild(parent.firstChild);
}

function showError(message) {
    const container = document.getElementById('state-content');
    clearEl(container);
    container.appendChild(el('div', { className: 'error-message' }, message));
}

function formatNumber(num) {
    if (num >= 1000) return num.toLocaleString();
    return String(num);
}

// --- Load State Data ---
async function loadStateOverview(stateCode) {
    const container = document.getElementById('state-content');

    try {
        const response = await fetch(`/api/members/${stateCode}/overview`);
        if (!response.ok) throw new Error('Failed to load state data');
        const data = await response.json();

        allMembers = data.members || [];
        const aggregate = data.aggregate || {};
        const stateName = STATE_NAMES[stateCode] || stateCode;

        document.title = `${stateName} Representatives — ClearVoting`;

        clearEl(container);
        renderStateHeader(container, stateCode, stateName, allMembers);
        renderStateStats(container, aggregate);
        renderPartyToggle(container);
        renderControls(container);
        renderComparisonTable(container, getFilteredMembers());
        renderMobileCards(container, getFilteredMembers());
    } catch {
        showError('Unable to load state data. Please try again later.');
    }
}

// --- State Header ---
function renderStateHeader(container, stateCode, stateName, members) {
    const senators = members.filter(m => getChamber(m) === 'Senate').length;
    const reps = members.filter(m => getChamber(m) !== 'Senate').length;

    const subtitle = `Congressional delegation — ${senators} Senator${senators !== 1 ? 's' : ''}, ${reps} House Representative${reps !== 1 ? 's' : ''}`;

    container.appendChild(
        el('section', { className: 'state-header' },
            el('h1', null, stateName),
            el('p', { className: 'subtitle' }, subtitle)
        )
    );
}

// --- Aggregate Stats ---
function renderStateStats(container, aggregate) {
    const totalVotesDisplay = aggregate.total_votes >= 1000
        ? Math.round(aggregate.total_votes / 1000) + 'K'
        : String(aggregate.total_votes);

    container.appendChild(
        el('div', { className: 'state-stats' },
            createStatBox('Representatives', String(aggregate.total_members)),
            createStatBox('Avg. Participation', aggregate.avg_participation + '%'),
            createStatBox('Avg. Support Rate', aggregate.avg_support_rate + '%'),
            createStatBox('Total Votes Cast', totalVotesDisplay)
        )
    );
}

function createStatBox(label, number) {
    return el('div', { className: 'state-stat' },
        el('div', { className: 'label' }, label),
        el('div', { className: 'number' }, number)
    );
}

// --- Party Toggle ---
function renderPartyToggle(container) {
    const toggleBar = el('div', { className: 'party-toggle-bar' });
    const text = el('span', null, 'Party labels are hidden so you can compare on the record.');
    const btn = el('button', { className: 'btn-secondary', id: 'state-party-toggle' },
        showParty ? 'Hide Party' : 'Reveal Party'
    );

    btn.addEventListener('click', () => {
        showParty = !showParty;
        localStorage.setItem('cv-show-party', String(showParty));
        btn.textContent = showParty ? 'Hide Party' : 'Reveal Party';
        text.textContent = showParty
            ? 'Party labels are visible.'
            : 'Party labels are hidden so you can compare on the record.';
        refreshDisplay();
    });

    toggleBar.appendChild(text);
    toggleBar.appendChild(btn);
    container.appendChild(toggleBar);
}

// --- Filter/Sort Controls ---
function renderControls(container) {
    const chamberSelect = el('select', { id: 'chamber-filter', className: 'filter-select' });
    ['All', 'Senate', 'House'].forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.toLowerCase();
        option.textContent = opt;
        chamberSelect.appendChild(option);
    });
    chamberSelect.value = currentChamber;

    const sortSelect = el('select', { id: 'sort-by', className: 'filter-select' });
    const sortOptions = [
        { value: 'name-asc', text: 'Name (A-Z)' },
        { value: 'participation-desc', text: 'Participation (High to Low)' },
        { value: 'support-desc', text: 'Support Rate (High to Low)' },
    ];
    sortOptions.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt.value;
        option.textContent = opt.text;
        sortSelect.appendChild(option);
    });
    sortSelect.value = currentSort;

    chamberSelect.addEventListener('change', () => {
        currentChamber = chamberSelect.value;
        refreshDisplay();
    });

    sortSelect.addEventListener('change', () => {
        currentSort = sortSelect.value;
        refreshDisplay();
    });

    container.appendChild(
        el('div', { className: 'controls-bar' },
            el('div', null,
                el('label', { for: 'chamber-filter' }, 'Chamber: '),
                chamberSelect
            ),
            el('div', null,
                el('label', { for: 'sort-by' }, 'Sort by: '),
                sortSelect
            )
        )
    );
}

// --- Filtering & Sorting ---
function getChamber(member) {
    if (member.chamber) return member.chamber;
    const terms = member.terms || { item: [] };
    const items = Array.isArray(terms.item) ? terms.item : [terms.item].filter(Boolean);
    const latest = items[items.length - 1];
    if (!latest) return '';
    const ch = latest.chamber || '';
    if (ch.toLowerCase().includes('senate')) return 'Senate';
    if (ch.toLowerCase().includes('house')) return 'House';
    return ch;
}

function getMemberName(member) {
    const raw = member.directOrderName || member.name || 'Unknown';
    return raw.includes(', ') ? raw.split(', ').reverse().join(' ') : raw;
}

function getFilteredMembers() {
    let filtered = allMembers;

    if (currentChamber !== 'all') {
        filtered = filtered.filter(m => getChamber(m).toLowerCase() === currentChamber);
    }

    filtered = [...filtered];

    if (currentSort === 'name-asc') {
        filtered.sort((a, b) => getMemberName(a).localeCompare(getMemberName(b)));
    } else if (currentSort === 'participation-desc') {
        filtered.sort((a, b) => (b.participation_rate || 0) - (a.participation_rate || 0));
    } else if (currentSort === 'support-desc') {
        filtered.sort((a, b) => (b.support_rate || 0) - (a.support_rate || 0));
    }

    return filtered;
}

function refreshDisplay() {
    const members = getFilteredMembers();
    const tableBody = document.getElementById('comparison-tbody');
    const mobileContainer = document.getElementById('mobile-cards');

    if (tableBody) {
        clearEl(tableBody);
        members.forEach(m => tableBody.appendChild(createTableRow(m)));
    }

    if (mobileContainer) {
        clearEl(mobileContainer);
        members.forEach(m => mobileContainer.appendChild(createMobileCard(m)));
    }
}

// --- Participation Bar Color ---
function getBarClass(pct) {
    if (pct >= 85) return 'high';
    if (pct >= 70) return 'medium';
    return 'low';
}

// --- Comparison Table ---
function renderComparisonTable(container, members) {
    const table = el('table', { className: 'comparison-table', 'aria-label': 'Representatives comparison' });

    const thead = el('thead', null,
        el('tr', null,
            el('th', { style: 'width: 240px;' }, 'Representative'),
            el('th', null, 'Chamber'),
            el('th', null, 'District'),
            el('th', { className: 'sorted' }, 'Participation'),
            el('th', null, 'Vote Split'),
            el('th', null, 'Total Votes')
        )
    );

    const tbody = el('tbody', { id: 'comparison-tbody' });
    members.forEach(m => tbody.appendChild(createTableRow(m)));

    table.appendChild(thead);
    table.appendChild(tbody);
    container.appendChild(table);
}

function createTableRow(member) {
    const name = getMemberName(member);
    const bioguideId = member.bioguideId || '';
    const depiction = member.depiction;
    const imageUrl = depiction ? depiction.imageUrl : '';
    const chamber = getChamber(member);
    const district = member.district || null;
    const participation = member.participation_rate || 0;
    const yea = member.yea_count || 0;
    const nay = member.nay_count || 0;
    const totalVotes = member.total_votes || 0;
    const yeaPct = (yea + nay) > 0 ? Math.round(yea / (yea + nay) * 100) : 0;
    const nayPct = 100 - yeaPct;
    const party = member.partyName || '';
    const initials = name.split(' ').map(n => n[0]).join('').slice(0, 2);

    const photoEl = imageUrl
        ? el('img', { className: 'table-photo', src: imageUrl, alt: '', loading: 'lazy' })
        : el('div', { className: 'table-photo-placeholder' }, initials);

    const nameEl = el('span', { className: 'table-name' }, name);

    const memberCell = el('td', null,
        el('div', { className: 'member-cell' },
            photoEl,
            el('div', null, nameEl)
        )
    );

    const chamberCell = el('td', null, el('span', { className: 'table-chamber' }, chamber));

    const districtText = chamber === 'Senate' ? '—' : (district ? String(district) : '—');
    const districtCell = el('td', null, el('span', { className: 'table-chamber' }, districtText));

    // Participation mini bar
    const barFill = el('div', { className: `mini-bar-fill ${getBarClass(participation)}` });
    barFill.style.width = participation + '%';

    const participationCell = el('td', null,
        el('div', { className: 'mini-bar-container' },
            el('div', { className: 'mini-bar-track' }, barFill),
            el('span', { className: 'mini-pct' }, Math.round(participation) + '%')
        )
    );

    // Vote split bar
    const splitBar = el('div', { className: 'vote-split-bar' });
    const yeaBar = el('div', { className: 'split-yea' });
    yeaBar.style.width = yeaPct + '%';
    const nayBar = el('div', { className: 'split-nay' });
    nayBar.style.width = nayPct + '%';
    splitBar.appendChild(yeaBar);
    splitBar.appendChild(nayBar);

    const voteSplitCell = el('td', null,
        splitBar,
        el('div', { className: 'split-text' }, yeaPct + '% yea')
    );

    const totalCell = el('td', { style: 'font-size: var(--text-sm); color: var(--text-secondary);' },
        formatNumber(totalVotes)
    );

    const tr = el('tr', null,
        memberCell, chamberCell, districtCell, participationCell, voteSplitCell, totalCell
    );

    tr.addEventListener('click', () => {
        window.location.href = `/member?id=${bioguideId}`;
    });

    return tr;
}

// --- Mobile Cards ---
function renderMobileCards(container, members) {
    const mobileContainer = el('div', { className: 'member-cards-mobile', id: 'mobile-cards' });
    members.forEach(m => mobileContainer.appendChild(createMobileCard(m)));
    container.appendChild(mobileContainer);
}

function createMobileCard(member) {
    const name = getMemberName(member);
    const bioguideId = member.bioguideId || '';
    const depiction = member.depiction;
    const imageUrl = depiction ? depiction.imageUrl : '';
    const chamber = getChamber(member);
    const district = member.district;
    const participation = member.participation_rate || 0;
    const yea = member.yea_count || 0;
    const nay = member.nay_count || 0;
    const totalVotes = member.total_votes || 0;
    const supportRate = member.support_rate || 0;
    const yeaPct = (yea + nay) > 0 ? Math.round(yea / (yea + nay) * 100) : 0;
    const nayPct = 100 - yeaPct;
    const initials = name.split(' ').map(n => n[0]).join('').slice(0, 2);

    const meta = chamber === 'Senate'
        ? `Senate`
        : `House${district ? ' — District ' + district : ''}`;

    const photoEl = imageUrl
        ? el('img', { className: 'mobile-card-photo', src: imageUrl, alt: '', loading: 'lazy' })
        : el('div', { className: 'table-photo-placeholder', style: 'width: 48px; height: 48px;' }, initials);

    const voteBar = el('div', { className: 'mobile-vote-bar' });
    const yeaBar = el('div', { className: 'split-yea' });
    yeaBar.style.width = yeaPct + '%';
    const nayBar = el('div', { className: 'split-nay' });
    nayBar.style.width = nayPct + '%';
    voteBar.appendChild(yeaBar);
    voteBar.appendChild(nayBar);

    const card = el('article', { className: 'mobile-card' },
        el('div', { className: 'mobile-card-header' },
            photoEl,
            el('div', null,
                el('div', { className: 'mobile-card-name' }, name),
                el('div', { className: 'mobile-card-meta' }, meta)
            )
        ),
        el('div', { className: 'mobile-card-stats' },
            el('div', { className: 'mobile-stat' },
                el('strong', null, Math.round(participation) + '%'), ' participation'
            ),
            el('div', { className: 'mobile-stat' },
                el('strong', null, supportRate + '%'), ' support rate'
            ),
            el('div', { className: 'mobile-stat' },
                el('strong', null, formatNumber(totalVotes)), ' votes'
            )
        ),
        voteBar
    );

    card.addEventListener('click', () => {
        window.location.href = `/member?id=${bioguideId}`;
    });

    return card;
}
