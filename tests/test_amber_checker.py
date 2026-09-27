"""The md-param-check wrapper: rule coverage, prefix soundness, prefix completeness.

Soundness is the property the sampler depends on: prefix_ok must never be False
on a prefix of a file that passes, or SMC and AWRS would drop valid mass.
"""
import itertools
import os
import random
from pathlib import Path

import pytest

from checkers import amber
from checkers.amber_grammar import in_language, prefix_in_language

CORPUS_ROOT = Path(os.environ.get(
    "MDIN_CORPUS", Path.home() / "Downloads/Single Particle/Single Particle"))
CORPUS = sorted(CORPUS_ROOT.glob("**/*.in"))


def mdin(*pairs: str, wt: str = "") -> str:
    return "Test\n &cntrl\n" + "".join(f"  {p},\n" for p in pairs) + " /\n" + wt


# ---- every FAIL rule fires, and a clean file passes ---------------------------

GOOD = mdin("imin=0", "irest=1", "ntx=5", "nstlim=5000", "dt=0.002", "ntc=2", "ntf=2",
            "cut=9.0", "ntt=3", "gamma_ln=2.0", "temp0=300.0", "ig=-1")

FAIL_CASES = {
    "&cntrl missing": "Test\n &wt type='END', /\n",
    "dt > 2 fs cap": mdin("imin=0", "dt=0.004", "ntc=2", "ntf=2"),
    "dt > 1 fs cap (no SHAKE)": mdin("imin=0", "dt=0.0015"),
    "SHAKE incoherent": mdin("imin=0", "dt=0.001", "ntc=2", "ntf=1"),
    "dt too large without SHAKE": mdin("imin=0", "dt=0.002", "ntc=1", "ntf=1"),
    "irest/ntx incoherent": mdin("imin=0", "irest=1", "ntx=1"),
    "cut out of range": mdin("imin=1", "cut=15.0"),
    "dt not a finite number": mdin("imin=0", "dt=1e400"),
    "value2 not a finite number": mdin(
        "nmropt=1", "temp0=300.0",
        wt=" &wt type='TEMP0', istep1=0, istep2=100, value1=0.0, value2=1e400, /\n"),
    amber.DUP_RULE: mdin("imin=0", "dt=0.004", "dt=0.002", "ntc=2", "ntf=2"),
}


def test_clean_file_passes():
    assert in_language(GOOD)
    assert amber.failures(GOOD) == ()


@pytest.mark.parametrize("rule", FAIL_CASES)
def test_rule_fires(rule):
    text = FAIL_CASES[rule]
    assert any(r.startswith(rule) for r in amber.failures(text)), amber.failures(text)
    if in_language(text):  # outside the grammar, the grammar potential is what rejects it
        assert not amber.prefix_ok(text)


def test_duplicate_key_dies_at_the_key():
    head = "Test\n &cntrl\n  imin = 0, ntf = 2,\n  "
    assert amber.prefix_ok(head + "nt")          # could still become ntc, ntx, ...
    assert not amber.prefix_ok(head + "ntf")     # no other grammar key starts with ntf
    assert not amber.prefix_ok(head + "NTF =")
    assert amber.prefix_ok(head + "ntc =")


# ---- soundness on real files ---------------------------------------------------

def test_corpus_is_present():
    assert len(CORPUS) > 100, f"expected the Single Particle mdin corpus, found {len(CORPUS)} files"


def test_prefix_sound_on_every_passing_corpus_file():
    checked = 0
    for f in CORPUS:
        text = f.read_text()
        if not (in_language(text) and amber.passes(text)):
            continue
        dead = [i for i in range(len(text) + 1) if not amber.prefix_ok(text[:i])]
        assert not dead, f"{f}: prefix rejected at byte {dead[0]}: {text[:dead[0]]!r}"
        checked += 1
    assert checked > 100


