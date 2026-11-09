"""Turns a WARD result into the demo report: two WCAG versions side by side,
explained violations, census placement, and UD26-style task units."""

import collections
import json
import os
import uuid
from datetime import datetime, timezone

from .checker import WARDLive, NEW22, REMOVED22, LEVEL_A, CRITERIA_21, CRITERIA_22
from .knowledge import info

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CENSUS_PATH = os.environ.get("WARD_CENSUS", os.path.join(HERE, "census_summary.json"))

with open(CENSUS_PATH, encoding="utf-8") as f:
    CENSUS = json.load(f)

COUNTRY_CODES = {"uk": "United Kingdom", "aus": "Australia", "usa": "United States",
                 "nz": "New Zealand", "irl": "Ireland", "all": "All five countries"}


def _sort_key(c):
    return [int(p) for p in c.split(".")]


def census_placement(n, version="21", country="all"):
    """Where a site with n violations sits in the census distribution."""
    block = CENSUS["countries"].get(country) or CENSUS["all"]
    hist = block["hist" + version]
    total = sum(hist.values())
    below = sum(v for k, v in hist.items() if int(k) < n)
    equal = hist.get(str(min(n, 200)), 0)
    # Share of census sites with fewer violations than this site (lower is better for the site).
    pct_better_than_site = round(100 * below / total, 1)
    pct_worse_than_site = round(100 * (total - below - equal) / total, 1)
    # Summary stats of the distribution, from the histogram
    cum = 0
    median = None
    p90 = None
    for k in sorted(hist, key=int):
        cum += hist[k]
        if median is None and cum >= total / 2:
            median = int(k)
        if p90 is None and cum >= total * 0.9:
            p90 = int(k)
    mean = block["sum" + version] / total if total else 0
    zero = hist.get("0", 0)
    return {
        "country": country, "country_name": block["name"], "version": "2.1" if version == "21" else "2.2",
        "audited_sites": total, "site_violations": n,
        "pct_sites_with_fewer": pct_better_than_site,
        "pct_sites_with_more": pct_worse_than_site,
        "median": median, "p90": p90, "mean": round(mean, 2), "zero_share_pct": round(100 * zero / total, 2),
    }


def census_histogram(version="21", country="all", cap=40):
    """Binned histogram for the chart: 0..cap-1 individually, then cap+."""
    block = CENSUS["countries"].get(country) or CENSUS["all"]
    hist = block["hist" + version]
    total = sum(hist.values())
    bins = [0] * (cap + 1)
    for k, v in hist.items():
        bins[min(int(k), cap)] += v
    return {"labels": [str(i) for i in range(cap)] + [f"{cap}+"],
            "counts": bins, "shares": [round(100 * b / total, 3) for b in bins], "total": total}


