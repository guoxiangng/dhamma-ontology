# Audit rubric: does each claim faithfully represent the text?

You are an independent auditor of a small ontology of early Buddhist teachings built from SuttaCentral (Bhikkhu Sujato's English, with the Pali). Someone else did the modelling. Your job is to find where they got it wrong. Be strict and skeptical, but fair: a claim that is right should be marked right.

Each packet is one text. It lists the claims that cite the text (with their fields and the segments they cite), what the modellers say they encoded and left out, and the text itself, segment by segment, in English and Pali.

## Rules

- **Judge only from the text in the packet.** Do not use commentaries, other suttas or your memory of what the tradition teaches. If a claim also cites other texts, judge only whether *this* text supports it.
- **Read the cited segments and their surroundings.** Context matters: who is speaking, and whether the line is a question, a view being rejected, or a simile.
- **The Pali is there to check the English.** Flag cases where the claim leans on an English rendering that the Pali doesn't support.
- **A summary may simplify. It may not change the meaning.** "Slants, slopes and inclines to extinguishment" mapped to "leads to extinguishment" is a fair simplification. Turning "can expect to develop" into "causes" would not be.

## Verdicts, one per claim

| Verdict | Use when |
|---|---|
| `SUPPORTED` | The text says this, in the cited segments, as teaching. The fields and the summary are a fair reading. |
| `STRETCH` | The text says something close, but the controlled relation, effect, subject, target or summary overstates, narrows or reframes it. Say what is off. |
| `WRONG_SPEAKER` | The words are in the text but said by an interlocutor, an opponent or a listener, not taught by the Buddha or a teaching disciple. |
| `MISREAD` | Wrong subject or target, wrong direction, wrong list members or count, or the cited segments don't contain what is claimed. |
| `NOT_SUPPORTED` | The text doesn't say this at all. |

Add `severity`: `minor` (a careful reader would shrug) or `major` (it would mislead someone using the ontology).

## Per text, also check

- **Omissions:** teaching statements in the text that are neither encoded nor mentioned in "left out". List them with segment ids. Ignore narrative framing, greetings and stock closing lines.
- **Left-out note:** is it accurate? Does it describe sections the text really has?
- **Coverage status:** "fully encoded" means every teaching claim is modelled. Is that true?

## Output

Write one JSON file (the path is given in your task) with this shape, and nothing else in it:

```json
{
  "batch": "<batch name>",
  "texts": [
    {
      "uid": "sn46.12",
      "claims": [
        {"id": "c-02", "verdict": "SUPPORTED", "severity": null, "reason": "1.2 says exactly this."},
        {"id": "c-17", "verdict": "STRETCH", "severity": "minor", "reason": "..."}
      ],
      "omissions": [{"segments": ["sn46.12:2.1"], "what": "..."}],
      "left_out_accurate": true,
      "coverage_status_accurate": true,
      "notes": "anything else a reviewer should know"
    }
  ]
}
```

Keep reasons to one or two sentences, and cite segment ids. In your final message, give totals by verdict and the three most serious problems you found.
