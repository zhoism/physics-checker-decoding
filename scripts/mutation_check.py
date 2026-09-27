"""Watch the checker tests go red: turn each mdin FAIL rule of check_amber.py into a
PASS in a scratch copy, run the suite against the copy, and report which rules
the suite would not notice losing. The real file is never touched.

    uv run python scripts/mutation_check.py      # exit 0 = every mutant killed
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from checkers.amber import CHECK_AMBER  # noqa: E402

src = CHECK_AMBER.read_text()
# mdin rules only: check_submit_script's rules are about shell scripts, not decoding
lo, hi = src.index("def check_amber_in"), src.index("def check_submit_script")
sites = [m.start() for m in re.finditer(r'Finding\("FAIL"', src) if lo < m.start() < hi]
survivors = []
for i, at in enumerate(sites):
    rule = src[at:at + 80].split("\n")[0]
    with tempfile.TemporaryDirectory() as d:
        mutant = Path(d) / "check_amber.py"
        mutant.write_text(src[:at] + 'Finding("PASS"' + src[at + len('Finding("FAIL"'):])
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
                            "tests/test_amber_checker.py"],
                           env={**os.environ, "MD_PARAM_CHECK": str(mutant)},
                           capture_output=True, text=True)
    killed = r.returncode != 0
    print(f"{'killed  ' if killed else 'SURVIVED'} {rule}")
    if not killed:
        survivors.append(rule)
print(f"{len(sites) - len(survivors)}/{len(sites)} mutants killed")
sys.exit(1 if survivors else 0)
