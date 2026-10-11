# physics-checker-decoding

When a language model writes simulation input, where should a deterministic checker go: inside the decoder
(constrained decoding), or after it (a loop that feeds the checker's verdict back)? This repo tested that on
AMBER, mostly on atom masks (`:1-10@CA`, `(:1<:6.0)&:WAT`), where cheap and open models fail often.

**Status: closed (2026-10-08).** Only the AMBER work ran. The planned OpenFOAM, GRPO and LAMMPS phases in
`docs/ONBOARDING.md` did not.

## Result

The checker belongs after the decoder, as feedback. Gemma-4-31B (bf16) on the mask bench: 125 tasks on four
systems, 3 runs, so n = 375. A mask counts as right when ambmask selects exactly the reference atoms.

| | right |
|---|---|
| first try, free | 172 (46%) |
| first try, grammar-constrained | 239 (64%) |
| free first try, then the loop with no feedback (the mask alone) | 213 (57%) |
| free first try, then the loop with lint's hints | 320 (85%) |
| free first try, then the loop with lint's hints and what ambmask selects | 347 (93%) |
| grammar first try, then the same full loop | 340 (91%) |

The loop runs up to 3 rounds with reasoning on; the model keeps each mask or corrects it.

- A second pass with no feedback fixed none of the 104 masks ambmask rejected on the first try.
- The grammar helps a single try, but adds nothing once the loop runs.
- For scale: Sonnet 5 gets 240 of 250 right on its first try, Haiku 4.5 220 of 375.
- On mdin files (the first target), frontier models never tripped the physics checker: Sonnet 5 and Gemini
  Flash passed 44 of 44 (`docs/research_notes/masks_scout.md`, one run).

The winner is a retry loop with a real verifier, which is a standard technique, so the study stopped here.

Caveats:
- Failures cluster within a sheet (one system, one sample), so gaps under about 10 points are not established.
- lint's hints were written from this bench's failures. The only held-out check is ubiquitin, a system the
  bench never used: 12 requests × 3 runs, 27 of 36 right first try, 35 of 36 after the loop (`masks/ubq/`).

All tables are in `masks/bench/results/report.md`, rebuilt from the logged masks. The write-up is
`docs/research_notes/masks_bench.md`.

## The mask tool

`masks/mask_tool.py` runs the 93% recipe on any AMBER system: a prmtop, an inpcrd and plain-English requests.

```
.venv/bin/python masks/mask_tool.py sys.parm7 sys.rst7 "the CA atoms of residues 1-10" \
    [--leap leap.in] [--pdb x.pdb] [--model google/gemma-4-31b-it] [--rounds 3]
```

For each request it prints the mask, what ambmask selects, and whether the model kept it. A kept mask can still
be wrong (7% of the bench). The tool imports the bench modules, so it runs only inside this repo with the bench
systems built.

## Layout

- `masks/bench/`: the 125-task bench.
  - `build.sh` builds the four systems, checked against `SHA256SUMS`.
  - `tasks.py` and `tasks.jsonl` hold the requests and their reference masks.
  - `view.py` builds what the model is shown about each system.
  - `blind.py` runs the API models; `decode.py` and `qwen.py` the constrained-decoding arms.
  - `lint.py` holds the hints, `verify.py` the loop, `report.py` the tables.
- `masks/pilot/`: the 10-task pilot and mask grammar v1.
- `masks/ubq/`: the ubiquitin check.
- `checkers/`, `decoding/`, `run_arms.py`, `prompts/`: the mdin phase, with the checker wrapper, the mdin
  grammar and the genlm-control potentials.
- `docs/`: `ONBOARDING.md` is the original design; `research_notes/` holds the write-ups and the prior-art notes.

## Running it

- Python 3.12 and `uv sync`.
- AmberTools 24 (tleap, ambmask, cpptraj). Set `AMBERHOME`; the default is a local conda env.
- `bash masks/bench/build.sh` builds the bench systems.
- `.venv/bin/python masks/bench/report.py > masks/bench/results/report.md` rescores every stored mask (about
  10 minutes).
- Model calls go through OpenRouter, with `OPENROUTER_API_KEY` in `.env`.
- The mdin checker wraps `md-param-check`, which is not in this repo. Point `MD_PARAM_CHECK` at its
  `check_amber.py`.
- `bash scripts/gates.sh` runs the tests.
