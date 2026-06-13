/* ============================================
   ClearVoting — Landing Page
   ============================================ */

const STATES = [
    { code: 'CA', name: 'California' },
    { code: 'FL', name: 'Florida' },
    { code: 'NY', name: 'New York' },
    { code: 'TX', name: 'Texas' },
];

const ISSUE_CATEGORIES = [
    'Cost of Living', 'Healthcare', 'Jobs & Workers', 'Taxes',
    'Safety & Crime', 'Education', 'Money in Politics', 'Housing',
    'Immigration', 'Environment & Energy', 'Veterans & Military',
    'Social Security & Retirement',
];

let showParty = localStorage.getItem('cv-show-party') === 'true';
let billOffset = 0;
const BILL_LIMIT = 20;
let expandedCardId = null;
let currentMembers = [];
const summaryCache = new Map();

// --- Initialize ---
document.addEventListener('DOMContentLoaded', () => {
    populateStates();
    populateCategories();
    loadRecentBills();
    setupEventListeners();
});

function setupEventListeners() {
    const stateSelect = document.getElementById('state-select');
    const lookupBtn = document.getElementById('lookup-btn');
    const partyToggle = document.getElementById('party-toggle');
    const searchBtn = document.getElementById('search-btn');
    const billSearch = document.getElementById('bill-search');
    const loadMoreBtn = document.getElementById('load-more-btn');
    stateSelect.addEventListener('change', () => {
        lookupBtn.disabled = !stateSelect.value;
    });

    lookupBtn.addEventListener('click', lookupMembers);

    partyToggle.addEventListener('click', () => {
        showParty = !showParty;
        localStorage.setItem('cv-show-party', String(showParty));
        const container = document.getElementById('results');
        container.classList.toggle('show-party', showParty);
        partyToggle.textContent = showParty ? 'Hide Party Affiliations' : 'Reveal Party Affiliations';

        if (showParty) {
            reloadMembersWithParty();
        } else {
            const grid = document.getElementById('member-grid');
            renderMembers(grid, currentMembers);
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

    // Hamburger menu handled by feedback.js (loaded on all pages)

    // First-visit tooltip for party toggle (Phase 3.1)
    if (!localStorage.getItem('cv-party-tooltip-seen')) {
        const resultsSection = document.getElementById('results');
        const tooltipObserver = new MutationObserver(() => {
            if (!resultsSection.hidden && !document.getElementById('party-tooltip')) {
                const tooltip = el('div', { className: 'party-tooltip', id: 'party-tooltip' },
                    'Party labels are hidden by default so you can form your own opinion. Reveal them anytime with the button below.'
                );
                const closeBtn = el('button', { className: 'party-tooltip-close', 'aria-label': 'Dismiss' }, '\u00D7');
                closeBtn.addEventListener('click', () => {
                    tooltip.remove();
                    localStorage.setItem('cv-party-tooltip-seen', 'true');
                });
                tooltip.appendChild(closeBtn);
                const toggleSection = resultsSection.querySelector('.party-toggle-section');
                if (toggleSection) toggleSection.parentNode.insertBefore(tooltip, toggleSection);
                localStorage.setItem('cv-party-tooltip-seen', 'true');
                tooltipObserver.disconnect();
            }
        });
        tooltipObserver.observe(resultsSection, { attributes: true, attributeFilter: ['hidden'] });
    }
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
    ISSUE_CATEGORIES.forEach(cat => {
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

function showLoading(container, message, type) {
    clearChildren(container);
    if (type === 'members') {
        // Skeleton cards for member grid
        const grid = el('div', { className: 'skeleton-grid' });
        for (let i = 0; i < 4; i++) {
            grid.appendChild(el('div', { className: 'skeleton-card' },
                el('div', { className: 'skeleton skeleton-avatar' }),
                el('div', { className: 'skeleton-lines' },
                    el('div', { className: 'skeleton skeleton-line skeleton-line-medium' }),
                    el('div', { className: 'skeleton skeleton-line skeleton-line-short' }),
                    el('div', { className: 'skeleton skeleton-line skeleton-line-short' })
                )
            ));
        }
        container.appendChild(grid);
    } else if (type === 'bills') {
        // Skeleton items for bill list
        for (let i = 0; i < 5; i++) {
            container.appendChild(el('div', { className: 'skeleton-bill' },
                el('div', { className: 'skeleton skeleton-line skeleton-line-short' }),
                el('div', { className: 'skeleton skeleton-line skeleton-line-long' }),
                el('div', { className: 'skeleton skeleton-line skeleton-line-medium' })
            ));
        }
    } else {
        const spinner = el('span', { className: 'spinner' });
        const wrapper = el('div', { className: 'loading' }, spinner, ` ${message}`);
        container.appendChild(wrapper);
    }
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
    showLoading(grid, 'Loading representatives...', 'members');
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    try {
        let url = `/api/members/${state}?include_stats=true`;
        if (district) url = `/api/members/${state}/${district}?include_stats=true`;

        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to load members');
        const data = await response.json();

        const members = data.members || [];
        if (members.length === 0) {
            clearChildren(grid);
            const stateName = document.getElementById('state-select').selectedOptions[0]?.text || state;
            let emptyMsg, emptyHint;
            if (district) {
                emptyMsg = `No representative found for District ${district} in ${stateName}.`;
                emptyHint = 'Try removing the district number to see all representatives from this state.';
            } else {
                emptyMsg = `No representatives found for ${stateName}.`;
                emptyHint = 'Try selecting a different state, or check your district number.';
            }
            const emptyDiv = el('div', { className: 'empty-state' },
                el('span', { className: 'empty-state-icon' }, '\uD83D\uDD0D'),
                emptyMsg,
                el('span', { className: 'empty-state-hint' }, emptyHint)
            );
            grid.appendChild(emptyDiv);
            return;
        }

        currentMembers = members;
        // Show results count
        const countEl = document.getElementById('results-count');
        if (countEl) countEl.textContent = `Showing ${members.length} representative${members.length !== 1 ? 's' : ''}`;

        renderMembers(grid, members);

        // Add "View All Representatives" link to state overview
        const existingOverviewLink = grid.parentElement.querySelector('.state-overview-link');
        if (existingOverviewLink) existingOverviewLink.remove();
        const overviewLink = el('a', {
            className: 'state-overview-link',
            href: `/state?code=${state}`,
        }, 'Compare all representatives side by side \u2192');
        grid.parentElement.appendChild(overviewLink);

        // Apply persisted party toggle state
        if (showParty) {
            const container = document.getElementById('results');
            container.classList.add('show-party');
            document.getElementById('party-toggle').textContent = 'Hide Party Affiliations';
            reloadMembersWithParty();
        }
    } catch (err) {
        showError(grid, 'Unable to load representatives. Congress.gov may be temporarily unavailable.');
    }
}

function renderMembers(grid, members) {
    clearChildren(grid);
    expandedCardId = null;

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

        const header = el('div', { className: 'card-header' }, photoEl, infoEl);

        const cardChildren = [header];

        // Add viz stats if available (from include_stats=true)
        const stats = member.stats;
        if (stats && window.ClearVoteViz) {
            const participation = stats.participation_rate || 0;
            const yea = stats.yea_count || 0;
            const nay = stats.nay_count || 0;
            const totalVotes = yea + nay;
            const yeaPct = totalVotes > 0 ? Math.round((yea / totalVotes) * 100) : 0;
            const nayPct = totalVotes > 0 ? 100 - yeaPct : 0;

            const ring = window.ClearVoteViz.createParticipationRing(participation, 40);
            const ringItem = el('div', { className: 'card-stat-item' }, ring, el('span', null, 'participation'));

            const voteBarLabels = el('div', { className: 'card-vote-bar-labels' },
                el('span', { className: 'yea-label' }, `${yeaPct}% yea`),
                el('span', { className: 'nay-label' }, `${nayPct}% nay`)
            );
            const voteBar = window.ClearVoteViz.createVoteSplitBar(yeaPct, nayPct, 0);
            const voteBarWrap = el('div', { className: 'card-vote-bar-wrap' }, voteBarLabels, voteBar);

            const statsRow = el('div', { className: 'card-stats' }, ringItem, voteBarWrap);
            cardChildren.push(statsRow);
        }

        // Narrative snippet
        if (member.narrative_snippet) {
            cardChildren.push(el('p', { className: 'card-narrative' }, member.narrative_snippet));
        }

        // Profile link
        cardChildren.push(el('a', {
            className: 'card-profile-link',
            href: `/member?id=${bioguideId}`,
        }, 'View Full Profile \u2192'));

        const card = el('article', {
            className: 'member-card hover-lift',
            role: 'button',
            tabindex: '0',
            'aria-expanded': 'false',
            'aria-label': `View voting snapshot for ${name}`,
            'data-member-id': bioguideId,
        }, ...cardChildren);

        card.addEventListener('click', (e) => {
            if (e.target.closest('a')) return;
            toggleCard(bioguideId, card);
        });
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (e.target.closest('a')) return;
                toggleCard(bioguideId, card);
            }
        });

        grid.appendChild(card);
    });
}

// --- Card Expand/Collapse ---
function toggleCard(bioguideId, card) {
    if (expandedCardId === bioguideId) {
        collapseCard(card);
        expandedCardId = null;
    } else {
        const prev = expandedCardId ? document.querySelector(`.member-card[data-member-id="${expandedCardId}"]`) : null;
        if (prev) collapseCard(prev);
        expandCard(bioguideId, card);
        expandedCardId = bioguideId;
    }
}

async function expandCard(bioguideId, card) {
    card.classList.add('expanded');
    card.setAttribute('aria-expanded', 'true');

    const snapshot = el('div', { className: 'card-snapshot' });
    card.appendChild(snapshot);

    // Trigger reflow then animate
    snapshot.offsetHeight;
    snapshot.classList.add('visible');

    // Auto-scroll expanded card into view after animation
    setTimeout(() => {
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 320);

    if (summaryCache.has(bioguideId)) {
        renderCardSnapshot(snapshot, summaryCache.get(bioguideId), bioguideId);
        return;
    }

    snapshot.appendChild(el('div', { className: 'snapshot-loading' },
        el('span', { className: 'spinner' }), ' Loading...'
    ));

    try {
        const resp = await fetch(`/api/members/${bioguideId}/summary`);
        if (!resp.ok) throw new Error('Not found');
        const data = await resp.json();
        summaryCache.set(bioguideId, data);
        clearChildren(snapshot);
        renderCardSnapshot(snapshot, data, bioguideId);
    } catch {
        clearChildren(snapshot);
        snapshot.appendChild(el('div', { className: 'snapshot-empty' }, 'Voting record not yet available'));
    }
}

function collapseCard(card) {
    card.classList.remove('expanded');
    card.setAttribute('aria-expanded', 'false');
    const snapshot = card.querySelector('.card-snapshot');
    if (snapshot) snapshot.remove();
}

function renderCardSnapshot(container, data, bioguideId) {
    const stats = data.stats || {};
    const yeaPct = stats.total_votes ? Math.round((stats.yea_count / stats.total_votes) * 100) : 0;
    const nayPct = 100 - yeaPct;

    const statsRow = el('div', { className: 'snapshot-stats' },
        el('span', { className: 'snapshot-stat' },
            el('strong', null, `${stats.participation_rate ?? 0}%`), ' participation'
        ),
        el('span', { className: 'snapshot-stat' },
            el('span', { className: 'snapshot-yea' }, `${yeaPct}% yea`),
            ' / ',
            el('span', { className: 'snapshot-nay' }, `${nayPct}% nay`)
        )
    );
    container.appendChild(statsRow);

    // Narrative snippet — first sentence, truncated to ~120 chars
    if (data.narrative) {
        const firstSentence = data.narrative.split(/(?<=\.)\s/)[0] || data.narrative;
        const truncated = firstSentence.length > 120
            ? firstSentence.slice(0, 120).replace(/\s+\S*$/, '') + '\u2026'
            : firstSentence;
        container.appendChild(el('p', { className: 'snapshot-narrative' }, truncated));
    }

    const profileLink = el('a', {
        className: 'snapshot-profile-link',
        href: `/member?id=${bioguideId}`,
    }, 'View Full Profile \u2192');
    container.appendChild(profileLink);
}

async function reloadMembersWithParty() {
    const state = document.getElementById('state-select').value;
    const district = document.getElementById('district-input').value;
    if (!state) return;

    try {
        let url = `/api/members/${state}?include_stats=true`;
        if (district) url = `/api/members/${state}/${district}?include_stats=true`;

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
                        // Merge detail (which has party) with stats from original member
                        const merged = detail.member || m;
                        if (m.stats) merged.stats = m.stats;
                        if (m.narrative_snippet) merged.narrative_snippet = m.narrative_snippet;
                        return merged;
                    }
                } catch { /* fall through */ }
                return m;
            })
        );

        const grid = document.getElementById('member-grid');
        clearChildren(grid);
        expandedCardId = null;

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
                const badge = el('span', { className: 'party-badge', style: 'display:inline-block;' }, party);
                infoChildren.push(badge);
            }

            const infoEl = el('div', { className: 'member-info' }, ...infoChildren);
            const header = el('div', { className: 'card-header' }, photoEl, infoEl);

            const cardChildren = [header];

            // Add viz stats if available
            const stats = member.stats;
            if (stats && window.ClearVoteViz) {
                const participation = stats.participation_rate || 0;
                const yea = stats.yea_count || 0;
                const nay = stats.nay_count || 0;
                const totalVotes = yea + nay;
                const yeaPct = totalVotes > 0 ? Math.round((yea / totalVotes) * 100) : 0;
                const nayPct = totalVotes > 0 ? 100 - yeaPct : 0;

                const ring = window.ClearVoteViz.createParticipationRing(participation, 40);
                const ringItem = el('div', { className: 'card-stat-item' }, ring, el('span', null, 'participation'));

                const voteBarLabels = el('div', { className: 'card-vote-bar-labels' },
                    el('span', { className: 'yea-label' }, `${yeaPct}% yea`),
                    el('span', { className: 'nay-label' }, `${nayPct}% nay`)
                );
                const voteBar = window.ClearVoteViz.createVoteSplitBar(yeaPct, nayPct, 0);
                const voteBarWrap = el('div', { className: 'card-vote-bar-wrap' }, voteBarLabels, voteBar);

                const statsRow = el('div', { className: 'card-stats' }, ringItem, voteBarWrap);
                cardChildren.push(statsRow);
            }

            if (member.narrative_snippet) {
                cardChildren.push(el('p', { className: 'card-narrative' }, member.narrative_snippet));
            }

            cardChildren.push(el('a', {
                className: 'card-profile-link',
                href: `/member?id=${bioguideId}`,
            }, 'View Full Profile \u2192'));

            const card = el('article', {
                className: 'member-card hover-lift',
                role: 'button',
                tabindex: '0',
                'aria-expanded': 'false',
                'aria-label': `View voting snapshot for ${name}`,
                'data-member-id': bioguideId,
            }, ...cardChildren);

            card.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;
                toggleCard(bioguideId, card);
            });
            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    if (e.target.closest('a')) return;
                    toggleCard(bioguideId, card);
                }
            });

            grid.appendChild(card);
        });
    } catch { /* silently fail — party reveal is optional */ }
}

