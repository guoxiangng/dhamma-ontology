# Contributing

Thank you for looking. This project is only as good as its checking, and the most valuable contribution is telling us where it's wrong.

## Report an error

If a claim misrepresents a text, a link is in the wrong layer, a translation choice is misleading, or a coverage note is wrong, please [open an issue](../../issues/new?template=correction.md) with:

- the concept, claim or file;
- the segment (e.g. `sn46.51:16.2`) and what it actually says;
- what you think it should be, and why.

Readers who know the texts well (monastics, scholars, long-term students) are especially welcome to review [DECISIONS.md](DECISIONS.md) and the gold answers in [eval/GOLD-REVIEW.md](eval/GOLD-REVIEW.md). A text's coverage record can be marked reviewed once a qualified reader has checked it.

## Add a text

Read [CLAUDE.md](CLAUDE.md) first. Its rules apply to people as much as to Claude. In short:

1. **Fetch and read** the whole text: `python scripts/sc.py fetch <uid>`, then `python scripts/sc.py show <uid> --cited`.
2. **Write a claim table** and match each claim to an existing pattern. Same claim as an existing node → add a citation, don't duplicate (D12). No pattern fits → leave it out and propose one.
3. **Write the data** in `data/<uid>-<topic>.ttl`, then run `python scripts/build_passages.py`.
4. **Write a coverage record** in `data/coverage.ttl`, including what you left out.
5. **Add 1–3 eval questions**, at least one of them a trap, with `status = "draft"`.
6. **Run the checks:**
   ```bash
   python scripts/dho.py check
   python -m pytest -q tests
   python eval/check_gold.py
   python scripts/coverage.py
   ```

With [Claude Code](https://claude.com/claude-code), `/add-text <uid>` walks through all of this.

## Pull requests

- Keep one text, or one modelling change, per PR.
- Explain any new pattern or changed decision in DECISIONS.md.
- CI runs the checks and tests; they must pass.
