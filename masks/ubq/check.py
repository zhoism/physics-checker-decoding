"""mask_tool.py on a system it was never tuned on: ubiquitin (build.sh), 12 requests, each with a reference mask
checked in ambmask (requests.json). A mask is right when it selects exactly the reference's atoms.
    .venv/bin/python masks/ubq/check.py <openrouter model id> <run>   # one run, logged to results/
    .venv/bin/python masks/ubq/check.py --score                        # the table, from the logged runs
"""
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import mask_tool as t  # noqa: E402
from tasks import select  # noqa: E402

REQUESTS = json.loads((HERE / "requests.json").read_text())


def right(d: str, mask: str | None, ref: str) -> bool:
    return bool(mask) and select(d, mask)[0] == select(d, ref)[0]


def run(model: str, label: str, d: Path) -> None:
    tasks = [{"id": str(i), "text": re.sub(r"(?i)^\s*select\s+", "", q).strip().rstrip(".")}
             for i, (q, _) in enumerate(REQUESTS, 1)]
    head = t.system_text(d, HERE / "leap.in", HERE / "1UBQ.pdb")
    log, real = [], t.ask

    def logged(m, text, think):  # every call's reply, so the run can be re-scored
        t0 = time.time()
        reply, err = real(m, text, think)
        log.append({"think": think, "reply": reply, "error": err, "s": round(time.time() - t0)})
        return reply, err

    t.ask = logged
    masks, status = t.run(model, 3, head, t.MaskLanguage(d / "sys.parm7").top, str(d), tasks)
    first = t.answers(log[0]["reply"])
    rows = [{"id": tk["id"], "request": q, "ref": ref, "first": first.get(tk["id"]), "final": masks[tk["id"]],
             "status": status[tk["id"]]} for (q, ref), tk in zip(REQUESTS, tasks)]
    (HERE / "results" / f"{model.split('/')[-1]}_{label}.json").write_text(json.dumps({"rows": rows, "log": log}, indent=1))


def score(d: Path) -> None:
    print("| run | first try | after the loop |\n|---|---|---|")
    tot = [0, 0, 0]
    for f in sorted((HERE / "results").glob("*.json")):
        rows = json.loads(f.read_text())["rows"]
        a = sum(right(str(d), r["first"], r["ref"]) for r in rows)
        b = sum(right(str(d), r["final"], r["ref"]) for r in rows)
        tot = [tot[0] + a, tot[1] + b, tot[2] + len(rows)]
        print(f"| {f.stem} | {a}/{len(rows)} | {b}/{len(rows)} |")
    print(f"| all | {tot[0]}/{tot[2]} | {tot[1]}/{tot[2]} |")


if __name__ == "__main__":
    os.environ["PATH"] = f"{t.AMBER / 'bin'}{os.pathsep}{os.environ['PATH']}"  # cpptraj
    with tempfile.TemporaryDirectory() as tmp:
        t.setup(HERE / "ubq.parm7", HERE / "ubq.rst7", Path(tmp))
        score(Path(tmp)) if sys.argv[1] == "--score" else run(sys.argv[1], sys.argv[2], Path(tmp))