def build_report(url, country="all", timeout=15):
    checker = WARDLive(timeout=timeout)
    raw = checker.analyze(url)
    report = {
        "id": uuid.uuid4().hex[:12],
        "requested_url": url,
        "final_url": raw.get("final_url"),
        "status": raw["status"],
        "error": raw.get("error"),
        "attempts": raw.get("attempts", []),
        "timing": {"fetch_ms": raw.get("fetch_ms"), "analyze_ms": raw.get("analyze_ms")},
        "audited_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "country": country,
    }
    if raw["status"] != "tested":
        report["unreachable_note"] = (
            "The census could not reach 15.9 percent of recorded civil society websites. "
            "This site joins that group for now; the error is recorded with its cause."
        )
        return report

    ext = raw["issues_extended"]
    report["page_title"] = raw.get("page_title", "")
    report["html_bytes"] = raw.get("html_bytes")

    set21 = [i for i in ext if i["criterion"] not in NEW22]
    set22 = [i for i in ext if i["criterion"] not in REMOVED22]

    def version_block(issues, criteria_set, label):
        violated = {i["criterion"] for i in issues}
        passed = sorted(criteria_set - violated, key=_sort_key)
        level_a = sum(1 for i in issues if i["level"] == "A")
        return {
            "label": label,
            "violations": len(issues),
            "level_a": level_a,
            "level_aa": len(issues) - level_a,
            "criteria_evaluated": len(criteria_set),
            "criteria_violated": len(violated),
            "criteria_passed": len(passed),
            "passed_list": passed,
            "compliance_pct": round(100 * len(passed) / len(criteria_set), 1),
            "fails_level_a": level_a > 0,
            "clean": len(issues) == 0,
        }

    v21 = version_block(set21, CRITERIA_21, "WCAG 2.1 AA")
    v22 = version_block(set22, CRITERIA_22, "WCAG 2.2 AA")
    added = [i for i in ext if i["criterion"] in NEW22]
    removed = [i for i in ext if i["criterion"] in REMOVED22]
    report["versions"] = {
        "wcag21": v21, "wcag22": v22,
        "transition": {
            "added_by_22": len(added), "removed_by_22": len(removed),
            "net_change": v22["violations"] - v21["violations"],
            "added_criteria": sorted({i["criterion"] for i in added}, key=_sort_key),
            "note": ("WCAG 2.2 removed 4.1.1 Parsing and added new criteria. The same page, "
                     "fetched once, is counted under both versions."),
        },
    }

    # Per-criterion groups with explanation, ordered Level A first then by count.
    groups = collections.OrderedDict()
    for i in ext:
        c = i["criterion"]
        g = groups.setdefault(c, {"criterion": c, "level": i["level"], "count": 0, "instances": [],
                                  "in_21": c not in NEW22, "in_22": c not in REMOVED22})
        g["count"] += 1
        if len(g["instances"]) < 25:
            g["instances"].append({"issue": i["issue"], "element": i["element"], "locator": i["locator"]})
    for c, g in groups.items():
        k = info(c)
        g.update({"name": k["name"], "principle": k["principle"], "detects": k["detects"],
                  "affects": k["affects"], "fix": k["fix"], "task_type": k["task_type"], "w3c": k["w3c"]})
        cen = CENSUS["criteria"].get(c)
        g["census_share_pct"] = cen["share_pct"] if cen else None
    ordered = sorted(groups.values(), key=lambda g: (g["level"] != "A", -g["count"], _sort_key(g["criterion"])))
    report["criteria"] = ordered

    # Principles breakdown (2.1 set, as in the paper)
    princ = collections.Counter(info(i["criterion"])["principle"] for i in set21)
    report["principles"] = dict(princ)

    # Census placement
    report["census"] = {
        "wcag21": census_placement(len(set21), "21", country),
        "wcag22": census_placement(len(set22), "22", country),
        "meta": CENSUS["meta"],
    }

    # Task units following the UD26 taxonomy: one unit per criterion group,
    # ordered Level A first, then by recurrence, split into two queues.
    tasks = []
    n = 0
    for g in ordered:
        k = info(g["criterion"])
        n += 1
        tasks.append({
            "task_id": f"{report['id']}-T{n:02d}",
            "queue": k["task_type"],
            "criterion": g["criterion"], "name": k["name"], "level": g["level"],
            "page_url": raw.get("final_url"),
            "instances": g["count"],
            "problem": k["detects"],
            "fix": k["fix"],
            "acceptance": k["acceptance"],
            "output": k["output"],
            "verification": k["verify"],
            "elements": [x["locator"] or x["element"][:80] for x in g["instances"][:5]],
            "est_minutes": max(5, min(60, 5 + 3 * g["count"])) if k["task_type"] == "non-technical" else max(15, min(90, 15 + 2 * g["count"])),
        })
    report["tasks"] = {
        "non_technical": [t for t in tasks if t["queue"] == "non-technical"],
        "technical": [t for t in tasks if t["queue"] == "technical"],
        "total_units": len(tasks),
        "total_instances": len(ext),
    }
    return report


def tasks_csv(report):
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["task_id", "queue", "criterion", "name", "level", "page_url", "instances", "problem",
                "fix", "acceptance_criteria", "output", "verification", "example_elements", "est_minutes",
                "contributor", "started", "finished", "minutes_spent", "completed",
                "clear_enough_to_start", "first_pass_passed", "notes"])
    for q in ("non_technical", "technical"):
        for t in report.get("tasks", {}).get(q, []):
            w.writerow([t["task_id"], t["queue"], t["criterion"], t["name"], t["level"], t["page_url"],
                        t["instances"], t["problem"], t["fix"], t["acceptance"], t["output"],
                        t["verification"], " | ".join(t["elements"]), t["est_minutes"],
                        "", "", "", "", "", "", "", ""])
    return buf.getvalue()
