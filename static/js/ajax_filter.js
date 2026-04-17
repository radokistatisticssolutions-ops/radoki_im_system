/**
 * ajax_filter.js
 * Intercepts GET filter forms, pagination links, and tab links inside
 * main.main-content and swaps only that container — no full page reload.
 */
(function () {
  'use strict';

  var mainSel = 'main.main-content';

  /* ── Loading indicator ── */
  function setLoading(on) {
    var el = document.querySelector(mainSel);
    if (!el) return;
    el.style.transition = 'opacity .15s';
    el.style.opacity    = on ? '0.45' : '1';
  }

  /* ── Swap main content from parsed document ── */
  function swapMain(html) {
    var doc    = new DOMParser().parseFromString(html, 'text/html');
    var newEl  = doc.querySelector(mainSel);
    var oldEl  = document.querySelector(mainSel);
    if (!newEl || !oldEl) return false;
    oldEl.innerHTML = newEl.innerHTML;
    return true;
  }

  /* ── Core fetch → swap ── */
  function navigate(url, pushState) {
    setLoading(true);
    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) {
        if (!r.ok) throw new Error('bad response');
        return r.text();
      })
      .then(function (html) {
        if (!swapMain(html)) { window.location.href = url; return; }
        if (pushState !== false) history.pushState({ ajaxUrl: url }, '', url);
        setLoading(false);
        attachAll();               // re-bind on new DOM
        window.scrollTo({ top: 0, behavior: 'smooth' });
      })
      .catch(function () {
        setLoading(false);
        window.location.href = url; // graceful fallback
      });
  }

  /* ── Helpers ── */
  function samePath(href) {
    try {
      var u = new URL(href, window.location.href);
      return u.origin === window.location.origin &&
             u.pathname === window.location.pathname;
    } catch (e) { return false; }
  }

  function bind(el, event, fn) {
    if (el._ajaxBound) return;
    el._ajaxBound = true;
    el.addEventListener(event, fn);
  }

  /* ── Bind GET filter/search forms ── */
  function bindForms() {
    var main = document.querySelector(mainSel);
    if (!main) return;

    main.querySelectorAll('form').forEach(function (form) {
      var method = (form.getAttribute('method') || 'get').toLowerCase();
      if (method !== 'get') return;                // skip POST forms (login etc.)
      if (form.id === 'logout-form') return;       // skip logout

      bind(form, 'submit', function (e) {
        e.preventDefault();
        var url    = new URL(window.location.href);
        var params = new URLSearchParams();
        new FormData(this).forEach(function (v, k) {
          if (k !== 'csrfmiddlewaretoken' && v !== '') params.set(k, v);
        });
        params.delete('page');          // reset to page 1 on new search
        url.search = params.toString();
        navigate(url.toString());
      });
    });
  }

  /* ── Bind pagination & same-page links (.page-link, tab links) ── */
  function bindLinks() {
    var main = document.querySelector(mainSel);
    if (!main) return;

    /* Pagination: Bootstrap .page-link anchors */
    main.querySelectorAll('a.page-link').forEach(function (a) {
      bind(a, 'click', function (e) {
        e.preventDefault();
        navigate(this.href);
      });
    });

    /* Tab links: .mc-tab, .nav-link, or any <a> that stays on same path */
    main.querySelectorAll('a.mc-tab, a.nav-link').forEach(function (a) {
      if (!a.href || a.href === '#') return;
      bind(a, 'click', function (e) {
        e.preventDefault();
        navigate(this.href);
      });
    });

    /* Generic same-path links with query params (e.g. status/course tab links) */
    main.querySelectorAll('a[href*="?"]').forEach(function (a) {
      if (!a.href || a.href === '#') return;
      if (!samePath(a.href)) return;               // skip external / different-page links
      if (a._ajaxBound) return;
      bind(a, 'click', function (e) {
        e.preventDefault();
        navigate(this.href);
      });
    });
  }

  function attachAll() {
    bindForms();
    bindLinks();
  }

  /* ── Browser back / forward ── */
  window.addEventListener('popstate', function (e) {
    var url = (e.state && e.state.ajaxUrl) || window.location.href;
    navigate(url, false);
  });

  /* ── Boot ── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachAll);
  } else {
    attachAll();
  }
}());
