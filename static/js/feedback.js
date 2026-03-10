/* Feedback widget — auto-captures page context */

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

    function getPageContext() {
        var path = window.location.pathname;
        var params = new URLSearchParams(window.location.search);

        if (path === '/member') {
            var name = document.querySelector('.member-header h2');
            return {
                page_type: 'member',
                context_id: params.get('id') || '',
                context_label: name ? name.textContent.trim() : ''
            };
        }

        if (path === '/bill') {
            var title = document.querySelector('.bill-header h2');
            return {
                page_type: 'bill',
                context_id: params.get('type') && params.get('number')
                    ? params.get('type') + params.get('number')
                    : '',
                context_label: title ? title.textContent.trim() : ''
            };
        }

        if (path === '/about') {
            return { page_type: 'about', context_id: '', context_label: '' };
        }

        return { page_type: 'home', context_id: '', context_label: '' };
    }

    function openModal() {
        modal.hidden = false;
        var ctx = getPageContext();
        if (ctx.context_label) {
            contextEl.textContent = 'About: ' + ctx.context_label;
            contextEl.hidden = false;
        } else {
            contextEl.textContent = '';
            contextEl.hidden = true;
        }
        messageEl.focus();
    }

    function closeModal() {
        modal.hidden = true;
    }

    var hamburger = document.querySelector('.hamburger');
    if (hamburger) {
        hamburger.addEventListener('click', function () {
            var nav = document.querySelector('nav');
            nav.classList.toggle('open');
            hamburger.setAttribute('aria-expanded', nav.classList.contains('open'));
        });
    }

    openBtn.addEventListener('click', openModal);
    cancelBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', closeModal);

    var aboutCta = document.getElementById('about-feedback-cta');
    if (aboutCta) {
        aboutCta.addEventListener('click', function () {
            openBtn.click();
        });
    }

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && !modal.hidden) {
            closeModal();
        }
    });

    form.addEventListener('submit', function (e) {
        e.preventDefault();

        var message = messageEl.value.trim();
        if (!message) return;

        var ctx = getPageContext();

        submitBtn.disabled = true;
        submitBtn.textContent = 'Sending...';

        fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                page_url: window.location.href,
                page_type: ctx.page_type,
                context_id: ctx.context_id,
                context_label: ctx.context_label
            })
        })
        .then(function (res) {
            if (!res.ok) throw new Error('Failed');
            statusEl.textContent = 'Thanks for your feedback!';
            statusEl.className = 'feedback-status feedback-success';
            statusEl.hidden = false;
            messageEl.value = '';
            setTimeout(function () {
                closeModal();
                statusEl.hidden = true;
                submitBtn.disabled = false;
                submitBtn.textContent = 'Send';
            }, 1500);
        })
        .catch(function () {
            statusEl.textContent = 'Something went wrong. Please try again.';
            statusEl.className = 'feedback-status feedback-error';
            statusEl.hidden = false;
            submitBtn.disabled = false;
            submitBtn.textContent = 'Send';
        });
    });
})();