// --- Bills ---
async function loadRecentBills(append = false) {
    const billList = document.getElementById('bill-list');
    const loadMoreBtn = document.getElementById('load-more-btn');

    if (!append) showLoading(billList, 'Loading recent bills...', 'bills');

    try {
        const response = await fetch(`/api/bills?offset=${billOffset}&limit=${BILL_LIMIT}`);
        if (!response.ok) throw new Error('Failed to load bills');
        const data = await response.json();

        const bills = data.bills || [];
        if (!append) clearChildren(billList);

        if (bills.length === 0 && !append) {
            clearChildren(billList);
            billList.appendChild(el('div', { className: 'empty-state' },
                el('span', { className: 'empty-state-icon' }, '\uD83D\uDCDC'),
                'No bills found.',
                el('span', { className: 'empty-state-hint' }, 'Try a different search term or browse by topic above.')
            ));
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
    showLoading(billList, 'Searching...', 'bills');
    loadMoreBtn.hidden = true;

    try {
        const response = await fetch(`/api/search/bills?q=${encodeURIComponent(query)}&limit=50`);
        if (!response.ok) throw new Error('Search failed');
        const data = await response.json();

        const bills = data.bills || [];

        clearChildren(billList);
        if (bills.length === 0) {
            billList.appendChild(el('div', { className: 'empty-state' },
                el('span', { className: 'empty-state-icon' }, '\uD83D\uDD0D'),
                `No bills found matching "${query}".`,
                el('span', { className: 'empty-state-hint' }, 'Try a broader term or browse by category above.')
            ));
            return;
        }

        billList.insertBefore(
            el('div', { className: 'results-count' }, `${bills.length} bill${bills.length !== 1 ? 's' : ''} found for "${query}"`),
            billList.firstChild
        );

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

    const item = el('article', { className: 'bill-item hover-lift', tabindex: '0' }, ...children);

    const navigate = () => {
        window.location.href = `/bill?congress=${congress}&type=${type.toLowerCase()}&number=${number}`;
    };
    item.addEventListener('click', navigate);
    item.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(); }
    });

    return item;
}
