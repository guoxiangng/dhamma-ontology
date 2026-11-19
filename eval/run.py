"""Run the eval: put each question to systems A, B and C, have a judge mark each answer, report.

    python eval/run.py plan                         # dry run: no model calls; counts, tool sizes, sample prompt
    python eval/run.py tool C lookup "monkey mind"  # try one of B's or C's tools locally (no model)
    python eval/run.py run --out eval/results/<name> [--only Q01,Q25] [--systems A,B,C] [--runs 1]
    python eval/run.py report --out eval/results/<name>

Model calls go through headless Claude Code (`claude -p`) on your Claude plan; nothing is
deployed and nothing is billed per call (usage counts toward the plan's limits). Each call is
isolated:

  --system-prompt   our instructions replace Claude Code's own
  --tools ""        no built-in tools: no file reading, no shell, no web
  --mcp-config + --strict-mcp-config
                    only B's or C's tool server (eval/mcp_server.py), nothing else
  --setting-sources project, run from an empty temporary folder outside the repo
                    no CLAUDE.md, hooks, skills or memory from this project

so a system can't reach the answer key. The judge gets the key in its prompt, and no tools.

`run` writes answers.jsonl and judgments.jsonl as it goes and skips anything already done, so
it can be stopped and resumed (for example after hitting the plan's usage limit).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import systems as S  # noqa: E402

QUESTIONS = HERE / "questions.toml"
ANSWER_MODEL = "claude-sonnet-5-5"
JUDGE_MODEL = "claude-opus-5-5"
EFFORT = "medium"
MAX_TURNS = 10
SERVER = {"B": "suttas", "C": "ontology"}

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "gold_points": {"type": "array", "items": {"type": "string", "enum": ["yes", "partly", "no"]}},
        "must_not": {"type": "array", "items": {"type": "boolean"}},
        "layer_mixup": {"type": "boolean"},
        "scope_honest": {"type": ["boolean", "null"]},
        "reason": {"type": "string"},
    },
    "required": ["gold_points", "must_not", "layer_mixup", "scope_honest", "reason"],
}


def load_questions(only: str | None = None) -> list[dict]:
    qs = tomllib.loads(QUESTIONS.read_text(encoding="utf-8"))["q"]
    if only:
        keep = {x.strip() for x in only.split(",")}
        qs = [q for q in qs if q["id"] in keep]
    return qs


def passages_for(q: dict) -> str:
    """The English and Pali of the question's gold segments, for the judge."""
    sys.path.insert(0, str(S.ROOT / "scripts"))
    from sc import load  # noqa: E402
    out = []
    for seg in q.get("segments", []) + q.get("also_ok_segments", []):
        try:
            en, pi = load(seg.split(":")[0])
            out.append(f"{seg}\n  en: {en.get(seg, '').strip()}\n  pi: {pi.get(seg, '').strip()}")
        except Exception as e:  # noqa: BLE001
            out.append(f"{seg}: could not load ({e})")
    return "\n".join(out) or "(none: the answer key rests on the absence of a source)"


# --------------------------------------------------------------------------- headless Claude Code

def claude_bin() -> str:
    """CLAUDE_BIN, else the newest binary bundled with the VS Code extension, else `claude` on PATH."""
    if os.environ.get("CLAUDE_BIN"):
        return os.environ["CLAUDE_BIN"]
    found = glob.glob(str(Path.home() / ".vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude.exe"))
    ver = lambda p: tuple(int(x) for x in re.search(r"claude-code-(\d+)\.(\d+)\.(\d+)", p).groups())  # noqa: E731
    return max(found, key=ver) if found else (shutil.which("claude") or "claude")


class LimitHit(Exception):
    """The plan's usage or rate limit: stop the run, resume later."""


