/* ============================================
   ClearVote — Vote Detail (embedded in bill page)
   Reusable vote rendering functions
   ============================================ */

const VOTE_COLORS = {
    yea: '#4CAF6A',
    nay: '#D64550',
    present: '#5B8FB8',
    absent: '#6B7B8B',
};

// --- SVG Pie Chart ---

function renderVotePieChart(counts, size) {
    const total = (counts.yeas || 0) + (counts.nays || 0) + (counts.present || 0) + (counts.absent || 0);
    if (total === 0) return null;

    const segments = [
        { label: 'Yea', count: counts.yeas || 0, color: VOTE_COLORS.yea },
        { label: 'Nay', count: counts.nays || 0, color: VOTE_COLORS.nay },
        { label: 'Present', count: counts.present || 0, color: VOTE_COLORS.present },
        { label: 'Not Voting', count: counts.absent || 0, color: VOTE_COLORS.absent },
    ].filter(s => s.count > 0);

    return _buildPieChart(segments, total, size || 160);
}

function renderPartyVotePieCharts(members) {
    if (!members || members.length === 0) return null;

    const parties = {};
    members.forEach(m => {
        const p = m.party || '?';
        if (!parties[p]) parties[p] = { yea: 0, nay: 0, present: 0, absent: 0, total: 0 };
        const vote = (m.vote || '').toLowerCase();
        if (vote === 'yea') parties[p].yea++;
        else if (vote === 'nay') parties[p].nay++;
        else if (vote === 'present') parties[p].present++;
        else parties[p].absent++;
        parties[p].total++;
    });

    const PARTY_NAMES = { R: 'Republican', D: 'Democrat', I: 'Independent' };
    const container = document.createElement('div');
    container.className = 'party-pie-charts';

    Object.keys(parties).sort().forEach(partyCode => {
        const data = parties[partyCode];
        const name = PARTY_NAMES[partyCode] || partyCode;

        const segments = [
            { label: 'Yea', count: data.yea, color: VOTE_COLORS.yea },
            { label: 'Nay', count: data.nay, color: VOTE_COLORS.nay },
            { label: 'Present', count: data.present, color: VOTE_COLORS.present },
            { label: 'Not Voting', count: data.absent, color: VOTE_COLORS.absent },
        ].filter(s => s.count > 0);

        const wrapper = document.createElement('div');
        wrapper.className = 'party-pie-wrapper';

        const heading = document.createElement('h5');
        heading.textContent = `${name} (${data.total})`;
        wrapper.appendChild(heading);

        wrapper.appendChild(_buildPieChart(segments, data.total, 120));

        const legend = document.createElement('div');
        legend.className = 'pie-legend';
        segments.forEach(s => {
            const item = document.createElement('span');
            item.className = 'pie-legend-item';
            const dot = document.createElement('span');
            dot.className = 'pie-legend-dot';
            dot.style.background = s.color;
            item.appendChild(dot);
            item.appendChild(document.createTextNode(` ${s.label}: ${s.count}`));
            legend.appendChild(item);
        });
        wrapper.appendChild(legend);

        container.appendChild(wrapper);
    });

    return container;
}

function _buildPieChart(segments, total, size) {
    const svgNS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('viewBox', `0 0 ${size} ${size}`);
    svg.setAttribute('width', String(size));
    svg.setAttribute('height', String(size));
    svg.setAttribute('class', 'vote-pie');
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Vote breakdown: ' + segments.map(s => s.label + ' ' + s.count).join(', '));

    const cx = size / 2;
    const cy = size / 2;
    const outerR = (size / 2) - 2;
    const strokeW = outerR * 0.55;
    const r = outerR - (strokeW / 2);
    const circumference = 2 * Math.PI * r;

    let offset = 0;
    segments.forEach(function(seg) {
        var pct = seg.count / total;
        var dashLen = pct * circumference;

        var circle = document.createElementNS(svgNS, 'circle');
        circle.setAttribute('cx', String(cx));
        circle.setAttribute('cy', String(cy));
        circle.setAttribute('r', String(r));
        circle.setAttribute('fill', 'none');
        circle.setAttribute('stroke', seg.color);
        circle.setAttribute('stroke-width', String(strokeW));
        circle.setAttribute('stroke-dasharray', dashLen + ' ' + (circumference - dashLen));
        circle.setAttribute('stroke-dashoffset', String(-offset));
        circle.setAttribute('transform', 'rotate(-90 ' + cx + ' ' + cy + ')');
        svg.appendChild(circle);

        offset += dashLen;
    });

    // Center text
    var text = document.createElementNS(svgNS, 'text');
    text.setAttribute('x', String(cx));
    text.setAttribute('y', String(cy));
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('dominant-baseline', 'central');
    text.setAttribute('fill', '#F0F4F8');
    text.setAttribute('font-size', String(Math.round(size * 0.18)));
    text.setAttribute('font-weight', '600');
    text.setAttribute('font-family', 'Inter, system-ui, sans-serif');
    text.textContent = String(total);
    svg.appendChild(text);

    return svg;
}

