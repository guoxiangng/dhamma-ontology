"""Write COVERAGE.md: which texts this ontology draws on, how much of each, and how
that compares with the whole Pali Sutta Piṭaka.

    python scripts/coverage.py                  # regenerate COVERAGE.md
    python scripts/coverage.py --refresh-canon  # re-download the canon list from SuttaCentral first

Inputs:
  data/coverage.ttl                       hand-written record per text (status, what's in, what's out, review)
  the reasoned graph                      which passages each claim cites
  sources/suttacentral/*.json             cached text, to count each text's segments
  sources/suttacentral/canon-index.tsv    every sutta file in SuttaCentral's bilara-data
"""

from __future__ import annotations

import json
import os
import re
import ssl
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from rdflib import RDF
from rdflib.namespace import SKOS

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dho  # noqa: E402
from sc import stem_for  # noqa: E402
from dho import DHO, ROOT, label  # noqa: E402

SOURCES = ROOT / "sources" / "suttacentral"
CANON = SOURCES / "canon-index.tsv"
TREE_API = "https://api.github.com/repos/suttacentral/bilara-data/git/trees/"

COLLECTIONS = [  # (key, label) in display order; KN collections are summed into one row
    ("dn", "Long Discourses (DN)"),
    ("mn", "Middle Discourses (MN)"),
    ("sn", "Linked Discourses (SN)"),
    ("an", "Numbered Discourses (AN)"),
    ("kn", "Minor Collection (KN)"),
]
STATUS_ORDER = [DHO.FullyEncoded, DHO.PartlyEncoded, DHO.CitedOnly, DHO.ReferencedOnly]


# --------------------------------------------------------------------------- canon list

def _get(url: str) -> dict:
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    ctx = ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "dhamma-ontology-coverage"})
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.load(r)


def refresh_canon() -> None:
    sha = "published"
    for part in ("root", "pli", "ms", "sutta"):
        sha = next(t["sha"] for t in _get(TREE_API + sha)["tree"] if t["path"] == part)
    tree = _get(TREE_API + sha + "?recursive=1")
    if tree.get("truncated"):
        raise SystemExit("GitHub returned a truncated tree; canon list not updated.")
    rows = sorted(
        (p[0], p[1] if p[0] == "kn" else p[0], p[-1].split("_")[0], "/".join(p[:-1]))
        for p in (t["path"].split("/") for t in tree["tree"] if t["path"].endswith(".json"))
    )
    with CANON.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# Pali sutta files in SuttaCentral bilara-data (branch: published), root/pli/ms/sutta. "
                "Regenerate: python scripts/coverage.py --refresh-canon\n# nikaya\tcollection\tuid\tdir\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print(f"canon list refreshed: {len(rows)} files")


def expand(uid: str) -> list[str]:
    """'an2.21-31' -> ['an2.21', ..., 'an2.31']; SuttaCentral groups short or abbreviated suttas into ranges."""
    m = re.fullmatch(r"(.*?)(\d+)-(\d+)", uid)
    if not m:
        return [uid]
    prefix, a, b = m.group(1), int(m.group(2)), int(m.group(3))
    return [f"{prefix}{i}" for i in range(a, b + 1)]


def canon() -> dict[str, list[str]]:
    by_nikaya: dict[str, list[str]] = defaultdict(list)
    for line in CANON.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        nikaya, _collection, uid, _dir = line.split("\t")
        by_nikaya[nikaya] += expand(uid)
    return by_nikaya


# --------------------------------------------------------------------------- per text

def segment_count(uid: str) -> int | None:
    try:
        path = SOURCES / f"{stem_for(uid)}_pli.json"
    except SystemExit:  # not a sutta we can hold (e.g. a commentary cited by reference)
        return None
    if not path.exists():
        return None
    keys = json.loads(path.read_text(encoding="utf-8")).keys()
    return sum(1 for k in keys if k.split(":")[0] == uid and not k.split(":")[1].startswith("0."))


def text_rows(g) -> list[dict]:
    rows = []
    for t in g.subjects(RDF.type, DHO.Text):
        uid = str(t).split("#t-", 1)[1]
        passages = set(g.subjects(DHO.inText, t))
        claims = {c for p in passages for c in g.subjects(DHO.citedBy, p)} | set(g.subjects(DHO.referencesText, t))
        rows.append({
            "uid": uid,
            "title": label(g, t) if label(g, t) != f"dho:t-{uid}" else str(g.value(t, SKOS.prefLabel)),
            "layer": label(g, g.value(t, DHO.layer)),
            "status": g.value(t, DHO.coverage),
            "review": label(g, g.value(t, DHO.review)),
            "cited": len(passages),
            "total": segment_count(uid),
            "claims": len(claims),
            "encodes": str(g.value(t, DHO.encodes) or ""),
            "left_out": str(g.value(t, DHO.leftOut) or ""),
            "by": str(g.value(t, DHO.modelledBy) or ""),
            "on": str(g.value(t, DHO.modelledOn) or ""),
            "url": str(g.value(t, DHO.url) or ""),
        })
    order = {s: i for i, s in enumerate(STATUS_ORDER)}
    return sorted(rows, key=lambda r: (order.get(r["status"], 9), r["uid"]))