class Claude:
    def __init__(self):
        self.bin = claude_bin()
        self.cwd = Path(tempfile.mkdtemp(prefix="dho-eval-"))  # empty, outside the repo
        self.env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
        self.env["ENABLE_CLAUDEAI_MCP_SERVERS"] = "false"
        py = sys.executable
        for s, name in SERVER.items():
            (self.cwd / f"mcp-{s}.json").write_text(json.dumps({"mcpServers": {name: {
                "type": "stdio", "command": py, "args": [str(HERE / "mcp_server.py"), s]}}}), encoding="utf-8")

    def call(self, prompt: str, system: str, model: str, mcp: str | None = None, schema: dict | None = None,
             stream: bool = False) -> list[dict] | dict:
        args = [self.bin, "-p", prompt, "--system-prompt", system, "--tools", "", "--strict-mcp-config",
                "--setting-sources", "project", "--no-session-persistence", "--model", model, "--effort", EFFORT,
                "--max-turns", str(MAX_TURNS)]
        if mcp:
            args += ["--mcp-config", str(self.cwd / f"mcp-{mcp}.json"), "--allowedTools", f"mcp__{SERVER[mcp]}"]
        if schema:
            args += ["--json-schema", json.dumps(schema)]
        args += ["--output-format", "stream-json", "--verbose"] if stream else ["--output-format", "json"]
        p = subprocess.run(args, cwd=self.cwd, env=self.env, stdin=subprocess.DEVNULL, capture_output=True,
                           encoding="utf-8", errors="replace", timeout=900)
        lines = [json.loads(l) for l in p.stdout.splitlines() if l.strip().startswith("{")]
        result = next((m for m in reversed(lines) if m.get("type") == "result"), None)
        if result is None:
            raise RuntimeError(f"no result (exit {p.returncode}): {p.stderr[-400:]}")
        if result.get("is_error"):
            text = str(result.get("result", ""))
            if re.search(r"usage limit|rate limit|429|overloaded|limit reached", text, re.I):
                raise LimitHit(text[:300])
            raise RuntimeError(text[:400])
        return lines if stream else result


def answer(cc: Claude, system: str, q: dict) -> dict:
    lines = cc.call(q["question"], S.system_prompt(system), ANSWER_MODEL, mcp=system if system != "A" else None,
                    stream=True)
    calls, pending = [], {}
    for m in lines:
        content = (m.get("message") or {}).get("content")
        if m.get("type") not in ("assistant", "user") or not isinstance(content, list):
            continue
        for b in content:
            if b.get("type") == "tool_use":
                pending[b["id"]] = {"tool": b["name"].split("__")[-1], "input": b.get("input", {})}
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                c = b.get("content")
                text = c if isinstance(c, str) else "".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
                calls.append({**pending.pop(b["tool_use_id"]), "chars": len(text), "head": text[:700]})
    result = next(m for m in reversed(lines) if m.get("type") == "result")
    return {"text": (result.get("result") or "").strip(), "turns": result.get("num_turns"), "calls": calls,
            "cost": round(result.get("total_cost_usd") or 0, 6), "model": ANSWER_MODEL}


JUDGE_SYSTEM = """You grade answers in an evaluation of question-answering systems about the early Buddhist suttas.

You get a question, an answer key written from the source texts, the source passages the key rests on, and one system's answer. Grade only against the answer key and the passages, not against your own views of Buddhism or of what a good answer would add. Wording may differ from the key; judge substance. Be literal and strict.

Fields:
- gold_points: for each answer-key point, in order: "yes" if the answer makes it, "partly" if it makes part of it, "no" if not.
- must_not: for each listed wrong claim, in order: true if the answer makes that claim.
- layer_mixup: true if the answer presents commentary, later or modern ideas as the Buddha's words or as what a sutta says.
- scope_honest: only when the prompt says SCOPE CHECK: yes. True if the answer is clear about what its sources do and don't support (it says when something isn't covered, and doesn't present general knowledge as if its sources said it). Otherwise null.
- reason: one or two sentences."""


def judge(cc: Claude, q: dict, system: str, ans: dict) -> dict:
    scope_check = q["scope"] in ("partial", "outside") and system != "A"
    tools_used = "\n".join(f"- {c['tool']}({json.dumps(c['input'], ensure_ascii=False)}) -> {c['head'][:400]!r}"
                           for c in ans["calls"]) or "(none)"
    prompt = f"""QUESTION ({q['category']}, {q['id']}): {q['question']}

ANSWER KEY POINTS:
{chr(10).join(f"{i + 1}. {g}" for i, g in enumerate(q['gold']))}

ALSO ACCEPTABLE: {'; '.join(q.get('also_ok', [])) or '(none)'}

WRONG CLAIMS TO CHECK FOR:
{chr(10).join(f"{i + 1}. {m}" for i, m in enumerate(q['must_not'])) or '(none)'}

NOTE FROM THE KEY'S AUTHOR: {q.get('note', '(none)')}

SOURCE PASSAGES:
{passages_for(q)}

{'SCOPE CHECK: yes. ' + S.TOOL_NOTE[system] + ' Its tool calls (results truncated):' + chr(10) + tools_used if scope_check else 'SCOPE CHECK: no'}

ANSWER TO GRADE:
{ans['text'] or '(empty)'}"""
    r = cc.call(prompt, JUDGE_SYSTEM, JUDGE_MODEL, schema=JUDGE_SCHEMA)
    v = r.get("structured_output") or {}
    if not v:
        m = re.search(r"\{.*\}", r.get("result") or "", re.S)
        try:
            v = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            v = {}
    return {"verdict": v, "raw": "" if v else (r.get("result") or ""), "cost": round(r.get("total_cost_usd") or 0, 6),
            "model": JUDGE_MODEL}


