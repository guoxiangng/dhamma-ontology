"""Build the single-file downloads in dist/.

    python scripts/release.py

  dist/dhamma-ontology.ttl           schema + data as written (what to load into Protégé or an RDF store)
  dist/dhamma-ontology-inferred.ttl  the same after OWL RL reasoning and rule R1 (types and `counters` filled in)
  dist/graph.json                    the simplified graph the viewer uses (nodes, typed links, passages)
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dho  # noqa: E402
from dho import ROOT  # noqa: E402
from export_graph import export  # noqa: E402

HEADER = (
    "# dhamma-ontology: https://github.com/guoxiangng/dhamma-ontology\n"
    "# {what}\n"
    "# Sutta text from SuttaCentral (CC0): English by Bhikkhu Sujato, Pali from the Mahāsaṅgīti edition.\n"
    "# Personal learning project; modelling unreviewed. See COVERAGE.md and DECISIONS.md.\n\n"
)


def main() -> int:
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    g = dho.load()
    (out / "dhamma-ontology.ttl").write_text(
        HEADER.format(what="Asserted: schema and data as written.") + g.serialize(format="turtle"), encoding="utf-8")
    g, asserted, derived, inferred = dho.build()
    (out / "dhamma-ontology-inferred.ttl").write_text(
        HEADER.format(what=f"Inferred: after OWL RL reasoning (+{inferred} triples) and rule R1 (+{sum(derived.values())}).")
        + g.serialize(format="turtle"), encoding="utf-8")
    (out / "graph.json").write_text(json.dumps(export(), ensure_ascii=False, indent=1), encoding="utf-8")
    for f in sorted(out.iterdir()):
        print(f"{f.relative_to(ROOT)}  {f.stat().st_size // 1024} KB")
    shutil.rmtree(ROOT / "scripts" / "__pycache__", ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
