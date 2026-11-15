# Modelling decisions

An ontology can't be neutral: every structural choice is a position. This file records each choice, why it was made, and what it costs, so a reader can disagree with a specific decision instead of with the whole thing.

This is a personal project with no institutional vetting. The ground rule follows from that.

**Who decided.** D1–D12 were proposed by Claude (the AI assistant) and accepted by the project owner in conversation; D13 was approved explicitly by the owner. From D14 on, the owner asked Claude to decide and log, and to revisit everything in a later pass, because the owner doesn't claim more expertise than the assistant. Each of those entries says so. **The [revisit list](#revisit-list) at the end collects every judgment call worth a second look.**

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

*Update 2026-11-14:* SN 46.52 splits them itself ("dullness is a hindrance; and drowsiness is also a hindrance"). The compounds stay one concept each, as members of the five, and each now divides into its two named qualities (D18).

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

## D14. Abbreviated suttas: record what is stated, don't expand

*Decided by Claude; the owner deferred. Revisit.*

Many suttas are abbreviated in the Pali itself (*peyyāla*, marked …pe…): SN 46.58–75 give only the practice, "*Puḷavakasaññā, bhikkhave, bhāvitā …pe…*", and leave the rest to be filled in from SN 46.57. The tradition expects the reader to expand them, and the translation fills in "very fruitful and beneficial".

The ontology records only what the translation's visible line states. Each such claim carries a note saying the Pali is abbreviated and the outcome is the translation's expansion. The rest of the expansion (developing the practice together with the awakening factors, the two results, great benefit and so on) is not added, and each coverage record says so. Expanding elisions is reconstruction, and reconstruction is where an editor's mistakes would hide.

*Correction 2026-11-15 (audit, D19):* the note was not enough. A claim resting only on the expansion still looked like a sutta claim. Such claims now carry `dho:support dho:ExpandedAbbreviation`, shown as a tag, and check S16 enforces it. The audit's blind run argued that the conventional expansion is legitimate. That's the tradition's view, which is why the claims are kept and marked rather than dropped.

## D15. Practices are their own concepts, even when they share a word

*Decided by Claude; the owner deferred. Revisit.*

The twenty meditation subjects of SN 46.57–76 (the perception of a skeleton, love, mindfulness of breathing, the perception of impermanence, …) are `dho:Practice` concepts. Each is "very fruitful and beneficial" when developed, an outcome (D13). SN 46.57 and 46.76, given in full, add that the practice is developed *together with* the awakening factors (*sahagata*, a new condition relation "accompanies the development of") and lists further results: one of two, enlightenment in this very life or non-return; great benefit, sanctuary from the yoke, inspiration and ease.

Where a practice shares a word with something already in the ontology, it stays a separate concept with an editor's link, not a merge:

- *upekkhā* in SN 46.65 sits in the run love, compassion, rejoicing, equanimity (SN 46.62–65), a different role from the awakening factor of equanimity;
- *mettā* in SN 46.62 vs SN 46.51's object "the heart's release by love" (*mettācetovimutti*);
- *asubhasaññā* in SN 46.67 vs SN 46.51's object "the feature of ugliness" (*asubhanimitta*).

*Correction 2026-11-15 (audit, D19):* the direction was reversed. The Pali, *aṭṭhikasaññāsahagataṁ satisambojjhaṅgaṁ bhāveti*, says the mendicant develops the awakening factor, accompanied by the perception. Sujato's English turns this round, and the claims had followed the English. Fixed: the perception accompanies the development of the awakening factors.

Chinese labels for the practices are left out for now: the standard term for *muditā* (喜) is already the label for rapture (*pīti*), and a wrong guess would mislead search.

## D16. Sequences are links, not a separate chain

*Decided by Claude; the owner deferred. Revisit.*

SN 46.3 describes the awakening factors arising in order: recollecting the teaching → mindfulness → investigation → energy → rapture → tranquility → immersion → equanimity. Each step is stated as its own sentence ("When they're energetic, rapture not of the flesh arises"), so each becomes its own condition (D13, when-then, "arise") with its own wording and citations. The sequence is what you get by following the links; no extra "chain" node is added. Where the text adds something to a step (bliss alongside tranquility), it goes in a note.

This does not settle SN 46.26's chain (craving given up → deeds given up → suffering given up), where the condition is the *giving up* of something, not a quality. That is still left out; dependent origination will need the same decision.

The same batch adds the relation "is a cause and reason for" (*hetu, paccaya*), SN 46.56.

