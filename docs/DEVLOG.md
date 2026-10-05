# Dev log

Dead ends and first occurrences only; newest first. Decisions live in commit messages.

watch: 2026-10-05 Qwen3.5-122B-A10B-FP8 keeps quantization_config on its outer vision-language config; AutoModelForCausalLM builds the text model from the inner config and transformers loaded the FP8 weights as bf16 (every `*_scale_inv` key UNEXPECTED, 228 GiB, offloaded to the CPU). Check the load report for UNEXPECTED keys; `PrefixLM.prequantized` passes the config on.

watch: 2026-10-05 `modal run --detach` stopped twice when the laptop's connection to Modal dropped (once mid-run, once mid-download). Deploy the app and `spawn` the call (`colab/modal_app.py`); poll the FunctionCall.

watch: 2026-10-04 `qwen.Sheet` accepted the end of a reply only after a newline following the last mask, so a model that wanted to stop after its mask was pushed on toward the 79-character cap: every answer in a one-task prompt, the last of each sheet. Median mask 77 characters on the 27B checked arm, 15 after the fix; `tests/test_mask_decode.py` covers it.

watch: 2026-10-04 a 4-bit Qwen3.8-27B across two T4s: `device_map="auto"` put 5.4 GiB on one and filled the other, which ran out of memory on the first prompt; a per-GPU `max_memory` cap then made the bitsandbytes loader refuse to start ("dispatched on the CPU"). `PrefixLM.device_map` splits the layers by hand.

watch: 2026-10-02 transformers 5.17 `DynamicCache.crop(n)` keeps n tokens when n > 0 (a deprecated legacy meaning) and removes |n| when n < 0, though the parameter is named `tokens_to_remove`. `decode.PrefixLM` crops with a negative count; `tests/test_mask_decode.py` fails on the other reading.

watch: 2026-10-02 Qwen2.5-7B-4bit on MLX with 10–12k-token mask-bench prompts, next to the user's desktop apps, filled the 36 GB laptop's RAM and all 36 GB of swap; the machine lagged for a long while and the job needed kill -9. Run long-prompt local decoding on Colab/Kaggle, or check `sysctl vm.swapusage` first.

watch: 2026-10-02 the mask-bench parser stripped quote characters from both ends of an answer, which chopped the prime off nucleic-acid atom names (`O4'` → `O4`, `HO3'` → `HO3`) and scored right masks as wrong. Strip only a pair of enclosing quotes (`blind.clean`).

watch: 2026-10-02 ambmask rejects a mask longer than about 80 characters (`pop_evalstack`) that pmemd26 reads (84 characters, 432 atoms); a right but long answer was scored "rejected". `tasks.select` evaluates long masks as a union of short pieces.

## 2026-10-02 — Qwen 7B answering one mask task per prompt, with the system view

**Tried:** the pilot's layout (one chat per task) with the bench view (4k–12k tokens) in the system prompt, on MLX.
**Failed because:** genlm's MLX pool reuses KV only for a live row that is a strict prefix of the next prompt, so every sample re-prefilled the whole view: 36 s for one sample, and one sample took 1,282 s. About 125 tasks × 3 samples × 2 arms would take hours.
**Do not retry unless:** the backend keeps a prefix cache across prompts. `qwen.py` instead answers a whole system as one sheet, the same prompt Claude gets.

## 2026-10-02 — a POPC:POPE:cholesterol bilayer from packmol-memgen

**Tried:** `--lipids POPC:POPE:CHL1`, ratios 2:1:1 and 3:1:1, at 40 and 50 Å, up to `--nloop_all 400` (10 min).
**Failed because:** packmol never converged (it wrote `bilayer_only.pdb_FORCED`), with the warning "sterol concentration too high or the system too small".
**Do not retry unless:** the box is larger or cholesterol is below 20%. The bench uses POPC:POPE 3:1 and keeps packmol's best solution, which also ends "without perfect packing" but is fine for masks.

watch: 2026-10-01 ParmEd's AmberMask accepts `@H*` (13,676 atoms) where pmemd and ambmask reject it; mask gold must come from ambmask, never ParmEd.

watch: 2026-10-01 ambmask silently truncates long file paths and cannot read a NetCDF restart (`STOP error reading natom from inpcrd`); run it with cwd in the system dir on an ASCII rst7.

