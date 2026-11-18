"""Run the eval: put each question to systems A, B and C, have a judge mark each answer, report.

    python eval/run.py plan                       # dry run: no model calls; counts, sample prompts, cost estimate
    python eval/run.py tool C lookup "monkey mind"  # try one of B's or C's tools locally (no model)
    python eval/run.py run --out eval/results/<name> --cap 15 [--only Q01,Q25] [--systems A,B,C] [--runs 3]
    python eval/run.py report --out eval/results/<name>

Runs on your machine. Model calls go to Amazon Bedrock with your default AWS profile
(region ap-southeast-1, the account's `global.` inference profiles). Nothing is deployed.
Behind a TLS-inspecting proxy, set AWS_CA_BUNDLE to your CA bundle.

`run` writes answers.jsonl and judgments.jsonl as it goes and skips anything already done,
so it can be stopped and resumed. It stops before spending more than --cap US dollars
(estimated at list prices; Bedrock bills separately and may differ).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
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
REGION = os.environ.get("EVAL_AWS_REGION", "ap-southeast-1")
ANSWER_MODEL = "global.anthropic.claude-haiku-5-5"
JUDGES = {"haiku": "global.anthropic.claude-haiku-5-5", "sonnet": "global.anthropic.claude-sonnet-5-5"}
JUDGE_MODEL = JUDGES["haiku"]  # set by --judge
# US$ per million tokens, input / output (Anthropic list prices; Haiku 5.5's rate is for prompts under 100K).
PRICE = {JUDGES["haiku"]: (0.10, 0.50), JUDGES["sonnet"]: (2.00, 10.00)}
MAX_TURNS = 8


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


# --------------------------------------------------------------------------- money

class Meter:
    def __init__(self, cap: float):
        self.cap, self.spent, self.lock = cap, 0.0, threading.Lock()

    def add(self, model: str, usage) -> float:
        pin, pout = PRICE[model]
        tin = (usage.input_tokens or 0) + (getattr(usage, "cache_creation_input_tokens", 0) or 0) \
            + (getattr(usage, "cache_read_input_tokens", 0) or 0)
        cost = (tin * pin + (usage.output_tokens or 0) * pout) / 1e6
        with self.lock:
            self.spent += cost
        return cost

    def ok(self) -> bool:
        with self.lock:
            return self.spent < self.cap


# --------------------------------------------------------------------------- model calls

def client():
    from anthropic import AnthropicBedrock
    kw = {}
    bundle = os.environ.get("AWS_CA_BUNDLE")
    if bundle:
        from anthropic import DefaultHttpxClient
        kw["http_client"] = DefaultHttpxClient(verify=bundle)
    return AnthropicBedrock(aws_region=REGION, **kw)


def create(cl, **kw):
    for attempt in range(5):
        try:
            return cl.messages.create(**kw)
        except Exception as e:  # noqa: BLE001  (SDK already retries 429/5xx twice; this covers throttling bursts)
            name = type(e).__name__
            if attempt == 4 or not any(k in name for k in ("RateLimit", "InternalServer", "APIConnection", "Overloaded", "Timeout")):
                raise
            time.sleep(5 * 2 ** attempt)


def answer(cl, meter: Meter, system: str, q: dict, tools) -> dict:
    messages = [{"role": "user", "content": q["question"]}]
    calls, cost, turns, r = [], 0.0, 0, None
    for turn in range(MAX_TURNS):
        turns += 1
        kw = dict(model=ANSWER_MODEL, max_tokens=8000, system=S.system_prompt(system), messages=messages,
                  output_config={"effort": "medium"})
        if tools:
            kw["tools"] = tools.TOOLS
            if turn == MAX_TURNS - 1:
                kw["tool_choice"] = {"type": "none"}
        r = create(cl, **kw)
        cost += meter.add(ANSWER_MODEL, r.usage)
        messages.append({"role": "assistant", "content": r.content})
        if r.stop_reason != "tool_use":
            break
        results = []
        for b in r.content:
            if b.type == "tool_use":
                out = tools.call(b.name, dict(b.input))
                calls.append({"tool": b.name, "input": dict(b.input), "chars": len(out), "head": out[:700]})
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": out})
        messages.append({"role": "user", "content": results})
    text = "\n".join(b.text for b in r.content if b.type == "text").strip()
    return {"text": text, "stop_reason": r.stop_reason, "turns": turns, "calls": calls, "cost": round(cost, 6)}


JUDGE_SYSTEM = """You grade answers in an evaluation of question-answering systems about the early Buddhist suttas.

You get a question, an answer key written from the source texts, the source passages the key rests on, and one system's answer. Grade only against the answer key and the passages, not against your own views of Buddhism or of what a good answer would add. Wording may differ from the key; judge substance. Be literal and strict.

