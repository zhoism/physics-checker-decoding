"""Rewrite a tutorial's mdin into the grammar of checkers/amber_grammar.py without changing
what pmemd reads. tests/test_amber_tasks.py holds every reference to that: pmemd must parse
the reference and its verbatim source to the same CONTROL DATA.

    uv run python -m scripts.normalize_mdin source.in > reference.in

Only surface changes: '!' comments, blank lines and lines outside the namelists go,
'&end' or '$end' becomes '/', each namelist starts on its own line, the title keeps only the
characters the grammar allows, Fortran 'd' exponents become 'e', a key's case is made
uniform, and a comma gets a space after it.
"""
import re
import sys

from checkers.amber_grammar import CNTRL_KEYS, WT_KEYS

_STR = r"'[^'\n]*'|\"[^\"\n]*\""
_COMMENT = re.compile(rf"({_STR})|!.*")
_KEY = re.compile(rf"({_STR})|\b([A-Za-z]\w*)(?=\s*=)")
_D_EXP = re.compile(rf"({_STR})|(?<![\w.])(-?(?:\d+\.?\d*|\.\d+))[dD]([-+]?\d+)\b")
_COMMA = re.compile(rf"({_STR})|,(?=\S)")
_KEYS = {k.lower() for k in CNTRL_KEYS + WT_KEYS}


def _outside_strings(pattern, repl, text):
    return pattern.sub(lambda m: m.group(1) or repl(m), text)


def normalize(text: str) -> str:
    lines = text.splitlines()
    title = []
    if lines and not lines[0].lstrip().startswith("&"):
        t = re.sub(r"[^A-Za-z0-9 _.,:;()+\-]", " ", lines.pop(0))
        title = [re.sub(r" +", " ", t).strip()[:80]]
    while lines and not lines[0].lstrip().startswith("&"):  # pmemd skips to the namelist
        lines.pop(0)
    body = _outside_strings(_COMMENT, lambda m: "", "\n".join(lines))
    body = re.sub(r"[&$]end\b", "/", body, flags=re.I)
    body = re.sub(r"/[ \t]*(&\w+)", r"/\n \1", body)  # '/ &wt' -> a new line per namelist
    body = _outside_strings(_D_EXP, lambda m: f"{m.group(2)}e{m.group(3)}", body)
    body = _outside_strings(
        _KEY, lambda m: m.group(2).lower() if m.group(2).lower() in _KEYS else m.group(2), body)
    body = _outside_strings(_COMMA, lambda m: ", ", body)
    kept = [line.rstrip() for line in body.splitlines() if line.strip()]
    while kept and not re.search(r"/\s*$", kept[-1]):  # an 'END' left after the last namelist
        kept.pop()
    return "\n".join(title + kept) + "\n"


if __name__ == "__main__":
    sys.stdout.write(normalize(open(sys.argv[1]).read()))
