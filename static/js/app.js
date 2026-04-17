// static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('ping');
  if (btn) {
    btn.addEventListener('click', async () => {
      const res = await fetch('/ajax/ping/');
      const data = await res.json();
      document.getElementById('ping-result').innerText =
        data.ok ? `AJAX OK for user: ${data.user}` : 'AJAX failed';
    });
  }
});
