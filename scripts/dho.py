"""dhamma-ontology command line.

    python scripts/dho.py check            reason, apply rules, run SHACL, print a report
    python scripts/dho.py ask "<words>"    resolve words to concepts and answer from the graph
    python scripts/dho.py sense dhamma     show the senses of an ambiguous word
    python scripts/dho.py query <file.rq>  run a SPARQL SELECT over the reasoned graph (see queries/)

Pipeline (same for every command):
    1. load   ontology/*.ttl + data/*.ttl            (what we wrote)
    2. reason OWL RL via owlrl                        (what follows logically)
    3. rules  rules/*.rq SPARQL CONSTRUCT             (what our named rules derive)
    4. check  shapes/*.ttl via pySHACL                (whether it all obeys the rules)
"""

from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import owlrl
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

ROOT = Path(__file__).resolve().parent.parent
DHO = Namespace("https://guoxiangng.github.io/dhamma-ontology/ns#")
SH = Namespace("http://www.w3.org/ns/shacl#")
ONTOLEX = Namespace("http://www.w3.org/ns/lemon/ontolex#")


# --------------------------------------------------------------------------- pipeline

def load(extra: list[Path] | None = None) -> Graph:
    g = Graph()
    for folder in ("ontology", "data"):
        for ttl in sorted((ROOT / folder).glob("*.ttl")):
            g.parse(ttl, format="turtle")
    for ttl in extra or []:
        g.parse(ttl, format="turtle")
    g.bind("dho", DHO)
    return g


def reason(g: Graph) -> int:
    before = len(g)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(g)
    return len(g) - before


def apply_rules(g: Graph) -> dict[str, int]:
    added = {}
    for rq in sorted((ROOT / "rules").glob("*.rq")):
        result = g.query(rq.read_text(encoding="utf-8"))
        before = len(g)
        for triple in result:
            g.add(triple)
        added[rq.stem] = len(g) - before
    return added


def build(extra: list[Path] | None = None) -> tuple[Graph, int, dict[str, int], int]:
    g = load(extra)
    asserted = len(g)
    inferred = reason(g)
    derived = apply_rules(g)
    return g, asserted, derived, inferred


def shapes() -> Graph:
    s = Graph()
    for ttl in sorted((ROOT / "shapes").glob("*.ttl")):
        s.parse(ttl, format="turtle")
    return s


def run_shacl(g: Graph) -> tuple[bool, list[dict]]:
    conforms, report, _ = validate(g, shacl_graph=shapes(), inference="none", advanced=True, allow_warnings=True)
    results = []
    for r in report.subjects(RDF.type, SH.ValidationResult):
        results.append({
            "severity": str(report.value(r, SH.resultSeverity)).rsplit("#", 1)[-1],
            "focus": short(report.value(r, SH.focusNode)),
            "shape": short(report.value(r, SH.sourceShape)),
            "message": str(report.value(r, SH.resultMessage) or ""),
        })
    results.sort(key=lambda x: (x["severity"] != "Violation", x["message"], x["focus"]))
    return conforms, results


# --------------------------------------------------------------------------- helpers

def short(node) -> str:
    if node is None:
        return "-"
    s = str(node)
    return "dho:" + s.split("#", 1)[1] if s.startswith(str(DHO)) else s


def label(g: Graph, node, lang: str = "en") -> str:
    for prop in (SKOS.prefLabel, RDFS.label):
        for l in g.objects(node, prop):
            if isinstance(l, Literal) and l.language == lang:
                return str(l)
    return short(node)


def labels(g: Graph, node) -> str:
    en, pi, zh = label(g, node, "en"), label(g, node, "pi"), label(g, node, "zh")
    parts = [en] + [x for x in (pi, zh) if not x.startswith("dho:") and x != en]
    return " · ".join(parts)


