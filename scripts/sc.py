"""SuttaCentral helpers shared by the scripts: find a text's file, fetch it, title it.

    python scripts/sc.py fetch sn46.2          # cache English (Sujato) + Pali into sources/suttacentral/
    python scripts/sc.py show sn46.2           # print every segment: id | English | Pali  (for reading)
    python scripts/sc.py show sn46.2 --cited   # same, marking segments the ontology already cites

Behind a TLS-inspecting proxy, set SSL_CERT_FILE to your CA bundle first.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources" / "suttacentral"
CANON = SOURCES / "canon-index.tsv"
RAW = "https://raw.githubusercontent.com/suttacentral/bilara-data/published"

# Hand-set titles where the file header doesn't give a good one (Dhammapada files hold a range of verses).
TITLE_OVERRIDES = {"dhp279": "Dhammapada 279"}


def _canon_rows() -> list[tuple[str, str, str, str]]:
    rows = []
    for line in CANON.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            rows.append(tuple(line.split("\t")))
    return rows


def _in_range(uid: str, file_uid: str) -> bool:
    m = re.fullmatch(r"(.*?)(\d+)-(\d+)", file_uid)
    if not m:
        return uid == file_uid
    u = re.fullmatch(re.escape(m.group(1)) + r"(\d+)", uid)
    return bool(u) and int(m.group(2)) <= int(u.group(1)) <= int(m.group(3))


def locate(uid: str) -> tuple[str, str]:
    """Return (file stem, bilara directory) for a text uid, e.g. 'dhp279' -> ('dhp273-289', 'kn/dhp')."""
    for _nikaya, _col, file_uid, directory in _canon_rows():
        if _in_range(uid, file_uid):
            return file_uid, directory
    raise SystemExit(f"'{uid}' is not in sources/suttacentral/canon-index.tsv (try: python scripts/coverage.py --refresh-canon)")


def stem_for(uid: str) -> str:
    """The cached file stem holding this text (a range file for chunked texts)."""
    if (SOURCES / f"{uid}_pli.json").exists():
        return uid
    return locate(uid)[0]


def load(uid: str) -> tuple[dict, dict]:
    stem = stem_for(uid)
    en = json.loads((SOURCES / f"{stem}_en.json").read_text(encoding="utf-8"))
    pi = json.loads((SOURCES / f"{stem}_pli.json").read_text(encoding="utf-8"))
    return en, pi


def title(uid: str, en: dict, pi: dict) -> str:
    """'SN 46.2 Kāyasutta — The Body', from the text's own header segments (x:0.n)."""
    if uid in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[uid]
    head = sorted(k for k in pi if k.split(":")[0] == uid and k.split(":")[1].startswith("0."))
    pli_title = pi[head[-1]].strip() if head else ""
    en_title = en.get(head[-1], "").strip() if head else ""
    m = re.fullmatch(r"([a-z-]+)(.+)", uid)
    code = f"{m.group(1).upper()} {m.group(2)}" if m else uid
    return " ".join(x for x in (code, pli_title, "—" if en_title else "", en_title) if x)


def _get(url: str) -> bytes:
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    ctx = ssl.create_default_context(cafile=cafile) if cafile else ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "dhamma-ontology"})
    with urllib.request.urlopen(req, context=ctx) as r:
        return r.read()


def fetch(uid: str) -> Path:
    stem, directory = locate(uid)
    urls = {
        "pli": f"{RAW}/root/pli/ms/sutta/{directory}/{stem}_root-pli-ms.json",
        "en": f"{RAW}/translation/en/sujato/sutta/{directory}/{stem}_translation-en-sujato.json",
    }
    for lang, url in urls.items():
        out = SOURCES / f"{stem}_{lang}.json"
        if out.exists():
            print(f"already cached: {out.name}")
            continue
        data = _get(url)
        json.loads(data)  # fail loudly on anything that isn't JSON
        out.write_bytes(data)
        print(f"cached {out.name}")
    en, pi = load(uid)
    print(f"{title(uid, en, pi)}: {sum(1 for k in pi if k.split(':')[0] == uid)} segments")
    return SOURCES / f"{stem}_pli.json"


def cited_segments(uid: str) -> set[str]:
    refs = re.compile(rf"dho:p-{re.escape(uid)}-(\d+(?:\.\d+)*)")
    found = set()
    for ttl in (ROOT / "data").glob("*.ttl"):
        if ttl.name != "passages.ttl":
            found |= {f"{uid}:{s}" for s in refs.findall(ttl.read_text(encoding="utf-8"))}
    return found


def show(uid: str, mark_cited: bool) -> None:
    en, pi = load(uid)
    cited = cited_segments(uid) if mark_cited else set()
    print(f"# {title(uid, en, pi)}")
    for k in pi:
        if k.split(":")[0] != uid:
            continue
        mark = "* " if k in cited else "  "
        print(f"{mark}{k} | {en.get(k, '').strip()} | {pi[k].strip()}")
    if mark_cited:
        print(f"\n* = already cited by the ontology ({len(cited)} segments)")


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(argv) < 3 or argv[1] not in {"fetch", "show"}:
        print(__doc__)
        return 2
    if argv[1] == "fetch":
        fetch(argv[2])
    else:
        show(argv[2], "--cited" in argv)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
