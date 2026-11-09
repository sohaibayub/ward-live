"""Build a compact census summary from the published replication package.
Run once; the demo reads census_summary.json."""
import gzip, json, os, sys, collections
RES = sys.argv[1]
OUT = sys.argv[2]
COUNTRIES = [("uk","United Kingdom"),("nz","New Zealand"),("aus","Australia"),("irl","Ireland"),("usa","United States")]
NEW22 = {"2.4.11","3.2.6","3.3.7","3.3.8"}
LEVEL_A = {"1.1.1","1.3.1","1.4.1","2.1.1","2.4.1","2.4.2","2.4.4","2.5.3","3.1.1","3.2.6","3.3.7","4.1.1","4.1.2"}

def load(code):
    with gzip.open(os.path.join(RES, f"results_{code}_orgs.json.gz"), "rt", encoding="utf-8") as f:
        recs = json.load(f)
    seen = {}
    for r in recs: seen.setdefault(r["url"], r)
    return list(seen.values())

summary = {"countries": {}, "all": None, "criteria": {}, "meta": {}}
hist21_all = collections.Counter(); hist22_all = collections.Counter()
crit_sites = collections.Counter(); crit_inst = collections.Counter()
n_all = 0; frame_all = 0; unreach_all = 0; sums = {}
for code, name in COUNTRIES:
    recs = load(code)
    tested = [r for r in recs if r["status"] == "tested"]
    h21 = collections.Counter(); h22 = collections.Counter(); s21 = s22 = 0
    for r in tested:
        ext = r["issues_2_2"]
        n21 = sum(1 for i in ext if i["criterion"] not in NEW22)
        n22 = sum(1 for i in ext if i["criterion"] != "4.1.1")
        h21[min(n21, 200)] += 1; h22[min(n22, 200)] += 1; s21 += n21; s22 += n22
        for c in {i["criterion"] for i in ext}: crit_sites[c] += 1
        for i in ext: crit_inst[i["criterion"]] += 1
    hist21_all.update(h21); hist22_all.update(h22)
    n_all += len(tested); frame_all += len(recs); unreach_all += len(recs) - len(tested)
    sums[code] = (s21, s22)
    summary["countries"][code] = {"name": name, "frame": len(recs), "audited": len(tested), "sum21": s21, "sum22": s22,
        "hist21": {str(k): v for k, v in sorted(h21.items())},
        "hist22": {str(k): v for k, v in sorted(h22.items())}}
summary["all"] = {"name": "All five countries", "frame": frame_all, "audited": n_all,
    "sum21": sum(v[0] for v in sums.values()), "sum22": sum(v[1] for v in sums.values()),
    "hist21": {str(k): v for k, v in sorted(hist21_all.items())},
    "hist22": {str(k): v for k, v in sorted(hist22_all.items())}}
summary["criteria"] = {c: {"sites": crit_sites[c], "share_pct": round(100*crit_sites[c]/n_all, 1),
                           "instances": crit_inst[c], "level": "A" if c in LEVEL_A else "AA"}
                       for c in sorted(crit_sites, key=lambda x: [int(p) for p in x.split(".")])}
summary["meta"] = {"source": "github.com/sohaibayub/cso-web-accessibility, Zenodo 10.5281/zenodo.23529469",
                   "audit_window": "June to July 2026", "frame": frame_all, "audited": n_all, "unreachable": unreach_all}
json.dump(summary, open(OUT, "w"), indent=1)
print(json.dumps(summary["meta"])); print({k: v["audited"] for k, v in summary["countries"].items()})
print("criteria", list(summary["criteria"].items())[:3])
