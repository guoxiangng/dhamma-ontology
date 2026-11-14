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

## D13. Outcomes and conditions: controlled relation, verbatim wording

Most of SN 46 says what the awakening factors lead to, or what conditions them. Two patterns, approved by the project owner on 2026-11-14:

- **Outcome** (pattern A): *of* (a quality, list or practice), *effect*, *to*, *wording*, citations. Effects are a small controlled set: leads to, does not lead to, strengthens, weakens, and leads to giving up. The last was added with SN 46.29/41/130, only for the text's *pahāna* ("giving up"). Ending (*khaya*, SN 46.26) and cessation (*nirodha*, SN 46.27) are different words, so they stay "leads to" with their own target concepts. Example: the seven awakening factors, developed, *lead to* extinguishment ("slants, slopes, and inclines to extinguishment", SN 46.7).
- **Condition** (pattern B): *condition*, *relation*, *conditioned*, optional *result*, *wording*, citations. Relations: is the basis of ("depending on and grounded on", "relies on"), is the forerunner of ("the forerunner and harbinger of"), is the root of ("rooted in and meet at"), gives rise to, supports the development of ("can expect to develop"), and when-then, whose result says what happens (arise; don't arise, or end; are absent; are fully developed).

Mapping the text's words onto a controlled relation is an editorial act. So every claim also keeps the text's own words in `dho:wording`, and **S14 fails the build if that wording isn't found verbatim in a passage the claim cites**. The controlled relation makes the graph queryable; the wording keeps it honest. SN 46.1 says "grounded on ethics" and SN 46.12 says "forerunner"; eval Q38 checks that a system keeps that difference.

Choices made along the way:

- **The stock formula** that ten suttas repeat for each factor ("relies on seclusion, fading away, and cessation, and ripens as letting go") is one outcome and three conditions, each cited by all ten suttas (D12).
- **One Pali word, two English renderings** (*virāga*: "fading away" in the formula, "dispassion" in SN 46.20) is one concept, with the second rendering as an alternative label.
- **One English word, two Pali words** (*bodhi* in SN 46.5/46.21, *sambodhi* in SN 46.20, both "awakening" in Sujato) are two concepts joined by an editor's link. Merging them would be our interpretation, not the text's (the D4 lesson).
- **Phrases that don't map cleanly** onto a target are left out and logged, not forced. Example: SN 46.40's "making blind, sightless, ignorant".

*Correction (2026-11-14).* v0.1 labelled the kinds of attention "frequent rational application of mind" (*yonisomanasikārabahulīkāra*). The frequency belongs to how SN 46.51 phrases its statements, not to the kind of attention; SN 46.24 says only "when you apply the mind rationally". The concepts are now *yoniso manasikāra*, *ayoniso manasikāra* and *amanasikāra*. SN 46.51's statements are still displayed with "frequent", in Sujato's words.

## Patterns not modelled yet

These kinds of teaching have come up and been left out (each logged in `data/coverage.ttl`) until a pattern is agreed:

- **Similes** (SN 46.1 dragons, 46.2 body and food, 46.7 rafters, 46.11 earth, 46.12/13/48 dawn, 46.33 gold, 46.53 four fire similes; SN 12.61 monkey). Probably a node linking the image, what it illustrates and the point it makes.
- **What a quality is or isn't called:** the hindrances are "obstacles and corruptions of the heart"; the awakening factors are "not obstacles", "noble and emancipating" (SN 46.19, 46.34, 46.37).
- **One fetter is not one hindrance.** SN 46.130's higher fetter *uddhacca* (restlessness) is its own concept, joined by an editor's link to the hindrance *uddhaccakukkucca* (restlessness and remorse), not merged into it. Eval Q39 tests this.
- **Ranking:** "diligence is said to be the best of them" (SN 46.31, 46.32).
- **Release from the defilements** (āsava), which needs the three defilements as a list (SN 46.5).
- **Chains:** "when craving is given up, deeds are given up; when deeds are given up, suffering is given up" (SN 46.26). Dependent origination will need the same shape, so it should be designed once, for both.
- **Correspondences:** "whoever has missed out on the seven awakening factors has missed out on the noble path" (SN 46.18).

See `triage/sn46.md` for which suttas each pattern unlocks.
