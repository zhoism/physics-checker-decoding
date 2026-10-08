"""masks/mask_tool.py runs the recipe the bench measured: replayed on the recorded replies of Gemma's 93% run,
it sends verify.py's prompts word for word and ends on that run's masks. Also: view.py's refactor rebuilds the
committed views, and a NetCDF restart is converted the way build.sh converted the membrane's. Skipped when the
bench systems are not built (masks/bench/build.sh)."""
import json
import os
import sys
from pathlib import Path

import pytest

MASKS = Path(__file__).resolve().parent.parent / "masks"
BENCH = MASKS / "bench"
SYSTEMS = ("bnbs", "tryp", "dna", "memb")
pytestmark = pytest.mark.skipif(not all((BENCH / "systems" / s / "sys.parm7").exists() for s in SYSTEMS),
                                reason="bench systems not built")
RUN = BENCH / "results" / "gemma-4-31b-it_verify_free_think.jsonl"  # the 93%: Gemma, reasoning on, 3 rounds


@pytest.fixture(scope="module")
def tool():
    sys.path.insert(0, str(MASKS))
    import mask_tool  # loads the bench systems, so only once they are built
    os.environ["PATH"] = f"{mask_tool.AMBER / 'bin'}{os.pathsep}{os.environ['PATH']}"  # cpptraj
    return mask_tool


@pytest.mark.parametrize("system", SYSTEMS)
def test_replay_of_the_93_percent_run(tool, monkeypatch, system):
    import blind
    import verify
    rows = [r for r in map(json.loads, RUN.read_text().splitlines()) if r["system"] == system and r["run"] == 0]
    log = next(r["log"] for r in rows if r["log"])
    tasks = [t for t in blind.TASKS if t["system"] == system]
    assert [t["id"] for t in tasks] == [r["id"] for r in rows]
    first = "".join(f"=== {r['id']} ===\n{r['masks'][0]}\n" for r in rows if r["masks"][0])
    calls = []

    def replay(model, text, think):
        k = len(calls)
        calls.append(think)
        if k == 0:
            return first, None
        asked = [t for t in tasks if t["id"] in log[k - 1]["asked"]]
        before = {r["id"]: r["masks"][k - 1] for r in rows}
        assert text == verify.prompt(system, asked, before), f"round {k}"
        return log[k - 1]["reply"], None

    monkeypatch.setattr(tool, "ask", replay)
    masks, status = tool.run("replay", 3, blind.system_prompt(system, "view"), blind.LANG[system].top, system, tasks)
    assert calls == [False] + [True] * len(log)  # reasoning off for the first try, on for the check
    assert masks == {r["id"]: r["verify_mask"] for r in rows}
    assert all(s.startswith(("kept", "corrected", "no answer")) for s in status.values())


@pytest.mark.parametrize("system", SYSTEMS)
def test_view_refactor_rebuilds_the_committed_views(tool, system):
    assert tool.view.view(system) == (BENCH / "views" / f"{system}.txt").read_text()


def test_netcdf_restart_is_converted(tool, tmp_path):
    memb = BENCH / "systems" / "memb"
    tool.setup(memb / "bilayer_only_lipid.top", memb / "bilayer_only_lipid.crd", tmp_path)
    assert not (tmp_path / "sys.rst7").is_symlink()
    for mask in (":PC@P31", "(:1<:6.0)&:WAT"):  # the distance selection reads the coordinates
        assert tool.card(str(tmp_path), mask) == tool.card("memb", mask), mask


def test_main_prints_each_request(tool, monkeypatch, capsys):
    replies = iter(["=== 1 ===\n:K+\n=== 2 ===\n@P31\n", "=== 1 ===\nKEEP\n=== 2 ===\n:PC@P31\n", "=== 2 ===\nKEEP\n"])
    monkeypatch.setattr(tool, "ask", lambda model, text, think: (next(replies), None))
    memb = BENCH / "systems" / "memb"
    monkeypatch.setattr(sys, "argv", ["mask_tool.py", str(memb / "sys.parm7"), str(memb / "sys.rst7"),
                                      "Select the potassium ions.", "the phosphorus atoms of the PC heads"])
    tool.main()
    out = capsys.readouterr().out
    assert "=== 1 === select the potassium ions\n:K+\nselects 6 atoms" in out and "kept in round 1" in out
    assert "=== 2 === select the phosphorus atoms of the PC heads\n:PC@P31\n" in out and "kept in round 2" in out