# --------------------------------------------------------------------------- scoring

REF = re.compile(r"\b(SN|MN|AN|DN|Dhp|Snp|Ud|Iti|Thag|Thig)\s?(\d+(?:\.\d+)?(?:[–-]\d+)?)", re.I)


def cited_uids(text: str) -> set[str]:
    # "SN 46" or "AN 4" alone names a whole collection, not a sutta.
    return {f"{a.lower()}{b}" for a, b in REF.findall(text) if "." in b or a.upper() not in ("SN", "AN")}


def key_uids(q: dict) -> set[str]:
    u = {s.split(":")[0] for s in q.get("segments", []) + q.get("also_ok_segments", [])}
    return u | cited_uids(" ".join(q.get("also_ok", [])))


def score(q: dict, v: dict) -> dict:
    gp = v.get("gold_points") or []
    yes = sum(x == "yes" for x in gp)
    some = sum(x in ("yes", "partly") for x in gp)
    correct = 2 if gp and yes == len(q["gold"]) else (1 if some else 0)
    return {"correct": correct, "complete": round(yes / len(q["gold"]), 2),
            "trap": any(v.get("must_not") or []), "layer_mixup": bool(v.get("layer_mixup")),
            "scope_honest": v.get("scope_honest")}


# --------------------------------------------------------------------------- commands

def jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []


def cmd_plan(a) -> int:
    qs = load_questions(a.only)
    systems, runs = a.systems.split(","), a.runs
    n = len(qs) * len(systems) * runs
    print(f"Questions: {len(qs)}   systems: {','.join(systems)}   runs each: {runs}")
    print(f"Calls: {n} answers ({ANSWER_MODEL}) + {n} judgments ({JUDGE_MODEL}), effort {EFFORT}")
    print(f"Via headless Claude Code on your plan: {claude_bin()}   (no calls in plan)\n")
    t0 = time.time()
    text = S.TextTools()
    print(f"B index: {len(text.segments):,} segments in {len(text.by_uid)} texts ({time.time() - t0:.1f}s)")
    t0 = time.time()
    onto = S.OntologyTools()
    print(f"C graph: {len(onto.g):,} triples, {len(onto.passages)} cited passages ({time.time() - t0:.1f}s)\n")
    search = [len(text.search_suttas(q["question"])) for q in qs]
    reads = [len(text.read_sutta(u)) for q in qs for u in {s.split(':')[0] for s in q["segments"]}] or [0]
    looks = [len(onto.lookup(w)) for w in ("sensual desire", "rapture", "dullness", "five hindrances",
                                           "awakening factors", "monkey mind", "first absorption", "love")]
    avg = lambda xs: sum(xs) / len(xs)  # noqa: E731
    print(f"Tool output, average characters: search {avg(search):,.0f}   read_sutta {avg(reads):,.0f}   "
          f"lookup {avg(looks):,.0f}   list_concepts {len(onto.list_concepts()):,}   list_suttas {len(text.list_suttas()):,}")
    print("\nThis uses your plan's usage allowance, not money. If it hits the limit, the run stops; rerun the same\n"
          "command later and it carries on where it stopped.\n")
    q = next((q for q in qs if q["category"] == "plain"), qs[0])
    print(f"--- sample: system prompt for C, question {q['id']} ---\n{S.system_prompt('C')}\n\nUSER: {q['question']}")
    return 0


def cmd_tool(a) -> int:
    t = S.TextTools() if a.system == "B" else S.OntologyTools()
    args = json.loads(a.args) if a.args.startswith("{") else {
        "search_suttas": {"query": a.args}, "read_sutta": {"uid": a.args}, "lookup": {"term": a.args},
        "word_senses": {"word": a.args}, "coverage": {"uid": a.args},
        "read_passages": {"segments": a.args.split(",")}}.get(a.name, {})
    print(t.call(a.name, args))
    return 0


