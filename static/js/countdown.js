// Live countdown timers for task deadlines.
// Elements opt in via data-deadline attribute (ISO 8601, UTC-accurate).
(function () {
    'use strict';

    var timers = [];

    function pad(n) {
        return n < 10 ? '0' + n : String(n);
    }

    function formatDuration(ms) {
        var totalSeconds = Math.floor(ms / 1000);
        var days = Math.floor(totalSeconds / 86400);
        var hours = Math.floor((totalSeconds % 86400) / 3600);
        var minutes = Math.floor((totalSeconds % 3600) / 60);
        var seconds = totalSeconds % 60;
        var parts = [];
        if (days > 0) parts.push(days + 'd');
        if (days > 0 || hours > 0) parts.push(hours + 'h');
        parts.push(pad(minutes) + 'm');
        parts.push(pad(seconds) + 's');
        return parts.join(' ');
    }

    function setText(el, value) {
        // Keep icons/decoration intact: write into .deadline-text if present
        var target = el.querySelector('.deadline-text') || el;
        target.textContent = value;
    }

    function update(el, now) {
        var deadline = new Date(el.dataset.deadline);
        if (isNaN(deadline.getTime())) return;

        var diff = deadline.getTime() - now;
        if (diff <= 0) {
            setText(el, el.dataset.overdueText || 'Overdue');
            el.classList.add('deadline-overdue');
            el.classList.remove('deadline-soon');
        } else {
            setText(
                el,
                (el.dataset.leftText || 'Time left: ') + formatDuration(diff)
            );
            el.classList.remove('deadline-overdue');
            // Highlight when less than 24 hours remain
            el.classList.toggle('deadline-soon', diff < 86400000);
        }
    }

    function tick() {
        var now = Date.now();
        timers.forEach(function (el) { update(el, now); });
    }

    function init() {
        timers = Array.prototype.slice.call(
            document.querySelectorAll('[data-deadline]')
        );
        if (timers.length === 0) return;
        tick();
        setInterval(tick, 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
