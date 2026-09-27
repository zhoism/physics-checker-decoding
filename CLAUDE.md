# CLAUDE.md

## What this is

A research repo for a placement study: should a deterministic physics checker for simulation
input files sit in the weights (GRPO or RFT with the checker as reward), in the decoder (SMC or
AWRS with the checker as a genlm-control potential), or after the decoder (repair loop), and
what does each placement cost? The testbeds are AMBER mdin (a pilot), OpenFOAM dictionaries (the
primary testbed) and LAMMPS (the second). Start with `docs/ONBOARDING.md`, which covers the
design, phases, kill criteria and the claims that still need checking. `docs/research_notes/`
holds the sourced notes behind it. The AMBER checker, `md-param-check`, lives in a separate
repo (`~/Downloads/Single Particle/Single Particle/.claude/skills/md-param-check/`, checker
`checks/check_amber.py`; that repo also holds the past MD work). This repo wraps it and does not fork it. If the two disagree about a rule, the checker
repo wins.

The code: `checkers/amber.py` (the checker with prefix semantics and a duplicate-key ban),
`checkers/amber_grammar.py` (the mdin grammar the decoder is held to),
`checkers/pmemd_gold.py` (the gold verdict: does pmemd accept the file),
`decoding/potentials.py` (both as genlm-control potentials) and `run_arms.py` (every decoding
arm on a prompt set; `--table` and `--verify` read a results file). The environment is
`uv sync`; the decode arms run Qwen2.5-7B-Instruct-4bit on MLX.

## The artifact

The study's results: the per-phase tables and figures (`results/`, `figs/`). Each one is
regenerated from logged runs by a committed command and carries its value, n and seeds.
Eventually these become a preprint and an upstream example (genlm-control or TRL).

Shipping is a command, not a push. A phase's results leave this repo through
`bash scripts/ship.sh && git tag -a results-phaseN`. ship.sh runs first and rebuilds that
phase's tables and figures from a clean state. A green suite is not done. Done is the
table regenerated and checked against the logged runs.

## The checks

```
bash scripts/gates.sh   # fast: the suite. Every push, via .githooks/pre-push
bash scripts/ship.sh    # slow: rebuild and check the results artifact. Before every results tag
```

Enable the hook once per clone or worktree: `git config core.hooksPath .githooks`.

The working discipline (scope, recording work, executed / read / unverified) is in the plugin's
`discipline` skill. Load it at the start of a task here. Every report opens with those three
words. `SHIP_BRANCH` in `scripts/ship.sh` is empty because the tag command above chains
ship.sh.

## Derive, don't recite

**If git or the filesystem owns a fact, do not write it down.** Branch, merged, pushed,
counts, sizes, test totals and what has been published each have an authoritative source.
A sentence that asserts one of them is a cache, and it goes stale before anyone re-reads it.
Run the command instead:

```
git log --oneline; ls results/ figs/     # what exists
git tag -l 'results-*'                   # what has shipped
```

What git does not own is **why**. That is the thing worth writing down. Record it in the commit
message. A claim sourced only from a PDF summary or a search snippet stays a lead until it is
checked against the paper (see the last table in `docs/ONBOARDING.md`).

## Watch-list

*Failures that have bitten **this** project twice. The first time, one line in `docs/DEVLOG.md`
tagged `watch:`. The second time, `grep watch:` finds it and it moves here. An entry leaves when
it stops matching. Empty on purpose; do not seed it with someone else's.*
