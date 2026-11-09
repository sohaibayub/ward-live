"""Contributor study log: which task units were handed out, what contributors
and verifiers recorded about them, and the summary figures.

Records are appended to JSONL files under data/. The latest record per task
wins for each role, so a correction is just a new entry."""

import json
import os
import statistics
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("WARD_DATA", os.path.join(HERE, "data"))
UNITS = os.path.join(DATA, "study_units.jsonl")
LOG = os.path.join(DATA, "study_log.jsonl")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _append(path, rec):
    os.makedirs(DATA, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _read(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def register_units(report):
    """Called when a report's task CSV is exported, which is how units are handed out."""
    for q in ("non_technical", "technical"):
        for t in report["tasks"][q]:
            _append(UNITS, {"task_id": t["task_id"], "queue": t["queue"], "criterion": t["criterion"],
                            "level": t["level"], "page_url": t["page_url"], "instances": t["instances"],
                            "report_id": report["id"], "exported_at": _now()})


def record(role, payload):
    rec = {"role": role, "recorded_at": _now()}
    rec.update(payload)
    _append(LOG, rec)
    return rec


def units():
    seen = {}
    for u in _read(UNITS):
        seen[u["task_id"]] = u
    return seen


def summary():
    us = units()
    contrib, verif = {}, {}
    for r in _read(LOG):
        if r.get("role") == "contributor":
            contrib[r["task_id"]] = r
        elif r.get("role") == "verifier":
            verif[r["task_id"]] = r
    known = set(us)
    completed = [r for r in contrib.values() if r.get("completed")]
    minutes = [float(r["minutes"]) for r in completed if r.get("minutes") not in (None, "")]
    clear_yes = sum(1 for r in contrib.values() if r.get("clear_to_start"))
    verified = [r for r in verif.values() if r["task_id"] in {c["task_id"] for c in completed}] or list(verif.values())
    passed = sum(1 for r in verified if r.get("passed_first_pass"))
    contributors = {r.get("contributor") for r in contrib.values() if r.get("contributor")}
    by_queue = {"non-technical": 0, "technical": 0}
    for u in us.values():
        by_queue[u["queue"]] = by_queue.get(u["queue"], 0) + 1

    def pct(a, b):
        return round(100.0 * a / b, 1) if b else None

    return {
        "units_registered": len(us), "units_by_queue": by_queue,
        "sites": len({u["page_url"] for u in us.values()}),
        "contributors": len(contributors),
        "contributor_records": len(contrib),
        "unknown_task_ids": sorted((set(contrib) | set(verif)) - known),
        "completed": len(completed), "completion_pct": pct(len(completed), len(contrib)),
        "mean_minutes": round(statistics.mean(minutes), 1) if minutes else None,
        "median_minutes": round(statistics.median(minutes), 1) if minutes else None,
        "clear_to_start": clear_yes, "clear_to_start_pct": pct(clear_yes, len(contrib)),
        "verified": len(verified), "first_pass_passed": passed, "first_pass_pct": pct(passed, len(verified)),
        "revisions": [r for r in verified if not r.get("passed_first_pass")],
    }


def export_csv():
    import csv
    import io
    us = units()
    rows = {}
    for r in _read(LOG):
        rows.setdefault(r["task_id"], {}).update({f"{r['role']}_{k}": v for k, v in r.items() if k not in ("role", "task_id")})
    buf = io.StringIO()
    cols = ["task_id", "queue", "criterion", "level", "page_url", "contributor_contributor", "contributor_minutes",
            "contributor_completed", "contributor_clear_to_start", "contributor_notes", "contributor_recorded_at",
            "verifier_passed_first_pass", "verifier_notes", "verifier_recorded_at"]
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for tid in sorted(set(us) | set(rows)):
        u = us.get(tid, {})
        w.writerow({"task_id": tid, "queue": u.get("queue"), "criterion": u.get("criterion"),
                    "level": u.get("level"), "page_url": u.get("page_url"), **rows.get(tid, {})})
    return buf.getvalue()
