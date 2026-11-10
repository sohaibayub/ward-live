(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var DEFAULT = "https://ward-live-hxcsdha3f8fteqgq.norwayeast-01.azurewebsites.net";
  var report = null, tab = null, server = DEFAULT;

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function plural(n, s) { return n + " " + s + (n === 1 ? "" : "s"); }

  // The audit server is fixed in DEFAULT. Only the country choice is remembered.
  $("help").href = server + "/#help";
  chrome.storage.sync.get({ country: "auto" }, function (o) { $("country").value = o.country || "auto"; });
  $("country").addEventListener("change", function () { chrome.storage.sync.set({ country: $("country").value }); });

  function setTab(t) {
    tab = t;
    var ok = tab && /^https?:/.test(tab.url || "");
    $("page").textContent = ok ? tab.url : "Open a web page to audit it.";
    $("audit").disabled = !ok;
  }
  chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
    if (tabs[0] && /^https?:/.test(tabs[0].url || "")) return setTab(tabs[0]);
    // The popup itself may be the active tab (for example when opened in a tab); fall back to the most recent web page.
    chrome.tabs.query({ url: ["http://*/*", "https://*/*"] }, function (all) {
      all.sort(function (a, b) { return (b.lastAccessed || 0) - (a.lastAccessed || 0); });
      setTab(all[0] || tabs[0]);
    });
  });

  $("audit").addEventListener("click", function () {
    $("audit").disabled = true; $("status").textContent = "Fetching and evaluating under WCAG 2.1 and 2.2 ..."; $("result").hidden = true;
    fetch(server + "/api/audit", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url: tab.url, country: $("country").value }) })
      .then(function (r) { if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || r.statusText); }); return r.json(); })
      .then(function (rep) { report = rep; render(); })
      .catch(function (e) { $("status").textContent = "The audit service could not be reached. Please try again in a moment. (" + e.message + ")"; })
      .then(function () { $("audit").disabled = false; });
  });

  function render() {
    var r = report;
    if (r.status !== "tested") { $("status").textContent = "This page could not be fetched for auditing: " + r.error; return; }
    $("status").textContent = "Done in " + (r.timing.total_ms / 1000).toFixed(1) + " s.";
    var v21 = r.versions.wcag21, v22 = r.versions.wcag22, tr = r.versions.transition;
    $("n21").textContent = v21.violations; $("s21").textContent = v21.criteria_passed + " of " + v21.criteria_evaluated + " criteria passed";
    $("n22").textContent = v22.violations; $("s22").textContent = v22.criteria_passed + " of " + v22.criteria_evaluated + " criteria passed";
    var t = [];
    if (tr.added_by_22) t.push(tr.added_by_22 + " added by " + tr.added_criteria.join(", "));
    if (tr.removed_by_22) t.push(tr.removed_by_22 + " dropped with 4.1.1");
    $("transition").textContent = t.length ? "2.1 to 2.2: " + t.join("; ") + "." : "Nothing on this page changes between 2.1 and 2.2.";
    var c = r.census.wcag21;
    var where = c.country === "all" ? "across all five countries" : "in " + (/^United/.test(c.country_name) ? "the " : "") + c.country_name;
    var sentence = c.site_violations === 0
      ? "No detectable violation. Only " + c.zero_share_pct + "% of " + c.audited_sites.toLocaleString() + " audited sites " + where + " reached that."
      : "Of " + c.audited_sites.toLocaleString() + " audited sites " + where + ", " + c.pct_sites_with_fewer + "% had fewer violations and " + c.pct_sites_with_more + "% had more (median " + c.median + ").";
    if (r.country_detected) sentence += " Compared with " + (/^United/.test(r.country_name) ? "the " : "") + r.country_name + " " + r.country_reason + ".";
    $("census").textContent = sentence;
    $("crit").innerHTML = r.criteria.length ? r.criteria.map(function (g) {
      return "<li><span class=\"badge " + g.level + "\">" + g.level + "</span><span><strong>" + esc(g.criterion) + " " + esc(g.name) + "</strong>, " + plural(g.count, "instance") + ". " + esc(g.fix) + "</span></li>";
    }).join("") : "<li>No violation detected by the 22 machine-checkable rules.</li>";
    $("full").href = server + "/?url=" + encodeURIComponent(tab.url);
    $("result").hidden = false;
  }

  // Outline offending elements on the live page using the locators from the report.
  function outline(items) {
    var style = document.getElementById("ward-live-style");
    if (!style) { style = document.createElement("style"); style.id = "ward-live-style"; document.documentElement.appendChild(style); }
    style.textContent = "[data-ward-live]{outline:3px solid #8a1c1c !important;outline-offset:2px !important;} [data-ward-live]::before{content:attr(data-ward-live);position:absolute;background:#8a1c1c;color:#fff;font:700 12px/1.4 system-ui,sans-serif;padding:0 6px;border-radius:3px;z-index:2147483647;transform:translateY(-100%);}";
    var matched = 0, tried = 0;
    items.forEach(function (it) {
      tried++;
      var els = [];
      try { if (it.locator) els = Array.prototype.slice.call(document.querySelectorAll(it.locator)); } catch (e) { els = []; }
      if (!els.length && it.criterion === "1.1.1") { els = Array.prototype.filter.call(document.querySelectorAll("img"), function (im) { return !im.hasAttribute("alt") && im.getAttribute("role") !== "presentation"; }); }
      if (!els.length && it.criterion === "3.1.1") { els = [document.documentElement]; }
      els.slice(0, 50).forEach(function (el) { el.setAttribute("data-ward-live", it.criterion + " " + it.issue); matched++; });
    });
    return { tried: tried, matched: matched };
  }
  function clearOutline() {
    document.querySelectorAll("[data-ward-live]").forEach(function (el) { el.removeAttribute("data-ward-live"); });
    var s = document.getElementById("ward-live-style"); if (s) s.remove();
  }

  $("highlight").addEventListener("click", function () {
    if (!report) return;
    var items = [];
    report.criteria.forEach(function (g) { g.instances.forEach(function (x) { items.push({ criterion: g.criterion, issue: x.issue, locator: x.locator }); }); });
    chrome.scripting.executeScript({ target: { tabId: tab.id }, func: outline, args: [items] }, function (res) {
      if (chrome.runtime.lastError || !res || !res[0]) { $("hl-status").textContent = "Could not outline on this page" + (chrome.runtime.lastError ? ": " + chrome.runtime.lastError.message : "") + "."; return; }
      var o = res[0].result;
      $("hl-status").textContent = o.matched + " element" + (o.matched === 1 ? "" : "s") + " outlined. The audit used the HTML as served, so elements built by scripts after load may not be found.";
    });
  });
  $("clear").addEventListener("click", function () {
    chrome.scripting.executeScript({ target: { tabId: tab.id }, func: clearOutline }, function () { $("hl-status").textContent = "Outlines cleared."; });
  });
})();
