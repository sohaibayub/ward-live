(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function radio(name) { var r = document.querySelector('input[name="' + name + '"]:checked'); return r ? r.value === "yes" : false; }

  function post(url, body, statusEl, okMsg) {
    return fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || r.statusText); }); return r.json(); })
      .then(function () { statusEl.textContent = okMsg; loadSummary(); })
      .catch(function (e) { statusEl.textContent = "Not saved: " + e.message; });
  }

  $("contrib-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var m = $("c-min").value;
    post("/api/study/contributor", {
      task_id: $("c-task").value.trim(), contributor: $("c-name").value.trim(),
      minutes: m === "" ? null : parseFloat(m), completed: radio("completed"), clear_to_start: radio("clear"),
      notes: $("c-notes").value.trim()
    }, $("c-status"), "Saved for " + $("c-task").value.trim() + ".").then(function () { $("c-task").value = ""; $("c-min").value = ""; $("c-notes").value = ""; $("c-task").focus(); });
  });

  $("verif-form").addEventListener("submit", function (e) {
    e.preventDefault();
    post("/api/study/verifier", { task_id: $("v-task").value.trim(), passed_first_pass: radio("passed"), notes: $("v-notes").value.trim() },
      $("v-status"), "Saved for " + $("v-task").value.trim() + ".").then(function () { $("v-task").value = ""; $("v-notes").value = ""; $("v-task").focus(); });
  });

  $("refresh").addEventListener("click", loadSummary);

  function row(k, v) { return "<tr><th scope=\"row\">" + esc(k) + "</th><td>" + esc(v == null ? "not yet" : v) + "</td></tr>"; }
  function pctText(n, d, p) { return d ? n + " of " + d + " (" + p + "%)" : "not yet"; }

  function loadSummary() {
    fetch("/api/study/summary").then(function (r) { return r.json(); }).then(function (s) {
      var q = s.units_by_queue || {};
      $("sum-body").innerHTML =
        row("Task units handed out", s.units_registered + " (" + (q["non-technical"] || 0) + " non-technical, " + (q["technical"] || 0) + " technical) across " + s.sites + " sites") +
        row("Contributors", s.contributors) +
        row("Units with a contributor record", s.contributor_records) +
        row("Completed", pctText(s.completed, s.contributor_records, s.completion_pct)) +
        row("Mean minutes per completed unit", s.mean_minutes == null ? null : s.mean_minutes + " (median " + s.median_minutes + ")") +
        row("Enough information to begin without asking", pctText(s.clear_to_start, s.contributor_records, s.clear_to_start_pct)) +
        row("Passed first-pass verification", pctText(s.first_pass_passed, s.verified, s.first_pass_pct));
      $("sum-note").textContent = s.unknown_task_ids && s.unknown_task_ids.length
        ? "Records exist for task ids that were never handed out: " + s.unknown_task_ids.join(", ") + ". Check for typing errors."
        : "";
      if (s.revisions && s.revisions.length) {
        $("rev-card").hidden = false;
        $("rev-list").innerHTML = s.revisions.map(function (r) { return "<li>" + esc(r.task_id) + (r.notes ? ": " + esc(r.notes) : "") + "</li>"; }).join("");
      } else { $("rev-card").hidden = true; }
    });
  }
  loadSummary();
})();
