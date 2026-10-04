"""The mask bench (masks/bench/tasks.jsonl) holds to its definition: complete rows, a held-out
split in every category, and a gold that ambmask reproduces from each reference mask on the
system it was computed on (SHA256SUMS). Skips the ambmask checks when a system is not built."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parent.parent / "masks" / "bench"
sys.path.insert(0, str(BENCH))
import tasks as bench  # noqa: E402

ROWS = [json.loads(line) for line in (BENCH / "tasks.jsonl").read_text().splitlines()]
SUMS = dict(reversed(line.split()) for line in (BENCH / "SHA256SUMS").read_text().splitlines())


def test_rows_complete_and_ids_unique():
    assert len({r["id"] for r in ROWS}) == len(ROWS)
    for r in ROWS:
        assert r["category"] in bench.CATEGORIES and r["difficulty"] in (1, 2, 3), r["id"]
        assert r["split"] in ("dev", "test") and r["text"] and r["reference"], r["id"]
        assert r["n"] == len(bench.from_ranges(r["gold"])) > 0, r["id"]
        assert r["system"] in SUMS and (BENCH / "views" / f"{r['system']}.txt").exists(), r["id"]


def test_every_category_has_held_out_tasks():
    for cat in {r["category"] for r in ROWS}:
        splits = [r["split"] for r in ROWS if r["category"] == cat]
        assert "test" in splits, cat


def test_rows_match_the_task_definitions():
    defined = {f"{s}-{t[0]}": (t[1], t[2], t[3], t[4]) for s, ts in bench.TASKS.items() for t in ts}
    assert {r["id"]: (r["category"], r["difficulty"], r["text"], r["reference"]) for r in ROWS} == defined


@pytest.mark.parametrize("system", sorted(SUMS))
def test_gold_reproduces(system):
    if not (bench.AMBER / "bin" / "ambmask").exists():
        pytest.skip(f"no ambmask under {bench.AMBER}")
    if not (BENCH / "systems" / system / "sys.parm7").exists():
        pytest.skip(f"{system} not built: bash masks/bench/build.sh {system}")
    assert bench.digest(system) == SUMS[system], f"{system} differs from the system the gold was computed on"
    rows = [r for r in ROWS if r["system"] == system]
    with ThreadPoolExecutor(8) as ex:
        got = list(ex.map(lambda r: bench.select(system, r["reference"]), rows))
    for r, (atoms, err) in zip(rows, got):
        assert atoms is not None, (r["id"], err)
        assert set(atoms) == bench.from_ranges(r["gold"]), r["id"]
