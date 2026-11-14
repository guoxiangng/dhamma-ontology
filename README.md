# dhamma-ontology

A small, **citation-first** ontology of Buddhist teachings, built from the Pali suttas. Every link points to the exact passage that states it, and a reasoner, rules and validation checks run over the whole thing.

It starts with one well-defined topic: the **five hindrances**, the **seven awakening factors** and the **factors of the first jhāna**, and what the Linked Discourses on the Awakening Factors (SN 46) say about what conditions them and where they lead. The aim is to show what an ontology can do that a glossary, a graph of related terms or a plain LLM can't, on material that can be checked line by line.

> **Status: v0.1, a personal learning project.** It draws on 33 texts out of SuttaCentral's 14,080 suttas ([COVERAGE.md](COVERAGE.md)). The modelling was done by a practitioner with an AI assistant, and **no qualified reader has reviewed it yet**. The quotes are the texts' own words; the structure is our interpretation, and every choice is written down in [DECISIONS.md](DECISIONS.md) so you can disagree with a specific one. Corrections are very welcome ([CONTRIBUTING.md](CONTRIBUTING.md)).

## What it does

```text
$ python scripts/dho.py ask "monkey mind"
'monkey mind' resolves to 2 concept(s): restlessness and remorse, restless mind

=== restlessness and remorse · uddhaccakukkucca · 掉舉惡作
  is a: Hindrance   (inferred by the reasoner from list membership)
  member of: the five corruptions of the mind   [sutta sn46.33:2.1, 2.3–2.4]
  member of: the five hindrances   [sutta mn43:20.3; sn46.37:1.1, 1.3–1.7; sn46.38:2.1–2.2; sn46.40:1.1, 1.3; sn46.51:1.2]
  fuelled by:
    - frequent irrational application of mind to the unsettled mind
        "There is the unsettled mind."  [sutta sn46.2:5.2–5.3; sn46.51:4.2–4.3]
  starved by:
    - frequent rational application of mind to the settled mind
        "There is the settled mind."  [sutta sn46.51:16.2–16.3]
  opposed by: bliss   [commentary, unverified: Visuddhimagga IV.86 (citing the Peṭakopadesa)]
  see also: restless mind   [editor's link, not a textual claim]

=== restless mind · uddhataṁ cittaṁ
  is a: mind state
  timing (SN 46.53):
    - when the mind is restless: right time to develop tranquility   [sutta sn46.53:13.1, 13.3]
    - when the mind is restless: wrong time to develop energy   [sutta sn46.53:10.1, 10.3]
    ...
```

- **Finds concepts from everyday words, Pali or Chinese** ("sleepy", "uddhacca kukkucca", "喜").
- **Classifies by reasoning.** Nothing is typed "hindrance" by hand; the OWL reasoner works it out from list membership. Rapture comes out as both an awakening factor and a jhāna factor.
- **Derives what a sutta implies but never states.** Rule R1 finds which awakening factor counters which hindrance from objects they share in SN 46.51. It finds exactly two pairs. It does *not* produce "tranquility counters restlessness", which many teachers say but SN 46.51 doesn't support.
- **Keeps layers apart.** Sutta, commentary and editor claims are always labelled, and the checks stop one being filed as another.
- **Keeps the text's own words.** Outcome and condition claims ("good friendship is the forerunner of the awakening factors") use a small controlled set of relations for querying, plus the sutta's exact wording; a check fails if that wording isn't in the cited passage.
- **Separates the meanings of one word.** `sense dhamma` shows four meanings of *dhamma*, each backed by a passage, and one contested use left unassigned.
- **Checks itself.** SHACL rules verify that list counts match the text, every claim is cited, cited passages exist, derived links are never typed by hand, and every text has an honest coverage record. Deliberately broken files in `tests/broken/` prove each rule fires.

Two viewers, both single HTML files you can open locally:

- **Graph** (`viz/graph.html`): click a concept to see its links, each with its quote and a link to SuttaCentral.
- **Review** (`viz/review.html`): each text segment by segment, with the claims that rest on each segment, the coverage record, the eval questions that cite it, and a "report" link that opens a correction issue for that segment. Segments with no claim stay visible, so gaps are as easy to see as what was encoded.

## Quick start

Python 3.11+.

