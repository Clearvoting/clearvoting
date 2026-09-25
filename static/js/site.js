/* ============================================
   ClearVoting — site.js, the shared client (plan T2.2–T2.3; spec §7, §10 #21)
   A classic script loaded before each page's own enhancer. Its top-level
   functions are the API those enhancers call. DOM is built with el() and
   textContent only (never from HTML strings); JS applies classes, never colours.
   The formatters are twins of app/render.py; tests/test_formatter_parity.py
   keeps the two in step (tables structurally, outputs through node).
   ============================================ */
'use strict';

/* ---- One string map for the UI copy site.js writes (spec §7.6, §12.1) ---- */
const STRINGS = {
    showParty: 'Show party labels',
    hideParty: 'Hide party labels',
    partyShown: 'Party labels shown',
    partyHidden: 'Party labels hidden',
    linkCopied: 'Link copied',
    remembered: 'Remembered: {place}',
    change: 'Change',
    forget: 'Forget',
    rememberDistrict: 'Remember District {district} as mine',
    notifyThanks: "Thanks — we'll email you when {state} is added.",
    notifyFailed: "We couldn't save that. Please try again in a few minutes.",
    invalidEmail: "That doesn't look like an email address.",
    pageError: "We couldn't load this page right now. Please try again in a moment, or use Report an error below to tell us.",
    noSummary: 'No plain-English summary yet',
    noFinalVotes: 'No final votes on bills in our record yet',
    latestFinalVote: 'Latest final vote',
    notInChamber: 'Not in the {chamber} for this vote',
};

function t(key, values) {
    return String(STRINGS[key] || '').replace(/\{(\w+)\}/g, (match, name) =>
        (values && values[name] !== undefined ? String(values[name]) : match));
}

/* ---- DOM helpers ---- */
// el('a', {className: 'vote-row', href: '/bill?…'}, child, 'text', …): className sets the
// class; every other key goes through setAttribute; strings become text nodes;
// null/undefined/false children are skipped.
function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
        Object.keys(attrs).forEach((key) => {
            const value = attrs[key];
            if (value === null || value === undefined || value === false) return;
            if (key === 'className') node.className = value;
            else node.setAttribute(key, value === true ? '' : String(value));
        });
    }
    children.forEach((child) => {
        if (child === null || child === undefined || child === false) return;
        node.appendChild(typeof child === 'string' || typeof child === 'number'
            ? document.createTextNode(String(child)) : child);
    });
    return node;
}

function clear(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
    return node;
}

/* ---- Bill codes, ordinals, names, dates (spec §7.5, §7.3) ---- */
/* bill-type-labels:start */
const BILL_TYPE_LABELS = {"hr": "H.R.", "s": "S.", "hjres": "H.J.Res.", "sjres": "S.J.Res.", "hconres": "H.Con.Res.", "sconres": "S.Con.Res.", "hres": "H.Res.", "sres": "S.Res."};
/* bill-type-labels:end */

function formatBillCode(type, number) {
    const raw = String(type || '').trim();
    const label = BILL_TYPE_LABELS[raw.toLowerCase()] || raw.toUpperCase();
    return `${label} ${String(number === null || number === undefined ? '' : number).trim()}`.trim();
}

function ordinal(n) {
    const value = Math.abs(parseInt(n, 10));
    if (Number.isNaN(value)) return String(n);
    const lastTwo = value % 100;
    const suffix = lastTwo >= 11 && lastTwo <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' })[value % 10] || 'th';
    return `${parseInt(n, 10)}${suffix}`;
}

// "Schumer, Charles E." → "Charles E. Schumer" (split at the first comma, as Python does);
// members.json has no directOrderName.
function displayName(name) {
    const text = String(name || '').trim();
    const comma = text.indexOf(',');
    if (comma === -1) return text;
    return `${text.slice(comma + 1).trim()} ${text.slice(0, comma).trim()}`.trim();
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
    'August', 'September', 'October', 'November', 'December'];

// ISO date or datetime → "September 3, 2026"; short → "Sep 3, 2026" (a style string
// "short"/"long" is accepted too). Empty → ''; anything not an ISO date → the text, stripped.
function formatDate(value, short) {
    const isShort = typeof short === 'string' ? short === 'short' : Boolean(short);
    const text = String(value || '').trim();
    if (!text) return '';
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text.slice(0, 10));
    if (!match) return text;
    const year = parseInt(match[1], 10);
    const month = parseInt(match[2], 10);
    const day = parseInt(match[3], 10);
    const check = new Date(Date.UTC(year, month - 1, day));
    if (year < 1 || check.getUTCMonth() !== month - 1 || check.getUTCDate() !== day) return text;
    const name = MONTHS[month - 1];
    return `${isShort ? name.slice(0, 3) : name} ${day}, ${match[1].replace(/^0+/, '')}`;
}

/* ---- Question classes (spec §7.1). The table below is the Python table in
   app/render.py QUESTION_CLASSES, row for row; the first matching pattern wins. ---- */
