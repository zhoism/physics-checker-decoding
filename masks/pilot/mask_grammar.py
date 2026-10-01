"""A system-aware grammar for AMBER atom masks, compiled from a topology (prmtop).

Stricter than ambmask on purpose: only well-formed masks, and only names that exist in the
topology (a name may end in the '=' wildcard if some name in the topology starts with it).
Rules checked against ambmask (AmberTools) on 2026-10-01:
  :res-list[@atom-list] | @atom-list ; lists of numbers, ranges and names, ',' separated
  '=' is the only wildcard ('*' only alone: ':*', '@*'); '?' and '@/' are rejected
  '%' selects atom types; '<' / '>' then ':' or '@' then a distance is a distance selection
  '!' negates, '&' and '|' combine, parentheses group; spaces around operators are allowed
Not allowed although ambmask accepts them: ':1--5', ':1,', a bare ':' or '@', and an atom
list after ')' (ambmask reads '(:1)@CA' as every CA in the system).
"""
import functools
import re
from pathlib import Path

import regex


def read_prmtop(path) -> dict:
    """Residue names, atom names and atom types from a prmtop, without ParmEd."""
    flags, cur = {}, None
    for line in Path(path).read_text().splitlines():
        if line.startswith("%FLAG"):
            cur = line.split()[1]
            flags[cur] = []
        elif line.startswith("%") or cur is None:
            continue
        else:
            flags[cur].append(line)

    def names(flag):
        s = "".join(flags[flag])
        return {s[i:i + 4].strip() for i in range(0, len(s), 4)} - {""}

    return {"residues": names("RESIDUE_LABEL"), "atoms": names("ATOM_NAME"), "types": names("AMBER_ATOM_TYPE")}


def _names(vocab: set[str]) -> str:
    """Exact names, or a prefix of one followed by the '=' wildcard. Longest first for the regex."""
    prefixes = {n[:i] for n in vocab for i in range(1, len(n) + 1)}
    alts = sorted((re.escape(n) for n in vocab), key=len, reverse=True)
    alts += sorted((re.escape(p) + "=" for p in prefixes), key=len, reverse=True)
    return "(?:" + "|".join(alts) + ")"


def build(top: dict, depth: int = 2) -> str:
    NUM = r"[0-9]{1,6}"
    RANGE = rf"{NUM}(?:-{NUM})?"
    res_item = rf"(?:{RANGE}|{_names(top['residues'])})"
    atom_item = rf"(?:{RANGE}|{_names(top['atoms'])}|%{_names(top['types'])})"
    RES = rf":(?:\*|{res_item}(?:,{res_item})*)"
    ATOM = rf"@(?:\*|{atom_item}(?:,{atom_item})*)"
    SEL = rf"(?:{RES}(?:{ATOM})?|{ATOM})"
    DIST = rf"(?:[<>][:@][0-9]{{1,3}}(?:\.[0-9]{{1,3}})?)"
    OP = r" ?[&|] ?"
    expr = None
    for _ in range(depth + 1):  # nesting depth, so the language stays regular
        primary = rf"(?:{SEL}{DIST}?" + (rf"|\({expr}\)" if expr else "") + ")"
        unary = rf"(?:! ?)?{primary}"
        expr = rf"{unary}(?:{OP}{unary})*"
    return expr


class MaskLanguage:
    def __init__(self, prmtop):
        self.top = read_prmtop(prmtop)
        self.full = regex.compile(build(self.top))

    @functools.lru_cache(maxsize=65536)
    def accepts(self, text: str) -> bool:
        return self.full.fullmatch(text) is not None

    @functools.lru_cache(maxsize=65536)
    def accepts_prefix(self, text: str) -> bool:
        return self.full.fullmatch(text, partial=True) is not None
