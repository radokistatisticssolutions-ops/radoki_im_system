(function () {
  'use strict';

  /* ── Selectors for the regions we swap out ── */
  var REGIONS = [
    '#changelist-form',   // results table + pagination
    '#changelist-filter', // filter sidebar
    '#toolbar',           // search bar + result count
  ];

  /* ── Loading overlay ── */
  function setLoading(on) {
    var wrap = document.getElementById('content-main');
    if (!wrap) return;
    wrap.style.transition = 'opacity .15s';
    wrap.style.opacity    = on ? '0.45' : '1';
  }

  /* ── Swap every region from a parsed document ── */
  function swapRegions(doc) {
    REGIONS.forEach(function (sel) {
      var newEl = doc.querySelector(sel);
      var oldEl = document.querySelector(sel);
      if (newEl && oldEl) oldEl.replaceWith(newEl);
    });
  }

  /* ── Core fetch + swap ── */
  function ajaxNavigate(url, pushState) {
    setLoading(true);

    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        var doc = new DOMParser().parseFromString(html, 'text/html');
        swapRegions(doc);
        if (pushState !== false) history.pushState({ ajaxUrl: url }, '', url);
        setLoading(false);
        attachAll();           // re-bind on new DOM
      })
      .catch(function () {
        setLoading(false);
        window.location.href = url;  // fallback: full navigation
      });
  }

  /* ── Bind filter sidebar links ── */
  function bindFilters() {
    var sidebar = document.getElementById('changelist-filter');
    if (!sidebar) return;
    sidebar.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        ajaxNavigate(this.href);
      });
    });
  }

  /* ── Bind paginator links ── */
  function bindPaginator() {
    document.querySelectorAll('.paginator a, a.paginator-nav:not(.disabled)').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        ajaxNavigate(this.href);
      });
    });
  }

  /* ── Bind search form ── */
  function bindSearch() {
    var form = document.getElementById('changelist-search');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var data = new FormData(this);
      var url  = new URL(window.location.href);
      data.forEach(function (v, k) { url.searchParams.set(k, v); });
      url.searchParams.delete('p');   // reset to page 1
      ajaxNavigate(url.toString());
    });
  }

  /* ── Bind "Clear all filters" / "Show counts" links ── */
  function bindToolbarLinks() {
    var toolbar = document.getElementById('toolbar');
    if (toolbar) {
      toolbar.querySelectorAll('a').forEach(function (a) {
        a.addEventListener('click', function (e) {
          e.preventDefault();
          ajaxNavigate(this.href);
        });
      });
    }
  }

  function attachAll() {
    bindFilters();
    bindPaginator();
    bindSearch();
    bindToolbarLinks();
  }

  /* ── Browser back / forward ── */
  window.addEventListener('popstate', function (e) {
    var url = (e.state && e.state.ajaxUrl) || window.location.href;
    ajaxNavigate(url, false);
  });

  /* ── Boot ── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachAll);
  } else {
    attachAll();
  }
})();
