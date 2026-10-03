// The repository card in the header shows the latest GitHub release, fetched
// in the browser. Show the documented release (from VERSION, injected by
// conf.py as fluxRestfulRelease) there instead, keeping the live stars and forks.
(function () {
  var release = window.fluxRestfulRelease;
  if (!release) { return; }
  function show() {
    document.querySelectorAll(".md-source__fact--version").forEach(function (el) {
      if (el.textContent !== release) { el.textContent = release; }
    });
  }
  document.addEventListener("DOMContentLoaded", function () {
    show();
    new MutationObserver(show).observe(document.body, { childList: true, subtree: true });
  });
})();
