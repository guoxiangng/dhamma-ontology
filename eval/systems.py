"""The three systems the eval compares, and the tools B and C call. No model calls here.

A  plain LLM: the question only
B  LLM + text: search and read the cached SuttaCentral texts (the same texts the ontology is
   built from, including the parts the ontology left out)
C  LLM + ontology: look up the reasoned graph (concept cards with cited links, word senses,
   cited passages, coverage records)

All three get the same instructions; B and C add one sentence about their tools. The only
difference between B and C is what their tools can reach.
"""

from __future__ import annotations

import json
import math
import re
import sys
import threading
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import dho  # noqa: E402
from rdflib.namespace import RDF, SKOS  # noqa: E402

SOURCES = ROOT / "sources" / "suttacentral"
MAX_TOOL_CHARS = 40_000

INSTRUCTIONS = """You answer questions about the early Buddhist suttas (the Pali Canon).

- Answer from what the suttas say. Cite the sutta for each point (for example "SN 46.51"), and the segment when you can (for example "SN 46.51:1.4").
- If a point comes from a commentary (such as the Visuddhimagga) or from later or modern teachers rather than the suttas, say so.
- If you don't know, or can't find support for something, say so plainly instead of guessing.
- Keep the answer under 250 words."""

TOOL_NOTE = {
    "A": "",
    "B": ("You have tools to search and read a collection of suttas (Pali, with Bhikkhu Sujato's English "
          "translation). It holds only some suttas, not the whole canon. Base your answer on what you find "
          "there, and say when the collection doesn't cover something."),
    "C": ("You have tools to look up a knowledge graph (ontology) of teachings built from some suttas. Every "
          "link in it cites the passage it rests on, and it records which texts it covers and what it left "
          "out. Base your answer on what the graph gives you, and say when it doesn't cover something."),
}


def system_prompt(system: str) -> str:
    return INSTRUCTIONS + ("\n\n" + TOOL_NOTE[system] if TOOL_NOTE[system] else "")


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def cap(text: str) -> str:
    if len(text) <= MAX_TOOL_CHARS:
        return text
    return text[:MAX_TOOL_CHARS] + f"\n[... cut at {MAX_TOOL_CHARS} characters]"


def tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {"name": name, "description": description,
            "input_schema": {"type": "object", "properties": properties, "required": required,
                             "additionalProperties": False}}


# --------------------------------------------------------------------------- B: the texts

STOP = set("the a an and or of to in on at is it that this what which who how does do did for with as by be "
           "from are was were according say says said sutta sn mn an dn".split())


