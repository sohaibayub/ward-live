# WARD Live

Interactive front end for WARD, the static web accessibility checker used for the
five-country civil society census. Paste a web address and the page is fetched once,
evaluated under WCAG 2.1 AA and WCAG 2.2 AA side by side, each violation is explained
with the element it concerns, the result is placed in the census distribution of
135,604 audited homepages, and the findings are turned into remediation task units
following the UD26 crowdsourcing taxonomy (non-technical and technical queues), with
CSV export.

## Run

    pip install -r requirements.txt
    uvicorn app:app --host 0.0.0.0 --port 8000

Open http://localhost:8000. A URL can be preloaded with ?url=https://example.org.

## Layout

    app.py                  FastAPI application and API
    wardlive/checker.py     WARD rule set with element capture (same conditions as the census tool)
    wardlive/knowledge.py   plain-language explanations and task templates per criterion
    wardlive/engine.py      report builder: versions, census placement, task units
    census_summary.json     compact distribution built from the published results
    build_census.py         rebuilds census_summary.json from the replication package
    test_parity.py          checks the demo checker against the census checker on live pages
    static/                 front end (no external dependencies, works offline)
    extension/              browser extension (Manifest V3) that audits the active tab through the server

## Rebuild the census summary

    git clone https://github.com/sohaibayub/cso-web-accessibility
    python build_census.py cso-web-accessibility/results census_summary.json

## Parity check

    python test_parity.py cso-web-accessibility https://example.org https://another.example

## API

    POST /api/audit                 {"url": "...", "country": "all|irl|uk|aus|nz|usa"}
    GET  /api/report/{id}           the stored report
    GET  /api/report/{id}/tasks.csv task units as CSV
    GET  /api/census?version=21|22&country=...
    GET  /api/criteria              explanations for all 22 criteria with census prevalence
    GET  /api/session               what has been audited at this instance

## Notes

Static analysis detects a subset of real violations; counts are floors. Colour
contrast and anything needing a rendered page are outside the tool. Fetching uses
verify=False, as the census did, so sites with broken certificates can still be audited.
Up to four audits run concurrently; results are kept in memory (last 500).

## Contributor study

Downloading a report's task CSV registers its units as handed out (data/study_units.jsonl).
The CSV carries empty columns for the contributor to fill in by hand (minutes spent,
completed, clear enough to start, notes). The page at /study takes the same information
through two short forms, one for contributors and one for the verifier, appends each
record to data/study_log.jsonl (latest record per task wins) and shows the summary the
paper reports: units by queue and sites, contributors, completion rate, mean and median
minutes per completed unit, share of units judged clear enough to begin without asking,
first-pass verification rate, and the units returned for revision with the reason.
/api/study/log.csv exports the joined log. Delete the data folder to start a study afresh.

## Browser extension

extension/ is a Manifest V3 extension for Chrome, Edge and Brave. Install it
from the Chrome Web Store (https://chromewebstore.google.com/detail/ward-live/plpodadcdleceoikdbmindckienlebjn), or unpacked
from chrome://extensions with Developer mode on. It reads the active tab's address,
asks the WARD Live server to audit it (so counts stay comparable with the census), shows
the 2.1 and 2.2 results, the census placement and the violated criteria with fixes,
outlines the offending elements on the page, and opens the full report. The server
address is the DEFAULT constant in extension/popup.js.