/* question-classes:start */
const QUESTION_CLASSES = [
    {"pattern": "^On Passage\\b", "flags": "i", "plain": "Final vote to pass", "noun": null, "class": "D"},
    {"pattern": "^On (the )?Motion to Suspend the Rules and Pass\\b", "flags": "i", "plain": "Vote to pass (fast-track, needed two-thirds)", "noun": null, "class": "D"},
    {"pattern": "^On Agreeing to the Resolution\\b|^On the (Joint |Concurrent )?Resolution\\b(?! of Ratification)", "flags": "i", "plain": "Vote to adopt", "noun": null, "class": "D"},
    {"pattern": "^On (the )?Motion to Suspend the Rules and Agree\\b", "flags": "i", "plain": "Vote to adopt (fast-track, needed two-thirds)", "noun": null, "class": "D"},
    {"pattern": "^On (the )?Motion to (Suspend the Rules and )?Concur\\b|^On the Motion \\(Motion to Concur\\b|^On the Motion \\([A-Z][\\w ()]*? Motion to Concur\\b(?!.*\\bwith an Amendment\\b)|^On the Motion \\(Senate Concurs\\b|^On Concurring\\b", "flags": "i", "plain": "Vote to accept the other chamber's changes", "noun": null, "class": "D"},
    {"pattern": "^Passage, Objections of the President|^On Overriding the Veto\\b|^On the Veto\\b", "flags": "i", "plain": "Vote to override the veto (needed two-thirds)", "noun": null, "class": "D"},
    {"pattern": "^On the Resolution of Ratification\\b", "flags": "i", "plain": "Vote to ratify a treaty (needed two-thirds)", "noun": null, "class": "D"},
    {"pattern": "^Guilty or Not Guilty\\b", "flags": "i", "plain": "Verdict on an article of impeachment (needed two-thirds)", "noun": null, "class": "D"},
    {"pattern": "^On Agreeing to the Amendment\\b|^On the Amendment\\b", "flags": "i", "plain": "Vote on an amendment", "noun": "an amendment", "class": "P"},
    {"pattern": "^On Cloture on the Motion to Proceed\\b|^On the Cloture Motion\\b", "flags": "i", "plain": "Vote to end debate (needed 60)", "noun": "a motion to end debate", "class": "P"},
    {"pattern": "^On the Motion to Proceed\\b|^Motion to Proceed\\b|^On the Motion \\(Motion to Proceed\\b", "flags": "i", "plain": "Vote to take it up", "noun": "a motion to take it up", "class": "P"},
    {"pattern": "^On (the )?Motion to (Recommit|Commit|Refer)\\b|^On the Motion \\((?!Motion to Waive).*\\bMotions? to (Recommit|Commit|Refer)\\b", "flags": "i", "plain": "Vote to send it back to committee", "noun": "a motion to send it back to committee", "class": "P"},
    {"pattern": "^On (the )?Motion to Table\\b|^Table Motion to Reconsider\\b", "flags": "i", "plain": "Vote to set it aside", "noun": "a motion to set it aside", "class": "P"},
    {"pattern": "^On Ordering the Previous Question\\b", "flags": "i", "plain": "Vote to end debate on the rule", "noun": "a motion to end debate on the rule", "class": "P"},
    {"pattern": "^On (the )?Motion to Discharge\\b|^On the Motion \\(Motion to Discharge\\b", "flags": "i", "plain": "Vote to bring it to the floor", "noun": "a motion to bring it to the floor", "class": "P"},
    {"pattern": "^On the Motion \\(Motion to Waive\\b", "flags": "i", "plain": "Vote to waive a budget rule (needed 60)", "noun": "a motion to waive a budget rule", "class": "P"},
    {"pattern": "^On the Point of Order\\b", "flags": "i", "plain": "Vote on a point of order", "noun": "a point of order", "class": "P"},
    {"pattern": "^On the Nomination\\b", "flags": "i", "plain": "Vote to confirm", "noun": null, "class": "P"},
    {"pattern": "^Election of the Speaker\\b", "flags": "i", "plain": "Election of the Speaker", "noun": null, "class": "P"},
    {"pattern": "^On (the )?Motion to Adjourn\\b", "flags": "i", "plain": "Vote to adjourn", "noun": "a motion to adjourn", "class": "P"},
    {"pattern": "^Call of the House\\b|^Call by States\\b|^(On the )?Motion for Attendance\\b", "flags": "i", "plain": "Attendance call", "noun": null, "class": "P"}
];
/* question-classes:end */

const QUESTION_FALLBACK = { pattern: null, flags: '', plain: 'Procedural vote', noun: 'a procedural motion', class: 'P' };
const QUESTION_PATTERNS = QUESTION_CLASSES.map((row) => new RegExp(row.pattern, row.flags));
const QUESTION_BY_PLAIN = {};
QUESTION_CLASSES.concat([QUESTION_FALLBACK]).forEach((row) => { QUESTION_BY_PLAIN[row.plain] = row; });

// The row names this file branches on (render.py branches on the row id; the plain
// question is unique per row, so it identifies the row here).
const PLAIN_SPEAKER = 'Election of the Speaker';
const PLAIN_NOMINATION = 'Vote to confirm';
const PLAIN_CONCUR = "Vote to accept the other chamber's changes";
const PLAIN_CLOTURE = 'Vote to end debate (needed 60)';
const PLAIN_AMENDMENT = 'Vote on an amendment';

