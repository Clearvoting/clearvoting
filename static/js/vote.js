/* ============================================
   ClearVote — Vote Detail (embedded in bill page)
   Reusable vote rendering functions
   ============================================ */

function renderVoteBar(counts) {
    const total = (counts.yeas || 0) + (counts.nays || 0) + (counts.present || 0) + (counts.absent || 0);
    if (total === 0) return null;

    const bar = document.createElement('div');
    bar.className = 'vote-bar';

    const segments = [
        { cls: 'yea', count: counts.yeas || 0 },
        { cls: 'nay', count: counts.nays || 0 },
        { cls: 'present', count: counts.present || 0 },
        { cls: 'absent', count: counts.absent || 0 },
    ];

    segments.forEach(seg => {
        if (seg.count > 0) {
            const segment = document.createElement('div');
            segment.className = `vote-bar-segment ${seg.cls}`;
            segment.style.width = `${(seg.count / total) * 100}%`;
            bar.appendChild(segment);
        }
    });

    return bar;
}

function renderVoteSummary(counts) {
    const summary = document.createElement('div');
    summary.className = 'vote-summary';

    const items = [
        { cls: 'yea', label: 'Yea', count: counts.yeas || 0 },
        { cls: 'nay', label: 'Nay', count: counts.nays || 0 },
        { cls: 'present', label: 'Present', count: counts.present || 0 },
        { cls: 'absent', label: 'Not Voting', count: counts.absent || 0 },
    ];

    items.forEach(item => {
        if (item.count > 0) {
            const dot = document.createElement('span');
            dot.className = `vote-dot ${item.cls}`;

            const countEl = document.createElement('div');
            countEl.className = 'vote-count';
            countEl.appendChild(dot);
            countEl.appendChild(document.createTextNode(` ${item.label}: ${item.count}`));
            summary.appendChild(countEl);
        }
    });

    return summary;
}

function renderVoteTable(members, showPartyColumn) {
    const table = document.createElement('table');
    table.className = 'data-table';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');

    const headers = ['Name', 'State'];
    if (showPartyColumn) headers.push('Party');
    headers.push('Vote');

    headers.forEach(h => {
        const th = document.createElement('th');
        th.textContent = h;
        if (h === 'Party') th.className = 'col-party';
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');

    // Sort: Yea first, then Nay, then Present, then Not Voting
    const voteOrder = { 'Yea': 0, 'Nay': 1, 'Present': 2, 'Not Voting': 3 };
    const sorted = [...members].sort((a, b) => {
        const aOrder = voteOrder[a.vote] ?? 4;
        const bOrder = voteOrder[b.vote] ?? 4;
        if (aOrder !== bOrder) return aOrder - bOrder;
        return (a.last_name || '').localeCompare(b.last_name || '');
    });

    sorted.forEach(member => {
        const row = document.createElement('tr');

        const nameCell = document.createElement('td');
        nameCell.textContent = `${member.first_name || ''} ${member.last_name || ''}`.trim();
        row.appendChild(nameCell);

        const stateCell = document.createElement('td');
        stateCell.textContent = member.state || '';
        row.appendChild(stateCell);

        if (showPartyColumn) {
            const partyCell = document.createElement('td');
            partyCell.className = 'col-party';
            partyCell.textContent = member.party || '';
            row.appendChild(partyCell);
        }

        const voteCell = document.createElement('td');
        const voteBadge = document.createElement('span');
        const vote = member.vote || 'Not Voting';
        voteBadge.className = `vote-label ${vote.toLowerCase().replace(/\s+/g, '-')}`;
        voteBadge.textContent = vote;
        voteCell.appendChild(voteBadge);
        row.appendChild(voteCell);

        tbody.appendChild(row);
    });

    table.appendChild(tbody);
    return table;
}

// Export for use in other scripts
window.ClearVoteUI = { renderVoteBar, renderVoteSummary, renderVoteTable };