// --- Vote Bar ---

function renderVoteBar(counts) {
    var total = (counts.yeas || 0) + (counts.nays || 0) + (counts.present || 0) + (counts.absent || 0);
    if (total === 0) return null;

    var bar = document.createElement('div');
    bar.className = 'vote-bar';

    var segments = [
        { cls: 'yea', count: counts.yeas || 0 },
        { cls: 'nay', count: counts.nays || 0 },
        { cls: 'present', count: counts.present || 0 },
        { cls: 'absent', count: counts.absent || 0 },
    ];

    segments.forEach(function(seg) {
        if (seg.count > 0) {
            var segment = document.createElement('div');
            segment.className = 'vote-bar-segment ' + seg.cls;
            segment.style.width = ((seg.count / total) * 100) + '%';
            bar.appendChild(segment);
        }
    });

    return bar;
}

// --- Vote Summary Legend ---

function renderVoteSummary(counts) {
    var summary = document.createElement('div');
    summary.className = 'vote-summary';

    var items = [
        { cls: 'yea', label: 'Yea', count: counts.yeas || 0 },
        { cls: 'nay', label: 'Nay', count: counts.nays || 0 },
        { cls: 'present', label: 'Present', count: counts.present || 0 },
        { cls: 'absent', label: 'Not Voting', count: counts.absent || 0 },
    ];

    items.forEach(function(item) {
        if (item.count > 0) {
            var dot = document.createElement('span');
            dot.className = 'vote-dot ' + item.cls;

            var countEl = document.createElement('div');
            countEl.className = 'vote-count';
            countEl.appendChild(dot);
            countEl.appendChild(document.createTextNode(' ' + item.label + ': ' + item.count));
            summary.appendChild(countEl);
        }
    });

    return summary;
}

// --- Vote Table ---

function renderVoteTable(members, showPartyColumn) {
    var table = document.createElement('table');
    table.className = 'data-table';

    var thead = document.createElement('thead');
    var headerRow = document.createElement('tr');

    var headers = ['Name', 'State'];
    if (showPartyColumn) headers.push('Party');
    headers.push('Vote');

    headers.forEach(function(h) {
        var th = document.createElement('th');
        th.textContent = h;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    var tbody = document.createElement('tbody');

    var voteOrder = { 'Yea': 0, 'Nay': 1, 'Present': 2, 'Not Voting': 3 };
    var sorted = members.slice().sort(function(a, b) {
        var aOrder = voteOrder[a.vote] !== undefined ? voteOrder[a.vote] : 4;
        var bOrder = voteOrder[b.vote] !== undefined ? voteOrder[b.vote] : 4;
        if (aOrder !== bOrder) return aOrder - bOrder;
        return (a.last_name || '').localeCompare(b.last_name || '');
    });

    sorted.forEach(function(member) {
        var row = document.createElement('tr');

        var nameCell = document.createElement('td');
        nameCell.textContent = ((member.first_name || '') + ' ' + (member.last_name || '')).trim();
        row.appendChild(nameCell);

        var stateCell = document.createElement('td');
        stateCell.textContent = member.state || '';
        row.appendChild(stateCell);

        if (showPartyColumn) {
            var partyCell = document.createElement('td');
            partyCell.textContent = member.party || '';
            row.appendChild(partyCell);
        }

        var voteCell = document.createElement('td');
        var voteBadge = document.createElement('span');
        var vote = member.vote || 'Not Voting';
        voteBadge.className = 'vote-label ' + vote.toLowerCase().replace(/\s+/g, '-');
        voteBadge.textContent = vote;
        voteCell.appendChild(voteBadge);
        row.appendChild(voteCell);

        tbody.appendChild(row);
    });

    table.appendChild(tbody);
    return table;
}

// Export for use in other scripts
window.ClearVoteUI = {
    renderVoteBar: renderVoteBar,
    renderVoteSummary: renderVoteSummary,
    renderVoteTable: renderVoteTable,
    renderVotePieChart: renderVotePieChart,
    renderPartyVotePieCharts: renderPartyVotePieCharts,
};
