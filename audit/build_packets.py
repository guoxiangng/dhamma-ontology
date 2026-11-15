"""Build one audit packet per text: full text (EN + Pali) and every claim citing it.

    python audit/build_packets.py audit/<run-date>            # every text with claims
    python audit/build_packets.py audit/<run-date> sn46.52    # only these texts (the add-text audit step)

Run from the repo root. Writes <run>/packets/<uid>.md and <run>/batches.json. An auditor agent
then grades each packet against audit/RUBRIC.md and writes <run>/results/<name>.json.
"""
import json
import sys
from pathlib import Path

from rdflib.namespace import RDF, SKOS

sys.path.insert(0, "scripts")
import dho  # noqa: E402
import sc  # noqa: E402
from dho import DHO, label  # noqa: E402
from export_review import claim_summary  # noqa: E402

OUT = Path(sys.argv[1])
ONLY = set(sys.argv[2:])
(OUT / "packets").mkdir(parents=True, exist_ok=True)

g, *_ = dho.build()


def seg_of(p):
    return str(g.value(p, DHO.segment))


def detail(c):
    """Field-level view of a claim, so the auditor sees exactly what we asserted."""
    types = set(g.objects(c, RDF.type))
    L = lambda n: label(g, n) if n is not None else None  # noqa: E731
    f = {}
    if DHO.Outcome in types:
        f = {"of": L(g.value(c, DHO.of)), "effect": L(g.value(c, DHO.effect)), "to": L(g.value(c, DHO.to))}
    elif DHO.Condition in types:
        f = {"condition": L(g.value(c, DHO.condition)), "relation": L(g.value(c, DHO.relation)),
             "conditioned": L(g.value(c, DHO.conditioned)), "result": L(g.value(c, DHO.result))}
    elif DHO.Division in types:
        f = {"divides": L(g.value(c, DHO.divides)), "basis": L(g.value(c, DHO.basis)),
             "parts": sorted(L(p) for p in g.objects(c, DHO.part))}
    elif DHO.Nutriment in types:
        f = {"object": L(g.value(c, DHO.object)), "attention": dho.nutriment_attention(g, g.value(c, DHO.attention)),
             "fuels": L(g.value(c, DHO.fuels)), "starves": L(g.value(c, DHO.starves))}
    elif DHO.TimingAdvice in types:
        f = {"whenMind": L(g.value(c, DHO.whenMind)), "develop": L(g.value(c, DHO.develop)), "timing": L(g.value(c, DHO.timing))}
    elif DHO.NumberedList in types:
        f = {"members": sorted(L(m) for m in g.objects(c, DHO.hasMember)), "expectedCount": str(g.value(c, DHO.expectedCount))}
    elif DHO.Definition in types:
        f = {"defines": L(g.value(c, DHO.defines)), "as": L(g.value(c, DHO["as"]))}
    w = g.value(c, DHO.wording)
    if w is not None:
        f["wording"] = str(w)
    n = g.value(c, SKOS.note)
    if n is not None:
        f["note"] = str(n)
    return {k: v for k, v in f.items() if v}


texts = []
for t in sorted(g.subjects(RDF.type, DHO.Text), key=str):
    uid = str(t).split("#t-", 1)[1]
    if ONLY and uid not in ONLY:
        continue
    try:
        en, pi = sc.load(uid)
    except SystemExit:
        continue  # commentary we don't hold (vism): can't be audited against a text
    passages = list(g.subjects(DHO.inText, t))
    claims = {}
    for p in passages:
        for c in g.subjects(DHO.citedBy, p):
            claims.setdefault(c, set()).add(seg_of(p))
    if not claims:
        continue
    cov = label(g, g.value(t, DHO.coverage))
    lines = [f"# {uid}: {g.value(t, SKOS.prefLabel) or uid}", "",
             f"Coverage status we recorded: **{cov}**", "",
             f"What we say we encoded: {g.value(t, DHO.encodes) or '(none)'}", "",
             f"What we say we left out: {g.value(t, DHO.leftOut) or '(nothing)'}", "",
             "## Claims citing this text", ""]
    for c in sorted(claims, key=lambda c: dho.short(c)):
        kind, layer, summary = claim_summary(g, c)
        other = sorted({seg_of(p).split(':')[0] for p in g.objects(c, DHO.citedBy)} - {uid})
        lines.append(f"### {dho.short(c).removeprefix('dho:')} ({kind}, layer: {layer})")
        lines.append(f"- summary: {summary}")
        for k, v in detail(c).items():
            lines.append(f"- {k}: {v}")
        lines.append(f"- segments cited in this text: {', '.join(sorted(claims[c], key=lambda s: [int(x) if x.isdigit() else x for x in s.split(':')[1].split('.')]))}")
        if other:
            lines.append(f"- also cites other texts (not shown, judge only this text's support): {', '.join(other)}")
        lines.append("")
    # Full text for encoded texts; for cited-only texts, the cited segments with context.
    keys = [k for k in pi if k.split(":")[0] == uid]
    if cov in ("cited only", "referenced only"):
        cited = {s for ss in claims.values() for s in ss}
        idx = {k: i for i, k in enumerate(keys)}
        keep = set()
        for s in cited:
            i = idx.get(s)
            if i is not None:
                keep.update(keys[max(0, i - 4): i + 5])
        keys = [k for k in keys if k in keep]
        lines.append("## Text (cited segments with 4 segments of context either side; the rest omitted)")
    else:
        lines.append("## Full text (segment | English, Sujato | Pali)")
    lines.append("")
    for k in keys:
        lines.append(f"{k} | {en.get(k, '').strip()} | {pi[k].strip()}")
    (OUT / "packets" / f"{uid}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    texts.append({"uid": uid, "claims": len(claims), "segments": len(keys), "coverage": cov})

# Six batches balanced by segment count.
texts.sort(key=lambda r: -r["segments"])
batches = [[] for _ in range(6)]
load = [0] * 6
for r in texts:
    i = load.index(min(load))
    batches[i].append(r["uid"])
    load[i] += r["segments"] + 8 * r["claims"]
(OUT / "batches.json").write_text(json.dumps(batches, indent=1), encoding="utf-8")
print(len(texts), "packets;", sum(r["claims"] for r in texts), "claim-text pairs; batch loads", load)
