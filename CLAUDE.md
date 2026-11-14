# CLAUDE.md

A citation-first OWL/SKOS ontology of Buddhist teachings, built from SuttaCentral's Pali suttas. Read README.md for what it does and DECISIONS.md before changing anything structural.

## The rule that matters most

**Integrity over volume.** The maintainer is a practitioner, not a teacher, and relies on these rules to keep the modelling faithful:

- **Never model from memory of a text.** Fetch it and read every segment (`python scripts/sc.py show <uid> --cited`). If you remember something a sutta says, check it in the text before writing it down. That's how the MN 44 error in D4 was caught.
- **Quotes are never typed by hand.** `scripts/build_passages.py` generates `data/passages.ttl` from `sources/suttacentral/`.
- **Every claim cites a segment.** Commentary claims are labelled commentary. The project's own judgments are labelled editor's links (`dho:editorialRelated`) and never presented as the text's.
- **Don't force a fit.** If a teaching doesn't fit an existing pattern, leave it out, log it in the coverage record's `leftOut`, and propose a pattern (draft a DECISIONS.md entry) instead of bending one.
- **Say what you don't know.** Partial coverage says what it leaves out. Nothing is marked reviewed unless the maintainer or a qualified reader has reviewed it.
- **Corrections are visible.** If new evidence contradicts a decision, fix the data and add a dated *Correction* note to that decision. Never rewrite history quietly.

## Adding a text

Use the `add-text` skill (`.claude/skills/add-text/SKILL.md`). It covers fetching, the claim table, patterns, coverage, eval questions and checks.

## Commands

```bash
python scripts/dho.py check                    # reason + rule R1 + SHACL; must be 0 violations
python -m pytest -q -p no:cacheprovider tests  # clean data passes; tests/broken/* each caught
python eval/check_gold.py                      # gold answers: segments exist, Pali terms match
python scripts/coverage.py                     # regenerate COVERAGE.md
python scripts/export_graph.py                 # rebuild viz/graph.html
python scripts/export_review.py                # rebuild viz/review.html (segment-by-segment review)
python scripts/release.py                      # rebuild dist/
python scripts/sc.py fetch|show <uid>          # cache / read a SuttaCentral text
```

Behind a TLS-inspecting proxy, set `SSL_CERT_FILE` to your CA bundle before `sc.py fetch`.

## Conventions

- **Namespace:** `dho: <https://guoxiangng.github.io/dhamma-ontology/ns#>`. Passages are `dho:p-<uid>-<segment>`, texts `dho:t-<uid>`.
- **Labels (D9):** English preferred label = Sujato's rendering; Pali from the text; Chinese = the standard term, editor-supplied; hidden labels only for real everyday words.
- **Classes like Hindrance are defined by list membership (D3).** Never type them by hand. `dho:counters` comes only from rule R1 (S9).
- **One claim stated in several suttas is one node with several citations (D12).**
- **New checks:** a new SHACL shape gets a broken fixture in `tests/broken/` and a line in `tests/test_ontology.py`.
- **Generated files:** don't edit `data/passages.ttl`, `COVERAGE.md`, `eval/GOLD-REVIEW.md`, `viz/graph.html`, `viz/review.html` or `dist/`. Regenerate them.
- **Eval:** new questions start `status = "draft"`. Only the maintainer marks them `checked`.
