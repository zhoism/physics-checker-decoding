"""md-param-check's AMBER validator as a prefix-checkable function.

The validator is imported from its own repo, not copied: its rules are the
claim's scope, and a fork would drift. Set MD_PARAM_CHECK to point elsewhere.

Two additions, both needed for decoding and neither changing a rule:

- A duplicate-key ban. The validator reads a namelist into a dict, so a later
  `dt=0.002` silently overrides an earlier `dt=0.004`. A prefix check is only
  sound if a committed violation cannot be undone, so a repeated key fails.
- `prefix_ok`: can some completion of this text still pass? It is answered
  with a small family of witness completions run through the validator
  itself. The family is complete for the current rule set on the grammar in
  checkers/amber_grammar.py, and tests/test_amber_checker.py checks that
  against brute force, the real corpus, and random grammar strings.
"""
from __future__ import annotations

import functools
import importlib.util
import itertools
import os
import re
import sys
from pathlib import Path

from checkers.amber_grammar import CNTRL_KEYS, WT_KEYS

DEFAULT_PATH = (
    Path.home() / "Downloads/Single Particle/Single Particle"
    / ".claude/skills/md-param-check/checks/check_amber.py"
)
CHECK_AMBER = Path(os.environ.get("MD_PARAM_CHECK", DEFAULT_PATH))


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("check_amber", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # @dataclass resolves its module through sys.modules
    spec.loader.exec_module(mod)
    return mod


ca = _load(CHECK_AMBER)

DUP_RULE = "duplicate key"


class _Text:
    """The validator reads `path.read_text()` and `path.name`; this serves both from memory."""

    name = "<text>"

    def __init__(self, text: str):
        self._text = text

    def read_text(self) -> str:
        return self._text


def duplicate_keys(text: str) -> list[str]:
    """Keys repeated inside one namelist block, found with the validator's own regexes."""
    dups = []
    for m in ca.NAMELIST_RE.finditer(text):
        keys = [k.lower() for k, _ in ca.KV_RE.findall(ca.strip_comments(m.group(2)))]
        dups += sorted({f"&{m.group(1).lower()} {k}" for k in keys if keys.count(k) > 1})
    return dups


@functools.lru_cache(maxsize=65536)
def failures(text: str) -> tuple[str, ...]:
    """FAIL-level rules the text violates. WARNs pass, as they do at the validator's exit code."""
    rules = [f.rule for f in ca.check_amber_in(_Text(text)).findings if f.level == "FAIL"]
    rules += [f"{DUP_RULE}: {d}" for d in duplicate_keys(text)]
    return tuple(rules)


def passes(text: str) -> bool:
    return not failures(text)


# ---- prefix ------------------------------------------------------------------

# A pair whose value may still grow ("dt = 0.00" can become 0.002 or 0.004e-1;
# "dt =" can take its value on the next line), or a trailing token not yet ended
# by whitespace, ',' or '/'. \Z, not $: $ also matches before a final newline.
_TAIL_PAIR = re.compile(r"\w+\s*=\s*[^\s,/]*\Z")
_TAIL_TOKEN = re.compile(r"[^\s,/]*\Z")
_OPEN_STR = re.compile(r"\w+\s*=\s*[\"'][^\"'\n]*\Z")
_STR = re.compile(r"'[^'\n]*'|\"[^\"\n]*\"")


def committed(text: str) -> str:
    """The longest prefix whose tokens can no longer change meaning."""
    m = _TAIL_PAIR.search(text) or _TAIL_TOKEN.search(text)
    p = text[: m.start()]
    m = _OPEN_STR.search(p)  # a string value still open: the whole pair is
    return p[: m.start()] if m else p


# Values that can only help. imin=1 switches off every dynamics rule; ntc=ntf=2
# gives the largest dt cap; ntx=5 makes any restart legal. Everything else is
# best left unset, since a FAIL rule only fires on a value that is present.
_RESCUERS = {"imin": "1", "ntc": "2", "ntf": "2", "ntx": "5"}
_BLOCK = re.compile(r"&(\w+)")


def _open_block(p: str) -> tuple[str, str] | None:
    """(name, body so far) of the namelist block p ends inside, if any.
    Quoted strings are blanked first: a mask like '!:WAT & !@H=' holds an '&'."""
    s = _STR.sub("''", p)
    starts = list(_BLOCK.finditer(s))
    if not starts or "/" in s[starts[-1].end():]:
        return None
    return starts[-1].group(1).lower(), s[starts[-1].end():]


def witnesses(p: str) -> list[str]:
    if not re.search(r"&cntrl\b", _STR.sub("''", p), re.I):
        return ["\n &cntrl\n  imin=1,\n /\n"]
    block = _open_block(p)
    if block is None:
        return [""]
    name, body = block
    keys = {k.lower() for k, _ in ca.KV_RE.findall(body)}
    if name == "cntrl":
        unset = [k for k in _RESCUERS if k not in keys]
        out = []
        for chosen in itertools.product([False, True], repeat=len(unset)):
            pairs = "".join(f"  {k}={_RESCUERS[k]},\n" for k, c in zip(unset, chosen) if c)
            out.append("\n" + pairs + " /\n")
        return sorted(out, key=lambda w: "imin" not in w)  # the usual rescuer first
    # an open &wt: a type other than TEMP0 skips its value check
    return ["\n /\n"] + ([] if "type" in keys else ["\n  type='END',\n /\n"])


@functools.lru_cache(maxsize=65536)
def _alive(p: str) -> bool:
    # each witness closes the open block, so failures() also sees its duplicate keys
    return any(passes(p + w) for w in witnesses(p))


def _key_is_duplicate(text: str, p: str) -> bool:
    """In the grammar every key is followed by '=', so the key being written is a
    duplicate as soon as every grammar key it could still become is already set.
    Waiting for its value instead leaves a token-level mask a dead end to walk into."""
    block = _open_block(p)
    m = re.match(r"\s*(\w+)(\s*=)?", text[len(p):])
    if block is None or m is None:
        return False
    name, body = block
    word = m.group(1).lower()
    keys = CNTRL_KEYS if name == "cntrl" else WT_KEYS
    candidates = {word} if m.group(2) else {k for k in keys if k.startswith(word)}
    return bool(candidates) and candidates <= {k.lower() for k, _ in ca.KV_RE.findall(body)}


def prefix_ok(text: str) -> bool:
    """False only if no completion of `text` inside the grammar can pass."""
    p = committed(text)
    return not _key_is_duplicate(text, p) and _alive(p)
