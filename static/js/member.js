/* ============================================
   ClearVoting — Member Profile Page
   ============================================ */

let showParty = false;
let memberData = null;

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const bioguideId = params.get('id');

    if (!bioguideId) {
        showError('No representative ID provided. Go back to the home page and select a representative.');
        return;
    }

    loadMember(bioguideId);
    // Hamburger menu handled by feedback.js (loaded on all pages)
});

// --- DOM Helpers ---
function el(tag, attrs, ...children) {
    const element = document.createElement(tag);
    if (attrs) {
        for (const [key, value] of Object.entries(attrs)) {
            if (key === 'className') element.className = value;
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
    const container = document.getElementById('member-content');
    clearEl(container);
    container.appendChild(el('div', { className: 'error-message' }, message));
}

// --- Load Member ---
async function loadMember(bioguideId) {
    const container = document.getElementById('member-content');

    try {
        const response = await fetch(`/api/members/detail/${bioguideId}`);
        if (!response.ok) throw new Error('Failed to load member');
        const data = await response.json();

        memberData = data.member || data;
        const titleName = memberData.directOrderName || memberData.name || memberData.firstName || 'Representative';
        document.title = `${titleName.includes(', ') ? titleName.split(', ').reverse().join(' ') : titleName} — ClearVoting`;
        renderMember(container, memberData, bioguideId);
    } catch (err) {
        showError('Unable to load representative data. Congress.gov may be temporarily unavailable.');
    }
}

function renderMember(container, member, bioguideId) {
    clearEl(container);

    const rawName = member.directOrderName || `${member.firstName || ''} ${member.lastName || ''}`.trim() || member.name || 'Unknown';
    // Convert "Last, First" to "First Last" if needed
    const name = rawName.includes(', ') ? rawName.split(', ').reverse().join(' ') : rawName;
    const depiction = member.depiction;
    const imageUrl = depiction ? depiction.imageUrl : '';
    const stateText = member.state || '';
    const terms = member.terms || { item: [] };
    const termItems = Array.isArray(terms.item) ? terms.item : [terms.item].filter(Boolean);
    const latestTerm = termItems[termItems.length - 1];
    const chamber = latestTerm ? latestTerm.chamber || '' : '';
    const district = member.district ? `District ${member.district}` : '';

    // Header with inline party toggle
    const photoEl = imageUrl
        ? el('img', { className: 'member-photo', src: imageUrl, alt: `Photo of ${name}`, loading: 'lazy' })
        : el('div', { className: 'member-photo-placeholder', 'aria-hidden': 'true' }, '?');

    const metaText = [chamber, stateText, district].filter(Boolean).join(' — ');

    const toggleBtn = el('button', { className: 'party-toggle-inline', id: 'party-toggle-btn', 'aria-label': 'Reveal party affiliation' }, 'Show Party');

    toggleBtn.addEventListener('click', async () => {
        showParty = !showParty;
        toggleBtn.textContent = showParty ? 'Hide Party' : 'Show Party';
        toggleBtn.classList.toggle('active', showParty);

        if (showParty) {
            try {
                const resp = await fetch(`/api/members/detail/${bioguideId}?show_party=true`);
                if (resp.ok) {
                    const detail = await resp.json();
                    const m = detail.member || detail;
                    const partyDisplay = document.getElementById('party-display');
                    clearEl(partyDisplay);
                    if (m.partyName) {
                        partyDisplay.appendChild(document.createTextNode(m.partyName));
                    }
                }
            } catch { /* silently fail */ }
        } else {
            const partyDisplay = document.getElementById('party-display');
            clearEl(partyDisplay);
        }
    });

    const headerInfo = el('div', { className: 'member-header-info' },
        el('h2', null, name),
        el('div', { className: 'member-meta-row' },
            el('span', { className: 'member-meta' }, metaText),
            toggleBtn
        ),
        el('div', { className: 'member-meta', id: 'party-display' })
    );

    const header = el('div', { className: 'member-header' }, photoEl, headerInfo);
    container.appendChild(header);

    // Sticky name bar — appears when the member header scrolls out of view
    const stickyBar = el('div', { className: 'member-sticky-bar' });
    if (imageUrl) {
        stickyBar.appendChild(el('img', { src: imageUrl, alt: '' }));
    }
    stickyBar.appendChild(el('span', { className: 'sticky-name' }, name));
    stickyBar.appendChild(el('span', { className: 'sticky-meta' }, metaText));
    container.appendChild(stickyBar);

    // Position sticky bar just below the site header
    const siteHeader = document.querySelector('.site-header');
    if (siteHeader) {
        stickyBar.style.top = siteHeader.offsetHeight + 'px';
    }

    const observer = new IntersectionObserver(([entry]) => {
        stickyBar.classList.toggle('visible', !entry.isIntersecting);
    }, { threshold: 0 });
    observer.observe(header);

    // Voting summary (brief text at top, loaded async)
    const summaryEl = el('div', { id: 'voting-summary', className: 'voting-summary' });
    container.appendChild(summaryEl);

    // Service info (collapsed)
    if (termItems.length > 0) {
        const firstYear = termItems[0]?.startYear || '';
        const latestYear = termItems[termItems.length - 1]?.endYear || 'present';
        const summaryText = `${chamber}, ${firstYear}–${latestYear}`;

        const serviceSection = el('section', { className: 'service-compact' });

        const serviceHeader = el('div', { className: 'service-compact-header' });
        serviceHeader.appendChild(el('h3', null, 'Service History'));
        serviceHeader.appendChild(el('span', { className: 'service-compact-summary' }, summaryText));

        const expandBtn = el('button', { className: 'service-expand-btn', 'aria-expanded': 'false', 'aria-label': 'Show full service history' }, 'Details');
        serviceHeader.appendChild(expandBtn);
        serviceSection.appendChild(serviceHeader);

        const table = el('table', { className: 'data-table service-detail-table' });
        const thead = el('thead', null,
            el('tr', null,
                el('th', null, 'Chamber'),
                el('th', null, 'Years')
            )
        );
        table.appendChild(thead);

        const tbody = el('tbody');
        termItems.forEach(term => {
            const row = el('tr', null,
                el('td', null, term.chamber || ''),
                el('td', null, `${term.startYear || ''}–${term.endYear || 'present'}`)
            );
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        serviceSection.appendChild(table);

        expandBtn.addEventListener('click', () => {
            const expanded = table.classList.toggle('expanded');
            expandBtn.setAttribute('aria-expanded', String(expanded));
            expandBtn.textContent = expanded ? 'Less' : 'Details';
        });

        container.appendChild(serviceSection);
    }

    // --- Tabbed Content ---
    const tabIds = ['voting-record', 'sponsored-section', 'finance-section'];
    const tabLabels = ['Voting Record', 'Sponsored Bills', 'Campaign Finance'];

    // Tab bar
    const tabBar = el('div', { className: 'member-tab-bar', role: 'tablist', 'aria-label': 'Member sections' });
    const tabPanels = [];

    tabIds.forEach((id, i) => {
        const isActive = i === 0;
        const tab = el('button', {
            className: 'member-tab' + (isActive ? ' active' : ''),
            role: 'tab',
            id: `tab-${id}`,
            'aria-selected': String(isActive),
            'aria-controls': `panel-${id}`,
        }, tabLabels[i]);

        tab.addEventListener('click', () => {
            tabBar.querySelectorAll('.member-tab').forEach(t => {
                t.classList.remove('active');
                t.setAttribute('aria-selected', 'false');
            });
            tab.classList.add('active');
            tab.setAttribute('aria-selected', 'true');
            tabPanels.forEach(p => p.hidden = true);
            document.getElementById(`panel-${id}`).hidden = false;
        });
        tabBar.appendChild(tab);

        const panel = el('div', {
            className: 'member-tab-panel',
            role: 'tabpanel',
            id: `panel-${id}`,
            'aria-labelledby': `tab-${id}`,
        });
        panel.hidden = !isActive;
        tabPanels.push(panel);
    });

    container.appendChild(tabBar);

    // Position tab bar sticky offset below site header + sticky bar
    const siteHeaderForTabs = document.querySelector('.site-header');
    if (siteHeaderForTabs) {
        const tabTop = siteHeaderForTabs.offsetHeight + stickyBar.offsetHeight;
        tabBar.style.top = tabTop + 'px';
    }

    // Voting Record panel (default active)
    const votingPanel = tabPanels[0];
    const votingSection = el('div', { id: 'voting-record' });
    votingSection.appendChild(el('div', { className: 'loading' },
        el('span', { className: 'spinner' }),
        ' Loading voting record...'
    ));
    votingPanel.appendChild(votingSection);
    container.appendChild(votingPanel);

    loadVotingRecord(bioguideId).then(() => {
        const tab = document.getElementById('tab-voting-record');
        if (tab && allVotes.length > 0) {
            tab.textContent = `Voting Record (${allVotes.length})`;
        }
    });

    // Sponsored Bills panel
    const sponsoredPanel = tabPanels[1];
    const sponsoredSection = el('section', { className: 'bill-section', id: 'sponsored-section' });
    sponsoredSection.appendChild(el('h3', null, 'Sponsored Legislation'));
    sponsoredSection.appendChild(el('div', { className: 'loading', id: 'sponsored-loading' },
        el('span', { className: 'spinner' }), ' Loading sponsored bills...'));
    sponsoredPanel.appendChild(sponsoredSection);
    container.appendChild(sponsoredPanel);

    loadSponsoredLegislation(bioguideId);

    // Campaign Finance panel
    const financePanel = tabPanels[2];
    const financeSection = el('section', { className: 'bill-section', id: 'finance-section' });
    financeSection.appendChild(el('h3', null, 'Campaign Finance'));
    financeSection.appendChild(el('div', { className: 'loading', id: 'finance-loading' },
        el('span', { className: 'spinner' }), ' Loading campaign finance data...'));
    financePanel.appendChild(financeSection);
    container.appendChild(financePanel);

    loadDonations(bioguideId);

    // Source link — Congress.gov requires /member/{name-slug}/{bioguideId}
    const nameSlug = name.toLowerCase().replace(/[^a-z\s-]/g, '').trim().replace(/\s+/g, '-');
    const sourceLink = el('a', {
        href: `https://www.congress.gov/member/${nameSlug}/${bioguideId}`,
        target: '_blank',
        rel: 'noopener',
        className: 'source-link',
    }, 'View full profile on Congress.gov');
    container.appendChild(sourceLink);
}

async function loadSponsoredLegislation(bioguideId) {
    const section = document.getElementById('sponsored-section');
    const loading = document.getElementById('sponsored-loading');
    if (!section) return;

    try {
        const response = await fetch(`/api/members/${bioguideId}/sponsored`);
        if (!response.ok) throw new Error('Failed');
        const data = await response.json();
        if (loading) loading.remove();

        const bills = data.bills || [];

        // Update tab count
        const sponsoredTab = document.getElementById('tab-sponsored-section');
        if (sponsoredTab) sponsoredTab.textContent = `Sponsored Bills (${bills.length})`;

        if (bills.length === 0) {
            section.appendChild(el('div', { className: 'empty-state' }, 'No sponsored bills found in synced data.'));
            return;
        }

        const countLabel = el('div', { className: 'vote-section-desc' }, `${bills.length} bill${bills.length !== 1 ? 's' : ''} sponsored in synced data`);
        section.appendChild(countLabel);

        const list = el('div', { className: 'vote-list' });
        bills.forEach(bill => {
            const item = el('div', { className: 'vote-item' });

            const topRow = el('div', { className: 'vote-item-top' });
            topRow.appendChild(el('span', { className: 'bill-number' }, `${bill.type}.${bill.number}`));
            topRow.appendChild(el('span', { className: 'bill-date' }, bill.introduced_date));
            item.appendChild(topRow);

            item.appendChild(el('div', { className: 'vote-item-title' }, bill.title));

            const bottomRow = el('div', { className: 'vote-item-bottom' });
            if (bill.latest_action) {
                bottomRow.appendChild(el('span', { className: 'vote-item-result' }, bill.latest_action));
            }
            if (bill.policy_area) {
                bottomRow.appendChild(el('span', { className: 'impact-tag' }, bill.policy_area));
            }
            item.appendChild(bottomRow);

            const billType = (bill.type || '').toUpperCase();
            item.style.cursor = 'pointer';
            item.addEventListener('click', () => {
                window.location.href = `/bill?congress=${bill.congress}&type=${billType}&number=${bill.number}`;
            });
            item.setAttribute('role', 'link');
            item.setAttribute('tabindex', '0');
            item.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    window.location.href = `/bill?congress=${bill.congress}&type=${billType}&number=${bill.number}`;
                }
            });

            list.appendChild(item);
        });
        section.appendChild(list);
    } catch {
        if (loading) loading.remove();
        section.appendChild(el('div', { className: 'empty-state' }, 'Could not load sponsored legislation.'));
    }
}

// --- Voting Record ---

function formatDeficitAmount(billions) {
    const abs = Math.abs(billions);
    const sign = billions >= 0 ? '+' : '-';
    if (abs >= 1000) return `${sign}$${(abs / 1000).toFixed(1)} trillion`;
    return `${sign}$${abs} billion`;
}

let allVotes = [];
let allCategories = [];
let activePolicyArea = 'all';
let activeVoteType = 'all';
let currentPage = 1;
const VOTES_PER_PAGE = 15;

async function loadVotingRecord(bioguideId) {
    const container = document.getElementById('voting-record');
    if (!container) return;

    try {
        const [votesResponse, summaryResponse] = await Promise.all([
            fetch(`/api/members/${bioguideId}/votes?limit=2000`),
            fetch(`/api/members/${bioguideId}/summary`).catch(() => null)
        ]);
        if (!votesResponse.ok) throw new Error('Failed to load votes');
        const data = await votesResponse.json();

        let summaryData = null;
        if (summaryResponse && summaryResponse.ok) {
            summaryData = await summaryResponse.json();
        }

        clearEl(container);
        renderVotingSummary(data.stats, data.votes, summaryData);
        renderVotingStats(container, data.stats, data.congresses, data.categories || data.policy_areas, data.votes);
    } catch (err) {
        clearEl(container);
        container.appendChild(el('div', { className: 'empty-state' }, 'Voting record unavailable.'));
    }
}

function renderVotingSummary(stats, votes, summaryData) {
    const summaryEl = document.getElementById('voting-summary');
    if (!summaryEl) return;
    clearEl(summaryEl);

    // Analyze voting patterns
    const yeaPct = Math.round((stats.yea_count / (stats.yea_count + stats.nay_count)) * 100);

    // Deduplicate votes by bill — keep final (most recent) vote per bill
    // Only include votes with real AI summaries (not raw bill numbers like "PN1748")
    // Spread across policy areas to avoid recency bias
    const seenBills = new Set();
    const yeaByArea = {};
    const nayByArea = {};
    votes.forEach(v => {
        const key = v.bill_id || v.one_liner;
        if (!key || seenBills.has(key)) return;
        // Skip votes with no real description — raw bill numbers are useless
        if (!v.one_liner || v.one_liner === v.bill_number || v.one_liner.match(/^(PN|P\.N\.)\s*\d/)) return;
        if (!v.policy_area) return;
        seenBills.add(key);
        const isYea = v.vote === 'Yea' || v.vote === 'Aye';
        const isNay = v.vote === 'Nay' || v.vote === 'No';
        const area = v.policy_area || 'Other';
        if (isYea) {
            if (!yeaByArea[area]) yeaByArea[area] = [];
            yeaByArea[area].push(v);
        } else if (isNay) {
            if (!nayByArea[area]) nayByArea[area] = [];
            nayByArea[area].push(v);
        }
    });
    // Pick votes spread across policy areas (round-robin) to show breadth
    function spreadPick(byArea, count) {
        const areas = Object.keys(byArea).sort((a, b) => byArea[b].length - byArea[a].length);
        const result = [];
        let idx = 0;
        while (result.length < count && areas.length > 0) {
            const area = areas[idx % areas.length];
            const areaVotes = byArea[area];
            const pick = areaVotes.shift();
            if (pick) result.push(pick);
            if (areaVotes.length === 0) areas.splice(idx % areas.length, 1);
            else idx++;
            if (areas.length === 0) break;
        }
        return result;
    }
    const uniqueYea = spreadPick(yeaByArea, 6);
    const uniqueNay = spreadPick(nayByArea, 4);

    // Build the summary card
    const card = el('section', { className: 'voting-summary-card' });
    card.appendChild(el('h3', null, 'At a Glance'));

    // AI narrative (if available)
    if (summaryData && summaryData.narrative) {
        const narrative = el('p', { className: 'summary-narrative' }, summaryData.narrative);
        card.appendChild(narrative);
        card.appendChild(el('p', { className: 'ai-attribution' },
            'Summary generated by AI from official voting record data.'));
    }

    // Overview — plain language
    const overview = el('p', { className: 'summary-overview' },
        `Supports ${yeaPct}% of bills that come to a vote. Shows up for ${stats.participation_rate}% of all votes.`
    );
    card.appendChild(overview);

    // What they voted for — deduplicated, plain language
    if (uniqueYea.length > 0) {
        const forSection = el('div', { className: 'summary-voted-section summary-for' });
        forSection.appendChild(el('h4', null, 'What They Supported'));
        const forList = el('ul', { className: 'summary-vote-list' });
        uniqueYea.slice(0, 6).forEach(v => {
            forList.appendChild(el('li', null, v.one_liner));
        });
        forSection.appendChild(forList);
        card.appendChild(forSection);
    }

    // What they voted against — deduplicated, plain language
    if (uniqueNay.length > 0) {
        const againstSection = el('div', { className: 'summary-voted-section summary-against' });
        againstSection.appendChild(el('h4', null, 'What They Opposed'));
        const againstList = el('ul', { className: 'summary-vote-list' });
        uniqueNay.slice(0, 4).forEach(v => {
            againstList.appendChild(el('li', null, v.one_liner));
        });
        againstSection.appendChild(againstList);
        card.appendChild(againstSection);
    }

    summaryEl.appendChild(card);
}


function renderVotingStats(container, stats, congresses, categories, votes) {
    allVotes = votes;
    allCategories = categories;

    const congressLabel = congresses && congresses.length > 1
        ? `${Math.min(...congresses)}th\u2013${Math.max(...congresses)}th Congress`
        : congresses && congresses.length === 1
            ? `${congresses[0]}th Congress`
            : '';

    // Compact stats bar with inline pie charts
    const statsBar = el('div', { className: 'stats-bar' });
    const total = stats.yea_count + stats.nay_count + stats.not_voting_count;

    // Participation segment with pie chart
    const participationItem = el('div', { className: 'stats-bar-item' });
    const partRow = el('div', { className: 'stats-bar-row' });
    const participationChart = window.ClearVotingUI.renderVotePieChart({
        yeas: Math.round(stats.participation_rate),
        nays: Math.round(100 - stats.participation_rate),
    }, 48);
    if (participationChart) partRow.appendChild(participationChart);
    partRow.appendChild(el('span', { className: 'stats-bar-label' },
        el('strong', null, `${stats.participation_rate}%`), ' participation'
    ));
    participationItem.appendChild(partRow);
    statsBar.appendChild(participationItem);

    // Vote breakdown segment with pie chart
    const breakdownItem = el('div', { className: 'stats-bar-item' });
    const breakRow = el('div', { className: 'stats-bar-row' });
    const voteChart = window.ClearVotingUI.renderVotePieChart({
        yeas: stats.yea_count,
        nays: stats.nay_count,
        absent: stats.not_voting_count,
    }, 48);
    if (voteChart) breakRow.appendChild(voteChart);
    breakRow.appendChild(el('span', { className: 'stats-bar-label' },
        el('span', { className: 'stats-bar-yea' }, `${stats.yea_count} Yea`),
        ' \u00b7 ',
        el('span', { className: 'stats-bar-nay' }, `${stats.nay_count} Nay`),
        ' \u00b7 ',
        el('span', { className: 'stats-bar-absent' }, `${stats.not_voting_count} Missed`)
    ));
    breakdownItem.appendChild(breakRow);
    statsBar.appendChild(breakdownItem);

    // Total + congress
    const totalItem = el('div', { className: 'stats-bar-item' });
    totalItem.appendChild(el('span', { className: 'stats-bar-label stats-bar-label-total' },
        el('strong', null, `${stats.total_votes} votes`),
        congressLabel ? ` \u00b7 ${congressLabel}` : ''
    ));
    statsBar.appendChild(totalItem);

    container.appendChild(statsBar);

    // Vote-type filter buttons (outside the stats bar)
    const voteTypeFilters = el('div', { className: 'vote-type-filters' });
    const voteTypes = [
        { key: 'all', label: 'All', color: null, count: total },
        { key: 'yea', label: 'Yea', color: '#2E8540', count: stats.yea_count },
        { key: 'nay', label: 'Nay', color: '#CD2026', count: stats.nay_count },
        { key: 'absent', label: 'Missed', color: '#AEB0B5', count: stats.not_voting_count },
    ];
    voteTypes.forEach(vt => {
        const btn = el('button', {
            className: 'vote-type-btn' + (vt.key === 'all' ? ' active' : ''),
            'data-vote-type': vt.key,
            'aria-label': `Filter votes: ${vt.label}`,
        });
        if (vt.color) {
            const dot = el('span', { className: 'vote-type-dot' });
            dot.style.background = vt.color;
            btn.appendChild(dot);
        }
        btn.appendChild(document.createTextNode(`${vt.label}: ${vt.count}`));
        btn.addEventListener('click', () => {
            activeVoteType = vt.key;
            document.querySelectorAll('.vote-type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentPage = 1;
            applyFilters();
        });
        voteTypeFilters.appendChild(btn);
    });
    container.appendChild(voteTypeFilters);

    // Category filter chips
    const filterRow = el('div', { className: 'issue-filters' });
    const allChip = el('button', { className: 'category-tag active', 'data-area': 'all' }, 'All');
    allChip.addEventListener('click', () => filterVotes('all'));
    filterRow.appendChild(allChip);

    const votesCategories = new Set(votes.flatMap(v => v.issue_categories || []));
    categories.filter(cat => votesCategories.has(cat)).forEach(cat => {
        const chip = el('button', { className: 'category-tag', 'data-area': cat }, cat);
        chip.addEventListener('click', () => filterVotes(cat));
        filterRow.appendChild(chip);
    });
    container.appendChild(filterRow);

    // Vote list
    const listEl = el('div', { id: 'vote-list', className: 'bill-list' });
    _renderVoteItems(listEl, votes);
    container.appendChild(listEl);
}

function matchesVoteType(vote, type) {
    const v = (vote.vote || '').toLowerCase();
    if (type === 'yea') return v === 'yea' || v === 'aye';
    if (type === 'nay') return v === 'nay' || v === 'no';
    if (type === 'absent') return v === 'not voting' || v === 'present';
    return true;
}

function filterVotes(area) {
    activePolicyArea = area;
    currentPage = 1;
    document.querySelectorAll('.issue-filters .category-tag').forEach(c => c.classList.remove('active'));
    const active = document.querySelector(`.issue-filters .category-tag[data-area="${CSS.escape(area)}"]`);
    if (active) active.classList.add('active');
    applyFilters();
}

function applyFilters() {
    const filtered = allVotes
        .filter(v => activePolicyArea === 'all' || (v.issue_categories || []).includes(activePolicyArea))
        .filter(v => activeVoteType === 'all' || matchesVoteType(v, activeVoteType));
    const listEl = document.getElementById('vote-list');
    if (listEl) {
        clearEl(listEl);
        _renderVoteItems(listEl, filtered);
    }
}


function getSourceUrl(vote) {
    if (!vote.vote_number || !vote.session) return null;
    const c = vote.congress || 119;
    const s = vote.session;
    const vn = vote.vote_number;
    if (vote.chamber === 'Senate') {
        const pad = String(vn).padStart(5, '0');
        return `https://www.senate.gov/legislative/LIS/roll_call_votes/vote${c}${s}/vote_${c}_${s}_${pad}.htm`;
    }
    if (vote.chamber === 'House') {
        const year = vote.date ? vote.date.slice(0, 4) : '2025';
        return `https://clerk.house.gov/Votes/${year}${vn}`;
    }
    return null;
}

function _parseBillId(billId) {
    if (!billId) return { type: null, number: null };
    const parts = billId.split('-');
    if (parts.length >= 3) {
        return { type: parts[1].toUpperCase(), number: parts.slice(2).join('-') };
    }
    return { type: null, number: null };
}

function _buildVoteItem(vote) {
    if (!vote._parsed) {
        const parsed = _parseBillId(vote.bill_id);
        vote.bill_type = parsed.type;
        vote.bill_number_raw = parsed.number;
        vote._parsed = true;
    }
    const item = el('div', { className: 'vote-item' });

    const topRow = el('div', { className: 'vote-item-top' });
    topRow.appendChild(el('span', { className: 'bill-number' }, vote.bill_number));
    topRow.appendChild(el('span', { className: 'bill-date' }, vote.date));
    item.appendChild(topRow);

    item.appendChild(el('div', { className: 'vote-item-title' }, vote.bill_title));
    item.appendChild(el('div', { className: 'vote-item-oneliner' }, vote.one_liner));

    const bottomRow = el('div', { className: 'vote-item-bottom' });
    const voteBadge = el('span', { className: 'vote-label ' + vote.vote.toLowerCase().replace(/\s+/g, '-') }, vote.vote);
    bottomRow.appendChild(voteBadge);

    const resultText = 'Bill ' + vote.result;
    bottomRow.appendChild(el('span', { className: 'vote-item-result' }, resultText));

    const policyTag = el('span', { className: 'impact-tag' }, vote.policy_area);
    bottomRow.appendChild(policyTag);

    if (vote.cbo_deficit_impact) {
        const deficitClass = vote.cbo_deficit_billions > 0 ? 'deficit-increase' : 'deficit-decrease';
        const cboTag = el('span', { className: `cbo-tag ${deficitClass}` }, `CBO: ${vote.cbo_deficit_impact}`);
        bottomRow.appendChild(cboTag);
    }

    item.appendChild(bottomRow);

    const sourceUrl = getSourceUrl(vote);
    if (sourceUrl) {
        const sourceLink = el('a', {
            className: 'vote-source-link',
            href: sourceUrl,
            target: '_blank',
            rel: 'noopener',
        }, 'Roll call source \u2192');
        sourceLink.addEventListener('click', (e) => e.stopPropagation());
        item.appendChild(sourceLink);
    }

    const clickableTypes = ['HR', 'S', 'HJRES', 'SJRES'];
    if (clickableTypes.includes(vote.bill_type)) {
        item.style.cursor = 'pointer';
        item.addEventListener('click', () => {
            window.location.href = `/bill?congress=${vote.congress}&type=${vote.bill_type}&number=${vote.bill_number_raw}`;
        });
        item.setAttribute('role', 'link');
        item.setAttribute('tabindex', '0');
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                window.location.href = `/bill?congress=${vote.congress}&type=${vote.bill_type}&number=${vote.bill_number_raw}`;
            }
        });
    } else {
        item.classList.add('vote-item-resolution');
        const resLabel = el('div', { className: 'resolution-label' }, 'Resolution — no details available');
        item.appendChild(resLabel);
    }

    return item;
}

