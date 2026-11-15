# Audit

An independent check of every claim against the texts it cites. The first run was on 2026-11-15, over 63 texts and 270 claim–text pairs.

## How it was done

1. **One packet per text** ([`audit/build_packets.py`](audit/build_packets.py)). Each packet holds the full text, segment by segment, in English (Sujato) and Pali. It also has every claim that cites the text, with all its fields and segments, plus what the coverage record says was encoded and left out.
2. **Six auditor agents** each took a batch of packets and graded every claim against [`audit/RUBRIC.md`](audit/RUBRIC.md):
   - `SUPPORTED`;
   - `STRETCH`: close, but the relation or summary overstates, narrows or reframes the text;
   - `WRONG_SPEAKER`;
   - `MISREAD`: wrong subject, target, direction, members or segments;
   - `NOT_SUPPORTED`.

   They also checked omissions, the left-out notes and the coverage statuses. The auditors were told to judge only from the packet. They saw neither DECISIONS.md nor the modelling reasoning.
3. **A seventh, blind run.** A general model judged 93 of the same claims (batches 3 and 4) from memory, without the texts. Comparing it with the text-based audit shows how much an LLM's memory catches on its own.
4. **Spot checks.** The modeller (Claude) re-checked every major finding, and several striking minor ones, against the text before acting on them.

All packets, the blind packets and the raw results are in [`audit/2026-11-15/`](audit/2026-11-15/). To regenerate the totals: `python audit/aggregate.py audit/2026-11-15`.

**Caveat:** the auditors are the same model family as the modeller and may share its blind spots. This audit does not replace review by a qualified reader. It narrows what that reader needs to look at.

## Results

| | Claim–text pairs |
|---|---:|
| Judged | 270 |
| Supported | 222 (82%) |
| Stretch, minor | 46 (17%) |
| Misread, major | 2 (one bug, in two texts) |
| Wrong speaker | 0 |
| Not supported at all | 0 |

| Coverage records | |
|---|---|
| Texts marked "fully encoded" that were not | 5 of 16 (SN 46.24, 46.35, 46.49, 46.50, 46.130) |
| Inaccurate left-out or encoded notes | 4 (SN 46.49, 46.50, 46.53, 46.56), plus small slips in MN 43, MN 44, SN 46.3, SN 46.76 |
| Teaching statements missed | 15 omissions in 10 texts |

### Blind run vs the text-based audit (same 93 claims)

| | Claims |
|---|---:|
| Both found no problem | 73 |
| Both found the problem | 6 |
| The text-based audit found a problem; the blind run said fine | 14 (4 with "high" confidence) |
| The blind run raised a problem the text-based audit did not | 0 |

From memory, the model caught 6 of the 20 problems in its sample. It raised no false alarms, and it rightly suspected that SN 46.49, 46.50 and 46.130 might be incomplete, but it could not confirm this without the text. On the abbreviated perception suttas, it argued that the conventional expansion of "…pe…" is legitimate. That is a real disagreement about method (D14), not an error (see below).

## What the audit found

**The root cause: the English was read, not the Pali.** Every serious finding traces back to this.

- **Direction reversed (both major findings).** SN 46.57 and 46.76 say *aṭṭhikasaññāsahagataṁ satisambojjhaṅgaṁ bhāveti*: the mendicant develops the awakening factor, accompanied by the perception. Sujato's English turns this round ("develops the perception of a skeleton together with the awakening factors"), and the ontology had followed the English.
- **Teaching given only in the Pali.** In SN 46.49 and 46.50 the English stops at "…", but the Pali continues in full (1.2–1.6). In SN 46.57, sections 2–6 are given in the Pali and abbreviated in the English. In SN 46.130:1.8, the Pali has the seclusion formula and the English of that segment does not.
- **Claims resting on the translator's expansion.** In SN 46.58–75, the Pali gives only the practice and "…pe…". "Very fruitful and beneficial" exists only in the English filling-in. The notes said so, but the claims still presented it as what the text says (18 claims).
- **List members only in the expansion.** In SN 46.33:2.3, the Pali names only sensual desire and abbreviates the other four corruptions.