function isImpeachRow(row) { return row.plain.startsWith('Verdict on an article of impeachment'); }
function isVetoRow(row) { return row.plain.startsWith('Vote to override the veto'); }
// render.py ids adopt, adopt_fast, treaty.
function isAdoptRow(row) { return row.plain.startsWith('Vote to adopt') || row.plain.startsWith('Vote to ratify'); }
// render.py's row threshold: '2/3' on exactly the rows whose plain question says "needed two-thirds".
function rowThreshold(row) { return /needed two-thirds/.test(row.plain) ? '2/3' : null; }

function questionRow(question) {
    const text = String(question || '').trim().replace(/\s+/g, ' ');
    for (let i = 0; i < QUESTION_CLASSES.length; i += 1) {
        if (QUESTION_PATTERNS[i].test(text)) return QUESTION_CLASSES[i];
    }
    return QUESTION_FALLBACK;
}

function questionClass(question) {
    return questionRow(question).class;
}

function plainQuestion(question) {
    return questionRow(question).plain;
}

/* ---- Result → seal text and outcome sentence (spec §7.2, §7.3), twins of
   render.result_phrase / render.outcome_sentence. rc = one votes_index roll call. ---- */
const PASSED_RE = /(Passed|Agreed to|Veto Overridden)$/i;
const FAILED_RE = /(Failed|Defeated|Rejected|Not Sustained|Veto Sustained)$/i;
const THRESHOLD_RE = /\((?:[^)]*?,\s*)?(3\/5|2\/3) majority required\)/;
const VP_RE = /Vice President/i;
const TWO_THIRDS_QUESTION_RE = /Suspend the Rules|Objections of the President|Overriding the Veto|^On the Veto\b/i;
const NEEDED = { '2/3': 'two-thirds needed', '3/5': '60 needed' };
const NEEDED_SENTENCE = { '2/3': 'two-thirds were needed', '3/5': '60 votes were needed' };

function chamberName(chamber) {
    return String(chamber || '').trim().toLowerCase().startsWith('senate') ? 'Senate' : 'House';
}

function otherChamber(chamber) {
    return chamberName(chamber) === 'Senate' ? 'House' : 'Senate';
}

// 'Bill Passed (90-6, …)' → 'Bill Passed'.
function resultText(result) {
    return String(result || '').split('(')[0].trim();
}

// The row for a roll call: by its stored plain question, else by classifying its question.
function rcRow(rc) {
    return QUESTION_BY_PLAIN[rc.plain || ''] || questionRow(rc.question);
}

// '2/3' or '3/5' from '(… majority required)', else the row's own threshold, else '2/3'
// when the question names a suspension or a veto, else null (render.parse_threshold).
function parseThreshold(result, row, question) {
    const match = THRESHOLD_RE.exec(String(result || ''));
    if (match) return match[1];
    const implied = rowThreshold(row);
    if (implied) return implied;
    return TWO_THIRDS_QUESTION_RE.test(String(question || '').trim().replace(/\s+/g, ' ')) ? '2/3' : null;
}

function rcThreshold(rc, row) {
    return rc.threshold || parseThreshold(rc.result, row, rc.question);
}

// 'passed', 'failed' or 'other'.
function rcOutcome(result) {
    const text = resultText(result);
    if (FAILED_RE.test(text)) return 'failed';
    if (PASSED_RE.test(text)) return 'passed';
    return 'other';
}

function rcCounts(rc) {
    const counts = rc.counts || {};
    return [parseInt(counts.yeas, 10) || 0, parseInt(counts.nays, 10) || 0];
}

// Seal text for one roll call, e.g. "Passed the Senate 90–6" (§7.2).
function resultPhrase(rc, chamber) {
    const row = rcRow(rc);
    const cls = rc.class || row.class;
    const ch = chamberName(chamber);
    const [yeas, nays] = rcCounts(rc);
    const tally = `${yeas}–${nays}`;
    const threshold = rcThreshold(rc, row);
    const needed = NEEDED[threshold] ? ` (${NEEDED[threshold]})` : '';
    const outcome = rcOutcome(rc.result);
    const text = resultText(rc.result);

    if (row.plain === PLAIN_SPEAKER) return 'Speaker elected';
    if (row.plain === PLAIN_NOMINATION) return text;
    if (yeas > 0 && yeas === nays && outcome !== 'other') {
        if (outcome === 'passed' && VP_RE.test(String(rc.result || ''))) return `Tied ${tally} — agreed to on the Vice President's vote`;
        return `Tied ${tally} — motion failed`;
    }
    if (cls === 'D') {
        if (isImpeachRow(row)) {
            const verdict = ({ 'not guilty': 'Not guilty', guilty: 'Guilty' })[text.toLowerCase()] || text;
            return `${verdict} ${tally} (${NEEDED['2/3']})`;
        }
        if (isVetoRow(row)) {
            if (outcome === 'passed') return `Veto overridden in the ${ch} ${tally}`;
            if (outcome === 'failed') return `Veto override failed ${tally} (${NEEDED['2/3']})`;
            return text;
        }
        if (outcome === 'passed') return isAdoptRow(row) ? `Adopted by the ${ch} ${tally}` : `Passed the ${ch} ${tally}`;
        if (outcome === 'failed') return `Rejected by the ${ch} ${tally}${needed}`;
        return text;
    }
    if (row.plain === PLAIN_CLOTURE) {
        if (outcome === 'passed') return `Debate ended ${tally}`;
        if (outcome === 'failed') return `Debate not ended ${tally} (${NEEDED[threshold || '3/5'] || NEEDED['3/5']})`;
        return text;
    }
    if (row.plain === PLAIN_AMENDMENT) {
        if (outcome === 'passed') return `Amendment adopted ${tally}`;
        if (outcome === 'failed') return `Amendment rejected ${tally}${needed}`;
        return text;
    }
    if (outcome === 'passed') return `Motion agreed to ${tally}`;
    if (outcome === 'failed') return `Motion rejected ${tally}${needed}`;
    return text;
}

