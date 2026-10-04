"""Mask grammar v2. v1 (masks/pilot/mask_grammar.py) is kept unchanged for comparison.

v2 makes five changes, each for a failure seen on the bench or in random masks fed to ambmask
(AmberTools 24.8):
- A mask is at most 79 characters: ambmask rejects 80 and more. The v1 sheet run looped '& :H=' until it
  ran out of tokens. A prefix is accepted only if it can still be finished within the limit.
- A ':' or '@' list is all numbers or all names. pmemd reads a mixed list (':1,TRP') as names only and
  drops the 1.
- '@%' starts a list of atom types ('@%CT,HC', which ambmask accepts and v1 rejected). '%' inside a
  name list ('@CA,%CT') is rejected by ambmask, but v1 accepted it.
- A type is written in full, and only if ambmask's type parser reads it: it rejects '@%C=' and any type
  with '+' or '-' ('@%Na+', '@%Cl-'), though it reads '@%C*'.
- The '=' wildcard follows at most 3 characters: ambmask reads 4 ('@HD2=') and rejects 5 ('@HD21=').
Kept from v1: no atom list after ')' (ambmask reads '(:7,137)@SG' as every SG in the system), residue
and atom names from the topology only, '=' the only wildcard, nesting depth 2.
"""
import functools
import re
import sys
from pathlib import Path

import regex

sys.path.append(str(Path(__file__).resolve().parent.parent / "pilot"))  # last: pilot/tasks.py must not shadow bench's
from mask_grammar import read_prmtop  # noqa: E402

MAX_LEN = 79  # ambmask rejects 80 characters and more ("pop_evalstack"); pmemd 26 reads 1024
DEPTH = 2


def _names(vocab: set[str]) -> str:
    """Exact names, or 1 to 3 leading characters of one and '='. Longest first for the regex."""
    prefixes = {n[:i] for n in vocab for i in range(1, min(len(n), 3) + 1)}
    alts = sorted((re.escape(n) for n in vocab), key=len, reverse=True)
    alts += sorted((re.escape(p) + "=" for p in prefixes), key=len, reverse=True)
    return "(?:" + "|".join(alts) + ")"


def readable_types(top: dict) -> set[str]:
    return {t for t in top["types"] if re.fullmatch(r"[A-Za-z0-9*]+", t)}


def build(top: dict, depth: int = DEPTH) -> str:
    NUM = r"[0-9]{1,6}"
    RANGE = rf"{NUM}(?:-{NUM})?"
    nums = rf"{RANGE}(?:,{RANGE})*"

    def names(vocab):
        n = _names(vocab)
        return rf"{n}(?:,{n})*"

    typ = "(?:" + "|".join(sorted(map(re.escape, readable_types(top)), key=len, reverse=True)) + ")"
    RES = rf":(?:\*|{nums}|{names(top['residues'])})"
    ATOM = rf"@(?:\*|{nums}|{names(top['atoms'])}|%{typ}(?:,{typ})*)"
    SEL = rf"(?:{RES}(?:{ATOM})?|{ATOM})"
    DIST = rf"(?:[<>][:@][0-9]{{1,3}}(?:\.[0-9]{{1,3}})?)"
    OP = r" ?[&|] ?"
    expr = None
    for _ in range(depth + 1):  # nesting depth, so the language stays regular
        primary = rf"(?:{SEL}{DIST}?" + (rf"|\({expr}\)" if expr else "") + ")"
        unary = rf"(?:! ?)?{primary}"
        expr = rf"{unary}(?:{OP}{unary})*"
    return expr


class MaskLanguage2:
    """accepts / accepts_prefix / top, the interface of v1's MaskLanguage, with the length cap."""

    def __init__(self, prmtop, max_len: int = MAX_LEN):
        self.top = read_prmtop(prmtop)
        self.full = regex.compile(build(self.top))
        self.max_len = max_len
        # A valid prefix is finished by one of these middles, then up to DEPTH ')': '' or '=' (a partial
        # residue or atom name; names have at most 4 characters, so a partial one has at most 3), '1' or
        # '*' (after a sigil, ',', '-' or '.'), ':1' (after an operator, '(' or '<'), '&:1' (after a
        # trailing space), a name's first letter and '=' (after ',' in a name list), or the rest of a type
        # (in a type list). slack bounds the shortest finisher, so shorter prefixes skip the search.
        # tests/test_mask_grammar2.py checks both claims on random masks.
        types = readable_types(self.top)
        rest = {t[i:] for t in types for i in range(len(t))}
        mids = {"", "=", "1", "*", ":1", "&:1"} | {n[0] + "=" for n in self.top["residues"] | self.top["atoms"]} | rest
        self.finishers = sorted({m + ")" * k for m in mids for k in range(DEPTH + 1)}, key=len)
        type_prefixes = {t[:i] for t in types for i in range(len(t))}
        longest_rest = max(min(len(t) - len(p) for t in types if t.startswith(p)) for p in type_prefixes)
        self.slack = max(3, longest_rest) + DEPTH

    @functools.lru_cache(maxsize=65536)
    def accepts(self, text: str) -> bool:
        return len(text) <= self.max_len and self.full.fullmatch(text) is not None

    @functools.lru_cache(maxsize=65536)
    def accepts_prefix(self, text: str) -> bool:
        if len(text) > self.max_len or self.full.fullmatch(text, partial=True) is None:
            return False
        if len(text) + self.slack <= self.max_len:
            return True
        return any(len(text) + len(f) <= self.max_len and self.full.fullmatch(text + f) for f in self.finishers)
