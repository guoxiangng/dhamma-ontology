---
name: add-text
description: Add a sutta to the dhamma-ontology, text by text, the same way every time - fetch and read the whole text, map each teaching to an existing pattern (or stop and propose one), write the data, coverage record and eval questions, then run every check. Use when the user says /add-text <uid>, "add SN 46.2", "encode the next sutta", or asks to expand coverage.
---

# Add a text to the ontology

The goal is integrity, not volume. The project owner is a practitioner, not a teacher, and relies on this workflow to keep the modelling faithful. Every claim must come from the text in front of you, never from memory of the text.

Arguments: one SuttaCentral uid (`sn46.2`, `mn20`, `an7.61`), or several, processed one at a time.

Setup:

```bash
PY=python                       # or the path to your venv's python
# export SSL_CERT_FILE=<ca-bundle.pem>   # only if behind a TLS-inspecting proxy
```

## 1. Fetch and read all of it

```bash
$PY scripts/sc.py fetch <uid>
$PY scripts/sc.py show <uid> --cited      # every segment: id | English | Pali; * = already cited
```

Read every segment, English and Pali. Don't skim, and don't model from what you remember of the sutta.

## 2. Make a claim table before writing any data

For each teaching statement, list its segments and the pattern it fits:

| Pattern | Shape | Example |
|---|---|---|
| List membership | `dho:NumberedList` + `hasMember` + `expectedCount` + cite | five hindrances (sn46.51:1.2) |
| Nutriment | `dho:Nutriment`: object, attention, fuels/starves | n-01 … n-24 |
| Timing advice | `dho:TimingAdvice`: whenMind, develop, timing | ta-01 … ta-13 |
| Attainment | `dho:Attainment`: givesUp / possesses a list | FirstJhana (mn43:20) |
| Definition | `dho:Definition`: defines X as Y | def-01 (mn44:12.2) |
| Outcome | `dho:Outcome`: of, effect (leads to / does not lead to / strengthens / weakens), to, **wording**, cite | o-02 (sn46.7:1.2) |
| Condition | `dho:Condition`: condition, relation (basis / forerunner / root / gives rise to / supports / when-then), conditioned, result, **wording**, cite | c-02 (sn46.12:1.2) |
| Word sense | OntoLex entry → sense → concept | lex-dhamma |
| Commentary claim | own node, `layer CommentaryLayer`, cite or citationNote | op-01 … op-05 |

Rules:

- **Already in the ontology?** Compare wording segment by segment (`sc.show` both texts). If it's the same claim, add a citation to the existing node (D12) and record any wording difference in the data file's comments. Never create a duplicate node.
- **Outcomes and conditions keep the text's own words** in `dho:wording`, copied verbatim from Sujato's English. S14 fails the build if they aren't in a cited passage.
- **No pattern fits?** Don't force it. Leave the claim out, list it in the coverage record's `leftOut`, and propose a pattern to the user with a draft DECISIONS.md entry. Similes are already waiting (see "Patterns not modelled yet" in DECISIONS.md).
- **Unsure what a passage means?** Leave it out or mark it contested (like mn10:36.2). Editor's links are only for the owner's own judgment, and are labelled as such.
- **Contradicts an existing decision?** Fix the data and add a dated *Correction* note to the decision, as D4 has. Tell the user prominently.

## 3. Write the data

- One file per text: `data/<uid>-<topic>.ttl`, with a header comment saying what it encodes.
- New concepts follow D9: English preferred label = Sujato's rendering; Pali from the text; Chinese only as the standard Buddhist term, supplied by the editor; hidden labels only for real everyday words.
- Classes come from list membership (D3). Never type `dho:Hindrance` etc. by hand.
- Derived links (`dho:counters`) are never written by hand (S9).

```bash
$PY scripts/build_passages.py      # regenerates data/passages.ttl; fails on any missing segment
```

## 4. Coverage record

Add a record to `data/coverage.ttl`: `coverage`, `review dho:Unreviewed`, `modelledOn`, `modelledBy`, `encodes`, and `leftOut` with section numbers. Check `leftOut` against the actual section list (`sc.py show`), not against memory.

## 5. Eval questions

Add 1–3 questions per text to `eval/questions.toml` (next free id, `status = "draft"`). At least one should be a trap: a popular claim, a misattribution, or a confusion with a neighbouring sutta. Put Pali terms in gold answers in brackets so the checker verifies them.

```bash
$PY eval/check_gold.py
```

## 6. Run every check

```bash
$PY scripts/dho.py check                       # 0 violations; warnings only the known S7 ones
$PY -m pytest -q -p no:cacheprovider tests
$PY scripts/coverage.py
$PY scripts/export_graph.py
$PY scripts/export_review.py      # then look at the new text in viz/review.html
$PY scripts/export_ask.py
```

Adding a new shape means adding a broken fixture in `tests/broken/` that it catches. 

## 7. Report to the user

Keep it short:

- claims added, concepts added, and citations added to existing claims;
- what was left out and why;
- patterns proposed;
- surprises, especially anything that corrected earlier work;
- what needs their review (the new eval gold answers, any editor's links).

Don't commit unless asked. If the graph page has been published, republish `viz/graph.html` to the same artifact.