## 2026-10-01 — MDDataBench and MDGym as sources of AMBER mdin tasks

**Tried:** cloning both (matsunagalab/MDDataBench; M3RG-IITD/MDGYM for arXiv 2605.08941) to take NL prompts and reference mdin files for the Phase 1 set.
**Failed because:** neither has an mdin. MDDataBench tasks are whole pipelines (prep, membrane, ligand, MD) scored against deposited MDDB trajectories, so a task maps to no single input file. MDGym covers LAMMPS and GROMACS only.
**Do not retry unless:** a single-stage AMBER task is wanted from MDDataBench's conditions (temperature, pressure, ensemble), with the reference mdin written by hand, or MDGym adds AMBER.

watch: 2026-10-01 pmemd 26 stops with `Fortran runtime error: End of file` when the final `/` has no newline after it; two ambermd.org `<pre>` blocks end in `/</pre>`.

## 2026-09-27 — listing the allowed &cntrl keys in the system prompt

**Tried:** appending the grammar's 71 &cntrl keys to the system prompt, so the 7B model would stop inventing keys (invented keys are what strand a masked model: after `nta` only `ntave` fits, and AWRS runs out of rejections).
**Failed because:** the model copies the list in order (`imin, irest, ntx, ntxo, nstlim, nscm, nrespa, …`), setting every key, and runs out of tokens. Validity fell on the first 8 rows (0 valid, where the run without the list had 2), so the run was stopped.
**Do not retry unless:** the list is short and task-specific (the keys a stage of this kind needs), or the model is trained, not prompted.

watch: 2026-09-27 genlm-control 0.4.0 `recursive_awrs` crashed on `assert log_q <= error_tolerance` (Qwen2.5-7B-Instruct-4bit on MLX, smc arm, heat-nvt, seed 0, max_rejects=2000, key-list prompt). run_arms.py now logs a sampler crash as that arm's failure (`sampler_error`) and keeps going. If it recurs, reproduce outside run_arms and report upstream.

## 2026-09-27 — AWRS with default proper weights for the single-sample arms

**Tried:** `AWRS(llm, condition)` with its defaults as the grammar and mask arms: one particle, no resampling.
**Failed because:** the properly weighted estimator sometimes returns a rejected token with weight 0. Without resampling that particle is simply dead (`&wt\niinpc`, logw −inf), so single-sample arms reported grammar-invalid output that looked like a leaky mask.
**Do not retry unless:** resampling follows. The smc arm keeps proper weights; grammar, mask and best-of-N use `proper_weights=False`.

## 2026-09-27 — genlm's BoolFSA as the mdin grammar potential

**Tried:** `BoolFSA.from_regex(MDIN_REGEX)`, coerced to the LLM, as the AWRS condition.
**Failed because:** its first `prefix` call runs `backward()`, a generic semiring linear solve over the whole automaton: 74 s and 295M semiring products on this grammar (M3 Pro) before the first token. On the 7B run the grammar arm sat at 100% CPU for more than 15 minutes.
**Do not retry unless:** genlm-grammar computes Boolean co-accessibility by graph search, or the grammar shrinks to a few dozen states. `MdinGrammar` (regex partial matching, about 66 µs a check) replaces it.

## 2026-09-27 — 1–1.5B models for the AMBER decode arms

**Tried:** Llama-3.2-1B-Instruct-4bit and Qwen2.5-1.5B-Instruct-4bit (MLX) writing an NVT-heating mdin, greedy and at T=1.
**Failed because:** neither knows the format. Greedy gives `MDIN 0 0 0 …` and `! Amber93mdout` repeated; T=1 gives unrelated text. There is nothing for a checker to steer. Qwen2.5-7B-Instruct-4bit knows the shape and makes the physics errors the checker tests, so the pilot uses it.
**Do not retry unless:** the small model has been trained on mdin (the RFT/GRPO arms), or the prompt carries dynamics examples, which leak the dt/SHAKE answers the checker tests.

watch: 2026-09-27 a Hugging Face xet download stalled for 10 min with a 0-byte `.incomplete` blob; `HF_HUB_DISABLE_XET=1` fetched the same model in 30 s.

watch: 2026-09-27 read pmemd's parsed values from mdout's CONTROL DATA section, never the input echo above it; reading the echo got the duplicate-key probe backwards.
