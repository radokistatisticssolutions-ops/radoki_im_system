/**
 * admin_auto_logout.js
 * Inactivity-based auto-logout for the Django admin.
 * Self-contained — no Bootstrap dependency.
 *
 * Config via window.RADOKI_ADMIN_AUTO_LOGOUT:
 *   csrfToken      — Django CSRF token
 *   logoutUrl      — AJAX logout endpoint  (default: /accounts/auto-logout/)
 *   loginUrl       — Redirect after logout (default: /admin/login/)
 *   timeoutSeconds — Total inactivity seconds (default: 20)
 *   warningSeconds — Warning duration before logout (default: 10)
 */
(function () {
  'use strict';

  var cfg          = window.RADOKI_ADMIN_AUTO_LOGOUT || {};
  var TIMEOUT_MS   = (cfg.timeoutSeconds || 20) * 1000;
  var WARNING_MS   = (cfg.warningSeconds || 10) * 1000;
  var WARN_AFTER   = TIMEOUT_MS - WARNING_MS;

  var idleTimer        = null;
  var warnTimer        = null;
  var countdownInterval = null;
  var secondsLeft      = 0;
  var CIRCUMFERENCE    = 2 * Math.PI * 36;   /* r = 36 */

  /* ─── Build modal DOM once ─── */
  var overlay = null;

  function buildModal() {
    if (overlay) return;

    var css = [
      '#radoki-al-overlay{position:fixed;inset:0;z-index:999999;',
        'display:none;align-items:center;justify-content:center;',
        'background:rgba(10,25,40,.72);backdrop-filter:blur(3px);}',
      '#radoki-al-overlay.visible{display:flex;}',
      '#radoki-al-box{background:#fff;border-radius:14px;width:340px;max-width:calc(100vw - 32px);',
        'box-shadow:0 20px 60px rgba(0,0,0,.35);overflow:hidden;font-family:"Segoe UI",Arial,sans-serif;}',
      '#radoki-al-head{background:linear-gradient(135deg,#0e3d5c 0%,#1a5276 60%,#2471a3 100%);',
        'padding:18px 20px;display:flex;align-items:center;gap:12px;}',
      '#radoki-al-head-icon{width:38px;height:38px;border-radius:9px;',
        'background:rgba(255,255,255,.15);display:flex;align-items:center;',
        'justify-content:center;flex-shrink:0;}',
      '#radoki-al-head-icon svg{width:20px;height:20px;fill:none;stroke:#fff;stroke-width:2;',
        'stroke-linecap:round;stroke-linejoin:round;}',
      '#radoki-al-head-title{color:#fff;font-size:.95rem;font-weight:700;margin:0;}',
      '#radoki-al-head-sub{color:rgba(255,255,255,.65);font-size:.75rem;margin:2px 0 0;}',
      '#radoki-al-body{padding:22px 24px 0;text-align:center;}',
      '#radoki-al-ring-wrap{position:relative;width:90px;height:90px;margin:0 auto 14px;}',
      '#radoki-al-ring-wrap svg{width:90px;height:90px;transform:rotate(-90deg);}',
      '.al-track{fill:none;stroke:#e8f0f8;stroke-width:7;}',
      '.al-arc{fill:none;stroke:url(#alAdminGrad);stroke-width:7;',
        'stroke-linecap:round;stroke-dasharray:'+CIRCUMFERENCE+';',
        'stroke-dashoffset:0;transition:stroke-dashoffset .9s linear;}',
      '#radoki-al-center{position:absolute;inset:0;display:flex;flex-direction:column;',
        'align-items:center;justify-content:center;}',
      '#radoki-al-num{font-size:1.45rem;font-weight:800;color:#1a5276;line-height:1;}',
      '#radoki-al-sec{font-size:.65rem;color:#64748b;margin-top:1px;}',
      '#radoki-al-title{font-size:.95rem;font-weight:700;color:#1e293b;margin:0 0 6px;}',
      '#radoki-al-sub{font-size:.8rem;color:#64748b;margin:0 0 12px;}',
      '#radoki-al-hint{font-size:.75rem;color:#94a3b8;margin:0 0 16px;}',
      '#radoki-al-divider{border:none;border-top:1px solid #e2e8f0;margin:0 -24px;}',
      '#radoki-al-footer{display:flex;gap:10px;padding:14px 24px;}',
      '#radoki-al-stay{flex:1;background:#1a5276;color:#fff;border:none;border-radius:7px;',
        'padding:9px 0;font-size:.85rem;font-weight:700;cursor:pointer;',
        'transition:background .15s;}',
      '#radoki-al-stay:hover{background:#2980b9;}',
      '#radoki-al-now{flex:1;background:#fee2e2;color:#991b1b;border:none;border-radius:7px;',
        'padding:9px 0;font-size:.85rem;font-weight:700;cursor:pointer;',
        'transition:background .15s;text-decoration:none;display:block;text-align:center;}',
      '#radoki-al-now:hover{background:#fecaca;}',
    ].join('');

    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    overlay = document.createElement('div');
    overlay.id = 'radoki-al-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-labelledby', 'radoki-al-title');
    overlay.innerHTML = [
      '<div id="radoki-al-box">',
        '<div id="radoki-al-head">',
          '<div id="radoki-al-head-icon">',
            '<svg viewBox="0 0 24 24">',
              '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
            '</svg>',
          '</div>',
          '<div>',
            '<p id="radoki-al-head-title">Session Timeout Warning</p>',
            '<p id="radoki-al-head-sub">Inactivity detected on admin session</p>',
          '</div>',
        '</div>',
        '<div id="radoki-al-body">',
          '<div id="radoki-al-ring-wrap">',
            '<svg viewBox="0 0 90 90">',
              '<defs>',
                '<linearGradient id="alAdminGrad" x1="0%" y1="0%" x2="100%" y2="0%">',
                  '<stop offset="0%" stop-color="#1a5276"/>',
                  '<stop offset="100%" stop-color="#2980b9"/>',
                '</linearGradient>',
              '</defs>',
              '<circle class="al-track" cx="45" cy="45" r="36"/>',
              '<circle class="al-arc" cx="45" cy="45" r="36" id="radoki-al-arc"/>',
            '</svg>',
            '<div id="radoki-al-center">',
              '<span id="radoki-al-num">10</span>',
              '<span id="radoki-al-sec">sec</span>',
            '</div>',
          '</div>',
          '<p id="radoki-al-title">You\'ve been inactive</p>',
          '<p id="radoki-al-sub">Your admin session will expire automatically to protect the system.</p>',
          '<p id="radoki-al-hint">&#128432; Move your mouse or press any key to stay signed in.</p>',
          '<hr id="radoki-al-divider">',
        '</div>',
        '<div id="radoki-al-footer">',
          '<button id="radoki-al-stay">&#10003; Stay Logged In</button>',
          '<a id="radoki-al-now" href="' + (cfg.loginUrl || '/admin/login/') + '">&#x2192; Logout Now</a>',
        '</div>',
      '</div>',
    ].join('');

    document.body.appendChild(overlay);

    document.getElementById('radoki-al-stay').addEventListener('click', function () {
      hideWarning();
      resetTimer();
    });
  }

  /* ─── Show / hide ─── */
  function showWarning() {
    buildModal();
    secondsLeft = Math.round(WARNING_MS / 1000);
    updateRing();
    overlay.classList.add('visible');

    clearInterval(countdownInterval);
    countdownInterval = setInterval(function () {
      secondsLeft = Math.max(0, secondsLeft - 1);
      updateRing();
      if (secondsLeft <= 0) clearInterval(countdownInterval);
    }, 1000);
  }

  function hideWarning() {
    if (!overlay) return;
    overlay.classList.remove('visible');
    clearInterval(countdownInterval);
    var arc = document.getElementById('radoki-al-arc');
    if (arc) arc.style.strokeDashoffset = 0;
  }

  function updateRing() {
    var numEl = document.getElementById('radoki-al-num');
    var arc   = document.getElementById('radoki-al-arc');
    if (numEl) numEl.textContent = secondsLeft;
    if (arc) {
      var total  = Math.round(WARNING_MS / 1000);
      var ratio  = total > 0 ? secondsLeft / total : 0;
      arc.style.strokeDashoffset = CIRCUMFERENCE * (1 - ratio);
    }
  }

  /* ─── Logout ─── */
  function performLogout() {
    clearInterval(countdownInterval);
    clearTimeout(idleTimer);
    clearTimeout(warnTimer);

    var done = function () {
      window.location.href = (cfg.loginUrl || '/admin/login/') + '?reason=idle';
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
    } catch (e) { done(); }
  }

  /* ─── Timer reset on activity ─── */
  function resetTimer() {
    clearTimeout(idleTimer);
    clearTimeout(warnTimer);
    hideWarning();
    warnTimer = setTimeout(showWarning,   WARN_AFTER);
    idleTimer = setTimeout(performLogout, TIMEOUT_MS);
  }

  var EVENTS = ['mousemove','mousedown','click','keydown','touchstart','scroll','wheel'];
  EVENTS.forEach(function (e) {
    document.addEventListener(e, resetTimer, { passive: true, capture: true });
  });

  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') resetTimer();
  });

  resetTimer();

}());
