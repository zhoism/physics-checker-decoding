#!/usr/bin/env bash
# Pack what arms.ipynb needs into masks/bench/colab/bundle.tar.gz (git-ignored): the bench code, the views,
# the tasks, both grammars and the built systems (bash masks/bench/build.sh first if they are missing).
# MANIFEST records the commit and a sha256 per file, so a run can be matched to the repo afterwards.
#   bash masks/bench/colab/bundle.sh
set -euo pipefail
cd "$(dirname "$0")/../../.."
files=(masks/bench/{blind,decode,lint,mask_grammar2,qwen,tasks,think}.py masks/bench/{tasks.jsonl,SHA256SUMS}
       masks/bench/views/*.txt masks/pilot/mask_grammar.py masks/bench/systems/{bnbs,tryp,dna,memb}/sys.{parm7,rst7})
for f in "${files[@]}"; do
  [ -f "$f" ] || { echo "missing $f (systems: bash masks/bench/build.sh)" >&2; exit 1; }
done
dirty=$(git status --porcelain -- "${files[@]}")  # the systems are git-ignored, so never listed
{ echo "commit $(git rev-parse --short HEAD)${dirty:+ with uncommitted changes}"; shasum -a 256 "${files[@]}"; } \
  > masks/bench/colab/MANIFEST
COPYFILE_DISABLE=1 tar -czf masks/bench/colab/bundle.tar.gz "${files[@]}" masks/bench/colab/MANIFEST  # no macOS ._ files
ls -lh masks/bench/colab/bundle.tar.gz
