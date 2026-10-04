# AMBER naming conventions and masks in published tutorials

Compiled 2026-10-02. No repository was edited. All scratch work lives under
`/private/tmp/claude-501/-Users-kevinzhou-Downloads-physics-checker-decoding/f748c8fc-97fe-42ff-ad2c-09897b65ebac/scratchpad/`
(written `$S` below).

**Labels**
- **RUN**: I ran the tool locally and the output is quoted. This is the strongest label.
  Installed tools: AmberTools 24.8 in the conda env `prime-amber`
  (`/opt/homebrew/Caskroom/miniforge/base/envs/prime-amber/conda-meta/ambertools-24.8-*.json`).
  Versions: tleap/teLeap, sander 24.0, cpptraj V6.24.0, ParmEd 4.3.1, pdb4amber 1.6.dev.
  Test inputs and outputs are in `$S/leaptest/` (t1.in … t7.in, *.log, *.prmtop).
- **READ**: I read it in a local file or on a fetched page. The decisive line is quoted.
- **LEAD**: I saw only a search snippet and did not read the page.

Local leap data is at `L=/opt/homebrew/Caskroom/miniforge/base/envs/prime-amber/dat/leap`.
The manual is the Amber 2026 Reference Manual, https://ambermd.org/doc12/Amber26.pdf,
read through `pdftotext -layout` (`$S/Amber26.txt`). Page numbers are the printed page numbers.
For history I also read https://ambermd.org/doc12/Amber14.pdf and
https://ambermd.org/doc12/AmberTools12.pdf.

---

# Part A. Residue and atom naming

## A0. Mask-parser facts that change what a name selects

These are not naming rules. They decide whether a name in a mask selects anything, so they come first.

| # | Fact | Evidence | Label |
|---|---|---|---|
| A0.1 | **sander/pmemd-style masks ignore case. cpptraj and ParmEd masks respect it.** On the same prmtop, `:wat` selects 600 atoms in sander and nothing in cpptraj or ParmEd. | Manual §25.1.1 (ambmask, p.510): *"Selections are case insensitive."* Manual §38.3.2 (cpptraj, p.728): *"All masks are case-sensitive."* RUN, `$S/leaptest/ca.prmtop`: sander 24.0 `restraintmask=':wat'` prints `Mask :wat; matches   600 atoms`. cpptraj `resinfo :wat` prints `Selection is empty.` ParmEd `AmberMask(p,':wat')` gives 0 atoms. | READ + RUN |
| A0.2 | **`@CA` also selects calcium ions.** The calcium unit is residue `CA` with atom `CA`. | Manual §25.1.1 BUGS (p.512): *"there is no way to distinguish some atom names: alpha carbon CA and a calcium ion Ca are a notorious example of that."* RUN (`ca.prmtop`, ACE-ALA-ALA-NME plus 1 Ca2+): sander `Mask @CA; matches 3 atoms`. cpptraj `atominfo @CA` lists `9 CA 2 ALA`, `19 CA 3 ALA`, `33 CA 5 CA … Ca2+`. The manual's own example (§25.1, p.509) says *"@CA = all atoms with the name CA (i.e., all C-alpha atoms)"*. | READ + RUN |
| A0.3 | **A mask that matches nothing does not stop sander.** `:Na+` in a system whose sodium is named `NA` (or the reverse) gives 0 atoms, and the run continues. | RUN: sander `Mask :Na+; matches 0 atoms` and `Mask :NA; matches 0 atoms` on `ca.prmtop`, which has no sodium. No error is printed. cpptraj prints `Selection is empty.` | RUN |
| A0.4 | **Residue names with `+` or `-` work as written** (`:Na+`, `:Cl-`, `:K+`, `@Cl-`). | RUN: cpptraj `resinfo :Cl-` selects residues 7–8 in `ions_old.prmtop`. sander `:Cl-` matches 2 atoms. ambmask `:Cl-` gives `:6-7`. | RUN |
| A0.5 | **`@/H` (select by element) works in cpptraj but is a syntax error in sander.** | RUN (`mix.prmtop`): cpptraj `atominfo @/H` gives `433 atoms selected.` sander exits 1 with `Error in group input::atommask.f::tokenize` / `illegal symbol in maskstr:/`. | RUN |
| A0.6 | **The manual's "entire protein backbone" mask also selects every water oxygen and calcium ion** in a solvated system. | Manual §25.1 (p.509): *"@CA,C,O,N,H = all atoms with names CA or C or O or N or H (i.e., the entire protein backbone)"*. RUN (`mix.prmtop`: 4-residue peptide, 208 OPC waters, Ca2+, Hg2+, Cl-): `@CA,C,O,N,H` selects 224 atoms in both sander and cpptraj. `:1-4@CA,C,O,N,H` selects 15. | READ + RUN |
| A0.7 | **`@H=` (names starting with H) also catches the mercury ion `HG`.** `!@H=` ("heavy atoms") keeps OPC/TIP4P-Ew extra points `EPW`, which are massless and not atoms in the chemical sense. | RUN (`mix.prmtop`): `@H=` gives 434 in sander and cpptraj, while element-based `@/H` gives 433 in cpptraj. The difference is the `HG` ion. `@EPW` gives 208 (one per OPC water). | RUN |

## A1. Ions

**Two names for Na+, K+ and Cl-.** `atomic_ions.lib` (AmberTools 24) defines both PDB-style and
old-style units. The residue name and the atom name are the same string in every unit. RUN
(my OFF parser, `$S/offdump.py`, on `$L/lib/atomic_ions.lib`):

| Ion | Unit = residue = atom name | Atom type |
|---|---|---|
| sodium | `NA` and `Na+` | `Na+` |
| potassium | `K` and `K+` | `K+` |
| chloride | `CL` and `Cl-` | `Cl-` |
| magnesium | `MG` | `Mg2+` |
| calcium | `CA` | `Ca2+` |
| zinc | `ZN` | `Zn2+` |
| others | `BR`, `F`, `IOD` (atom `I`), `LI`, `RB`, `CS`, `CU` (Cu2+), `CU1` (atom `CU`, Cu+), `FE` (Fe3+), `FE2`, `HG`, `NH4` (atom `N`), `H3O+` (atom `O`), … 67 units in all | |

- READ `$L/lib/atomic_ions.cmd`, header: *"Monoatomic ions using PDB-standard atom & residue names where applicable; for Na+, K+ and Cl-, also add units with the older Amber names, for backwards compatibility. But people should be moving to the PDB standard nomenclature"*.
- READ `$L/lib/ions94.lib` (the old scheme): units `Na+`, `Cl-`, `K+`, `Li+`, `Rb+`, `Cs+`, `MG2` (atom `MG`), `CIO`, `IB`.
- **Which name ends up in the prmtop depends on what the user typed** in `addIons`/`addIons2`. RUN (`$S/leaptest/t3.in`): `addIons2 s1 Na+ 2; addIons2 s1 Cl- 2` gives prmtop residues `Na+ Na+ Cl- Cl-`. `addIons2 s2 NA 2; … CL 2; … K+ 1; … K 1` gives `NA NA CL CL K+ K`, so one system can mix both styles. A PDB with residues `NA`, `CL`, `ZN`, `MG` loads as `NA CL ZN MG` (t2).
- **Placement in the residue order.** RUN: ions added by `addIons2` come right after the solute and before all waters (t3: residues 5–10 are ions, then 296 `WAT`).
- **History.** READ AmberTools12 manual p.50: *"ions08.lib topologies for ions with the new naming scheme / ions94.lib topologies for ions with the old naming scheme"*. Same page: *"Most leaprc files still load the 'old' ion parameters; to use the newer versions, you will need to load the ions08.lib file"*. READ Amber14 manual p.45: *"atomic_ions.lib topologies for monoatomic ions (new naming scheme) / ions94.lib … old naming scheme"*. Amber26 p.59 has the same two lines. READ local `$L/cmd/oldff/leaprc.ff99SB` line 97: `loadOff ions94.lib`. `$L/cmd/oldff/leaprc.ff14SB` line 110: `loadOff atomic_ions.lib`. **Conclusion:** systems built with ff99SB-era leaprc files had only `Na+`/`Cl-`/`K+`. From Amber14 on, both spellings are available. ions08.lib's unit list is not in the local install, so I could not check it.
- **Current water leaprcs load atomic_ions.lib.** READ `$L/cmd/leaprc.water.tip3p`: `loadOff atomic_ions.lib`, `loadOff solvents.lib`. The same holds for opc, spce, tip4pew and opc3.
- **CHARMM names.** READ https://raw.githubusercontent.com/openmm/openmmforcefields/main/charmm/tests/toppar/toppar_water_ions.str (a mirror of CHARMM `toppar_water_ions.str`): `RESI SOD 1.00 ! Sodium Ion` / `ATOM SOD SOD`; `RESI POT … ! Potassium Ion`; `RESI CLA -1.00 ! Chloride Ion`; `RESI CAL 2.00 ! Calcium Ion`; `RESI MG`; `RESI ZN2 … ATOM ZN`; `RESI LIT`, `RUB`, `CES`, `BAR`, `CD2`.
- **CHARMM to AMBER, as AmberTools converts it.** READ `/opt/homebrew/Caskroom/miniforge/base/envs/prime-amber/dat/charmmlipid2amber/charmmlipid2amber.csv` (v2.0.5): `SOD` → `Na+`, `CLA` → `Cl-`, `POT` → `K+`, `CAL` → `CA`, `MG` → `MG`, `TIP3` (`OH2`) → `WAT` (`O`). The converter writes the **old** `Na+`/`Cl-`/`K+` names.
- **packmol-memgen default salt** is also old-style. READ `…/site-packages/packmol_memgen/main.py:139-140`: `--salt_c default="K+"`, `--salt_a default="Cl-"`.
- **GROMACS names.** READ https://raw.githubusercontent.com/gromacs/gromacs/main/share/top/amber99sb-ildn.ff/ions.itp: moleculetypes `NA`, `CL`, `K`, `MG`, `CA`, `ZN`, `LI`, `RB`, `CS`, residue = atom name. READ …/charmm27.ff/ions.itp: residue `NA` with atom type `SOD`, `K`/`POT`, `CA`/`CAL`, `CL`/`CLA`. So GROMACS-CHARMM uses CHARMM *types* but PDB-style *residue names*.
- **PDB names.** READ https://files.rcsb.org/ligands/download/NA.cif: `_chem_comp.id NA`, name "SODIUM ION", atom `NA`, charge 1. CL.cif: `CL` "CHLORIDE ION". K.cif: `K`. MG.cif: `MG`. ZN.cif: `ZN`. CA.cif: `CA` "CALCIUM ION", atom `CA`.

## A2. Water

- **Every tleap water model gets residue name `WAT`.** READ manual §3.7 (p.55–56): *"By default, the residue name in the prmtop file will be WAT, regardless of which water model is used."* READ `$L/lib/solvents.lib` (parsed): units `TP3`, `TP4`, `TP5`, `T4E`, `OPC`, `OP3`, `O3P`, `SPC`, `SPF`, `SPG`, `FB3`, `FB4`, `PL3`, `TPF`, `DC4`, plus `$L/lib/tip4pd.off` `T4D`. Every one has residue `WAT`. RUN: a PDB containing `HOH` loads to prmtop `WAT` under tip3p, opc, tip4pew, spce and opc3 (t2).
- **How the mapping works.** READ `$L/cmd/leaprc.water.tip3p`: `HOH = TP3` / `WAT = TP3`. The other leaprcs: `HOH = OPC` / `WAT = OPC` (opc), `OP3` (opc3), `SPC` (spce and spceb), `T4E` (tip4pew), `FB3`/`FB4`, `T4D` (tip4pd), `O3P` (opc3pol). Manual p.55: *"There is no default, but TIP3P will be used for residues with names HOH or WAT"*. That sentence holds only after `leaprc.water.tip3p` has been sourced.
- **Atom names** (RUN, parsed from `solvents.lib` and seen in the prmtops):

| Model | tleap unit | Atom names |
|---|---|---|
| TIP3P | TP3 | `O H1 H2` |
| SPC/E (and SPC/Eb) | SPC | `O H1 H2` |
| OPC3 | OP3 | `O H1 H2` |
| OPC | OPC | `O H1 H2 EPW` (RUN in prmtop) |
| TIP4P-Ew | T4E | `O H1 H2 EPW` (RUN in prmtop) |
| TIP4P, TIP4P-FB, TIP4P-D | TP4, FB4, T4D | `O H1 H2 EPW` |
| TIP5P | TP5 / TIP5PBOX | `O H1 H2 EP1 EP2` |
| OPC3-pol | O3P | `O H1 H2 Y1` |

  The local AmberTools 24 has no `leaprc.water.tip5p`. The TIP5P unit and box exist only in `solvents.lib`/`tip5pbox.off`.
