(function () {
  "use strict";

  function activate(group, value) {
    document.querySelectorAll('[data-fg-select="' + group + '"]').forEach(function (button) {
      var active = button.getAttribute("data-fg-value") === value;
      button.setAttribute("aria-pressed", String(active));
      button.classList.toggle("is-selected", active);
    });
    document.querySelectorAll('[data-fg-panel="' + group + '"]').forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-fg-value") !== value;
    });
    document.querySelectorAll('[data-fg-row-group="' + group + '"]').forEach(function (row) {
      row.classList.toggle("is-selected", row.getAttribute("data-fg-row-value") === value);
    });
  }

  function bindSelectors() {
    document.addEventListener("click", function (event) {
      var control = event.target.closest("[data-fg-select]");
      if (!control) return;
      var group = control.getAttribute("data-fg-select");
      var value = control.getAttribute("data-fg-value");
      if (!group || !value) return;
      activate(group, value);
    });
  }

  function bindCopyButtons() {
    document.querySelectorAll("[data-fg-copy]").forEach(function (button) {
      button.addEventListener("click", async function () {
        var source = document.querySelector(button.getAttribute("data-fg-copy"));
        if (!source) return;
        var text = "value" in source ? source.value : source.textContent;
        var result = button.nextElementSibling;
        if (!result || !result.classList.contains("fg-copy-result")) {
          result = document.createElement("span");
          result.className = "fg-copy-result";
          result.setAttribute("role", "status");
          button.after(result);
        }
        if (!navigator.clipboard || !text) {
          result.textContent = "Copy unavailable. Select the visible value to copy it manually.";
          return;
        }
        button.disabled = true;
        button.setAttribute("aria-busy", "true");
        try {
          await navigator.clipboard.writeText(text);
          result.textContent = "Copied to clipboard.";
        } catch (error) {
          result.textContent = "Copy unavailable. Select the visible value to copy it manually.";
        } finally {
          button.disabled = false;
          button.setAttribute("aria-busy", "false");
        }
      });
    });
  }

  function bindRows() {
    document.querySelectorAll("[data-fg-row-value]").forEach(function (row) {
      row.addEventListener("click", function (event) {
        if (event.target.closest("a")) return;
        activate(row.getAttribute("data-fg-row-group"), row.getAttribute("data-fg-row-value"));
      });
    });
  }

  function bindStaticForms() {
    document.querySelectorAll("[data-fg-static-form]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        var result = form.querySelector(".fg-form-result");
        if (!result) {
          result = document.createElement("p");
          result.className = "fg-form-result";
          result.setAttribute("role", "status");
          form.appendChild(result);
        }
        result.textContent = "Preview only. No request was sent. The displayed sample record is unchanged.";
      });
    });
  }

  /** Decorative chart heights are not recorded measurements or quantitative evidence. */
  function explainIllustrativeCharts() {
    document.querySelectorAll(".forecast-calibration, .report-mini-bars").forEach(function (chart) {
      chart.setAttribute("role", "img");
      chart.setAttribute("aria-label", "Illustrative shape only; recorded measurements are unavailable.");
      var note = document.createElement("p");
      note.className = "chart-source-limit";
      note.textContent = "Illustrative shape only. Source values and units were not recorded; do not read bar height as a measurement.";
      chart.after(note);
    });
  }

  function bindOversight() {
    document.querySelectorAll("[data-oversight-agent]").forEach(function (button) {
      button.addEventListener("click", function () {
        document.querySelectorAll("[data-oversight-agent]").forEach(function (candidate) {
          candidate.setAttribute("aria-pressed", String(candidate === button));
        });
        ["name", "role", "summary", "coverage", "steward", "knowledge", "approval"].forEach(function (key) {
          var target = document.querySelector("[data-oversight-" + key + "]");
          if (target) target.textContent = button.getAttribute("data-" + key) || "-";
        });
        var status = document.querySelector("[data-oversight-status]");
        if (status) {
          status.textContent = button.getAttribute("data-status") || "Review";
          status.className = "fg-badge " + (button.getAttribute("data-tone") || "");
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindSelectors();
    bindCopyButtons();
    bindRows();
    bindStaticForms();
    bindOversight();
    explainIllustrativeCharts();
  });
})();
