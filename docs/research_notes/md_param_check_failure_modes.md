# md-param-check failure modes, checked against pmemd

Findings only. Nothing here is fixed in md-param-check, and nothing in its repo was changed.
The checker is `checks/check_amber.py` in
`~/Downloads/Single Particle/Single Particle/.claude/skills/md-param-check/`, read as of 2026-09-27.
Cases 9–12 turned up on 2026-10-01 in published tutorial files, while building the Phase 1 task
set (`phase1_amber_tasks.md`). Each was then reduced to a minimal file and run through
`check_amber_in` and `checkers/pmemd_gold.accepts` (pmemd 26 up to its RESULTS header).
Cases 13–28 are atom masks, checked on 2026-10-02 during the mask study (`mask_catalogue.md`,
`masks_bench.md`), the same way.

## How each case was checked

Each case is a small mdin that differs from a legal baseline in one thing. It was run two ways:
through `check_amber_in`, and through pmemd 26 (`~/Downloads/pmemd26/bin/pmemd`, 2 steps) on the
Single Particle system (`phase3-explicit-solvent-md/complex.parm7` + `complex.rst7`, 27,356 atoms).

```
pmemd -O -i t.in -p complex.parm7 -c complex.rst7 -o t.out -r t.rst7
```

The pmemd value is the one printed in mdout's `CONTROL DATA FOR THE RUN` section, not the input
echo above it. My first pass read the echo and got the duplicate-key case backwards. Every run
blows up in the first steps (NaN temperatures, then `Coordinate resetting (shake) was not
accomplished`) because the structure is not minimized. That happens after the input is parsed,
so it does not affect anything below.

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
| 9 | minimization with `ntmin = 3` | PASS | aborts: `ntmin must be set to 0, 1 or 2!` |
| 10 | `restraintmask = ":1-100@CA.C.N"` (periods for commas) | PASS | aborts: `Error in group input::atommask.f::atom_namelist` |

1. **A `/` inside a comment ends the block early.** `NAMELIST_RE` finds the first `/` before
   comments are removed, so every key after the comment disappears. pmemd skips the comment and
   reads them. The restart rule works around this by re-parsing comment-stripped text, but the
   dt, SHAKE, cut, thermostat and temp0 rules use the truncated parse. This one is already
   known: `Gap_Gate_Coverage.md` (2026-06-27) records it with the shared-parser fix deferred.
   It is still present. It hides a violation only when the keys a rule needs come before the
   comment: with `ntc`/`ntf` after it, SHAKE reads as off and the file FAILs, for the wrong reason.
2. **Unknown keys pass.** The checker only reads the keys it knows. A hallucinated key is
   invisible to it and fatal to pmemd. That matters here, because inventing keys is the most
   common thing the 7B model does wrong (`ntfout`, `nsa`, `icell`, `nmd` in the smoke run).
3. **`nmropt = 1` does not check for the `&wt type='END'` terminator** that pmemd needs. The
   `&wt` code only compares the TEMP0 ramp with `temp0`.