def cmd_run(a) -> int:
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    qs = load_questions(a.only)
    systems = a.systems.split(",")
    cc = Claude()
    print(f"Claude Code: {cc.bin}\nWorking folder (empty, outside the repo): {cc.cwd}")
    lock = threading.Lock()
    cfg = out / "config.json"
    if not cfg.exists():
        cfg.write_text(json.dumps({
            "via": "headless Claude Code", "answer_model": ANSWER_MODEL, "judge_model": JUDGE_MODEL,
            "effort": EFFORT, "max_turns": MAX_TURNS, "systems": systems, "instructions": S.INSTRUCTIONS,
            "tool_notes": S.TOOL_NOTE, "judge_system": JUDGE_SYSTEM, "started": time.strftime("%Y-%m-%d %H:%M:%S")},
            indent=2, ensure_ascii=False), encoding="utf-8")

    def append(name, rec):
        with lock, open(out / name, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    done = {(r["id"], r["system"], r["run"]): r for r in jsonl(out / "answers.jsonl")}
    judged = {(r["id"], r["system"], r["run"]) for r in jsonl(out / "judgments.jsonl") if r.get("verdict")}
    by_id = {q["id"]: q for q in qs}
    jobs = [(q, s, n) for n in range(1, a.runs + 1) for q in qs for s in systems]
    stopped = threading.Event()

    def work(job):
        q, s, n = job
        key = (q["id"], s, n)
        if stopped.is_set():
            return
        try:
            if key not in done:
                ans = answer(cc, s, q)
                rec = {"id": q["id"], "system": s, "run": n, **ans}
                append("answers.jsonl", rec)
                done[key] = rec
            if key not in judged:
                j = judge(cc, by_id[q["id"]], s, done[key])
                append("judgments.jsonl", {"id": q["id"], "system": s, "run": n, **j})
                sc = score(by_id[q["id"]], j["verdict"])["correct"] if j["verdict"] else "?"
                print(f"  {q['id']} {s} run {n}: {sc}   ({len(done[key]['calls'])} tool calls)", flush=True)
        except LimitHit as e:
            stopped.set()
            print(f"  plan limit: {e}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  {key}: failed: {type(e).__name__}: {e}", flush=True)

    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        list(pool.map(work, jobs))
    if stopped.is_set():
        print("Stopped at the plan's usage limit. Rerun the same command later to carry on.")
    shutil.rmtree(cc.cwd, ignore_errors=True)
    return cmd_report(a)


def cmd_report(a) -> int:
    out = Path(a.out)
    qs = {q["id"]: q for q in load_questions()}
    answers = {(r["id"], r["system"], r["run"]): r for r in jsonl(out / "answers.jsonl")}
    cfg = json.loads((out / "config.json").read_text(encoding="utf-8")) if (out / "config.json").exists() else {}
    rows = []
    for j in jsonl(out / "judgments.jsonl"):
        key = (j["id"], j["system"], j["run"])
        if not j.get("verdict") or key not in answers:
            continue
        q, ans = qs[j["id"]], answers[key]
        sc = score(q, j["verdict"])
        cites = cited_uids(ans["text"])
        sc["right_source"] = bool(cites & key_uids(q)) if q["segments"] else None
        sc["other_cites"] = sorted(cites - key_uids(q))
        rows.append({**j, **sc, "category": q["category"], "scope": q["scope"], "answer": ans["text"],
                     "answer_cost": ans["cost"], "turns": ans["turns"], "ncalls": len(ans["calls"])})
    if not rows:
        print("No judged answers yet.")
        return 1
    systems = sorted({r["system"] for r in rows})
    pct = lambda xs: f"{100 * sum(xs) / len(xs):.0f}%" if xs else "–"  # noqa: E731

    def stats(rs):
        bysq = defaultdict(list)
        graded = [r for r in rs if r["category"] != "scope"]  # scope questions are scored only for honesty
        for r in graded:
            bysq[r["id"]].append(r["correct"])
        return {
            "answers": len(rs),
            "accuracy": pct([r["correct"] / 2 for r in graded]),
            "fully right": pct([r["correct"] == 2 for r in graded]),
            "wrong (0)": pct([r["correct"] == 0 for r in graded]),
            "trap failed": pct([r["trap"] for r in rs if qs[r["id"]]["must_not"]]),
            "layer mix-up": pct([r["layer_mixup"] for r in rs]),
            "scope honest": pct([bool(r["scope_honest"]) for r in rs if r["scope_honest"] is not None]),
            "right source": pct([r["right_source"] for r in rs if r["right_source"] is not None]),
            "cites outside key": pct([bool(r["other_cites"]) for r in rs]),
            "consistent": pct([len(set(v)) == 1 for v in bysq.values() if len(v) > 1]),
            "tool calls/answer": f"{sum(r['ncalls'] for r in rs) / len(rs):.1f}",
            "API-equivalent cost": f"${sum(r['answer_cost'] + r['cost'] for r in rs):.2f}",
        }

    st = {s: stats([r for r in rows if r["system"] == s]) for s in systems}
    names = {"A": "A plain", "B": "B + text", "C": "C + ontology"}
    L = [f"# Eval results: {out.name}", "",
         f"Answers by `{cfg.get('answer_model', '?')}`, marked by `{cfg.get('judge_model', '?')}`, "
         f"via {cfg.get('via', '?')}. {len(rows)} judged answers. "
         "Every gold answer is still **draft**, and the judge's verdicts are unreviewed until the owner checks the list below.", "",
         "| Measure | " + " | ".join(names[s] for s in systems) + " |", "|---|" + "---:|" * len(systems)]
    for m in next(iter(st.values())):
        L.append(f"| {m} | " + " | ".join(str(st[s][m]) for s in systems) + " |")
    L += ["", "Accuracy is the mean score out of 2, leaving out the two scope questions. Trap failed counts only "
          "questions with wrong claims to check. Scope honest counts only B and C on partial and outside questions. "
          "Consistent counts questions run more than once. API-equivalent cost is what the calls would cost at list "
          "price; on the plan they count toward its usage limit instead.", "",
          "## By category (accuracy)", "", "| Category | " + " | ".join(names[s] for s in systems) + " |",
          "|---|" + "---:|" * len(systems)]
    for cat in sorted({r["category"] for r in rows}):
        L.append(f"| {cat} | " + " | ".join(pct([r["correct"] / 2 for r in rows if r["system"] == s and r["category"] == cat])
                                         for s in systems) + " |")
    L += ["", "## Every question (score per run, 0–2; T = trap failed, L = layer mix-up)", "",
          "| Q | Cat | " + " | ".join(systems) + " |", "|---|---|" + "---|" * len(systems)]
    for qid in sorted({r["id"] for r in rows}):
        cells = []
        for s in systems:
            rs = sorted((r for r in rows if r["id"] == qid and r["system"] == s), key=lambda r: r["run"])
            cells.append(" ".join(f"{r['correct']}{'T' if r['trap'] else ''}{'L' if r['layer_mixup'] else ''}" for r in rs))
        L.append(f"| {qid} | {qs[qid]['category']} | " + " | ".join(cells) + " |")
    L += ["", "## For the owner to check", "",
          "Every 0, every trap flag, every layer flag, and every sutta cited outside the answer key "
          "(possible invented citations). Each line: question, system, run, the judge's reason.", ""]
    for r in sorted(rows, key=lambda r: (r["id"], r["system"], r["run"])):
        flags = [f for f, on in (("score 0", r["correct"] == 0 and r["category"] != "scope"), ("trap", r["trap"]),
                                 ("layer", r["layer_mixup"]), ("not honest about scope", r["scope_honest"] is False),
                                 (f"cites {', '.join(r['other_cites'])}", r["other_cites"])) if on]
        if flags:
            L.append(f"- **{r['id']} {r['system']} run {r['run']}** ({'; '.join(flags)}): {r['verdict'].get('reason', '')}")
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:6 + len(next(iter(st.values())))]))
    print(f"\nWrote {out / 'summary.md'}")
    return 0


def main() -> int:
    global ANSWER_MODEL, JUDGE_MODEL
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "run"):
        sp = sub.add_parser(name)
        sp.add_argument("--only", help="comma-separated question ids")
        sp.add_argument("--systems", default="A,B,C")
        sp.add_argument("--runs", type=int, default=1)
        sp.add_argument("--model", default=ANSWER_MODEL, help="model that answers (same for A, B and C)")
        sp.add_argument("--judge", default=JUDGE_MODEL, help="model that marks")
        if name == "run":
            sp.add_argument("--out", required=True)
            sp.add_argument("--workers", type=int, default=2)
    sp = sub.add_parser("report")
    sp.add_argument("--out", required=True)
    sp = sub.add_parser("tool")
    sp.add_argument("system", choices=["B", "C"])
    sp.add_argument("name")
    sp.add_argument("args", nargs="?", default="")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    ANSWER_MODEL, JUDGE_MODEL = getattr(a, "model", ANSWER_MODEL), getattr(a, "judge", JUDGE_MODEL)
    return {"plan": cmd_plan, "run": cmd_run, "report": cmd_report, "tool": cmd_tool}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
