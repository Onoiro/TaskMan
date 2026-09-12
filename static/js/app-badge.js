/**
 * PWA app badge for unread notifications (Badging API).
 * Gracefully no-ops on browsers without navigator.setAppBadge support.
 */
(function () {
  'use strict';

  var POLL_INTERVAL_MS = 60000;

  function supported() {
    return 'setAppBadge' in navigator && 'clearAppBadge' in navigator;
  }

  function updateBadge(count) {
    if (!supported()) return;
    try {
      if (count > 0) {
        navigator.setAppBadge(count);
      } else {
        navigator.clearAppBadge();
      }
    } catch (err) {
      // Some browsers expose the API but reject calls outside installed PWAs
      console.debug('App badge update failed:', err);
    }
  }

  window.refreshAppBadge = function () {
    fetch('/notifications/unread-count/', {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(function (response) {
        if (!response.ok) return null;
        return response.json();
      })
      .then(function (data) {
        if (data) updateBadge(data.unread_count);
      })
      .catch(function () {
        // Network errors are fine, badge just stays stale
      });
  };

  function start() {
    updateBadgeFromPage();
    window.refreshAppBadge();

    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'visible') {
        window.refreshAppBadge();
      }
    });

    setInterval(window.refreshAppBadge, POLL_INTERVAL_MS);
  }

  // Server-rendered badge already holds the count on page load,
  // so the first fetch can be skipped when the badge element exists.
  function updateBadgeFromPage() {
    var badge = document.getElementById('notificationBadge');
    if (badge) {
      var count = parseInt(badge.textContent, 10);
      if (!isNaN(count) && count > 0) updateBadge(count);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
