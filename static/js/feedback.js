/* Feedback dialog — native <dialog>, auto-captures page context
   (plan T2.4; spec §2.2 #5, §6.4 dialog, §10 #17). Hooks: #feedback-modal,
   #feedback-open, #feedback-cancel, #feedback-overlay, #feedback-form,
   #feedback-message, #feedback-submit, #feedback-status, #feedback-context,
   #about-feedback-cta, the h1 inside .member-header/.bill-header/.state-header,
   .state-header[data-context-label] (preferred on /state, T4.2) and any
   [data-feedback-open] button, including ones added later by JS (delegated). */

(function () {
    'use strict';

    var modal = document.getElementById('feedback-modal');
    var openBtn = document.getElementById('feedback-open');
    var cancelBtn = document.getElementById('feedback-cancel');
    var overlay = document.getElementById('feedback-overlay');
    var form = document.getElementById('feedback-form');
    var messageEl = document.getElementById('feedback-message');
    var submitBtn = document.getElementById('feedback-submit');
    var statusEl = document.getElementById('feedback-status');
    var contextEl = document.getElementById('feedback-context');

    var SENT = 'Thanks — sent.';
    var FAILED = "We couldn't send that. Please try again in a few minutes.";
    // A 422 is the report itself, not an outage: waiting and retrying would fail the same way.
    var REFUSED = "We couldn't accept that message. Please shorten it and try again.";
    var opener = null;

    function getPageContext() {
        var path = window.location.pathname;
        var params = new URLSearchParams(window.location.search);

        if (path === '/member') {
            var name = document.querySelector('.member-header h1');
            return {
                page_type: 'member',
                context_id: params.get('id') || '',
                context_label: name ? name.textContent.trim() : ''
            };
        }

        if (path === '/bill') {
            var title = document.querySelector('.bill-header h1');
            return {
                page_type: 'bill',
                context_id: params.get('type') && params.get('number')
                    ? params.get('type') + params.get('number')
                    : '',
                context_label: title ? title.textContent.trim() : ''
            };
        }

        if (path === '/state') {
            // T4.2 puts the place the page is about ("New York, District 4") on the header,
            // because the h1 there reads "New York's representatives"; old shells use the h1.
            var labelled = document.querySelector('.state-header[data-context-label]');
            var stateTitle = document.querySelector('.state-header h1');
            return {
                page_type: 'state',
                context_id: params.get('code') || '',
                context_label: labelled
                    ? labelled.getAttribute('data-context-label')
                    : (stateTitle ? stateTitle.textContent.trim() : '')
            };
        }

        if (path === '/about' || path === '/methodology' || path === '/privacy') {
            return { page_type: path.slice(1), context_id: '', context_label: '' };
        }

        return { page_type: 'home', context_id: '', context_label: '' };
    }

    function setStatus(text, failed) {
        statusEl.textContent = text;
        statusEl.classList.toggle('field-error', !!failed);
    }

    function openModal(trigger) {
        if (!modal || typeof modal.showModal !== 'function') return;
        opener = trigger || document.activeElement;
        var ctx = getPageContext();
        if (ctx.context_label) {
            contextEl.textContent = 'About: ' + ctx.context_label;
            contextEl.hidden = false;
        } else {
            contextEl.textContent = '';
            contextEl.hidden = true;
        }
        setStatus('', false);
        submitBtn.disabled = false;
        if (!modal.open) modal.showModal();
        messageEl.focus();
    }

    function closeModal() {
        if (modal && modal.open) modal.close();
    }

    var hamburger = document.querySelector('.hamburger');
    var nav = document.querySelector('nav');
    if (hamburger && nav) {
        hamburger.addEventListener('click', function () {
            nav.classList.toggle('open');
            hamburger.setAttribute('aria-expanded', nav.classList.contains('open'));
        });

        // Close mobile menu when a nav link is clicked
        nav.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', function () {
                nav.classList.remove('open');
                hamburger.setAttribute('aria-expanded', 'false');
            });
        });

        // Close mobile menu on Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && nav.classList.contains('open')) {
                nav.classList.remove('open');
                hamburger.setAttribute('aria-expanded', 'false');
            }
        });
    }

    // Set active nav link based on current path
    var currentPath = window.location.pathname;
    if (nav) {
        nav.querySelectorAll('a').forEach(function (link) {
            link.classList.remove('active');
            var href = link.getAttribute('href');
            if (currentPath === '/' && (href === '/' || href === '')) {
                link.classList.add('active');
            } else if (currentPath === '/about' && href === '/about') {
                link.classList.add('active');
            } else if (currentPath === '/member' && href === '/') {
                // No active state on detail pages
            } else if (currentPath === '/bill' && href === '/#browse') {
                link.classList.add('active');
            }
        });
    }

    if (!modal || !form) return;

    // Openers: the footer "Report an error on this page" (#feedback-open) and, at ≥880,
    // the fixed .feedback-btn. On the old shells they are the same element.
    var openers = [];
    if (openBtn) openers.push(openBtn);
    document.querySelectorAll('.feedback-btn').forEach(function (btn) {
        if (openers.indexOf(btn) === -1) openers.push(btn);
    });
    openers.forEach(function (btn) {
        btn.addEventListener('click', function () { openModal(btn); });
    });
    // Delegated opener for [data-feedback-open] buttons, including ones JS adds later
    // (the home vacancy row, T4.2 app.js); the trigger is the opener, so focus returns to it.
    document.addEventListener('click', function (e) {
        var trigger = e.target.closest && e.target.closest('[data-feedback-open]');
        if (trigger) openModal(trigger);
    });

    var aboutCta = document.getElementById('about-feedback-cta');
    if (aboutCta) {
        aboutCta.addEventListener('click', function () { openModal(aboutCta); });
    }

    if (cancelBtn) cancelBtn.addEventListener('click', closeModal);
    if (overlay) overlay.addEventListener('click', closeModal);
    // No backdrop-click close (§6.4 asks for Esc and Cancel only): a click on the
    // dialog's own padding also targets the dialog element itself and would throw away a
    // half-typed report.

    // Esc (the native cancel) and every close() end here: focus goes back to the opener.
    modal.addEventListener('close', function () {
        setStatus('', false);
        submitBtn.disabled = false;
        if (opener && document.body.contains(opener) && typeof opener.focus === 'function') {
            opener.focus();
        }
        opener = null;
    });

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        var message = messageEl.value.trim();
        if (!message) return;

        var ctx = getPageContext();
        // No #fragment, and never over the server's 500 characters (F070): a long ?q= or
        // tracking parameters used to turn every report from the page into a 422.
        var pageUrl = (window.location.origin + window.location.pathname + window.location.search).slice(0, 500);
        submitBtn.disabled = true;
        setStatus('', false);

        fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                page_url: pageUrl,
                page_type: ctx.page_type,
                context_id: ctx.context_id,
                context_label: ctx.context_label
            })
        })
        .then(function (res) {
            if (!res.ok) throw new Error(res.status === 422 ? 'Refused' : 'Failed');
            // Success stays in the dialog until the reader closes it (§6.4).
            messageEl.value = '';
            setStatus(SENT, false);
            submitBtn.disabled = false;
        })
        .catch(function (err) {
            setStatus(err && err.message === 'Refused' ? REFUSED : FAILED, true);
            submitBtn.disabled = false;
        });
    });
})();
