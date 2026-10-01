"""The Phase 1 AMBER task set (prompts/amber_phase1.jsonl) holds to its definition: each
reference is its tutorial's file made grammatical without changing what pmemd reads, and it
passes the checker. Gold is pmemd: it must read the reference and the verbatim source alike."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from checkers import amber, pmemd_gold
from checkers.amber_grammar import in_language
from scripts.normalize_mdin import normalize

ROOT = Path(__file__).resolve().parent.parent / "prompts"
TASKS = [json.loads(line) for line in (ROOT / "amber_phase1.jsonl").read_text().splitlines()]
IDS = [t["id"] for t in TASKS]
SEED = re.compile(r"^\s*ig\s*=.*$", re.M)  # ig = -1 draws a fresh seed on every run


def files(tid):
    d = ROOT / "amber_phase1"
    return (d / "source" / f"{tid}.in").read_text(), (d / f"{tid}.in").read_text()


def test_ids_are_unique_and_rows_complete():
    assert len(IDS) == len(set(IDS))
    for t in TASKS:
        assert all(t.get(k) for k in ("id", "text", "url", "tutorial", "license", "quote")), t["id"]


@pytest.mark.parametrize("tid", IDS)
def test_reference_is_the_normalized_source(tid):
    source, reference = files(tid)
    assert reference == normalize(source)


@pytest.mark.parametrize("tid", IDS)
def test_reference_is_in_the_grammar_and_passes_the_checker(tid):
    _, reference = files(tid)
    assert in_language(reference)
    assert amber.failures(reference) == ()


@pytest.fixture(scope="module")
def parses():
    if not pmemd_gold.PMEMD.exists():
        pytest.skip(f"no pmemd at {pmemd_gold.PMEMD}")
    texts = [t for tid in IDS for t in files(tid)]
    with ThreadPoolExecutor(8) as ex:
        out = [None if p is None else SEED.sub("", p) for p in ex.map(pmemd_gold.parsed, texts)]
    return dict(zip(IDS, zip(out[::2], out[1::2])))


@pytest.mark.parametrize("tid", IDS)
def test_pmemd_reads_reference_as_it_reads_the_source(parses, tid):
    source, reference = parses[tid]
    assert source is not None, "pmemd rejects the tutorial's own file"
    assert reference == source
