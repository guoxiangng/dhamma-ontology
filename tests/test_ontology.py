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
    assert dho.resolve(graph, "喜") == [dho.DHO.Rapture]


@pytest.mark.parametrize("fixture, expected", [
    ("hindrance-is-factor.ttl", ["S1:", "S2:"]),
    ("wrong-attention.ttl", ["S5:"]),
    ("uncited-nutriment.ttl", ["S4:"]),
    ("fake-passage.ttl", ["S8:"]),
    ("hand-written-counters.ttl", ["S9:"]),
    ("commentary-as-sutta.ttl", ["S7:"]),
    ("text-without-coverage.ttl", ["S10:"]),
    ("partial-without-left-out.ttl", ["S10:"]),
])
def test_broken_data_is_caught(fixture, expected):
    g, *_ = dho.build([BROKEN / fixture])
    conforms, results = dho.run_shacl(g)
    assert not conforms
    messages = " | ".join(r["message"] for r in results if r["severity"] == "Violation")
    for code in expected:
        assert code in messages, f"{fixture}: expected {code} in {messages}"
