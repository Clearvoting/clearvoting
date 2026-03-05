/* ============================================
   ClearVote — Member Profile Page
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
    setupHamburger();
});

function setupHamburger() {
    const hamburger = document.querySelector('.hamburger');
    hamburger.addEventListener('click', () => {
        const nav = document.querySelector('nav');
        nav.classList.toggle('open');
        hamburger.setAttribute('aria-expanded', nav.classList.contains('open'));
    });
}

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
        document.title = `${memberData.directOrderName || memberData.firstName || 'Representative'} — ClearVote`;
        renderMember(container, memberData, bioguideId);
    } catch (err) {
        showError('Unable to load representative data. Congress.gov may be temporarily unavailable.');
    }
}

function renderMember(container, member, bioguideId) {
    clearEl(container);

    const name = member.directOrderName || `${member.firstName || ''} ${member.lastName || ''}`.trim();
    const depiction = member.depiction;
    const imageUrl = depiction ? depiction.imageUrl : '';
    const stateText = member.state || '';
    const terms = member.terms || { item: [] };
    const termItems = Array.isArray(terms.item) ? terms.item : [terms.item].filter(Boolean);
    const latestTerm = termItems[termItems.length - 1];
    const chamber = latestTerm ? latestTerm.chamber || '' : '';
    const district = member.district ? `District ${member.district}` : '';

    // Header
    const photoEl = imageUrl
        ? el('img', { className: 'member-photo', src: imageUrl, alt: `Photo of ${name}`, loading: 'lazy' })
        : el('div', { className: 'member-photo-placeholder', 'aria-hidden': 'true' }, '?');

    const metaText = [chamber, stateText, district].filter(Boolean).join(' — ');

    const headerInfo = el('div', null,
        el('h2', null, name),
        el('div', { className: 'member-meta' }, metaText),
        el('div', { className: 'member-meta', id: 'party-display' })
    );

    const header = el('div', { className: 'member-header' }, photoEl, headerInfo);
    container.appendChild(header);

    // Party toggle
    const toggleSection = el('div', { className: 'party-toggle-section' });
    const toggleMsg = el('p', null, "You're viewing this representative without party labels. Want to see party affiliation?");
    const toggleBtn = el('button', { className: 'btn btn-secondary btn-small', id: 'party-toggle-btn' }, 'Reveal Party Affiliation');

    toggleBtn.addEventListener('click', async () => {
        showParty = !showParty;
        toggleBtn.textContent = showParty ? 'Hide Party Affiliation' : 'Reveal Party Affiliation';
        toggleMsg.textContent = showParty
            ? 'Party affiliation is now visible.'
            : "You're viewing this representative without party labels. Want to see party affiliation?";

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

    toggleSection.appendChild(toggleMsg);
    toggleSection.appendChild(toggleBtn);
    container.appendChild(toggleSection);

    // Service info
    if (termItems.length > 0) {
        const serviceSection = el('section', { className: 'bill-section' });
        serviceSection.appendChild(el('h3', null, 'Service History'));

        const table = el('table', { className: 'data-table' });
        const thead = el('thead', null,
            el('tr', null,
                el('th', null, 'Congress'),
                el('th', null, 'Chamber'),
                el('th', null, 'Years')
            )
        );
        table.appendChild(thead);

        const tbody = el('tbody');
        termItems.forEach(term => {
            const row = el('tr', null,
                el('td', null, String(term.congress || '')),
                el('td', null, term.chamber || ''),
                el('td', null, `${term.startYear || ''}–${term.endYear || 'present'}`)
            );
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        serviceSection.appendChild(table);
        container.appendChild(serviceSection);
    }

    // Sponsored legislation
    const sponsoredSection = el('section', { className: 'bill-section' });
    sponsoredSection.appendChild(el('h3', null, 'Sponsored Legislation'));
    const sponsoredList = el('div', { className: 'bill-list', id: 'sponsored-bills' });
    sponsoredList.appendChild(el('div', { className: 'loading' },
        el('span', { className: 'spinner' }),
        ' Loading sponsored legislation...'
    ));
    sponsoredSection.appendChild(sponsoredList);
    container.appendChild(sponsoredSection);

    loadSponsoredLegislation(bioguideId);

    // Voting record (loaded async)
    const votingSection = el('div', { id: 'voting-record' });
    votingSection.appendChild(el('div', { className: 'loading' },
        el('span', { className: 'spinner' }),
        ' Loading voting record...'
    ));
    container.appendChild(votingSection);

    loadVotingRecord(bioguideId);

    // Source link
    const sourceLink = el('a', {
        href: `https://www.congress.gov/member/${bioguideId}`,
        target: '_blank',
        rel: 'noopener',
        className: 'source-link',
    }, 'View full profile on Congress.gov');
    container.appendChild(sourceLink);
}

async function loadSponsoredLegislation(bioguideId) {
    const listEl = document.getElementById('sponsored-bills');

    try {
        const response = await fetch(`/api/members/detail/${bioguideId}`);
        if (!response.ok) throw new Error('Failed');
        const data = await response.json();
        const member = data.member || data;

        const sponsoredUrl = member.sponsoredLegislation?.url;
        if (!sponsoredUrl) {
            clearEl(listEl);
            listEl.appendChild(el('div', { className: 'empty-state' }, 'No sponsored legislation data available.'));
            return;
        }

        // The URL from Congress API points to the API itself — we'd need to fetch through our backend
        // For now, show the count and link to Congress.gov
        clearEl(listEl);
        const count = member.sponsoredLegislation?.count || 0;
        listEl.appendChild(el('div', { className: 'empty-state' },
            `${count} bills sponsored. `,
            el('a', {
                href: `https://www.congress.gov/member/${bioguideId}?q=%7B%22sponsorship%22%3A%22sponsored%22%7D`,
                target: '_blank',
                rel: 'noopener',
            }, 'View on Congress.gov')
        ));
    } catch {
        clearEl(listEl);
        listEl.appendChild(el('div', { className: 'empty-state' }, 'Unable to load sponsored legislation.'));
    }
}

// --- Voting Record ---

let allVotes = [];

async function loadVotingRecord(bioguideId) {
    const container = document.getElementById('voting-record');
    if (!container) return;

    try {
        const response = await fetch(`/api/members/${bioguideId}/votes`);
        if (!response.ok) throw new Error('Failed to load votes');
        const data = await response.json();

        clearEl(container);
        renderVotingStats(container, data.stats);
        renderVoteFilters(container, data.policy_areas, data.votes);
        renderVoteList(container, data.votes);
    } catch (err) {
        clearEl(container);
        container.appendChild(el('div', { className: 'empty-state' }, 'Voting record unavailable.'));
    }
}

function renderVotingStats(container, stats) {
    const section = el('section', { className: 'bill-section' });
    section.appendChild(el('h3', null, 'Voting Statistics'));

    const statsGrid = el('div', { className: 'stats-grid' });

    // Participation donut
    const participationWrapper = el('div', { className: 'stat-card' });
    participationWrapper.appendChild(el('div', { className: 'stat-label' }, 'Participation'));
    const participationChart = window.ClearVoteUI.renderVotePieChart({
        yeas: Math.round(stats.participation_rate),
        nays: Math.round(100 - stats.participation_rate),
    }, 100);
    if (participationChart) participationWrapper.appendChild(participationChart);
    participationWrapper.appendChild(el('div', { className: 'stat-value' }, `${stats.participation_rate}%`));
    statsGrid.appendChild(participationWrapper);

    // Yea/Nay donut
    const voteWrapper = el('div', { className: 'stat-card' });
    voteWrapper.appendChild(el('div', { className: 'stat-label' }, 'Vote Breakdown'));
    const voteChart = window.ClearVoteUI.renderVotePieChart({
        yeas: stats.yea_count,
        nays: stats.nay_count,
        absent: stats.not_voting_count,
    }, 100);
    if (voteChart) voteWrapper.appendChild(voteChart);
    const legend = el('div', { className: 'stat-legend' },
        el('span', null, `Yea: ${stats.yea_count}`),
        el('span', null, ` · Nay: ${stats.nay_count}`),
        el('span', null, ` · Missed: ${stats.not_voting_count}`)
    );
    voteWrapper.appendChild(legend);
    statsGrid.appendChild(voteWrapper);

    // Total votes
    const totalWrapper = el('div', { className: 'stat-card' });
    totalWrapper.appendChild(el('div', { className: 'stat-label' }, 'Total Votes'));
    totalWrapper.appendChild(el('div', { className: 'stat-big-number' }, String(stats.total_votes)));
    totalWrapper.appendChild(el('div', { className: 'stat-sublabel' }, '119th Congress'));
    statsGrid.appendChild(totalWrapper);

    section.appendChild(statsGrid);
    container.appendChild(section);
}

function renderVoteFilters(container, policyAreas, votes) {
    allVotes = votes;
    const section = el('section', { className: 'bill-section' });
    section.appendChild(el('h3', null, 'Voting Record'));

    const filterRow = el('div', { className: 'issue-filters' });

    const allChip = el('button', { className: 'category-tag active', 'data-area': 'all' }, 'All');
    allChip.addEventListener('click', () => filterVotes('all'));
    filterRow.appendChild(allChip);

    policyAreas.forEach(area => {
        const chip = el('button', { className: 'category-tag', 'data-area': area }, area);
        chip.addEventListener('click', () => filterVotes(area));
        filterRow.appendChild(chip);
    });

    section.appendChild(filterRow);
    container.appendChild(section);
}

function filterVotes(area) {
    document.querySelectorAll('.issue-filters .category-tag').forEach(c => c.classList.remove('active'));
    const active = document.querySelector(`.issue-filters .category-tag[data-area="${CSS.escape(area)}"]`);
    if (active) active.classList.add('active');

    const filtered = area === 'all' ? allVotes : allVotes.filter(v => v.policy_area === area);
    const listEl = document.getElementById('vote-list');
    if (listEl) {
        clearEl(listEl);
        _renderVoteItems(listEl, filtered);
    }
}

function renderVoteList(container, votes) {
    const listEl = el('div', { id: 'vote-list', className: 'bill-list' });
    _renderVoteItems(listEl, votes);
    container.appendChild(listEl);
}

function _renderVoteItems(listEl, votes) {
    if (votes.length === 0) {
        listEl.appendChild(el('div', { className: 'empty-state' }, 'No votes found for this category.'));
        return;
    }

    votes.forEach(vote => {
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
        item.appendChild(bottomRow);

        // Link to bill detail if it's a standard bill type
        if (vote.bill_type === 'HR' || vote.bill_type === 'S') {
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
        }

        listEl.appendChild(item);
    });
}
