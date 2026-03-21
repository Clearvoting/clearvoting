/* ============================================
   ClearVoting — Bill Detail Page
   ============================================ */

let showParty = localStorage.getItem('cv-show-party') === 'true';

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

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const congress = params.get('congress');
    const type = params.get('type');
    const number = params.get('number');

    if (!congress || !type || !number) {
        showError('Missing bill information. Go back to the home page and select a bill.');
        return;
    }

    loadBill(congress, type, number);
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
    const container = document.getElementById('bill-content');
    clearEl(container);
    container.appendChild(el('div', { className: 'error-message' }, message));
}

// --- Load Bill ---
async function loadBill(congress, type, number) {
    const container = document.getElementById('bill-content');

    try {
        const response = await fetch(`/api/bills/${congress}/${type}/${number}`);
        if (!response.ok) throw new Error('Failed to load bill');
        const data = await response.json();

        const bill = data.bill || data;
        document.title = `${bill.title || 'Bill'} — ClearVoting`;
        renderBill(container, bill, congress, type, number);

        // Load AI summary asynchronously
        loadAISummary(congress, type, number);
    } catch (err) {
        showError('Unable to load bill data. Congress.gov may be temporarily unavailable.');
    }
}

function renderBill(container, bill, congress, type, number) {
    clearEl(container);

    const title = bill.title || 'Untitled Bill';
    const billNumber = `${(type || '').toUpperCase()}.${number}`;
    const latestAction = bill.latestAction || {};
    const statusText = latestAction.text || '';
    const statusDate = latestAction.actionDate || '';
    const originChamber = bill.originChamber || '';
    const subjects = bill.subjects?.legislativeSubjects || [];
    const policyArea = bill.policyArea?.name || '';

    // Bill Header
    const header = el('div', { className: 'bill-header' },
        el('span', { className: 'bill-number' }, `${billNumber} — ${congress}th Congress`),
        el('h2', null, title),
        el('div', { className: 'bill-status' },
            statusDate ? `Latest action (${statusDate}): ${statusText}` : statusText
        )
    );
    container.appendChild(header);

    // Copy Link button
    if (navigator.clipboard) {
        const copyBtn = el('button', { className: 'copy-link-btn', 'aria-label': 'Copy page link to clipboard' }, 'Copy Link');
        copyBtn.addEventListener('click', () => {
            navigator.clipboard.writeText(window.location.href).then(() => {
                copyBtn.textContent = 'Copied!';
                copyBtn.classList.add('copied');
                setTimeout(() => {
                    copyBtn.textContent = 'Copy Link';
                    copyBtn.classList.remove('copied');
                }, 2000);
            }).catch(() => {});
        });
        container.appendChild(copyBtn);
    }

    // Impact tags
    if (policyArea || subjects.length > 0) {
        const tagsDiv = el('div', { className: 'impact-tags' });
        if (policyArea) {
            tagsDiv.appendChild(el('span', { className: 'impact-tag' }, policyArea));
        }
        subjects.slice(0, 5).forEach(subj => {
            const name = subj.name || '';
            if (name) tagsDiv.appendChild(el('span', { className: 'impact-tag' }, name));
        });
        container.appendChild(tagsDiv);
    }

    // Mini table of contents
    const toc = el('nav', { className: 'bill-toc', 'aria-label': 'Jump to section' });
    toc.appendChild(el('a', { href: '#ai-summary-section' }, 'Summary'));
    toc.appendChild(el('a', { href: '#official-summary-section' }, 'Official Text'));
    if (bill.sponsors && bill.sponsors.length > 0) {
        toc.appendChild(el('a', { href: '#sponsors-section' }, 'Sponsors'));
    }
    toc.appendChild(el('a', { href: '#votes-section' }, 'Votes'));
    container.appendChild(toc);

    // AI Summary section (placeholder — loaded async)
    const aiSection = el('section', { className: 'bill-section', id: 'ai-summary-section' });
    aiSection.appendChild(el('h3', null, 'What This Bill Does'));
    aiSection.appendChild(el('div', { id: 'ai-summary-content', className: 'loading', 'aria-live': 'polite' },
        el('span', { className: 'spinner' }),
        ' Generating plain-language summary...'
    ));
    aiSection.appendChild(el('p', { className: 'ai-disclaimer' },
        'This summary was generated by AI to present bill provisions in plain language. See the official summary below for the authoritative version.'
    ));
    container.appendChild(aiSection);

    // Official Summary (collapsible if long — secondary visual weight)
    const officialSection = el('section', { className: 'bill-section bill-section-official', id: 'official-summary-section' });
    officialSection.appendChild(el('h3', null, 'Official Summary'));
    const summaries = bill.summaries || [];
    if (summaries.length > 0) {
        const latestSummary = summaries[0].text || 'No summary available.';
        const summaryDiv = el('div', { className: 'official-summary' });
        summaryDiv.textContent = '';
        // Content is sanitized — only safe tags (P, EM, STRONG, B, I, BR, UL, OL, LI, A) remain
        const sanitized = sanitizeHtml(latestSummary);
        summaryDiv.insertAdjacentHTML('afterbegin', sanitized);
        officialSection.appendChild(summaryDiv);

        // Measure at natural height (double-RAF ensures layout), then collapse if tall
        requestAnimationFrame(() => { requestAnimationFrame(() => {
            if (summaryDiv.scrollHeight > 150) {
                summaryDiv.classList.add('summary-collapsed');
                const expandBtn = el('button', { className: 'btn btn-secondary btn-small summary-expand-btn' }, 'Show full summary');
                expandBtn.addEventListener('click', () => {
                    const collapsed = summaryDiv.classList.toggle('summary-collapsed');
                    expandBtn.textContent = collapsed ? 'Show full summary' : 'Collapse summary';
                });
                officialSection.appendChild(expandBtn);
            }
        }); });
    } else {
        officialSection.appendChild(el('div', { className: 'empty-state' }, 'Official summary not yet available for this bill.'));
    }
    container.appendChild(officialSection);

    // Sponsors
    if (bill.sponsors && bill.sponsors.length > 0) {
        const sponsorSection = el('section', { className: 'bill-section', id: 'sponsors-section' });
        sponsorSection.appendChild(el('h3', null, 'Sponsors'));
        bill.sponsors.forEach(sponsor => {
            const name = sponsor.fullName || sponsor.firstName + ' ' + sponsor.lastName || '';
            const link = el('a', {
                href: `/member?id=${sponsor.bioguideId || ''}`,
            }, name);
            const div = el('div', null, link);
            sponsorSection.appendChild(div);
        });
        container.appendChild(sponsorSection);
    }

    // Votes section (placeholder — loaded async)
    const votesSection = el('section', { className: 'bill-section', id: 'votes-section' });
    votesSection.appendChild(el('h3', null, 'Roll Call Votes'));
    votesSection.appendChild(el('div', { id: 'votes-content', className: 'loading', 'aria-live': 'polite' },
        el('span', { className: 'spinner' }),
        ' Loading vote data...'
    ));
    container.appendChild(votesSection);

    loadBillVotes(congress, type, number);

    // Source link — prefer the canonical URL from Congress.gov API when available
    let congressGovUrl = bill.legislationUrl;
    if (!congressGovUrl) {
        const typeMap = { hr: 'house-bill', s: 'senate-bill', hjres: 'house-joint-resolution', sjres: 'senate-joint-resolution', hres: 'house-resolution', sres: 'senate-resolution', hconres: 'house-concurrent-resolution', sconres: 'senate-concurrent-resolution' };
        const typeForUrl = typeMap[(type || '').toLowerCase()] || (type || '').toLowerCase();
        congressGovUrl = `https://www.congress.gov/bill/${congress}th-congress/${typeForUrl}/${number}`;
    }
    container.appendChild(el('a', {
        href: congressGovUrl,
        target: '_blank',
        rel: 'noopener',
        className: 'source-link',
    }, 'View full bill on Congress.gov'));
}

