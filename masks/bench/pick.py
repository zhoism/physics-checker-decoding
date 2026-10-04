"""Pick from options: a check that shows what each candidate mask selects, and the model chooses.

For each task the candidates are the distinct first-try masks in some results files (the model's own
samples). Each is shown with what ambmask selects (atom count, residues, atom names) or that ambmask
rejects it: what a checking tool would show, never the gold. The model, given the view and the task,
answers with a letter or NONE. A NONE where no candidate is right turns a silent failure into a loud one.
    .venv/bin/python masks/bench/pick.py <openrouter model id> <out.jsonl> <results.jsonl>...
"""
import functools
import hashlib
import json
import random
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
from blind import TASKS, system_prompt, verdict  # noqa: E402
from run_api import call  # noqa: E402
from tasks import from_ranges, select  # noqa: E402

LETTERS = "ABCDEFGH"


@functools.cache
def atoms_of(system):
    """Per atom serial (1-based): (residue number, residue name, atom name); and atoms per residue."""
    flags, cur = {}, None
    for line in (HERE / "systems" / system / "sys.parm7").read_text().splitlines():
        if line.startswith("%FLAG"):
            cur = flags.setdefault(line.split()[1], [])
        elif not line.startswith("%") and cur is not None:
            cur.append(line)
    names = lambda flag: [s[i:i + 4].strip() for s in ["".join(flags[flag])] for i in range(0, len(s), 4)]
    atom_names, res_names = names("ATOM_NAME"), names("RESIDUE_LABEL")
    starts = [int(x) for x in "".join(flags["RESIDUE_POINTER"]).split()] + [len(atom_names) + 1]
    atoms = {}
    for r, (a, b) in enumerate(zip(starts, starts[1:]), 1):
        for serial in range(a, b):
            atoms[serial] = (r, res_names[r - 1], atom_names[serial - 1])
    return atoms, {r: b - a for r, (a, b) in enumerate(zip(starts, starts[1:]), 1)}


def ranges(nums):
    out, start = [], None
    for a, b in zip(nums, nums[1:] + [None]):
        start = a if start is None else start
        if b != a + 1:
            out.append(f"{start}" if start == a else f"{start}-{a}")
            start = None
    return ",".join(out)


def card(system, mask):
    sel, err = select(system, mask)
    if sel is None:
        return f"ambmask rejects it ({err[:80]})."
    if not sel:
        return "selects no atoms."
    atoms, size = atoms_of(system)
    by_res, rname = defaultdict(list), {}
    for s in sel:
        r, rn, an = atoms[s]
        by_res[r].append(an)
        rname[r] = rn
    res = sorted(by_res)
    if len(res) <= 6:
        where = "; ".join(f"{rname[r]} {r} ({'all' if len(by_res[r]) == size[r] else len(by_res[r])} of {size[r]} atoms)"
                          for r in res)
    else:
        kinds = Counter(rname[r] for r in res)
        full = sum(len(by_res[r]) == size[r] for r in res)
        where = (f"residues {ranges(res)[:120]}; names {', '.join(f'{k}x{v}' for k, v in kinds.most_common(6))}"
                 f"{' ...' if len(kinds) > 6 else ''}; {full} of {len(res)} residues whole")
    names = Counter(n for ns in by_res.values() for n in ns)
    atom_part = ", ".join(sorted(names)) if len(names) <= 12 else f"{len(names)} distinct names"
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"selects {plural(len(sel), 'atom')} in {plural(len(res), 'residue')}: {where}. Atom names: {atom_part}."


def prompt(task, cands):
    lines = "".join(f"{LETTERS[i]}. {m}\n   {card(task['system'], m)}\n" for i, m in enumerate(cands))
    return (f"{system_prompt(task['system'], 'view')}TASK {task['id']}\nSelect {task['text']}.\n\n"
            f"Candidate AMBER masks for this task, each with what it selects in this system (from ambmask):\n{lines}\n"
            f"Which candidate selects exactly the atoms the task asks for? Reply with only its letter, or NONE if "
            f"no candidate does.")


def judge(model, task, cands):
    """The model's reply and its letter. A free endpoint sometimes answers with an error body and no choice:
    retried, and after that recorded as no answer rather than ending the pass."""
    for attempt in range(4):
        try:
            body = call("openrouter", "chat/completions", {"model": model, "temperature": 0, "max_tokens": 200,
                                                           "reasoning": {"enabled": False},
                                                           "messages": [{"role": "user", "content": prompt(task, cands)}]})
            reply = body["choices"][0]["message"].get("content") or ""
            break
        except (KeyError, IndexError, RuntimeError) as e:
            reply = f"ERROR: {e!r}"[:300]
            time.sleep(20 * (attempt + 1))
    m = re.search(r"\b(NONE|[A-H])\b", reply.upper()) if not reply.startswith("ERROR") else None
    return reply, (m.group(1) if m else None)


def main(model, out, files):
    pools, seen = defaultdict(list), defaultdict(set)
    for f in files:
        for r in map(json.loads, Path(f).read_text().splitlines()):
            m = r["mask"]
            if not m or m in pools[r["id"]]:
                continue
            sel = select(r["system"], m)[0]
            key = tuple(sel) if sel else m  # masks that select the same atoms are one candidate
            if key not in seen[r["id"]]:
                seen[r["id"]].add(key)
                pools[r["id"]].append(m)
    jobs = []
    for t in TASKS:
        cands = pools[t["id"]][:len(LETTERS)]
        random.Random(int(hashlib.sha256(t["id"].encode()).hexdigest()[:8], 16)).shuffle(cands)  # no position cue
        jobs.append((t, cands))
    with ThreadPoolExecutor(4) as ex:
        replies = list(ex.map(lambda j: judge(model, *j) if j[1] else ("", None), jobs))
    rows = []
    for (t, cands), (reply, choice) in zip(jobs, replies):
        gold = from_ranges(t["gold"])
        mask = cands[LETTERS.index(choice)] if choice and choice != "NONE" and LETTERS.index(choice) < len(cands) else None
        rows.append({"model": f"openrouter:{model}", "decode": "pick", "arm": "view", "run": 0, "system": t["system"],
                     "id": t["id"], "category": t["category"], "difficulty": t["difficulty"], "split": t["split"],
                     "mask": mask, "verdict": verdict(t["system"], mask, gold), "choice": choice, "reply": reply,
                     "pool": cands, "pool_verdicts": [verdict(t["system"], m, gold) for m in cands]})
    Path(out).write_text("".join(json.dumps(r) + "\n" for r in rows))
    has = [r for r in rows if "EXACT" in r["pool_verdicts"]]
    print(f"picked exact {sum(r['verdict'] == 'EXACT' for r in rows)}/{len(rows)}; a right candidate existed for "
          f"{len(has)}, picked it in {sum(r['verdict'] == 'EXACT' for r in has)}; no right candidate for "
          f"{len(rows) - len(has)}, said NONE in {sum(r['choice'] == 'NONE' for r in rows if r not in has)}; "
          f"NONE overall {sum(r['choice'] == 'NONE' for r in rows)}, unparsed {sum(r['choice'] is None for r in rows)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