def test_grammar_prefix_sound_on_corpus():
    for f in CORPUS:
        text = f.read_text()
        if in_language(text):
            assert all(prefix_in_language(text[:i]) for i in range(len(text) + 1)), f


def test_prefix_catches_every_failing_corpus_file():
    failing = [f.read_text() for f in CORPUS]
    failing = [t for t in failing if in_language(t) and not amber.passes(t)]
    assert failing
    for text in failing:
        assert not amber.prefix_ok(text)


# ---- completeness: prefix_ok against brute force over a small domain -----------

DOMAIN = {
    "imin": ["0", "1"],
    "dt": ["0.001", "0.0015", "0.002", "0.004"],
    "ntc": ["1", "2"],
    "ntf": ["1", "2"],
    "irest": ["0", "1"],
    "ntx": ["1", "5"],
    "cut": ["15.0"],
}


def _options(key):
    return [None] + DOMAIN[key]


def test_prefix_matches_brute_force():
    """For each committed set of pairs, prefix_ok must equal "some completion passes",
    where a completion gives each unset key any domain value or leaves it out."""
    keys = list(DOMAIN)
    mismatches = []
    for committed in itertools.product(*[_options(k) for k in keys]):
        pre = [f"{k}={v}" for k, v in zip(keys, committed) if v is not None]
        unset = [k for k, v in zip(keys, committed) if v is None]
        text = "Test\n &cntrl\n" + "".join(f"  {p},\n" for p in pre)
        truth = any(
            amber.passes(text + "".join(f"  {k}={v},\n" for k, v in zip(unset, fill) if v) + " /\n")
            for fill in itertools.product(*[_options(k) for k in unset])
        )
        if amber.prefix_ok(text) != truth:
            mismatches.append((pre, truth))
    assert not mismatches, mismatches[:5]


# ---- random grammar strings: soundness and monotonicity ------------------------

def _random_mdin(rng: random.Random) -> str:
    keys = rng.sample(["imin", "irest", "ntx", "dt", "ntc", "ntf", "cut", "ntt", "nmropt",
                       "temp0", "nstlim", "restraintmask", "gamma_ln"], k=rng.randint(0, 9))
    vals = {"imin": ["0", "1"], "irest": ["0", "1"], "ntx": ["1", "5", "7"],
            "dt": ["0.001", "0.002", "0.004", "2e-3", ".0005"], "ntc": ["1", "2", "3"],
            "ntf": ["1", "2"], "cut": ["8.0", "9", "12.0", "15.0"], "ntt": ["1", "3"],
            "nmropt": ["0", "1"], "temp0": ["300.0", "310"], "nstlim": ["5000", "5000000"],
            "restraintmask": ["'!:WAT & !@H='", '":1-20@CA"'], "gamma_ln": ["2.0", "0.5"]}
    sep = lambda: rng.choice([",\n  ", ", ", ",\n\n  ", " \n  ", ",  "])
    body = sep().join(f"{k}{rng.choice(['=', ' = '])}{rng.choice(vals[k])}" for k in keys)
    text = f"Random run\n &cntrl\n  {body}\n /\n"
    if rng.random() < 0.4:
        v2 = rng.choice(["300.0", "310.0", "1e400"])
        text += f" &wt\n  type='TEMP0', istep1=0, istep2=100,\n  value1=0.0, value2={v2},\n /\n"
        text += " &wt type='END', /\n"
    return text


def test_random_grammar_strings_sound_and_monotone():
    rng = random.Random(0)
    n_pass = 0
    for _ in range(300):
        text = _random_mdin(rng)
        assert in_language(text), text
        alive = [amber.prefix_ok(text[:i]) for i in range(len(text) + 1)]
        if amber.passes(text):
            n_pass += 1
            assert all(alive), (text, alive.index(False))
        first_dead = alive.index(False) if False in alive else len(alive)
        assert not any(alive[first_dead:]), f"prefix revived after dying: {text!r}"
    assert 30 < n_pass < 270  # both outcomes are exercised
