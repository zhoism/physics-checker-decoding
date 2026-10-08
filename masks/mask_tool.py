"""AMBER masks for any system, by the recipe that took an open model furthest on the bench: a first try, then the
selection loop with reasoning on (Gemma-4-31B: 46% -> 93% of 375, docs/research_notes/masks_bench.md).

    .venv/bin/python masks/mask_tool.py <prmtop> <inpcrd> "<request>" ["<request>" ...]
                                        [--leap leap.in] [--pdb x.pdb] [--model google/gemma-4-31b-it] [--rounds 3]

1. The model is shown the system as the bench showed it (view.py: cpptraj's listings of the topology, and the
   leap input and the PDB's residues when given) with every request, and answers each with a mask, reasoning off.
2. Each mask goes through ambmask on these files. The model sees what it selects (pick.card) and lint's hints,
   and answers KEEP or a corrected mask, reasoning on. A correction is shown again, for --rounds rounds at most.
Prints each request's mask, what it selects, and whether the model kept it. A kept mask can still be wrong: the
loop left 7% of the bench silently wrong. The first try is blind.py's prompt and the check is verify.py's, word
for word (tests/test_mask_tool.py replays the 93% run through it). Runs in this repo with the bench systems built
(masks/bench/build.sh), since the bench modules load them at import; calls OpenRouter with the key in .env;
ambmask and cpptraj come from AMBERHOME or the prime-amber env.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path[:0] = [str(HERE / "bench"), str(HERE / "pilot"), str(HERE.parent)]
import view  # noqa: E402
from blind import FORMAT, INSTRUCTIONS, parse  # noqa: E402
from lint import lint  # noqa: E402
from mask_grammar import MaskLanguage  # noqa: E402
from pick import card  # noqa: E402
from tasks import AMBER  # noqa: E402
from verify import ASK, ask  # noqa: E402


def setup(prmtop: Path, inpcrd: Path, d: Path) -> None:
    """d gets sys.parm7 and sys.rst7, the names the bench helpers read. ambmask cannot read a NetCDF restart
    (tleap writes one when packmol-memgen drives it), so one is converted with cpptraj."""
    (d / "sys.parm7").symlink_to(prmtop.resolve())
    with inpcrd.open("rb") as f:
        netcdf = f.read(4) in (b"CDF\x01", b"CDF\x02", b"\x89HDF")
    if netcdf:
        subprocess.run(["cpptraj", "-p", "sys.parm7"], input=f"trajin {inpcrd.resolve()}\ntrajout sys.rst7 restart\nrun\n",
                       cwd=d, capture_output=True, text=True, check=True)
    else:
        (d / "sys.rst7").symlink_to(inpcrd.resolve())


def system_text(d: Path, leap: Path | None, pdb: Path | None) -> str:
    """What the model is shown, as blind.system_prompt shows a bench system."""
    parts = [f"The topology sys.parm7 and coordinates sys.rst7 {f'were built from {pdb.name}' if pdb else 'are the system'}."]
    if leap:
        parts.append(f"$ cat {leap.name}\n{leap.read_text().rstrip()}")
    parts += view.topology(str(d))
    if pdb:
        parts.append(view.pdb_residues(pdb))
    return f"{INSTRUCTIONS}\n\nSYSTEM\n" + "\n\n".join(parts) + "\n\n"


def answers(reply: str) -> dict:
    """blind.parse, also reading '=== TASK 1 ===': with numbered tasks Gemma copies the TASK line into every header
    (with the bench's named ids it never did)."""
    return parse(re.sub(r"(?m)^=== TASK ", "=== ", reply))


def first_prompt(head: str, tasks: list[dict]) -> str:
    """blind.one_system's prompt."""
    body = "".join(f"TASK {t['id']}\nSelect {t['text']}.\n\n" for t in tasks)
    return f"{head}TASKS\n{body}{FORMAT}"


def check_prompt(head: str, top: dict, system: str, tasks: list[dict], masks: dict) -> str:
    """verify.prompt, for a system that is not on the bench."""
    body = ""
    for t in tasks:
        m = masks[t["id"]]
        hints = "".join(f"Hint: {h}\n" for h in lint(m or "", top)) if m else ""
        body += (f"TASK {t['id']}\nSelect {t['text']}.\nYour mask: {m or '(none)'}\n"
                 f"What it selects: {card(system, m) if m else 'nothing (no mask given)'}\n{hints}\n")
    return (f"{head}Your answers to these tasks, each with what it selects in this "
            f"system (from ambmask):\n\n{body}{ASK}")


def run(model: str, rounds: int, head: str, top: dict, system: str, tasks: list[dict]) -> tuple[dict, dict]:
    """verify.sheet's loop, from a first try made here: each task's final mask and what became of it."""
    reply, err = ask(model, first_prompt(head, tasks), False)
    if err:
        raise SystemExit(f"the first try failed: {err}")
    got = answers(reply)
    masks = {t["id"]: got.get(t["id"]) for t in tasks}
    status = {t["id"]: "not checked" for t in tasks}
    open_ = list(tasks)
    for rnd in range(1, rounds + 1):
        if not open_:
            break
        reply, err = ask(model, check_prompt(head, top, system, open_, masks), True)
        if err:
            print(f"round {rnd} failed, the masks stand as they were: {err}", file=sys.stderr)
            break
        got = answers(reply)
        still = []
        for t in open_:
            new = got.get(t["id"])
            if not new:
                status[t["id"]] = f"no answer in round {rnd}"
            elif new.strip().upper() == "KEEP" or new == masks[t["id"]]:
                status[t["id"]] = f"kept in round {rnd}"
            else:
                masks[t["id"]] = new
                status[t["id"]] = f"corrected in round {rnd}" + ("" if rnd < rounds else ", not checked again")
                still.append(t)  # a correction is shown again next round
        open_ = still
    return masks, status


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("prmtop", type=Path)
    p.add_argument("inpcrd", type=Path)
    p.add_argument("requests", nargs="+", help="what to select, in plain English")
    p.add_argument("--leap", type=Path, help="the leap input the system was built with, shown to the model")
    p.add_argument("--pdb", type=Path, help="the PDB file it was built from; its residues are shown to the model")
    p.add_argument("--model", default="google/gemma-4-31b-it", help="an OpenRouter model id")
    p.add_argument("--rounds", type=int, default=3)
    a = p.parse_args()
    os.environ["PATH"] = f"{AMBER / 'bin'}{os.pathsep}{os.environ['PATH']}"  # cpptraj
    # "Select the CA atoms." and "the CA atoms" both become the bench's "Select the CA atoms."
    tasks = [{"id": str(i), "text": re.sub(r"(?i)^\s*select\s+", "", r).strip().rstrip(".")}
             for i, r in enumerate(a.requests, 1)]
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        setup(a.prmtop, a.inpcrd, d)
        head = system_text(d, a.leap, a.pdb)
        # The bench helpers take a system id and read systems/<id>; an absolute path takes its place
        masks, status = run(a.model, a.rounds, head, MaskLanguage(d / "sys.parm7").top, str(d), tasks)
        for t in tasks:
            m = masks[t["id"]]
            print(f"=== {t['id']} === select {t['text']}\n{m or '(no mask)'}\n"
                  f"{card(str(d), m) if m else 'no mask given'}\n{status[t['id']]}\n")


if __name__ == "__main__":
    main()
