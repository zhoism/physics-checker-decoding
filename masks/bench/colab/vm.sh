#!/usr/bin/env bash
# decode.py on a Google Cloud GPU VM (a Deep Learning VM image, PyTorch preinstalled): arms.ipynb's steps
# without the notebook. Unpacks the bundle, installs the pinned packages and AmberTools 24.8 for ambmask,
# checks that every gold reproduces, then runs the arms into ~/results. Copy bundle.tar.gz and this file
# to the VM's home first (gcloud compute scp).
#   bash vm.sh <hf model> <nf4|fp16|bf16|fp32> <runs> <tasks per system|all> <decode:layout[:runs]>...
set -euo pipefail
cd ~
mkdir -p maskbench results && tar -xzf bundle.tar.gz -C maskbench
[ -d venv ] || python3 -m venv --system-site-packages venv  # keeps the image's CUDA build of torch
venv/bin/pip install -q genlm-control==0.4.0 genlm-backend==0.3.0 genlm-bytes==0.2.0 genlm-grammar==0.2.0 \
    transformers==5.17.0 accelerate==1.15.0 regex==2026.9.10 bitsandbytes
if [ ! -x amber/bin/ambmask ]; then
  curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj bin/micromamba
  bin/micromamba create -y -q -p ~/amber -c conda-forge "ambertools=24.8=cuda_None_nompi_py311*_101" \
    > amber.log 2>&1 || { tail -20 amber.log; exit 1; }
fi
export AMBERHOME=~/amber HF_HUB_DISABLE_XET=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
venv/bin/python - <<'EOF'
import json, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
bench = Path.home() / "maskbench" / "masks" / "bench"
sys.path.insert(0, str(bench))
import tasks
sums = dict(reversed(line.split()) for line in (bench / "SHA256SUMS").read_text().splitlines())
assert all(tasks.digest(s) == h for s, h in sums.items()), "a system differs from the one the gold was computed on"
rows = [json.loads(line) for line in (bench / "tasks.jsonl").read_text().splitlines()]
with ThreadPoolExecutor(8) as ex:
    got = list(ex.map(lambda r: tasks.select(r["system"], r["reference"])[0], rows))
bad = [r["id"] for r, a in zip(rows, got) if a is None or set(a) != tasks.from_ranges(r["gold"])]
assert not bad, bad
print(f"{len(rows)}/{len(rows)} golds reproduce with this ambmask")
EOF
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
venv/bin/python maskbench/masks/bench/decode.py "$1" "$2" "$3" ~/results "$4" "${@:5}"
