/* ============================================
   ClearVote — Visualization Helpers
   Pure DOM-element factories for data visualizations.
   Uses viz-* CSS classes from Phase 1.
   Exposed as window.ClearVoteViz
   ============================================ */

(function () {
    'use strict';

    const SVG_NS = 'http://www.w3.org/2000/svg';

    function svgEl(tag, attrs) {
        const element = document.createElementNS(SVG_NS, tag);
        if (attrs) {
            for (const [key, value] of Object.entries(attrs)) {
                element.setAttribute(key, value);
            }
        }
        return element;
    }

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

    /**
     * Creates an SVG participation ring showing a percentage.
     * @param {number} percentage - 0 to 100
     * @param {number} size - pixel width/height (default 40)
     * @returns {SVGElement}
     */
    function createParticipationRing(percentage, size) {
        size = size || 40;
        const r = (size / 2) - 3;
        const circumference = 2 * Math.PI * r;
        const offset = circumference * (1 - percentage / 100);

        const svg = svgEl('svg', {
            class: 'viz-participation-ring',
            width: String(size),
            height: String(size),
            viewBox: `0 0 ${size} ${size}`,
        });

        const cx = String(size / 2);
        const cy = String(size / 2);

        svg.appendChild(svgEl('circle', {
            cx, cy, r: String(r), class: 'viz-ring-bg',
        }));

        const fill = svgEl('circle', {
            cx, cy, r: String(r), class: 'viz-ring-fill',
            'stroke-dasharray': String(circumference),
            'stroke-dashoffset': String(offset),
            transform: `rotate(-90 ${cx} ${cy})`,
        });
        svg.appendChild(fill);

        const text = svgEl('text', {
            x: cx, y: cy, class: 'viz-ring-text',
        });
        text.textContent = `${Math.round(percentage)}%`;
        svg.appendChild(text);

        return svg;
    }

    /**
     * Creates a proportional vote split bar (yea/nay/missed).
     * @param {number} yeaPct - percentage for yea
     * @param {number} nayPct - percentage for nay
     * @param {number} missedPct - percentage for missed
     * @returns {HTMLElement}
     */
    function createVoteSplitBar(yeaPct, nayPct, missedPct) {
        const bar = el('div', { className: 'viz-vote-bar' });

        if (yeaPct > 0) {
            const yea = el('div', { className: 'viz-bar-yea' });
            yea.style.width = `${yeaPct}%`;
            bar.appendChild(yea);
        }
        if (nayPct > 0) {
            const nay = el('div', { className: 'viz-bar-nay' });
            nay.style.width = `${nayPct}%`;
            bar.appendChild(nay);
        }
        if (missedPct > 0) {
            const missed = el('div', { className: 'viz-bar-missed' });
            missed.style.width = `${missedPct}%`;
            bar.appendChild(missed);
        }

        return bar;
    }

    /**
     * Creates an SVG donut chart with legend.
     * @param {Array<{label: string, count: number, color: string}>} segments
     * @param {number} total
     * @param {number} size - pixel width/height (default 160)
     * @returns {HTMLElement} - a div.viz-donut-row containing SVG + legend
     */
    function createDonutChart(segments, total, size) {
        size = size || 160;
        const r = 60;
        const circumference = 2 * Math.PI * r;
        const cx = size / 2;
        const cy = size / 2;

        const row = el('div', { className: 'viz-donut-row' });

        const svg = svgEl('svg', {
            class: 'viz-donut-chart',
            width: String(size),
            height: String(size),
            viewBox: `0 0 ${size} ${size}`,
        });

        // Background circle
        svg.appendChild(svgEl('circle', {
            cx: String(cx), cy: String(cy), r: String(r),
            fill: 'none', stroke: 'var(--border-light)', 'stroke-width': '20',
        }));

        // Colored segments
        let offset = 0;
        segments.forEach(seg => {
            if (seg.count <= 0) return;
            const segLen = (seg.count / total) * circumference;
            const gap = circumference - segLen;

            const circle = svgEl('circle', {
                cx: String(cx), cy: String(cy), r: String(r),
                fill: 'none',
                stroke: seg.color,
                'stroke-width': '20',
                'stroke-dasharray': `${segLen} ${gap}`,
                'stroke-dashoffset': String(-offset),
                transform: `rotate(-90 ${cx} ${cy})`,
            });
            circle.style.transition = 'stroke-dasharray 1s ease';
            svg.appendChild(circle);

            offset += segLen;
        });

        // Center text
        const totalFormatted = total.toLocaleString();
        const bigText = svgEl('text', {
            x: String(cx), y: String(cy - 6),
            'text-anchor': 'middle',
            'font-size': '22',
            'font-weight': '700',
            fill: 'var(--text-primary)',
            'font-family': 'var(--font-heading)',
        });
        bigText.textContent = totalFormatted;
        svg.appendChild(bigText);

        const subText = svgEl('text', {
            x: String(cx), y: String(cy + 14),
            'text-anchor': 'middle',
            'font-size': '11',
            fill: 'var(--text-dim)',
            'font-family': 'var(--font-body)',
        });
        subText.textContent = 'total votes';
        svg.appendChild(subText);

        row.appendChild(svg);

        // Legend
        const legend = el('div', { className: 'viz-donut-legend' });
        segments.forEach(seg => {
            const pct = total > 0 ? Math.round((seg.count / total) * 100) : 0;
            const dot = el('span', { className: 'viz-legend-dot' });
            dot.style.background = seg.color;
            const item = el('div', { className: 'viz-legend-item' },
                dot,
                el('span', null, seg.label),
                el('span', { className: 'viz-legend-value' }, `${seg.count.toLocaleString()} (${pct}%)`)
            );
            legend.appendChild(item);
        });
        row.appendChild(legend);

        return row;
    }

    /**
     * Creates a topic dual-bar row (supported vs opposed).
     * @param {number} supported - count of supported
     * @param {number} opposed - count of opposed
     * @param {string} label - topic name
     * @returns {HTMLElement}
     */
    function createTopicBar(supported, opposed, label) {
        const total = supported + opposed;
        const row = el('div', { className: 'viz-topic-row' });
        row.appendChild(el('span', { className: 'viz-topic-name', title: label }, label));

        const dualBar = el('div', { className: 'viz-topic-dual-bar' });

        if (total > 0) {
            const supBar = el('div', { className: 'viz-topic-supported-bar' },
                el('span', { className: 'viz-bar-label' }, String(supported))
            );
            supBar.style.width = `${(supported / total) * 100}%`;
            dualBar.appendChild(supBar);

            const oppBar = el('div', { className: 'viz-topic-opposed-bar' },
                el('span', { className: 'viz-bar-label' }, String(opposed))
            );
            oppBar.style.width = `${(opposed / total) * 100}%`;
            dualBar.appendChild(oppBar);
        }

        row.appendChild(dualBar);
        row.appendChild(el('span', { className: 'viz-topic-summary' },
            `${supported} supported, ${opposed} opposed`));

        return row;
    }

    /**
     * Creates the full attendance visualization section.
     * @param {number} percentage - participation rate
     * @param {number} attended - votes attended
     * @param {number} total - total eligible votes
     * @param {string} congressLabel - e.g. "117th-119th Congress"
     * @returns {HTMLElement}
     */
    function createAttendanceBar(percentage, attended, total, congressLabel) {
        const container = el('div', { className: 'viz-attendance-bar-container' });

        const labelRow = el('div', { className: 'viz-attendance-label-row' });
        labelRow.appendChild(el('span', { className: 'viz-attendance-label' }, 'Floor Vote Participation'));
        labelRow.appendChild(el('span', { className: 'viz-attendance-pct' }, `${percentage}%`));
        container.appendChild(labelRow);

        const barTrack = el('div', { className: 'viz-attendance-bar' });
        const fill = el('div', { className: 'viz-attendance-fill' });
        fill.style.width = `${percentage}%`;
        barTrack.appendChild(fill);
        container.appendChild(barTrack);

        const context = `Attended ${attended.toLocaleString()} of ${total.toLocaleString()} eligible floor votes`;
        const contextText = congressLabel ? `${context} (${congressLabel})` : context;
        container.appendChild(el('p', { className: 'viz-attendance-context' }, contextText));

        return container;
    }

    /**
     * Creates a stat card.
     * @param {string} label - small label text
     * @param {string} number - large number text
     * @param {string} detail - small detail text
     * @returns {HTMLElement}
     */
    function createStatCard(label, number, detail) {
        return el('div', { className: 'viz-stat-card' },
            el('div', { className: 'viz-stat-label' }, label),
            el('div', { className: 'viz-stat-number' }, number),
            el('div', { className: 'viz-stat-detail' }, detail)
        );
    }

    window.ClearVoteViz = {
        createParticipationRing,
        createVoteSplitBar,
        createDonutChart,
        createTopicBar,
        createAttendanceBar,
        createStatCard,
    };
})();