## D17. Encode what is taught, not what interlocutors say

*Decided by Claude; the owner deferred. Revisit.*

Suttas mix teaching with framing: questions, other teachers' views, and listeners' responses. The ontology encodes what is taught, whether by the Buddha or by a disciple teaching (MN 43's Sāriputta, MN 44's Dhammadinnā). It leaves out a listener's approving restatement. In SN 46.56 the line "overcome by even a single hindrance you wouldn't truly know or see" is Prince Abhaya's response, not the Buddha's teaching, so it is not encoded, and the coverage record says so. Eval Q44 checks that a system attributes it correctly.

The ontology does not yet record who speaks each claim. That is on the revisit list.

## D18. Divisions: "becomes twofold" (SN 46.52)

*Decided by Claude; the owner deferred. Revisit.*

SN 46.52 says the five hindrances become ten and the seven awakening factors fourteen: each "becomes twofold". Each of the twelve statements is one `dho:Division` node: the quality it divides, exactly two parts, the basis of the division, the text's own wording and citations (SHACL S15). The bases, as the text gives them:

| Basis | Qualities |
|---|---|
| internal and external (*ajjhattaṁ / bahiddhā*) | sensual desire, ill will, doubt, mindfulness, investigation, equanimity |
| physical and mental (*kāyika / cetasika*) | energy, tranquility |
| with and without placing the mind and keeping it connected (*savitakka savicāra / avitakka avicāra*) | rapture, immersion |
| the two qualities a compound name joins | dullness / drowsiness, restlessness / remorse |

- **Parts of the first three kinds are aspects** (`dho:Aspect`), named with Sujato's words: "sensual desire for what is internal", "physical energy". They are not separate qualities, only ways the one quality occurs.
- **Parts of the compounds are qualities** (`dho:MentalQuality`): dullness (*thina*), drowsiness (*middha*), restlessness (*uddhacca*) and remorse (*kukkucca*). This takes up what D10 deferred.
- **Restlessness is one concept**, shared by SN 46.130's higher fetter and SN 46.52's half of the hindrance: same Pali word, same rendering (D13's rule). The editor's link from restlessness to the hindrance restlessness and remorse is removed, because the connection is now cited.
- **The parts are not classified as hindrances or awakening factors**, though the text says "is also a hindrance". Classes still come from list membership (D3). A query can find the hindrances' parts by following the divisions.
- **The ten and the fourteen are not modelled as lists.** The text counts them, but the twelve divisions already say everything the lists would, and two more lists would double the claim.
- **The wanderers' restatement** of the teaching (3.2, "corruptions of the heart that weaken wisdom") is left out (D17).

## D19. Read the Pali first; audit every text

*Decided by Claude after the 2026-11-15 audit (AUDIT.md); the owner asked for the audit. Revisit.*

An independent audit checked all 270 claim–text pairs against the texts. 82% were supported, 17% were minor stretches, and 2 were major misreads (one bug in two texts). No claim was invented or put in the wrong speaker's mouth. But 5 of the 16 texts marked "fully encoded" were not. Every serious finding had one cause: the modelling read Sujato's English and treated the Pali as a check, when the English sometimes abbreviates, leaves out or rearranges what the Pali says.

- **Read the Pali first.** Sujato's English is a translation: it can reverse grammar (SN 46.57's *sahagata*), leave out a formula (SN 46.130:1.8), or stop at "…" while the Pali carries on (SN 46.49, 46.50, 46.57). The add-text skill now reads each segment's Pali before its English.
- **Wording may quote the Pali** when the English doesn't carry the claim. S14 accepts either.
- **A fully encoded text cannot hide untranslated Pali.** A test fails if any untranslated Pali segment in such a text is uncited (questions, end markers and summary verses excepted).
- **Claims resting only on an expanded abbreviation are marked** `dho:support dho:ExpandedAbbreviation` (S16).
- **Results and effects keep the text's distinctions:**
  - "can be expected to lead to (one of the alternatives)" for *pāṭikaṅkha*;
  - "arise, and once arisen increase and grow";
  - "arise, and once arisen are fully developed";
  - "don't arise, or are given up" (*pahīyati*), kept apart from "cease" (*nirujjhati*).
- **Every new text gets an audit** before it is committed (`audit/`, add-text step 7). A major finding blocks the commit.

## Patterns not modelled yet

These kinds of teaching have come up and been left out (each logged in `data/coverage.ttl`) until a pattern is agreed:

