"""decode.py on a Modal GPU: arms.ipynb's steps as a Modal function. The image holds the pinned packages,
AmberTools 24.8 (for ambmask) and the bundle; the function checks every gold, then runs the arms. Rows go
to the Volume 'mask-bench-results' as they finish, so a rerun resumes.
    bash masks/bench/colab/bundle.sh
    modal run masks/bench/colab/modal_app.py --model google/gemma-4-31B-it --quant bf16 --runs 1 --limit 2 \
        --arms free:sheet,grammar2:sheet       # MASK_BENCH_GPU=H100:2 for another GPU (default A100-80GB)
    Unattended (the call survives the laptop): modal deploy masks/bench/colab/modal_app.py, then
    modal.Function.from_name("mask-bench", "arms_fn").with_options(gpu="H200").spawn(model, quant, runs, "2,all", arms)
    modal volume get mask-bench-results <model>-<quant>_<decode>_<layout>.jsonl masks/bench/results/
"""
import os
import subprocess
from pathlib import Path

import modal

BUNDLE = Path(__file__).parent / "bundle.tar.gz"
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl", "bzip2")
    .pip_install("torch==2.9.1", "genlm-control==0.4.0", "genlm-backend==0.3.0", "genlm-bytes==0.2.0",
                 "genlm-grammar==0.2.0", "transformers==5.17.0", "accelerate==1.15.0", "regex==2026.9.10",
                 "bitsandbytes", "huggingface_hub")
    .run_commands("curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C /usr/local bin/micromamba",
                  'micromamba create -y -q -p /opt/amber -c conda-forge "ambertools=24.8=cuda_None_nompi_py311*_101"')
    .pip_install("kernels==0.16.2")  # the FP8 matmul kernels transformers fetches for an fp8 checkpoint
    .env({"AMBERHOME": "/opt/amber", "HF_HUB_DISABLE_XET": "1",
          "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"})
    .add_local_file(BUNDLE, "/root/bundle.tar.gz")
)
app = modal.App("mask-bench", image=image)
results = modal.Volume.from_name("mask-bench-results", create_if_missing=True)

GOLD_CHECK = """
import json, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/root/maskbench/masks/bench")
import tasks
from pathlib import Path
bench = Path("/root/maskbench/masks/bench")
sums = dict(reversed(line.split()) for line in (bench / "SHA256SUMS").read_text().splitlines())
assert all(tasks.digest(s) == h for s, h in sums.items()), "a system differs from the one the gold was computed on"
rows = [json.loads(line) for line in (bench / "tasks.jsonl").read_text().splitlines()]
with ThreadPoolExecutor(8) as ex:
    got = list(ex.map(lambda r: tasks.select(r["system"], r["reference"])[0], rows))
bad = [r["id"] for r, a in zip(rows, got) if a is None or set(a) != tasks.from_ranges(r["gold"])]
assert not bad, bad
print(f"{len(rows)}/{len(rows)} golds reproduce with this ambmask", flush=True)
"""


def arms_fn(model, quant, runs, limit, arms, script="decode.py"):  # script: decode.py or think.py
    os.makedirs("/root/maskbench", exist_ok=True)
    subprocess.run(["tar", "-xzf", "/root/bundle.tar.gz", "-C", "/root/maskbench"], check=True)
    print(open("/root/maskbench/masks/bench/colab/MANIFEST").readline().strip(), flush=True)
    subprocess.run(["python", "-c", GOLD_CHECK], check=True)
    subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], check=True)
    for lim in str(limit).split(","):  # "2,all": a smoke run, then the full run on the same download
        out = "/results" if lim == "all" else "/results/smoke"  # smoke rows must not seed a full run's resume
        os.makedirs(out, exist_ok=True)
        proc = subprocess.Popen(["python", f"/root/maskbench/masks/bench/{script}", model, quant,
                                 str(1 if lim != "all" else runs), out, lim, *arms.split(",")])
        try:
            while proc.poll() is None:  # commit rows as they are written, so a lost container keeps them
                try:
                    proc.wait(timeout=300)
                except subprocess.TimeoutExpired:
                    pass
                results.commit()
        finally:
            results.commit()
        if proc.returncode:
            raise RuntimeError(f"{script} exited {proc.returncode} (limit {lim})")


GPU = os.environ.get("MASK_BENCH_GPU", "A100-80GB")
run_arms = app.function(gpu=GPU, timeout=6 * 3600, volumes={"/results": results})(arms_fn)


@app.local_entrypoint()
def main(model: str, quant: str = "bf16", runs: int = 1, limit: str = "2", arms: str = "free:sheet,grammar2:sheet"):
    run_arms.remote(model, quant, runs, limit, arms)
