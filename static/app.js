(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var report = null;
  var censusCache = {};

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmt(n) { return Number(n).toLocaleString("en-IE"); }
  function plural(n, s) { return n + " " + s + (n === 1 ? "" : "s"); }

  $("audit-form").addEventListener("submit", function (e) {
    e.preventDefault();
    runAudit($("url").value.trim(), $("country").value);
  });

  document.querySelectorAll('input[name="cv"]').forEach(function (r) {
    r.addEventListener("change", function () { if (report) renderCensus(); });
  });

  function setStatus(msg, busy) {
    $("status").textContent = msg;
    $("go").disabled = !!busy;
  }

  function runAudit(url, country) {
    if (!url) return;
    setStatus("Fetching " + url + " and evaluating against WCAG 2.1 and 2.2 ...", true);
    $("results").hidden = true;
    fetch("/api/audit", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url, country: country })
    }).then(function (r) {
      if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || r.statusText); });
      return r.json();
    }).then(function (rep) {
      report = rep;
      render();
      setStatus(rep.status === "tested"
        ? "Done in " + (rep.timing.total_ms / 1000).toFixed(1) + " s."
        : "Could not reach the site.", false);
      loadSession();
    }).catch(function (err) {
      setStatus("Audit failed: " + err.message, false);
    });
  }

  function render() {
    var r = report;
    $("results").hidden = false;
    $("r-url").textContent = r.final_url || r.requested_url;
    $("r-meta").textContent = (r.page_title ? "Page title: " + r.page_title + ". " : "") +
      "Audited " + r.audited_at + ". Fetch " + r.timing.fetch_ms + " ms, analysis " + (r.timing.analyze_ms || 0) + " ms. " +
      (r.country_detected ? "Compared with " + (/^United/.test(r.country_name) ? "the " : "") + r.country_name + ", " + r.country_reason + "; change the comparison above and run again if you prefer another." : "Compared with " + r.country_name + ".");
    if (r.status !== "tested") {
      $("r-body").hidden = true;
      $("r-error").hidden = false;
      $("r-error").innerHTML = "<p><strong>Unreachable: " + esc(r.error) + "</strong></p><p>" + esc(r.unreachable_note) + "</p>" +
        "<p class=\"muted\">Attempts: " + r.attempts.map(function (a) { return esc(a.url) + " (" + esc(a.status || a.error) + ")"; }).join("; ") + "</p>";
      $("results").scrollIntoView({ behavior: "smooth" });
      return;
    }
    $("r-error").hidden = true;
    $("r-body").hidden = false;

    var v21 = r.versions.wcag21, v22 = r.versions.wcag22, tr = r.versions.transition;
    fillVersion("v21", v21); fillVersion("v22", v22);
    var t = [];
    if (tr.added_by_22) t.push(plural(tr.added_by_22, "violation") + " added by the new criteria (" + tr.added_criteria.join(", ") + ")");
    if (tr.removed_by_22) t.push(plural(tr.removed_by_22, "duplicate-ID violation") + " no longer counted because 4.1.1 was removed");
    $("transition").textContent = t.length
      ? "Same page, same fetch. Under 2.2: " + t.join("; ") + ". Net change " + (tr.net_change > 0 ? "+" : "") + tr.net_change + "."
      : "Same page, same fetch. Nothing in this page is affected by the move from 2.1 to 2.2.";

    renderCensus();
    renderCriteria();
    renderTasks();
    $("csv-link").href = "/api/report/" + r.id + "/tasks.csv";
    $("results").scrollIntoView({ behavior: "smooth" });
  }

  function fillVersion(p, v) {
    $(p + "-n").textContent = fmt(v.violations);
    $(p + "-a").textContent = fmt(v.level_a);
    $(p + "-aa").textContent = fmt(v.level_aa);
    $(p + "-pass").textContent = v.criteria_passed + " of " + v.criteria_evaluated;
    $(p + "-pct").textContent = v.compliance_pct + "%";
  }

  function renderCensus() {
    var ver = document.querySelector('input[name="cv"]:checked').value;
    var c = report.census[ver === "21" ? "wcag21" : "wcag22"];
    var key = ver + ":" + report.country;
    var p = censusCache[key] ? Promise.resolve(censusCache[key])
      : fetch("/api/census?version=" + ver + "&country=" + encodeURIComponent(report.country)).then(function (r) { return r.json(); }).then(function (h) { censusCache[key] = h; return h; });
    p.then(function (h) {
      var n = c.site_violations;
      var where = c.country === "all" ? "across all five countries" : "in " + (/^United/.test(c.country_name) ? "the " : "") + c.country_name;
      var text = "Under WCAG " + c.version + " this homepage has " + plural(n, "detectable violation") + ". ";
      if (n === 0) {
        text += "Only " + c.zero_share_pct + "% of the " + fmt(c.audited_sites) + " audited sites " + where + " reached zero. ";
      } else {
        text += "Across the " + fmt(c.audited_sites) + " audited sites " + where + ", " + c.pct_sites_with_fewer + "% had fewer violations and " + c.pct_sites_with_more + "% had more. ";
      }
      text += "The census median is " + c.median + ", the mean " + c.mean + ", and one site in ten has " + c.p90 + " or more.";
      $("census-text").textContent = text;
      drawHist(h, n, c);
    });
  }

  function drawHist(h, n, c) {
    var svg = $("hist");
    var W = 820, H = 260, L = 48, R = 12, T = 18, B = 44;
    var bins = h.shares, cap = bins.length - 1;
    var max = Math.max.apply(null, bins);
    var bw = (W - L - R) / bins.length;
    var out = [];
    out.push('<line class="axis" x1="' + L + '" y1="' + (H - B) + '" x2="' + (W - R) + '" y2="' + (H - B) + '"/>');
    out.push('<line class="axis" x1="' + L + '" y1="' + T + '" x2="' + L + '" y2="' + (H - B) + '"/>');
    var ticks = [0, Math.round(max / 2 * 10) / 10, Math.round(max * 10) / 10];
    ticks.forEach(function (tv) {
      var y = H - B - (tv / max) * (H - B - T);
      out.push('<text class="tick" x="' + (L - 6) + '" y="' + (y + 4) + '" text-anchor="end">' + tv + '%</text>');
    });
    var me = Math.min(n, cap);
    for (var i = 0; i < bins.length; i++) {
      var bh = (bins[i] / max) * (H - B - T);
      out.push('<rect class="bar' + (i === me ? " me" : "") + '" x="' + (L + i * bw + 1) + '" y="' + (H - B - bh) + '" width="' + (bw - 2) + '" height="' + bh + '"><title>' + h.labels[i] + ' violations: ' + fmt(h.counts[i]) + ' sites (' + bins[i] + '%)</title></rect>');
      if (i % 5 === 0 || i === cap) {
        out.push('<text class="tick" x="' + (L + i * bw + bw / 2) + '" y="' + (H - B + 16) + '" text-anchor="middle">' + h.labels[i] + '</text>');
      }
    }
    var mx = L + me * bw + bw / 2;
    out.push('<line class="marker" x1="' + mx + '" y1="' + (T - 4) + '" x2="' + mx + '" y2="' + (H - B) + '"/>');
    var anchor = me > cap * 0.75 ? "end" : "start";
    out.push('<text class="marker-label" x="' + (mx + (anchor === "end" ? -6 : 6)) + '" y="' + (T + 6) + '" text-anchor="' + anchor + '">this site: ' + n + '</text>');
    out.push('<text class="tick" x="' + ((L + W - R) / 2) + '" y="' + (H - 6) + '" text-anchor="middle">violations per homepage, WCAG ' + c.version + ', ' + esc(c.country_name) + '</text>');
    svg.innerHTML = svg.querySelector("title").outerHTML + svg.querySelector("desc").outerHTML + out.join("");
    $("hist-desc").textContent = "Histogram of violations per homepage for " + fmt(c.audited_sites) + " sites. This site, with " + n + ", is marked. Median " + c.median + ".";
    $("hist-cap").textContent = "Share of the " + fmt(h.total) + " audited homepages in " + c.country_name + " by number of detectable violations under WCAG " + c.version + ". The last bar groups " + cap + " or more. Source: cso-web-accessibility dataset.";
  }

  function renderCriteria() {
    var groups = report.criteria;
    var box = $("criteria");
    if (!groups.length) {
      box.innerHTML = '<p class="card"><span class="badge ok">Clean</span> No violation detected by any of the 22 machine-checkable rules. Colour contrast, focus visibility and anything needing a rendered page are not covered.</p>';
      $("crit-summary").textContent = "";
      return;
    }
    $("crit-summary").textContent = (groups.length === 1 ? "1 criterion" : groups.length + " criteria") + " violated, " + plural(report.tasks.total_instances, "instance") + " in total. Level A failures first.";
    box.innerHTML = groups.map(function (g) {
      var ver = g.in_21 && g.in_22 ? "2.1 and 2.2" : g.in_21 ? "2.1 only" : "2.2 only";
      var cen = g.census_share_pct != null ? "Found on " + g.census_share_pct + "% of census sites." : "";
      return '<details class="crit">' +
        '<summary><span class="badge ' + g.level + '">Level ' + g.level + '</span>' +
        '<span class="title">' + esc(g.criterion) + ' ' + esc(g.name) + '</span>' +
        '<span class="n">' + plural(g.count, "instance") + '</span>' +
        '<span class="badge v">WCAG ' + ver + '</span>' +
        (cen ? '<span class="n">' + esc(cen) + '</span>' : "") +
        '</summary><div class="body"><dl>' +
        '<dt>What was detected</dt><dd>' + esc(g.detects) + '</dd>' +
        '<dt>Who it affects</dt><dd>' + esc(g.affects) + '</dd>' +
        '<dt>How to fix it</dt><dd>' + esc(g.fix) + ' <a href="' + esc(g.w3c) + '">Understanding ' + esc(g.criterion) + ' at W3C</a></dd>' +
        '<dt>Where on the page</dt><dd><ul class="inst">' +
        g.instances.map(function (x) {
          return '<li>' + esc(x.issue) + (x.locator ? ' <span class="loc">' + esc(x.locator) + '</span>' : "") +
            (x.element ? '<code>' + esc(x.element) + '</code>' : "") + '</li>';
        }).join("") + (g.count > g.instances.length ? '<li class="muted">and ' + (g.count - g.instances.length) + ' more</li>' : "") +
        '</ul></dd></dl></div></details>';
    }).join("");
  }

  function taskCard(t) {
    return '<article class="task"><div class="tid">' + esc(t.task_id) + ' <span class="badge ' + t.level + '">Level ' + t.level + '</span></div>' +
      '<h5>' + esc(t.criterion) + ' ' + esc(t.name) + ': ' + plural(t.instances, "instance") + '</h5><dl>' +
      '<dt>Problem, as given to the contributor</dt><dd>' + esc(t.problem) + '</dd>' +
      '<dt>What to do</dt><dd>' + esc(t.fix) + '</dd>' +
      '<dt>Acceptance criteria</dt><dd>' + esc(t.acceptance) + '</dd>' +
      '<dt>Output and verification</dt><dd>' + esc(t.output) + ' ' + esc(t.verification) + '</dd>' +
      '<dt>Estimated effort</dt><dd>about ' + t.est_minutes + ' minutes</dd>' +
      '</dl></article>';
  }

  function renderTasks() {
    var nt = report.tasks.non_technical, te = report.tasks.technical;
    $("q-nt-n").textContent = "(" + plural(nt.length, "unit") + ")";
    $("q-t-n").textContent = "(" + plural(te.length, "unit") + ")";
    $("q-nt").innerHTML = nt.length ? nt.map(taskCard).join("") : '<p class="empty">Nothing for content editors.</p>';
    $("q-t").innerHTML = te.length ? te.map(taskCard).join("") : '<p class="empty">Nothing for developers.</p>';
  }

  function loadSession() {
    fetch("/api/session").then(function (r) { return r.json(); }).then(function (s) {
      if (!s.count) return;
      $("session").hidden = false;
      $("session-list").innerHTML = s.items.map(function (it) {
        return "<li>" + esc(it.url) + ": " + (it.status === "tested" ? it.v21 + " under 2.1, " + it.v22 + " under 2.2" : "unreachable") + " <span class=\"muted\">(" + esc(it.at) + ")</span></li>";
      }).join("");
    });
  }

  var q = new URLSearchParams(location.search).get("url");
  if (q) { $("url").value = q; runAudit(q, $("country").value); }
  loadSession();
})();
