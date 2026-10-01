"""Blind-by-construction runs of Claude models on the mask tasks, plus one repair round.

Each call is a separate `claude -p` process with every tool off (--tools ""), no MCP servers,
no saved session, started in a fresh empty directory, with the tasks pasted into the prompt.
It cannot read a file, so it cannot see an answer. The raw JSON of every call is kept.

    .venv/bin/python blind.py <haiku|sonnet> <runs> <out-prefix>
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

AMBER = os.environ.get("AMBERHOME", "/opt/homebrew/Caskroom/miniforge/base/envs/prime-amber")
os.environ["PATH"] = f"{AMBER}/bin:" + os.environ["PATH"]
os.environ["AMBERHOME"] = AMBER
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from mask_grammar import MaskLanguage  # noqa: E402
from tasks import select  # noqa: E402

INSTRUCTIONS = ("You write AMBER atom-selection masks in the syntax that pmemd and ambmask accept. Reply with "
                "the mask only: no quotes, no code fences, no explanation.")
FORMAT = ("Treat each task independently. Reply with only the answers, in exactly this form and nothing else:\n"
          "=== <id> ===\n<mask>\n=== <next id> ===\n<mask>")
LANG = MaskLanguage(HERE / "system" / "complex.parm7")
RUNS = HERE / "runs"  # one empty dir per call, raw JSON kept; git-ignored


def ask(model: str, prompt: str, tag: str) -> str:
    d = tempfile.mkdtemp(dir=RUNS, prefix=f"{tag}.")
    p = subprocess.run(["claude", "-p", prompt, "--model", model, "--tools", "", "--strict-mcp-config",
                        "--no-session-persistence", "--output-format", "json"],
                       cwd=d, capture_output=True, text=True, timeout=600)
    (Path(d) / "response.json").write_text(p.stdout)
    r = json.loads(p.stdout)
    assert r["num_turns"] == 1 and not r["is_error"], (tag, r.get("num_turns"), r.get("is_error"))
    return r["result"]


def parse(text: str) -> dict:
    b = re.split(r"^=== (\S+) ===\s*\n", text, flags=re.M)[1:]
    return {i: x.strip().strip("`'\"").strip() for i, x in zip(b[::2], b[1::2])}


def verdict(mask, gold):
    atoms, err = select(mask)
    if atoms is None:
        return "rejected", err
    return ("EXACT" if set(atoms) == gold else "empty" if not atoms else "wrong atoms"), ""


def feedback(mask, v, err) -> str:
    """What a checking tool would tell the agent: ambmask's verdict, and where the grammar stops."""
    if v == "rejected":
        i = next((i for i in range(1, len(mask) + 1) if not LANG.accepts_prefix(mask[:i])), len(mask))
        return (f"ambmask rejects '{mask}' ({err}). It stops being valid AMBER mask syntax at character {i}: "
                f"'{mask[:i]}' <- here.")
    if v == "empty":
        return f"'{mask}' is valid syntax but selects no atoms in this system."
    atoms, _ = select(mask)
    return f"'{mask}' is valid and selects {len(atoms)} atoms; check that these are the atoms the task asks for."


if __name__ == "__main__":
    RUNS.mkdir(exist_ok=True)
    model, runs, prefix = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    system = (HERE / "system.txt").read_text()
    tasks = [json.loads(line) for line in (HERE / "tasks.jsonl").read_text().splitlines()]
    gold = {t["id"]: set(t["gold"]) for t in tasks}
    task_text = "".join(f"TASK {t['id']}\nSelect {t['text']}.\n\n" for t in tasks)
    rows = []
    for run in range(runs):
        first = parse(ask(model, f"{INSTRUCTIONS}\n\n{system}\n\n{task_text}{FORMAT}", f"{model}{run}"))
        assert set(first) == set(gold), sorted(set(gold) ^ set(first))
        firsts = {i: (m, *verdict(m, gold[i])) for i, m in first.items()}
        bad = {i: x for i, x in firsts.items() if x[1] != "EXACT"}
        fixed = {}
        if bad:  # one repair round, told only what a checking tool would say
            fb = "".join(f"TASK {i}\nSelect {next(t['text'] for t in tasks if t['id'] == i)}.\nYour mask: {m}\n"
                         f"Checker: {feedback(m, v, e)}\n\n" for i, (m, v, e) in bad.items())
            fixed = parse(ask(model, f"{INSTRUCTIONS}\n\n{system}\n\nYour masks for these tasks failed a check. "
                                     f"Write a corrected mask for each.\n\n{fb}{FORMAT}", f"{model}{run}r"))
        for i, (m, v, _) in firsts.items():
            m2 = fixed.get(i, m)
            rows.append({"model": model, "run": run, "id": i, "mask": m, "verdict": v,
                         "repaired_mask": m2, "repaired_verdict": verdict(m2, gold[i])[0] if i in bad else v})
    Path(prefix + ".jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    n = len(rows)
    print(f"{model}: first try {sum(r['verdict'] == 'EXACT' for r in rows)}/{n} exact, "
          f"after one repair {sum(r['repaired_verdict'] == 'EXACT' for r in rows)}/{n}")
    for r in rows:
        if r["verdict"] != "EXACT":
            print(f"   {r['id']:16s} {r['mask']!r:36s} {r['verdict']:9s} -> {r['repaired_mask']!r:36s} {r['repaired_verdict']}")
