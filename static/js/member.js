/* ClearVoting — member page enhancer.
   The server renders the whole page (header, recent votes, record, sponsored, money).
   This file only starts what needs the browser, all of it owned by site.js: the party
   reveal (site.js fills the header's party span and each Speaker row's candidate name
   from the show_party=true payload), Share, and the remembered-district breadcrumb
   (site.js's initSite already runs the photo fallback on load). The record filters
   submit only through their Filter button (WCAG 3.2.2: no navigation when a control's
   value changes). CSP-safe: no inline handlers, no HTML strings. */
(function () {
    'use strict';

    var header = document.querySelector('.member-header');
    if (!header) return;
    var bioguide = header.getAttribute('data-bioguide') || '';
    var state = header.getAttribute('data-state') || '';

    // §4.3: when the remembered district is in this member's state, the breadcrumb goes to it.
    function initBreadcrumb() {
        var crumb = document.querySelector('.crumb a[data-state]');
        if (!crumb) return;
        var home = readHome();
        if (home && home.state === state) crumb.setAttribute('href', homeHref(home));
    }

    initPartyToggle({
        url: '/api/members/detail/' + encodeURIComponent(bioguide) + '?show_party=true'
    });
    initShare();
    initBreadcrumb();
})();
