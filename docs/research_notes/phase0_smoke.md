# Phase 0 smoke run: what the five arms do on the laptop

A smoke test of the pipeline, not a result: 8 hand-written prompts, one seed. Any
difference of one or two samples between arms is noise. What it can show is how each arm
fails, and it shows that clearly.

```
uv run python run_arms.py --prompts prompts/amber_smoke.jsonl --n 8 --out results/amber_smoke.jsonl
uv run python run_arms.py --table results/amber_smoke.jsonl
```

Settings: Qwen2.5-7B-Instruct-4bit on MLX (M3 Pro, 36 GB), T=0.7, 400-token budget, 8
particles for best-of-N and SMC, AWRS capped at 2,000 rejections per token. The system prompt
carries one fixed format example (a minimization), so it gives away no dt/SHAKE/restart
answers.

| arm | n | valid | grammar ok | checker ok | has duplicate keys | pmemd ok | valid, pmemd rejects | LLM queries / sample | LLM queries / valid | checker calls / sample | s / sample |
|---|---|---|---|---|---|---|---|---|---|---|---|
| free | 8 | 0/8 | 0/8 | 4/8 | 2/8 | 1/8 | 0 | 261 | inf | 0 | 9.8 |
| grammar | 8 | 2/8 | 2/8 | 4/8 | 2/8 | 1/8 | 1 | 240 | 962 | 0 | 9.4 |
| bestofn | 8 | 5/8 | 5/8 | 6/8 | 5/8 | 2/8 | 3 | 1917 | 3067 | 0 | 63.4 |
| smc | 8 | 0/8 | 0/8 | 6/8 | 0/8 | 2/8 | 0 | 1335 | inf | 1315 | 62.1 |
| mask | 8 | 1/8 | 1/8 | 3/8 | 0/8 | 2/8 | 1 | 163 | 1302 | 2409 | 152.4 |

"valid" means the file is complete, in the grammar, and passes md-param-check. "pmemd ok" is
the gold column: pmemd 26 reads the file through to its RESULTS header.

## What it shows

1. **The constraint binds, but mostly on syntax, not physics.** No free sample was valid, and
   none was in the grammar, because the model invents keys (`ntfout`, `nsh`, `nts`, `ifree`, and
   more). Half of
   them pass md-param-check's rules on their own. On this model, the physics rules, which are
   the thing the study is about, account for a small share of the errors.
2. **Most failures are particles that died.** 24 of the 40 picked samples carry weight −inf.
   The model starts a key it made up. The grammar allows the prefix only because a real key
   begins that way (`nta` → only `ntave` fits; `icf` → only `icfe`). The one allowed
   continuation is so unlikely that AWRS exhausts its 2,000 rejections, and the particle dies.
   Without the cap, the same states cost up to 34 minutes on one prompt, in an earlier run on
   the pre-review code. This is the dead-end form of the distortion that greedy masking is
   known for, and it hits the mask arm (7/8 dead) and SMC (8/8 dead) hardest.
3. **SMC with 8 particles does not survive this model.** Every SMC sample died, from grammar
   dead ends and checker rejections. SMC needs particles in
   proportion to how rarely the model stays valid, and 8 is far too few here.
4. **Best-of-N is the strongest arm at this size, and it pays for it:** 5/8 valid, at about
   8× the LLM queries of one grammar sample.
5. **Checker-valid is not pmemd-valid.** pmemd rejected 8 complete, live samples that pass
   md-param-check's rules:
   - 4 on value-domain rules the checker does not have: `ntr must be set to 0 or 1!` (3) and
     `ntxo must be set to 1, or 2!` (1).
   - 3 free-arm samples on invented keys (`nitro`, `ntfout`, `ntfb`).
   - 1 on an unfinished `&wt` block.

   Unfinished files from dead particles account for most of the other pmemd rejections. Among
   those files, `ntp must be 0 if ntb != 2!` and `nmropt must be set to 0 or 1!` also appear.
6. **The mask found a loophole before the grammar was typed.** Barred from writing `ntc = 2`
   beside `ntf = 1` (a SHAKE-incoherent FAIL), a masked sample wrote `ntc = 2.01`. That switches
   off the checker's `ntc == 2` tests, and pmemd rejects it. The grammar now types every key as
   pmemd does, which closes this case. The general lesson stands: a decoder held to a checker
   finds the checker's blind spots, so gold has to be independent of it.

## What this changes for Phase 1

- **Keep pmemd as a gold column in every table.** Checker validity alone overstates success
  (point 5).
- **Take the syntax noise out before measuring physics placement.** Candidates: key sets per
  stage type in the grammar (a heating stage needs about 15 keys, not 71), a model that knows
  mdin (a larger or coder model; the disk has about 16 GB free), or SFT on the corpus first.
  Listing all 71 keys in the prompt made things worse (docs/DEVLOG.md).
- **Size SMC by the survival rate**, not at 8. Measure per-step particle death first.
- **The token mask needs either a cheap vectorised checker or a tighter grammar.** Python
  prefix checks inside AWRS cost 2,400 checker calls and 150 s a sample here.
- **Throughput for planning:** 7B on MLX is about 30 tokens/s for one stream. A 50-prompt × 3-seed
  × 5-arm run at these costs is roughly 10–15 hours on the laptop, so it belongs on PACE with vLLM.
