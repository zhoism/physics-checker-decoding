# AMBER atom masks: what goes wrong, by category

2026-10-02. A sourced catalogue of mask failures, compiled for scoping the mask tool
(`masks_scout.md`). Each failure has a real example and a column for what could catch it: the
**grammar** (decoding constrained to valid masks), a **lint** hint (`masks/bench/lint.py`, from the
mask and topology alone), or **grounding** (giving the model a fact it lacks, such as a PDB→topology
residue map). The bench (`masks/bench/`, 125 tasks) has one category per row group.

Labels:
- **E**: executed in this session. ambmask, cpptraj V6.24.0 and tleap are from AmberTools 24.8; pmemd is
  the Amber26 build at `~/Downloads/pmemd26`. The probes are in the bench systems.
- **E26**: executed by a research agent on the conda-forge AmberTools 26.0 (ambmask, sander,
  cpptraj V7.6.2) and on pmemd26. Its probe scripts were scratch files and are not kept; the counts
  are tabulated in `mask_sources/manual_cpptraj.md`.
- **R**: read at the cited page or file.
- **L**: a lead (search snippet only).

The detailed notes, with every quote and URL, are in `mask_sources/`:
- `manual_cpptraj.md`: Amber26 manual ch. 25, pmemd/cpptraj/ParmEd source, a 5-tool count table.
- `mailing_list.md`: 48 archive threads.
- `dialects.md`: VMD, MDAnalysis, PyMOL, MDTraj, GROMACS and CHARMM.
- `naming_tutorials.md`: leap libraries, plus about 200 masks from published tutorials.

Agents compiled them, and they carry their own labels. Abbreviations: AM26 = Amber 2026 Reference
Manual (https://ambermd.org/doc12/Amber26.pdf; printed page = PDF page). Mnn = thread nn in
`mailing_list.md`. Tnn = ambermd.org tutorial nn.

## 0. Two facts that make the rest silent

- **A mask that selects nothing is not an error.** pmemd and sander print `Mask ...; matches 0 atoms`
  and run on (E26; M30, M37). ambmask prints only "Warning: no atoms selected" (E).
- **A wrong but non-empty mask is invisible** unless someone reads the `matches N atoms` line. Of the 48
  mailing-list threads, at least 12 were silent failures (`mailing_list.md`, summary). The developers'
  standing advice is to check that line and test the mask with ambmask (M01, M15, M30, M31, M33).

So a tool must check syntax, and it must also show *which atoms* a mask selects.

## 1. Dialect: syntax from another selection language

| failure | real example | source | caught by |
|---|---|---|---|
| VMD/MDAnalysis words (`protein and name CA`, `resname HOH`, `resid 10 to 20`) | Qwen 7B: 29/30 masks rejected for this, with the right intent | `masks_scout.md` | grammar; lint |
| glob `*`, `?` in names (`@H*`, `@C?`) | Haiku `@H*` (scout); `@N*,C*,O*` rejected by sander (M23) | scout; M23; E26 | grammar; lint |
| cpptraj-only selectors `@/H` (element), `^1` (molecule), `::A` (chain), `:;5` (PDB number) | Haiku `:1-12&!@/H` on the bench smoke run; pmemd rejects `@/`, `^` and `::`, and **silently selects 0 for `:;5`** | E; AM26 p. 728; E26 | grammar; lint |
| `.` typed for `@` (`:1-185.CA`, `:WAT.O`, `@CA.C.N`) | 3 users on the list; the Rizzo tutorials' `restraintmask=":1-489@CA.C.N"`, fatal in sander and silently empty in cpptraj | M20, M21; `naming_tutorials.md` B1.1 | grammar |
| `:A,:B` (colon repeated in a list), `@(N,CA,C,O)` | Haiku `:HID,:HIE`, `@(N,CA,C,O)`; Rizzo `strip :WAT:Na+:Cl-` (works in cpptraj, fatal in sander) | scout; B1.1 | grammar |
| distance written VMD-style or out of order (`@<:100@5.0`, `<:224>:3.0`, `(:K+)<:6.0(:1-24)`) | Haiku, bench smoke run | E | grammar; lint |
| `~` for not, `:1:10` as a range | M23; cpptraj silently reads `:1:10` as residues 1 and 10 | M23; `dialects.md` (E) | grammar |

The AMBER archive itself teaches the `.` error. Its spam filter rewrites most `@` in masks as `.`
(`!@H=` shows as `!.H=`), and in two threads this leaves the developer's correction unreadable (M20,
M21; checked in the raw HTML). Any corpus scraped from the archive carries the wrong operator.
Typographic quotes on WordPress tutorial pages (`”:1-542″`) are the same kind of hazard
(`naming_tutorials.md` B1.3.8).

## 2. Accepted by pmemd, but not the atoms meant

No error is raised for any of these.