// The Lora outcome sentence for one roll call (§7.3); '' for Speaker elections and
// nominations (Python returns None there).
function outcomeSentence(rc, chamber) {
    const row = rcRow(rc);
    if (row.plain === PLAIN_SPEAKER || row.plain === PLAIN_NOMINATION) return '';
    const cls = rc.class || row.class;
    const ch = chamberName(chamber);
    const [yeas, nays] = rcCounts(rc);
    const when = formatDate(rc.date);
    const threshold = rcThreshold(rc, row);
    const outcome = rcOutcome(rc.result);
    const text = resultText(rc.result);

    if (yeas > 0 && yeas === nays && outcome !== 'other') {
        const how = outcome === 'passed' && VP_RE.test(String(rc.result || '')) ? "passed on the Vice President's vote" : 'failed';
        return `The ${ch} tied, ${yeas} to ${nays}, on ${when}; the motion ${how}.`;
    }
    if (isImpeachRow(row)) return `On ${when}, the ${ch} voted ${yeas} to ${nays}; two-thirds were needed to convict.`;
    if (outcome === 'other') return `On ${when}, the ${ch} voted ${yeas} to ${nays}: ${text}.`;

    if (cls === 'D') {
        if (isVetoRow(row)) {
            const verb = outcome === 'passed' ? 'voted to override the veto' : 'did not override the veto';
            return `The ${ch} ${verb}, ${yeas} to ${nays}, on ${when}.`;
        }
        if (outcome === 'passed') {
            let verb = 'passed it';
            if (isAdoptRow(row)) verb = 'adopted it';
            else if (row.plain === PLAIN_CONCUR) verb = `accepted the ${otherChamber(chamber)}'s changes`;
            return `The ${ch} ${verb}, ${yeas} to ${nays}, on ${when}.`;
        }
        const need = NEEDED_SENTENCE[threshold] ? `; ${NEEDED_SENTENCE[threshold]}` : '';
        return `The ${ch} rejected it, ${yeas} to ${nays}, on ${when}${need}.`;
    }
    if (row.plain === PLAIN_CLOTURE) {
        if (outcome === 'passed') return `On ${when}, the ${ch} voted to end debate, ${yeas} to ${nays}.`;
        const need = NEEDED_SENTENCE[threshold || '3/5'] || NEEDED_SENTENCE['3/5'];
        return `On ${when}, the ${ch} voted ${yeas} to ${nays} to end debate; ${need}, so debate did not end.`;
    }
    let verb;
    if (row.plain === PLAIN_AMENDMENT) {
        verb = outcome === 'passed' ? 'adopted an amendment' : 'rejected an amendment';
    } else {
        const noun = row.noun || QUESTION_FALLBACK.noun;
        verb = outcome === 'passed' ? `agreed to ${noun}` : `rejected ${noun}`;
    }
    return `On ${when}, the ${ch} ${verb}, ${yeas} to ${nays}.`;
}

/* ---- Vote positions (spec §7.1 "Positions") ---- */
/* positions:start */
const POSITIONS = {"Yea": ["yes", "Voted yes"], "Aye": ["yes", "Voted yes"], "Nay": ["no", "Voted no"], "No": ["no", "Voted no"], "Not Voting": ["nv", "Didn't vote"], "Present": ["present", "Present"], "Present, Giving Live Pair": ["present", "Present"], "Guilty": ["other", "Guilty"], "Not Guilty": ["other", "Not Guilty"]};
const SHORT_LABELS = {"yes": "Yes", "no": "No", "nv": "Didn't vote", "present": "Present"};
/* positions:end */
const POSITIONS_LOWER = {};
Object.keys(POSITIONS).forEach((key) => { POSITIONS_LOWER[key.toLowerCase()] = POSITIONS[key]; });

// [kind, label] for a raw position (trimmed, any case, as render.position_chip); a
// Speaker-election candidate name → ["other", "Voted"]; no position at all → null
// (the member was not in the roll call).
function positionChip(position) {
    const text = String(position === null || position === undefined ? '' : position).trim();
    if (!text) return null;
    return POSITIONS_LOWER[text.toLowerCase()] || ['other', 'Voted'];
}

/* ---- Builders: classes and text only ---- */
const SEAL_VARIANTS = ['final', 'moving', 'pending', 'ballot'];

function seal(text, variant) {
    const kind = SEAL_VARIANTS.indexOf(variant) === -1 ? 'moving' : variant;
    return el('span', { className: `seal seal--${kind}` }, text);
}

