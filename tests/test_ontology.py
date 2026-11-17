"""The ontology must pass its own checks, and each deliberately broken file
in tests/broken/ must be caught by the check it targets."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from rdflib.namespace import RDF

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dho  # noqa: E402

BROKEN = ROOT / "tests" / "broken"


@pytest.fixture(scope="module")
def graph():
    g, *_ = dho.build()
    return g


def test_clean_data_passes(graph):
    conforms, results = dho.run_shacl(graph)
    violations = [r for r in results if r["severity"] == "Violation"]
    assert conforms, violations
    # The only warnings allowed are the five unverified commentary pairings.
    assert sorted(r["focus"] for r in results) == [f"dho:op-0{i}" for i in range(1, 6)]


def test_fully_encoded_texts_have_no_uncited_untranslated_pali(graph):
    """The 2026-11-15 audit found teaching given only in the Pali (SN 46.49, 46.50). In a text
    marked fully encoded, every Pali segment with no English must be cited, unless it is a
    one-word end marker ("Navamaṁ."), a question, or a chapter summary verse."""
    import json
    from rdflib.namespace import SKOS  # noqa: F401
    src = dho.ROOT / "sources" / "suttacentral"
    cited = {str(graph.value(p, dho.DHO.segment)) for p in graph.subjects(RDF.type, dho.DHO.Passage)
             if any(True for _ in graph.subjects(dho.DHO.citedBy, p))}
    missing = []
    for t in graph.subjects(dho.DHO.coverage, dho.DHO.FullyEncoded):
        uid = str(t).split("#t-", 1)[1]
        en_f, pi_f = src / f"{uid}_en.json", src / f"{uid}_pli.json"
        if not pi_f.exists():
            continue
        en = json.loads(en_f.read_text(encoding="utf-8")) if en_f.exists() else {}
        pi = json.loads(pi_f.read_text(encoding="utf-8"))
        in_summary = False
        for k, v in pi.items():
            if k.split(":")[0] != uid or k.split(":")[1].startswith("0."):
                continue
            if v.strip().startswith("Tassuddānaṁ"):
                in_summary = True
            if en.get(k, "").strip() or in_summary or len(v.split()) < 3 or v.strip().rstrip("”’'").endswith("?"):
                continue
            if k not in cited:
                missing.append(k)
    assert not missing, missing


def test_reasoner_classifies_from_lists(graph):
    assert len(set(graph.subjects(RDF.type, dho.DHO.Hindrance))) == 5
    assert len(set(graph.subjects(RDF.type, dho.DHO.AwakeningFactor))) == 7
    assert len(set(graph.subjects(RDF.type, dho.DHO.JhanaFactor))) == 5
    # Rapture is in two lists, so it is both.
    assert (dho.DHO.Rapture, RDF.type, dho.DHO.AwakeningFactor) in graph
    assert (dho.DHO.Rapture, RDF.type, dho.DHO.JhanaFactor) in graph


def test_rule_r1_derives_exactly_two_pairs(graph):
    pairs = set(graph.subject_objects(dho.DHO.counters))
    assert pairs == {
        (dho.DHO.Energy, dho.DHO.DullnessDrowsiness),
        (dho.DHO.Investigation, dho.DHO.Doubt),
    }


def test_resolve_finds_hindrance_and_mind_state(graph):
    assert set(dho.resolve(graph, "monkey mind")) == {dho.DHO.RestlessnessRemorse, dho.DHO.RestlessMind}
    assert dho.resolve(graph, "uddhacca kukkucca") == [dho.DHO.RestlessnessRemorse]
    # 喜 is the standard Chinese for both pīti (rapture) and muditā (rejoicing); D24 shows both.
    assert set(dho.resolve(graph, "喜")) == {dho.DHO.Rapture, dho.DHO.Rejoicing}
    assert set(dho.resolve(graph, "慈悲")) == {dho.DHO.Love, dho.DHO.Compassion}


@pytest.mark.parametrize("fixture, expected", [
    ("hindrance-is-factor.ttl", ["S1:", "S2:"]),
    ("wrong-attention.ttl", ["S5:"]),
    ("uncited-nutriment.ttl", ["S4:"]),
    ("fake-passage.ttl", ["S8:"]),
    ("hand-written-counters.ttl", ["S9:"]),
    ("commentary-as-sutta.ttl", ["S7:"]),
    ("text-without-coverage.ttl", ["S10:"]),
    ("partial-without-left-out.ttl", ["S10:"]),
    ("wording-not-in-text.ttl", ["S14:"]),
    ("condition-incomplete.ttl", ["S13:"]),
    ("outcome-bad-effect.ttl", ["S12:"]),
    ("division-one-part.ttl", ["S15:"]),
    ("abbreviation-unflagged.ttl", ["S16:"]),
    ("simile-incomplete.ttl", ["S17:"]),
])
def test_broken_data_is_caught(fixture, expected):
    g, *_ = dho.build([BROKEN / fixture])
    conforms, results = dho.run_shacl(g)
    assert not conforms
    messages = " | ".join(r["message"] for r in results if r["severity"] == "Violation")
    for code in expected:
        assert code in messages, f"{fixture}: expected {code} in {messages}"


def test_pali_labels_appear_in_cited_pali(graph):
    """Concepts reached by outcome, condition and division claims: each word of their Pali label
    appears (case endings tolerated) in the Pali of the passages those claims cite."""
    import unicodedata
    from rdflib.namespace import SKOS

    def fold(s):
        s = unicodedata.normalize("NFKD", s.lower())
        return "".join(c for c in s if not unicodedata.combining(c) and c.isalpha())

    blob = {}
    for cls, props in ((dho.DHO.Outcome, (dho.DHO.of, dho.DHO.to)),
                       (dho.DHO.Condition, (dho.DHO.condition, dho.DHO.conditioned)),
                       (dho.DHO.Division, (dho.DHO.divides, dho.DHO.part))):
        for claim in graph.subjects(RDF.type, cls):
            pali = fold(" ".join(str(graph.value(p, dho.DHO.textPi) or "") for p in graph.objects(claim, dho.DHO.citedBy)))
            for prop in props:
                for c in graph.objects(claim, prop):
                    blob[c] = blob.get(c, "") + pali
    missing = []
    for c, text in blob.items():
        for lab in graph.objects(c, SKOS.prefLabel):
            if lab.language == "pi":
                for word in str(lab).split():
                    w = fold(word)
                    if (w[:-1] if len(w) > 4 else w) not in text:
                        missing.append(f"{dho.short(c)}: {word}")
    assert blob and not missing, missing