| failure | what happens | source | caught by |
|---|---|---|---|
| `@H` for "hydrogens" | only atoms named exactly H (backbone amide H): 29 vs 15 atoms in a test, and 3,446 vs 3,675 in T25's own pmemd output | `dialects.md` E; `naming_tutorials.md` B1.2 | lint |
| a list mixing numbers and names, `:1,ALA` | pmemd reads the whole list as names and drops residue 1. cpptraj and ParmEd keep it: **the same string selects 140 atoms in pmemd and 161 in cpptraj** on the trypsin system | E (pmemd26, ambmask, cpptraj); `findmask.F90` "if there is a letter in it, it is NAMELIST" | lint |
| `@CA` with a calcium ion present | the Ca²⁺ atom is also named CA: 224 vs 223 on trypsin. The manual lists this as a known bug | E; AM26 p. 512 | lint |
| `@C=` for "carbons" | also matches Cl⁻ (atom name `Cl-`), CL and the CA calcium: 21 ion atoms on trypsin (1,033 vs 1,012) | E26 (761 vs 759); E | lint (partly) |
| `@H=` for "hydrogens" | also matches the mercury ion HG; `!@H=` keeps massless extra points (EPW) | `naming_tutorials.md` A0.7 (E) | — |
| unrestricted backbone `@CA,C,N,O` | also every water oxygen (atom `O`): T26 ASMD restrains 2,922 waters. The manual's own `@CA,C,O,N,H` example does the same | `naming_tutorials.md` B1.2, A0.6; AM26 p. 509 | grounding (residue range) |
| `(:7,137)@SG` | the atom list after `)` applies to the whole system, so it selects every SG | E (bench smoke: Haiku); scout | lint; grammar (forbids it) |
| `:=A` | selects every atom (the manual says `=` cannot match name ends) | E26; AM26 p. 511 | grammar |
| `:9999`, `:10-1`, `:;5` | 0 atoms, no message in pmemd | E26 | — (empty check) |
| a residue name that does not exist (`:HOH`, `:HIS`, `:Na+` when the system has `NA`) | 0 atoms | E; `naming_tutorials.md` A0.3 | lint; grammar (system vocabulary) |
| case: `:wat` | pmemd/ambmask ignore case (600 atoms), cpptraj and ParmEd do not (0) | AM26 pp. 510, 728; E26 | — |

## 3. Numbering: the topology is not the PDB

A pmemd mask can only use the topology's sequential residue numbers (AM26 p. 509: "Do not use the
original atom numbers from the raw PDB file").

| failure | example | source | caught by |
|---|---|---|---|
| chains restart at 1 in the PDB, but the topology runs on | "1 chain with residue from 1 to 119, the other ... 1 to 30" → `:1-149` | M01 | grounding |
| a structure that starts past residue 1 | barnase (1BRS chain A) starts at Val3: PDB His102 is `:100` | M02; bench `bnbs` | grounding |
| missing residues | barstar Glu64–Asn65 are unresolved: PDB 66–89 is `:172-195`, not `:174-197` | bench `bnbs` | grounding |
| insertion codes and numbering skips | trypsin uses chymotrypsin numbering: 184A and 184 are `:164` and `:165`; PDB 30–40 is nine residues (`:15-23`) | bench `tryp` | grounding |
| pdb4amber's `_renum.txt` | has no insertion-code column (184A and 184 both print as `184`); written before `-d` stripping, so it goes stale | E; `naming_tutorials.md` A6 | — |
| tleap moves crystal waters after the ions it adds | trypsin's 62 crystal waters are `:257-318`. pdb4amber's map says 225–286, off by the 32 ions | E (atom-by-atom position match) | grounding |
| residues renumber after a strip | `:38-318` names different residues after `parmstrip` (M05); MMPBSA ligand number after stripping (M45) | M05, M45 | — |
| PDB columns wrap at 9999 | residue 9999 is followed by 0 in a cpptraj PDB | M08 | — |
| MDTraj numbers are 0-based | MDTraj `resid 10` is file residue 11 | `dialects.md` | — |

## 4. Chains: the prmtop has none

- A tleap prmtop has no chain IDs or original residue numbers. tleap's `keep_chainid` is off by
  default (AM26 pp. 270, 272); our four tleap builds have no such fields (E).
- pmemd's mask parser has no chain selector (`findmask.F90`). cpptraj's `::A` and `:;5` need those
  fields; without them `::A` silently selects 0 atoms (E26; AM26 p. 728; M02).
- pdb4amber splits a chain at a gap and inserts a TER. On barstar this made a second N-terminus (with
  H1–H3) and a second C-terminus (with OXT) in the middle of the chain (E). With `--noter` and no TER
  before the HETATMs, tleap fails instead (E). It also put a TER at every chymotrypsin numbering skip
  in trypsin (E).

## 5. Names