// The vote chip (§6.4). options.short → the roll-call table form (data-short);
// options.chamber ("House"/"Senate") names the chamber in the absent chip.
function chip(position, options) {
    const opts = options || {};
    const found = positionChip(position);
    if (!found) return el('span', { className: 'chip chip--absent' }, t('notInChamber', { chamber: opts.chamber || 'House' }));
    const [kind, label] = found;
    if (opts.short) return el('span', { className: `chip chip--${kind}`, 'data-short': true }, SHORT_LABELS[kind] || label);
    return el('span', { className: `chip chip--${kind}` }, label);
}

const NAME_SUFFIXES = ['Jr.', 'Sr.', 'II', 'III', 'IV'];

function initials(name) {
    const words = String(name || '').split(/\s+/).filter((word) => word && NAME_SUFFIXES.indexOf(word) === -1);
    if (!words.length) return '';
    return (words[0].charAt(0) + (words.length > 1 ? words[words.length - 1].charAt(0) : '')).toUpperCase();
}

// Photo over an initials block (§6.3). Only congress.gov images pass the CSP img-src.
function photo(url, name, size) {
    const box = el('span', { className: size === 64 ? 'photo photo--header' : 'photo', 'data-initials': initials(name) });
    if (/^https:\/\/www\.congress\.gov\//.test(String(url || ''))) {
        box.appendChild(el('img', { src: url, alt: '', loading: size === 64 ? null : 'lazy', width: size || 56, height: size || 56 }));
    }
    return box;
}

// The shared vote row (§6.4), the DOM twin of render.render_vote_row:
// data = {href, position, chamber, headline, displayable, meta: [strings]}.
function voteRow(data) {
    const headline = el('span', { className: data.displayable ? 'row-headline' : 'row-headline row-headline--official' }, data.headline || '');
    const meta = el('span', { className: 'meta' }, (data.meta || []).filter(Boolean).join(' · '));
    const parts = [chip(data.position, { chamber: data.chamber }), headline];
    if (!data.displayable) parts.push(seal(t('noSummary'), 'pending'));
    parts.push(meta);
    return data.href ? el('a', { className: 'vote-row', href: data.href }, ...parts) : el('div', { className: 'vote-row' }, ...parts);
}

// "Latest final vote · Sep 3, 2026 · {headline} — Voted yes" (§4.2 person row), the DOM twin
// of render._signal_line. vote = the render-ready latest_vote that T4.1's
// render.overview_member_fields returns (§10 #7): headline, displayable, seal, chip,
// chip_class, date_short. The chip text and class come from the server, never re-derived here.
function signalLine(vote) {
    if (!vote) return el('span', { className: 'person-signal' }, t('noFinalVotes'));
    const line = el('span', { className: 'person-signal' },
        vote.date_short ? `${t('latestFinalVote')} · ${vote.date_short} · ` : `${t('latestFinalVote')} · `);
    if (vote.displayable) line.append(vote.headline || '');
    else line.append(el('span', { className: 'official' }, vote.headline || ''), ' ', seal(vote.seal || t('noSummary'), 'pending'));
    line.append(' — ', el('span', { className: `chip ${vote.chip_class || 'chip--other'}` }, vote.chip || ''));
    return line;
}

// The person row (§6.4), the DOM twin of render.render_person_row for rows JS builds:
// member = one T4.1 overview_member_fields object (bioguideId, display_name, initials,
// seat_line, seat_seal, url, photo — already congress.gov-only or "" — district, latest_vote).
// trailing (optional Element) replaces the latest-vote signal: the bill page's reps slot
// (T7.3) passes chip(position, {chamber}) for this bill's vote instead.
function personRow(member, stateCode, trailing) {
    const bioguide = String(member.bioguideId || '');
    const name = member.display_name || '';
    const box = photo(member.photo, name, 56);
    if (member.initials) box.setAttribute('data-initials', member.initials);
    const body = el('span', { className: 'person-body' },
        el('span', { className: 'person-name' }, name),
        ' ',
        el('span', { className: 'person-seat' }, member.seat_line || ''));
    if (member.seat_seal) body.append(' ', seal(member.seat_seal, 'ballot'));
    body.append(' ', trailing || signalLine(member.latest_vote || null), ' ', el('span', { className: 'party' }));
    return el('a', {
        className: 'person',
        href: member.url || `/member?id=${encodeURIComponent(bioguide)}`,
        'data-bioguide': bioguide,
        'data-state': stateCode || member.state || '',
        'data-district': member.district === null || member.district === undefined ? '' : String(member.district),
    }, box, ' ', body);
}

// One roll-call table row (§6.4), the DOM twin of the server's state-group rows:
// member = a /api/votes/… member {first_name, last_name, state, vote, bioguide_id,
// covered_id, district}; options = {chamber: 'house'|'senate', current: bool}.
function rcTableRow(member, options) {
    const opts = options || {};
    const house = opts.chamber !== 'senate';
    const name = `${member.first_name || ''} ${member.last_name || ''}`.trim();
    const covered = /^[A-Z]\d{6}$/.test(String(member.covered_id || '')) ? String(member.covered_id) : '';
    const key = house ? String(member.bioguide_id || '') : `${member.state || ''}-${member.last_name || ''}`;
    const seat = opts.current && house && Number.isInteger(member.district) ? `District ${member.district}` : String(member.state || '');
    const position = String(member.vote || 'Not Voting');
    return el('tr', { 'data-key': key, 'data-bioguide': covered || null, 'data-position': position },
        el('th', { scope: 'row' },
            covered ? el('a', { href: `/member?id=${covered}` }, name) : name,
            el('span', { className: 'rc-seat' }, seat),
            el('span', { className: 'party' })),
        el('td', null, chip(position, { short: true })));
}