def fold(text: str) -> str:
    """Lower-case and strip diacritics so 'uddhacca' matches 'uddhācca' etc."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c)).replace("-", " ").strip()


def cite(g: Graph, claim) -> str:
    """Citations grouped by text, consecutive segments collapsed: 'mn43:20.3; sn46.37:1.1, 1.3–1.7'."""
    by_text: dict[str, list[tuple[int, ...]]] = {}
    for p in g.objects(claim, DHO.citedBy):
        uid, seg = str(g.value(p, DHO.segment)).split(":", 1)
        by_text.setdefault(uid, []).append(tuple(int(x) for x in seg.split(".")))
    if not by_text:
        return "-"
    parts = []
    for uid in sorted(by_text):
        segs = sorted(set(by_text[uid]))
        runs: list[list[tuple[int, ...]]] = []
        for s in segs:
            prev = runs[-1][-1] if runs else None
            if prev and len(s) == len(prev) == 2 and s[0] == prev[0] and s[1] == prev[1] + 1:
                runs[-1].append(s)
            else:
                runs.append([s])
        fmt = lambda s: ".".join(map(str, s))  # noqa: E731
        parts.append(f"{uid}:" + ", ".join(fmt(r[0]) if len(r) == 1 else f"{fmt(r[0])}–{fmt(r[-1])}" for r in runs))
    return "; ".join(parts)


def quote(g: Graph, passage, lang: str = "en") -> str:
    v = g.value(passage, DHO.textEn if lang == "en" else DHO.textPi)
    return str(v) if v else ""


# SN 46.51 states every nutriment as *frequent* attention (bahulīkāra). That frequency belongs
# to the statement, not to the kind of attention, so it is added here, in Sujato's words.
NUTRIMENT_ATTENTION = {
    "RationalAttention": "frequent rational application of mind",
    "IrrationalAttention": "frequent irrational application of mind",
    "NonAttention": "not frequently applying the mind",
}


def nutriment_attention(g: Graph, att) -> str:
    return NUTRIMENT_ATTENTION.get(str(att).rsplit("#", 1)[-1], label(g, att))


# --------------------------------------------------------------------------- resolve

def resolve(g: Graph, text: str) -> list[URIRef]:
    """Map free text to concepts by matching any label (pref/alt/hidden, any language)."""
    q = fold(text)
    candidates = (set(g.subjects(RDF.type, DHO.MentalQuality)) | set(g.subjects(RDF.type, DHO.MindState))
                  | set(g.subjects(RDF.type, DHO.Concept)) | set(g.subjects(RDF.type, DHO.AttentionMode))
                  | set(g.subjects(RDF.type, DHO.NumberedList)))
    exact, partial = [], []
    for c in candidates:
        names = [fold(str(l)) for p in (SKOS.prefLabel, SKOS.altLabel, SKOS.hiddenLabel, RDFS.label) for l in g.objects(c, p)]
        if q in names:
            exact.append(c)
        elif any(len(n) > 2 and (n in q or q in n) for n in names):
            partial.append(c)
    hits = exact or partial
    return sorted(hits, key=lambda c: (DHO.MindState in set(g.objects(c, RDF.type)), label(g, c)))


# --------------------------------------------------------------------------- answer

def card(g: Graph, c) -> list[str]:
    out = [f"\n=== {labels(g, c)}"]
    types = set(g.objects(c, RDF.type))
    kinds = [label(g, t) for t in (DHO.Hindrance, DHO.AwakeningFactor, DHO.JhanaFactor) if t in types]
    if kinds:
        out.append(f"  is a: {', '.join(kinds)}   (inferred by the reasoner from list membership)")
    elif DHO.MindState in types:
        out.append("  is a: mind state")
    for lst in sorted(g.objects(c, DHO.memberOf)):
        out.append(f"  member of: {label(g, lst)}   [sutta {cite(g, lst)}]")
    if DHO.NumberedList in types:
        members = sorted(label(g, m) for m in g.objects(c, DHO.hasMember))
        out.append(f"  members ({len(members)}): {', '.join(members)}   [sutta {cite(g, c)}]")

    def nutriments(prop):
        rows = []
        for n in g.subjects(prop, c):
            obj, att = g.value(n, DHO.object), g.value(n, DHO.attention)
            obj_passage = sorted(g.objects(n, DHO.citedBy), key=lambda p: str(g.value(p, DHO.segment)))[0]
            rows.append(f"    - {nutriment_attention(g, att)} to {label(g, obj)}\n"
                        f"        \"{quote(g, obj_passage)}\"  [sutta {cite(g, n)}]")
        return rows

    fed = nutriments(DHO.fuels)
    if fed:
        out.append("  fuelled by:")
        out += fed
    starved = nutriments(DHO.starves)
    if starved:
        out.append("  starved by:")
        out += starved

    for h in sorted(g.objects(c, DHO.counters)):
        out.append(f"  counters: {label(g, h)}   [derived by rule R1 from SN 46.51: same object fuels this and starves that]")
    for f in sorted(g.subjects(DHO.counters, c)):
        d = next(g.subjects(DHO.derivedSubject, f), None)
        obj = next((v for v in g.objects(d, DHO.via) if (v, RDF.type, DHO.AttentionObject) in g), None) if d else None
        out.append(f"  countered by: {label(g, f)}   [derived by rule R1, shared object: {label(g, obj) if obj else '?'}]")

    advice = list(g.subjects(DHO.develop, c)) + list(g.subjects(DHO.whenMind, c))
    if advice:
        out.append("  timing (SN 46.53):")
        for a in sorted(advice, key=str):
            state, factor, timing = g.value(a, DHO.whenMind), g.value(a, DHO.develop), g.value(a, DHO.timing)
            when = f"when the mind is {label(g, state).replace(' mind', '')}" if state else "at any time"
            out.append(f"    - {when}: {label(g, timing)} {label(g, factor)}   [sutta {cite(g, a)}]")

    for op in g.subjects(DHO.target, c):
        out.append(f"  opposed by: {label(g, g.value(op, DHO.opponent))}   "
                   f"[commentary, unverified: {g.value(op, DHO.citationNote)}]")
    for op in g.subjects(DHO.opponent, c):
        out.append(f"  opposes: {label(g, g.value(op, DHO.target))}   "
                   f"[commentary, unverified: {g.value(op, DHO.citationNote)}]")

    # Outcomes and conditions (D13) about this node, or about a list it belongs to.
    subjects = [c] + sorted(g.objects(c, DHO.memberOf))

    def via(node):
        return "" if node == c else f" (as one of {label(g, node)})"

    rows = []
    for s in subjects:
        for o in g.subjects(DHO.of, s):
            rows.append(("outcomes", f"{label(g, g.value(o, DHO.effect))} {label(g, g.value(o, DHO.to))}{via(s)}", o))
        for o in g.subjects(DHO.to, s):
            rows.append(("outcomes", f"{label(g, g.value(o, DHO.of))} → {label(g, g.value(o, DHO.effect))}", o))
        for k in g.subjects(DHO.conditioned, s):
            res = g.value(k, DHO.result)
            cond = label(g, g.value(k, DHO.condition))
            if res:
                text = f"when {cond} is present, these {label(g, res)}{via(s)}"
            else:
                text = f"{cond} → {label(g, g.value(k, DHO.relation))} this{via(s)}"
            rows.append(("conditions", text, k))
        for k in g.subjects(DHO.condition, s):
            rows.append(("conditions", f"{label(g, g.value(k, DHO.relation))} {label(g, g.value(k, DHO.conditioned))}"
                         + (f": {label(g, g.value(k, DHO.result))}" if g.value(k, DHO.result) else ""), k))
    for section in ("outcomes", "conditions"):
        items = [r for r in rows if r[0] == section]
        if items:
            out.append(f"  {section}:")
            for _, text, node in sorted(items, key=lambda r: r[1]):
                out.append(f"    - {text}   \"{g.value(node, DHO.wording)}\"  [sutta {cite(g, node)}]")
                note = g.value(node, SKOS.note)
                if note:
                    out.append(f"        note: {note}")

    for d in g.subjects(DHO.defines, c):
        out.append(f"  is defined as: {label(g, g.value(d, DHO['as']))}   [sutta {cite(g, d)}]")
    for d in g.subjects(DHO['as'], c):
        out.append(f"  defines: {label(g, g.value(d, DHO.defines))} is {label(g, c)}   [sutta {cite(g, d)}]")

    related = set(g.objects(c, DHO.editorialRelated)) | set(g.subjects(DHO.editorialRelated, c))
    for r in sorted(related):
        out.append(f"  see also: {label(g, r)}   [editor's link, not a textual claim]")
    return out


def cmd_ask(text: str) -> int:
    g, *_ = build()
    hits = resolve(g, text)
    if not hits:
        print(f"No concept matches '{text}'. The ontology covers only the texts in COVERAGE.md "
              "(the hindrances, awakening factors and first-jhāna factors, and what SN 46 says about them).")
        return 1
    print(f"'{text}' resolves to {len(hits)} concept(s): " + ", ".join(label(g, h) for h in hits))
    for h in hits:
        print("\n".join(card(g, h)))
    return 0


def cmd_sense(word: str) -> int:
    g, *_ = build()
    entries = [e for e in g.subjects(RDF.type, ONTOLEX.LexicalEntry)
               if any(fold(str(f)) == fold(word) for form in g.objects(e, ONTOLEX.canonicalForm)
                      for f in g.objects(form, ONTOLEX.writtenRep))]
    if not entries:
        print(f"No lexical entry for '{word}'.")
        return 1
    for e in entries:
        senses = sorted(g.objects(e, ONTOLEX.sense))
        print(f"'{word}' has {len(senses)} senses:")
        for s in senses:
            concept = g.value(s, ONTOLEX.reference)
            print(f"\n  - {label(g, concept)}")
            print(f"      {g.value(concept, SKOS.definition)}")
            for p in sorted(g.objects(s, DHO.citedBy), key=str):
                print(f"      e.g. {g.value(p, DHO.segment)}: \"{quote(g, p)}\" / \"{quote(g, p, 'pi')}\"")
            for p in g.subjects(DHO.usesSense, s):
                print(f"      tagged passage {g.value(p, DHO.segment)} (by {g.value(p, DHO.senseAssignedBy)})")
        contested = [p for p in g.subjects(DHO.translatorRendering, None)]
        for p in contested:
            print(f"\n  contested, left unassigned: {g.value(p, DHO.segment)} \"{quote(g, p, 'pi')}\""
                  f" (rendered '{g.value(p, DHO.translatorRendering)}')")
    return 0


def cmd_check(extra: list[Path] | None = None) -> int:
    g, asserted, derived, inferred = build(extra)
    print(f"asserted triples : {asserted}")
    print(f"inferred by OWL  : {inferred}")
    for rule, n in derived.items():
        print(f"derived by {rule}: {n} triples")

    print("\nclassified by the reasoner (never typed by hand):")
    for cls in (DHO.Hindrance, DHO.AwakeningFactor, DHO.JhanaFactor):
        members = sorted(label(g, m) for m in g.subjects(RDF.type, cls))
        print(f"  {label(g, cls):28} {len(members)}: {', '.join(members)}")

    print("\nrule R1, awakening factor counters hindrance:")
    for f, h in sorted(g.subject_objects(DHO.counters)):
        print(f"  {label(g, f)} -> {label(g, h)}")

    conforms, results = run_shacl(g)
    violations = [r for r in results if r["severity"] == "Violation"]
    warnings = [r for r in results if r["severity"] == "Warning"]
    print(f"\nSHACL: {'PASS' if conforms else 'FAIL'}  ({len(violations)} violations, {len(warnings)} warnings)")
    for r in results:
        print(f"  [{r['severity']}] {r['focus']}: {r['message']}")
    return 0 if conforms else 1


def cmd_query(path: str) -> int:
    """Run a SPARQL SELECT over the reasoned graph (inferred types and R1 links included)."""
    g, *_ = build()
    result = g.query(Path(path).read_text(encoding="utf-8"))
    cols = [str(v) for v in result.vars]

    def show(v):
        if v is None:
            return ""
        return label(g, v) if isinstance(v, URIRef) and str(v).startswith(str(DHO)) else str(v)

    rows = [[show(row[c]) for c in cols] for row in result]
    widths = [min(60, max([len(c)] + [len(r[i]) for r in rows])) for i, c in enumerate(cols)]
    print("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print("  ".join(x[:60].ljust(w) for x, w in zip(r, widths)))
    print(f"\n{len(rows)} row(s)")
    return 0


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(argv) < 2 or argv[1] not in {"check", "ask", "sense", "query"}:
        print(__doc__)
        return 2
    if argv[1] == "query":
        return cmd_query(argv[2])
    if argv[1] == "check":
        return cmd_check([Path(p) for p in argv[2:]])
    if argv[1] == "ask":
        return cmd_ask(" ".join(argv[2:]))
    return cmd_sense(" ".join(argv[2:]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
