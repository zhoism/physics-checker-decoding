# Scout: who needs a checker, and AMBER atom masks as the next target

2026-10-01. Small samples (one run of 44 mdin tasks; 10 mask tasks × 3–5 tries), so read the
numbers as directions, not results. Raw rows: `results/scout/` and `masks/pilot/results/`.
Status: scoping. ONBOARDING's design is unchanged until the mask direction is confirmed.
Followed by `masks_bench.md` (125 realistic tasks, 2026-10-02) and `mask_catalogue.md`.

## mdin: frontier models never trip the physics checker

| model | prompts | checker ok | pmemd ok | what went wrong |
|---|---|---|---|---|
| Qwen2.5-7B-4bit (laptop), free | parameters stated | 17/44 | 3/44 | loops, invented keys; 27/44 hit 400 tokens |
| Haiku 4.5 (subagent) | parameters stated | 33/44 | 21/44 | `ntc=2` without `ntf=2` ×11; mask syntax ×12 |
| Haiku 4.5 (subagent) | goal only | 32/44 | 29/44 | `irest=1` without `ntx=5` ×12 |
| Gemini 3.8 Flash (`run_api.py`) | parameters stated | 44/44 | 36/44, 43 after repair | `@H*` masks ×8 |
| Sonnet 5 (subagent) | both | 44/44 | 44/44 | none |

- Kill criterion (>90% checker pass) holds for frontier models on this set.
- Silent intent error the checker cannot see: on goal prompts Haiku halved 16/33 run lengths
  (`nstlim` sized for 2 fs, `dt` left at the 1 fs default). Checker and pmemd both pass them.
- `prompts/amber_phase1_goal.jsonl`: the same 44 tasks with timestep, SHAKE, steps,
  thermostat/barostat parameters and cutoff removed.
- Grammar too strict on titles: 22 of Sonnet's goal files failed only on `/` or `>` in the title.

## Masks: dialect, not intent, is what small and mid models get wrong

`masks/pilot/`: 10 English → mask tasks on the gold system. Gold is the atom set from
`ambmask`.

| arm | exact |
|---|---|
| Qwen 7B, plain prompt, free | 0/30 (29 rejected: VMD/MDAnalysis syntax, right intent) |
| Qwen 7B + AMBER cheat sheet (prompting only) | 7/50 |
| Qwen 7B + grammar (`mask_grammar.py`) | 9/30 |
| Qwen 7B + cheat sheet + grammar | 18/50; self-consistency over 5 tries: no gain |
| Haiku, blind (`blind.py`) | 15/30, 22/30 after one repair round; 21/30 as a subagent |
| Sonnet, blind | 30/30; 28/30 as a subagent (`@/H` ×2) |

- Every Claude error was syntax, never the wrong atoms, and the grammar blocks all 11.
  Haiku's repeat offenders: `@H*`, `:HID,:HIE`, `@(N,CA,C,O)`, distance syntax. A generic
  "invalid at character k" did not fix them. A targeted hint would.
- The 7B's gap is semantics: `!@H` for non-hydrogen, water selected by atom names. The
  cheat sheet also biased it: its `@CB` example turned "alpha carbons" into CB.
- These tasks are easy, and each prompt carried a hand-written system summary. The value case
  is cheaper and open-weights models (Sonnet is not open-weight), on realistic tasks.

## Facts about the tools

- `ambmask` (prime-amber env) shares pmemd's mask engine: both give 1190 atoms for
  `:1-155&!@H=` on the gold system.
- ParmEd's `AmberMask` is not a gold. It accepts `@H*` (13,676 atoms), which pmemd and ambmask
  reject.
- ambmask rejects `?` and `@/H`. cpptraj accepts `@/H`, and so does Sonnet.
- `=` is the only wildcard. `*` only stands alone (`:*`, `@*`).
- ambmask accepts junk: `:1--5`, `:1,`, a bare `@`. It reads `(:1)@CA` as every CA. The
  grammar is stricter on purpose.
- ambmask needs an ASCII restart and a short path. Run it with cwd in the system dir.
- System-aware vocabulary cuts both ways. It blocks `:HOH`, but it also blocked Sonnet's
  correct `:HID,HIE,HIP` (HIP is absent, and AMBER just ignores it). Next design: standard
  AMBER names in the grammar, an empty selection rejected separately.
- Closed-book runs must be blind by construction. `blind.py` runs `claude -p --tools ""
  --strict-mcp-config --no-session-persistence` from a fresh empty dir, with the tasks
  inline. A canary asked to read the answer file could not; it wrote fake tool calls as
  text.
- Load: 7B 4-bit on the M3 Pro took 1–2 s and 5–7 GB per mask, about 40 s of GPU for 30 masks.

Rebuild `masks/pilot/system/` (git-ignored) in the prime-amber env:

```
cp "<Single Particle>/phase3-explicit-solvent-md/_archive/submit-output-20260618/complex.parm7" masks/pilot/system/
python -c "import parmed; parmed.load_file('masks/pilot/system/complex.parm7', '<same dir>/heat-2.rst7').save('masks/pilot/system/ascii.rst7', format='rst7')"
```