- **Similes** (SN 46.1 dragons, 46.2 body and food, 46.7 rafters, 46.11 earth, 46.12/13/48 dawn, 46.33 gold, 46.53 four fire similes; SN 12.61 monkey). Probably a node linking the image, what it illustrates and the point it makes.
- **What a quality is or isn't called:** the hindrances are "obstacles and corruptions of the heart"; the awakening factors are "not obstacles", "noble and emancipating" (SN 46.19, 46.34, 46.37).
- **One fetter is not one hindrance.** SN 46.130's higher fetter *uddhacca* (restlessness) is its own concept, not merged into the hindrance *uddhaccakukkucca* (restlessness and remorse). Eval Q39 tests this. *Since D18:* SN 46.52 names restlessness as one of the two qualities in that hindrance, so the two are now joined by a cited division instead of an editor's link.
- **Ranking:** "diligence is said to be the best of them" (SN 46.31, 46.32).
- **Release from the defilements** (āsava), which needs the three defilements as a list (SN 46.5).
- **Chains:** "when craving is given up, deeds are given up; when deeds are given up, suffering is given up" (SN 46.26). Dependent origination will need the same shape, so it should be designed once, for both.
- **Correspondences:** "whoever has missed out on the seven awakening factors has missed out on the noble path" (SN 46.18).

See `triage/sn46.md` for which suttas each pattern unlocks.

## Revisit list

Judgment calls a second pass should look at first. Each was made deliberately and logged, but each is where a qualified reader would most likely disagree.

| # | Call | Where | Why it might be wrong |
|---|---|---|---|
| 1 | Immersion (*samādhi*) and unification (*cittekaggatā*) are separate concepts joined by MN 44's definition, not merged | D4 | MN 44 states they are the same; some would merge |
| 2 | *bodhi* and *sambodhi* are separate concepts, editor-linked | D13 | Sujato renders both "awakening"; the difference may not matter |
| 3 | *virāga* is one concept for "fading away" and "dispassion" | D13 | The two contexts may intend different senses |
| 4 | Mapping wordings onto controlled effects and relations ("bring … to" → leads to; "block wisdom" → weakens) | D13 | Each mapping is editorial; the verbatim wording is kept, but queries use the mapping |
| 5 | The fetter *uddhacca* is separate from the hindrance *uddhaccakukkucca*, and is the same concept as the *uddhacca* half of that hindrance | D13, D18 | Same word in two lists may not be the same quality; or the commentaries may treat fetter and hindrance as one |
| 6 | Abbreviated suttas are not expanded | D14 | The tradition expects expansion; we may under-represent SN 46.58–75 |
| 7 | *upekkhā*, *mettā* and *asubha* as practices are separate from the same words elsewhere | D15 | They may be the same qualities in different settings |
| 8 | Mind states (*līnaṁ cittaṁ*, *uddhataṁ cittaṁ*) are separate from the hindrances | D6 | The link may be closer than an editor's link suggests |
| 9 | Search words (hidden labels) such as "monkey mind", "sleepy" | D9 | Everyday words are guesses at what people mean |
| 10 | The Visuddhimagga pairings of jhāna factors and hindrances, cited from memory | D5, `data/commentary-vism.ttl` | Not checked against an edition |
| 12 | Sequences modelled as pairwise links (SN 46.3) | D16 | A chain may deserve to be one object, e.g. for the order of the seven fruits |
| 13 | Interlocutors' lines left out; speakers not recorded (MN 43, MN 44 claims are disciples' teaching) | D17 | Some responses add content; a speaker field may be needed |
| 14 | SN 46.52's parts are aspects (internal/external etc.) or qualities (the compounds' halves), and are not classified as hindrances or factors | D18 | The text calls each part "a hindrance"; a reader may want them classified |
| 15 | Claims resting on an expanded abbreviation are kept, marked (D19) | D14, D19 | Either too generous (drop them) or too cautious (the tradition expands them) |
| 16 | Sujato's labels kept where the Pali is narrower (*rūparāga*, *ajjhattaṁ kāmacchando*, *amanasikārabahulīkāro*) | D9, AUDIT.md | A Pali-literal label would be more faithful, less readable |
| 11 | What each coverage record says was left out | `data/coverage.ttl` | Written by Claude after reading each text; a reader may see claims we missed |

A revisit pass can work text by text: every claim cites its segments, every text has a coverage record with the date it was modelled, and the review view (`viz/review.html`) shows each text beside the claims resting on it.