// --- AI Summary ---
async function loadAISummary(congress, type, number) {
    const summaryContent = document.getElementById('ai-summary-content');
    if (!summaryContent) return;

    try {
        const response = await fetch(`/api/bills/${congress}/${type}/${number}/ai-summary`);
        if (!response.ok) throw new Error('AI summary failed');
        const data = await response.json();

        clearEl(summaryContent);
        summaryContent.className = '';

        // Provisions list
        const provisions = data.provisions || [];
        if (provisions.length > 0) {
            const list = el('ul', { className: 'provision-list' });
            provisions.forEach(p => list.appendChild(el('li', null, p)));
            summaryContent.appendChild(list);
        }

        // AI-generated issue categories
        const categories = data.issue_categories || [];
        if (categories.length > 0) {
            const tagsDiv = el('div', { className: 'impact-tags' });
            categories.forEach(cat => {
                tagsDiv.appendChild(el('span', { className: 'impact-tag' }, cat));
            });
            summaryContent.appendChild(el('h4', { className: 'issue-areas-heading' }, 'Issue Areas'));
            summaryContent.appendChild(tagsDiv);
        }

        // Both-sides arguments — side-by-side on desktop
        const args = data.arguments;
        if (args && (args.supporters?.length > 0 || args.critics?.length > 0)) {
            const argsSection = el('div', { className: 'bill-arguments' });
            argsSection.appendChild(el('h4', null, 'What People Are Saying'));

            const argsGrid = el('div', { className: 'bill-arguments-grid' });

            if (args.supporters && args.supporters.length > 0) {
                const supportSide = el('div', { className: 'arguments-side arguments-support' });
                supportSide.appendChild(el('div', { className: 'arguments-side-header' }, 'Supporters say'));
                const supportList = el('ul');
                args.supporters.forEach(s => supportList.appendChild(el('li', null, s)));
                supportSide.appendChild(supportList);
                argsGrid.appendChild(supportSide);
            }

            if (args.critics && args.critics.length > 0) {
                const criticsSide = el('div', { className: 'arguments-side arguments-critics' });
                criticsSide.appendChild(el('div', { className: 'arguments-side-header' }, 'Critics say'));
                const criticsList = el('ul');
                args.critics.forEach(c => criticsList.appendChild(el('li', null, c)));
                criticsSide.appendChild(criticsList);
                argsGrid.appendChild(criticsSide);
            }

            argsSection.appendChild(argsGrid);
            summaryContent.appendChild(argsSection);
        }
    } catch {
        clearEl(summaryContent);
        summaryContent.className = '';
        summaryContent.appendChild(el('div', { className: 'empty-state' },
            'Plain-language summary is not available for this bill. Some procedural votes and resolutions don\u2019t have enough detail for AI analysis. See the official summary below.'
        ));
    }
}

