"""The mdin surface language the decoder is held to (the grammar potential).

An optional title line (pmemd 26 finds the namelist without one), one &cntrl
block, then zero or more &wt blocks. Keys come from a fixed list (pmemd aborts on
an unknown one), each with its pmemd type: integer, real, or a one-line string.
It leaves out the things that make the validator's parser
unsound as a prefix checker (docs/research_notes/md_param_check_failure_modes.md):
'!' comments, a '/' or newline inside a string, &end terminators, and a second
&cntrl.
"""
import regex

# Typed, because pmemd is: an integer variable rejects "2.01" ("Cannot match namelist
# object name .01"), and without types a mask steered a model to ntc = 2.01, which the
# checker's ntc == 2 tests then ignore.
CNTRL_INT = """
imin irest ntx ntxo nstlim nscm nrespa ntc ntf ntb ntp barostat mcbarint ntt ig
vrand nsnb ntpr ntwx ntwr ntwe ntwv ntwf ntave ioutfm iwrap ntwprt idecomp ntr
ibelly nmropt maxcyc ncyc ntmin igb gbsa jfastw ifqnt icfe ifsc
""".split()
CNTRL_FLOAT = """
dt tol pres0 comp taup temp0 tempi tautp gamma_ln vlimit cut fswitch restraint_wt
dx0 drms saltcon rgbmax surften extdiel intdiel dielc clambda
""".split()
CNTRL_STR = "restraintmask bellymask timask1 timask2 scmask1 scmask2".split()
WT_INT, WT_FLOAT, WT_STR = "istep1 istep2 iinc imult".split(), ["value1", "value2"], ["type"]
CNTRL_KEYS = CNTRL_INT + CNTRL_FLOAT + CNTRL_STR
WT_KEYS = WT_INT + WT_FLOAT + WT_STR

TITLE = r"[A-Za-z0-9 _.,:;()+\-]{0,80}"  # pmemd reads an 80-column title
INT = r"-?[0-9]{1,9}"  # pmemd overflows at 2**31
NUM = r"-?([0-9]{1,10}\.?[0-9]{0,10}|\.[0-9]{1,10})([eE][\-+]?[0-9]{1,3})?"  # bounded: a mask
# otherwise lets a model loop on "2.0E+000000..." forever
STR = r"('[^'\"\n/]*'|\"[^'\"\n/]*\")"
WT_TYPE = r"('[A-Z][A-Z0-9]*'|\"[A-Z][A-Z0-9]*\")"  # pmemd: "Invalid TYPE flag" for 'temp0'
WS = r"[ \t]*"
GAP = r"[ \t\n]+"


def _block(name: str, ints: list[str], floats: list[str], strs: list[str], string=STR) -> str:
    def alt(keys):  # Fortran names are case-blind; models often shout
        return "|".join(keys + [k.upper() for k in keys])

    pair = (rf"(({alt(ints)}){WS}={WS}{INT}|({alt(floats)}){WS}={WS}{NUM}"
            rf"|({alt(strs)}){WS}={WS}{string}),?")
    return rf"{WS}&{name}({GAP}{pair})*[ \t\n]*/{WS}\n[ \t\n]*"


MDIN_REGEX = (rf"({TITLE}\n)?{_block('cntrl', CNTRL_INT, CNTRL_FLOAT, CNTRL_STR)}"
              rf"({_block('wt', WT_INT, WT_FLOAT, WT_STR, WT_TYPE)}){{0,4}}")  # a ramp or two plus END;
# unbounded, a masked model loops on &wt blocks until the token budget runs out

_FULL = regex.compile(MDIN_REGEX)


def in_language(text: str) -> bool:
    return _FULL.fullmatch(text) is not None


def prefix_in_language(text: str) -> bool:
    """True if some continuation of text is in the language."""
    return _FULL.fullmatch(text, partial=True) is not None
