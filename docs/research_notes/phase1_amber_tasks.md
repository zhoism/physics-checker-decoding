# Phase 1 AMBER task set: what is in it and why

`prompts/amber_phase1.jsonl` holds one natural-language prompt per row, with its source URL,
tutorial, license and the tutorial's own description of the step (`quote`).
`prompts/amber_phase1/<id>.in` is the reference mdin, and
`prompts/amber_phase1/source/<id>.in` is the tutorial's file as published. The definition is
checked on every push:

```
uv run pytest -q tests/test_amber_tasks.py
```

Every reference is `scripts/normalize_mdin.py` applied to its source. It is in the grammar
and passes md-param-check. pmemd 26 also reads it to the same CONTROL DATA as the verbatim
source (values, masks, `&wt` changes), so normalizing changed nothing pmemd sees. Gold is
pmemd's acceptance, not anyone's judgement. A reference is one valid answer, not the only one.

## Where the files came from

Collected 2026-10-01, every file fetched verbatim with curl or git.

| source | collected | in the set | license |
|---|---|---|---|
| ambermd.org tutorials (alanine dipeptide; RAMP1 relaxation; pmemd; DNA decamer; PFF library) | 40 | 21 | "All materials copyrighted by authors." |
| Compute Canada molmodsim-amber-md-lesson (gh-pages a117664) | 9 | 4 | CC BY 4.0 |
| Rizzo Lab wiki, 2008–2026 AMBER tutorials | 40 | 10 | none stated |
| York group AMBER2026 workshop, Hands-On 2 (MTR1 ribozyme) | 28 | 9 | "© Copyright 2026, York Group." |
| MDGym (arXiv 2605.08941) | 0 | 0 | LAMMPS and GROMACS only; no AMBER files |
| MDDataBench (matsunagalab) | 0 | 0 | no mdin files; tasks are whole pipelines scored against MDDB trajectories |

Only the Compute Canada files carry an open license. The set is fine for research in this
repo. A preprint table or an upstream example should link to the tutorials rather than ship
their files, unless the authors agree.

MDDataBench's prompts ask for a whole pipeline: system prep, membrane embedding, ligands,
then MD. They do not ask for one input file. Of its 98 reference simulations, 84 ran at 2 fs
and 14 record no timestep. The "HMR 4 fs" in its README is only the recipe for the authors'
own MDClaw solves. So the decision that md-param-check's 2 fs cap stands costs MDDataBench
nothing. The one 4 fs file found anywhere (York's production input, `dt = 0.004` commented
"1 fs") is out on two counts: the cap, and a restraint file it needs.

## Why 73 of 117 files are not in the set

| reason | files |
|---|---|
| pmemd needs an external file (`DISANG=restrnt.disang`): York archive equilibration and production | 12 |
| block not terminated as printed (Rizzo 2013–2017 wiki pages), or not an mdin (a format example) | 9 |
| sander-only key or value (`scee`, `scnb`, `ntmin = 3`, `imin = 5`) | 8 |
| GB with `igb = 8`: the gold topology's radii are out of range for it | 7 |
| old GROUP restraint input after the namelist: the grammar has no form for it, and dropping it changes pmemd's parse | 6 |
| md-param-check FAIL, pmemd accepts: `cut = 999` in vacuum or GB (failure mode 12) | 4 |
| shell templates (`${X}`, `$MAXCYC`) | 4 |
| membrane `ntp = 3`: the gold box is a truncated octahedron | 3 |
| md-param-check FAIL, pmemd accepts: a real SOP violation in the tutorial (below) | 3 |
| malformed mask (`@CA.C.N`), or an `&ntrl` typo | 2 |
| passes all three, dropped in curation (below) | 15 |

Curation dropped 15 files that pass. **2 are GB (`igb = 1`)**: their references pass on the
gold system, but a valid answer using another GB model would fail there for the radii, so
gold would not be fair. **5 repeat another file**: same values once the restraint mask and
output frequencies are ignored. Two of these are Rizzo 2008, which copies the old AMBER DNA
tutorial. **3 are York page excerpts** of the short NPT steps. They set no thermostat, though
their prose says the temperature is held at 300 K. **4 are template repeats**: the 2024 1NDV
and 2026 1XGJ versions of steps the 2026 1G2L page also has. **1 is a lesson's deliberate
bug**: the Compute Canada 6N4O minimization "crashes after 4 cycles", and the lesson asks the
reader to fix it.

Gold depends on the system. pmemd checks GB radii and box shape when it reads the input, so
GB (`igb = 8`) and membrane stages cannot be scored on the current explicit-solvent
protein. Admitting them needs a second gold system, not a different task set.

**Three published tutorial files fail md-param-check for real reasons**, and pmemd runs all
three:
- Rizzo 2008 runs oxytocin in vacuum at `dt = 0.002` with no SHAKE.
- Rizzo 2013 (1LOQ) sets `ntc = 2, ntf = 1` in two files, one of them at 2 fs.

These are the errors the checker exists for, made by people who teach the method.

## How the prompts were written

Each prompt describes its reference, in physical terms and without keyword names:

- **Stated explicitly:** run type and length, timestep, SHAKE, fresh start or continuation
  with velocities, temperatures, thermostat, ensemble and barostat, pressure and coupling
  time when set, cutoff, vacuum, restraints (atoms in words, plus weight), and temperature
  ramps. An explicit `ntf = 1` reads as "no bond constraints".
- **Never stated:** output frequencies, file formats, seeds, COM removal, SHAKE tolerance,
  `tempi` on a restart.
- **Left to the model on purpose:** a setting the reference leaves at pmemd's default. That
  is where the physics checker can bind. Three Compute Canada stages set no timestep and no
  SHAKE, for example, so the model has to pick a pair that is legal. There is one
  exception: "no restraints" is stated after restrained stages, even where the file just
  leaves `ntr` unset.
- **Prose that contradicts its file:** the prompt follows the file, and the row's `note`
  says so. The York heating pages describe a 600 ps ramp, but their files have none. The
  York equilibration pages set `ntx = 5` without `irest = 1`. The manual says that ignores the
  velocities, but pmemd 26 starts from them (133.5 K at step 0 on the gold system; 0 K with
  the restart's velocities zeroed) and resets only the clock. Gold is pmemd, so these
  prompts ask for a continuation with velocities.

Prompt fidelity is the one part no command checks. An adversarial review read every prompt
against its reference. It checked every number in every prompt by script against the
reference values and `nstlim × dt`, and ran pmemd where the semantics were in doubt. It
found the York velocity error above, the 6N4O row, and wording gaps: "isotropic" missing on
five Monte Carlo rows, an unstated thermostat target, and two missing notes. All are fixed.
