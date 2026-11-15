"""Total an audit run's results and compare the blind run (if any) with the text-based one.

    python audit/aggregate.py audit/2026-11-15
"""
import collections
import json
import sys
from pathlib import Path

A = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "2026-11-15") / "results"
runs = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(A.glob("*.json"))}

text_v, blind_v = {}, {}
issues, omissions, status_bad = [], [], []
for name, run in runs.items():
    for t in run["texts"]:
        for c in t["claims"]:
            key = (t["uid"], c["id"])
            (blind_v if name == "blind" else text_v)[key] = c
            if name != "blind" and c["verdict"] != "SUPPORTED":
                issues.append((c.get("severity") or "", c["verdict"], t["uid"], c["id"], c["reason"]))
        if name != "blind":
            for o in t.get("omissions") or []:
                omissions.append((t["uid"], o))
            if t.get("left_out_accurate") is False or t.get("coverage_status_accurate") is False:
                status_bad.append((t["uid"], t.get("left_out_accurate"), t.get("coverage_status_accurate"), t.get("notes", "")))

print("text-based runs:", sorted(k for k in runs if k != "blind"))
v = collections.Counter(c["verdict"] for c in text_v.values())
sev = collections.Counter((c["verdict"], c.get("severity")) for c in text_v.values() if c["verdict"] != "SUPPORTED")
print("claim-text pairs judged:", len(text_v), dict(v))
print("by severity:", dict(sev))
print("\n== non-SUPPORTED (major first)")
for s, verdict, uid, cid, reason in sorted(issues, key=lambda r: (r[0] != "major", r[1], r[2])):
    print(f"[{s or '-'}] {verdict:13} {uid:9} {cid:10} {reason}")
print(f"\n== omissions ({len(omissions)})")
for uid, o in omissions:
    print(f"{uid:9} {','.join(o.get('segments', []))}: {o.get('what')}")
print(f"\n== coverage notes or status questioned ({len(status_bad)})")
for r in status_bad:
    print(r)

if blind_v:
    print("\n== blind vs text, on shared claim-text pairs")
    shared = [k for k in blind_v if k in text_v]
    agree = collections.Counter()
    for k in shared:
        tv, bv = text_v[k]["verdict"], blind_v[k]["verdict"]
        agree[(tv == "SUPPORTED", bv == "SUPPORTED", blind_v[k].get("confidence"))] += 1
    print("shared:", len(shared))
    for (t_ok, b_ok, conf), n in sorted(agree.items(), key=str):
        print(f"  text says {'ok ' if t_ok else 'BAD'} | blind says {'ok ' if b_ok else 'BAD'} | blind confidence {conf}: {n}")
    print("  blind confidence overall:", dict(collections.Counter(c.get("confidence") for c in blind_v.values())))
    print("  disagreements:")
    for k in shared:
        tv, bv = text_v[k], blind_v[k]
        if (tv["verdict"] == "SUPPORTED") != (bv["verdict"] == "SUPPORTED"):
            print(f"   {k}: text={tv['verdict']} blind={bv['verdict']}({bv.get('confidence')}) | blind: {bv['reason'][:160]}")
