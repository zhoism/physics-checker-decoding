"""The gold check agrees with pmemd on files whose fate is known (see
docs/research_notes/md_param_check_failure_modes.md for the probes behind these)."""
import pytest

from checkers import pmemd_gold

pytestmark = pytest.mark.skipif(not pmemd_gold.PMEMD.exists(), reason=f"no pmemd at {pmemd_gold.PMEMD}")

RESTART = ("Restart\n &cntrl\n  imin=0, irest=1, ntx=5, nstlim=10, dt=0.002, ntc=2, ntf=2,\n"
           "  cut=9.0, ntb=1, ntt=3, gamma_ln=2.0, temp0=300.0, ig=-1,\n /\n")


def test_accepts_a_legal_restart():
    assert pmemd_gold.accepts(RESTART) == (True, "")


@pytest.mark.parametrize("change, error", [
    ("ig=-1, ntsx=1", "Cannot match namelist object name ntsx"),
    ("ig=-1, nmropt=1", 'No "wt" namelist with TYPE=END found'),
    ("ig=-1, ntr=2", "ntr must be set to 0 or 1"),
])
def test_rejects_what_the_checker_passes(change, error):
    ok, msg = pmemd_gold.accepts(RESTART.replace("ig=-1", change))
    assert not ok and error in msg, msg
