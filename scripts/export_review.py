"""Build the review view, viz/review.html: each text segment by segment, with the
claims that cite each segment, its coverage record, and the eval questions resting on it.

    python scripts/export_review.py

It's for checking the modelling against the text: what was encoded, whether it
matches, and what was left out (uncited segments stay visible).
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

from rdflib import RDF
from rdflib.namespace import SKOS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dho  # noqa: E402
import sc  # noqa: E402
from dho import DHO, ONTOLEX, ROOT, label  # noqa: E402


def claim_summary(g, c) -> tuple[str, str, str]:
    """(kind, layer, one-line summary) for a node that cites a passage."""
    types = set(g.objects(c, RDF.type))
    L = lambda n: label(g, n)  # noqa: E731
    if DHO.Nutriment in types:
        effect = "fuels" if g.value(c, DHO.fuels) else "starves"
        target = g.value(c, DHO.fuels) or g.value(c, DHO.starves)
        return "nutriment", "sutta", f"{dho.nutriment_attention(g, g.value(c, DHO.attention))} to {L(g.value(c, DHO.object))} {effect} {L(target)}"
    if DHO.TimingAdvice in types:
        state, factor, timing = g.value(c, DHO.whenMind), g.value(c, DHO.develop), g.value(c, DHO.timing)
        when = f"when the mind is {L(state).replace(' mind', '')}: " if state else ""
        return "timing", "sutta", f"{when}{L(timing)} {L(factor)}"
    if DHO.NumberedList in types:
        members = sorted(L(m) for m in g.objects(c, DHO.hasMember))
        return "list", "sutta", f"{L(c)} ({g.value(c, DHO.expectedCount)}): {', '.join(members)}"
    if DHO.Attainment in types:
        return "attainment", "sutta", (f"{L(c)} gives up {L(g.value(c, DHO.givesUp))}, "
                                       f"has {L(g.value(c, DHO.possesses))}")
    if DHO.Definition in types:
        return "definition", "sutta", f"{L(g.value(c, DHO.defines))} is defined as {L(g.value(c, DHO['as']))}"
    if DHO.Outcome in types:
        sup = " [expanded abbreviation]" if g.value(c, DHO.support) is not None else ""
        return "outcome", "sutta", (f"{L(g.value(c, DHO.of))} {L(g.value(c, DHO.effect))} {L(g.value(c, DHO.to))}"
                                    f" (“{g.value(c, DHO.wording)}”){sup}")
    if DHO.Condition in types:
        res = g.value(c, DHO.result)
        what = f"{L(g.value(c, DHO.relation))} {L(g.value(c, DHO.conditioned))}" + (f": {L(res)}" if res else "")
        return "condition", "sutta", f"{L(g.value(c, DHO.condition))} {what} (“{g.value(c, DHO.wording)}”)"
    if DHO.Simile in types:
        ill = ", ".join(sorted({L(e) for i in g.objects(c, DHO.illustrates) for e in dho.claim_endpoints(g, i)}))
        return "simile", "sutta", f"simile: {L(c)}, illustrating {ill}"
    if DHO.Division in types:
        parts = " and ".join(sorted(L(p) for p in g.objects(c, DHO.part)))
        return "division", "sutta", f"{L(g.value(c, DHO.divides))} becomes twofold ({L(g.value(c, DHO.basis))}): {parts}"
    if ONTOLEX.LexicalSense in types:
        return "word sense", "lexicon", f"'dhamma' meaning {L(g.value(c, ONTOLEX.reference))}"
    if DHO.Opposition in types:
        return "opposition", "commentary", f"{L(g.value(c, DHO.opponent))} opposes {L(g.value(c, DHO.target))}"
    return "claim", "sutta", L(c)


def export() -> dict:
    g, *_ = dho.build()
    questions = tomllib.loads((ROOT / "eval" / "questions.toml").read_text(encoding="utf-8"))["q"]
    q_by_seg: dict[str, list[str]] = {}
    for q in questions:
        for s in q.get("segments", []):
            q_by_seg.setdefault(s, []).append(q["id"])

    texts = []
    for t in sorted(g.subjects(RDF.type, DHO.Text), key=str):
        uid = str(t).split("#t-", 1)[1]
        rec = {
            "uid": uid,
            "title": str(g.value(t, SKOS.prefLabel) or uid),
            "layer": label(g, g.value(t, DHO.layer)),
            "coverage": label(g, g.value(t, DHO.coverage)),
            "review": label(g, g.value(t, DHO.review)),
            "encodes": str(g.value(t, DHO.encodes) or ""),
            "leftOut": str(g.value(t, DHO.leftOut) or ""),
            "modelledBy": str(g.value(t, DHO.modelledBy) or ""),
            "modelledOn": str(g.value(t, DHO.modelledOn) or ""),
            "segments": [],
        }
        claims_by_seg: dict[str, list[dict]] = {}
        for p in g.subjects(DHO.inText, t):
            seg = str(g.value(p, DHO.segment))
            for c in g.subjects(DHO.citedBy, p):
                kind, layer, text = claim_summary(g, c)
                claims_by_seg.setdefault(seg, []).append({"kind": kind, "layer": layer, "text": text})
            sense = g.value(p, DHO.usesSense)
            if sense is not None:
                claims_by_seg.setdefault(seg, []).append({"kind": "uses sense", "layer": "editor",
                    "text": f"uses 'dhamma' as {label(g, g.value(sense, ONTOLEX.reference))} "
                            f"({g.value(p, DHO.senseAssignedBy)})"})
            rendering = g.value(p, DHO.translatorRendering)
            if rendering is not None:
                claims_by_seg.setdefault(seg, []).append({"kind": "contested", "layer": "editor",
                    "text": f"contested use of 'dhamma', left unassigned (rendered '{rendering}')"})
        try:
            en, pi = sc.load(uid)
        except SystemExit:
            en, pi = {}, {}
        for k in pi:
            if k.split(":")[0] != uid:
                continue
            rec["segments"].append({"id": k, "en": en.get(k, "").strip(), "pi": pi[k].strip(),
                                    "claims": claims_by_seg.get(k, []), "eval": q_by_seg.get(k, [])})
        rec["cited"] = sum(1 for s in rec["segments"] if s["claims"])
        texts.append(rec)
    order = {"fully encoded": 0, "partly encoded": 1, "cited only": 2, "referenced only": 3}
    texts.sort(key=lambda r: (order.get(r["coverage"], 9), r["uid"]))
    return {"texts": texts}


def main() -> int:
    data = export()
    template = (ROOT / "viz" / "review-template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    (ROOT / "viz" / "review.html").write_text(template.replace("/*__DATA__*/null", payload), encoding="utf-8")
    n = sum(len(t["segments"]) for t in data["texts"])
    print(f"wrote viz/review.html: {len(data['texts'])} texts, {n} segments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
