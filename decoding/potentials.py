"""The checker and the grammar as genlm-control potentials over bytes.

Coerce either to an LLM with `.coerce(llm, f=b"".join)`.
"""
import functools
from collections import Counter

from genlm.control import Potential

from checkers import amber
from checkers.amber_grammar import in_language, prefix_in_language

NEG_INF = float("-inf")
CALLS = Counter()  # checker evaluations during decoding; run_arms resets it per arm


def _text(context) -> str:
    return bytes(context).decode("utf-8", errors="replace")


class AmberChecker(Potential):
    """md-param-check as a boolean potential: 0 if the file can still pass, -inf if not.

    terminal_only=True is the complete-only mode: prefixes are never judged, so as
    an SMC critic it only reweights finished samples.
    """

    def __init__(self, terminal_only: bool = False):
        super().__init__(vocabulary=list(range(256)))
        self.terminal_only = terminal_only

    async def complete(self, context):
        CALLS["checker"] += 1
        return 0.0 if amber.passes(_text(context)) else NEG_INF

    async def prefix(self, context):
        if self.terminal_only:
            return 0.0
        CALLS["checker"] += 1
        return 0.0 if amber.prefix_ok(_text(context)) else NEG_INF

    def is_terminal_only(self) -> bool:
        return self.terminal_only


class MdinGrammar(Potential):
    """The mdin grammar as a boolean potential, by partial regex matching.

    Not genlm's BoolFSA: on this grammar its first prefix call runs a backward
    solve over the automaton that took 74 s (295M semiring products) on an M3 Pro.
    """

    def __init__(self):
        super().__init__(vocabulary=list(range(256)))

    async def complete(self, context):
        return 0.0 if _in(bytes(context)) else NEG_INF

    async def prefix(self, context):
        return 0.0 if _prefix_in(bytes(context)) else NEG_INF


@functools.lru_cache(maxsize=65536)
def _in(b: bytes) -> bool:
    return b.isascii() and in_language(b.decode())


@functools.lru_cache(maxsize=65536)
def _prefix_in(b: bytes) -> bool:
    return b.isascii() and prefix_in_language(b.decode())