/* ============================================
   Behaviours (plan T2.3; spec §5.4, §6.3, §6.4, §6.6, §8 items 10–11, C-13)
   Every init is idempotent: site.js runs the page-independent ones itself at
   DOMContentLoaded, and a page enhancer may call any of them again safely.
   ============================================ */

const COVERED_STATES = { CA: 'California', FL: 'Florida', NY: 'New York', TX: 'Texas' };
const BREAKPOINTS = { narrow: '(min-width: 560px)', wide: '(min-width: 880px)' };
const HOME_KEY = 'cv-home';
const PARTY_KEY = 'cv-show-party';
const bound = new Set();

// Read once (§6.6): programmatic scrolls use behavior 'auto' when reduced motion is set.
const REDUCED_MOTION = (() => {
    try {
        return typeof window !== 'undefined' && !!window.matchMedia
            && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) {
        return false;
    }
})();

function isWide() {
    try {
        return !!window.matchMedia && window.matchMedia(BREAKPOINTS.wide).matches;
    } catch (e) {
        return false;
    }
}

function once(name) {
    if (bound.has(name)) return false;
    bound.add(name);
    return true;
}

/* ---- Storage: every access in try/catch (private mode, blocked storage) ---- */
function storageGet(store, key) {
    try {
        return window[store].getItem(key);
    } catch (e) {
        return null;
    }
}

function storageSet(store, key, value) {
    try {
        window[store].setItem(key, value);
        return true;
    } catch (e) {
        return false;
    }
}

function storageRemove(store, key) {
    try {
        window[store].removeItem(key);
    } catch (e) {
        /* nothing stored, nothing to remove */
    }
}

/* ---- Focus (§8 item 11) ---- */
function focusHeading(heading) {
    if (!heading) return;
    if (!heading.hasAttribute('tabindex')) heading.setAttribute('tabindex', '-1');
    heading.focus({ preventScroll: true });
    heading.scrollIntoView({ block: 'start', behavior: REDUCED_MOTION ? 'auto' : 'smooth' });
}

function focusFirstControl(container) {
    if (!container) return;
    const target = container.querySelector('input, select, textarea, button, a[href], summary');
    if (target) target.focus();
}

/* ---- Remembered district: localStorage['cv-home'] (§5.4, C-13) ---- */
// {state, district, savedAt} or null. Only covered states and whole district numbers count.
function readHome() {
    let value = null;
    try {
        value = JSON.parse(storageGet('localStorage', HOME_KEY) || 'null');
    } catch (e) {
        return null;
    }
    if (!value || !COVERED_STATES[value.state]) return null;
    const district = Number(value.district);
    if (!Number.isInteger(district) || district < 1 || district > 99) return null;
    return { state: value.state, district, savedAt: String(value.savedAt || '') };
}

function todayIso() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

// Written only on the reader's own act: a #mine landing, the Remember button, or a
// bill-page ZIP pick (T7.3). Returns the stored object, or null when it was refused.
function rememberDistrict(state, district) {
    const code = String(state || '').toUpperCase();
    const number = Number(district);
    if (!COVERED_STATES[code] || !Number.isInteger(number) || number < 1 || number > 99) return null;
    const home = { state: code, district: number, savedAt: todayIso() };
    return storageSet('localStorage', HOME_KEY, JSON.stringify(home)) ? home : null;
}

function forgetHome() {
    storageRemove('localStorage', HOME_KEY);
}

function homePlace(home) {
    return `${COVERED_STATES[home.state]}, District ${home.district}`;
}

function homeHref(home) {
    return `/state?code=${home.state}&district=${home.district}`;
}

// "Remembered: New York, District 4 · Change · Forget" (§5.4). onForget(line) runs after
// the key is removed and returns the re-rendered container; focus goes to its first control.
function rememberedLine(home, onForget) {
    const forget = el('button', { type: 'button', className: 'btn--secondary remember-forget' }, t('forget'));
    const line = el('p', { className: 'meta remembered-line' },
        t('remembered', { place: homePlace(home) }), ' · ',
        el('a', { href: '/#find', className: 'remember-change' }, t('change')), ' · ',
        forget);
    forget.addEventListener('click', () => {
        forgetHome();
        rewriteMastheadLink();
        const container = typeof onForget === 'function' ? onForget(line) : null;
        if (container) focusFirstControl(container);
    });
    return line;
}

// The #mine fragment is the only automatic trigger (§3.3): write cv-home from the URL's own
// code and district, then drop the fragment with history.replaceState.
function initHome() {
    if (!once('home')) return readHome();
    if (window.location.hash === '#mine') {
        const params = new URLSearchParams(window.location.search);
        if (params.get('code') && params.get('district')) rememberDistrict(params.get('code'), params.get('district'));
        try {
            history.replaceState(history.state, '', window.location.pathname + window.location.search);
        } catch (e) {
            /* the fragment stays; nothing else depends on it */
        }
    }
    return readHome();
}

