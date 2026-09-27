# Dev log

Dead ends and first occurrences only; newest first. Decisions live in commit messages.

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
