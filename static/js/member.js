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

    // Sponsored legislation (compact)
    const sponsoredSection = el('section', { className: 'service-compact', id: 'sponsored-section' });
    const sponsoredHeader = el('div', { className: 'service-compact-header' });
    sponsoredHeader.appendChild(el('h3', null, 'Sponsored Legislation'));
    sponsoredHeader.appendChild(el('span', { className: 'service-compact-summary', id: 'sponsored-count' }, 'Loading...'));
    sponsoredSection.appendChild(sponsoredHeader);
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
    const countEl = document.getElementById('sponsored-count');
    const section = document.getElementById('sponsored-section');
    if (!countEl || !section) return;

    try {
        const response = await fetch(`/api/members/detail/${bioguideId}`);
        if (!response.ok) throw new Error('Failed');
        const data = await response.json();
        const member = data.member || data;

        const count = member.sponsoredLegislation?.count || 0;
        const cosponsored = member.cosponsoredLegislation?.count || 0;
        countEl.textContent = `${count} bills sponsored · ${cosponsored} cosponsored`;

        const rawName = member.directOrderName || `${member.firstName || ''} ${member.lastName || ''}`.trim() || '';
        const slug = rawName.toLowerCase().replace(/[^a-z\s-]/g, '').trim().replace(/\s+/g, '-');
        const detailsLink = el('a', {
            href: `https://www.congress.gov/member/${slug}/${bioguideId}?q=%7B%22sponsorship%22%3A%22sponsored%22%7D`,
            target: '_blank',
            rel: 'noopener',
            className: 'service-expand-btn',
        }, 'Details →');
        section.querySelector('.service-compact-header').appendChild(detailsLink);
    } catch {
        countEl.textContent = 'Unavailable';
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

async function loadVotingRecord(bioguideId) {
    const container = document.getElementById('voting-record');
    if (!container) return;

    try {
        const [votesResponse, summaryResponse] = await Promise.all([
            fetch(`/api/members/${bioguideId}/votes`),
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
        if (data.scorecard && data.scorecard.length > 0) {
            renderScorecard(container, data.scorecard);
        }
        renderVotingStats(container, data.stats);
        renderVoteFilters(container, data.policy_areas, data.votes);
        renderVoteList(container, data.votes);
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

    // Count votes by area with direction-aware stance
    const areaVotes = {};
    votes.forEach(v => {
        if (!v.policy_area) return;
        if (!areaVotes[v.policy_area]) areaVotes[v.policy_area] = { yea: 0, nay: 0, total: 0, strengthen: 0, weaken: 0, neutral: 0 };
        areaVotes[v.policy_area].total++;
        const isYea = v.vote === 'Yea' || v.vote === 'Aye';
        const isNay = v.vote === 'Nay' || v.vote === 'No';
        if (isYea) areaVotes[v.policy_area].yea++;
        else if (isNay) areaVotes[v.policy_area].nay++;

        if (v.direction === 'strengthens') {
            if (isYea) areaVotes[v.policy_area].strengthen++;
            else if (isNay) areaVotes[v.policy_area].weaken++;
        } else if (v.direction === 'weakens') {
            if (isYea) areaVotes[v.policy_area].weaken++;
            else if (isNay) areaVotes[v.policy_area].strengthen++;
        } else {
            if (isYea || isNay) areaVotes[v.policy_area].neutral++;
        }
    });

    // Top areas by total votes — exclude votes with no policy area
    const sortedAreas = Object.entries(areaVotes)
        .filter(([area]) => area && area !== 'undefined' && area !== 'null')
        .sort((a, b) => b[1].total - a[1].total);
    const topAreas = sortedAreas.slice(0, 5);

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
    }

    // Overview — plain language
    const overview = el('p', { className: 'summary-overview' },
        `Supports ${yeaPct}% of bills that come to a vote. Shows up for ${stats.participation_rate}% of all votes.`
    );
    card.appendChild(overview);

    // Top issues with mini bars
    const issuesSection = el('div', { className: 'summary-issues' });
    issuesSection.appendChild(el('h4', null, 'Where They Focus'));
    topAreas.forEach(([area, data]) => {
        const row = el('div', { className: 'summary-issue-row' });
        row.appendChild(el('span', { className: 'summary-issue-name' }, area));

        const hasDirection = (data.strengthen + data.weaken) > 0;

        if (hasDirection) {
            // Direction-aware: show strengthening/weakening counts
            const parts = [];
            if (data.strengthen > 0) parts.push(`${data.strengthen} strengthening`);
            if (data.weaken > 0) parts.push(`${data.weaken} weakening`);
            if (data.neutral > 0) parts.push(`${data.neutral} neutral`);
            const label = parts.join(' · ') || `${data.total} votes`;
            row.appendChild(el('span', { className: 'summary-issue-count' }, label));

            // Blue (strengthen) / orange (weaken) bar
            const stanceTotal = data.strengthen + data.weaken + data.neutral;
            const strengthenPct = stanceTotal > 0 ? Math.round((data.strengthen / stanceTotal) * 100) : 0;
            const bar = el('div', { className: 'summary-mini-bar' });
            bar.style.background = 'var(--vote-weaken)';
            const strengthenSeg = el('div', { className: 'summary-mini-bar-strengthen' });
            strengthenSeg.style.width = strengthenPct + '%';
            bar.appendChild(strengthenSeg);
            row.appendChild(bar);
        } else {
            // Fallback: yea/nay when no direction data
            const yeaPctArea = data.total > 0 ? Math.round((data.yea / data.total) * 100) : 0;
            const label = data.nay > 0 ? `${data.yea} for · ${data.nay} against` : `${data.yea} for`;
            row.appendChild(el('span', { className: 'summary-issue-count' }, label));

            const bar = el('div', { className: 'summary-mini-bar' });
            const yeaSeg = el('div', { className: 'summary-mini-bar-yea' });
            yeaSeg.style.width = yeaPctArea + '%';
            bar.appendChild(yeaSeg);
            row.appendChild(bar);
        }

        issuesSection.appendChild(row);
    });
    card.appendChild(issuesSection);

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

function renderScorecard(container, scorecard) {
    const section = el('section', { className: 'scorecard-section' });
    section.appendChild(el('h3', null, 'Issues You Care About'));
    section.appendChild(el('p', { className: 'scorecard-subtitle' },
        'How they voted on the issues most Americans agree on — based on Pew Research and Gallup polling.'));

    const grid = el('div', { className: 'scorecard-grid' });

    scorecard.forEach(issue => {
        const card = el('div', { className: 'scorecard-card' });

        const header = el('div', { className: 'scorecard-card-header' });
        header.appendChild(el('h4', null, issue.issue));
        header.appendChild(el('span', { className: 'scorecard-card-subtitle' }, issue.subtitle));
        card.appendChild(header);

        if (issue.votes.length === 0) {
            card.appendChild(el('p', { className: 'scorecard-empty' }, 'No tracked votes on this issue yet.'));
        } else if (issue.issue === 'National Debt') {
            // Special rendering for national debt — show net + itemized
            const deficitVotes = issue.votes.filter(v => v.deficit);
            if (deficitVotes.length > 0) {
                const netBillions = deficitVotes.reduce((sum, v) => {
                    const match = v.deficit.match(/([+-])\$?([\d.]+)\s*(trillion|billion)/i);
                    if (!match) return sum;
                    const sign = match[1] === '+' ? 1 : -1;
                    const num = parseFloat(match[2]);
                    const multiplier = match[3].toLowerCase() === 'trillion' ? 1000 : 1;
                    return sum + sign * num * multiplier;
                }, 0);

                const netFormatted = formatDeficitAmount(netBillions);
                const direction = netBillions > 0 ? 'added to' : 'reduced';
                const netClass = netBillions > 0 ? 'deficit-increase' : 'deficit-decrease';

                card.appendChild(el('div', { className: `scorecard-net ${netClass}` },
                    `Net: ${netFormatted} ${direction} the deficit`));
            }

            const list = el('ul', { className: 'scorecard-vote-list' });
            issue.votes.forEach(v => {
                const li = el('li', { className: 'scorecard-vote-item' });
                const badge = el('span', { className: 'scorecard-vote-badge vote-' + v.vote.toLowerCase() }, v.vote);
                li.appendChild(badge);
                const text = el('span', { className: 'scorecard-vote-text' });
                text.appendChild(document.createTextNode(v.summary));
                if (v.deficit && v.deficit !== '$0') {
                    const deficitClass = v.deficit.startsWith('+') ? 'deficit-increase' : 'deficit-decrease';
                    text.appendChild(el('span', { className: `scorecard-deficit-tag ${deficitClass}` }, ` ${v.deficit}`));
                }
                li.appendChild(text);
                list.appendChild(li);
            });
            card.appendChild(list);
        } else {
            // Standard rendering — show vote list
            const list = el('ul', { className: 'scorecard-vote-list' });
            issue.votes.forEach(v => {
                const li = el('li', { className: 'scorecard-vote-item' });
                const badge = el('span', { className: 'scorecard-vote-badge vote-' + v.vote.toLowerCase() }, v.vote);
                li.appendChild(badge);
                li.appendChild(el('span', { className: 'scorecard-vote-text' }, v.summary));
                list.appendChild(li);
            });
            card.appendChild(list);
        }

        grid.appendChild(card);
    });

    section.appendChild(grid);
    container.appendChild(section);
}

function renderVotingStats(container, stats) {
    const section = el('section', { className: 'bill-section' });
    section.appendChild(el('h3', null, 'Voting Statistics'));

    const statsGrid = el('div', { className: 'stats-grid' });

    // Participation donut
    const participationWrapper = el('div', { className: 'stat-card' });
    participationWrapper.appendChild(el('div', { className: 'stat-label' }, 'Participation'));
    const participationChart = window.ClearVotingUI.renderVotePieChart({
        yeas: Math.round(stats.participation_rate),
        nays: Math.round(100 - stats.participation_rate),
    }, 100);
    if (participationChart) participationWrapper.appendChild(participationChart);
    participationWrapper.appendChild(el('div', { className: 'stat-value' }, `${stats.participation_rate}%`));
    statsGrid.appendChild(participationWrapper);

    // Yea/Nay donut
    const voteWrapper = el('div', { className: 'stat-card' });
    voteWrapper.appendChild(el('div', { className: 'stat-label' }, 'Vote Breakdown'));
    const voteChart = window.ClearVotingUI.renderVotePieChart({
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

        if (vote.cbo_deficit_impact) {
            const deficitClass = vote.cbo_deficit_billions > 0 ? 'deficit-increase' : 'deficit-decrease';
            const cboTag = el('span', { className: `cbo-tag ${deficitClass}` }, `CBO: ${vote.cbo_deficit_impact}`);
            bottomRow.appendChild(cboTag);
        }

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