// Masthead "My representatives": server href is /#find; point it at the remembered district.
function rewriteMastheadLink() {
    const link = document.getElementById('nav-mine');
    if (!link) return;
    const home = readHome();
    link.setAttribute('href', home ? homeHref(home) : '/#find');
}

// The reveal lives in sessionStorage only; the old localStorage key is removed on every load.
function removeLegacyPartyKey() {
    storageRemove('localStorage', PARTY_KEY);
}

/* ---- Photos (§6.3): a failed <img> is removed so the initials block shows ---- */
function dropBrokenPhoto(img) {
    if (img && img.parentNode && img.parentNode.classList && img.parentNode.classList.contains('photo')) {
        img.parentNode.removeChild(img);
    }
}

function initPhotos() {
    if (once('photos')) {
        document.addEventListener('error', (event) => {
            if (event.target && event.target.tagName === 'IMG') dropBrokenPhoto(event.target);
        }, true);
    }
    // Images that failed before this script ran: complete, nothing decoded, a source chosen
    // (a lazy image not yet requested has currentSrc '' and is caught by the listener later).
    document.querySelectorAll('.photo img').forEach((img) => {
        if (img.complete && img.naturalWidth === 0 && img.currentSrc) dropBrokenPhoto(img);
    });
}

/* ---- Party toggle (§6.4, §4.2, §4.3, §5.4) ----
   One control pair, "Show party labels" / "Hide party labels" (the label is the state); the
   role=status sibling .party-status (present and empty in the HTML) announces the change.
   Accepted call shapes, so each page passes what it has:
     initPartyToggle()                         – fetch the toggle's data-party-url and fill spans
     initPartyToggle(fill)                     – fill(true|false) after the default fill/clear
     initPartyToggle(onShow, onHide)           – onShow(payload) / onHide()
     initPartyToggle({url, onShow, onHide})    – as above with an explicit ?show_party=true URL */
function initPartyToggle(arg, hideArg) {
    const toggles = Array.from(document.querySelectorAll('.party-toggle'));
    if (!toggles.length || !once('party')) return;
    let url = toggles[0].getAttribute('data-party-url') || '';
    let onShow = null;
    let onHide = null;
    if (typeof arg === 'function' && typeof hideArg === 'function') {
        onShow = arg;
        onHide = hideArg;
    } else if (typeof arg === 'function') {
        onShow = () => arg(true);
        onHide = () => arg(false);
    } else if (arg && typeof arg === 'object') {
        url = arg.url || url;
        onShow = typeof arg.onShow === 'function' ? arg.onShow : null;
        onHide = typeof arg.onHide === 'function' ? arg.onHide : null;
    }
    let revealed = false;
    let partyName = '';
    let payload = null;
    // Every Show and Hide press takes a new number. A reveal whose fetch or page callback
    // settles after a later press is stale: it must not touch the screen, the session key
    // or the status line (§8 item 10, §5.4).
    let attempt = 0;

    function status(key) {
        document.querySelectorAll('.party-status').forEach((node) => { node.textContent = key ? t(key) : ''; });
    }

    function label() {
        toggles.forEach((button) => { button.textContent = revealed ? t('hideParty') : t('showParty'); });
    }

    // Default fill from the payload: overview members by data-bioguide, the member header,
    // and "Voted for {Name}" into Speaker rows. Page callbacks may add to it.
    function fillSpeakerPicks() {
        const picks = (payload && payload.speaker_votes) || {};
        document.querySelectorAll('.speaker-pick[data-rc]').forEach((span) => {
            const name = revealed ? picks[span.getAttribute('data-rc')] : '';
            span.textContent = name ? `Voted for ${name}` : '';
        });
    }

    function fillSpans() {
        const byId = {};
        const members = payload ? [].concat(payload.senators || [], payload.house || [], payload.members || []) : [];
        members.forEach((member) => { if (member && member.bioguideId) byId[member.bioguideId] = member.partyName || ''; });
        document.querySelectorAll('[data-bioguide] .party').forEach((span) => {
            const holder = span.closest('[data-bioguide]');
            const value = holder ? byId[holder.getAttribute('data-bioguide')] : '';
            if (value !== undefined) span.textContent = revealed ? value : '';
        });
        partyName = payload && payload.member ? payload.member.partyName || '' : '';
        document.querySelectorAll('.member-header .party').forEach((span) => { span.textContent = revealed ? partyName : ''; });
        fillSpeakerPicks();
    }

    async function show(announce) {
        const mine = ++attempt;
        revealed = true;
        label();
        try {
            if (url && !payload) {
                const response = await fetch(url);
                if (!response.ok) throw new Error(`party ${response.status}`);
                payload = await response.json();
                if (mine !== attempt || !revealed) return;
            }
            fillSpans();
            if (onShow) await onShow(payload);
            if (mine !== attempt || !revealed) {
                // A Hide landed while the page callback ran: its fill must not outlive the Hide.
                if (!revealed && onHide) onHide();
                return;
            }
            storageSet('sessionStorage', PARTY_KEY, '1');
            if (announce) status('partyShown');
        } catch (e) {
            if (mine !== attempt || !revealed) return;   // a later press owns the state now
            // The reveal failed: put the "Show party labels" label back and say nothing.
            // "Party labels hidden" would be a false status after a Show press (§8 item 10),
            // and the spec gives no failure copy for this control.
            revealed = false;
            label();
            fillSpans();
            status('');
        }
    }

    function hide() {
        attempt++;
        revealed = false;
        label();
        document.querySelectorAll('.party, .speaker-pick').forEach((span) => { span.textContent = ''; });
        if (onHide) onHide();
        storageRemove('sessionStorage', PARTY_KEY);
        status('partyHidden');
    }

    function onToggle() {
        if (revealed) hide();
        else show(true);
    }

    toggles.forEach((button) => button.addEventListener('click', onToggle));
    label();
    if (storageGet('sessionStorage', PARTY_KEY) === '1') show(false);
}