def nikaya_of(uid: str) -> str:
    for key in ("dn", "mn", "sn", "an"):
        if re.match(rf"{key}\d", uid):
            return key
    return "kn"


# --------------------------------------------------------------------------- report

def report() -> str:
    g, *_ = dho.build()
    rows = text_rows(g)
    can = canon()
    sutta_rows = [r for r in rows if r["status"] != DHO.ReferencedOnly]
    touched: dict[str, Counter] = defaultdict(Counter)
    for r in sutta_rows:
        touched[nikaya_of(r["uid"])][r["status"]] += 1

    out = [
        "# Coverage",
        "",
        f"_Generated by `scripts/coverage.py` on {date.today().isoformat()}. Do not edit by hand: "
        "change `data/coverage.ttl` and regenerate._",
        "",
        "This is how much of the canon the ontology actually draws on. It is small on purpose: a text "
        "only counts once its claims are modelled and cited, and partial work says what it leaves out.",
        "",
        "**Who did the modelling.** The project owner is a practitioner, not a teacher, and the modelling "
        "was drafted with an AI assistant (Claude). The claims are the texts' own words, quoted from "
        "SuttaCentral; the *structure* (what counts as a claim, how it is split, which editor links exist) "
        "is our interpretation. Until a text is marked reviewed, treat its modelling as a draft.",
        "",
        "## Against the Pali Sutta Piṭaka",
        "",
        "| Collection | Suttas in SuttaCentral | Fully encoded | Partly encoded | Cited only | Share touched |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    total_canon = total_touched = 0
    for key, name in COLLECTIONS:
        n = len(can.get(key, []))
        c = touched.get(key, Counter())
        t = sum(c.values())
        total_canon += n
        total_touched += t
        out.append(f"| {name} | {n:,} | {c[DHO.FullyEncoded]} | {c[DHO.PartlyEncoded]} | {c[DHO.CitedOnly]} | "
                   f"{t / n:.2%} |" if n else f"| {name} | 0 | | | | |")
    fully = sum(c[DHO.FullyEncoded] for c in touched.values())
    out += [
        f"| **Total** | **{total_canon:,}** | **{fully}** | | | **{total_touched / total_canon:.2%}** |",
        "",
        "Counts follow SuttaCentral's numbering, with grouped ranges (e.g. `sn12.93-213`) counted as the "
        "suttas they number. Many of those are abbreviated repetitions, so this overstates the amount of "
        "distinct text. KN mixes early and late material (Dhammapada and Sutta Nipāta beside Jātaka and "
        "Apadāna) and Dhammapada is counted by verse.",
        "",
        "## Texts drawn on",
        "",
        "| Text | Layer | Coverage | Segments cited / in text | Claims citing it | Review |",
        "|---|---|---|---:|---:|---|",
    ]
    for r in rows:
        seg = f"{r['cited']} / {r['total']}" if r["total"] else (f"{r['cited']} / ?" if r["cited"] else "not held")
        title = f"[{r['title']}]({r['url']})" if r["url"] else r["title"]
        out.append(f"| {title} | {r['layer']} | {label(g, r['status'])} | {seg} | {r['claims']} | {r['review']} |")
    out += ["", "Segments cited are the passages a claim points to. A fully encoded text can still cite "
            "fewer than all its segments, because headings, questions and restatements carry no new claim.", ""]

    for r in rows:
        out += [f"### {r['title']}", "",
                f"- **Coverage:** {label(g, r['status'])} · **Review:** {r['review']} · "
                f"**Modelled:** {r['on']} by {r['by']}",
                f"- **Encodes:** {r['encodes']}"]
        if r["left_out"]:
            out.append(f"- **Left out:** {r['left_out']}")
        out.append("")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--refresh-canon" in argv:
        refresh_canon()
    text = report()
    (ROOT / "COVERAGE.md").write_text(text + "\n", encoding="utf-8")
    print("wrote COVERAGE.md")
    print("\n".join(l for l in text.splitlines() if l.startswith("| ")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
