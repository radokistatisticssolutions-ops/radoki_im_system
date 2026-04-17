/* RADOKI IMS — User Admin JS fixes
 * Injected on all /admin/accounts/user/ pages via UserAdmin.Media.
 * Runs on window.load so Django's SelectFilter2.js has already built the widget.
 */
(function () {
  function fixSelectorArrows() {
    document.querySelectorAll('.selector-chooser .selector-add').forEach(function (btn) {
      btn.textContent = '';
      btn.style.cssText =
        'display:flex;align-items:center;justify-content:center;' +
        'width:30px;height:30px;border-radius:7px;cursor:pointer;' +
        'background:#1a5276;border:none;text-decoration:none;' +
        'font-size:15px;font-weight:700;color:#fff;line-height:1;' +
        'overflow:visible;text-indent:0;';
      btn.innerHTML = '&#8594;'; /* → */
    });

    document.querySelectorAll('.selector-chooser .selector-remove').forEach(function (btn) {
      btn.textContent = '';
      btn.style.cssText =
        'display:flex;align-items:center;justify-content:center;' +
        'width:30px;height:30px;border-radius:7px;cursor:pointer;' +
        'background:#fee2e2;border:none;text-decoration:none;' +
        'font-size:15px;font-weight:700;color:#991b1b;line-height:1;' +
        'overflow:visible;text-indent:0;';
      btn.innerHTML = '&#8592;'; /* ← */
    });
  }

  window.addEventListener('load', fixSelectorArrows);
})();