| family | the trap | source |
|---|---|---|
| ions | `atomic_ions.lib` has both `NA` and `Na+`, `CL` and `Cl-`, `K` and `K+`; the prmtop gets whatever addIons was given, and one system can mix them. Calcium is residue and atom `CA`. CHARMM uses SOD/CLA/POT/CAL; charmmlipid2amber and packmol-memgen write `Na+`/`Cl-`/`K+` | `naming_tutorials.md` A1 (E, R); E |
| water | every tleap water model is residue `WAT` (PDB HOH, CHARMM TIP3, GROMACS SOL). OPC and TIP4P-Ew add `EPW`; TIP5P adds `EP1 EP2` | AM26 pp. 55–56; A2 (E) |
| protonation | there is no `HIS` unit: HIS becomes HIE. The others are HID, HIP, ASH, GLH, LYN, CYX, CYM, so ":HIS" selects nothing and "all histidines" needs every variant present | A3 (R, E); E |
| protein termini | the prmtop drops the N/C prefix (`:NVAL` selects nothing). A terminus is found by number or by `@H1,H2,H3` / `@OXT`. Water also has atoms named H1 and H2 | A3 (E); E |
| nucleic termini | the prmtop keeps the 5/3 suffix (`DC5`, `DG3`), so `:DG` misses `DG3`. 5′ residues have no P, so `:1-12@P` is 11 atoms | A4 (R, E); E |
| old atom names | `O1P/O2P` → `OP1/OP2`, `H5'1` → `H5'`, RNA `RA/RU` → `A/U`, NME `CH3/HH31` → `C/H1`. leap maps them on PDB input only, so an old mask selects nothing | A3, A4 (R) |
| Lipid21 | one lipid is three residues (sn-1 tail, head, sn-2 tail: POPC = `PA PC OL`). PA and OL reuse `C12`, `C13` … so `@C12` hits both tails. The ester carbonyls `C11`, `C21` sit in the head residue. Phosphorus and nitrogen are `P31`, `N31`. `:PC` is only the head | AM26 pp. 54–55; A5; E |
| primes in mdin | inside a single-quoted mdin string, a prime is written twice: `C1'` becomes `'C1'''` | AM26 p. 429 |

## 6. Operators and distance

- **Precedence** is `()` > distance > `!` > `&` > `|` (AM26 p. 511; E26, E). So `:1-3|:5-7&@CA`
  is `:1-3|(:5-7&@CA)`. `:GLY@CA | !:GLY@CB` means "everything but GLY CB" (M16). MDAnalysis gives
  `and` and `or` equal precedence, so a literal translation changes the meaning (`dialects.md`).
- **English "and" often means union.** A request for "protein, ligand and lipid heads", written with
  `&`, matched nothing (M15).
- **`<:` selects whole residues; `<@` selects atoms.** Both include the reference atoms: VMD `within`
  does too, MDAnalysis `around` does not (AM26 p. 547; `dialects.md` E). Bench task `bnbs-mda-around`
  tests the translation.
- **`>` is the complement of `<`** in ambmask 24, pmemd26 and cpptraj (E: 25 + 6 = 31 ions; E26). A 2013
  thread (M24) describes the older "any atom farther" meaning, which ParmEd 4.3.1 still uses (E26).
- **When a distance mask is evaluated.** It runs once, at setup, on the `-c` coordinates. The undocumented
  `mask_from_ref=1` switches to `-ref`, giving 132 vs 143 atoms (E26; M26). cpptraj uses the reference
  frame, except for its `mask` action (AM26 p. 729; M27).

## 7. Context: the variable around the mask

- `restraintmask` does nothing without `ntr=1`, and `ntr=1` needs `-ref` (M37, M38).
- **`bellymask` selects the atoms that move**, the inverse of `restraintmask` (AM26 p. 433; M25).
- **Length limits.** The limits are sander 256 (AM26 p. 433), pmemd 1,024 (source; E26) and ambmask 80
  (AM26 p. 512), which in practice is 79: an 80-character mask fails (E). Past its limit each fails with
  an unexplained `pop_evalstack` (E26). Here, ambmask rejected an 84-character list that pmemd26 read as
  432 atoms (E). The bench scores a long mask as a union of short pieces (`tasks.select`).
- **Quoting.** An unquoted mask gives a namelist error, and the run continues with restraint energy 0
  (M31). A mask split across lines fails (M36).
- **Variable names.** The manual's `ramdprotmask` and `cofactormask` are rejected by pmemd26, which wants
  `ramdproteinmask` and `cofacmask`. The AT26 sander rejects the manual's `scmask` (E26).
- **TI.** `timask1/2` must match the same number of atoms (M40). tiMerge on a two-chain protein gave a
  wrong `timask2` (M41).
- **MMPBSA.py.** Its input parser splits at commas, so `:1-468,509-510` loses a range (M47). The masks
  must partition the complex, with a contiguous ligand (M44). `ante-MMPBSA.py -n`'s help text is the
  reverse of what the code does (`naming_tutorials.md` B1.1, R from source).

## 8. What the categories say about a tool

- **Grammar** catches section 1 and some of section 2 (`(...)@`, `:=A`, names absent from the
  topology). It cannot see sections 3–7: those masks are valid.
- **Lint hints** cover the rest of section 2 and the name traps (`@H`, `@CA` with calcium, mixed lists,
  missing protonation or terminal variants, a type written as a name). They need the topology but not
  the answer.
- **Grounding** is the only fix for section 3 (numbering). The map must be computed from tleap's real
  order, not pdb4amber's renum file.
- **Showing the selection** (count, residues) is the check the developers ask for. It turns sections
  2 and 6 from silent into visible.

What the bench measures about each is in `masks/bench/` and the results note.
