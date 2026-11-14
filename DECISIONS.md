# Modelling decisions

An ontology can't be neutral: every structural choice is a position. This file records each choice, why it was made, and what it costs, so a reader can disagree with a specific decision instead of with the whole thing.

This is a personal project with no institutional vetting. The ground rule follows from that.

## D1. Citation first: the text makes the claims, not us

Every doctrinal link cites the passage that states it, down to the SuttaCentral segment (e.g. `sn46.51:16.2`). Quotes are generated from SuttaCentral's CC0 data by `scripts/build_passages.py` and never typed by hand. SHACL fails the build if a claim has no citation (S4, S6) or cites a passage that doesn't exist (S8).

## D2. Nutriment is a node, not an arrow

SN 46.51 doesn't say "beauty fuels sensual desire". It says *frequent irrational attention* to *the feature of beauty* fuels it. A single `fuels` arrow would drop the attention, and the attention is the point: the same object can feed or starve depending on how it's attended to. So each of the sutta's 24 statements is a `dho:Nutriment` node with object, attention, effect and citation (an n-ary relation, in W3C terms).

## D3. A hindrance is whatever is in the list of five hindrances

The data never types anything as `dho:Hindrance`. The schema defines the class as "member of the five hindrances", and the OWL reasoner classifies. It's the same for awakening factors and first-jhāna factors. This keeps one source of truth (the list, which the text states) and lets SHACL check the list against the count the text gives (S1).

## D4. One concept can sit in several lists

Rapture (pīti) is an awakening factor (SN 46.51) and a first-jhāna factor (MN 43). It's modelled as one concept with two memberships, so the reasoner classifies it as both. The alternative, two "rapture" nodes, would hide that it's the same quality in two contexts.

Immersion (samādhi, an awakening factor) and unification of mind (cittekaggatā, a jhāna factor) are kept as separate concepts, joined by a **cited definition**: MN 44:12.2, "Unification of the mind is immersion" (*cittassa ekaggatā ayaṁ samādhi*).

*Correction (2026-11-14).* v0.1 said equating the two was our interpretation and joined them only by an editor's link. That was wrong: a sutta states it. It was caught while checking eval answers against the text. We still don't merge them into one concept, because one discourse's definition is evidence, not licence to treat the words as interchangeable everywhere (merging would also make immersion a jhāna factor in every context). The definition is a `dho:Definition` node citing the passage, checked by S11.

## D5. Three source layers, never mixed

| Layer | Meaning | Example |
|---|---|---|
| Sutta | Early discourses, held verbatim | SN 46.51, SN 46.53, MN 43 |
| Commentary | Later treatises | Visuddhimagga IV.86 |
| Editor | This project's own judgment | "restless mind ↔ restlessness and remorse" |

Answers always show the layer. SHACL stops a commentary pairing being filed as sutta (S7).

## D6. Mind states are not hindrances

SN 46.53 speaks of a *restless mind* (uddhataṁ cittaṁ) and a *sluggish mind* (līnaṁ cittaṁ). These are close to, but not the same as, the hindrances *restlessness and remorse* and *dullness and drowsiness*: the sutta uses different words, and is about the timing of practice, not the hindrances. So they're separate concepts linked only by an editor's link. A search for "restless" returns both, each with its own sources.

## D7. Rule R1 derives only what the text supports

`dho:counters` (awakening factor → hindrance) is never written by hand (S9). Rule R1 derives it when one object, attended to rationally, both fuels a factor and starves a hindrance. From SN 46.51 that gives exactly two pairs:

- energy → dullness and drowsiness (via "the elements of initiative, persistence, and exertion")
- investigation of principles → doubt (via "skillful and unskillful qualities…")

It does **not** give tranquility → restlessness, which many teachers would expect. That pairing isn't derivable from SN 46.51. SN 46.53 supports something related but different: *when the mind is restless*, it's the right time to develop tranquility. That's kept as timing advice, not merged into `counters`.

## D8. "Dhamma" is one word with four senses

Following OntoLex-Lemon (the W3C lexicon model), the word *dhamma* is one lexical entry with four senses: the teaching, any phenomenon, an object of mind, and a mental quality. Each sense is a separate concept backed by a passage where the meaning is clear.

Passages are tagged with the sense they use only when it's clear. MN 10's *dhammesu dhammānupassī* is contested among translators, so it's recorded as contested, with Sujato's rendering, and left unassigned.

## D9. Labels

- **English preferred label:** Sujato's rendering, because that's the translation we cite. Other common renderings ("sloth and torpor", "concentration") are alternative labels.
- **Chinese labels:** the standard Chinese Buddhist terms (五蓋, 七覺支 and so on), supplied by the editor and not cited to a text. Mind states have no Chinese label yet, rather than an invented one.
- **Hidden labels** ("monkey mind", "sleepy"): search-only everyday words, chosen by the editor. They help resolve plain-language questions and are never shown as doctrine.

## D10. Compound hindrances are kept whole (for now)

*thinamiddha* (dullness and drowsiness) and *uddhaccakukkucca* (restlessness and remorse) are each one hindrance in the list of five, so each is one concept. Splitting them into components is deferred.

## D11. Coverage is logged, and so is who did the modelling

Every text the ontology draws on has a coverage record in `data/coverage.ttl`: fully encoded, partly encoded, cited only (quoted as evidence, teaching not modelled), or referenced only (not held). A partial record must say what it leaves out. Each record also says who modelled it and whether anyone has reviewed it. SHACL fails the build without one (S10).

`scripts/coverage.py` turns the records into `COVERAGE.md` and compares them with SuttaCentral's full list of Pali suttas, so the project's reach is stated as a number, not implied by a nice graph.

The reason: the project owner is a practitioner, not a teacher, and the modelling is drafted with an AI assistant. The quotes are the texts' own words and can be checked by anyone; the structure is our interpretation. So the honest position is to say exactly which texts the structure rests on, how much of each, and that it is unreviewed until someone qualified reviews it.

## D12. A claim stated in several suttas is one claim with several citations

SN 46.2 repeats SN 46.51's twelve "fuels" statements: identical English, and Pali that differs only in punctuation and one spelling variant. They are added as extra citations on the existing nutriment nodes, not as new nodes. Duplicating them would make the graph look bigger without saying anything new, and would make "how many suttas support this?" impossible to answer. Being stated in two discourses is information; it shows up as two citations.

Before merging, the wording of each pair is compared segment by segment, and any difference is recorded in the data file. Where the wording differs in substance, it's a different claim and gets its own node.

## Patterns not modelled yet

These kinds of teaching have come up and been left out (each logged in `data/coverage.ttl`) until a pattern is agreed:

- **A. Outcomes: "developing X leads to Y"**, and what a quality does (the hindrances weaken wisdom; the awakening factors lead to knowledge and freedom). The most common shape in SN 46. Draft: a node with the practice or quality, the outcome, and the citation, like a nutriment.
- **B. Conditions: "X is the forerunner / root / basis of Y"; "when X, then Y"** (good friendship, rational attention, ethics, attentive listening). Needed again for dependent origination. Draft: a node with condition, conditioned, the kind of relation in the text's own words, and the citation.
- **C. Similes** (SN 46.2 body and food; SN 46.33 gold; SN 46.53's four fire similes; SN 12.61's monkey). Probably a node linking the image, what it illustrates and the point it makes.

See `triage/sn46.md` for which suttas each pattern unlocks.
