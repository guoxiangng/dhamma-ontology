"""Export the reasoned graph (after OWL inference and rule R1) as JSON, and build
the interactive viewer viz/graph.html from viz/template.html.

    python scripts/export_graph.py

The viewer shows what the ontology knows, not what the files say: classifications
come from the reasoner and `counters` links from rule R1, each labelled by layer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from rdflib import Literal
from rdflib.namespace import RDF, SKOS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dho  # noqa: E402
from dho import DHO, ONTOLEX, ROOT, label, short  # noqa: E402

KINDS = [  # order matters: first match is the node's main kind
    (DHO.Hindrance, "hindrance"),
    (DHO.AwakeningFactor, "factor"),
    (DHO.JhanaFactor, "jhana"),
    (DHO.MindState, "mindstate"),
    (DHO.AttentionObject, "object"),
    (DHO.NumberedList, "list"),
    (DHO.Attainment, "attainment"),
    (ONTOLEX.LexicalEntry, "word"),
    (DHO.Concept, "sense"),
]
CLASS_NAMES = {DHO.Hindrance: "Hindrance", DHO.AwakeningFactor: "Awakening factor", DHO.JhanaFactor: "Jhāna factor"}


def lid(node) -> str:
    return short(node).removeprefix("dho:")


def cites(g, node) -> list[str]:
    return sorted((lid(p) for p in g.objects(node, DHO.citedBy)), key=lambda p: str(g.value(DHO[p], DHO.segment)))


def langs(g, node, prop) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for l in g.objects(node, prop):
        if isinstance(l, Literal):
            out.setdefault(l.language or "", []).append(str(l))
    return out


def export() -> dict:
    g, asserted, derived, inferred = dho.build()

    nodes = {}
    for cls, kind in KINDS:
        for n in g.subjects(RDF.type, cls):
            if lid(n) in nodes or not str(n).startswith(str(DHO)):
                continue
            types = set(g.objects(n, RDF.type))
            pref = langs(g, n, SKOS.prefLabel)
            if kind == "word":
                form = next(g.objects(n, ONTOLEX.canonicalForm))
                pref = {"pi": [str(next(g.objects(form, ONTOLEX.writtenRep)))]}
            nodes[lid(n)] = {
                "id": lid(n),
                "kind": kind,
                "en": (pref.get("en") or [None])[0],
                "pi": (pref.get("pi") or [None])[0],
                "zh": (pref.get("zh") or [None])[0],
                "alt": sorted(set(sum(langs(g, n, SKOS.altLabel).values(), []))),
                "hidden": sorted(set(sum(langs(g, n, SKOS.hiddenLabel).values(), []))),
                "classes": [name for c, name in CLASS_NAMES.items() if c in types],
                "inferred": bool(types & set(CLASS_NAMES)),
                "definition": str(g.value(n, SKOS.definition) or "") or None,
                "note": str(g.value(n, SKOS.note) or "") or None,
                "cites": cites(g, n),
            }

    edges = []

    def edge(src, tgt, rel, layer, cite=(), note=None, **extra):
        s, t = lid(src), lid(tgt)
        if s in nodes and t in nodes:
            edges.append({"id": f"e{len(edges)}", "source": s, "target": t, "rel": rel,
                          "layer": layer, "cites": list(cite), "note": note, **extra})

    for q, lst in g.subject_objects(DHO.memberOf):
        edge(q, lst, "member of", "sutta", cites(g, lst))
    for a, lst in g.subject_objects(DHO.givesUp):
        edge(a, lst, "gives up", "sutta", cites(g, a))
    for a, lst in g.subject_objects(DHO.possesses):
        edge(a, lst, "has the factors", "sutta", cites(g, a))

    nutriments = []
    for n in g.subjects(RDF.type, DHO.Nutriment):
        effect = "fuels" if g.value(n, DHO.fuels) else "starves"
        target = g.value(n, DHO.fuels) or g.value(n, DHO.starves)
        att = g.value(n, DHO.attention)
        nutriments.append({"id": lid(n), "object": lid(g.value(n, DHO.object)), "attention": label(g, att),
                           "attentionId": lid(att), "effect": effect, "target": lid(target), "cites": cites(g, n)})
    nutriments.sort(key=lambda x: x["id"])

    for d in g.subjects(RDF.type, DHO.Derivation):
        f, h = g.value(d, DHO.derivedSubject), g.value(d, DHO.derivedObject)
        via = list(g.objects(d, DHO.via))
        obj = next((v for v in via if (v, RDF.type, DHO.AttentionObject) in g), None)
        cs = sorted({c for v in via for c in cites(g, v)}, key=lambda p: str(g.value(DHO[p], DHO.segment)))
        edge(f, h, "counters", "derived", cs, f"Rule R1: '{label(g, obj)}', attended to rationally, "
             f"fuels {label(g, f)} and starves {label(g, h)}.", via=lid(obj) if obj else None)

    timing = []
    for a in g.subjects(RDF.type, DHO.TimingAdvice):
        state, factor, t = g.value(a, DHO.whenMind), g.value(a, DHO.develop), g.value(a, DHO.timing)
        rec = {"id": lid(a), "state": lid(state) if state else None, "factor": lid(factor),
               "timing": label(g, t), "timingId": lid(t), "cites": cites(g, a)}
        timing.append(rec)
        if state:
            edge(state, factor, label(g, t), "sutta", rec["cites"], timing=lid(t))
    timing.sort(key=lambda x: x["id"])

    for op in g.subjects(RDF.type, DHO.Opposition):
        edge(g.value(op, DHO.opponent), g.value(op, DHO.target), "opposes", "commentary",
             cites(g, op), str(g.value(op, DHO.citationNote) or ""))

    for d in g.subjects(RDF.type, DHO.Definition):
        edge(g.value(d, DHO.defines), g.value(d, DHO["as"]), "is defined as", "sutta", cites(g, d))

    for a, b in g.subject_objects(DHO.editorialRelated):
        edge(a, b, "see also", "editor", note="Editor's link, not a textual claim.")

    for e in g.subjects(RDF.type, ONTOLEX.LexicalEntry):
        for s in g.objects(e, ONTOLEX.sense):
            edge(e, g.value(s, ONTOLEX.reference), "sense", "lexicon", cites(g, s))

    passages = {}
    for p in g.subjects(RDF.type, DHO.Passage):
        sense = g.value(p, DHO.usesSense)
        passages[lid(p)] = {
            "segment": str(g.value(p, DHO.segment)),
            "en": str(g.value(p, DHO.textEn) or ""),
            "pi": str(g.value(p, DHO.textPi) or ""),
            "url": str(g.value(p, DHO.url) or ""),
            "contested": str(g.value(p, DHO.translatorRendering) or "") or None,
            "sense": lid(g.value(sense, ONTOLEX.reference)) if sense else None,
        }

    conforms, results = dho.run_shacl(g)
    return {
        "stats": {"asserted": asserted, "inferred": inferred, "derived": sum(derived.values()),
                  "concepts": len(nodes), "links": len(edges) + len(nutriments), "passages": len(passages),
                  "shacl": "pass" if conforms else "fail",
                  "warnings": sum(r["severity"] == "Warning" for r in results)},
        "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
        "edges": edges,
        "nutriments": nutriments,
        "timing": timing,
        "passages": passages,
    }


def main() -> int:
    data = export()
    out_dir = ROOT / "viz"
    (out_dir / "graph.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    template = (out_dir / "template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    (out_dir / "graph.html").write_text(template.replace("/*__DATA__*/null", payload), encoding="utf-8")
    s = data["stats"]
    print(f"wrote viz/graph.json and viz/graph.html: {s['concepts']} nodes, {s['links']} links, "
          f"{s['passages']} passages, SHACL {s['shacl']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