function _buildPaginationControls(totalItems, scrollTarget) {
    const totalPages = Math.ceil(totalItems / VOTES_PER_PAGE);
    if (totalPages <= 1) return null;

    const start = (currentPage - 1) * VOTES_PER_PAGE + 1;
    const end = Math.min(currentPage * VOTES_PER_PAGE, totalItems);

    const controls = el('div', { className: 'vote-pagination' });

    const prevBtn = el('button', {
        className: 'vote-pagination-btn',
        'aria-label': 'Previous page',
    }, '\u2039 Prev');
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            applyFilters();
            if (scrollTarget) scrollTarget.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });

    const nextBtn = el('button', {
        className: 'vote-pagination-btn',
        'aria-label': 'Next page',
    }, 'Next \u203a');
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            applyFilters();
            if (scrollTarget) scrollTarget.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });

    controls.appendChild(prevBtn);
    controls.appendChild(el('span', { className: 'vote-pagination-info' },
        `Showing ${start}\u2013${end} of ${totalItems}`));
    controls.appendChild(nextBtn);

    return controls;
}

function _renderVoteItems(listEl, votes) {
    if (votes.length === 0) {
        listEl.appendChild(el('div', { className: 'empty-state' }, 'No votes found for this category.'));
        return;
    }

    // Parse all votes
    votes.forEach(v => {
        if (!v._parsed) {
            const parsed = _parseBillId(v.bill_id);
            v.bill_type = parsed.type;
            v.bill_number_raw = parsed.number;
            v._parsed = true;
        }
    });

    // Paginate the combined list
    const totalPages = Math.ceil(votes.length / VOTES_PER_PAGE);
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * VOTES_PER_PAGE;
    const pageVotes = votes.slice(start, start + VOTES_PER_PAGE);

    // Top pagination
    const topControls = _buildPaginationControls(votes.length, listEl);
    if (topControls) listEl.appendChild(topControls);

    // Render page of votes
    pageVotes.forEach(vote => {
        listEl.appendChild(_buildVoteItem(vote));
    });

    // Bottom pagination
    const bottomControls = _buildPaginationControls(votes.length, listEl);
    if (bottomControls) listEl.appendChild(bottomControls);
}