```bash
git clone https://github.com/guoxiangng/dhamma-ontology && cd dhamma-ontology
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/dho.py ask sleepy
python scripts/dho.py sense dhamma
python scripts/dho.py check                   # reason + rules + SHACL report
python scripts/dho.py query queries/01-what-fuels-and-starves.rq
python -m pytest -q tests
```

## Using the data

| You want | Use |
|---|---|
| One file to load anywhere | `dist/dhamma-ontology.ttl` (as written) or `dist/dhamma-ontology-inferred.ttl` (after reasoning and rule R1) |
| To browse the classes | Open `dist/dhamma-ontology.ttl` in [Protégé](https://protege.stanford.edu/) and run a reasoner |
| To query it | Any SPARQL store (Jena Fuseki, GraphDB, Oxigraph), or `python scripts/dho.py query <file.rq>`; examples in [`queries/`](queries/) |
| A simple node/edge graph | `dist/graph.json` (what the viewer uses) |
| To use it from Python | `rdflib.Graph().parse("dist/dhamma-ontology-inferred.ttl")` |

Rebuild `dist/` with `python scripts/release.py`.

## Project documents

| | |
|---|---|
| [DECISIONS.md](DECISIONS.md) | Every modelling choice, why it was made, and corrections (D1–D13) |
| [COVERAGE.md](COVERAGE.md) | Which texts are encoded, how much of each, what's left out, review status. Generated |
| [triage/](triage/) | Collections sorted by the modelling pattern each sutta needs, before ingesting them |
| [eval/](eval/) | A golden question set for testing whether the ontology helps an LLM answer more faithfully, and the method |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to report an error or add a text |

## Layout

| Path | What |
|---|---|
| `ontology/dho-schema.ttl` | Schema: classes, and what each relation means |
| `data/*.ttl` | Lists and qualities, SN 46.51 / 46.2 nutriments, SN 46.53 timing, SN 46 outcomes and conditions, MN 44 definition, commentary pairings, dhamma senses, coverage records |
| `data/passages.ttl` | **Generated**: cited passages with exact English and Pali |
| `rules/` | Rule R1 (SPARQL CONSTRUCT) |
| `shapes/dho-shapes.ttl` | SHACL checks S1–S14 |
| `scripts/` | `dho.py` (check, ask, sense, query), `sc.py` (fetch and read SuttaCentral texts), `build_passages.py`, `coverage.py`, `export_graph.py`, `export_review.py`, `release.py` |
| `queries/` | Example SPARQL queries |
| `viz/` | Viewer templates; `export_graph.py` builds `viz/graph.html`, `export_review.py` builds `viz/review.html` |
| `tests/` | Clean data passes; each file in `tests/broken/` is caught by the check it targets |
| `sources/suttacentral/` | Cached SuttaCentral text (CC0) and the canon index |
| `dist/` | Single-file downloads |

## Working on it with Claude

The repo includes [CLAUDE.md](CLAUDE.md), the project rules for Claude Code, and an `add-text` skill. In Claude Code, run `/add-text sn46.1` and it follows the same steps for every new text:

1. Fetch and read every segment.
2. Map each claim to an existing pattern, or stop and propose a new one.
3. Write the data, the coverage record and eval questions.
4. Run all the checks.

The rules are strict on purpose: nothing is modelled from memory of a text, only from the text itself.

## Standards

RDF/Turtle, OWL 2 RL (via [owlrl](https://github.com/RDFLib/OWL-RL)), SKOS, [OntoLex-Lemon](https://www.w3.org/2016/05/ontolex/), SHACL (via [pySHACL](https://github.com/RDFLib/pySHACL)) and SPARQL.

## Sources and licence

- **Sutta text:** from [SuttaCentral](https://suttacentral.net). English by Bhikkhu Sujato, Pali from the Mahāsaṅgīti edition, both dedicated to the public domain (CC0).
- **Commentary pairings:** cite the Visuddhimagga by reference only, and are flagged as unverified.
- **This repo:**
  - Code (`scripts/`, `eval/*.py`, `tests/`, `viz/`) is under the [MIT licence](LICENSE).
  - The ontology, data, rules, shapes and queries are dedicated to the public domain under [CC0 1.0](LICENSE-DATA), like the texts they're built from.

This is not an authority on the Dhamma. For guidance in practice, a teacher and a community remain the place to go.
