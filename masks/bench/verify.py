"""The selection loop: every answer is shown what it selects, and the model keeps it or corrects it.

A check a pipeline can run without the answer key. For each task of a sheet the model sees its mask and
ambmask's view of it (pick.card: the atom count, residues and atom names, or that ambmask rejects it), with
lint's hints when there are any, and answers KEEP or a corrected mask. Corrections are shown the same way
in the next round, until every task is kept or the rounds run out. Unlike blind.py's repairs, no task is
singled out by the gold: right and wrong answers are shown alike, so the loop can also break a right mask.
The first tries come from a results file (any decode arm); the loop itself calls a served model.
    .venv/bin/python masks/bench/verify.py <openrouter model id> <rounds> <out.jsonl> <results.jsonl> [runs] [--pdb]
--pdb also shows the PDB numbering of the selected residues (from the grounding map), for the three PDB systems.
--think turns the served model's reasoning on for the check (every other arm in this bench runs with it off).
"""
import http.client
import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
from blind import LANG, TASKS, parse, system_prompt, verdict  # noqa: E402
from lint import lint  # noqa: E402
from pick import card  # noqa: E402
from run_api import call  # noqa: E402
from tasks import from_ranges  # noqa: E402

ASK = ("For each task, if your mask selects exactly the atoms the task asks for, write KEEP under its header; "
       "otherwise write a corrected mask. Reply with only the answers, in exactly this form and nothing else:\n"
       "=== <id> ===\n<KEEP or mask>\n=== <next id> ===\n<KEEP or mask>")


def prompt(system, tasks, masks, pdb=False):
    body = ""
    for t in tasks:
        m = masks[t["id"]]
        hints = "".join(f"Hint: {h}\n" for h in lint(m or "", LANG[system].top)) if m else ""
        body += (f"TASK {t['id']}\nSelect {t['text']}.\nYour mask: {m or '(none)'}\n"
                 f"What it selects: {card(system, m, pdb) if m else 'nothing (no mask given)'}\n{hints}\n")
    return (f"{system_prompt(system, 'view')}Your answers to these tasks, each with what it selects in this "
            f"system (from ambmask):\n\n{body}{ASK}")


def ask(model, text, think=False):
    for attempt in range(4):
        try:
            body = call("openrouter", "chat/completions", {"model": model, "temperature": 0.7,
                                                           "max_tokens": 32000 if think else 16000,
                                                           "reasoning": {"enabled": think},
                                                           "messages": [{"role": "user", "content": text}]})
            return body["choices"][0]["message"].get("content") or "", None
        except (KeyError, IndexError, RuntimeError, OSError, http.client.HTTPException) as e:  # a long reply's stream can drop
            err = repr(e)[:300]
            time.sleep(20 * (attempt + 1))
    return "", err


def sheet(model, rounds, system, run, tasks, first, pdb=False, think=False):
    """One sheet through the loop: per task, the mask after each round (round 0 is the first try)."""
    masks = dict(first)
    history = {t["id"]: [first[t["id"]]] for t in tasks}
    open_ = list(tasks)
    log = []
    for rnd in range(1, rounds + 1):
        if not open_:
            break
        reply, err = ask(model, prompt(system, open_, masks, pdb), think)
        got = parse(reply)
        log.append({"round": rnd, "asked": [t["id"] for t in open_], "reply": reply, "error": err})
        still = []
        for t in open_:
            new = got.get(t["id"])
            if new and new.strip().upper() != "KEEP" and new != masks[t["id"]]:
                masks[t["id"]] = new
                still.append(t)  # a correction is shown again next round
        for t in tasks:
            history[t["id"]].append(masks[t["id"]])
        open_ = still
    return history, log


def main(model, rounds, out, src, runs=None, pdb=False, think=False):
    rows = [json.loads(line) for line in Path(src).read_text().splitlines()]
    if runs is not None:
        rows = [r for r in rows if r["run"] < runs]
    by = defaultdict(dict)
    for r in rows:
        by[(r["system"], r["run"])][r["id"]] = r["mask"]
    jobs = [(s, run, [t for t in TASKS if t["system"] == s], first) for (s, run), first in sorted(by.items())]
    with ThreadPoolExecutor(4) as ex:
        done = list(ex.map(lambda j: sheet(model, rounds, *j, pdb=pdb, think=think), jobs))
    outrows = []
    for (s, run, tasks, _), (history, log) in zip(jobs, done):
        for t in tasks:
            gold = from_ranges(t["gold"])
            h = history[t["id"]]
            outrows.append({"model": f"openrouter:{model}", "decode": "verify", "arm": "view", "source": Path(src).name, "card": "pdb" if pdb else "plain", "think": think,
                            "run": run, "system": s, "id": t["id"], "category": t["category"],
                            "difficulty": t["difficulty"], "split": t["split"], "mask": h[0],
                            "verdict": verdict(s, h[0], gold), "verify_mask": h[-1],
                            "verify_verdict": verdict(s, h[-1], gold), "masks": h,
                            "verdicts": [verdict(s, m, gold) for m in h], "log": log if t is tasks[0] else None})
    Path(out).write_text("".join(json.dumps(r) + "\n" for r in outrows))
    n = len(outrows)
    first = sum(r["verdict"] == "EXACT" for r in outrows)
    final = sum(r["verify_verdict"] == "EXACT" for r in outrows)
    fixed = sum(r["verdict"] != "EXACT" and r["verify_verdict"] == "EXACT" for r in outrows)
    broke = sum(r["verdict"] == "EXACT" and r["verify_verdict"] != "EXACT" for r in outrows)
    per_round = [sum(r["verdicts"][min(k, len(r["verdicts"]) - 1)] == "EXACT" for r in outrows) for k in range(rounds + 1)]
    silent = sum(r["verify_verdict"] in ("empty", "wrong atoms") for r in outrows)
    print(f"{Path(src).name}: first {first}/{n} -> after the loop {final}/{n}; right per round {per_round}; "
          f"fixed {fixed}, broke {broke}; silent failures after {silent}, rejected after "
          f"{sum(r['verify_verdict'] == 'rejected' for r in outrows)}; "
          f"errors {sum(bool(l['error']) for r in outrows if r['log'] for l in r['log'])}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a not in ("--pdb", "--think")]
    main(args[0], int(args[1]), args[2], args[3], int(args[4]) if len(args) > 4 else None, pdb="--pdb" in sys.argv,
         think="--think" in sys.argv)
