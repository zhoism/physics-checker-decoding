"""Gold verdict independent of md-param-check: does pmemd itself accept the file?

pmemd reads and validates the whole input (every namelist, the &wt END terminator,
restart coordinates and velocities) before it prints its "4.  RESULTS" header. A file
that reaches that header parsed cleanly, and the run is killed there: no dynamics.

The system is Single Particle's solvated protein, with a restart that carries
velocities so that restart stages (ntx=5) can be read too. Point PMEMD and
PMEMD_SYSTEM elsewhere to use another install or system.
"""
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

PMEMD = Path(os.environ.get("PMEMD", Path.home() / "Downloads/pmemd26/bin/pmemd"))
SYSTEM = Path(os.environ.get(
    "PMEMD_SYSTEM",
    Path.home() / "Downloads/Single Particle/Single Particle/phase3-explicit-solvent-md"
    / "_archive/submit-output-20260618",
))
# The header line itself, not the phrase: a title reading "4.  RESULTS" is echoed too.
READY = re.compile(r"^-+\n   4\.  RESULTS\s*\n-+$", re.M)


def _past_echo(log: str, text: str) -> str:
    """mdout after pmemd's echo of the input file (header, blank line, one line per input line)."""
    i = log.find("Here is the input file:")
    if i < 0:
        return ""
    return "\n".join(log[i:].split("\n")[2 + len(text.splitlines()):])


def _run(text: str, timeout: float) -> tuple[str, str]:
    """(mdout, stdout) of pmemd on text, killed at the RESULTS header."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "mdin").write_text(text)
        rst = SYSTEM / "heat-2.rst7"
        mdout, stdout = Path(d) / "mdout", Path(d) / "stdout"
        with stdout.open("w") as so:
            proc = subprocess.Popen(
                [str(PMEMD), "-O", "-i", "mdin", "-p", str(SYSTEM / "complex.parm7"), "-c", str(rst),
                 "-ref", str(rst), "-o", "mdout", "-r", "restrt", "-x", "mdcrd", "-inf", "mdinfo"],
                cwd=d, stdout=so, stderr=subprocess.STDOUT,
                # gfortran buffers mdout; a healthy run can sit on the header for minutes
                env={**os.environ, "GFORTRAN_UNBUFFERED_ALL": "y"},
            )
            deadline = time.time() + timeout
            while proc.poll() is None and time.time() < deadline:
                if mdout.exists() and READY.search(_past_echo(mdout.read_text(errors="replace"), text)):
                    break
                time.sleep(0.05)
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        log = mdout.read_text(errors="replace") if mdout.exists() else ""
        return log, stdout.read_text(errors="replace")


def accepts(text: str, timeout: float = 60.0) -> tuple[bool, str]:
    """(True, "") if pmemd gets through input processing, else (False, its last error line)."""
    log, out = _run(text, timeout)
    if READY.search(_past_echo(log, text)):
        return True, ""
    lines = [l.strip() for l in (log + "\n" + out).splitlines() if l.strip()]
    errors = [l for l in lines if "rror" in l or "ERROR" in l or "nvalid" in l]
    return False, (errors[0] if errors else lines[-1] if lines else "no output")[:200]


def parsed(text: str, timeout: float = 60.0) -> str | None:
    """What pmemd read from text: mdout from its CONTROL DATA header to RESULTS (values,
    masks, &wt changes), or None if it rejects the file. Two files that pmemd reads the
    same way give the same section, except for the seed line when ig = -1."""
    log = _past_echo(_run(text, timeout)[0], text)
    m = READY.search(log)
    start = log.find("2.  CONTROL  DATA  FOR  THE  RUN")
    return log[start:m.start()] if m and start >= 0 else None
