# Eval: does the ontology help an LLM answer better?

The question this answers: for questions about the suttas, does an LLM do better with this ontology than without it, and better than with plain text search over the same suttas?

## Files

| File | What |
|---|---|
| `questions.toml` | 57 questions with gold answers, cited segments and "fails if it says" traps |
| `check_gold.py` | Verifies every cited segment exists and every Pali term in a gold answer appears in the cited Pali; writes the review sheet |
| `GOLD-REVIEW.md` | **Generated.** Each gold answer beside the exact English and Pali it rests on, for a human to check |
| `systems.py` | The three systems: shared instructions, and the tools B and C call (no model calls) |
| `run.py` | The runner: asks each system each question through headless Claude Code, has a judge mark each answer, writes the report |
| `mcp_server.py` | Serves B's or C's tools to Claude Code over MCP |
| `requirements.txt` | Extra package the runner needs (`mcp`) |
| `results/<name>/` | **Generated** by a run: `answers.jsonl`, `judgments.jsonl`, `config.json`, `summary.md` |

```bash
$PY eval/check_gold.py                                    # gold answers: segments exist, Pali terms match
$PY eval/run.py plan                                      # dry run: no model calls; counts and tool sizes
$PY eval/run.py tool C lookup "monkey mind"               # try one of B's or C's tools, no model
$PY eval/run.py run --out eval/results/<name>             # the real run (resumable)
$PY eval/run.py report --out eval/results/<name>          # rebuild summary.md from the logs
```

## Where it runs

On your machine, through headless Claude Code (`claude -p`) on the owner's Claude plan: nothing is deployed and nothing is billed per call; usage counts toward the plan's limits. If a run hits the limit it stops, and rerunning the same command carries on where it stopped.

Each call is isolated so that no system can reach the answer key:

| Flag | Effect |
|---|---|
| `--system-prompt` | Our instructions replace Claude Code's own (a test call received 140 input tokens: the instruction and the question, nothing else) |
| `--tools ""` | No built-in tools: no file reading, no shell, no web |
| `--mcp-config` + `--strict-mcp-config` | Only B's or C's tool server (`mcp_server.py`); the test call listed exactly those tools |
| `--setting-sources project`, run from an empty temporary folder | No CLAUDE.md, hooks, skills or memory from this project |

The judge gets the answer key in its prompt and no tools. The runner uses the newest Claude Code bundled with the VS Code extension (set `CLAUDE_BIN` to choose another), since older standalone versions can't run the current models.

| Role | Model |
|---|---|
| Answers (A, B and C) | Claude Sonnet 5.5, effort medium (`--model` to change) |
| Judge | Claude Opus 5.5, effort medium (`--judge` to change) |

The judge is a stronger model than the one answering. It still makes mistakes, so the owner checks its verdicts (below).

## Systems compared

All three use the same model and the same instructions ("answer from the suttas; cite; say when you don't know"; in `systems.py`). B and C add one sentence saying what their tools reach. Temperature can't be set, so consistency is measured by running questions more than once (`--runs`; default 1 to spare the plan's limits).

| | System | Gets |
|---|---|---|
| **A** | Plain LLM | The question only |
| **B** | LLM + text search | Tools over the same cached SuttaCentral texts the ontology is built from, including the parts it left out: keyword search (BM25) over every segment in English and Pali, read a whole sutta, list the suttas |
| **C** | LLM + ontology | Tools over the reasoned graph: look up a word (the concept cards `dho.py ask` prints), list concepts, a word's senses, the text of cited passages, coverage records |

B and C run the same tool loop (up to 10 turns). The only difference between them is what their tools can reach.

B is the control that matters. "Ontology beats a bare LLM" is easy to show and not very interesting. The real question is whether structure beats retrieval over the same text.

## Question categories

| Category | Tests | Count |
|---|---|---:|
| recall | What a text says | 22 |
| list | Completeness of numbered lists | 5 |
| trap | A popular claim the text doesn't support, or a near-miss reading | 15 |
| derived | A link the text implies but never states | 1 |
| layer | Keeping sutta and commentary apart | 4 |
| plain | Everyday-language questions | 2 |
| sense | Which meaning of an ambiguous word | 3 |
| citation | Naming the right source | 1 |
| partial | A part of a covered text the ontology left out | 2 |
| scope | Outside the ontology entirely | 2 |

Q40 (left out of the ontology, but in B's text) is there on purpose: B should win it. (Q17 had that role until its simile was added to the ontology.) A fair eval includes questions the favoured system should lose.

## Scoring each answer

| Measure | How | Scored by |
|---|---|---|
| Correct | 2 = all gold points, 1 = some, 0 = none or wrong (scope questions excluded) | LLM judge marks each gold point yes / partly / no, given the gold and the cited passages; the script turns that into 0–2. Owner checks every 0 and a sample of the rest |
| Complete | Share of list items present (list questions) | Script |
| Fails a trap | Any `must_not` claim present | LLM judge; owner checks every flag |
| Right source | Names a text in `segments` or `also_ok` | Script (regex over sutta references) |
| Invented citation | Cites a sutta for something it doesn't say | Script lists every sutta cited outside the gold list; owner checks each |
| Layer honesty | Commentary or modern ideas presented as the Buddha's words | LLM judge; owner checks |
| Scope honesty | For `partial` and `outside` questions, B and C only: says what its sources don't cover, and doesn't present general knowledge as sourced | LLM judge, shown the system's tool calls |
| Consistency | Same verdict on all three runs | Script |

The headline numbers for the write-up: accuracy, trap failures, invented citations, layer mix-ups, scope honesty, consistency, each for A, B and C.

## Limitations, stated up front

- **Small:** 57 questions on a narrow slice (76 suttas, mostly SN 46, plus MN 43, MN 44 and a few word senses).
- **Home advantage:** the questions were written by the same people who built the ontology, so they lean towards what it models. The traps and the B-should-win question partly offset this; outside questions written by someone else would offset it more.
- **Gold drafted with an AI assistant.** Every gold point cites segments that a script checks, and Pali terms are checked against the cited Pali. Gold is still `draft` until the owner checks it in `GOLD-REVIEW.md`. Q21's pairing rests on a text we don't hold (Visuddhimagga) and stays unverified until checked against an edition.
- **The judge is a model too.** It sees the gold and the passages, not the whole canon; `summary.md` lists every verdict the owner should check.
- **Absence claims** ("no sutta says X") are only as good as the coverage in `COVERAGE.md`.
