# WARD Live browser extension

Audits the page in the active tab against WCAG 2.1 AA and WCAG 2.2 AA through a
running WARD Live server, shows where the page sits in the census of 135,604 civil
society homepages, lists the violated criteria with the fix for each, outlines the
offending elements on the page, and opens the full report with the remediation backlog.

Install from the Chrome Web Store: https://chromewebstore.google.com/detail/ward-live/plpodadcdleceoikdbmindckienlebjn

Install unpacked (Chrome, Edge, Brave): open chrome://extensions, turn on Developer mode,
choose "Load unpacked" and select this folder. The popup calls the hosted WARD Live
server; to use a local one (uvicorn app:app --port 8000) change DEFAULT in popup.js.

The server fetches the page itself with the census tool's rule set, so the counts are
comparable with the published dataset. Outlining matches the server's element locators
against the live DOM; elements created by scripts after load may not be found.