class TextTools:
    """Segment-level BM25 over the cached texts, plus reading a whole sutta."""

    TOOLS = [
        tool("search_suttas", "Keyword search over every segment of the sutta collection, English and Pali. "
             "Returns the best-matching segments with their ids.",
             {"query": {"type": "string", "description": "Words to search for (English or Pali)"},
              "limit": {"type": "integer", "description": "How many segments to return (default 10, max 25)"}},
             ["query"]),
        tool("read_sutta", "Read a whole sutta, segment by segment, in English and Pali.",
             {"uid": {"type": "string", "description": "SuttaCentral id, for example 'sn46.51', 'mn43', 'dhp279'"}},
             ["uid"]),
        tool("list_suttas", "List every sutta in the collection with its title.", {}, []),
    ]

    def __init__(self):
        self.segments: list[tuple[str, str, str]] = []  # (segment id, english, pali)
        self.by_uid: dict[str, list[int]] = defaultdict(list)
        for pi_file in sorted(SOURCES.glob("*_pli.json")):
            en_file = pi_file.with_name(pi_file.name.replace("_pli.json", "_en.json"))
            pi = json.loads(pi_file.read_text(encoding="utf-8"))
            en = json.loads(en_file.read_text(encoding="utf-8")) if en_file.exists() else {}
            for key, p in pi.items():
                self.by_uid[key.split(":")[0]].append(len(self.segments))
                self.segments.append((key, en.get(key, "").strip(), p.strip()))
        self.docs = [self._tokens(f"{e} {p}") for _, e, p in self.segments]
        self.df = Counter(t for d in self.docs for t in set(d))
        self.avg = sum(map(len, self.docs)) / len(self.docs)

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [t for t in re.findall(r"[a-z0-9]+", fold(text)) if len(t) > 1 and t not in STOP]

    def search_suttas(self, query: str, limit: int = 10) -> str:
        limit = max(1, min(int(limit or 10), 25))
        q = self._tokens(query)
        if not q:
            return "No search words in the query."
        n, k1, b = len(self.docs), 1.5, 0.75
        scores = []
        for i, d in enumerate(self.docs):
            if not d:
                continue
            tf = Counter(d)
            s = sum(math.log(1 + (n - self.df[t] + 0.5) / (self.df[t] + 0.5)) * tf[t] * (k1 + 1)
                    / (tf[t] + k1 * (1 - b + b * len(d) / self.avg)) for t in q if t in tf)
            if s:
                scores.append((s, i))
        scores.sort(reverse=True)
        if not scores:
            return "No segments match."
        return "\n\n".join(f"{self.segments[i][0]}\n  en: {self.segments[i][1]}\n  pi: {self.segments[i][2]}"
                           for _, i in scores[:limit])

    def read_sutta(self, uid: str) -> str:
        uid = uid.strip().lower().replace(" ", "")
        if uid not in self.by_uid:
            return f"'{uid}' is not in the collection. Use list_suttas to see what is."
        return cap("\n".join(f"{self.segments[i][0]} | {self.segments[i][1]} | {self.segments[i][2]}"
                             for i in self.by_uid[uid]))

    def list_suttas(self) -> str:
        rows = []
        for uid, idx in sorted(self.by_uid.items()):
            heads = [self.segments[i][1] for i in idx if self.segments[i][0].split(":")[1].startswith("0.")]
            rows.append(f"{uid}: {' / '.join(h for h in heads if h)}")
        return "\n".join(rows)

    def call(self, name: str, args: dict) -> str:
        if name == "search_suttas":
            return self.search_suttas(args.get("query", ""), args.get("limit", 10))
        if name == "read_sutta":
            return self.read_sutta(args.get("uid", ""))
        if name == "list_suttas":
            return self.list_suttas()
        return f"Unknown tool {name}"


# --------------------------------------------------------------------------- C: the ontology

