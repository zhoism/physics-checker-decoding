#!/usr/bin/env bash
# Ubiquitin (1UBQ), protein only, ff14SB in implicit solvent: a system mask_tool.py was never tuned on.
# Writes 1UBQ.pdb, prot.pdb, ubq.parm7, ubq.rst7 here (git-ignored). Needs tleap (the prime-amber env).
set -euo pipefail
cd "$(dirname "$0")"
curl -sf -o 1UBQ.pdb https://files.rcsb.org/download/1UBQ.pdb
{ grep '^ATOM' 1UBQ.pdb; echo TER; echo END; } > prot.pdb
tleap -f leap.in > leap.log
