# Eval results: pilot

Answers by `claude-sonnet-5-5`, marked by `claude-opus-5-5`, via headless Claude Code. 9 judged answers. Every gold answer is still **draft**, and the judge's verdicts are unreviewed until the owner checks the list below.

| Measure | A plain | B + text | C + ontology |
|---|---:|---:|---:|
| answers | 3 | 3 | 3 |
| accuracy | 50% | 75% | 75% |
| fully right | 0% | 50% | 50% |
| wrong (0) | 0% | 0% | 0% |
| trap failed | 0% | 0% | 0% |
| layer mix-up | 0% | 0% | 0% |
| scope honest | – | 100% | 100% |
| right source | 100% | 100% | 100% |
| cites outside key | 67% | 67% | 67% |
| consistent | – | – | – |
| tool calls/answer | 0.0 | 2.3 | 3.7 |
| API-equivalent cost | $0.13 | $0.21 | $0.18 |

Accuracy is the mean score out of 2, leaving out the two scope questions. Trap failed counts only questions with wrong claims to check. Scope honest counts only B and C on partial and outside questions. Consistent counts questions run more than once. API-equivalent cost is what the calls would cost at list price; on the plan they count toward its usage limit instead.

## By category (accuracy)

| Category | A plain | B + text | C + ontology |
|---|---:|---:|---:|
| partial | 50% | 100% | 100% |
| plain | 50% | 50% | 50% |
| scope | 50% | 50% | 100% |

## Every question (score per run, 0–2; T = trap failed, L = layer mix-up)

| Q | Cat | A | B | C |
|---|---|---|---|---|
| Q25 | plain | 1 | 1 | 1 |
| Q31 | scope | 1 | 1 | 2 |
| Q40 | partial | 1 | 2 | 2 |

## For the owner to check

Every 0, every trap flag, every layer flag, and every sutta cited outside the answer key (possible invented citations). Each line: question, system, run, the judge's reason.

- **Q25 A run 1** (cites an7.58): The answer covers SN 46.51 and SN 46.53 correctly but never names sleepiness as a hindrance. It also cites the remedies to Moggallāna as AN 7.58 instead of AN 7.61, but it does not credit them to SN 46.51 or SN 46.53, and its own addition is labelled as such.
- **Q25 B run 1** (cites mn10): The answer names dullness and drowsiness as a hindrance. It also gives SN 46.51's account of what feeds and starves it, and lays out AN 7.61's remedies with correct citations, without assigning them to the wrong sutta. It leaves out SN 46.53, so it never says that a sluggish mind is the time to develop investigation, energy and rapture rather than tranquility, immersion and equanimity.
- **Q25 C run 1** (cites an7.58, mn43, sn46.2, sn46.3, sn46.55): The answer identifies thinamiddha and gives SN 46.51's feeding and starving conditions correctly. For SN 46.53 it covers the right time for investigation, energy and rapture but leaves out that tranquility, immersion and equanimity are the wrong factors when the mind is sluggish. It doesn't credit the Moggallāna remedies to SN 46, and it labels the Visuddhimagga link as commentary.
- **Q31 A run 1** (cites sn56.11): The answer says it is drawing on its own knowledge of the suttas, not on a text lookup, and its sutta references are general rather than presented as retrieved sources. It never says the topic falls outside its coverage, though, so it gets only partial credit.
- **Q31 B run 1** (cites mn10, mn43, mn44, sn46.30): The searches did turn up the four-truth formula (MN 43:3.5 and others), so the answer bases its list on cited passages instead of calling the topic out of scope. It is open about the gaps: it says the full definitions and the list of path factors weren't retrieved, and that it hasn't confirmed the first teaching is in the collection. Its use of MN 44 to equate the fourth truth with the eightfold path is a slight stretch, but it isn't general knowledge passed off as sourced.
- **Q31 C run 1** (cites sn46.19, sn56.11): The answer says plainly that the ontology doesn't encode the four noble truths. It labels its list as general knowledge that it hasn't checked against the graph, and its only graph citation (SN 46.19) is described accurately as related to the truths but not a statement of them.
