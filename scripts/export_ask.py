"""Build the ask page, viz/ask.html: search in English, Pali or Chinese and get cited answers.

    python scripts/export_ask.py

The page runs entirely in the browser over the same data as the graph view: no server,
no model, nothing generated. It answers only from the ontology and says so when a word
isn't covered.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dho import ROOT  # noqa: E402
from export_graph import export  # noqa: E402


def main() -> int:
    data = export()
    template = (ROOT / "viz" / "ask-template.html").read_text(encoding="utf-8")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    (ROOT / "viz" / "ask.html").write_text(template.replace("/*__DATA__*/null", payload), encoding="utf-8")
    print(f"wrote viz/ask.html: {len(data['nodes'])} concepts searchable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
