# md-param-check failure modes, checked against pmemd

Findings only. Nothing here is fixed in md-param-check, and nothing in its repo was changed.
The checker is `checks/check_amber.py` in
`~/Downloads/Single Particle/Single Particle/.claude/skills/md-param-check/`, read as of 2026-09-27.

## How each case was checked

Each case is a small mdin that differs from a legal baseline in one thing. It was run two ways:
through `check_amber_in`, and through pmemd 26 (`~/Downloads/pmemd26/bin/pmemd`, 2 steps) on the
Single Particle system (`phase3-explicit-solvent-md/complex.parm7` + `complex.rst7`, 27,356 atoms).

```
pmemd -O -i t.in -p complex.parm7 -c complex.rst7 -o t.out -r t.rst7
```

The pmemd value is the one printed in mdout's `CONTROL DATA FOR THE RUN` section, not the input
echo above it. My first pass read the echo and got the duplicate-key case backwards. Every run
goes NaN at step 1 because the structure is not minimized. That happens after the input is
parsed, so it does not affect anything below.

Baseline (legal, passes both):
`imin=0, irest=0, ntx=1, nstlim=2, dt=0.002, ntc=2, ntf=2, cut=9.0, ntb=1, ntt=3, gamma_ln=2.0,
temp0=300.0, tempi=300.0, ig=71277, ntpr=1`.

## False PASS: the checker accepts a file pmemd rejects or runs with a violating value

| # | Case (change from baseline) | check_amber | pmemd 26 |
|---|---|---|---|
| 1 | `dt = 0.002, ! 2 fs/step` then `cut = 15.0` on the next line | PASS | reads `cut = 15.00000` and runs |
| 2 | an unknown key in `&cntrl` (`ntsx = 1`) or in `&wt` (`bogus = 1`) | PASS | aborts: `Fortran runtime error: Cannot match namelist object name ntsx` |
| 3 | `nmropt = 1` with no `&wt type='END'` (and with no `&wt` at all) | PASS | aborts: `ERROR: No "wt" namelist with TYPE=END found` |
| 4 | `dt = 0.0`, and `dt = -0.002` | PASS | reads `dt = 0.00000` / `dt = -0.00200` and starts MD |

1. **A `/` inside a comment ends the block early.** `NAMELIST_RE` finds the first `/` before
   comments are removed, so every key after the comment disappears. pmemd skips the comment and
   reads them. The restart rule works around this by re-parsing comment-stripped text, but the
   dt, SHAKE, cut, thermostat and temp0 rules use the truncated parse. This one is already
   known: `Gap_Gate_Coverage.md` (2026-06-27) records it with the shared-parser fix deferred.
   It is still present.
2. **Unknown keys pass.** The checker only reads the keys it knows. A hallucinated key is
   invisible to it and fatal to pmemd. That matters here, because inventing keys is the most
   common thing the 7B model does wrong (`ntfout`, `nsa`, `icell`, `nmd` in the smoke run).
3. **`nmropt = 1` does not check for the `&wt type='END'` terminator** that pmemd needs. The
   `&wt` code only compares the TEMP0 ramp with `temp0`.
4. **`dt` has an upper bound and no lower bound.** Zero and negative timesteps pass.

## False FAIL: the checker rejects a file pmemd runs as written

| # | Case | check_amber | pmemd 26 |
|---|---|---|---|
| 5 | block closed with `&end` instead of `/`, legal values | FAIL `&cntrl missing` | reads it (`dt = 0.00200`) |
| 6 | `ntc = 3, ntf = 3` at `dt = 0.002` (SHAKE on all bonds) | FAIL `dt > 1 fs cap (no SHAKE)` | runs with `ntc = 3` |
| 7 | `dt = 2.0d-3` (Fortran d-exponent) | FAIL `dt not a finite number` | reads `dt = 0.00200` |

5. **`&end` is not a terminator** for `NAMELIST_RE`. The known fix, deferred in the same
   2026-06-27 entry, is to make the parser also accept `&end`.
6. **Only `ntc = 2, ntf = 2` counts as SHAKE on**, because the code tests `ntc == 2 and
   ntf == 2`. SOP §3 allows 2 fs "when SHAKE is on". Whether `ntc = 3` counts as SHAKE on is a
   question for whoever owns the SOP.
7. **The d-exponent is refused by stated policy** (the error message says so). It is listed
   only for completeness.

## Right verdict, misleading reason

| # | Case | check_amber | pmemd 26 |
|---|---|---|---|
| 8 | `ntc = 2` with `ntf` omitted, `dt = 0.002` | FAIL `dt > 1 fs cap (no SHAKE)` | runs (ntf defaults to 1) |

8. The FAIL is consistent with SOP §3, which requires `ntc = 2, ntf = 2`. The reason is wrong,
   though: SHAKE is on (`ntc = 2`), and the real fault is the ntc/ntf mismatch. `SHAKE
   incoherent` does not fire because it only compares `ntf` when `ntf` is written out. The
   restart rule applies AMBER defaults for omitted keys; this rule does not. So "SHAKE
   incoherent" silently depends on `ntf` being explicit.

## Checked and fine: the checker agrees with pmemd

| Case | check_amber | pmemd 26 |
|---|---|---|
| duplicate key, `dt = 0.004` then `dt = 0.002` | PASS | uses the last value, `dt = 0.00200` |
| a second `&cntrl` block with `dt = 0.004` | PASS | uses the first block |
| no title line (`&cntrl` on line 1) | same verdict as with a title | finds the namelist (dt read correctly) |

The duplicate-key case matters for decoding even though the checker is right. Last-value-wins
means a committed `dt = 0.004` can be "undone" by a later `dt = 0.002`, so a prefix checker that
reported the violation early would be unsound. That is why the wrapper in `checkers/amber.py`
bans duplicate keys. The ban is a decoding requirement, not a checker bug.

## Failure modes that only appear when the checker is used as a prefix checker

These are not bugs in md-param-check for its original job (checking finished files). They are why
`checkers/amber_grammar.py` restricts the surface syntax.

- **Last value wins** (above): a violation can be overridden later, so decoding bans duplicates.
- **Truncation by `/` in comments or strings**: a prefix's parse can change when a later `/`
  arrives. The grammar allows no comments and no `/` inside strings.
- **Quoted values span lines.** `KV_RE`'s `'[^']*'` alternative crosses newlines, so a quote
  opened on one line and closed several lines later swallows every key in between. Not
  checked against pmemd; the grammar keeps strings on one line.
- **Every dynamics rule is conditional on `imin`.** A prefix holding `dt = 0.004` is still alive
  until `imin` is written, because `imin = 1` would switch the dt rule off. This is sound, but it
  catches violations late when a model writes `imin` after `dt`.
- **WARN never blocks.** The temp0/&wt mismatch (the heat-3 bug), `gamma_ln` range, fixed `ig`,
  `iwrap` on long runs, and non-Langevin thermostats are WARNs, and the decoder treats WARN as
  pass, as the checker's exit code does. Enforcing any of them is a scope decision for the study.

## What this means for the study

Checker-pass and pmemd-runs are different columns. Cases 1–4 are the reward-hacking surface
the onboarding report warns about: a decoder or a GRPO policy optimized against this checker can
satisfy it with a file pmemd rejects, and hallucinated keys (case 2) are the 7B model's commonest
error. The grammar's key whitelist closes case 2 for the decoding arms only. The gold evaluator
should be the pmemd parse itself (does mdout's CONTROL DATA show the intended values, and does
pmemd get past input processing), which takes about a second per file on this machine.
