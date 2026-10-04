"""Blind-by-construction runs of Claude models on the mask bench, then two separate repair rounds.

Each call is its own `claude -p` with every tool off (--tools ""), no MCP servers, no saved session,
started in a fresh empty directory, with the system view and all of that system's tasks pasted in.
It cannot read a file, so it cannot see an answer. The raw JSON of every call is kept in runs/.

    .venv/bin/python masks/bench/blind.py <haiku|sonnet|openrouter:<model id>> <runs> <view|map> <out.jsonl>
    .venv/bin/python masks/bench/blind.py <haiku|sonnet> canary

Arms: 'view' shows views/<system>.txt; 'map' adds views/<system>.map.txt (grounding: PDB residue
numbers mapped to topology numbers). Every first-try failure then gets two independent repairs:
'checker' is the pilot's feedback (ambmask's verdict, where the grammar stops, the atom count) and
'lint' is that plus lint.py's targeted hints. Neither sees the gold.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE), str(HERE.parent / "pilot")]
from lint import VERSION as LINT_VERSION, lint  # noqa: E402
from mask_grammar import MaskLanguage  # noqa: E402
from tasks import from_ranges, select  # noqa: E402

INSTRUCTIONS = ("You write AMBER atom-selection masks in the syntax that pmemd and ambmask accept. For each task, "
                "write the mask that selects exactly the atoms described, in the system below.")
FORMAT = ("Treat each task independently. Reply with only the answers, in exactly this form and nothing else:\n"
          "=== <id> ===\n<mask>\n=== <next id> ===\n<mask>")
RUNS = HERE / "runs"  # one empty dir per call, raw JSON kept; git-ignored
TASKS = [json.loads(line) for line in (HERE / "tasks.jsonl").read_text().splitlines()]
LANG = {s: MaskLanguage(HERE / "systems" / s / "sys.parm7") for s in {t["system"] for t in TASKS}}


REUSE_SINCE = float(os.environ.get("BLIND_REUSE_SINCE", "inf"))  # epoch: replay calls saved after this


def ask(model: str, prompt: str, tag: str) -> str:
    """One blind call. 'openrouter:<model id>' is one chat completion through run_api.py (an API call has no
    tools either), at the GPU runs' temperature 0.7. A saved response with the same tag from this launch
    (BLIND_REUSE_SINCE) is replayed: a tag fixes the prompt, because repairs are built from the replayed
    first tries."""
    tag = re.sub(r"[/:]", "_", tag)  # an OpenRouter id has a '/'
    for d in sorted(RUNS.glob(f"{tag}.*"), key=lambda d: d.stat().st_mtime, reverse=True):
        f = d / "response.json"
        if d.name.count(".") == tag.count(".") + 1 and d.stat().st_mtime >= REUSE_SINCE and f.exists():
            r = json.loads(f.read_text() or "{}")
            if r.get("result") and not r.get("is_error"):
                return r["result"]
    d = tempfile.mkdtemp(dir=RUNS, prefix=f"{tag}.")
    if model.startswith("openrouter:"):
        sys.path.append(str(HERE.parents[1]))
        from run_api import call
        body = call("openrouter", "chat/completions", {"model": model.split(":", 1)[1], "temperature": 0.7,
                                                       "max_tokens": 16000,
                                                       # answer directly: decoding constrains the answer, and a
                                                       # thinking model spent all 16k tokens thinking on a sheet
                                                       "reasoning": {"enabled": False},
                                                       "messages": [{"role": "user", "content": prompt}]})
        r = {"result": body["choices"][0]["message"].get("content") or "", "is_error": False, "api": body}
        (Path(d) / "response.json").write_text(json.dumps(r))
        return r["result"]
    p = subprocess.run(["claude", "-p", prompt, "--model", model, "--tools", "", "--strict-mcp-config",
                        "--no-session-persistence", "--output-format", "json"],
                       cwd=d, capture_output=True, text=True, timeout=1800)
    (Path(d) / "response.json").write_text(p.stdout)
    r = json.loads(p.stdout)
    # num_turns can be 2 with no tool at all (seen: a long first turn); with --tools "" no turn can read a file.
    assert not r["is_error"] and not r.get("permission_denials"), (tag, r.get("num_turns"), r.get("is_error"))
    return r["result"]


def clean(x: str) -> str:
    """Strip code fences and a pair of enclosing quotes, but never a trailing prime (O4', H5'')."""
    x = x.strip().strip("`").strip()
    return x[1:-1].strip() if len(x) > 1 and x[0] in "'\"" and x[-1] == x[0] else x


def parse(text: str) -> dict:
    b = re.split(r"^=== (\S+) ===\s*\n", text, flags=re.M)[1:]
    return {i: clean(x) for i, x in zip(b[::2], b[1::2])}


def verdict(system: str, mask: str | None, gold: set) -> str:
    if not mask:
        return "missing"
    atoms, _ = select(system, mask)
    return "rejected" if atoms is None else "EXACT" if set(atoms) == gold else "empty" if not atoms else "wrong atoms"


def checker(system: str, mask: str, v: str) -> str:
    """The pilot's feedback: what a checking tool says without knowing the answer."""
    if v == "rejected":
        lang = LANG[system]
        i = next((i for i in range(1, len(mask) + 1) if not lang.accepts_prefix(mask[:i])), len(mask))
        return (f"ambmask rejects '{mask}' ({select(system, mask)[1]}). It stops being valid AMBER mask syntax at "
                f"character {i}: '{mask[:i]}' <- here.")
    if v == "empty":
        return f"'{mask}' is valid syntax but selects no atoms in this system."
    if v == "missing":
        return "No mask was given."
    return (f"'{mask}' is valid and selects {len(select(system, mask)[0])} atoms; check that these are the atoms "
            f"the task asks for.")


def system_prompt(system: str, arm: str) -> str:
    view = (HERE / "views" / f"{system}.txt").read_text()
    grounding = HERE / "views" / f"{system}.map.txt"
    if arm == "map" and grounding.exists():
        view += "\n" + grounding.read_text()
    return f"{INSTRUCTIONS}\n\nSYSTEM\n{view}\n"


def one_system(model: str, arm: str, run: int, system: str) -> list[dict]:
    tasks = [t for t in TASKS if t["system"] == system]
    head = system_prompt(system, arm)
    body = "".join(f"TASK {t['id']}\nSelect {t['text']}.\n\n" for t in tasks)
    first = parse(ask(model, f"{head}TASKS\n{body}{FORMAT}", f"{model}.{arm}{run}.{system}"))
    rows = []
    for t in tasks:
        m = first.get(t["id"])
        rows.append({"model": model, "arm": arm, "run": run, "system": system, "id": t["id"],
                     "category": t["category"], "difficulty": t["difficulty"], "split": t["split"],
                     "mask": m, "verdict": verdict(system, m, from_ranges(t["gold"]))})
    bad = [r for r in rows if r["verdict"] != "EXACT"]
    for kind in ("checker", "lint"):
        fixed = {}
        if bad:
            fb = ""
            for r in bad:
                t = next(t for t in tasks if t["id"] == r["id"])
                hints = lint(r["mask"] or "", LANG[system].top) if kind == "lint" else []
                r[f"{kind}_hints"] = hints
                fb += (f"TASK {r['id']}\nSelect {t['text']}.\nYour mask: {r['mask']}\nChecker: "
                       f"{checker(system, r['mask'] or '', r['verdict'])}\n"
                       + "".join(f"Hint: {h}\n" for h in hints) + "\n")
            fixed = parse(ask(model, f"{head}Your masks for these tasks failed a check. Write a corrected mask "
                                     f"for each.\n\n{fb}{FORMAT}",
                                f"{model}.{arm}{run}.{system}.{kind}{LINT_VERSION if kind == 'lint' else ''}"))
        for r in rows:
            if r in bad:
                r[f"{kind}_mask"] = fixed.get(r["id"], r["mask"])  # left out of the reply: kept unchanged
                t = next(t for t in tasks if t["id"] == r["id"])
                r[f"{kind}_verdict"] = verdict(system, r[f"{kind}_mask"], from_ranges(t["gold"]))
            else:
                r[f"{kind}_mask"], r[f"{kind}_verdict"] = r["mask"], r["verdict"]
    return rows


def canary(model: str) -> None:
    """The setup must not be able to read an answer: ask it to, and check the reply has no reference mask."""
    target = HERE / "tasks.jsonl"
    reply = ask(model, f"Use your tools to read the file {target} and reply with the 'reference' field of its "
                       f"first line, verbatim.", f"{model}.canary")
    leaked = TASKS[0]["reference"] in reply
    print(f"canary {model}: {'LEAKED' if leaked else 'blind'}; reply: {reply[:300]!r}")
    assert not leaked


if __name__ == "__main__":
    RUNS.mkdir(exist_ok=True)
    model = sys.argv[1]
    if sys.argv[2] == "canary":
        canary(model)
        sys.exit()
    runs, arm, out = int(sys.argv[2]), sys.argv[3], sys.argv[4]
    jobs = [(run, s) for run in range(runs) for s in sorted(LANG)]
    rows = []
    with ThreadPoolExecutor(4) as ex:
        for rs in ex.map(lambda j: one_system(model, arm, *j), jobs):  # saved as each system finishes
            rows += rs
            Path(out).write_text("".join(json.dumps(r) + "\n" for r in rows))
    n = len(rows)
    for k in ("verdict", "checker_verdict", "lint_verdict"):
        print(f"{model} {arm} {k:16s} {sum(r[k] == 'EXACT' for r in rows)}/{n} exact")
