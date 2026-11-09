"""Check that the demo checker reports exactly the criteria and counts the
census tool reports, on the same HTML. Usage:
    python test_parity.py <path to replication package> url1 url2 ...
"""
import collections
import sys

sys.path.insert(0, sys.argv[1] + "/ward")
from ward_civil_chunk_json import WARDCivil  # noqa: E402  (the census tool)
from wardlive.checker import WARDLive  # noqa: E402

orig = WARDCivil()
live = WARDLive()
ok = True
for url in sys.argv[2:]:
    html, final, err, _ = live.fetch(url)
    if err:
        print(f"{url}: fetch failed ({err})")
        continue
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    a = collections.Counter(i["criterion"] for i in orig._check_2_0(soup) + orig._check_2_1(soup) + orig._check_2_2(soup))
    b = collections.Counter(i["criterion"] for i in live.analyze_html(html)[0])
    same = a == b
    ok &= same
    print(f"{'OK ' if same else 'DIFF'} {final}  census={sum(a.values())} demo={sum(b.values())}")
    if not same:
        print("   census:", dict(a)); print("   demo:  ", dict(b))
print("PARITY" if ok else "MISMATCH")
sys.exit(0 if ok else 1)