- **Other programs.** PDB: `HOH`, atoms `O H1 H2` (READ https://files.rcsb.org/ligands/download/HOH.cif). CHARMM: `RESI TIP3`, atoms `OH2 H1 H2` (READ toppar_water_ions.str, lines 68–72). GROMACS: moleculetype/residue `SOL`, atoms `OW HW1 HW2`, plus `MW` for TIP4P-Ew (READ gromacs `amber99sb-ildn.ff/tip3p.itp` and `tip4pew.itp`).
- **What each tool treats as solvent.** cpptraj: *"by default residues named WAT, HOH, or TIP3"* (READ manual p.815, `closest`). ParmEd `defineSolvent`: *"By default, HOH and WAT residues are recognized as solvent"* (READ p.305). pdb4amber `-d` strips `parmed.residue.WATER_NAMES` = `HOH SPC SPCE SWM4 SWM6 TIP3 TIP4 TIP5 WAT` (RUN).
- **tleap moves crystal waters to the end.** RUN (t2, t3): the input PDB listed `HOH 101`, `HOH 102` before `NA 103`, `CL 104`, `ZN 105`, `MG 106`. Both the tleap PDB and the prmtop list `NA CL ZN MG` as residues 8–11 and `WAT WAT` as 12–13. Residue numbers from the original PDB therefore do not carry over to masks.

## A3. Protein residues (ff14SB / ff19SB)

- **Protonation and special residues.** READ `$L/lib/amino12.lib` and `amino19.lib` (28 units each): `ASH` (neutral Asp, extra `HD2`), `GLH` (neutral Glu, `HE2`), `LYN` (neutral Lys, no `HZ1`), `CYX` (disulfide Cys, no `HG`), `CYM` (deprotonated Cys), `HID` (`HD1` only), `HIE` (`HE2` only), `HIP` (both), and `HYP`. There is no `HIS` unit.
- **Plain HIS becomes HIE.** READ `$L/cmd/leaprc.protein.ff14SB` and `…ff19SB` (last lines): `NHIS = NHIE` / `HIS = HIE` / `CHIS = CHIE`, under the comment *"assume that most often proteins use HIE"*. Manual §13.2 (p.235): *"a "HIS" residue in a PDB file will be translated automatically to HIE"*. RUN: `sequence {NALA HIS …}` and a PDB with `HIS` both give prmtop `HIE`. A HIS that carries an `HD1` hydrogen still maps to HIE and fails: `Created a new atom named: HD1 within residue: .R<HIE 6>` (t5 first attempt). That failure is why pdb4amber's renaming step matters (A6).
- **Disulfides.** Manual p.235: *"If the cysteine is known to be in a S-S bridge, the residue name in the PDB file must be "CYX" … S-S bonds to pairing cysteines are not automatically made but must be specified by the user."*
- **Neutral Asp/Glu/Lys.** Manual p.235: *"The residue names must then be changed to "ASH", "GLH", and "LYN"… A neutral form of arginine is not foreseen in AMBER."*
- **Terminal units.** READ `$L/lib/aminont12.lib` (`NALA`…`NVAL`, `NHID/NHIE/NHIP`, `NCYX`, `ACE`) and `aminoct12.lib` (`CALA`…`CVAL`, `CHYP`, `NME`, `NHE`). The N-terminal units carry `H1 H2 H3` instead of `H` (NPRO has `H2 H3`). The C-terminal units add `OXT`. Manual §14.4.2 (p.256): *"The N-terminal amino acid UNIT/RESIDUE names and aliases are prefaced by the letter N (e.g., NALA) and the C-terminal amino acids by the letter C (e.g., CALA)… The default for loading from PDB files is to use N- and C-terminal residues; this is established by the addPdbResMap command."*
- **The prmtop does not keep the N/C prefix.** RUN (t1): `sequence { NALA HIS CYS ASH GLH LYN CALA }` gives prmtop `RESIDUE_LABEL` `ALA HIE CYS ASH GLH LYN ALA`. tleap prints `Converting N-terminal residue name to PDB format: NALA -> ALA` and `… CALA -> ALA`. So `:NALA` selects nothing in the prmtop, and terminal residues are found by number or by `@H1,H2,H3` / `@OXT`. I checked only AmberTools 24 here; whether older tleap wrote `NALA` is UNVERIFIED.
- **Caps.** RUN/READ `aminont12.lib` `ACE` = `H1 CH3 H2 H3 C O`. `aminoct12.lib` `NME` = `N H C H1 H2 H3`. `NHE` = `N HN1 HN2`. Manual p.235–236: *"Note the atom name "CH3" for this special carbon"* (ACE), and for NME *"The atom name for the carbon must be "C", as in the CIF format."*
  - **These names changed.** READ old `$L/lib/all_aminoct94.lib` (ff94/ff99SB era): `NME` = `N H CH3 HH31 HH32 HH33`. `all_aminont94.lib`: `ACE` = `HH31 CH3 HH32 HH33 C O`. Old masks such as `:NME@CH3` select nothing under ff14SB/ff19SB. Under the new names, `@C` and `@C,CA,N` masks also catch the NME methyl carbon.
- Minor: `leaprc.protein.ff19SB` maps `{ 0 "HYP" "NHYP" }`, but `aminont12.lib` has no `NHYP` unit. ff14SB maps `{ 0 "HYP" "HYP" }` (READ both files).
- Manual §13.2 (p.235): *"PDB files written by LEaP will keep the "special" names, which sometimes leads to annoying effects in software packages which are not prepared for amino acids called HIE, HIP, CYX… You can also use the "-bres" option in ambpdb."*

## A4. Nucleic acids

- **Residue names.** READ `$L/lib/DNA.OL15.lib`, `ff-nucleic-OL21.lib`, `parmBSC1.lib` (16 units each): `DA DA5 DA3 DAN`, and likewise for `DC`, `DG`, `DT`. READ `$L/lib/RNA.lib` (OL3): `A A5 A3 AN`, likewise for `C`, `G`, `U`, plus `OHE`. Manual §14.4.3 (p.257): *"Residue names like "A" or "DA" can be followed by a "5" or "3" ("DA5", "DA3") for residues at the ends of chains; this is also the default established by addPdbResMap… The "5" and "3" residues are "capped" by a hydrogen; the plain and "3" residues include a "leading" phosphate group. Neutral residues (nucleosides) capped by hydrogens end their names with "N", as in "DAN"."*
- **The prmtop keeps the 5/3 suffix**, unlike proteins. RUN (t1): `DG5 DA DT DC3 G5 A U C3`. Consequences, RUN with cpptraj on `vac.prmtop`:
  - `:DG` gives `Selection is empty.` because the only G is the terminal `DG5`. `:DG*` selects it.
  - `:A*` selects `ACE`, three `ALA`, `ASH` and RNA `A`: 6 residues across protein and RNA.
  - The 5′ residue has no `P OP1 OP2` (the `DA5`/`DG5` atom list starts at `HO5'`), so `:12-15@P` gives 3 atoms for a 4-nucleotide strand.
- **PDB names they come from.** READ `$L/cmd/leaprc.DNA.OL15` (OL21 and bsc1 are identical): `{ 0 "DG" "DG5" } { 1 "DG" "DG3" }` and so on. PDB `DA/DC/DG/DT` map to `*5` at the 5′ end and `*3` at the 3′ end. Old names are accepted too: *"some really old Amber residue names, assuming DNA"* `GUA ADE CYT THY` → `DG DA DC DT`. READ `leaprc.RNA.OL3`: `{ 0 "G" "G5" } { 1 "G" "G3" }`, and *"some old Amber residue names for RNA"* `RA5 RA RA3` → `A5 A A3` (likewise `RC`, `RG`, `RU`).
- **Old residue and atom names.** READ `$L/lib/all_nucleic94.lib` (ff94/ff99 era) has RNA units `RA RA3 RA5 RAN RC… RG… RU…`. Its DNA `DA` atoms are `P O1P O2P O5' C5' H5'1 H5'2 …`. Current libraries use `OP1 OP2`, `H5' H5''`, `H2' H2''`. The leaprc `addPdbAtomMap` translates `O1P` → `OP1`, `H5'1` → `H5'`, `H2'2` → `H2''`, `O5*` → `O5'`, and so on, on PDB input only. A mask written with old names (`@O1P`) selects nothing in a current prmtop. Manual §3.2.3 (p.41): *"Nucleic acid residues use the new (version 3) PDB nomenclature: "DC" is used for deoxy-cytosine, and "C" for cytosine in RNA, etc. Earlier force fields (which are not recommended!) use "RC" for the RNA version."*
- Prime and double-prime atom names (`C1'`, `H2''`, `HO5'`) appear in masks. They need shell quoting but no mask escaping (I did not test escaping).
- The Amber26 manual recommends DNA **OL24** (`leaprc.DNA.OL24`, p.33). That file is **not** in the local AmberTools 24.8, so I could not check its residue names.
- Manual p.41: the LJbb RNA set uses *"the somewhat non-standard residue names AMP, GMP, UMP and CMP … to indicate 5' phosphorylation."*

## A5. Lipid21

- **One lipid is three residues: sn-1 tail, head group, sn-2 tail, followed by TER.** READ manual §3.6.1 (p.54–55): *"phospholipids are divided into interchangeable head group and tail group "residues.""* Table 3.10: *"Lipid 1: sn-1 tail residue / head group residue / sn-2 tail residue / TER card"*. Also: *"Each phospholipid molecule in LIPID21 is made up of three residues. Atoms from each residue must be in contiguous blocks and ordered as described."*
- **Residue names** (manual Table 3.9, p.54; units confirmed in `$L/lib/lipid21.lib`, RUN): tails `LAL` (12:0), `MY` (14:0), `PA` (16:0), `SA` (sphingosine), `OL` (18:1), `ST` (18:0), `AR` (20:4), `DHA` (22:6). Heads `PC`, `PE`, `PS`, `PGR`, `PGS`, `PH-`, `SPM`. Cholesterol `CHL` (one residue).
- **Concrete splits** (READ `charmmlipid2amber.csv`, residue order as converted): POPC → `PA PC OL`, DOPC → `OL PC OL`, POPE → `PA PE OL`, DPPC → `PA PC PA`, PSM → `PA SPM SA`, CHL1 → `CHL`. RUN: `sequence { PA PC OL }` gives prmtop residues `PA PC OL` (t1).
- **Consequences for masks.** A POPC is `:PA,PC,OL` across 3 consecutive residue numbers. The molecule operator `^` or a residue-triplet range is needed to select a whole lipid. Tail atom names repeat between residues: both `PA` and `OL` use `C12`, `C13`, …, so `@C12` hits both tails (RUN, cpptraj on `vac.prmtop`: `@C12` gives 2 atoms, in `20 PA` and `22 OL`). `:PA,OL` is "all tails", and `:PC` is the head group only, not the whole lipid. Head-group phosphorus is `P31` and nitrogen `N31` (READ `PC` unit), not `P`/`N`.
- Manual p.55: *"PDB formatted structure files with alternative residue and atom names (such as Charmm C36) may be converted to the LIPID21 naming convention by way of the script called charmmlipid2amber.py"*.

## A6. pdb4amber (1.6.dev, AmberTools 24)

`pdb4amber --help` (RUN) lists `-y` (remove H), `-d` (remove water), `-s STRIP_ATOM_MASK`,
`-p` (protein only), `-a`, `--constantph` (*"rename GLU,ASP,HIS for constant pH simulation"*),
`--reduce`, `--most-populous`, `--keep-altlocs`, `--add-missing-atoms`, `--model`, `-l`,
`--leap-template`, `--no-conect` and `--noter`.

Manual §13.4 (READ, p.237–238) versus what I observed (RUN on `$S/leaptest/p4a_in.pdb`: chain A residues 5, 6, 7, 7A, 8 with HIS variants; chain B residues 100–101; `HOH A301`, `HOH A302`; `NA A401`):

| Topic | Manual says | Observed (RUN) |
|---|---|---|
| Numbering | *"all residues sequentially re-numbered from 1 to N"* | Yes, across chains: A5→1 … A8→5, B100→6, B101→7, HOH→8, 9, NA→10. |
| Chain IDs | listed to screen | Kept in the output PDB (`A`, `B`). **tleap then drops them:** the prmtop has no RESIDUE_CHAINID flag, and the tleap-written PDB has no chain column (t5). So `::A` cannot work on a tleap prmtop. |
| Insertion codes | *"pdb4amber discards insertion codes and re-numbers all residues from 1 to N. But the insertions are listed to the screen and also included in the _renum.txt file."* | Output kept the code: `ATOM 45 CA HIP A 4A`. pdb4amber also wrote a `TER` between residue 3 and 4A, which made tleap treat 4A as a new N-terminus (`FATAL: Atom .R<NHIP 4>.A<H 21> does not have a type`). `_renum.txt` has **no** insertion-code column: both rows read `HIS A 7`. One synthetic file only; cause not traced. |
| Histidines | *"Any histidines whose protonation state can not be determined are renamd to HIE."* | HIS with `HD1` → `HID`; with `HD1`+`HE2` → `HIP`; with no ring H it **stays `HIS`**. Source `pdb4amber.py:assign_histidine` renames only when H atoms are present. tleap's `HIS = HIE` alias then makes it HIE (t5 prmtop: `ALA HID HIE HIP ALA ALA HID NA WAT WAT`). Same end result, different step. |
| Waters | `-d` writes `_water.pdb` | Without `-d`, waters stay `HOH` (tleap's alias renames them later). With `-d`, they are removed. |
| `_renum.txt` | *"a table to help convert the renumbered residues into the original ones"* | Format `%3s %1s %5s    %3s %5s` = name, chain, original number, name, new index (source `_write_renum`). It is written **before** HIS renaming and before `-d/-p/-s` stripping (`run()`, line ~520). So (a) its 4th column says `HIS` where the output says `HID`, and (b) **after `-d` it is stale**: `NA A 401 → 10` in renum, but `NA` is residue 8 in `p4a_dry.pdb`. |
| Other files | `_nonprot.pdb`, `_water.pdb` (with -d), `_sslink` | All produced (`p4a_out_nonprot.pdb`, `p4a_out_sslink`, `p4a_dry_water.pdb`). |

**The full renumbering chain for one atom** (RUN): original PDB `NA A 401` → pdb4amber residue 10
→ tleap prmtop residue **8**, because tleap moved the two waters after it. A mask written from
the original PDB (`:401`) or from pdb4amber's renum table (`:10`) selects the wrong residue
in the prmtop. The manual warns about atom numbers in general (§25.1, p.509): *"Do not use the
original atom numbers from the raw PDB file you started with."*

---

# Part B. Masks in published tutorials

**Where the entries come from.** Two delegated harvesting passes fetched the pages with curl
and recorded every mask with its URL, program/variable, verbatim string, the tutorial's own
description, and READ/LEAD. Both are included verbatim below:
- **B2**, ambermd.org plus the AMBER-hub pages it links: 105 entries, about 160 mask strings.
- **B3**, other public tutorials (Compute Canada, Rizzo lab wiki, York group, AMBER-hub, BioExcel, Singh, the Miao lab GaMD page, Ryde): 93 entries.

All ~200 entries are READ. None is LEAD-only. I re-fetched a sample (B1.2) and ran every open
syntax question through the local tools (B1.1).

**Contexts covered:**
- TI/FEP: `timask1/2`, `scmask1/2`, `crgmask`, `noshakemask`, ParmEd `tiMerge`, FEW, ACES/GTI
- MMPBSA.py and ante-MMPBSA.py (`receptor_mask`, `ligand_mask`, `strip_mask`, `-s/-m/-n`)
- pmemd/sander `restraintmask` in about 30 protocols
- cpptraj/ptraj: `rms`, `strip`, `center`, `autoimage`, `hbond`, `distance`, `pucker`, `dihedral`, `matrix`/`projection`, `cluster`, `atomicfluct`, `radial`, `diffusion`
- pytraj
- `qmmask`, NEB `tgtfitmask`/`tgtrmsmask`
- ParmEd `change`/`addLJType`/`add12_6_4`
- mdgx `&ipolq`/`&fitq`/`&configs`
- AmberFlow/AmberStudio keyword masks
- GaMD `timask`
- Lipid14/Lipid21, DNA, RNA, constant pH

Coverage gaps:
- **MMPBSA.py:** no ambermd.org tutorial sets `receptor_mask`/`ligand_mask`/`strip_mask`; it relies on MMPBSA.py's "Best guess" (B2 #20–21). The explicit examples are from Compute Canada and Singh (B3 #7–9, #84–88).
- **DISANG/NMR/umbrella restraint files** in the tutorials always use `iat=`/`igr=` atom numbers, never masks (B2 #70–78).

## B1.1 RUN verdicts on the syntax questions the harvest left open

Test topologies: `$S/leaptest/ions_old.prmtop` (ACE-ALA-ALA-NME, 2 `Na+`, 2 `Cl-`, 296 OPC `WAT`;
1220 atoms) and `mix.prmtop` (A0). Tools: sander 24.0 (the same restraintmask parser family as
pmemd; **pmemd itself was not run**), cpptraj V6.24.0, ParmEd 4.3.1, pytraj 2.0.6.

| Mask (tutorial form) | Where | sander | cpptraj | ParmEd | Verdict |
|---|---|---|---|---|---|
| `:1-4@CA.C.N` | Rizzo 4S0V/2P16/2ITO/1Y0X equil 08–09 (B3 #18, #30, #32, #34) | **fatal**, rc=1: `atom_namelist unknown symbol:.` | `Selection is empty.` | `MaskError … [.]` | Stops sander; silently empty in cpptraj. |
| `:WAT:Na+:Cl-` | Rizzo cpptraj `strip`; Singh `:CLA:SOD:TIP3` (B3 #21, #84–88) | **fatal**: `residue_namelist unknown symbol::` | 1188, same as `:WAT,Na+,Cl-` | 1188 | Works in cpptraj and ParmEd, which is the engine ante-MMPBSA.py calls (`parmed_commands = "strip %s nobox"`, local `ante-MMPBSA.py` l.113). Fatal in sander. |
| `:WAT@-O` | Rizzo hbond `solventacceptor` (B3 #24, #35) | 0 atoms, no error | `Selection is empty.` | 0 | **Silently empty**, so no water acceptors are counted. |
| `:!@H=` | Rizzo 3WZE/6ME2/1X70 `restraintmask` (B3 #26) | 611 = `!@H=` | **error**: `empty token for ':'` | `MaskError empty token` | Accepted by sander only. |
| `:1-4&!@H` vs `:1-4&!@H=` | York RMSF fit (B3 #64); GIST T25 (B2 #52) | 29 vs 15 | 29 vs 15 | — | `@H` = atoms named exactly H, so most hydrogens stay in. |
| `ALA@CA` (no leading `:`) | Ryde `scmask1="GU1@C8,…"` (B3 #91) | **fatal**: `elementary mask does not start with : or @` | error | `MaskError Bad syntax` | Invalid everywhere. |
| `:ALA,` (trailing comma) | Ryde `timask2=":GU2,"` (B3 #92) | 20 = `:ALA` | 20 | 20 | Harmless. |
| `@CA ` (trailing space) | York `'@CA '` (B3 #48, #50) | 2 = `@CA` | 2 | — | Harmless. |
| `:PROTEIN+LIPID`, `:PROTEIN` | Lipid21/PACKMOL-Memgen T38 runnable inputs (B2 #57–58) | **fatal**: `residue name should not have more than 4 chars` | `Selection is empty.` | — | An unedited input stops sander. |
| `!:WAT & !@H=` **unquoted on a cpptraj command line** | general | 19 | `atominfo`: **36** (mask cut at the first space); `strip`: error `Not all arguments handled: [ & !@H= ]` | — | cpptraj masks with spaces must be quoted. With quotes: 19. |
| `:1-4 and not hydrogen` (pytraj) | Compute Canada atomiccorr (B3 #14–15) | — | — | — | pytraj `top.select` → **0 atoms**. `pt.atomiccorr(..., byres=False)` gives a 32×32 matrix, the same as `:1-4`, so the clause is ignored and hydrogens are kept. |
| `@CA,C,O,N\|(:HEH,PRN)@FE,NA,NB,NC,ND,C3D,C2A,C3B,C2C,CA,CB` | cpHE T33 (B2 #50, F2) | **127** on the published `mp8_is.prmtop`, matching pmemd's published `mp8_is.min.mdout` line 126 | **error**: `Mask stack is not empty.` | `MaskError` (per B2) | Resolves B2's open F2. ambmask's listing is `:2@CA :5@CA :6@CA,CB :7@CA,CB :8@CA :9@CA :10@CA,CB :11@CA,CB :12@CA,CB :14-16`. That is all 113 heme/propionate atoms plus 14 protein CA/CB, the same set as `:HEH,PRN\|@FE,…,CA,CB` (127). **Backbone C, O and N are not restrained**, although the text says "restraint on backbone atoms". |

**ante-MMPBSA `-n` (B3 #8), resolved from source.** The help text says `-n` is the *"Amber mask
of atoms needed to be stripped from COMPLEX to create LIGAND"* (READ local
`/opt/homebrew/Caskroom/miniforge/base/envs/prime-amber/bin/ante-MMPBSA.py` l.32–34). The code
does the opposite (l.108–137): `Creating receptor topology file by stripping %s` … `% opt.ligand_mask`,
and `Creating ligand topology file by stripping %s` … `% opt.receptor_mask`. So `-n :1-243`
names the ligand, consistent with that page's `ligand_mask=:1-243`. **The help text is backwards,
and the tutorial copied it.**

## B1.2 Spot-checks of the delegated READ claims (I re-fetched these)

- Rizzo 4S0V, `…?title=2023_AMBER_tutorial_1_with_PDBID_4S0V&action=raw`:
  - lines 448 and 483: `restraintmask=":1-489@CA.C.N"`
  - line 613: `strip :WAT:Na+:Cl-`
  - line 690: `… solventacceptor :WAT@-O`

  Confirmed.
- T33 cpHE, https://ambermd.org/tutorials/advanced/tutorial33/files/mp8_is.min.mdout, line 126: `Mask @CA,C,O,N|(:HEH,PRN)@FE,…; matches   127 atoms` (NATOM 237). Confirmed, and reproduced by sander (above).
- T26 ASMD, published `files/ala.asmd.prmtop`, cpptraj: `@CA,C,N,O` gives 2965 atoms, `:WAT@O` gives 2922, `:1-12@CA,C,N,O` gives 43. Confirmed: the "backbone" restraint holds every water oxygen.
- T25 GIST: `files/Section1_out/equil-npt.out` line 48 reads `restraintmask='!:WAT & !@H',` and line 218 reads `Mask !:WAT & !@H; matches  3446 atoms`. The published input `files/Section1_in/md-eq-npt-10ns.in` line 17 reads `restraintmask="!:WAT  & !@H=",`. Confirmed: the input and output do not match.

## B1.3 Patterns across the ~200 entries (details and URLs in B2/B3)

1. **An unrestricted "backbone" mask also catches water.** `@CA,C,N,O` / `@CA,C,O,N` in explicit solvent: T26 ASMD (2922 water O, checked), BioExcel pH notebook (B3 #81), T33 explicit, and the manual's own `@CA,C,O,N,H` example (A0.6). Tutorials that drop O (`@CA,N,C`, T13) or restrict residues avoid it. "Backbone" is spelled at least 6 ways: `@CA,C,N`, `@CA,N,C`, `@CA,N,O`, `@C,N,O`, `@CA,C,O,N`, `@N,CA,C,O`, `@P,O3',O5',C3',C4',C5'`. Compute Canada uses three of them in one course.
2. **`@H` vs `@H=`.** GIST T25 (3446 vs 3675 atoms, from pmemd's own output) and the York RMSF fit. The opposite slip, "heavy atoms" with no H exclusion: aMD T22 `:1-58`, BioExcel `!:WAT,Cl-,Na+`.
3. **Residue numbers that do not fit the system:**
   - T27 hydroxyapatite: `:1-64` restrains 16 HAP plus 48 waters (checked by B2).
   - T43 "end-to-end" `:2@CA :8@CA` on a 10-Ala peptide.
   - AMBER-hub clustering: 575 vs 576.
   - Rizzo 6ME2/4qmz/1c87/1Y0X: the numbers clash within each page.
   - York AmberStudio: three different residue counts for one complex.
   - York pKa: residue 70 vs 78.
   - A Compute Canada PCA count of 234 assumes every residue has a P (A4 shows 5′ residues have none).
4. **A string one AMBER program accepts and another rejects** (B1.1): `:WAT:Na+:Cl-`, `:!@H=`, `(…)@…`, `@CA.C.N`, `:PROTEIN+LIPID`.
5. **Masks that silently select nothing:** `:WAT@-O`, `:NA` vs `:Na+` (A0.3), unquoted cpptraj masks, pytraj "and not hydrogen", `:DG` when only `DG5` exists (A4).
6. **The description contradicts the mask:**
   - T20 comment says "Adenine N7" on the `:G*,DG*@N7` line.
   - T17 titled "Phi/Psi" but restrains ω.
   - Rizzo `:1-490@CA` "including the ligand", though a GAFF ligand has no CA.
   - Rizzo explains `!@H=` as "restrain all the hydrogen atoms".
   - BioExcel "heavy atoms" with a mask that includes hydrogens.
   - T16 "tail residues" for `":PC | :OL"`.
7. **Look-alikes that are not ambmask:**
   - FEW `LFc@C14,H1` (B2 #18)
   - NAB `suppose` `::C*,N*,O*,P*` (B2 #105)
   - GROUP `RES 1 24` blocks (B2 #65–69)
   - DISANG `iat=` numbers
   - CHARMM-named masks `:SOD,CLA,TIP3` (B3 #75, valid syntax but force-field-specific names)
8. **Copy-paste hazards:** WordPress typographic quotes (`”:1-542″`, `‘:225’`, `''` turned into `”`) on the Singh and GaMD pages (B3 #84–90). Apostrophes inside atom names (`@C1'`, `O3'`; B2 #45, #100).
9. **Useful as positive controls** (counts printed by the tools themselves):
   - T39 ACES TI masks: 45/45/1/1/90 atoms.
   - T18 lysozyme `@CA,C,O,N`: 516.
   - T25 `!:WAT`: 3675.
   - AMBER-hub trpzip2 `:1-13&!@H=`: 116 of 220.
   - York `!@H= & !:MG,NA,CL,PB,ZN,MN,WAT`: 1459.
   - York `:L01`: 8.
   - York `:LIG`: 32.

---

---

# B2. ambermd.org tutorials (delegated harvest, included verbatim; headings demoted one level)

> Where an entry below says "not run", "unverified" or "I did not check", see B1.1 first. Several of those questions now have RUN verdicts: `@CA.C.N`, `:WAT:Na+:Cl-`, `:WAT@-O`, `:!@H=`, `!@H`, `GU1@…`, `:PROTEIN+LIPID`, pytraj "and not hydrogen", the cpHE 127-atom mask (F2), and the ante-MMPBSA `-n` direction (B3 #8).

## Part B: atom-selection masks in the published AMBER tutorials (ambermd.org)

Harvested 2026-10-02 from https://ambermd.org/tutorials/ (index), its topic pages (FreeEnergy.php, EnhancedSampling.php,
MembraneSystems.php, ChemicalReactions.php, Tools.php, deprecated.php) and every tutorial they link on ambermd.org, plus the
AMBER-hub (amberhub.chpc.utah.edu) cpptraj recipes and one GitHub tutorial that the ambermd.org index links to.
Pages and input files were fetched with curl. Tarballs were unpacked where the tutorial ships its inputs only that way.

**Status words.** READ = I saw the string on the fetched page or file. LEAD = search snippet only. Every entry below is READ;
the only LEAD material is listed under "Pages tried that failed / leads".

**Format.** The cells hold masks containing `|`, so a markdown table would mangle them. Each entry is a short block instead.
"Mask" is copied character for character, including quotes and doubled spaces. "Says" quotes the tutorial; "not stated"
means the tutorial gives no description. Anything after **Interp:** is my reading of AMBER mask syntax, not the tutorial's words.

**Checks against published topologies.** For five flags I evaluated the mask on the tutorial's own published prmtop with ParmEd 4.3.1
(`parmed.amber.AmberMask`, pip-installed into scratch). Where a tutorial publishes its mdout, I quote pmemd's own
"Mask ... matches N atoms" line. These are marked **Checked:**. ParmEd is one implementation of the mask language. The cpHE entry (#47)
shows ParmEd and pmemd can disagree.

Abbreviations: T9 = advanced/tutorial9 and so on. "dep." = listed on https://ambermd.org/tutorials/deprecated.php.

---

### 1. TI / FEP / relative free energy

**1.** URL: https://ambermd.org/tutorials/advanced/tutorial9/pages/run_TI.html (content shown in tutorial9/index.html#run_TI)
- Program/var: pmemd `timask1` / `timask2`
- Mask: `timask1 = ':1', timask2 = ':2',`
- Says: "Pmemd requires explicit definition of the TI regions and there are also two masks for the softcore atoms in each state."
  setup_pmemd.html: "The ligands will be placed at the beginning and leap will number these residues as 1 and 2."
- READ. Flag: none.

**2.** Same page. pmemd `scmask1`
- Mask: `scmask1=':1@H6'`
- Says: overview.html: "Disappearing or appearing atoms are treated in a special way with "softcore" potentials (SCA) ... (blue atom for benzene and green atoms for phenol...)"
- READ. Flag: none.

**3.** Same page. pmemd `scmask2`
- Mask: `scmask2=':2@O1,H6'`
- Says: as #2. Benzene H6 is replaced by phenol O1/H6.
- READ. Flag: none.

**4.** Same page. pmemd `crgmask` (vdW+bonded step)
- Mask: `crgmask=':1@H6 | :2@O1,H6'`
- Says: "The charge mask is the union of each individual ligand charge mask."
- READ. Flag: none.

**5.** Same page. sander `scmask` / `crgmask`, initial state
- Mask: `scmask=':1@H6', crgmask=':1@H6'`
- Says: "Sander has no concept of TI regions ... The input for the first process (initial state) is"
- READ. Flag: none.

**6.** Same page. sander, final state
- Mask: `scmask=':1@O1,H6', crgmask=':1@O1,H6'`
- Says: "The input for the second process (final state) is"
- READ. Flag: none. Phenol is residue 1 in sander's own state-1 prmtop.

**7.** https://ambermd.org/tutorials/advanced/tutorial9/A9.tar.xz → `A9/ligand/pmemd/free_energy/setup.sh`. pmemd `crgmask` (decharge / recharge)
- Mask: `decharge_crg=":2@H6"` ; `recharge_crg=":1@O1,H6"` ; alternatives `#decharge_crg=":2"` `#vdw_crg=":1,2"` `#recharge_crg=":1"`
- Says: "# partial removal/addition of charges: softcore atoms only" and "# complete removal/addition of charges"
- READ. Flag: none.

**8.** A9.tar.xz → `A9/ligand/pmemd/setup/{ligands,complex}_prepare/min.in` (also heat.in, press.in, relres.in)
- Mask: `timask1 = ':BNZ', timask2 = ':PHN',` and `scmask1 = ':BNZ@H6', scmask2 = ':PHN@O1,H6'`
- Says: not stated. These are the residue-name form of #1–#3, used in the preparatory runs.
- READ. Flag: none.

**9.** A9.tar.xz → `A9/ligand/{pmemd,sander}/free_energy/heat.tmpl` (also every *_prepare/*.in). pmemd/sander `restraintmask`
- Mask: `restraintmask='!:WAT & !@H=',`
- Says: not stated. The tutorial text never mentions positional restraints.
- **Interp:** all non-water atoms whose names do not start with H. `1_leap.sh` runs `addions ligands Cl- 0` / `addions complex Cl- 0`,
  so any Cl- ions are restrained along with the solute.
- READ. Flag: none (no description to contradict).

**10.** A9.tar.xz → `A9/ligand/pmemd/setup/3_strip.sh`. cpptraj `strip`
- Mask: `strip ":1,2"` / `strip ":2-999999"` / `strip ":1,3-999999"`
- Says: "# remove the two ligands and keep the rest" / "# extract the first ligand" / "# extract the second ligand"
- READ. Flag: none. `999999` is used as an open-ended residue range.

**11.** A9.tar.xz → `A9/ligand/sander/setup/2_strip.sh`. cpptraj `strip`
- Mask: `strip ":1@H= | :2-999999"`
- Says: "# keep only first ligand without hydrogens"
- READ. Flag: none.

**12.** https://ambermd.org/tutorials/advanced/tutorial9/pages/sidechain_mini.html. ParmEd `tiMerge`
- Mask: `tiMerge :1-162 :163-324 :99 :261`
- Says: "The tiMerge commands uses the first two masks to mark the duplicated protein. The last two masks mark the mutated residue in
  each copy. The residue number 261 is due to the duplication (162 + 99 = 261)."
- READ. Flag: none (arithmetic consistent).

**13.** A9.tar.xz → `A9/sidechain/pmemd/free_energy/prod.tmpl` (also min.tmpl, heat.tmpl). pmemd `timask1/2`, `scmask1/2`
- Mask: `timask1 = ':99', timask2 = ':163',` and `scmask1 = ':99', scmask2 = ':163',`
- Says: "Please note, that the new residue number of the single valine changes and now is 163". Also "the whole residue will be
  transformed and thus all atoms of the residue are defined as softcore atoms."
- READ. Flag: none.

**14.** Same file. Commented "method 2" alternative
- Mask: `!scmask1 = '', scmask2 = ':163@HG=',` and `!noshakemask = ':99,163',`
- Says: "The mapping achieved through 1b_leap.sh is a single–topology description for all but the appearing atoms (the six Hγ atoms of
  valine)." The file comment: "!needed for method 2, also set dt=0.001".
- **Interp:** `@HG=` matches names starting with HG (HG11…HG23). That gives the six Hγ, which is consistent.
- READ. Flag: none (the sander copy is flagged in #15).

**15.** A9.tar.xz → `A9/sidechain/sander/free_energy/setup.sh` and `prod.tmpl` / `heat.tmpl`. sander
- Mask: `#scmask1 = '', scmask2 = ':163@HG=',` (setup.sh) ; `!noshakemask = ':99,163',` (prod.tmpl) ; active `scmask = '%M%',` with `%M%`→`:99` for both states
- Says: as #14.
- READ. **Flag F12.** The pmemd-only variable names and residue 163 were copied into the sander templates.

**16.** https://ambermd.org/tutorials/advanced/tutorial9/setup_old.html (original 2007 sander tutorial) + `prepare_example.bat`
- Mask: `crgmask=''` / `scmask=''` / `crgmask=':BNZ@H6'` / `scmask=':BNZ@H6'` / `crgmask=':PHN@O1,H6'` / `scmask=':PHN@O1,H6'` ;
  bat file: `mask0=''` `mask1=':BNZ@H6'`
- Says: step headings "(removing charge on BNZ H6)", "(changing BNZ into PHN)", "(Adding charges on PHN O1,H6)". Also
  "crgmask='XXX' a mask string to indicate that some atoms should have their atomic partial charges removed".
- READ. Flag: none. The empty mask `''` is a meaningful value here.

**17.** https://ambermd.org/tutorials/advanced/tutorial39/index.php (ACES / FE-Workflow) + `include/tutorial.mdout.tar.gz`. pmemd (GTI)
- Mask: `noshakemask     = '@1-90'` / `timask1         = '@1-45'` / `timask2         = '@46-90'` / `crgmask         = ""` /
  `scmask1         = '@41'` / `scmask2         = '@90'`
- Says: not stated what the atom ranges are. Nearby: "0.00000000_ti.nc for real state ligand 1h1q (resid :1), 1.00000000_ti.nc for
  real state ligand 1h1r (resid :2)."
- **Checked:** the published com and aq mdouts both print "TI Mask 1 @1-45; matches 45 atoms", "TI Mask 2 @46-90; matches 45 atoms",
  "SC Mask 1 @41; matches 1 atoms", "SC Mask 2 @90; matches 1 atoms", "Noshake mask @1-90; matches 90 atoms." Both ligand mol2 files
  in `include/initial.tar.xz` have 45 atoms.
- READ. Flag: none. Note the atom-number masks and that the empty crgmask uses double quotes while the others use single.

**18.** https://ambermd.org/tutorials/advanced/tutorial24/tiw.php + `files/TI_setup_L51c_d.in` (FEW). FEW `softcore_mask_v0/v1`
- Mask: `softcore_mask_v0            LFc@C14,H1` and `softcore_mask_v1            LFd@N3`
- Says: format "<lig_alias_v0>@<atom name list separated by comma>". Also "The softcore_mask's define the soft-core atoms, i.e. the atoms
  that shall be changed, "appear" or "disappear", i.e. are decoupled, upon transfer of ligand L51c into ligand L51d."
- READ. **Flag F13.** This is FEW's own format (no leading `:`), not an AMBER mask.

**19.** https://ambermd.org/tutorials/advanced/tutorial6/ (pKa by TI)
- No mask is used. The inputs use `icfe=1, clambda=...` with two separate topologies and no scmask/crgmask. Listed only for coverage.

### 2. MMPBSA.py

**20.** https://ambermd.org/tutorials/advanced/tutorial3/py_script/section1.php. MMPBSA.py (printed by the program, not user input)
- Mask: `|Best guess for receptor mask:   ":1-166"` / `|Best guess for  ligand  mask:   ":167-242"`
- Says: "In this setup we have defined RAS to be the receptor and RAF to be the ligand."
- READ. Flag: none. The tutorial's `mmpbsa.in` has **no** `receptor_mask` / `ligand_mask` / `strip_mask`. Every mmpbsa*.in in
  py_script/ relies on MMPBSA.py's guess. I found no ambermd.org tutorial that sets these variables explicitly.

**21.** https://ambermd.org/tutorials/advanced/tutorial3/py_script/section2.php (also section5.php)
- Mask: `|Best guess for receptor mask:   ":1-240"` / `|Best guess for  ligand  mask:   ":241"`
- Says: "the protein-ligand complex between the Estrogen Receptor protein and Raloxifene ligand."
- READ. Flag: none.

**22.** https://ambermd.org/tutorials/advanced/tutorial3/section1.php + `files/min.in`, `heat.in`, `density.in`. sander `restraintmask`
- Mask: `restraintmask=':1-242',`
- Says: "50ps of density equilibration with weak restraints on the complex". Ras is 1-166 and Raf 167-242 per #20.
- READ. Flag: none.

**23.** Same page + `files/measure_equil_rmsd.ptraj` (and `measure_prod_rmsd.ptraj`). ptraj/cpptraj `rms`
- Mask: `rms reference out equil.rmsd @CA,C,N`
- Says: "we will examine the protein backbone RMSD with respect to the minimized structure"
- READ. **Flag F14.** The script's reference is `reference ras-raf_solvated.inpcrd`, the LEaP starting coordinates, not the
  minimized structure. The mask itself matches "backbone" (N, CA, C).

### 3. cpptraj analysis

**24.** https://ambermd.org/tutorials/analysis/tutorial0/index.php. cpptraj `distance`
- Mask: `distance end-to-end :1 :13 out dist-end-to-end.agr`
- Says: "calculate a distance named end-to-end from the center of mass of residue 1 to residue 13"
- READ. Flag: none.

**25.** https://ambermd.org/tutorials/analysis/tutorial1/index.php + `rmsd1.in`, `rmsd2.in`. cpptraj `rms`
- Mask: `rms ToFirst :1-13&!@H= first out rmsd1.agr mass`
- Says: "using all non-hydrogen atoms in residues 1 to 13". The echo reads "Mask [:1-13&!@H*] corresponds to 116 atoms."
- READ. Flag: none. cpptraj echoes `H=` back as `H*`, so the two wildcard spellings are synonyms.

**26.** Same page + `rmsd3.in`. cpptraj `rms` with separate target/reference masks
- Mask: `rms ToGB1 ref [GB1] :1-12@CA :42-47,50-55@CA out rmsd3.agr`
- Says: "residues 1 to 6 and 7 to 12 of trpzip2 overlap with residues 42 to 47 and 50 to 55 of GB1" ... "we will only use alpha carbons".
  Both masks echo as 12 atoms.
- READ. Flag: none.

**27.** https://ambermd.org/tutorials/basic/tutorial0/index.php + `include/rmsd.cpptraj`. cpptraj `rms`
- Mask: `rms reference mass out 02_03.rms time 2.0 :2`
- Says: "Specifically, we will analyze the alanine atoms (residue 2)."
- READ. Flag: none.

**28.** Same page, explanation table. cpptraj `center` / `image`
- Mask: `center :1-3 mass origin` / `image origin center`
- Says: "Center the residues 1-3 by mass to the system origin" / "Image the atoms to the origin using the center of mass of the molecule"
- READ. **Flag F15.** Neither command is in the script the page shows or links. That script uses `autoimage`.

**29.** https://ambermd.org/tutorials/advanced/tutorial41/index.php + `include/ALL.in` (MAD2 PCA). cpptraj
- Mask: `autoimage anchor @CA` / `rms first @N,C,CA` / `average @N,C,CA crdset trajaverage` / `crdaction trajectory matrix covar name covmatrix @N,C,CA` /
  `nmwizmask @N,C,CA` / `trajoutmask @N,C,CA`
- Says: not stated ("PCA was performed using this input file").
- **Interp:** `autoimage anchor @CA` anchors imaging on the CA atoms. The PCA atom set is backbone N, C, CA with no residue restriction.
- READ. Flag: none.

**30.** https://ambermd.org/tutorials/advanced/tutorial43/index.php (T-REMD analysis). cpptraj `distance`
- Mask: `distance d1 out dist.ensemble.dat :2@CA :8@CA` (also `dist.replicas.dat`)
- Says: "calculating end-to-end distances for replica trajectories and temperature trajectories". The system, per
  https://ambermd.org/tutorials/advanced/tutorial42/index.php, is "m = sequence { ACE ALA ALA ALA ALA ALA ALA ALA ALA ALA ALA NHE }".
- READ. **Flag F6.**

**31.** https://ambermd.org/tutorials/advanced/tutorial15/Tutorial2.php (ionic liquid). ptraj `radial`
- Mask: `radial CH3CN_N1 .1 15.0 :ACN@N`
- Says: "We will be calculating the RDF between the N1 atoms of the Acetonitrile [CH3CN]" ... ":ACN@N is the mask for selecting atoms
  we want to use for our analysis."
- READ. Flag (minor, F16): in the tutorial's own `acn.mol2` the nitrogen's **name** is `N` and its GAFF **type** is `n1`. The mask is
  right; the prose "N1 atoms" mixes up name and type.

**32.** Same page. ptraj `diffusion`
- Mask: `diffusion mask timestep average`, with `mask` → `":ACN"` or `":*"`
- Says: "if you want to calculate D for acetonitrile, replace "mask" with ":ACN". To calculate D for all residues (which is what this
  tutorial does), use ":*"."
- READ. Flag: none. (Template placeholder in the command.)

**33.** https://ambermd.org/tutorials/basic/tutorial24/index.php (GBION, DNA) + `include/Dickerson_Drew_Dodecamer_files/cpptraj.in`. cpptraj `rms`
- Mask: `rms ToFirst :1-24&!@H= out rms_dna.txt`
- Says: "Use CPPTRAJ to compute RMSD of DNA heavy atoms over the production trajectory."
- READ. Flag: none (12-bp duplex = 24 residues).

**34.** https://amberhub.chpc.utah.edu/hydrogen-bond-analysis-within-a-protein/ (AMBER-hub, linked from the ambermd.org index as 4.5). cpptraj `hbond`
- Mask: `hbond All out All.hbvtime.dat solventdonor :WAT solventacceptor :WAT@O \`
- Says: "track all solute-solute and solute-solvent hydrogen bonds (all solvent residues are named WAT, the Amber default)"
- READ. Flag: none.

**35.** Same page. cpptraj `hbond`
- Mask: `hbond Backbone :1-12@C,O,N,H avgout BB.avg.dat series uuseries bbhbond.gnu`
- Says: "we will provide a mask so that only C, O, N, and H atoms will be considered as potential donors/acceptors."
- READ. Flag: none.

**36.** Same page. cpptraj `rms`
- Mask: `rms BBrmsd :1-12@C,CA,N out BBrmsd.agr`
- Says: "calculate backbone RMSD to the first frame as a means to track unfolding"
- READ. Flag: none. Backbone here is C, CA, N; the hbond mask in #35 uses C, O, N, H.

**37.** https://amberhub.chpc.utah.edu/introduction-to-principal-component-analysis/ (linked as 4.3). cpptraj `rms` / `matrix` / `projection`
- Mask: `rms first :1-36&!@H=` (same mask in `crdaction ... rms`, `matrix covar`, `nmwizmask`, `projection`, `trajoutmask`)
- Says: "RMS fitting to the first frame using all atoms of the DNA (residues 1-36) except the hydrogen atoms." Also "It is also
  necessary that the same atom mask that was used to generate the matrix is used for projection."
- READ. Flag: none. The page calls the system a "36-mer double stranded DNA, d(GCACGAACGAACGAACGC)". That is an 18-nt sequence, so
  36 residues across two strands. The mask fits; "36-mer" is loose wording.

**38.** Same page. cpptraj `parmstrip`
- Mask: `parmstrip !(:1-36&!@H=)`
- Says: not stated separately.
- **Interp:** removes everything except DNA heavy atoms, so the topology matches the PCA atom set.
- READ. Flag: none.

**39.** https://amberhub.chpc.utah.edu/clustering-a-protein-trajectory/ (linked as 4.4). cpptraj `strip`
- Mask: `strip :Na+,Cl-`
- Says: "Will delete the ions that are present in both the topology and the trajectory data."
- READ. Flag: none.

**40.** Same page. cpptraj `cluster ... rms`
- Mask: `rms :1-576@C,N,O,CA,CB&!@H= \`
- Says: "Use the RMSD of residues 1 to 576 and only using atoms C, N, O, CA and CB as distance metric, do not consider hydrogens." Later:
  "the Kdist analysis will be performed in residues 1 to 575, only considering the atom types C, N, O, CA and CB". System: "the 575
  amino acid tyrosine phosphatase ... We have included an inhibitor in the active site".
- READ. **Flag F7.**

**41.** Same page, "Tip!" loop. cpptraj `cluster`
- Mask: `cluster C$N kmeans :1-576@N,CA,C,O out clusters $N ...`
- Says: not stated.
- READ. Flag: part of F7. This metric drops CB and is not the mask used in the main runs.

**42.** https://amberhub.chpc.utah.edu/analisis-of-nucleic-acid-simulation/ (linked from ambermd.org deprecated.php). sander/pmemd `restraintmask`
- Mask: `restraintmask=':1-24',`
- Says: "Minimzing the system with 25 kcal/mol restraints on DNA". The system is the "Drew-Dickerson dodecamer" d(CGCGAATTCGCG), 12 bp.
- READ. Flag: none.

**43.** Same page. cpptraj `strip`
- Mask: `strip :WAT`
- Says: "Strip all residues with the name 'WAT' (delete the water molecules)"
- READ. Flag: none.

**44.** Same page. cpptraj `rmsd`
- Mask: `rmsd notail first :3-10,15-22&!@H= \`
- Says: "Measure the residues 3 through 10 and 15 to 22, but only the atoms that are not H." Also "around 3.5 and 4.5 for the central base pairs".
- READ. Flag: none. **Interp:** strand 2 is 13-24, so 3↔22 and 10↔15 pair. The mask drops two terminal pairs at each end, as described.

**45.** Same page. cpptraj `pucker`
- Mask: `pucker pucker5 :5@C1' :5@C2' :5@C3' :5@C4' :5@O4' \` (likewise residues 6–8)
- Says: "The pucker commands measure the pseudo-pucker rotation around the atoms C1′ through O4′ of residue 5."
- READ. Flag: none. The atom names contain an apostrophe, so any tokenizer must not treat `'` as a quote.

### 4. Positional restraints (`restraintmask`, `ntr=1`) in sander/pmemd

**46.** https://ambermd.org/tutorials/basic/tutorial13/index.php (Relaxation of Explicit Water Systems). pmemd `restraintmask`
- Mask: `restraintmask = ':1-81'` (also `restraintmask=':1-81'`)
- Says: "restraintmask = ':1-81'  Restrain the solute - protein (res 1-81)."
- **Checked:** RESIDUE_LABEL in the published https://ambermd.org/tutorials/basic/tutorial7/include/RAMP1_ion.prmtop gives residues
  1–81 as protein (1 CYX … 81 SER). Residue 82 onward is Na+/Cl-/WAT.
- READ. Flag: none.

**47.** Same page. pmemd `restraintmask`
- Mask: `restraintmask="@CA,N,C"` (also `restraintmask = "@CA,N,C"`)
- Says: "This string specifies that alpha C, N, and carbons are all restrained." Also "Minimization of the system with restraints only
  on the backbone of the protein."
- READ. Flag: none. **Interp:** no O, so OPC water atoms (O, H1, H2, EPW) are not matched.

**48.** https://ambermd.org/tutorials/basic/tutorial15/index.php (Relaxation of Implicit Solvent System, GB). sander/pmemd `restraintmask`
- Mask: `restraintmask="@CA,N,C,O",`
- Says: input title "heating with backbone restraints". Prose: "Along with the heating, this job script also inputs the thermostat
  options and water restraint." Later: "the specified atoms (CA, N, C, and O’’)".
- READ. **Flag F11 (minor).** This is an implicit-solvent run (igb=8, no water); "water restraint" is a text slip. Compare
  basic/tutorial13 (#47), whose backbone omits O.

**49.** https://ambermd.org/tutorials/advanced/tutorial18/section2.php (Constant pH, lysozyme, GB). sander `restraintmask`
- Mask: `restraintmask = '@CA,C,O,N' ! Restraints on the backbone atoms only` (heat: `restraintmask='@CA,C,O,N',`)
- Says: "Restraints on the backbone atoms only"
- **Checked:** published `files/4LYT.min.mdout`: "Mask @CA,C,O,N; matches   516 atoms" (NATOM 1997). 129 residues × 4 = 516; implicit solvent, no water.
- READ. Flag: none.

**50.** https://ambermd.org/tutorials/advanced/tutorial33/Section2.php (Constant pH and redox, implicit and explicit) + `files/*.mdin`
- Mask: `restraintmask='@CA,C,O,N|(:HEH,PRN)@FE,NA,NB,NC,ND,C3D,C2A,C3B,C2C,CA,CB',`
- Says: "we will minimize the system applying restraint on backbone atoms and on some heme atoms". Heating: "We keep the restraints on
  the backbone atoms".
- **Checked:** see Flag F2. The published mdouts say pmemd matched 127 atoms. ParmEd 4.3.1 rejects the string. Read with standard
  precedence, `@CA,C,O,N` alone picks up all 2388 water oxygens in the explicit system.
- READ. **Flag F2.**

**51.** https://ambermd.org/tutorials/advanced/tutorial25/section1.php (GIST, factor Xa) + `files/Section1_in/min_sys-1.in`, `md-eq-nvt-5ns.in`
- Mask: `restraintmask='!:WAT',` (min_sys-1) and `restraintmask="!:WAT",` (md-eq-nvt-5ns)
- Says: "Minimize only the water while restraining the protein" / "Relax the system, restraining all atoms in the protein (NVT, 300K, 5ns)"
- **Checked:** published `Section1_out/equil-nvt.out`: "Mask !:WAT; matches 3675 atoms" (NATOM 30021). The page says the system has
  "no ions".
- READ. Flag: none.

**52.** Same tutorial: `min_sys-2.in`, `md-heat-50K.in`, `md-heat-300K.in`, and section2.php production `md-nvt-30ns.in`
- Mask: `restraintmask='!:WAT & !@H',`
- Says: "Minimize the water and the protein hydrogen atoms" ; "Heat the system to 50K while restraining the protein heavy atoms" ;
  "since we will be restraining all heavy atoms during the production simulation" ; "our example simulation is performed with strong
  heavy atom restraints of 100 kcal/Å^2".
- **Checked:** published mdouts (min2.out, heat1.out, heat2.out): "Mask !:WAT & !@H; matches 3446 atoms". `!:WAT` matches 3675
  (#51), so only 229 atoms were released.
- READ. **Flag F1.**

**53.** Same tutorial: `md-eq-npt-10ns.in` (section1.php)
- Mask: `restraintmask="!:WAT  & !@H=",` (two spaces before `&`)
- Says: "Relax the system, restraining the protein heavy atoms (NPT, 300K, 10ns)"
- **Checked:** the published output for this stage (`Section1_out/equil-npt.out`) echoes `restraintmask='!:WAT & !@H',` with
  `cut = 9.0`, and reports "Mask !:WAT & !@H; matches 3446 atoms". The published input has `!@H=` and `cut = 10.0`.
- READ. **Flag F1** (the input/output pair does not match).

**54.** https://ambermd.org/tutorials/advanced/tutorial26/section1.php (ASMD, deca-alanine) + `files/min1.in`. sander/pmemd `restraintmask`
- Mask: `restraintmask="!(:WAT)",`
- Says: "First minimize the waters and then minimize the entire system." Input title "Minimize solvent".
- READ. Flag: none.

**55.** Same page + `files/heat.mdin`, `density.mdin`
- Mask: `restraintmask=':1-12',` (heat) and `restraintmask=":1-12",` (density)
- Says: not stated. System: "a helical peptide deca-alanine ... with different end caps( ACE and NH2)".
- **Checked (ParmEd on published `files/ala.asmd.prmtop`):** `:1-12` = 109 atoms = ACE + 10 ALA + NHE, identical to `!(:WAT)`.
- READ. Flag: none.

**56.** Same page + `files/equil1.mdin`…`equil3.mdin`
- Mask: `restraintmask='@CA,C,N,O',`
- Says: "The restraints of the backbone atoms "C,CA,N,O" are reduced from 10 to 0". Inputs are titled "MD1 simulation backbone restrained".
- **Checked (ParmEd on published `ala.asmd.prmtop`, TIP3P box):** 2965 atoms = ACE 2 + ALA 40 + NHE 1 + **WAT 2922**.
- READ. **Flag F3.**

**57.** https://ambermd.org/tutorials/advanced/tutorial38/equi_input.php (PACKMOL-Memgen / Lipid21) + `equi_inputs/01_min_water_primary.in`, `02_...`
- Mask: `restraintmask = ':PROTEIN+LIPID',`
- Says: "you have to make sure to replace the restraining mask for the proper residue span in the system you generated. For example, if
  you have a system with a protein of 100 residues, and you have 70 lipids per leaflet, you will have to replace :PROTEIN+LIPID for the
  corresponding mask that selects all of them (considering that each lipid has 3 "residues", and we have 2 leaflets, the selection will
  probably be :1-520)."
- READ. **Flag F10.** It is an explicit placeholder. The worked example is consistent (100 + 70·2·3 = 520).

**58.** Same page + `03_min_primary.in` / `04_min_secondary.in`, `06_nvt_initial.in`, `07_npt_initial.in`
- Mask: `restraintmask = ':PROTEIN+LIGAND',` and `restraintmask = ':PROTEIN',`
- Says: "Membrane minimization, (restraining the protein and ligand residues, if present, with 5 kcal mol-1Å-2)" / "(restraining the
  protein residues, if present, ...)" / "with restraints on the protein, and optionally on the membrane".
- READ. **Flag F10** (placeholders).

**59.** https://ambermd.org/tutorials/advanced/tutorial27/pro_metal.php + `files/pro_metal_min.in`, `_heat.in`, `_prod.in`. sander `restraintmask`
- Mask: `restraintmask=':10-2057',`
- Says: "In order to prevent the Ag cluster fall into pieces, during these modelings we will restrained the positions of the Ag cluster
  by the harmonic potentials."
- **Checked (ParmEd on published `files/pro_metal.prmtop`):** `:10-2057` = exactly 2048 `Ag0` atoms. `:1-9` = ACE-ALA7-NME.
- READ. Flag: none.

**60.** https://ambermd.org/tutorials/advanced/tutorial27/hap_water.php + `files/hap16_water_min1.in`. pmemd `restraintmask`
- Mask: `restraintmask=':1-64',`
- Says: step list "minimization of water, full minimization, heating, and production". Build: "PropPDB -p hap.pdb -o hap16.pdb -ix 4 -iy 4 -iz 1".
- **Checked (ParmEd on published `files/hap16_water.prmtop`):** `:1-64` = 848 atoms = **HAP 704 + WAT 144**. `:1-16` = `:HAP` = 704.
- READ. **Flag F4.**

**61.** https://ambermd.org/tutorials/advanced/tutorial28/Part1.php (mdgx IPolQ, glycerol) + `min.in`, `equil.in`
- Mask: `restraintmask = ':1',`
- Says: "the key aspects are that ntr = 1, that restraintmask = ':1', and that restraint_wt be set to some significant value (in this case 100.0 kcal/mol-Å2)."
- READ. Flag: none (glycerol is residue 1).

**62.** https://ambermd.org/tutorials/advanced/tutorial20/m1264.php + `files/m1264/md_min1.in`
- Mask: `restraintmask='!:WAT',`
- Says: not stated.
- READ. Flag: none.

**63.** dep. https://ambermd.org/tutorials/advanced/tutorial22/section1.php (aMD, BPTI) + `files/min_wat.in`, `md_wat.in`
- Mask: `restraintmask="!:WAT",`
- Says: "Minimize only the water, restraining the protein (20000 cycles)" / "Let water move (NTP, 300K), restraining the protein"
- READ. Flag (minor, F17). **Interp:** the build runs `addions2 mol Cl- 6`, so `!:WAT` also restrains the 6 Cl- ions, not only the protein.

**64.** dep. Same page + `files/heat.in`, `density.in`
- Mask: `ntc=2,restraintmask=':1-58',` and `ntr=1, restraintmask=':1-58',`
- Says: "Heat the system, restraining the protein (NVT 0 to 300K)" and "Relax the system, restraining the protein heavy atoms (NPT, 300K, 0.5ns)"
- READ. **Flag F9.**

### 5. GROUP-style restraint input (residue ranges, not masks)

**65.** https://ambermd.org/tutorials/advanced/tutorial21/section2.php (binding enthalpy, CB7/B2)
- Mask: `Hold the Guest (B2) Fixed` / `100.0` / `RES 1` / `END` / `END` ; and `RES 1 2` under "Hold the Host (CB7) and Guest (B2) Fixed"
- Says: the titles quoted.
- READ. Flag: none. This uses GROUP syntax (`RES first [last]`), not an ambmask.

**66.** https://ambermd.org/tutorials/basic/tutorial24/index.php (GBION) + `min.in`
- Mask: `RESTRAIN DNA` / `0.1` / `RES 1 24` / `END` / `END`
- Says: "RES 1 24 – specifying residues included into nucleosome, restraints will be applied to these residues."
- READ. Flag (minor, F17): the system is the 12-bp Dickerson–Drew dodecamer, not a nucleosome. The range itself (24 residues) is right.

**67.** dep. https://ambermd.org/tutorials/basic/tutorial1/section5.php (poly(A)-poly(T) DNA)
- Mask: `Hold the DNA fixed` / `500.0` / `RES 1 20` / `END` / `END` ; mdout echo `GRP    1 RES    1 TO    20`
- Says: "In the first stage we will keep the DNA fixed and just minimize the positions of the water and ions." Input title
  "polyA-polyT 10-mer: initial minimization solvent + ions".
- READ. Flag: none (10-mer duplex = 20 residues).

**68.** dep. https://ambermd.org/tutorials/advanced/tutorial16/index.php (Lipid14 DOPC) + `include/02_Heat.in`, `03_Heat2.in`
- Mask: `Hold lipid fixed` / `10.0` / `RES 1 384` / `END` / `END`
- Says: "DOPC lipid bilayer with 128 lipids". Also "three "residues": two tail groups and one head group".
- READ. Flag: none (128 × 3 = 384).

**69.** GitHub tutorial linked from ambermd.org index 7.6: https://github.com/callumjd/AMBER-Umbrella_COM_restraint_tutorial (`pulling/02_Heat.in`)
- Mask: `Hold lipid fixed` / `10.0` / `RES 1 217 `
- Says: the title "Hold lipid fixed".
- READ. Flag (minor, F17): residue 1 is the methanol (`igr1=1,2,3,4,5,6,`; the README centres the bilayer with `:2-217@N31`), so
  `RES 1 217` also holds the methanol.

### 6. Umbrella / NMR / SMD restraints (atom numbers via `iat`/`igr`, and masks used only to pick atoms)

**70.** https://ambermd.org/tutorials/advanced/tutorial17/section2.php + `files/disang.120`. sander DISANG
- Mask: `iat=9,15,17,19,` (atom numbers, no mask)
- Says: "Here the iat specifies the atom numbers forming the restraint, in this case 9, 15, 17 and 19." Also "we will be varying the angle
  of the C-N bond from 0 to 180 degrees". index.php: "a PMF for the trans to cis isomerization of alanine tripeptide". Every page title:
  "Calculating the PMF for Alanine Dipeptide Phi/Psi Rotation". section1: `mol = sequence { ACE ALA ALA NME }`.
- READ. **Flag F8.**

**71.** https://ambermd.org/tutorials/advanced/tutorial19/C7eq.restraints (EMIL; also alphaL/C7ax/alphaR.restraints)
- Mask: `iat(1)=5, !select four atoms for a torsional restraint` / `iat(2)=7,` / `iat(3)=9,` / `iat(4)=15,` ; second block `iat(1)=7` `9` `15` `17`
- Says: "!select four atoms for a torsional restraint". index.php: "Φ is defined by the sequence C-N-Cα-C, and Ψ is defined by N-Cα-C-N."
- READ. Flag: none. #74 confirms 5,7,9,15 = Φ and 7,9,15,17 = Ψ for ACE-ALA-NME.

**72.** https://ambermd.org/tutorials/advanced/tutorial29/APR_section2.php (APR). DISANG header and restraints
- Mask: `#AnchorAtoms :OCT@C11 :OCT@C23 :OCT@C51 :MOL@N1 :MOL@C6 #Type a ...` and `&rst iat= 200,13, r1=0.0000, ...`
- Says: APR_section1.php: "Those five atoms correspond to H1, H2, H3, G1 and G2 in the APR input file apr.in, respectively." Also "The
  Amber mask syntax (":" for residue selection and "@" for atom selection) will be used to indicate those atoms".
- READ. Flag: none. Masks name the anchors; the restraints sander reads use atom numbers.

**73.** https://ambermd.org/tutorials/advanced/tutorial29/APR_section1.php. zalign.py arguments
- Mask: `python2 zalign.py -f pdb/oa_cba.pdb -a1 :OCT@O3 -a2 :OCT@O7 -a3 :OCT@O8 -a4 :OCT@O11 -c :MOL@N1 -r 85`
- Says: "the three host atoms :OCT@O3, :OCT@O7 and :OCT@O8 are three host atoms that you think should lie in the same XY plane after the
  Z-axis alignment". Also "it sets the coordinates of atom G1 as the new origin, which is specified by -c flag."
- READ. Flag: none.

**74.** dep. https://ambermd.org/tutorials/advanced/tutorial22/section3.php. cpptraj `dihedral`, annotated with the iat equivalent
- Mask: `dihedral phi :1@C :2@N :2@CA :2@C out Phi_Psi` (comments `# 2 ALA PHI:  (1 ACE C)-(2 ALA N)-(2 ALA CA)-(2 ALA C)` and
  `#      dihedral iat 5,     7,     9,    15,`) ; `dihedral psi :2@N :2@CA :2@C :3@N out Phi_Psi` (comment `iat  7,     9,    15,    17`)
- Says: the comments quoted.
- READ. Flag: none. One line gives both the mask form and the atom-number form of the same dihedral.

**75.** https://ambermd.org/tutorials/advanced/tutorial26/section2.php (ASMD). sander SMD `iat`
- Mask: `iat=9,99,`
- Says: "The reaction coordinate is the end-to-end distance between the CA atoms of ALA1 and ALA10."
- **Checked (ParmEd on published `ala.asmd.prmtop`):** `@9` = CA of residue 2 (first ALA), `@99` = CA of residue 11 (last ALA).
- READ. Flag: none.

**76.** https://ambermd.org/tutorials/basic/tutorial24/index.php (GBION) + `disang.py`. COM restraints
- Mask: `igr1=588,545,209,186,166,153,140,139,134,108,igr2=808` with `iat=-1,-1`
- Says: "iat=-1,-1 - instructs AMBER to read igr1 and igr2 groups, then restrain their centers of mass." Also "igr1 - (set of 10 atoms) →
  DNA’s geometric center." and "igr2 - index of an ion."
- READ. Flag: none. `starting_index_of_ion= 759` + 50 ions → last ion is atom 808, consistent.

**77.** GitHub umbrella COM tutorial (linked from ambermd.org index 7.6), README "Step 4: Windows". cpptraj, plus DISANG `igr`
- Mask: `center mass origin :2-217@N31` ; `vector c0 :1 :1 out c0.out` ; `pulling/COM_pull.RST`: `igr1=1,2,3,4,5,6,` / `igr2=67,185,303,...,8445,`
- Says: "the bilayer center-of-mass, as defined by N31 head group atoms, is imaged to the origin". Also "the c0.out file which contains
  the postion of the methanol".
- READ. Flag: none. igr2 lists 72 atoms (67 + 118k) = one N31 per DMPC.

**78.** dep. https://ambermd.org/tutorials/advanced/tutorial4/index.php (NMR refinement of DNA) + `files/7col.dist`, `files/rst.dist`
- Mask: 7-column input `   1  GUA H1'      1  GUA H3'           4.6` → makeDIST_RST output `iat=  10,  27, r1= 1.30, ...`
- Says: "The program used to convert a 7-column file to the much less intuitive AMBER restraint file is makeDIST_RST."
- READ. Flag: none. The restraint is written as residue + name and compiled to atom numbers. There is no ambmask in DISANG files here.

### 7. ParmEd, mdgx, and other programs that take masks

**79.** https://ambermd.org/tutorials/advanced/tutorial20/12_6_4.php + `files/1264/parmed_1264_na.in` (Mg2+/DNA 1D23). ParmEd `change`
- Mask: `change AMBER_ATOM_TYPE :A*,DA*@N7 NAMG`
- Says: "#Change atom type of Adenine N7 atom to NAMG"
- READ. Flag (latent, F5b). **Interp:** `:A*` matches every residue name starting with A (ALA, ARG, ASN, ASP …). That is harmless in this
  DNA-only system and wrong if reused on a protein–nucleic acid complex.

**80.** Same file. ParmEd `change`
- Mask: `change AMBER_ATOM_TYPE :G*,DG*@N7 NGMG`
- Says: "#Change atom type of Adenine N7 atom to NGMG"
- READ. **Flag F5.**

**81.** Same file. ParmEd `change`
- Mask: `change AMBER_ATOM_TYPE :*@OP* OPMG`
- Says: "#Change atom type of backbone phosphate oxygen to OPMG"
- READ. Flag: none.

**82.** Same file. ParmEd `addLJType` (atom-type selector `@%`)
- Mask: `addLJType @%NAMG` / `addLJType @%NGMG` / `addLJType @%OPMG`
- Says: "#Add a new LJ type for Adenine N7 atom" / "...Guanine N7 atom" / "...backbone phosphate oxygen"
- READ. Flag: none.

**83.** Same page + `files/1264/1264_parmed.in`. ParmEd `add12_6_4` / `printLJMatrix`
- Mask: `add12_6_4 :MG watermodel TIP4PEW` (parmed_1264_na.in) ; `add12_6_4 :MG watermodel SPCE` (1264_parmed.in) ; `printLJMatrix :MG`
- Says: "you can specify in the amber mask in the add12_6_4 command."
- READ. Flag: none.

**84.** https://ambermd.org/tutorials/advanced/tutorial20/12_6.php + `files/126/126_parmed.in`. ParmEd
- Mask: `printDetails :ZN` / `printLJMatrix :ZN`
- Says: "Here we use ":ZN" (ZN is the residue name of zinc ion in the 4V2Y_clean_A_2.pdb file) to represent the zinc ion."
- READ. Flag: none.

**85.** https://ambermd.org/tutorials/advanced/tutorial20/mcpbpy.php + `files/mcpbpy/mcpbpy_parmed.in`. ParmEd
- Mask: `printBonds :ZN1` / `printAngles :ZN1` / `printDihedrals :ZN1` / `printDetails :ZN1`
- Says: "in which we have ":ZN1" as the mask of the zinc ion."
- READ. Flag: none.

**86.** https://ambermd.org/tutorials/advanced/tutorial20/m1264.php + `files/m1264/addc4_PO4.in`. ParmEd
- Mask: `change AMBER_ATOM_TYPE @2,3,4,5 o-` ; `addLJType @%o-` ; `add12_6_4 @%o-,Ca2+ c4file c4.txt polfile pol_addc4_phosphate.dat` ; `printLJMatrix :1-2`
- Says: "In "addc4_PO4.in", notice that we changed the "OP" atom type to add a new atom type for "o-". This is in order to fulfill criteria #1."
- READ. Flag: none. **Interp:** the phosphate oxygens are picked by atom number (`@2,3,4,5`), not by name.

**87.** Same page + `files/m1264/cg-addc4.in`. ParmEd
- Mask: `change AMBER_ATOM_TYPE :HID@NE2 MUTE` ; `addLJType @%MUTE` ; `add12_6_4 @%Zn2+ c4file c4-zn.txt polfile lj_1264_pol.dat` ; `printLJMatrix @%Zn2+`
- Says: "These files modify the C4 terms between the zinc ion and the NE2 atom of HID residues in the protein." File comment:
  "#changes the atom type of the target atom to MUTE".
- READ. Flag: none for the masks. The file's own comment names "c4-metal-ion.txt" and "cg-lj.dat", which differ from the files the command uses.

**88.** https://ambermd.org/tutorials/advanced/tutorial28/Part2.php. mdgx `&ipolq` `solute`, `modq`
- Mask: `solute      ':1',` ; `modq        ':WAT & @O'     -1.0106,` ; `modq        ':WAT & @H1,H2'   0.5053,`
- Says: "For TIP3P water ... places a charge of -1.0106 proton units on the oxygen and 0.5053 on each hydrogen."
- READ. Flag: none.

**89.** https://ambermd.org/tutorials/advanced/tutorial28/Part3.php. mdgx `&fitq` `equalq` / `minq`
- Mask: `equalq    '@C1,C3'` / `equalq    '@O1,O3'` / `equalq    '@H11,H12,H31,H32'` / `equalq    '@HO1,HO3'` / `minq      '@C2'`
- Says: "each instance specifying a group of partial charges that should have the same value. mdgx will treat all partial charges named
  in each ambmask string ... as a single variable". Also "The minq keyword is what applies harmonic restraints to atoms".
- READ. Flag: none. The symmetry-equivalent glycerol atoms are grouped as described.

**90.** https://ambermd.org/tutorials/basic/tutorial6/index.php. mdgx `&configs` `GridSample` (Ace-Ala-Hid-Ala-Nme)
- Mask: `GridSample  :2@C  :3@N  :3@CA :3@C` and `GridSample  :3@N  :3@CA :3@C  :4@N` (each followed by `{ -180.0 180.0 }  fbhw  10.0  Krst 64.0,`)
- Says: "% Backbone phi and psi sampling". Also "sampling conformations of the center residue's Φ and Ψ coordinates every 45°". And
  "Any other values it finds ... are going ot be assumed to be ambmask atom masks specifying a single atom."
- READ. Flag: none (Φ = C(i-1)-N-CA-C and Ψ = N-CA-C-N(i+1) for residue 3).

**91.** Same page. mdgx `Set` (H-bond blocking)
- Mask: `Set   :1@O  :2@H  { 50.0 50.0 }  fbhw 47.5 Krst 64.0,` (ten pairs, through `:4@O  :5@H`)
- Says: "we will add the following input to prevent hydrogen bonding between atoms of subsequent residues in the backbone"
- READ. Flag: none.

**92.** Same page. mdgx `RandomSample`
- Mask: `RandomSample  :3@CG  :3@CB  :3@CA  :3@N` and `RandomSample  :3@ND1 :3@CG  :3@CB  :3@CA`
- Says: "The position of the side chain should vary from one conformation to the next, but perhaps not in a systematic way alongside
  the backbone."
- READ. Flag: none (χ1 and χ2 of HID 3, atoms written in reverse order).

**93.** dep. https://ambermd.org/tutorials/advanced/tutorial2/section3.php (QM/MM, NMA in water) + `files/min_qmmm.in`, `md_qmmm.in`. sander `qmmask`
- Mask: `qmmask=':1-2',`
- Says: "qmmask = ':1-2' - This specifies what to treat quantum mechanically using standard AMBER mask notation. Here it implies residue 1
  and 2 which is the ACE and NME making up the NMA molecule. Alternatively you can manually specify the atom numbers using iqmatoms.
  E.g. iqmatoms=1,2,3,4,5,6,7,8,9,10,11,12,"
- READ. Flag: none. The same page also gives the atom-number form.

**94.** dep. https://ambermd.org/tutorials/advanced/tutorial5_amber11/section4.php (NEB, alanine dipeptide). sander `tgtfitmask` / `tgtrmsmask`
- Mask: `tgtfitmask=":1,2,3",` / `tgtrmsmask=":1,2,3@N,CA,C",`
- Says: "we are setting the tgtfit mask to rms fit to all residues of the alanine dipeptide, and we set the tgtrms mask to the backbone C,
  CA, and N atoms."
- READ. Flag: none. **Interp:** ACE has no N/CA and NME no CA, so the selection is ACE@C, ALA@N,CA,C, NME@N.

### 8. Deprecated-tutorial cpptraj/ptraj masks (still published on ambermd.org)

**95.** dep. https://ambermd.org/tutorials/advanced/tutorial22/section3.php (aMD PCA)
- Mask: `center origin :1-58` / `strip :WAT,Cl-` / `rms reference mass :1-58@CA,C,N out ...` / `matrix covar name matrixdat @CA out covmat-ca.dat` /
  `rms reference out rms-av.dat :4-54@CA` / `projection modes ... :4-54@CA`
- Says: not stated per mask ("The cpptraj input file used to produce the PCA vectors from the aMD trajectory ...").
- READ. Flag: none.

**96.** dep. https://ambermd.org/tutorials/advanced/tutorial7/index.php (REMD, Ala10) + `files/create_replica_trajs.x`
- Mask: `distance d1 out dist.rep.$ext :2@CA :8@CA`
- Says: "In the example below, a distance is calculated, and each numbered output file will have the time sequence of this distance for
  the corresponding replica."
- READ. Flag: none here. This looks like the source of #30, where the newer tutorial added "end-to-end".

**97.** dep. https://ambermd.org/tutorials/advanced/tutorial8/loop13.php (HIV integrase loop)
- Mask: `center :1-154` / `strip :WAT` / `strip :Cl-` / `rms first :3-152@CA` / `rms reference out $ofile :1-154` /
  `rms first out wt1mg_ca.b :1-154@CA` / `atomicfluct out wt1mg.bfactor @CA byatom bfactor`
- Says: for atomicfluct, "This will give you the B-factor of each C-alpha atom." The others are not stated.
- READ. Flag: none.

**98.** dep. https://ambermd.org/tutorials/advanced/tutorial16/index.php + `include/density.cpptraj` (Lipid14 DOPC)
- Mask: `center ":PC | :OL" origin`
- Says: "# Center the lipid bilayer tail residues at zero coordinates"
- READ. **Flag F18.**

**99.** Same file
- Mask: `image origin center ":WAT"` ; `density out electron_density.dat electron delta 0.25 "*"`
- Says: "# Image all water molecules to the zero coordinates using the center of mass of the molecules"
- READ. Flag: none. Masks are double-quoted inside a cpptraj script.

**100.** dep. https://ambermd.org/tutorials/basic/tutorial1/section5.php + `files/amber_input_files/polyAT_wat_calc_backbone_rms.in`. cpptraj `rms`
- Mask: `rms first out polyAT_wat_backbone.rms @P,O3',O5',C3',C4',C5' time 0.2`
- Says: "we shall consider just the main backbone atoms, P, O3*, O5* C3*, C4* and C5* (P, O3', O5', C3', C4' and C5' in our prmtop)."
- READ. Flag: none. There are six apostrophes inside one mask, and the text notes the older `*` naming.

**101.** dep. https://ambermd.org/tutorials/basic/tutorial3/section6.php (Trp-cage TC5b) + `files/measure_rmsd.trajin`
- Mask: `rms reference out rmsd_to_lowest_energy_struct.dat @N,CA,C time 1.0`
- Says: "figure 1B which shows the backbone RMSd between the trajectory structures and this lowest energy structure"
- READ. Flag: none.

**102.** Same page + `files/extract_pdb.cpptraj`
- Mask: `rms first mass :2-20@CA,C,N`
- Says: "#orient all frames best fit to backbone of helix in NMR structure"
- READ. **Flag F19.**

**103.** Same page + `files/measure_trp_angles.cpptraj`
- Mask: `dihedral trpphi :5@C :6@N :6@CA :6@C` / `dihedral trppsi :6@N :6@CA :6@C :7@N` / `dihedral trpchi1 :6@N :6@CA :6@CB :6@CG` /
  `dihedral trpchi2 :6@CA :6@CB :6@CG :6@CD2`
- Says: "take a look at the various backbone related dihedral angles involving the Tryptophan".
- READ. **Flag F20** (chi2 uses CD2).

**104.** Same tutorial + `files/analyse_hbond.cpptraj` and `average_28-35_crd.cpptraj`
- Mask: `hbond :* avgout avg-hbt.dat printatomnum` ; `rms first mass @C,CA,N`
- Says: for the rms, "we can do a mass weighted backbone RMS fit of every frame to the first frame". The hbond mask is not stated.
- READ. Flag: none.

**105.** dep. https://ambermd.org/tutorials/advanced/tutorial4/suppose.htm (NAB `suppose` manual page). **Not ambmask syntax.**
- Mask: `suppose -fit "::C*,N*,O*,P*" -calc "::C*,N*,O*,P*" -rot gcg_a.ann.pdb` (index.php) ; manual examples `::P,O?P,C[3-5]?,O[35]?`,
  `:C*[^']`, `-fit ":1-10:C,CA,N"`
- Says: "::P,O?P,C[3-5]?,O[35]?  The nucleic acid backbone." Also ":C*[^'] Select all non-sugar carbons in a nucleic acid."
- READ. **Flag F21.** This is NAB's strand:residue:atom syntax and looks almost like an AMBER mask.

---

### Flags

**F1. GIST tutorial: `!@H` is used where heavy atoms are meant (advanced/tutorial25; #52, #53).** In AMBER mask syntax `@H` matches only
atoms named exactly `H` (the backbone amide H). All hydrogens is `@H=`. The tutorial says "protein heavy atoms" and "restraining all
heavy atoms during the production simulation", and labels a minimization "the water and the protein hydrogen atoms". pmemd's own
published counts settle it: `!:WAT` = 3675 atoms and `!:WAT & !@H` = 3446. Only 229 atoms were released; every side-chain and Hα
hydrogen stayed restrained at 100 kcal/mol/Å². The 10-ns NPT input is published with `!@H=`, the correct form. Its published output
`equil-npt.out` was run with `!@H` (and cut 9.0 instead of 10.0). So the input and output posted for that stage are not a matching pair.

**F2. cpHE tutorial: one mask, three different answers (advanced/tutorial33; #50).**
`'@CA,C,O,N|(:HEH,PRN)@FE,NA,NB,NC,ND,C3D,C2A,C3B,C2C,CA,CB'`
1. Reading it the obvious way, `@CA,C,O,N` has no residue restriction. In the explicit-solvent topology (TIP3PBOX; ParmEd on the
   published `mp8_es.new.prmtop`) `@CA,C,O,N` alone selects 2432 atoms, 2388 of them water oxygens. With an explicit `&` after the
   parenthesis, the whole mask gives 2443 atoms (explicit) and 55 (implicit, `mp8_is.prmtop`).
2. ParmEd 4.3.1 refuses the string as written: `MaskError: There may be missing operands in the mask`. It does not accept `(...)@...`
   without an operator.
3. pmemd's published mdouts (`mp8_es.min.mdout`, `mp8_is.min.mdout`) both say "matches 127 atoms". The two systems have the same
   237-atom solute. I could not reproduce 127 under any parse I tried (44 / 55 / 60 / 131 / 155 / 2443). The implicit system has only
   122 non-hydrogen atoms (ParmEd `!@H=`), so pmemd's 127 must include hydrogens.

None of these matches "restraint on backbone atoms and on some heme atoms". At minimum, the published mask behaves differently in two
AMBER tools. **Unverified:** what pmemd actually selected. That needs `ambmask` or cpptraj `mask` run on the published topology.

**F3. ASMD tutorial: unrestricted backbone mask in explicit water (advanced/tutorial26; #56).** `'@CA,C,N,O'` is described as "the
backbone atoms "C,CA,N,O"". ParmEd on the published `ala.asmd.prmtop` (TIP3P) selects 2965 atoms, 2922 of them water oxygens. Every
water O is restrained at 10, 5 and 1 kcal/mol/Å² through the "backbone-restrained" stages. Residue-restricted forms would be `:1-12@CA,C,N,O`
or `!:WAT & @CA,C,N,O`. Compare #47 (basic/tutorial13), which drops O, and #49 (T18), which is in implicit solvent: both avoid the problem.

**F4. Hydroxyapatite tutorial: residue range too large (advanced/tutorial27 hap_water; #60).** The slab is 4×4×1 unit cells, one `HAP`
residue each, so 16 residues (the published `hap16.pdb` has residues 1–16, 704 atoms). `':1-64'` therefore also restrains water residues
17–64. ParmEd on the published `hap16_water.prmtop`: `:1-64` = 704 HAP + 144 WAT atoms (48 waters). In the "minimization of water" step,
48 waters stay pinned.

**F5. 12-6-4 tutorial: comment says Adenine, mask says Guanine (advanced/tutorial20/12_6_4.php; #80).**
`change AMBER_ATOM_TYPE :G*,DG*@N7 NGMG #Change atom type of Adenine N7 atom to NGMG`. The next line (`addLJType @%NGMG #Add a new LJ type
for Guanine N7 atom`) shows the mask is right and the comment is a copy-paste slip.
F5b (#79): `:A*` / `:G*` are prefix wildcards over residue names. In a protein-containing system `:A*` would also hit ALA/ARG/ASN/ASP.
That is latent here, since 1D23 is DNA only.

**F6. T-REMD analysis: "end-to-end" distance that does not span the ends (advanced/tutorial43; #30).** For
`ACE ALA×10 NHE` (residues 1–12, Ala = 2–11), `:2@CA :8@CA` measures from the 1st to the 7th alanine. The deprecated predecessor (#96)
used the same mask and only called it "a distance". End-to-end would be `:2@CA :11@CA`, or `:1 :12` for the caps.

**F7. Clustering recipe: 575 vs 576 (AMBER-hub clustering; #40, #41).** The system is described as a "575 amino acid" protein "with an
inhibitor in the active site". The mask is `:1-576`, explained once as "residues 1 to 576" and once as "residues 1 to 575". If residue 576
is the inhibitor, any of its atoms named C, N, O, CA or CB enter the protein RMSD metric (**unverified**; the topology is a 1.7 GB-class
download I did not fetch). `&!@H=` is redundant after an explicit name list, and the names are called "atom types". The "Tip!" loop
quietly switches to `@N,CA,C,O`.

**F8. Umbrella-sampling tutorial: title says phi/psi, restraint is omega (advanced/tutorial17; #70).** Every page is titled "Alanine
Dipeptide Phi/Psi Rotation". The system is `ACE ALA ALA NME` (a tripeptide in the tutorial's words), the text says "the angle of the C-N
bond" and "trans to cis isomerization", and `iat=9,15,17,19`. **Interp:** with standard templates (ACE 1–6, ALA2 N7 H8 CA9 … C15 O16,
ALA3 N17 H18 CA19), that is CA–C–N–CA, the ω peptide-bond torsion. #74 confirms the numbering (ACE C = 5, ALA N = 7, CA = 9, C = 15,
next N = 17). The restraint matches the prose; the title does not.

**F9. aMD tutorial: "heavy atoms" without a hydrogen exclusion (dep. advanced/tutorial22; #64).** "Relax the system, restraining the
protein heavy atoms (NPT, 300K, 0.5ns)" uses `':1-58'`, which includes all hydrogens of BPTI.

**F10. Placeholders that look like masks (advanced/tutorial38; #57, #58).** `:PROTEIN+LIPID`, `:PROTEIN+LIGAND` and `:PROTEIN` ship in
runnable input files. The page says to replace them. **Interp:** `+` is not a mask operator, and these strings would be read as residue
names that do not exist. A pipeline that runs the files unedited gets no restraint, or an error, depending on the program.

**F11. Text slip (basic/tutorial15; #48).** "water restraint" appears in an implicit-solvent (igb=8) heating step whose mask is the backbone.

**F12. pmemd-only TI masks copied into sander templates (advanced/tutorial9 A9 sidechain/sander; #15).** The commented "method 2" lines
in the sander scripts use `scmask1`/`scmask2` (pmemd variable names) and residue `:163`. Residue 163 is the mutated valine only in pmemd's
tiMerge-merged topology; sander uses separate V0/V1 prmtops with the mutation at 99. They are commented out, but uncommenting them as the
comment invites would give wrong or unknown variables in sander.

**F13. FEW softcore mask is not an AMBER mask (advanced/tutorial24; #18).** `LFc@C14,H1` has no leading `:`. The FEW input documents
this as its own `<alias>@<names>` format. A mask checker must not judge it as ambmask.

**F14. MMPBSA tutorial: reference structure (advanced/tutorial3 section1; #23).** The text says RMSD "with respect to the minimized
structure"; the script's reference is `ras-raf_solvated.inpcrd`. The mask (`@CA,C,N`, backbone) is consistent.

**F15. basic/tutorial0 explanation table lists commands not in the script (#28).** `center :1-3 mass origin` + `image origin center` are
explained. The script shown and linked uses `autoimage`.

**F16. Name vs type (advanced/tutorial15; #31).** The prose says "N1 atoms". The acetonitrile nitrogen's name is `N` and its GAFF type is
`n1`. The mask `:ACN@N` is right.

**F17. Minor wording.** #63: `!:WAT` also restrains Cl- ions ("restraining the protein"). #66: "nucleosome" for a dodecamer. #69:
"Hold lipid fixed" with `RES 1 217` also holds the methanol in residue 1.

**F18. Lipid14 electron-density script (dep. advanced/tutorial16; #98).** The comment says "Center the lipid bilayer tail residues". The
mask `":PC | :OL"` includes the PC head-group residues as well as the OL tails, i.e. whole lipids. (The page also says to run
`ptraj_mod ... density.ptraj_mod` right after showing a cpptraj script.)

**F19. Trp-cage fit mask vs comment (dep. basic/tutorial3; #102).** The comment says "best fit to backbone of helix in NMR structure". The
command fits `:2-20@CA,C,N` to the **first frame** (`rms first`), not the NMR structure, over residues 2–20 of a 20-residue protein, not
the helix alone.

**F20. Trp χ2 definition (dep. basic/tutorial3; #103).** `:6@CA :6@CB :6@CG :6@CD2`. The common convention is χ2(Trp) = CA–CB–CG–CD1
("CD1 cis to CA"), per the Garlic dihedral-definition table
(http://www.mlb.co.jp/linux/science/garlic/doc/commands/dihedrals.html, read). Using CD2 shifts the angle by about 180°. Source is
secondary; I did not check it against the IUPAC-IUB 1970 document itself.

**F21. Look-alike syntax (dep. advanced/tutorial4; #105).** NAB's `suppose` uses `strand:residue:atom` expressions (`::C*,N*,O*,P*`,
`:1-10:C,CA,N`, `[3-5]` and `?` globs). They look like AMBER masks and are not. A checker or LLM trained on both will confuse them.

Consistency checks that **passed** (useful as positive controls): #12 tiMerge arithmetic; #17 ACES TI masks (published mdout counts);
#46 RAMP1 `:1-81` (prmtop labels); #49 lysozyme 516 = 129×4; #55, #59 ParmEd counts; #57 the 520 example; #67/#68 GROUP residue ranges;
#75 ASMD iat = first/last Ala CA; #76 GBION ion indices; #77 72 N31 atoms in igr2.

### Coverage notes

- **MMPBSA.py:** the only ambermd.org MMPBSA.py tutorial (advanced/tutorial3/py_script) never sets `receptor_mask`, `ligand_mask` or
  `strip_mask`. It relies on MMPBSA.py's "Best guess" (#20, #21). FEW (#18 context) generates its MMPBSA inputs internally.
- **DISANG files** in the tutorials (T17, T19, T29, T4, GBION, umbrella COM) always use `iat=`/`igr1=`/`igr2=` atom numbers, never masks.
  Masks appear only as human-readable annotations (#72) or in cpptraj (#74).
- **No mask found** in: advanced/tutorial1 (DNA-ligand), 6 (pKa TI), 13 (crystal), 31 (NFE), 32, 34, 35, 36, 37 (WESTPA), 40 (3D-RISM),
  42 (REMD inputs; chirality restraints are generated by makeCHIR_RST); basic/tutorial4b, 5, 7, 8, 9, 10, 12, 14, 19, 20, 21, 22, 23; pengfei (LEaP).
- No current ambermd.org tutorial uses `bellymask` (dep. basic/tutorial1 discusses BELLY in prose and recommends restraints instead) or
  `qmmask` (only dep. tutorial2).

### Pages tried that failed / leads

- 404 at first, then found at another path: `advanced/tutorial9/pages/A9.tar.xz`, `pages/setup_old.html`, `pages/analysis_old.html` (they
  live at `advanced/tutorial9/…`); `advanced/tutorial33/section1-4.php` (the real pages are `Section1-4.php`).
- 404: `advanced/tutorial3/section4.php`, `section5.php`, `section6.php` (linked from the old mm_pbsa.pl pages);
  `advanced/tutorial24/files/TI_setup3_L51c_d.in`, `advanced/tutorial24/tutorialA17.php`; `advanced/tutorial13/Construction.html`,
  `Selection.html`; `advanced/tutorial10/code/index.html`; `advanced/tutorial18/eq3`; `advanced/tutorial21/sims/*_npt2.out` (4 files);
  `advanced/tutorial25/files/Section3_out/*.dx`, `Section4_out/*.dx`, `GISTPP/*.dx` (output grids, no masks expected);
  `advanced/tutorial32/report.m`; `advanced/tutorial38/packing/1BL8/leap.in`; `basic/tutorial2/index.htm`.
- 403 (directory listings): `advanced/tutorial42/include/ReplicaExchange/`, `…/00EQUIL/`; `basic/tutorial21/include/pmemd/`.
- 500: `advanced/tutorial39/install_feworkflow.php`.
- Not fetched: AMBER-hub clustering topology/trajectories (multi-GB), so F7's inhibitor question is unverified. Also not fetched: the
  CHARMM-GUI, Maestro-lipid, membrane-protein (callumjd) and pAPRika tutorials linked from the index; the ambertutorials (Rutgers) GitLab
  workshop pages; the LiveCoMS GIST paper.
- LEAD only (WebSearch snippets, not tutorials, not used above): AMBER mailing-list threads on MMPBSA masks, e.g.
  http://archive.ambermd.org/201111/0603.html ("How to use strip mask and receptor mask in the new mmpbsa.py?") and
  http://archive.ambermd.org/201104/0553.html. The search snippet claims `strip_mask` examples such as `":200-204,205-END"` appear in
  those threads. I did not open them; it would be a source for real `strip_mask` strings if Part B needs them.

---

# B3. Public AMBER tutorials outside ambermd.org (delegated harvest, included verbatim; headings demoted one level)

> Where an entry below says "not run", "unverified" or "I did not check", see B1.1 first. Several of those questions now have RUN verdicts: `@CA.C.N`, `:WAT:Na+:Cl-`, `:WAT@-O`, `:!@H=`, `!@H`, `GU1@…`, `:PROTEIN+LIPID`, pytraj "and not hydrogen", the cpHE 127-atom mask (F2), and the ante-MMPBSA `-n` direction (B3 #8).

## Part B: AMBER masks in public tutorials outside ambermd.org

Collected 2026-10-02. Every entry marked READ was seen in a page or file that I fetched in this session
(curl of the HTML, the MediaWiki `action=raw` source, the GitHub raw file, or a tarball the tutorial
links to). A spot check confirmed that the masks also appear on the live rendered pages (Compute Canada x6,
Rizzo 4S0V). LEAD means I saw it only in a search snippet. **Every entry here is READ.** I did not fill any
gap from memory.

Format note: I used a list rather than a table because several masks contain `|`, which would break a
markdown table if left unescaped. The masks appear between backticks exactly as printed on the page,
quote characters included. On WordPress pages that means typographic quotes (see #84 to #89).

Reference used for "interpretation" notes: the cpptraj manual source,
https://raw.githubusercontent.com/Amber-MD/cpptraj/master/doc/cpptraj.lyx, section "Atom Mask Selection
Syntax" (READ). Relevant lines from it:
"'*' Zero or more characters. '=' Same as '*' '?' One character.";
"@CA,C,O,N,H All backbone atoms.";
":*&!@H= All non-hydrogen atoms (equivalent to "!@H=").";
":1-500@O&!(:WAT|:LYS,ARG) All backbone oxygens in residues 1-500 but not in water, lysine or arginine residues."
Comma-separated lists are the only list form the manual documents. It shows no `:A:B` chaining, no `@-X`
form and no `and not` keywords.

Abbreviations: CC = Compute Canada / Alliance lessons. RZ = Rizzo lab wiki (ringo.ams.stonybrook.edu).
YK = York group tutorials (yorkgrouptutorials-db4433.gitlab.io). HUB = AMBER-hub (amberhub.chpc.utah.edu).
BB = BioExcel biobb_wf_amber notebooks.

---

### A. Compute Canada / Alliance: molmodsim-amber-md-lesson and molmodsim-pytraj-analysis

**1.** https://computecanada.github.io/molmodsim-amber-md-lesson/13-Running_Simulations/index.html
- program/variable: sander/pmemd `restraintmask` (min.in, heating input, equilibrate_1.in; the same string appears 3 times)
- mask: `"(:1-96)&(@CA,N,O)"`
- tutorial says: "In the first stage we restrain all original atoms. In the second stage we restrain only the original backbone atoms. Our example protein is very small and we have limited time, so we skip the first step and restrain only protein backbone."
- READ
- flag: **backbone defined without C.** The text says "protein backbone", but the mask lists CA,N,O and leaves out the carbonyl carbon C. The cpptraj manual lists `@CA,C,O,N,H` as "All backbone atoms". The same lesson's pytraj RMSD episode (#9) instead uses `@C,N,O`, which leaves out CA.

**2.** same page (13-Running_Simulations)
- program/variable: cpptraj `strip` and cpptraj `parmstrip` (two commands with the identical mask)
- mask: `!(:1-96)`
- tutorial says: "The following command will remove everything except residues from 1 to 96 and save every second frame."
- READ
- flag: none.

**3.** https://computecanada.github.io/molmodsim-amber-md-lesson/20-Simulating_RNA_Silencing_Complex/index.html
- program/variable: exercise answer (an AMBER mask the lesson later uses for restraints)
- mask: `:22-120,126-185,190-246,251-272,276-295,303-819,838-858,860-868,870-877,879-885,889-896`
- tutorial says: "Create AMBERMASK representing all residues in the simulation system that are given in the original pdb entry 6N4O." The residue-mapping table on the page gives Protein A 1-859, RNA chain C 860-880, RNA chain D 881-898 and MG ions 899-901.
- READ
- flag: none for the mask. Separately, the page's mapping table row "RNA chain D | 1-18 | 898 | 881-898" lists a shift of 898, but 1-18 → 881-898 is a shift of 880. That is a table typo, not a mask error.

**4.** same page (20-Simulating...), min_1.in
- program/variable: sander `restraintmask`
- mask: `"(:22-120,126-185,190-246,251-272,276-295,303-819,838-858,860-868,870-877,879-885,889-896)"`
- tutorial says: "Let's do a two a two stage minimization. In the first stage we restrain all original atoms."
- READ
- flag: none. Hydrogens are included, which matches "all original atoms" (interpretation).

**5.** same page (20-Simulating...), second minimization
- program/variable: sander `restraintmask` (min_2), also given as the exercise answer
- mask: `(:22-120,126-185,190-246,251-272,276-295,303-819,838-858,860-868,870-877,879-885,889-896)&(@CA,N,O,P,C4',O3')`
- tutorial says: "In the second round of minimization constrain only backbone atoms of all original residues." Definition given on the page: "Use the following definition of backbone atoms/: CA, N, O, P for protein, and  P, C4', O3' for nucleic."
- READ
- flag: (a) the protein backbone again leaves out C, as in #1. (b) The text puts "P" in the protein backbone definition. Proteins have no atom named P, so this is harmless but wrong as stated (interpretation).

**6.** same page (20-Simulating...)
- program/variable: cpptraj `strip` and `parmstrip`
- mask: `!(:1-901)`
- tutorial says: "The following command will remove everything except residues from 1 to 901 and save every second frame in the file mdcrd_nowat.nc"
- READ
- flag: none. 1-901 includes the MG ions (899-901) according to the table.

**7.** https://computecanada.github.io/molmodsim-amber-md-lesson/23-preparing_small_molecule_topology/index.html
- program/variable: ante-MMPBSA.py `-s`
- mask: `'!(:214-456,669-1029)'`
- tutorial says: "-s Amber mask of atoms needed to be stripped from PRMTOP to make the COMPLEX topology file"
- READ
- flag: none on its own. Arithmetic check (mine): it keeps 243 + 361 = 604 residues, which matches `receptor_mask=:244-604` in #9.

**8.** same page (23-...)
- program/variable: ante-MMPBSA.py `-n`
- mask: `':1-243'`
- tutorial says: "-n Amber mask of atoms needed to be stripped from COMPLEX to create LIGAND."
- READ
- flag: **ambiguous or contradictory.** Read literally ("stripped from COMPLEX to create LIGAND"), ligand.prmtop would contain residues 244-604. The MMPBSA input on the same page says `ligand_mask=:1-243` (#9). The tutorial's sentence matches the ante-MMPBSA.py `-h` help text as reproduced at https://gohom.win/2016/03/30/amber-mmpbsa/ (READ): "-n LIGAND_MASK, --ligand-mask=LIGAND_MASK Amber mask of atoms needed to be stripped from COMPLEX to create LIGAND." So one of the two readings is wrong. I did not check ante-MMPBSA.py's source to find out which one it implements. Also, the "ligand" here is 243 residues on a page titled "small molecules", and the page does not say what it is.

**9.** same page (23-...), MMPBSA.py input `&general`
- program/variable: MMPBSA.py `strip_mask`, `ligand_mask`, `receptor_mask`
- mask: `strip_mask=!(:214-456,669-1029)` / `ligand_mask=:1-243` / `receptor_mask=:244-604`
- tutorial says: not stated beyond the variable names
- READ
- flag: see #8.

**10.** https://computecanada.github.io/molmodsim-pytraj-analysis/03-RMSD_Analysis_with_pytraj/index.html
- program/variable: pytraj `pt.rmsd(..., mask=...)` and `pt.pmap_mpi(pt.rmsd, ..., mask=...)`
- mask: `'@C,N,O'`
- tutorial says: "Compute and plot RMSD of the protein backbone atoms."
- READ
- flag: **"backbone" without CA.** The mask selects atoms named C, N and O and leaves out CA. In the same course, CC lesson #1 uses CA,N,O, which leaves out C instead. Neither matches the manual's `@CA,C,O,N,H`.

**11.** same page (03-RMSD...), exercise solution
- program/variable: pytraj `pt.rmsd` mask
- mask: `'(:U,A,G,C)&!(@H=)'`
- tutorial says: "Compute and plot RMSD of all nucleic acid atoms (residues U,A,G,C) excluding hydrogens for all frames."
- READ
- flag (interpretation, unverified): AMBER nucleic-acid topologies usually name chain-terminal residues differently (for example G5 or C3). If this system does that, `:U,A,G,C` silently drops the terminal nucleotides. The page does not list the residue names.

**12.** same page (03-RMSD...), exercise solution
- program/variable: pytraj `pt.rmsd` mask
- mask: `'(:1-859)&!(@H=)'`
- tutorial says: "Compute and plot RMSD of all protein atoms (residues 1-859) excluding hydrogens for frames 1000-1999."
- READ
- flag: none. It agrees with the protein range 1-859 in #3.

**13.** https://computecanada.github.io/molmodsim-pytraj-analysis/05-PCA_analysis/index.html
- program/variable: pytraj `pt.pca(..., mask=...)`
- mask: `":860-898@O3',C3',C4',C5',O5',P"`
- tutorial says: "Analyze 39 nucleic acid residues, 6 backbone atoms in each residue. The total number of atoms included in the analysis is 234, so eigenvectors will be 234 elements long."
- READ
- flag (interpretation, unverified): the count of 234 assumes every residue has a P atom. AMBER 5'-terminal nucleotides normally have no P, and there are two RNA chains here (860-880 and 881-898), so the true count would likely be 232. The page also says "Request calculations of the three first principal components" while the code passes `n_vecs=5`. That second point is not about the mask.

**14.** https://computecanada.github.io/molmodsim-pytraj-analysis/06-CrossCorrelation_analysis/index.html
- program/variable: pytraj `pt.atomiccorr(..., mask=...)`
- mask: `":50-150 and not hydrogen"`
- tutorial says: "Calculate correlation matrix for residues 50-150"
- READ
- flag: **not AMBER mask syntax.** The cpptraj manual documents no `and`/`not`/`hydrogen` keywords; the AMBER form would be `:50-150&!@H=`. Whether pytraj accepts this string I did not verify.

**15.** same page (06-CrossCorrelation...)
- program/variable: pytraj `pt.atomiccorr` mask (used twice, frames 1-600 and a second chunk)
- mask: `":860-898 and not hydrogen"`
- tutorial says: "we just need to recompute the correlation matrix using different atom mask."
- READ
- flag: same as #14.

---

### B. Rizzo lab wiki (Stony Brook AMS536 AMBER tutorials)

Fetched as MediaWiki source with `https://ringo.ams.stonybrook.edu/index.php?title=<page>&action=raw`. The rendered URL is `https://ringo.ams.stonybrook.edu/index.php/<page>`.

**16.** https://ringo.ams.stonybrook.edu/index.php/2023_AMBER_tutorial_1_with_PDBID_4S0V
- program/variable: pmemd/sander `restraintmask`, steps 01 to 07 (7 occurrences)
- mask: `":1-490 & !@H="`
- tutorial says: "after that command, if you see a "!", that is telling AMBER to exclude any atoms that follow; if you see "@H=", that is telling AMBER to restrain all the hydrogen atoms.  In the first 7 input files we want to restrain all residues in our complex, including the ligand." Also: "We see that there are 490 residues in our complex.  489 in the protein and one for the ligand."
- READ
- flag: **the syntax explanation is backwards.** `@H=` selects atoms whose names start with H, and `!@H=` excludes them, so the hydrogens are the atoms that are *not* restrained. The page's own heading "Minmize all the hydrogens" agrees with the mask, not with the explanation. Interpretation: water and ions sit outside 1-490 and are also unrestrained. The same paragraph appears verbatim on the 1Y0X page (#33).

**17.** same page (4S0V), prose right after 01.min.mdin
- program/variable: `restraintmask` (shown in the text as "the line" to edit)
- mask: `restraintmask=":1-490@CA,C,N", ! atoms to be restrained.`
- tutorial says: "In the above input file you'll see a line: ... This is where the number of residues for your system needs to be updated."
- READ
- flag: **the text does not match the file.** The 01.min.mdin printed just above contains `":1-490 & !@H="`, not `":1-490@CA,C,N"`.

**18.** same page (4S0V), 08.equil.mdin and 09.equil.mdin
- program/variable: `restraintmask`
- mask: `":1-489@CA.C.N"`
- tutorial says: "! atoms to be restrained, only the backbone" and "NOTE: for the above input file we only want to restrain the protein and not the ligand so the '490' needs to be change to '489'."
- READ
- flag: **periods instead of commas.** The manual's atom-name list is comma-separated (`@CA,C,N`). Read as syntax, `@CA.C.N` is a single atom name "CA.C.N", which matches nothing. That would make the restraint empty, or the parser may error. This is interpretation; I did not run it. The production file on the same page uses `":1-489@CA,C,N"` with commas (#19). The same dotted form appears on the 2P16, 2ITO and 1Y0X pages (#27, #30, #34).

**19.** same page (4S0V), 10.prod.mdin
- program/variable: `restraintmask`
- mask: `":1-489@CA,C,N"`
- tutorial says: "Note for the restraintmask line, use the same number as for the 09.equil.mdin file in the previous step.  In our case, this number is 489."
- READ
- flag: none. CA,C,N is the N–CA–C chain without O, which is a common "backbone" choice.

**20.** same page (4S0V), cpptraj cpp_strip_water.in
- program/variable: cpptraj `rmsd ... reference <mask>`
- mask: `:1-490@CA`
- tutorial says: "Note that this should cover all CA atoms (including the ligand) in your complex" and "The reference mask should contain BOTH the ligand and receptor in its value."
- READ
- flag (interpretation): `@CA` keeps only atoms named CA. A small-molecule ligand typed by antechamber/GAFF would normally have no atom named CA, so residue 490 most likely contributes zero atoms, contrary to "including the ligand". The same pattern appears on all the Rizzo pages: `:1-299@CA`, `:1-235@CA`, `:1-325@CA`, `:1-263@CA`, `:1-729@CA`, `:1-298@CA`.

**21.** same page (4S0V), cpptraj cpp_strip_water.in
- program/variable: cpptraj `strip`
- mask: `:WAT:Na+:Cl-`
- tutorial says: "create an input file which will delete the water and charges from the production trajectory."
- READ
- flag: **an undocumented form.** Residue names chained with `:` (rather than the documented comma list `:WAT,Na+,Cl-`) do not appear in the cpptraj manual's syntax section. I did not check whether cpptraj accepts this form. It appears on every Rizzo page fetched (3WZE, 2P16, 2ITO, 1Y0X, 6ME2, 1X70, 4qmz, 1c87), and the Singh page uses the same style (#84 to #88).

**22.** same page (4S0V), cpp_rmsd_lig.in
- program/variable: cpptraj `rmsd rms1 "<mask>" nofit mass`
- mask: `":490&!(@H=)"`
- tutorial says: "And check that the reference mask only factors in the ligand (490) in this file."
- READ
- flag: none.

**23.** same page (4S0V), cpp_rmsd_receptor.in
- program/variable: cpptraj `rmsd`
- mask: `":1-489&!(@H=)"`
- tutorial says: "And check that the reference mask only takes into account the receptor (1-489)."
- READ
- flag: none.

**24.** same page (4S0V), cpp_hbonds.in
- program/variable: cpptraj `hbond hb1 <mask> ... solventdonor <mask> solventacceptor <mask>`
- mask: `:1-490` / `:WAT` / `:WAT@-O`
- tutorial says: "Be sure that the hbobnd hb1 parameter corresponds to the residue numbers of the relevant ligand AND receptor (490 in our case)." The solvent masks are not described.
- READ
- flag: **`@-O` is not documented syntax.** The 2P16 and 1c87 pages use `:WAT@O`, and 4qmz uses `:WAT`. `@-O` looks like a typo that has been copied forward (it also appears on 3WZE, 2ITO, 1Y0X, 6ME2 and 1X70). I did not verify how cpptraj parses it.

**25.** https://ringo.ams.stonybrook.edu/index.php/2023_AMBER_tutorial_2_with_PDBID_3WZE, 01.min
- program/variable: `restraintmask`
- mask: `"!@H="`
- tutorial says: title line "Minimize all the hydrogens"; "You'll want to pay close attention to the restraint mask - it lifts in later steps."
- READ
- flag (interpretation): this mask restrains every non-hydrogen atom in the solvated system, water oxygens and ions included. That is consistent with "minimize all the hydrogens", but it differs from the 4S0V and 2P16 protocol, which restrains only the complex.

**26.** same page (3WZE), 02.equil.mdin
- program/variable: `restraintmask`
- mask: `":!@H="`
- tutorial says: not stated (same comment, "! atoms to be restrained")
- READ
- flag: **malformed-looking.** A `:` with no residue list followed by `!@H=` matches no form in the manual. It probably meant `"!@H="` as in step 01. I did not verify whether the parser rejects it or how it reads it. The same string appears on the 2022 6ME2 and 1X70 pages.

**27.** same page (3WZE), 08.equil.mdin
- program/variable: `restraintmask`
- mask: `":1-299@CA,C,N"`
- tutorial says: "Here, you will need to specify the exact residues of your COMPLEX to enter at the restraintmask line. This means the total protein residues plus the ligand. ... So here, 3WZE is 298 residues plus the ligand is 299."
- READ
- flag (interpretation): as in #20, `@CA,C,N` keeps the ligand residue only if it happens to have atoms named CA, C or N, so "plus the ligand" probably adds nothing.

**28.** same page (3WZE), 10.prod.mdin
- program/variable: `restraintmask`
- mask: `":1-298@CA,C,N"`
- tutorial says: "Note the restraint mask should include ONLY protein residues this time."
- READ
- flag: none.

**29.** same page (3WZE), cpptraj ligand and receptor RMSD
- program/variable: cpptraj `rmsd`
- mask: `":299&!(@H=)"` / `":1-298&!(@H=)"`
- tutorial says: "Reference mask once again contains protein residues + ligand." (about `:1-299@CA`) and "Restraint mask here only contains protein residues." (about the receptor RMSD; it calls an RMSD mask a "restraint mask")
- READ
- flag: minor wording only.

**30.** https://ringo.ams.stonybrook.edu/index.php/2023_AMBER_tutorial_3_with_PDBID_2P16
- program/variable: `restraintmask` (steps 1-7) and steps 8-9
- mask: `":1-235 & !@H="` / `":1-234@CA.C.N"`
- tutorial says: "Ensure that the number in the restraintmask parameter corresponds to the number of residues in the protein + 1 for the ligand, since we are restraining both for the first few iterations." and "Ensure the restraintmask number is 1 lower for this step and the next one, since we're only restraining the protein and not the ligand for the last two rounds of the minimization."
- READ
- flag: same dotted-list problem as #18 (`@CA.C.N`).

**31.** same page (2P16), cpptraj.hbond.in
- program/variable: cpptraj `hbond ... solventacceptor`
- mask: `:WAT@O`
- tutorial says: not stated
- READ
- flag: none. This is the plausible correct form of the `:WAT@-O` seen elsewhere.

**32.** https://ringo.ams.stonybrook.edu/index.php/2024_AMBER_tutorial_1_with_PDBID_2ITO
- program/variable: `restraintmask` files 1-7 and files 8-9
- mask: `":1-325 & !@H="` / `":1-324@CA.C.N"`
- tutorial says: "In our example, the protein is residues 1-324 and the ligand is 325." and "Note, for files 1-7, set the restraint mask to the entire system (1-325). For files 8-9, set the restraint mask to cover only the receptor (1-324)."
- READ
- flag: (a) "entire system (1-325)" is protein plus ligand only; water and ions are outside 1-325 (interpretation). (b) The dotted list, as in #18.

**33.** https://ringo.ams.stonybrook.edu/index.php/2024_AMBER_tutorial_3_with_PDBID_1Y0X
- program/variable: `restraintmask` (01-07) and the prose line
- mask: `":1-263 & !@H="` / prose: `restraintmask=":1-263@CA,C,N", ! atoms to be restrained.`
- tutorial says: "We see that there are 263 residues in our complex.  262 in the protein and one for the ligand." and "In the above input file you'll see a line:" followed by the prose mask
- READ
- flag: the same text/file mismatch as #17 (the file above uses `& !@H=`), and the same backwards "@H=" explanation as #16.

**34.** same page (1Y0X), 08/09.equil.mdin
- program/variable: `restraintmask`
- mask: `":1-262@CA.C.N"`
- tutorial says: "! atoms to be restrained, only the backbone"
- READ
- flag: the dotted list, as in #18.

**35.** same page (1Y0X), cpp_hbonds.in
- program/variable: cpptraj `hbond hb1` / `hbond hb2`
- mask: `hbond hb1 :1-263 ... solventacceptor :WAT@-O` / `hbond hb2 :1-263 out 1y0x_lig.hbond.out ... solventacceptor :WAT`
- tutorial says: "Be sure that the hbobnd hb1 parameter corresponds to the residue numbers of the relevant ligand AND receptor (490 in our case)."
- READ
- flag: (a) **wrong system's number.** The text says "490", which is the 4S0V system, while this page's complex is 263 residues. (b) `hb2` writes "lig" output files but uses the same full-complex mask `:1-263` as `hb1` (not stated why). (c) `@-O`, as in #24.

**36.** https://ringo.ams.stonybrook.edu/index.php/2022_AMBER_tutorial_1_with_PDBID_6ME2
- program/variable: `restraintmask` steps 8-9 and production
- mask: `":1-433@CA,C,N"` / `":1-432@CA,C,N"`
- tutorial says: "Note that the restraint mask in files 8 and 9 have to be specified to the relevant system being simulated." and "The restraint mask should be modified on this file as well to only include the receptor, not the ligand (i.e., it should be one fewer than the restraint mask value in the 8th input file from the previous directory)."
- READ
- flag: see #37.

**37.** same page (6ME2), cpptraj analysis
- program/variable: cpptraj `rmsd ... reference`, ligand `rmsd`, receptor `rmsd`, `hbond hb1`
- mask: `:1-263@CA` / `":254&!(@H=)"` / `":1-253&!(@H=)"` / `:1-263`
- tutorial says: "The reference mask should contain both the ligand and receptor in its value." "And check that the reference mask only factors in the ligand in this file." "Be sure that the hbobnd hb1 parameter corresponds to the residue numbers of the relevant ligand and receptor."
- READ
- flag: **residue numbers contradict each other on the same page.** The restraint masks put the complex at 433 residues with the ligand last (#36). The analysis treats the ligand as 254, the receptor as 1-253 and the complex as 1-263. Even taken alone, ligand 254 plus receptor 1-253 does not give 1-263. The analysis block looks copied from another system; the output filenames say "calcipotriol", while this page's ligand is "JEV".

**38.** https://ringo.ams.stonybrook.edu/index.php/2022_AMBER_tutorial_3_with_PDBID_1X70
- program/variable: `restraintmask` step 8, step 9 and production
- mask: `":1-729@CA,C,N"` / `":1-728@CA,C,N"`
- tutorial says: "The one for step 8 should include both the receptor and the ligand, and the one for step 9 should include only the receptor. ... Search for the residue labelled LIG, and that will be the number for step 8 (in our case it was 729), and for step 9, it will be 1 number less (removes ligand from the mask)."
- READ
- flag: same ligand-name filter issue as #27 (does `@CA,C,N` catch any ligand atoms?). The analysis masks (`:1-729@CA`, `":729&!(@H=)"`, `":1-728&!(@H=)"`, hbond `:1-729`) agree with each other.

**39.** https://ringo.ams.stonybrook.edu/index.php/2017_AMBER_tutorial_with_4qmz
- program/variable: `restraintmask` (01 to 07)
- mask: `":1-288 & !@H="`
- tutorial says: "In the first minimization step, we use a large restraint_wt on all heavy atoms (5.0 kcal/molA^2). Thus, only hydrogens are allowed to relax and only steric clashes involving hydrogens are removed."
- READ
- flag (interpretation): the mask covers heavy atoms of residues 1-288 only, so water and ion heavy atoms are also free to relax. "only hydrogens are allowed to relax" overstates what the mask does.

**40.** same page (4qmz), parameter glossary under 01.min.in
- program/variable: `restraintmask` (explanatory text)
- mask: `':1-224 & !@H='`
- tutorial says: "restraintmask = ':1-224 & !@H='; String that specifies restrained atoms (all atoms except hydrogens are restrained)"
- READ
- flag: **the glossary uses a different residue range (1-224)** from every input file on the page (1-288). This glossary line appears twice on the page.

**41.** same page (4qmz), equil 08/09, production and analysis
- program/variable: `restraintmask`; cpptraj `rmsd`, ligand `rmsd`, `hbond`
- mask: `":1-287@CA,C,N"` / `:1-287@CA` / `":288&!(@H=)"` / `hbond hb1 :1-288 ... solventdonor :WAT solventacceptor :WAT`
- tutorial says: "Next is to compute ligand rmsd versus the crystal structure pose" and "Next is to analyze hydrogen bonding between the ligand and the enzyme residues."
- READ
- flag: none beyond #40.

**42.** https://ringo.ams.stonybrook.edu/index.php/2018_AMBER_tutorial_with_1c87
- program/variable: `restraintmask` (all equil steps), production `restraintmask`, ligand `rmsd`
- mask: `":1-298 & !@H="` / `":1-298@CA,C,N"` / `":298&!(@H=)"`
- tutorial says: "Next is to compute ligand rmsd vs. the crystal structure pose and histogram the RMSD."
- READ
- flag: unlike the other pages, the production restraint includes the ligand residue (298). The page gives no reason. (The `@CA,C,N` filter caveat from #27 applies.)

**43.** same page (1c87), hbond
- program/variable: cpptraj `hbond hb1`
- mask: `:1-297` (with `solventdonor :WAT solventacceptor :WAT@O`)
- tutorial says: "We can find out hydrogen bonding between the ligand and the enzyme residues." and "We can take a look at the h-bonds with ligand."
- READ
- flag: **leaves out the ligand.** On this page the ligand is residue 298 (#42), so `:1-297` excludes it, while the text says the analysis is of ligand–enzyme hydrogen bonds.

---

### C. York group tutorials (Amber workshop material, FE-ToolKit / AmberFlow / AmberStudio)

**44.** https://yorkgrouptutorials-db4433.gitlab.io/ModularTutorials/Alchemical/ABFE_of_Tyk2/equilibrate_endstates.html, aqueous (binder) leg
- program/variable: pmemd `restraintmask` (minimization, heating, "Lower Protein Restraints 1-5")
- mask: `':1&!@H='`
- tutorial says: section headings only ("Lower Protein Restraints 1" and so on). The warning on the page says "plus 1 to account for the ligand being the first residue."
- READ
- flag: the "Lower Protein Restraints" headings in the aqueous leg, where only the ligand is present. The mask itself (the ligand's heavy atoms) is consistent.

**45.** same page, complex leg
- program/variable: pmemd `restraintmask`
- mask: `':1-289&!@H='`
- tutorial says: "The primary difference between these mdin files and the previous ones is the protein restraint mask 1-289, which restrains the protein residues in addition to the ligand." and "The key change to make is to adjust the protein residue range in the restraint mask (e.g. 1-289) to match the protein you are working with, plus 1 to account for the ligand being the first residue."
- READ
- flag: none.

**46.** same page, "Backbone Binder" step (appears in both legs)
- program/variable: pmemd `restraintmask`
- mask: `'@CA,N,C | :1&!@H='`
- tutorial says: step name "Backbone Binder Restraints" (mermaid diagram); no further description
- READ
- flag (interpretation): in the aqueous leg there is no protein, so `@CA,N,C` can match only ligand atoms that happen to be named CA, N or C. The "backbone" part of the mask is a leftover there.

**47.** https://yorkgrouptutorials-db4433.gitlab.io/ModularTutorials/Alchemical/ABFE_of_Tyk2/tutorial.html
- program/variable: AmberFlow `FlowRoeRelax1(...)` keyword masks
- mask: `complex_full_restraint_mask=":1-289"` / `complex_noh_restraint_mask=":1-289&!@H="` / `binder_full_restraint_mask=":1"` / `binder_noh_restraint_mask=":1&!@H="` / `bb_restraint_mask="@CA,N,C | :1&!@H="`
- tutorial says: "The parameters used here are appropriate for the Tyk2 system, which has 288 residues and a single ligand residue (hence 1-289) in the complex restraint mask (which includes the ligand as residue 1)."
- READ
- flag: none. These agree with #44 to #46.

**48.** same page (ABFE tutorial), `FlowABFE7(...)`
- program/variable: AmberFlow `heating_restraint_mask`, `complex_rmsd_mask1`, `complex_rmsd_mask2`
- mask: `":1-289&!@H="` / `":1 & !@H="` / `"@CA "`
- tutorial says: not stated
- READ
- flag: `"@CA "` has a trailing space inside the quotes (verbatim). Interpretation: it selects every atom named CA in the complex, mostly protein Cα.

**49.** https://yorkgrouptutorials-db4433.gitlab.io/ModularTutorials/Alchemical/ABFE_of_Tyk2/anhilate_binder.html (also in the 2026 SSB Day4 HandsOn10-ABFE page)
- program/variable: pmemd TI `timask1`, `timask2`, `scmask1`, `scmask2`
- mask: `timask1 = ':1'` / `timask2 = ''` / `scmask1 = ':1'` / `scmask2 = ''`
- tutorial says: "we can now slowly annihilate the ligand from the equilibrated complex and binder end-states. Roughly, in both cases this involves starting from the end-state where \(\lambda = 0\) and gradually turning off the ligand’s interactions with its environment until it is fully decoupled at \(\lambda = 1\)."
- READ
- flag: none. The ligand is residue 1 according to #45.

**50.** same page (anhilate_binder), complex-leg equilibration/production mdins
- program/variable: pmemd `rmsd_mask(1)`, `rmsd_mask(2)`, `crgmask`
- mask: `rmsd_mask(1)    = ':1 & !@H='` / `rmsd_mask(2)    = '@CA '` / `crgmask         = ""`
- tutorial says: not stated
- READ
- flag: none. (Trailing space in `'@CA '`, as in #48.)

**51.** https://yorkgrouptutorials-db4433.gitlab.io/ModularTutorials/Alchemical/RBFE_of_Tyk2/soft-core-potentials.html and the linked example `_downloads/4f28c26ae16861f226fe2a650d6876de/tyk2_softcore.tar.gz` (sp_lam_1.0.mdin)
- program/variable: pmemd TI `timask1`, `scmask1`, `timask2`, `scmask2`
- mask: `timask1 = ':LIG',` / `scmask1 = ':LIG',` / `timask2 = '',` / `scmask2 = '',`
- tutorial says: "In this case, you are just looking at a single ligand in which we are treating the whole ligand as soft-core."
- READ. **pmemd's own verdict** is in the tarball's sp_lam_1.0.mdout (Amber 24 pmemd.cuda): "TI Mask 1 :LIG; matches     32 atoms", "TI Mask 2  matches      0 atoms", "SC Mask 1 :LIG; matches     32 atoms".
- flag: none for the mask. Unrelated mismatches in the same file: the page says the example is "in vacuum", but the mdin has `ntb = 1`; the title says "lambda = 0.125", but `clambda = 1.0`.

**52.** same page (soft-core-potentials), last edit
- program/variable: pmemd TI `timask1`, `timask2` (with `ifsc = 0`)
- mask: `timask1 = ':LIG',` / `timask2 = ':LIG',`
- tutorial says: "Finally, let’s fully revert to linear scaling."
- READ (the same block is on the 2026 SSB Day4 HandsOn9-RBFE page)
- flag (interpretation, unverified): in this single-ligand system, timask1 and timask2 select the same 32 atoms. TI normally expects two separate regions, one for each end state. The page does not say whether pmemd accepts an identical pair or what it computes. I did not check the AMBER manual's rule.

**53.** https://yorkgrouptutorials-db4433.gitlab.io/TutorialsInProgress/pKa/tutorial.html (listed under "Tutorials In Progress")
- program/variable: TI mdin template `timask1`, `timask2`, `scmask1`, `scmask2`
- mask: `timask1     = '@260-291'` / `timask2     = '@2189-2219'` / `scmask1     = '@291'` / `scmask2      = ''`
- tutorial says: "“timask1” contains the atoms of the first copy of C10 in its protonated form (residue 9 in the merged topology), “timask2” contains the atoms in the second copy of C10 (residue 70 in the merged topology), “scmask1” contains C10:H3, and “scmask2” is empty because C10:H3 is disappearing and not present in the second copy."
- READ
- flag: **the residue number in the text is wrong.** The same page's merge command is `timerge ":1-69" ":70-138" ":9" ":78" ":69" ":138"`, with "residue 78 is its copy". So the second copy of C10 is residue 78, not 70. The atom counts are consistent (my arithmetic): 32 atoms in timask1, 31 in timask2, and 31 in each once the soft-core atoms are removed.

**54.** same page (pKa), ACES variant
- program/variable: TEMPLATE.sh variables that become timask1/2 and scmask1/2
- mask: `TI1='@260-291,2220-2238'` / `TI2='@2189-2219,2239-2257'` / `SC1='@291,2220,2231,2233-2235'` / `SC2='@2239,2250,2252-2254'`
- tutorial says: "The TEMPLATE.sh script must be modified to put the ligand in the TI regions and the OCH3 group in the softcore regions"
- READ
- flag: none. My arithmetic check: TI1 has 51 atoms and TI2 has 50; after removing SC1 (6) and SC2 (5), 45 atoms remain in each. Each copy's ligand soft-core part is 5 atoms (O, C, 3H = OCH3), with a consistent +19 offset between the copies.

**55.** https://yorkgrouptutorials-db4433.gitlab.io/ModularTutorials/MTR1_QMMM/GenWins.html (the same string is in RunPathCV, 2024 UCSD 04_qmmmMTR1, 2024 UCSD 06 MTR1, 2026 SSB Day2 HandsOn4 and Day5 HandsOn11)
- program/variable: sander/pmemd QM/MM `qmmask`
- mask: `qmmask  = ':69|@272-282,290-291,1975-1988'`
- tutorial says: "The QM region is defined by the mask ‘:69|@272-282,290-291,1975-1988’ which includes the entire ligand (:69), the nucleobase of C10 (@272-282,290-291) and the nucleobase of A63 (@1975-1988)."
- READ
- flag: see #57 on residue naming.

**56.** same page (GenWins)
- program/variable: `noshakemask`
- mask: `noshakemask = ":69|@272-282,290-291,1975-1988"    ! do not shake these`
- tutorial says: "The noshakemask (pink) contains the same mask as the QM region, thus we will not shake QM atoms"
- READ
- flag: none.

**57.** https://yorkgrouptutorials-db4433.gitlab.io/WorkshopTutorials/2026_Amber_Workshop_SSB/Day2/HandsOn4-FESurface.html
- program/variable: `qmmask` (also passed to mm2qmmm.py `-m`)
- mask: `":69|@272-282,290-291,1975-1988"`
- tutorial says: "The QM mask corresponding to the bases of C9 and A62 and the O6mG cofactor is “:69|@272-282,290-291,1975-1988”, and the net QM charge is +1 due to the protonated C residue"
- READ
- flag: **the same mask is described with different residue names.** Here it is "C9 and A62"; in GenWins (#55) it is "C10 and A63". The pKa page explains the offset ("residue 9 corresponds to C10 in the MTR1 structure"), so this is a numbering-convention difference, not a mask error. Still, a reader cannot tell from either page alone which numbering is meant.

**58.** https://yorkgrouptutorials-db4433.gitlab.io/TutorialsInProgress/DeltaMLP/tutorial.html (in progress)
- program/variable: `qmmask`, `noshakemask`, `&dprc mask`
- mask: `':81,220-224|@1-10,22-39,55-60,706-710,723-736,1969-1990,1992-1993'` (qmmask, single quotes) / `":81,220-224|@1-10,22-39,55-60,706-710,723-736,1969-1990,1992-1993"` (noshakemask and dprc `mask=`, double quotes)
- tutorial says: "Modify the QM region, noshake mask, and dprc mask for your system. The mask in the dprc section should be your QM region."
- READ
- flag: none. The three masks are identical apart from the quote style.

**59.** https://yorkgrouptutorials-db4433.gitlab.io/ModularTutorials/Bookend/eqsampling/eqsampling.html (also noneqsampling, 2024 UCSD 06 mm2qmmm and 2026 SSB Day5 HandsOn12)
- program/variable: `qmmask`, `noshakemask`, dprc `mask`
- mask: `qmmask  = ':1'` / `noshakemask=':1'` / `mask=":1"`
- tutorial says (mm2qmmm page): "The machine learning potential is applied to the atoms in mask, which is the selected QM atoms."
- READ
- flag: none. The system is a single solute, acetic acid, as residue 1 (interpretation, from the page's "for acetic acid").

**60.** https://yorkgrouptutorials-db4433.gitlab.io/ModularTutorials/MISC/introduction_to_CPPTRAJ/tutorial.html (the same text is in 2026 SSB Day1 HandsOn1-VMD)
- program/variable: cpptraj `center ... mass origin`, `autoimage`, `center ... mass reference`
- mask: `'!@H= & !:MG,NA,CL,PB,ZN,MN,WAT'`
- tutorial says: "This mask selects all atoms that are not hydrogens, water, nor magnesium, sodium, chlorine, or lead ions." cpptraj output printed on the page: "Mask [!@H* & !:MG,NA,CL,PB,ZN,MN,WAT] corresponds to 1459 atoms."
- READ
- flag (minor): the description leaves out ZN and MN, which the mask also excludes.

**61.** same page (intro to CPPTRAJ)
- program/variable: shell variable `solute` (an example only)
- mask: `solute='!@H= & !:MG,NA,CL,PB,ZN,MN,WAT & :1-69'`
- tutorial says: "You can create a more specific mask to center around the catalytic residues or a ligand. For example:"
- READ
- flag: :1-69 is not "catalytic residues or a ligand". The same page calls 1-69 "the entire nucleic molecule" (#63), and the York pKa and QM/MM pages say residue 69 is the ligand. Interpretation: :1-69 is the whole RNA plus the ligand.

**62.** same page (intro to CPPTRAJ), wrap.in and the bash version
- program/variable: cpptraj `center` / `autoimage`
- mask: `'!@H= & !:MG= & !:NA= & !:CL= & !:PB= & !:WAT='`
- tutorial says: the page's symbol key: "= — Wildcard (matches anything that begins with the preceding text)"
- READ
- flag: none.

**63.** same page (intro to CPPTRAJ), ctraj.RMSD_MTR1.in
- program/variable: cpptraj `rms ToFirst <mask> first ... mass`
- mask: `:1-69&!@H=`
- tutorial says: "using all non-hydrogen atoms in the residues 1 through 69. This residue selection is the entire nucleic molecule."
- READ (also in 2024 UCSD 01_vmd_visualization)
- flag: "entire nucleic molecule" versus residue 69 being the ligand (O6mG) on the other York MTR1 pages (#55, #53). I did not verify that both use the same topology.

**64.** same page (intro to CPPTRAJ), ctraj.RMSF_MTR1.in
- program/variable: cpptraj `rms ... reference mass` (the fit before `atomicfluct`)
- mask: `:1-69&!@H`
- tutorial says: not stated for this line. The two `atomicfluct` lines in the same script use `:1-69&!@H=` (#65).
- READ (also in 2024 UCSD 01_vmd_visualization)
- flag: **missing `=`.** Without the wildcard, `@H` matches only atoms named exactly "H", so this fit mask keeps nearly all hydrogens (interpretation, from the manual syntax). It is inconsistent with the heavy-atom masks used on the very next lines.

**65.** same page (intro to CPPTRAJ)
- program/variable: cpptraj `atomicfluct ... byres` and `average`
- mask: `:1-69&!@H=`
- tutorial says: "atomicfluct out RMSF.dat :1-69&!@H= byres and atomicfluct out RMSF_Bfact.dat :1-69&!@H= byres bfactor. atomicfluct is the command for an RMSF calculation."
- READ
- flag: none.

**66.** https://yorkgrouptutorials-db4433.gitlab.io/WorkshopTutorials/2024_Amber_Workshop_UCSD/01_vmd_visualization/tutorial.html
- program/variable: cpptraj `center ... mass`, `autoimage`, `center ... reference`
- mask: `:L01`
- tutorial says: "The mask :L01 specifies all the atoms in residue L01." cpptraj output on the page: "Mask [:L01] corresponds to 8 atoms."
- READ
- flag: none. Acetic acid has 8 atoms, so the count is consistent.

**67.** https://yorkgrouptutorials-db4433.gitlab.io/WorkshopTutorials/2024_Amber_Workshop_UCSD/02_intoMD/tutorial.html (the same mask appears 12 times in 2026 SSB Day1 HandsOn2-MD)
- program/variable: pmemd `restraintmask`
- mask: `restraintmask = '!@H= & !:NA,CL,MG,WAT', ! (restrain only solute)`
- tutorial says: "all atoms not (!) included in the mask @H= and not :NA,CL,MG,WAT. This means all heavy atoms that are not sodium, chloride, magnesium, or water will experience the positional restraint (ie. the RNA heavy atoms are effectively frozen in place)."
- READ
- flag: none.

**68.** same page (02_intoMD)
- program/variable: cpptraj `center` / `autoimage`
- mask: `'!@H= & !:MG= & !:NA= & !:CL= & !:WAT='`
- tutorial says: "In this input file we set the center of mass of the RNA at the origin, then we image the solute around the RNA."
- READ
- flag: none.

**69.** https://yorkgrouptutorials-db4433.gitlab.io/WorkshopTutorials/2026_Amber_Workshop_SSB/Day5/HandsOn13-AmberStudio.html, run_equil.py
- program/variable: AmberStudio `FlowRoeRelax(...)` masks
- mask: `complex_full_restraint_mask=":1-178"` / `complex_noh_restraint_mask=":1-178&!@H="` / `binder_full_restraint_mask=":179"` / `binder_noh_restraint_mask=":179&!@H="` / `bb_restraint_mask="@CA,N,C | :1&!@H="`
- tutorial says: not stated (system: Tyk2 target with ligand ejm31)
- READ
- flag: **numbering does not hold together.** The binder (ligand) is residue 179 here, yet `bb_restraint_mask` still adds `:1&!@H=` (the ligand-as-residue-1 convention from #47), so on this system it would restrain protein residue 1 instead of the ligand.

**70.** same page (AmberStudio), run_abfe.py
- program/variable: AmberStudio `FlowABFEProduction(...)`
- mask: `heating_restraint_mask=":1-290&!@H="` / `complex_restraint_mask=":1-290&!@H="`
- tutorial says: "Most are reproduced from the earlier tutorial"
- READ
- flag: **a third residue count for the Tyk2/ejm31 complex.** This page uses 1-290; the equilibration on the same page implies 179 (#69); and the earlier York ABFE tutorial says "288 residues and a single ligand residue (hence 1-289)" (#47). The page does not explain the difference.

---

### D. AMBER-hub (Univ. of Utah CHPC, cpptraj material)

**71.** https://amberhub.chpc.utah.edu/amber-hub/start-here-rmsd-analysis-in-cpptraj/
- program/variable: cpptraj `rms ToFirst <mask> first out rmsd1.agr mass`
- mask: `:1-13&!@H=`
- tutorial says: "using all non-hydrogen atoms in residues 1 to 13". cpptraj output on the page: "Target mask: [:1-13&!@H*](116)" for "trpzip2.ff10.mbondi.parm7, 220 atoms, 13 res".
- READ
- flag: none.

**72.** https://amberhub.chpc.utah.edu/amber-hub/introduction-to-data-sets/
- program/variable: cpptraj `distance end-to-end <mask1> <mask2>`
- mask: `:1` / `:13`
- tutorial says: not stated beyond the data set name "end-to-end". Interpretation: the distance between the centers of residues 1 and 13, the two ends of the 13-residue trpzip2.
- READ
- flag: none.

**73.** https://amberhub.chpc.utah.edu/cpptraj-cookbook/cpptraj-one-liners/
- program/variable: cpptraj `rms`
- mask: `^1&@C,CA,N` / `^2&@C,CA,N` (the second with `nofit`)
- tutorial says: "Do RMSD analysis of the first molecule (which presumably is chain A) use the ^ operator. Then do RMSD of chain B (molecule 2) but still using the previous fit (to molecule 1) you would add the nofit keyword"
- READ
- flag: none.

**74.** same page (one-liners)
- program/variable: cpptraj command-line `--mask` / `--resmask` / `--charge`
- mask: `:1` / `:1-10`
- tutorial says: "To inspect residue number one from a topology. This also works for atoms using @1 instead of :1" / "To view more information (#Res, Name, First atom, Last atom, number of atoms, #Orig and #Mol) for residues one through ten."
- READ
- flag: none.

**75.** same page (one-liners), loop example on a CHARMM PSF
- program/variable: cpptraj `strip`, `rms`, `distance`
- mask: `:SOD,CLA,TIP3,TIP,POPC` / `@CA` / `:1088@CA :1370@CA` (and four more `:<n>@CA` pairs)
- tutorial says: not stated
- READ
- flag: none. These are CHARMM residue names, which shows that the masks are force-field-specific (interpretation).

---

### E. BioExcel Building Blocks AMBER workflows (Jupyter notebooks on GitHub)

The notebooks pass masks to sander as Python strings with escaped quotes (for example `'\":*&!@H=\"'`), and that escaped form is what's quoted below. The resulting mdin string is shown after the arrow; that rendering is my interpretation.

**76.** https://github.com/bioexcel/biobb_wf_amber/blob/main/biobb_wf_amber/notebooks/md_setup/biobb_wf_amber_md_setup.ipynb (cell 19; the same mask is in md_setup_lig cell 33)
- program/variable: sander `restraintmask` (min_vacuo)
- mask: `'\":*&!@H=\"'` → `":*&!@H="`
- tutorial says: "**Hydrogen** minimization, applying **position restraints** (50 Kcal/mol.$Å^{2}$) to the **protein heavy atoms**."
- READ
- flag: none. This form is equivalent to `!@H=` per the manual.

**77.** same notebook (md_setup), cells 37-39
- program/variable: sander `restraintmask` (solvated minimization)
- mask: `'\"!:WAT,Cl-,Na+\"'` → `"!:WAT,Cl-,Na+"`, code comment `# Restraining solute`, `restraint_wt : 50.0`
- tutorial says: markdown: "**Restraining heavy atoms** with a force constant of 15 Kcal/mol.$Å^{2}$ to their initial positions."
- READ
- flag: **the text and the code disagree.** The mask restrains all solute atoms, hydrogens included (no `&!@H=`), and the weight is 50, not 15.

**78.** same notebook (md_setup), cells 49-51 (NVT; also used for NPT)
- program/variable: sander `restraintmask`
- mask: `'\"!:WAT,Cl-,Na+ & !@H=\"'` → `"!:WAT,Cl-,Na+ & !@H="`, comment `# Restraining solute heavy atoms`
- tutorial says: "Protein **heavy atoms** will be restrained using position restraining forces"
- READ
- flag: none.

**79.** https://github.com/bioexcel/biobb_wf_amber/blob/main/biobb_wf_amber/notebooks/md_setup_lig/biobb_wf_amber_md_setup_lig.ipynb (cells 31, 37, 38)
- program/variable: sander `restraintmask` (built in Python)
- mask: `'\":' + ligandCode + '\"'` → `":JZ4"` (`ligandCode` is JZ4 according to `'heteroatoms' : [{"name": "JZ4"}]`)
- tutorial says: cell 37: "**System** minimization, with **restraints** only on the **small molecule**, to avoid a possible change in position due to **protein repulsion**." Cell 31 (overview of the same step): "[Step 2](#minv_2): **System** minimization, with **no restraints**."
- READ
- flag: **the text contradicts itself, and the restraint may not be active.** The two descriptions of the same step disagree. Also, the `mdin` dict in cell 38 sets `restraintmask` and `restraint_wt : 500.0` but no `'ntr' : 1`, and the call passes no `input_ref_path`. ntr=1 is the switch that turns positional restraints on (the CC lesson's own parameter table: "ntr | 1 | Use cartesian harmonic restraints"). Whether biobb's `min_vacuo` preset sets ntr=1 is not stated; I did not check biobb's defaults.

**80.** same notebook (md_setup_lig), cells 51-53
- program/variable: sander `restraintmask`
- mask: `'\"!:WAT,Cl-,Na+\"'` → `"!:WAT,Cl-,Na+"`, comment `# Restraining solute`, `'restraint_wt' : 15.0                       # With a force constant of 50 Kcal/mol*A2`
- tutorial says: "**Restraining heavy atoms** with a force constant of 15 15 Kcal/mol.$Å^{2}$ to their initial positions."
- READ
- flag: the mask includes hydrogens, although the text says "heavy atoms"; and the code comment says 50 while the value is 15.

**81.** https://github.com/bioexcel/biobb_wf_amber/blob/main/biobb_wf_amber/notebooks/md_setup_ph/biobb_wf_amber_md_setup_ph.ipynb (cells 29-31, 35-37 and later)
- program/variable: sander `restraintmask` (minimization, heating, ...)
- mask: `'\"@CA,C,O,N\"'` → `"@CA,C,O,N"`
- tutorial says: "applying **position restraints** (10 Kcal/mol.$Å^{2}$) to the **protein backbone atoms**." and the code comment "# Restraints on the backbone atoms only"
- READ
- flag: **not limited to protein.** The mask has no residue or solvent restriction, and the system is solvated (TIP3PBOX, set in cell 20). Any water oxygen named O would be restrained too. The cpptraj manual's own example `:1-500@O&!(:WAT|:LYS,ARG)` explicitly excludes `:WAT` from an `@O` selection, which implies that water oxygens match `@O`. I did not check the atom names in this topology.

**82.** https://github.com/bioexcel/biobb_wf_amber/blob/main/biobb_wf_amber/notebooks/abc_setup/biobb_wf_amber_abc_setup.ipynb and its config file https://raw.githubusercontent.com/bioexcel/biobb_wf_amber/main/biobb_wf_amber/notebooks/abc_setup/ABCix_config_files/step1.in
- program/variable: sander `restraintmask` (steps 1-4, 6, 7); the notebook overrides the value from the file
- mask: in step1.in: `restraintmask = ":1-40&!@H="`; notebook override: `'\":DA,DC,DG,DT,D=3,D=5&!@H=\"'` → `":DA,DC,DG,DT,D=3,D=5&!@H="`
- tutorial says: markdown: "restraintmask = :1-40&!@H=;&nbsp;&nbsp;&nbsp;&nbsp;     Restraints on DNA atoms only" (HTML entities as in the notebook source); code comment: "# Overwrite DNA heavy atoms mask to make it more generic"
- READ
- flag: none. The markdown shows the file's mask, while the code actually sends the override. Interpretation: `D=3`/`D=5` use the `=` wildcard ("Same as '*'" per the manual) to catch 3'/5'-terminal residue names such as DA3 and DC5.

**83.** same notebook (abc_setup), step 8 and ABCix_config_files/step8.in
- program/variable: sander `restraintmask`
- mask: in step8.in: `restraintmask = ":1-40@P,O5',C5',C4',C3',O3'"`; notebook override: `'\":DA,DC,DG,DT,D=3,D=5&@P,O5\',C5\',C4\',C3\',O3\'\"'`
- tutorial says: "Releasing **position restraints** from the atoms of the **DNA bases** (keeping only backbone atoms restrained)."
- READ
- flag: none.

---

### F. Other sites (personal or lab pages)

**84.** https://drrajeshsingh.wordpress.com/tutorials/free-energy-calculations/ ("Free Energy Calculations using AMBER-MMPBSA.py module", for CHARMM-GUI inputs)
- program/variable: ante-MMPBSA.py `-s` (complex)
- mask: `:CLA:SOD:TIP3`
- tutorial says: "For COMPLEX *.prmtop:"
- READ
- flag: the same undocumented `:A:B` chaining as #21.

**85.** same page
- program/variable: ante-MMPBSA.py `-s` (membrane variant)
- mask: `“:CLA:SOD:POPC:WAT”` (typographic quotes, as rendered)
- tutorial says: "(add :POPC too for membrane proteins)"
- READ
- flag: (a) the water name changes from TIP3 (used everywhere else on the page for CHARMM-GUI water) to WAT. (b) The typographic quotes “ ” are not ASCII quotes; pasted into a shell they become part of the argument (interpretation).

**86.** same page
- program/variable: ante-MMPBSA.py `-s` (receptor)
- mask: `:CLA:SOD:TIP3:UNK`
- tutorial says: "For RECEPTOR *.prmtop:"
- READ
- flag: none beyond the chaining.

**87.** same page
- program/variable: ante-MMPBSA.py `-s` (ligand)
- mask: `“!(:UNK)”`
- tutorial says: "For LIGAND *.prmtop:"
- READ
- flag: typographic quotes, as in #85.

**88.** same page, mmpbsa-strip-GB.in and mmpbsa-strip.in
- program/variable: MMPBSA.py `receptor_mask`, `ligand_mask`, `strip_mask`
- mask: `receptor_mask=”:1-542″, ligand_mask=”:543″, strip_mask=”:SOD:CLA:TIP3″,`
- tutorial says: "######Residue No. for receptor_mask and ligand_mask ######## check the residue# in ‘ ../step3_charmm2amber.crd’ file via -> vi ../step3_charmm2amber.crd and search-> :/UNK"
- READ (the HTML source has `&#8221;` and `&#8243;`, that is ” and ″, around each mask)
- flag: **the quote characters are not ASCII.** WordPress has replaced the quotes with ” (closing double quote) and ″ (double prime). Interpretation: copied into an MMPBSA.py input, these are not valid quote characters.

**89.** https://www.med.unc.edu/pharm/miaolab/resources/gamd/tutorial/ (Miao lab GaMD; plain curl got a stub page, so it was fetched with a browser user-agent)
- program/variable: pmemd LiGaMD (`igamd = 11`) and Pep-GaMD (`igamd = 15`): `timask1`, `scmask1`, `timask2`, `scmask2`
- mask: `timask1 = ‘:225’, scmask1 = ‘:225’,` / `timask2 = ”, scmask2 = ”,`
- tutorial says: not stated on the tutorial page. The GaMD manual (https://www.med.unc.edu/pharm/miaolab/resources/gamd/manual/, READ) says: "timask1 Specifies atoms of the first (bound) ligand or peptide in ambmask format when igamd = 10, 11, 14 or 15." and "nlig ... Use residue ID of the first (bound) ligand in timask1 and scmask1".
- READ
- flag: **the quote characters are not ASCII.** ‘ ’ around `:225`, and the empty string `''` has been turned into a single ” (the raw HTML has `&#8221;`). Copied as shown, `timask2 = ”` is not an empty string.

**90.** same page (GaMD), PPI-GaMD (`igamd = 17`)
- program/variable: `timask1`, `scmask1` with `bgpro2atm`, `edpro2atm`
- mask: `timask1 = ‘:1-110’, scmask1 = ‘:1-110’,` / `timask2 = ”, scmask2 = ”,` / `bgpro2atm=1, edpro2atm=1453,`
- tutorial says: not stated. Manual: "bgpro2atm    Start atomic number of the second protein." "edpro2atm    The final atomic number of the second protein."
- READ
- flag (interpretation): residue 1 contains atom 1, so the "second protein" atom range 1-1453 overlaps the first-protein mask `:1-110`. As printed, the example looks self-contradictory, unless it is only a schematic. The manual's `timask1` definition also lists igamd 10, 11, 14 and 15, not 17. Same quote problem as #89.

**91.** https://signe.teokem.lu.se/ulf/Methods/rel_free.html (Ulf Ryde, "Relative binding affinities using Amber"), sample sander.in4
- program/variable: sander TI `timask1`, `scmask1`
- mask: `timask1=":GU1",scmask1="GU1@C8,H81,H82,H83",`
- tutorial says: "The lambda=0 state is that defined in timask1." and "Note that the soft-core mask also defines which atoms will have different coordinates for the two ligands."
- READ
- flag: **`scmask1` has no leading `:`.** Every elementary selection in the manual starts with `:`, `@` or `^`, so this was most likely meant to be `:GU1@C8,H81,H82,H83`. I did not verify how sander parses it.

**92.** same page, the next line of sander.in4
- program/variable: sander TI `timask2`, `scmask2`
- mask: `timask2=":GU2,"scmask2="GU2@H8"`
- tutorial says: not stated beyond #91
- READ (the raw HTML line is identical)
- flag: **misplaced quote.** The comma sits inside the quotes, which gives the mask `:GU2,` and leaves no separator before `scmask2`. `scmask2` also lacks the leading `:`. In addition, the page's "Sample fep.in file" lists the soft-core atoms as `C8,H81,H82,H83` and `H5`, while scmask2 says `H8`. The page does not say whether the two samples describe the same system.

**93.** same page, old Amber 11 procedure (mkfep input)
- program/variable: mkfep fep.in mask lines (passed on to sander)
- mask: `":GU1 | :GU5"` / `":GU5@Cl6 | :GU1@H6"`
- tutorial says: not stated (only "Set up the fep.in file and then run mkfep <fep.in")
- READ
- flag: none. Interpretation: the first is the union of residues GU1 and GU5; the second is atom Cl6 of GU5 plus atom H6 of GU1, which looks like a perturbed-atom pair.

---

### Flags (summary)

1. **Dotted atom list `@CA.C.N`** in the backbone restraints of four Rizzo pages: 4S0V (#18), 2P16 (#30), 2ITO (#32), 1Y0X (#34). By the manual's comma-list syntax this names one atom "CA.C.N"; the production files on the same pages use commas. Likely an empty or failing restraint (not run).
2. **Prose versus file mismatch** in Rizzo 4S0V and 1Y0X: the text quotes `":1-490@CA,C,N"` / `":1-263@CA,C,N"` as "the line" in a file that actually has `& !@H=` (#17, #33). The same pages explain "@H=" as "restrain all the hydrogen atoms", which is backwards for `!@H=` (#16).
3. **Residue numbers that contradict each other on one page:** Rizzo 6ME2 (433/432 in the restraints versus 263/254/253 in the analysis, #37); Rizzo 4qmz glossary `:1-224` versus 288 in the files (#40); Rizzo 1c87 hbond `:1-297` leaves out ligand 298 (#43); Rizzo 1Y0X text says "490" for a 263-residue complex (#35); York AmberStudio uses 1-178/179, 1-290 and `:1` for the same Tyk2 complex (#69, #70); York pKa text says copy residue 70, where the merge command gives 78 (#53).
4. **"Backbone" defined three different ways in one course** (Compute Canada): `@CA,N,O` (no C, #1, #5), `@C,N,O` (no CA, #10), and "CA, N, O, P for protein" (#5). The manual gives `@CA,C,O,N,H`.
5. **"Including the ligand" with an atom-name filter:** `:1-490@CA` and `:1-299@CA,C,N` style masks (#20, #27, #38) keep a GAFF ligand only if it has atoms named CA, C or N (interpretation).
6. **Restraint masks that are wider than the text says:** BioExcel `@CA,C,O,N` with no solvent exclusion in a solvated system (#81); BioExcel "heavy atoms" with a mask that includes hydrogens, plus weight mismatches (#77, #80); a BioExcel ligand restraint with no `ntr=1` in its dict and a step described both as "no restraints" and as "restraints only on the small molecule" (#79); Rizzo 4qmz says "only hydrogens are allowed to relax" while the mask leaves the solvent free (#39).
7. **Syntax not documented in the cpptraj manual:** `:WAT:Na+:Cl-` / `:SOD:CLA:TIP3` chaining (#21, #84 to #88); `:WAT@-O` (#24); `":!@H="` (#26); pytraj `"... and not hydrogen"` (#14, #15); `scmask1="GU1@..."` with no `:` (#91); a misplaced quote in `timask2=":GU2,"scmask2=...` (#92).
8. **Missing wildcard:** York `rms :1-69&!@H` next to `atomicfluct :1-69&!@H=` (#64).
9. **TI and soft-core masks:** York `timask1 = ':LIG'`, `timask2 = ':LIG'` select identical atoms (#52); GaMD PPI example `:1-110` overlaps `bgpro2atm=1` (#90); the ante-MMPBSA `-n` description versus `ligand_mask=:1-243` on the Compute Canada page (#8). The York pKa and ACES TI/SC sets were checked by atom count and are consistent (#53, #54).
10. **WordPress typographic quotes** in the Singh MMPBSA and GaMD pages (#85, #87 to #90). Copied as shown, the masks are wrapped in ” ″ ‘ ’, and `''` becomes a single ”.
11. **Gold-like counts printed by the tools themselves** (useful as test fixtures): `:1-13&!@H=` → 116 atoms of 220 in trpzip2 (cpptraj, #71); `!@H= & !:MG,NA,CL,PB,ZN,MN,WAT` → 1459 atoms in MTR1 (cpptraj, #60); `:L01` → 8 atoms in acetic acid (cpptraj, #66); `:LIG` → 32 atoms for timask1 and scmask1 in ejm31 (pmemd.cuda Amber 24 mdout, #51).

### Pages tried that failed or were not used

- https://amber-md.github.io/pytraj/latest/atom_mask_selection.html returned HTTP 200, but my HTML-to-text pass gave an empty result. I did not use it; I used the cpptraj manual source (cpptraj.lyx on GitHub) instead.
- https://www.med.unc.edu/pharm/miaolab/resources/gamd/tutorial/: plain curl returned a 906-byte stub. It succeeded with a browser user-agent. A WebFetch summary of the same page paraphrased `atom_l = 4` as "Ligand atom count (4 atoms)", while the manual defines atom_l as a ligand atom's serial number, so I used no WebFetch paraphrase; every quote above comes from the raw HTML.
- The Rizzo "2023 AMBER tutorial with 4-amino-8-quinoline..." page named in the brief: I did not locate a page by that title. I covered the nine Rizzo AMBER tutorial pages that search returned (2017 4qmz, 2018 1c87, 2022 6ME2 and 1X70, 2023 4S0V, 3WZE and 2P16, 2024 2ITO and 1Y0X).
- The Compute Canada lesson has no umbrella-sampling episode on its live site or on any of its four branches (gh-pages, instructor_view, improve_jobscripts, alliance_branding). The MMPBSA masks are in episode 23 (#7 to #9). The molmodsim-md-extra-topics repo holds only "diagnosing_unstable_systems.md", which has no masks.
- Not covered for lack of time: the openfe/alchemistry pages, the Swanson "Ambertools tutorial" on GitHub, CHARMM-GUI AMBER inputs, and the Galaxy Training Network. amber.tkanai-lab.org is a mirror of the ambermd.org tutorials and was skipped as out of scope.
- ambermd.org/GPUFeatures.php was out of scope (ambermd.org). The search snippet suggested it carries `scmask1="GU1@C8,H81,H82,H83"`, but my grep of the fetched page found only the prose "Define perturbated regions in timask1, timask2" and "Define softcore regions in scmask1, scmask2", not that sample line. The missing-colon sample I recorded (#91, #92) is the one on Ryde's page.
