"""Mask grammar v2 (masks/bench/mask_grammar2.py): it admits every bench reference, refuses the traps it
was written for, never strands a decoder (every accepted prefix can be finished within the length cap),
and every mask it generates is one ambmask reads. Needs the built systems (git-ignored); skips without."""
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parent.parent / "masks" / "bench"
sys.path.insert(0, str(BENCH))
import tasks as bench  # noqa: E402
from mask_grammar2 import MaskLanguage2  # noqa: E402

ROWS = [json.loads(line) for line in (BENCH / "tasks.jsonl").read_text().splitlines()]
SYSTEMS = sorted({r["system"] for r in ROWS})


def lang(system):
    parm = BENCH / "systems" / system / "sys.parm7"
    if not parm.exists():
        pytest.skip(f"{system} not built: bash masks/bench/build.sh {system}")
    return MaskLanguage2(parm)


def walk(L, rng, stop=0.08):
    """A random mask, one character at a time, each drawn from those the grammar allows next."""
    alphabet = sorted(set(":@%*=,-.<>!&|() 0123456789") | {c for n in L.top["residues"] | L.top["atoms"] |
                                                          L.top["types"] for c in n})
    text = ""
    while True:
        nxt = [c for c in alphabet if L.accepts_prefix(text + c)]
        if L.accepts(text) and (not nxt or rng.random() < stop):
            return text
        assert nxt, f"stranded at {text!r}"
        text += rng.choice(nxt)


@pytest.mark.parametrize("system", SYSTEMS)
def test_every_reference_is_in_the_grammar(system):
    L = lang(system)
    assert [r["id"] for r in ROWS if r["system"] == system and not L.accepts(r["reference"])] == []


def test_the_traps():
    L = lang("tryp")
    longest = ":" + "1," * 38 + "11"
    assert len(longest) == L.max_len
    for bad in (":1,PRO", "@1-20,CA", "@CA,%CT", "(:7,137)@SG", "@H*", "@%C=", "@%Na+", "@HD21=", "protein and name CA",
                longest + "1"):
        assert not L.accepts(bad) and not L.accepts_prefix(bad), bad
    for good in ("@%CT,HC", "@%C*", "@HD2=", ":7,137@SG", ":1|:PRO", ":1-3@1-5", "(:CA<:3.0)&:1-223", longest):
        assert L.accepts(good), good


@pytest.mark.parametrize("system", SYSTEMS)
def test_no_prefix_strands_a_decoder(system):
    """walk() asserts at every step that an accepted prefix is complete or can be extended; low stop odds
    drive many walks to the cap. Short prefixes skip the finisher search, so check the bound it relies on."""
    L, rng = lang(system), random.Random(0)
    masks = [walk(L, rng, stop) for stop in (0.0, 0.02, 0.1) for _ in range(8)]
    assert max(len(m) for m in masks) >= L.max_len - 2
    for m in masks:
        for p in {m[:i] for i in range(min(len(m), L.max_len - L.slack) + 1)}:
            assert any(L.accepts(p + f) for f in L.finishers if len(f) <= L.slack), p


@pytest.mark.parametrize("system", SYSTEMS)
def test_ambmask_reads_what_the_grammar_writes(system):
    if not (bench.AMBER / "bin" / "ambmask").exists():
        pytest.skip(f"no ambmask under {bench.AMBER}")
    L, rng = lang(system), random.Random(1)
    masks = [walk(L, rng, stop) for stop in (0.0, 0.05, 0.2) for _ in range(3)]  # ambmask is slow on wide cutoffs
    with ThreadPoolExecutor(8) as ex:
        got = list(ex.map(lambda m: bench._ambmask(system, m), masks))
    assert [(m, err) for m, (atoms, err) in zip(masks, got) if atoms is None] == []