4. **`dt` has an upper bound and no lower bound.** Zero and negative timesteps pass.
9. **Value domains are not checked.** `ntmin = 3` (sander's LBFGS) is legal in sander, and
   pmemd 26 refuses it. The Compute Canada lesson's bilayer minimization uses it. The same
   class as the smoke run's `ntr` and `ntxo` rejections.
10. **Masks are never parsed.** A malformed mask passes and pmemd aborts on it. The Rizzo 2024
    1NDV tutorial prints this mask in two of its inputs.

## Atom masks: the checker never reads them (cases 13–28)

md-param-check takes only the mdin, never the topology, and it has no rule for `restraintmask`,
`bellymask`, `ntr`, `ibelly` or the TI masks (`check_amber.py`, read 2026-10-02 at f9f54b1). Its
findings are identical with and without a restraint mask. Each case adds
`ntr=1, restraint_wt=2.0, restraintmask=...` to the baseline above. pmemd 26 ran on the same Single
Particle system (154 protein residues, MG, two `Cl-` ions, 4-point `WAT`), with the mask counts read
from pmemd's own `Mask ...; matches N atoms` line. The checker's verdict for every case is PASS,
apart from the baseline's fixed-seed WARN (`ig=71277`), which is unrelated.

**False PASS: pmemd stops on the mask.** These extend case 10.

| # | Case | check_amber | pmemd 26 |
|---|---|---|---|
| 13 | `'@H*'` (glob wildcard; AMBER's is `=`) | PASS | aborts: `atommask.f::atom_namelist` |
| 14 | `'@/H'` (cpptraj's element selector) | PASS | aborts: `atommask.f::tokenize` |
| 15 | `':40,:84,:120'` (`:` repeated inside a list; cpptraj accepts it) | PASS | aborts: `atommask.f::residue_numlist` |
| 16 | `'protein and name CA'` (VMD syntax) | PASS | aborts: `atommask.f::selectElemMask` |
| 17 | `restraintmask=:1-154&!@H=` (unquoted) | PASS | aborts: `Cannot match namelist object name :1-154&@h` |
| 18 | a 1,476-character residue list | PASS | aborts: `atommask.f::pop_evalstack` (pmemd reads up to 1,024 characters; sander up to 256, AM26 p. 433) |
| 19 | `':1-10@C1''` (a prime inside a single-quoted mask; AM26 p. 429 says to double it: `C1'''`) | PASS | aborts: `Fortran runtime error: End of file` |
| 20 | `ramdprotmask=':1'`, the name the Amber26 manual gives (p. 459); pmemd's is `ramdproteinmask` | PASS | aborts: `Cannot match namelist object name ramdprotmask` (case 2's class, documented in the manual) |

**Silent: pmemd runs, and restrains other atoms than the mask was meant to.** A checker that reads
only the mdin cannot see these, because each depends on the topology. They are the harder half:
the run goes on with a wrong restraint, and only the `matches N atoms` line shows it.

| # | Case | meant | pmemd 26 restrains |
|---|---|---|---|
| 21 | `'!:HOH&!@H='`: the PDB water name; AMBER's is `WAT` | protein heavy atoms (1,189) | 13,680: also all 6,244 water oxygens, all 6,244 extra points, MG and both Cl- |
| 22 | `'!@H= & !:NA,CL,MG,WAT'`, the Rizzo tutorials' mask, on a system whose chloride is `Cl-` | 1,189 | 1,191: both chloride ions restrained |
| 23 | `':1,ALA'`: a list mixing a number and a name | residue 1 plus the alanines (142, as `:1\|:ALA`) | 130: pmemd reads the whole list as names and drops residue 1 |
| 24 | `':1-154&!@H'` for "heavy atoms" | 1,189 | 2,229: `@H` is only atoms named exactly H; `@H=` is every hydrogen |
| 25 | `'@CA,C,N,O'` for "backbone", unrestricted | 616 (`:1-154@CA,C,N,O`) | 6,860: every water oxygen (atom `O`) too |
| 26 | `'(:1-10)@CA'` | the CA atoms of residues 1–10 (10) | 154: an atom list after `)` applies to the whole system |
| 27 | `':;5'`, cpptraj's original-residue-number selector | residue 5 | 0 atoms, no error: the run has no restraint |
| 28 | `restraintmask` set with `ntr=0` | a restraint | no `Mask` line at all: the mask is ignored, the run is unrestrained (mailing list 202211/0168) |

Not run through pmemd here but documented with sources in `mask_catalogue.md`:
- A residue name present in one system and not another (`:Na+` vs `:NA`; `:HIS` when tleap wrote
  `HIE`).
- `@CA` also selecting a calcium ion (the manual's own BUGS note, AM26 p. 512).
- `bellymask` selecting the atoms that *move*, the inverse of `restraintmask` (AM26 p. 433).
- Distance masks evaluated once, on the `-c` coordinates, unless the undocumented `mask_from_ref=1`
  is set.

**What catching them would take** (written up, not implemented, per the hands-off rule):
- Cases 13–19 need a mask parser, such as the bench's grammar (`masks/pilot/mask_grammar.py`) or a
  call to ambmask.
- Cases 21–27 need the topology. Evaluate the mask and report its count and residues, flag an empty
  selection, and flag names absent from the topology. `masks/bench/lint.py` does the second part
  from the mask and the prmtop.
- Case 28 is an mdin-only rule: `restraintmask` without `ntr=1`, or `bellymask` without `ibelly=1`.

## False FAIL: the checker rejects a file pmemd runs as written

| # | Case | check_amber | pmemd 26 |
|---|---|---|---|
| 5 | block closed with `&end` instead of `/`, legal values | FAIL `&cntrl missing` | reads it (`dt = 0.00200`) |
| 6 | `ntc = 3, ntf = 3` at `dt = 0.002` (SHAKE on all bonds) | FAIL `dt > 1 fs cap (no SHAKE)` | runs with `ntc = 3` |
| 7 | `dt = 2.0d-3` (Fortran d-exponent) | FAIL `dt not a finite number` | reads `dt = 0.00200` |
| 11 | block closed with `$end` instead of `/` | FAIL `&cntrl missing` | reads it |
| 12 | `cut = 999.0` with `ntb = 0`, in vacuum (`igb = 0`) or GB (`igb = 1`) | FAIL `cut out of range` | reads `cut = 999.00000` |

5. **`&end` is not a terminator** for `NAMELIST_RE`. The known fix, deferred in the same
   2026-06-27 entry, is to make the parser also accept `&end`.
6. **Only `ntc = 2, ntf = 2` counts as SHAKE on**, because the code tests `ntc == 2 and
   ntf == 2`. SOP §3 allows 2 fs "when SHAKE is on". Whether `ntc = 3` counts as SHAKE on is a
   question for whoever owns the SOP.
7. **The d-exponent is refused by stated policy** (the error message says so). It is listed
   only for completeness.
11. **`$end` is the other legacy terminator** and fails the same way as case 5. Rizzo's 2024
    1NDV production input uses it.
12. **The cut range is applied to every run**, though its message says "for explicit
    solvent". In a vacuum or GB run, `cut = 999` is how AMBER spells "no cutoff". The AMBER DNA
    tutorial says so in its own words ("we simply set CUT to be larger than the extent of the
    system (e.g. CUT = 999)"), and its no-cutoff runs fail the checker. Whether the [8, 12] Å
    range should depend on `ntb`/`igb` is a question for whoever owns the SOP.

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
pmemd get past input processing), which takes 0.2–0.4 s per file on this machine.