// --- Votes ---
async function loadBillVotes(congress, type, number) {
    const votesContent = document.getElementById('votes-content');
    if (!votesContent) return;

    try {
        const response = await fetch(`/api/bills/${congress}/${type}/${number}/votes`);
        if (!response.ok) throw new Error('Failed to load votes');
        const data = await response.json();

        const senateVotes = data.senate || [];
        const hasVotes = senateVotes.length > 0;

        if (!hasVotes) {
            clearEl(votesContent);
            votesContent.className = '';
            votesContent.appendChild(el('div', { className: 'empty-state' },
                'No roll call votes recorded for this bill yet.'
            ));
            return;
        }

        clearEl(votesContent);
        votesContent.className = '';

        for (const voteRef of senateVotes) {
            await loadSenateVote(votesContent, voteRef.congress, voteRef.session, voteRef.vote_number);
        }
    } catch {
        clearEl(votesContent);
        votesContent.className = '';
        votesContent.appendChild(el('div', { className: 'empty-state' },
            'Vote data is not available for this bill.'
        ));
    }
}

async function loadSenateVote(container, congress, session, voteNumber) {
    try {
        const url = `/api/votes/senate/${congress}/${session}/${voteNumber}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error('Vote not found');
        const data = await response.json();

        const voteBlock = el('div', { className: 'vote-block' });

        // Header
        voteBlock.appendChild(el('h4', null,
            `Senate Vote #${data.vote_number} — ${data.vote_date || ''}`
        ));
        voteBlock.appendChild(el('div', { className: 'vote-question' }, data.question || ''));
        voteBlock.appendChild(el('div', { className: 'vote-result' }, `Result: ${data.result || ''}`));

        if (data.note) {
            voteBlock.appendChild(el('div', { className: 'vote-note' }, data.note));
        }

        // Pie chart + legend
        const counts = data.counts || {};
        const chartRow = el('div', { className: 'vote-chart-row' });
        const pie = window.ClearVotingUI.renderVotePieChart(counts);
        if (pie) chartRow.appendChild(pie);
        chartRow.appendChild(window.ClearVotingUI.renderVoteSummary(counts));
        voteBlock.appendChild(chartRow);

        // Party breakdown container (shown on reveal)
        const partyBreakdown = el('div', { id: `party-breakdown-${voteNumber}`, className: 'party-breakdown' });
        voteBlock.appendChild(partyBreakdown);

        // Party toggle
        const toggleSection = el('div', { className: 'party-toggle-section', style: 'margin-top:1rem;' });
        toggleSection.appendChild(el('p', null, 'Viewing senators without party labels.'));
        const toggleBtn = el('button', { className: 'btn btn-secondary btn-small' }, 'Reveal Party Affiliations');
        toggleSection.appendChild(toggleBtn);
        voteBlock.appendChild(toggleSection);

        // Table (wrapped for mobile scroll — initially without party)
        const members = data.members || [];
        const tableContainer = el('div', { id: `vote-table-${voteNumber}`, className: 'vote-table-wrap' });
        tableContainer.appendChild(window.ClearVotingUI.renderVoteTable(members, false));
        voteBlock.appendChild(tableContainer);

        if (showParty) {
            toggleBtn.textContent = 'Hide Party Affiliations';
            // Auto-load party data from persisted state
            fetch(`${url}?show_party=true`).then(resp => resp.ok ? resp.json() : null).then(partyData => {
                if (partyData) {
                    const partyMembers = partyData.members || [];
                    clearEl(partyBreakdown);
                    const partyCharts = window.ClearVotingUI.renderPartyVotePieCharts(partyMembers);
                    if (partyCharts) partyBreakdown.appendChild(partyCharts);
                    clearEl(tableContainer);
                    tableContainer.appendChild(window.ClearVotingUI.renderVoteTable(partyMembers, true));
                }
            }).catch(() => {});
        }

        toggleBtn.addEventListener('click', async () => {
            showParty = !showParty;
            localStorage.setItem('cv-show-party', String(showParty));
            toggleBtn.textContent = showParty ? 'Hide Party Affiliations' : 'Reveal Party Affiliations';

            if (showParty) {
                const resp = await fetch(`${url}?show_party=true`);
                if (resp.ok) {
                    const partyData = await resp.json();
                    const partyMembers = partyData.members || [];

                    // Show party breakdown pie charts
                    clearEl(partyBreakdown);
                    const partyCharts = window.ClearVotingUI.renderPartyVotePieCharts(partyMembers);
                    if (partyCharts) partyBreakdown.appendChild(partyCharts);

                    // Update table with party column
                    clearEl(tableContainer);
                    tableContainer.appendChild(window.ClearVotingUI.renderVoteTable(partyMembers, true));
                }
            } else {
                clearEl(partyBreakdown);
                clearEl(tableContainer);
                tableContainer.appendChild(window.ClearVotingUI.renderVoteTable(members, false));
            }
        });

        container.appendChild(voteBlock);
    } catch { /* silently fail for individual vote */ }
}
