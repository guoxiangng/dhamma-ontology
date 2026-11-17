# Eval: does the ontology help an LLM answer better?

The question this answers: for questions about the suttas, does an LLM do better with this ontology than without it, and better than with plain text search over the same suttas?

## Files

| File | What |
|---|---|
| `questions.toml` | 57 questions with gold answers, cited segments and "fails if it says" traps |
| `check_gold.py` | Verifies every cited segment exists and every Pali term in a gold answer appears in the cited Pali; writes the review sheet |
| `GOLD-REVIEW.md` | **Generated.** Each gold answer beside the exact English and Pali it rests on, for a human to check |

```bash
$PY eval/check_gold.py
```

## Systems compared

All three use the same model, the same instructions ("answer from the suttas; cite; say when you don't know"), temperature 0, and three runs per question.

| | System | Gets |
|---|---|---|
| **A** | Plain LLM | The question only |
| **B** | LLM + text search | Top-k segments retrieved from the same cached SuttaCentral texts the ontology is built from (whole texts, including parts the ontology left out) |
| **C** | LLM + ontology | Tools over the reasoned graph: resolve words to concepts, get a concept's cited links, get a word's senses, get coverage |

B is the control that matters. "Ontology beats a bare LLM" is easy to show and not very interesting. The real question is whether structure beats retrieval over the same text.

## Question categories

| Category | Tests | Count |
|---|---|---:|
| recall | What a text says | 21 |
| list | Completeness of numbered lists | 5 |
| trap | A popular claim the text doesn't support, or a near-miss reading | 15 |
| derived | A link the text implies but never states | 1 |
| layer | Keeping sutta and commentary apart | 4 |
| plain | Everyday-language questions | 2 |
| sense | Which meaning of an ambiguous word | 3 |
| citation | Naming the right source | 1 |
| partial | A part of a covered text the ontology left out | 3 |
| scope | Outside the ontology entirely | 2 |

Q17 (left out of the ontology, but in B's text) is there on purpose: B should win it. A fair eval includes questions the favoured system should lose.

## Scoring each answer

| Measure | How | Scored by |
|---|---|---|
| Correct | 2 = all gold points, 1 = some, 0 = none or wrong | LLM judge with gold + quotes; owner checks every 0 and a sample of the rest |
| Complete | Share of list items present (list questions) | Script |
| Fails a trap | Any `must_not` claim present | LLM judge; owner checks every flag |
| Right source | Names a text in `segments` or `also_ok` | Script (regex over sutta references) |
| Invented citation | Cites a sutta for something it doesn't say | Owner, for every citation outside the gold list |
| Layer honesty | Commentary or modern ideas presented as the Buddha's words | LLM judge; owner checks |
| Scope honesty | For `partial` and `outside` questions: says it's outside what it can cite | LLM judge |
| Consistency | Same verdict on all three runs | Script |

The headline numbers for the write-up: accuracy, trap failures, invented citations, layer mix-ups, scope honesty, consistency, each for A, B and C.

## Limitations, stated up front

- **Small:** 57 questions on a narrow slice (76 suttas, mostly SN 46, plus MN 43, MN 44 and a few word senses).
- **Home advantage:** the questions were written by the same people who built the ontology, so they lean towards what it models. The traps and the B-should-win question partly offset this; outside questions written by someone else would offset it more.
- **Gold drafted with an AI assistant.** Every gold point cites segments that a script checks, and Pali terms are checked against the cited Pali. Gold is still `draft` until the owner checks it in `GOLD-REVIEW.md`. Q21's pairing rests on a text we don't hold (Visuddhimagga) and stays unverified until checked against an edition.
- **Absence claims** ("no sutta says X") are only as good as the coverage in `COVERAGE.md`.
