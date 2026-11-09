"""WARD Live: interactive web accessibility audit against the civil society census.

Run:  uvicorn app:app --host 0.0.0.0 --port 8000
"""
import asyncio
import collections
import os
import time

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from wardlive.engine import build_report, tasks_csv, census_histogram, CENSUS, COUNTRY_CODES
from wardlive.knowledge import CRITERIA
from wardlive import study

HERE = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title="WARD Live", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

# Recent reports kept in memory for CSV export and the session log shown at the stand.
REPORTS = collections.OrderedDict()
MAX_REPORTS = 500
AUDIT_SEMAPHORE = asyncio.Semaphore(4)


class AuditRequest(BaseModel):
    url: str
    country: str = "all"


def _remember(report):
    REPORTS[report["id"]] = report
    while len(REPORTS) > MAX_REPORTS:
        REPORTS.popitem(last=False)


@app.post("/api/audit")
async def audit(req: AuditRequest):
    url = req.url.strip()
    if not url or " " in url or len(url) > 2000:
        raise HTTPException(400, "Please enter one web address.")
    country = req.country if req.country in COUNTRY_CODES else "all"
    async with AUDIT_SEMAPHORE:
        t0 = time.time()
        report = await asyncio.to_thread(build_report, url, country)
        report["timing"]["total_ms"] = int((time.time() - t0) * 1000)
    _remember(report)
    return report


@app.get("/api/report/{report_id}")
def get_report(report_id: str):
    r = REPORTS.get(report_id)
    if not r:
        raise HTTPException(404, "Report not found or expired.")
    return r


@app.get("/api/report/{report_id}/tasks.csv")
def get_tasks_csv(report_id: str):
    r = REPORTS.get(report_id)
    if not r or r["status"] != "tested":
        raise HTTPException(404, "Report not found.")
    study.register_units(r)
    return PlainTextResponse(tasks_csv(r), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="ward_tasks_{report_id}.csv"'})


@app.get("/api/census")
def census(version: str = Query("21", pattern="^(21|22)$"), country: str = "all"):
    country = country if country in COUNTRY_CODES else "all"
    h = census_histogram(version, country)
    h["country"] = country
    h["country_name"] = COUNTRY_CODES[country]
    h["meta"] = CENSUS["meta"]
    h["countries"] = {k: {"name": v["name"], "audited": v["audited"], "frame": v["frame"]} for k, v in CENSUS["countries"].items()}
    return h


@app.get("/api/criteria")
def criteria():
    out = {}
    for c, k in CRITERIA.items():
        cen = CENSUS["criteria"].get(c, {})
        out[c] = {**k, "census_share_pct": cen.get("share_pct"), "census_instances": cen.get("instances")}
    return out


@app.get("/api/session")
def session_log():
    """What has been audited at this stand so far (for the demo screen)."""
    items = []
    for r in reversed(REPORTS.values()):
        items.append({"id": r["id"], "url": r.get("final_url") or r["requested_url"], "status": r["status"],
                      "v21": r.get("versions", {}).get("wcag21", {}).get("violations"),
                      "v22": r.get("versions", {}).get("wcag22", {}).get("violations"),
                      "at": r["audited_at"]})
    return {"count": len(items), "items": items[:30]}


class ContributorRecord(BaseModel):
    task_id: str
    contributor: str = ""
    minutes: float | None = None
    completed: bool = False
    clear_to_start: bool = False
    notes: str = ""


class VerifierRecord(BaseModel):
    task_id: str
    passed_first_pass: bool = False
    notes: str = ""


@app.post("/api/study/contributor")
def study_contributor(rec: ContributorRecord):
    if not rec.task_id.strip():
        raise HTTPException(400, "Task id is required.")
    return study.record("contributor", rec.model_dump())


@app.post("/api/study/verifier")
def study_verifier(rec: VerifierRecord):
    if not rec.task_id.strip():
        raise HTTPException(400, "Task id is required.")
    return study.record("verifier", rec.model_dump())


@app.get("/api/study/summary")
def study_summary():
    return study.summary()


@app.get("/api/study/log.csv")
def study_log_csv():
    return PlainTextResponse(study.export_csv(), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="ward_study_log.csv"'})


@app.get("/study")
def study_page():
    return FileResponse(os.path.join(HERE, "static", "study.html"))


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "static", "index.html"))


app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
