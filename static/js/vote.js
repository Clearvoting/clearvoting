/* ============================================
   ClearVoting — roll-call tables (bill page)
   Rows come from site.js rcTableRow (one vocabulary with the server, §10 #21);
   classes only: every colour lives in site.css (spec §6.1, §6.4).
   ============================================ */

const RC_PARTY_NAMES = { D: 'Democratic', R: 'Republican', I: 'Independent', ID: 'Independent' };

// Same key the server writes on each row (render._rc_row) and rcTableRow sets:
// House by bioguide id, Senate by state + last name.
function rcMemberKey(member, chamber) {
    return chamber === 'house'
        ? (member.bioguide_id || '')
        : `${member.state || ''}-${member.last_name || ''}`;
}

// render._rc_sorted_rows: 119th House by district (unknown last), else last name, first name.
function rcSortMembers(members, chamber, current) {
    const byName = (a, b) => (a.last_name || '').localeCompare(b.last_name || '')
        || (a.first_name || '').localeCompare(b.first_name || '');
    const rows = members.slice();
    if (current && chamber === 'house') {
        const rank = (m) => (Number.isInteger(m.district) ? m.district : Infinity);
        return rows.sort((a, b) => (rank(a) - rank(b)) || byName(a, b));
    }
    return rows.sort(byName);
}

// current: a 119th-Congress roll call inside one state's group (district print and order).
function buildRcTable(captionText, members, chamber, current) {
    const head = el('thead', null, el('tr', null,
        el('th', { scope: 'col' }, 'Member'), el('th', { scope: 'col' }, 'Vote')));
    const body = el('tbody', null, ...rcSortMembers(members, chamber, current)
        .map((member) => rcTableRow(member, { chamber, current })));
    return el('table', { className: 'rc' }, el('caption', null, captionText), head, body);
}

// Accent- and case-blind text for the name search (G1-022): 'velazquez' finds 'Nydia Velázquez'
// (the roll-call names are precomposed), and an accent the reader types still matches.
function rcFold(text) {
    return String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function filterRcRows(container, query, show) {
    const needle = rcFold((query || '').trim());
    container.querySelectorAll('tbody tr').forEach((row) => {
        const found = positionChip(row.dataset.position);
        const kindMatches = show === 'all' || (found ? found[0] : 'nv') === show;
        const cell = row.querySelector('th');
        const name = cell && cell.firstChild ? cell.firstChild.textContent : '';
        row.hidden = !(kindMatches && (!needle || rcFold(name).includes(needle)));
    });
}

function fillPartySpans(container, members, chamber) {
    const partyByKey = new Map(members.map((m) => [rcMemberKey(m, chamber), m.party]));
    container.querySelectorAll('tbody tr[data-key]').forEach((row) => {
        const span = row.querySelector('.party');
        if (!span) return;
        const code = partyByKey.get(row.dataset.key);
        span.textContent = code ? ` · ${RC_PARTY_NAMES[code] || code}` : '';
    });
}

function clearPartySpans(container) {
    container.querySelectorAll('.party').forEach((span) => { span.textContent = ''; });
}