Reply with one JSON object and nothing else:
{
  "gold_points": [one of "yes", "partly", "no" for each answer-key point, in order],
  "must_not": [true or false for each listed wrong claim, in order: true if the answer makes that claim],
  "layer_mixup": true if the answer presents commentary, later or modern ideas as the Buddha's words or as what a sutta says, else false,
  "scope_honest": for questions marked SCOPE CHECK only: true if the answer is clear about what its sources do and don't support (it says when something is not covered, and doesn't present general knowledge as if its sources said it), else false; null for other questions,
  "reason": "one or two sentences"
}"""


def judge(cl, meter: Meter, q: dict, system: str, ans: dict) -> dict:
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
    r = create(cl, model=JUDGE_MODEL, max_tokens=8000, system=JUDGE_SYSTEM,
               messages=[{"role": "user", "content": prompt}], output_config={"effort": "medium"})
    cost = meter.add(JUDGE_MODEL, r.usage)
    raw = "\n".join(b.text for b in r.content if b.type == "text")
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        v = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        v = {}
    return {"verdict": v, "raw": raw if not v else "", "cost": round(cost, 6)}


# --------------------------------------------------------------------------- scoring

REF = re.compile(r"\b(SN|MN|AN|DN|Dhp|Snp|Ud|Iti|Thag|Thig)\s?(\d+(?:\.\d+)?(?:[–-]\d+)?)", re.I)


def cited_uids(text: str) -> set[str]:
    return {f"{a.lower()}{b}" for a, b in REF.findall(text)}


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
    print(f"Questions: {len(qs)}   systems: {','.join(systems)}   runs each: {runs}")
    print(f"Answers to get: {len(qs) * len(systems) * runs}   judgments: {len(qs) * len(systems) * runs}")
    print(f"Answer model: {ANSWER_MODEL}   judge: {JUDGE_MODEL}   region: {REGION}   (no calls in plan)\n")
    t0 = time.time()
    text = S.TextTools()
    print(f"B index: {len(text.segments):,} segments in {len(text.by_uid)} texts ({time.time() - t0:.1f}s)")
    t0 = time.time()
    onto = S.OntologyTools()
    print(f"C graph: {len(onto.g):,} triples, {len(onto.passages)} cited passages ({time.time() - t0:.1f}s)\n")

    # Measure what the tools actually return for these questions, to size the estimate.
    search = [len(text.search_suttas(q["question"])) for q in qs]
    reads = [len(text.read_sutta(u)) for q in qs for u in {s.split(':')[0] for s in q["segments"]}] or [0]
    looks = [len(onto.lookup(w)) for w in ("sensual desire", "rapture", "dullness", "five hindrances",
                                           "awakening factors", "monkey mind", "first absorption", "love")]
    avg = lambda xs: sum(xs) / len(xs)  # noqa: E731
    print(f"Tool output, average characters: search {avg(search):,.0f}   read_sutta {avg(reads):,.0f}   "
          f"lookup {avg(looks):,.0f}   list_concepts {len(onto.list_concepts()):,}   list_suttas {len(text.list_suttas()):,}")
    judge_in = avg([len(passages_for(q)) for q in qs]) / 3 + 1200

    tok = lambda chars: chars / 3  # noqa: E731  (Pali diacritics tokenise densely; err high)
    base = {s: tok(len(S.system_prompt(s)) + (3000 if s != "A" else 0)) + 60 for s in systems}
    # B: one search and one read, then answer. C: two lookups and one passage read, then answer.
    loops = {"A": (base.get("A", 0), 1500),
             "B": (3 * base.get("B", 0) + 2 * tok(avg(search)) + tok(avg(reads)), 3000),
             "C": (4 * base.get("C", 0) + 3 * tok(avg(looks)) + tok(1500), 3500)}
    total = 0.0
    print("\nEstimate per answer (tokens in / out, cost):")
    for s in systems:
        tin, tout = loops[s]
        c = (tin * PRICE[ANSWER_MODEL][0] + tout * PRICE[ANSWER_MODEL][1]) / 1e6
        n = len(qs) * runs
        total += c * n
        print(f"  {s}: {tin:>7,.0f} / {tout:,}   ${c:.4f}  x {n} = ${c * n:.2f}")
    nj = len(qs) * len(systems) * runs
    cj = ((judge_in + 400) * PRICE[JUDGE_MODEL][0] + 2000 * PRICE[JUDGE_MODEL][1]) / 1e6
    total += cj * nj
    print(f"  judge: {judge_in + 400:>7,.0f} / 2,000   ${cj:.4f}  x {nj} = ${cj * nj:.2f}")
    print(f"\nEstimated total: ${total:.2f}   (allow up to ${2 * total:.2f}: tool loops vary)")
    print("At Anthropic list prices; Bedrock bills these models separately and may differ.\n")

    q = next((q for q in qs if q["category"] == "plain"), qs[0])
    print(f"--- sample: system prompt for C, question {q['id']} ---\n{S.system_prompt('C')}\n\nUSER: {q['question']}")
    print(f"\n--- sample: B search for that question (first 600 chars) ---\n{text.search_suttas(q['question'])[:600]}")
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
    meter = Meter(a.cap)
    meter.spent = sum(r.get("cost", 0) for f in ("answers.jsonl", "judgments.jsonl") for r in jsonl(out / f))
    print(f"Already spent in {out}: ${meter.spent:.4f}   cap ${a.cap:.2f}")
    tools = {"A": None, "B": S.TextTools() if "B" in systems else None, "C": S.OntologyTools() if "C" in systems else None}
    cl = client()
    lock = threading.Lock()
    (out / "config.json").write_text(json.dumps({
        "answer_model": ANSWER_MODEL, "judge_model": JUDGE_MODEL, "region": REGION, "runs": a.runs,
        "systems": systems, "instructions": S.INSTRUCTIONS, "tool_notes": S.TOOL_NOTE,
        "judge_system": JUDGE_SYSTEM, "started": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=2, ensure_ascii=False),
        encoding="utf-8")

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
        if key not in done:
            if not meter.ok():
                stopped.set()
                return
            try:
                ans = answer(cl, meter, s, q, tools[s])
            except Exception as e:  # noqa: BLE001
                print(f"  {key}: answer failed: {type(e).__name__}: {e}")
                return
            rec = {"id": q["id"], "system": s, "run": n, **ans}
            append("answers.jsonl", rec)
            done[key] = rec
        if key not in judged:
            if not meter.ok():
                stopped.set()
                return
            try:
                j = judge(cl, meter, by_id[q["id"]], s, done[key])
            except Exception as e:  # noqa: BLE001
                print(f"  {key}: judge failed: {type(e).__name__}: {e}")
                return
            append("judgments.jsonl", {"id": q["id"], "system": s, "run": n, **j})
            print(f"  {q['id']} {s} run {n}: {score(by_id[q['id']], j['verdict'])['correct'] if j['verdict'] else '?'}"
                  f"   spent ${meter.spent:.3f}")

    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        list(pool.map(work, jobs))
    if stopped.is_set():
        print(f"Stopped at the ${a.cap:.2f} cap (spent ${meter.spent:.4f}). Rerun with a higher --cap to continue.")
    print(f"Spent ${meter.spent:.4f}")
    return cmd_report(a)


def cmd_report(a) -> int:
    out = Path(a.out)
    qs = {q["id"]: q for q in load_questions()}
    answers = {(r["id"], r["system"], r["run"]): r for r in jsonl(out / "answers.jsonl")}
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
            "n": len(rs),
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
            "cost": f"${sum(r['answer_cost'] + r['cost'] for r in rs):.2f}",
        }

    st = {s: stats([r for r in rows if r["system"] == s]) for s in systems}
    names = {"A": "A plain", "B": "B + text", "C": "C + ontology"}
    L = [f"# Eval results: {out.name}", "",
         f"Answer model `{ANSWER_MODEL}`, judge `{JUDGE_MODEL}`. {len(rows)} judged answers. "
         "Every gold answer is still **draft**; judge verdicts are unreviewed until the owner checks the list below.", "",
         "| Measure | " + " | ".join(names[s] for s in systems) + " |", "|---|" + "---:|" * len(systems)]
    for m in next(iter(st.values())):
        L.append(f"| {m} | " + " | ".join(str(st[s][m]) for s in systems) + " |")
    L += ["", "Accuracy is the mean score out of 2. Trap failed counts only questions with wrong claims to check. "
          "Scope honest counts only B and C on partial and outside questions. Consistent counts questions run more than once.", "",
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
        flags = [f for f, on in (("score 0", r["correct"] == 0), ("trap", r["trap"]), ("layer", r["layer_mixup"]),
                                 (f"cites {', '.join(r['other_cites'])}", r["other_cites"])) if on]
        if flags:
            L.append(f"- **{r['id']} {r['system']} run {r['run']}** ({'; '.join(flags)}): {r['verdict'].get('reason', '')}")
    (out / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("\n".join(L[:6 + len(next(iter(st.values())))]))
    print(f"\nWrote {out / 'summary.md'}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "run"):
        sp = sub.add_parser(name)
        sp.add_argument("--judge", choices=sorted(JUDGES), default="haiku",
                        help="marking model: haiku (default, ~20x cheaper) or sonnet")
        sp.add_argument("--only", help="comma-separated question ids")
        sp.add_argument("--systems", default="A,B,C")
        sp.add_argument("--runs", type=int, default=3)
        if name == "run":
            sp.add_argument("--out", required=True)
            sp.add_argument("--cap", type=float, required=True, help="stop before spending more than this many US$")
            sp.add_argument("--workers", type=int, default=4)
    sp = sub.add_parser("report")
    sp.add_argument("--out", required=True)
    sp = sub.add_parser("tool")
    sp.add_argument("system", choices=["B", "C"])
    sp.add_argument("name")
    sp.add_argument("args", nargs="?", default="")
    a = p.parse_args()
    global JUDGE_MODEL
    JUDGE_MODEL = JUDGES[getattr(a, "judge", "haiku")]
    if a.cmd == "report" and (Path(a.out) / "config.json").exists():
        JUDGE_MODEL = json.loads((Path(a.out) / "config.json").read_text(encoding="utf-8"))["judge_model"]
    sys.stdout.reconfigure(encoding="utf-8")
    return {"plan": cmd_plan, "run": cmd_run, "report": cmd_report, "tool": cmd_tool}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
