/** Bounded dependency failure UI for local WebGL studies, never synthetic operational evidence. */
(function () {
  "use strict";
  var terminal = false;
  var timer;
  function unavailable() {
    if (terminal) return;
    terminal = true;
    window.clearTimeout(timer);
    var loading = document.getElementById("loading");
    if (loading) loading.hidden = true;
    document.body.classList.add("experiment-unavailable");
    var panel = document.querySelector("[data-experiment-fallback]");
    if (!panel) {
      panel = document.createElement("section");
      panel.dataset.experimentFallback = "";
      panel.className = "experiment-fallback";
      panel.setAttribute("role", "status");
      panel.innerHTML = '<h1>Interactive study unavailable</h1><p>A graphics dependency could not be loaded. This experimental preview is not an operational surface.</p><a href="../ui/ontology-instances-2d.html">Open the local 2D reference</a>';
      document.body.appendChild(panel);
    }
    panel.hidden = false;
  }
  window.addEventListener("error", unavailable);
  window.addEventListener("unhandledrejection", unavailable);
  window.addEventListener("load", function () {
    var loading = document.getElementById("loading");
    if (!loading || loading.classList.contains("hidden")) return;
    timer = window.setTimeout(function () {
      if (!loading.classList.contains("hidden")) unavailable();
    }, 5000);
    var observer = new MutationObserver(function () {
      if (loading.classList.contains("hidden")) {
        window.clearTimeout(timer);
        observer.disconnect();
      } else if (/failed|error/i.test(loading.textContent)) {
        unavailable();
        observer.disconnect();
      }
    });
    observer.observe(loading, { attributes: true, childList: true, characterData: true, subtree: true });
    if (/failed|error/i.test(loading.textContent)) unavailable();
  });
})();
