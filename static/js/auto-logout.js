/**
 * auto-logout.js — Inactivity-based automatic session logout
 *
 * Configuration (set via window.RADOKI_AUTO_LOGOUT before this script loads):
 *   csrfToken      — Django CSRF token for the AJAX POST request
 *   logoutUrl      — Server-side logout endpoint (POST, invalidates session)
 *   loginUrl       — Where to redirect after logout
 *   timeoutSeconds — Total inactivity timeout (default: 20)
 *   warningSeconds — How many seconds before timeout to show the warning modal (default: 10)
 */
(function () {
  'use strict';

  const cfg            = window.RADOKI_AUTO_LOGOUT || {};
  const TIMEOUT_MS     = (cfg.timeoutSeconds || 20) * 1000;
  const WARNING_MS     = (cfg.warningSeconds || 10) * 1000;
  const WARN_AFTER_MS  = TIMEOUT_MS - WARNING_MS;   // inactivity time before warning appears

  let idleTimer        = null;
  let warnTimer        = null;
  let countdownInterval = null;
  let bsModal          = null;
  let secondsLeft      = 0;
  let modalVisible     = false;

  /* ── Bootstrap modal instance (lazy) ── */
  function getModal() {
    if (!bsModal) {
      const el = document.getElementById('autoLogoutModal');
      if (el && window.bootstrap) {
        bsModal = new bootstrap.Modal(el, { backdrop: 'static', keyboard: false });
      }
    }
    return bsModal;
  }

  /* ── Update countdown display + SVG ring ── */
  var RING_CIRCUMFERENCE = 226;   /* 2π × r(36) ≈ 226 */

  function updateCountdown() {
    var el = document.getElementById('autoLogoutCountdown');
    if (el) el.textContent = secondsLeft;

    /* Animate the ring: full circle at start, shrinks to 0 */
    var arc = document.getElementById('alRingArc');
    if (arc) {
      var total   = Math.round(WARNING_MS / 1000);
      var ratio   = total > 0 ? secondsLeft / total : 0;
      var offset  = RING_CIRCUMFERENCE * (1 - ratio);
      arc.style.strokeDashoffset = offset;
    }
  }

  /* ── Show warning modal ── */
  function showWarning() {
    modalVisible = true;
    secondsLeft  = Math.round(WARNING_MS / 1000);
    updateCountdown();

    const modal = getModal();
    if (modal) modal.show();

    clearInterval(countdownInterval);
    countdownInterval = setInterval(function () {
      secondsLeft = Math.max(0, secondsLeft - 1);
      updateCountdown();
      if (secondsLeft <= 0) clearInterval(countdownInterval);
    }, 1000);
  }

  /* ── Hide warning modal ── */
  function hideWarning() {
    modalVisible = false;
    clearInterval(countdownInterval);
    var modal = getModal();
    if (modal) modal.hide();
    /* Reset ring to full */
    var arc = document.getElementById('alRingArc');
    if (arc) arc.style.strokeDashoffset = 0;
  }

  /* ── Perform server-side logout then redirect ── */
  function performLogout() {
    clearInterval(countdownInterval);
    clearTimeout(idleTimer);
    clearTimeout(warnTimer);

    /* Invalidate session on the server before redirecting */
    const done = function () {
      window.location.href = (cfg.loginUrl || '/accounts/login/') +
        '?next=' + encodeURIComponent(window.location.pathname) +
        '&reason=idle';
    };

    try {
      fetch(cfg.logoutUrl || '/accounts/auto-logout/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': cfg.csrfToken || '',
          'X-Requested-With': 'XMLHttpRequest',
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
      }).then(done).catch(done);
    } catch (e) {
      done();
    }
  }

  /* ── Reset inactivity timers (called on every user interaction) ── */
  function resetTimer() {
    clearTimeout(idleTimer);
    clearTimeout(warnTimer);

    /* If the warning modal is visible, close it */
    if (modalVisible) hideWarning();

    /* Schedule warning → then logout */
    warnTimer = setTimeout(showWarning,     WARN_AFTER_MS);
    idleTimer = setTimeout(performLogout,   TIMEOUT_MS);
  }

  /* ── Attach activity listeners ── */
  var ACTIVITY_EVENTS = [
    'mousemove', 'mousedown', 'click',
    'keydown', 'keypress',
    'touchstart', 'touchmove',
    'scroll', 'wheel',
    'focus',
  ];
  ACTIVITY_EVENTS.forEach(function (evt) {
    document.addEventListener(evt, resetTimer, { passive: true, capture: true });
  });

  /* ── Handle visibility change (tab switching, phone lock screen) ── */
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') {
      /* Treat returning to the tab as activity */
      resetTimer();
    }
  });

  /* ── "Stay Logged In" button ── */
  document.addEventListener('DOMContentLoaded', function () {
    var stayBtn = document.getElementById('autoLogoutStayBtn');
    if (stayBtn) {
      stayBtn.addEventListener('click', function () {
        hideWarning();
        resetTimer();
      });
    }
  });

  /* ── Kick off ── */
  resetTimer();

}());
