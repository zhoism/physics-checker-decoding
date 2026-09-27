"""Gold verdict independent of md-param-check: does pmemd itself accept the file?

pmemd reads and validates the whole input (every namelist, the &wt END terminator,
restart coordinates and velocities) before it prints its "4.  RESULTS" header. A file
that reaches that header parsed cleanly, and the run is killed there: no dynamics.

The system is Single Particle's solvated protein, with a restart that carries
velocities so that restart stages (ntx=5) can be read too. Point PMEMD and
PMEMD_SYSTEM elsewhere to use another install or system.
"""
import os
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
READY = "4.  RESULTS"


def accepts(text: str, timeout: float = 60.0) -> tuple[bool, str]:
    """(True, "") if pmemd gets through input processing, else (False, its last error line)."""
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "mdin").write_text(text)
        rst = SYSTEM / "heat-2.rst7"
        proc = subprocess.Popen(
            [str(PMEMD), "-O", "-i", "mdin", "-p", str(SYSTEM / "complex.parm7"), "-c", str(rst),
             "-ref", str(rst), "-o", "mdout", "-r", "restrt", "-x", "mdcrd", "-inf", "mdinfo"],
            cwd=d, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            # gfortran buffers mdout; a healthy run can sit on the header for minutes
            env={**os.environ, "GFORTRAN_UNBUFFERED_ALL": "y"},
        )
        mdout = Path(d) / "mdout"
        deadline = time.time() + timeout
        while proc.poll() is None and time.time() < deadline:
            if mdout.exists() and READY in mdout.read_text(errors="replace"):
                break
            time.sleep(0.05)
        if proc.poll() is None:
            proc.kill()
        out = proc.communicate()[0]
        log = mdout.read_text(errors="replace") if mdout.exists() else ""
    if READY in log:
        return True, ""
    lines = [l.strip() for l in (log + "\n" + out).splitlines() if l.strip()]
    errors = [l for l in lines if "rror" in l or "ERROR" in l or "nvalid" in l]
    return False, (errors[0] if errors else lines[-1] if lines else "no output")[:200]