// --- Campaign Finance ---

function formatDollars(amount) {
    if (amount >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`;
    if (amount >= 1000) return `$${(amount / 1000).toFixed(0)}K`;
    return `$${amount.toLocaleString()}`;
}

async function loadDonations(bioguideId) {
    const section = document.getElementById('finance-section');
    const loading = document.getElementById('finance-loading');
    if (!section) return;

    try {
        const response = await fetch(`/api/members/${bioguideId}/donations`);
        if (!response.ok) throw new Error('No donation data');
        const data = await response.json();
        if (loading) loading.remove();

        const contributors = data.top_contributors || [];
        const industries = data.top_industries || [];

        if (contributors.length === 0 && industries.length === 0) {
            section.appendChild(el('div', { className: 'empty-state' }, 'No campaign finance data available.'));
            return;
        }

        const grid = el('div', { className: 'finance-grid' });

        // Top Contributors column
        if (contributors.length > 0) {
            const contribCol = el('div', { className: 'finance-column' });
            contribCol.appendChild(el('h4', { className: 'finance-heading' }, 'Top Contributors'));

            const maxTotal = Math.max(...contributors.map(c => c.total));
            contributors.slice(0, 10).forEach(c => {
                const row = el('div', { className: 'finance-row' });
                const info = el('div', { className: 'finance-info' });
                info.appendChild(el('span', { className: 'finance-name' }, c.org_name));
                info.appendChild(el('span', { className: 'finance-amount' }, formatDollars(c.total)));
                row.appendChild(info);

                const barTrack = el('div', { className: 'bar-track' });
                const pct = maxTotal > 0 ? (c.total / maxTotal) * 100 : 0;
                const barFill = el('div', { className: 'bar-fill' });
                barFill.style.width = `${pct}%`;

                // Split bar into PACs (darker) and individuals (lighter)
                if (c.total > 0) {
                    const pacPct = (c.pacs / c.total) * 100;
                    const indivPct = (c.individuals / c.total) * 100;
                    const pacSegment = el('div', { className: 'bar-segment bar-pacs' });
                    pacSegment.style.width = `${pacPct}%`;
                    const indivSegment = el('div', { className: 'bar-segment bar-indivs' });
                    indivSegment.style.width = `${indivPct}%`;
                    barFill.appendChild(pacSegment);
                    barFill.appendChild(indivSegment);
                }

                barTrack.appendChild(barFill);
                row.appendChild(barTrack);
                contribCol.appendChild(row);
            });

            grid.appendChild(contribCol);
        }

        // Top Industries column
        if (industries.length > 0) {
            const industryCol = el('div', { className: 'finance-column' });
            industryCol.appendChild(el('h4', { className: 'finance-heading' }, 'Top Industries'));

            const maxIndustry = Math.max(...industries.map(i => i.total));
            industries.slice(0, 10).forEach(i => {
                const row = el('div', { className: 'finance-row' });
                const info = el('div', { className: 'finance-info' });
                info.appendChild(el('span', { className: 'finance-name' }, i.industry_name));
                info.appendChild(el('span', { className: 'finance-amount' }, formatDollars(i.total)));
                row.appendChild(info);

                const barTrack = el('div', { className: 'bar-track' });
                const pct = maxIndustry > 0 ? (i.total / maxIndustry) * 100 : 0;
                const barFill = el('div', { className: 'bar-fill bar-fill-industry' });
                barFill.style.width = `${pct}%`;
                barTrack.appendChild(barFill);
                row.appendChild(barTrack);
                industryCol.appendChild(row);
            });

            grid.appendChild(industryCol);
        }

        section.appendChild(grid);

        // Bar legend
        const legend = el('div', { className: 'finance-legend' });
        legend.appendChild(el('span', { className: 'finance-legend-item' },
            el('span', { className: 'legend-dot legend-pacs' }), ' PACs'));
        legend.appendChild(el('span', { className: 'finance-legend-item' },
            el('span', { className: 'legend-dot legend-indivs' }), ' Individuals'));
        section.appendChild(legend);

        // Attribution
        section.appendChild(el('p', { className: 'ai-attribution' },
            `Data from the Federal Election Commission \u00b7 ${data.cycle || '2024'} election cycle`));
    } catch {
        if (loading) loading.remove();
        section.appendChild(el('div', { className: 'empty-state' },
            'Campaign finance data not yet available for this representative.'));
    }
}