/* ---- Share (§4.3 Share, §6.4): navigator.share, else copy the canonical URL ---- */
function canonicalUrl() {
    const link = document.querySelector('link[rel="canonical"]');
    return link ? link.href : window.location.origin + window.location.pathname;
}

function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text);
    return new Promise((resolve, reject) => {
        const field = el('textarea', { readonly: true, className: 'visually-hidden' });
        field.value = text;
        document.body.appendChild(field);
        field.select();
        const ok = document.execCommand && document.execCommand('copy');
        document.body.removeChild(field);
        if (ok) resolve();
        else reject(new Error('copy'));
    });
}

function initShare() {
    document.querySelectorAll('.share-btn, [data-share]').forEach((button) => {
        if (button.hasAttribute('data-share-bound')) return;
        button.setAttribute('data-share-bound', '');
        button.addEventListener('click', async () => {
            const data = {
                title: button.getAttribute('data-share-title') || document.title.split(' | ')[0],
                text: button.getAttribute('data-share-text') || '',
                url: button.getAttribute('data-share-url') || canonicalUrl(),
            };
            const statusNode = (button.parentNode && button.parentNode.querySelector('.share-status'))
                || document.querySelector('.share-status');
            if (navigator.share) {
                try {
                    await navigator.share(data);
                    return;
                } catch (e) {
                    if (e && e.name === 'AbortError') return;
                }
            }
            try {
                await copyText(data.url);
                if (statusNode) {
                    // Empty the line first, so a second copy is a change a screen reader announces.
                    statusNode.textContent = '';
                    setTimeout(() => { statusNode.textContent = t('linkCopied'); }, 100);
                }
            } catch (e) {
                if (statusNode) statusNode.textContent = data.url;
            }
        });
    });
}

/* ---- Notify form (§4.1 m2): JSON POST, result in role=status, focus to it ---- */
function initNotify() {
    const form = document.getElementById('notify-form');
    if (!form || !once('notify')) return;
    const fields = form.querySelector('fieldset.notify-fields');
    if (fields) fields.disabled = false;
    const stateSelect = document.getElementById('notify-state');
    const email = document.getElementById('notify-email');
    const emailError = document.getElementById('notify-email-error');
    const submit = document.getElementById('notify-submit');
    const status = document.getElementById('notify-status');
    if (!stateSelect || !email || !status) return;

    function setEmailError(message) {
        if (!emailError) return;
        emailError.textContent = message;
        if (message) {
            email.setAttribute('aria-describedby', emailError.id);
            email.setAttribute('aria-invalid', 'true');
        } else {
            email.removeAttribute('aria-invalid');
        }
    }

    email.addEventListener('invalid', () => setEmailError(t('invalidEmail')));
    email.addEventListener('input', () => setEmailError(''));
    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const state = stateSelect.value;
        const stateName = stateSelect.options[stateSelect.selectedIndex]
            ? stateSelect.options[stateSelect.selectedIndex].textContent.trim() : state;
        if (submit) submit.disabled = true;
        status.textContent = '';
        let ok = false;
        let rejected = false;
        try {
            const response = await fetch('/api/notify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: email.value.trim(), state }),
            });
            ok = response.ok;
            rejected = response.status === 422;
        } catch (e) {
            ok = false;
        }
        if (rejected) {
            // The server's email check is stricter than the browser's type=email (a@b passes
            // the browser, not the server), so this is the reader's address, not an outage.
            if (submit) submit.disabled = false;
            status.classList.remove('field-error');
            if (emailError) setEmailError(t('invalidEmail'));
            else status.textContent = t('invalidEmail');
            email.focus();
            return;
        }
        status.textContent = ok ? t('notifyThanks', { state: stateName }) : t('notifyFailed');
        status.classList.toggle('field-error', !ok);
        if (ok) form.reset();
        if (submit) submit.disabled = false;
        if (!status.hasAttribute('tabindex')) status.setAttribute('tabindex', '-1');
        status.focus();
    });
}

/* ---- Page-independent start-up: run once per page, before page enhancers ---- */
function initSite() {
    removeLegacyPartyKey();
    initHome();
    rewriteMastheadLink();
    initPhotos();
    initNotify();
}

if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initSite);
    else initSite();
}

/* ---- Node export for tests/test_formatter_parity.py (browsers skip this) ---- */
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        STRINGS, BILL_TYPE_LABELS, QUESTION_CLASSES, POSITIONS, SHORT_LABELS,
        t, formatBillCode, ordinal, displayName, formatDate, questionClass, plainQuestion,
        resultPhrase, outcomeSentence, positionChip, initials,
        readHome, rememberDistrict, forgetHome, homePlace, homeHref, initHome,
    };
}