class OntologyTools:
    """Lookups over the reasoned graph: the same functions the CLI's `ask` and `sense` use."""

    TOOLS = [
        tool("list_concepts", "List every concept in the ontology (English · Pali · Chinese labels) with its kind.",
             {}, []),
        tool("lookup", "Look up a word or phrase (English, Pali or Chinese; everyday words work too). Returns the "
             "matching concepts, each with its lists, what it leads to, what conditions it, its parts, "
             "definitions, similes and editor's links, every one with its sutta wording and citation.",
             {"term": {"type": "string", "description": "For example 'sleepiness', 'pīti', 'five hindrances'"}},
             ["term"]),
        tool("word_senses", "The senses of an ambiguous Pali word (for example 'dhamma'), with example passages.",
             {"word": {"type": "string"}}, ["word"]),
        tool("read_passages", "The English and Pali text of passages the ontology cites, by segment id.",
             {"segments": {"type": "array", "items": {"type": "string"},
                           "description": "Segment ids, for example ['sn46.51:1.4', 'mn43:19.3']"}},
             ["segments"]),
        tool("coverage", "Which texts the ontology covers, and for one text what it encodes and what it left out.",
             {"uid": {"type": "string", "description": "A sutta id such as 'sn46.53'; leave empty to list all"}},
             []),
    ]

    def __init__(self):
        self.g, *_ = dho.build()
        self.lock = threading.Lock()
        self.passages = {str(self.g.value(p, dho.DHO.segment)): p for p in self.g.subjects(RDF.type, dho.DHO.Passage)}

    def list_concepts(self) -> str:
        g = self.g
        kinds = (dho.DHO.Hindrance, dho.DHO.AwakeningFactor, dho.DHO.JhanaFactor, dho.DHO.NumberedList,
                 dho.DHO.MindState, dho.DHO.AttentionMode, dho.DHO.Simile, dho.DHO.MentalQuality, dho.DHO.Concept)
        rows = []
        for c in {c for k in kinds for c in g.subjects(RDF.type, k)}:
            types = set(g.objects(c, RDF.type))
            kind = next((dho.label(g, k) for k in kinds if k in types), "")
            rows.append(f"{dho.labels(g, c)}  [{kind}]")
        return "\n".join(sorted(rows))

    def lookup(self, term: str) -> str:
        hits = dho.resolve(self.g, term)
        if not hits:
            return (f"No concept matches '{term}'. The ontology covers only the texts listed by the coverage tool. "
                    "Try another word, or list_concepts.")
        out = [f"'{term}' matches {len(hits)} concept(s): " + ", ".join(dho.label(self.g, h) for h in hits)]
        for h in hits[:6]:
            out += dho.card(self.g, h)
        return cap("\n".join(out))

    def word_senses(self, word: str) -> str:
        g, O = self.g, dho.ONTOLEX
        entries = [e for e in g.subjects(RDF.type, O.LexicalEntry)
                   if any(dho.fold(str(f)) == dho.fold(word) for form in g.objects(e, O.canonicalForm)
                          for f in g.objects(form, O.writtenRep))]
        if not entries:
            return f"No lexical entry for '{word}'."
        out = []
        for e in entries:
            senses = sorted(g.objects(e, O.sense))
            out.append(f"'{word}' has {len(senses)} senses:")
            for s in senses:
                concept = g.value(s, O.reference)
                out.append(f"- {dho.label(g, concept)}: {g.value(concept, SKOS.definition)}")
                for p in sorted(g.objects(s, dho.DHO.citedBy), key=str):
                    out.append(f"    e.g. {g.value(p, dho.DHO.segment)}: \"{dho.quote(g, p)}\" / \"{dho.quote(g, p, 'pi')}\"")
            for p in g.subjects(dho.DHO.translatorRendering, None):
                out.append(f"contested, left unassigned: {g.value(p, dho.DHO.segment)} \"{dho.quote(g, p, 'pi')}\" "
                           f"(rendered '{g.value(p, dho.DHO.translatorRendering)}')")
        return "\n".join(out)

    def read_passages(self, segments: list[str]) -> str:
        out = []
        for s in segments[:40]:
            p = self.passages.get(s.strip())
            out.append(f"{s}\n  en: {dho.quote(self.g, p)}\n  pi: {dho.quote(self.g, p, 'pi')}" if p
                       else f"{s}: not a passage the ontology cites.")
        return "\n\n".join(out)

    def coverage(self, uid: str = "") -> str:
        g, D = self.g, dho.DHO
        texts = sorted(g.subjects(D.coverage, None), key=str)
        if not uid:
            return "\n".join(f"{str(t).split('#t-', 1)[1]}: {dho.label(g, g.value(t, D.coverage))}" for t in texts)
        t = D[f"t-{uid.strip().lower().replace(' ', '')}"]
        if g.value(t, D.coverage) is None:
            return f"'{uid}' is not in the ontology's coverage: it has not been read or modelled."
        return (f"{uid}: {dho.label(g, g.value(t, D.coverage))}\n"
                f"encodes: {g.value(t, D.encodes) or '-'}\nleft out: {g.value(t, D.leftOut) or '-'}")

    def call(self, name: str, args: dict) -> str:
        with self.lock:
            if name == "list_concepts":
                return self.list_concepts()
            if name == "lookup":
                return self.lookup(args.get("term", ""))
            if name == "word_senses":
                return self.word_senses(args.get("word", ""))
            if name == "read_passages":
                segs = args.get("segments") or []
                return self.read_passages([segs] if isinstance(segs, str) else segs)
            if name == "coverage":
                return self.coverage(args.get("uid", "") or "")
            return f"Unknown tool {name}"