**Flattening what the text says.**

- **"Can expect one of" became "leads to".** SN 46.3's seven fruits are ranked alternatives, and SN 46.57/76 give "one of two results".
- **"Arise, and once arisen grow" became "arise".** This happened in SN 46.24 and 46.35. The coverage notes even claimed the growth was encoded.
- **Two different verbs got one result.** "Given up" (*pahīyati*) and "cease" (*nirujjhati*) were both "end".
- **The full condition was cut short.** SN 46.38's whole clause (attention, applying the mind, wholehearted concentration, listening) became "actively listens".

**Citations.** Several list claims cited segments that give only the count ("five hindrances") and not the members. The nutriment claims of SN 46.51 and 46.2 left out the segment that actually says "fuels" or "starves".

## What was changed

Each fix is logged in [DECISIONS.md](DECISIONS.md) (D19, with correction notes on D14 and D15) and in the data files' comments.

| Finding | Fix |
|---|---|
| Direction reversed (c-p57, c-p76) | Reversed: the perception accompanies the development of the awakening factors. Wording now quotes the Pali (*aṭṭhikasaññāsahagataṁ*). |
| Teaching only in the Pali (SN 46.49, 46.50, 46.57, 46.130) | Cited. S14 now accepts wording found in the Pali as well as the English. A new test fails if a fully encoded text has an uncited, untranslated Pali segment (questions, end markers and summary verses excepted). |
| Outcomes resting on an expanded abbreviation (18) | Marked `dho:support dho:ExpandedAbbreviation`, which the pages show as a tag. New check S16 fails if a claim rests only on abbreviated Pali without the mark. |
| "Can expect one of" (o-29, o-p57-a/b, o-p76-a/b) | New effect "can be expected to lead to (one of the alternatives)". The fruits' order and the "ending of the five lower fetters" condition are in notes. |
| "Arise and grow", "given up" vs "cease" | New results: arise and grow; arise and are fully developed; don't arise, or are given up. The old "end" label is now "cease". |
| SN 46.38's condition | Wording now gives the whole clause. |
| List and nutriment citations | Member-naming segments and "fuels / starves" segments are cited. SN 46.33's abbreviated list has a note. |
| Coverage notes | Corrected for SN 46.49, 46.50, 46.53, 46.56, 46.76, 46.130, MN 43, MN 44 and SN 46.3, each with a dated note. |

## Accepted, not changed

These were flagged as minor stretches and kept deliberately. Each is on the revisit list.

- **English labels follow Sujato (D9)** even where he interprets: "desire for rebirth in the realm of luminous form" (*rūparāga*); "sensual desire for what is internal" (*ajjhattaṁ kāmacchando*, which has no "things"); "not frequently applying the mind" (*amanasikārabahulīkāro*, closer to "frequent non-attention"); "progress" (*aparihāna*, "non-decline").
- **Mapping wordings onto a few controlled relations (revisit #4).** "Block wisdom" (*paññānirodhikā*, SN 46.40) and "weaken wisdom" (*dubbalīkaraṇa*, SN 46.37) are both "weakens". So are "should be developed for" (a purpose, SN 46.130) and "give up by developing these" (SN 46.41) under "leads to giving up". Each claim keeps the verbatim wording, and the difference is spelled out in a note.
- **The list called "the five hindrances"** is cited by MN 43 and SN 46.24, which name the same five without the word *nīvaraṇa*. The citation supports the members; the name comes from the other texts that cite the list.

## How it is used from now on

The `add-text` skill has an audit step. After a text is encoded, `python audit/build_packets.py audit/<date> <uid>` builds its packet, and an auditor agent grades it against the rubric. A major finding blocks the commit. The skill now also says to read the Pali first and check the English against it.
