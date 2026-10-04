# AMBER atom-selection masks: manual, ambmask, mdin variables, cpptraj, prmtop, ParmEd

Compiled 2026-10-02. Every claim carries a source and one of four tags:

- **READ**: I read the sentence on the page, in the PDF text, or in the source file named.
- **READ-SRC**: I read it in program source code, not in documentation. Code is what runs, but the
  authors do not promise it, so it can change in any release.
- **EXECUTED**: I ran the program and the output shows it. The probe scripts and raw logs are in this
  directory (listed at the end).
- **LEAD**: it comes only from a search snippet or a secondary source. Not checked.

## Sources and versions

| Key | What | Where | Version read |
|---|---|---|---|
| AM26 | Amber 2026 Reference Manual ("Covers Amber26 and AmberTools26") | https://ambermd.org/doc12/Amber26.pdf | Server Last-Modified 31 Aug 2026. Downloaded 2026-10-02 and converted with `pdftotext -layout`. Its PDF page numbers equal its printed page numbers (the printed footer on PDF page 509 reads 509), so "p. N" below means both. |
| PRMTOP | Swails, prmtop format appendix | https://ambermd.org/prmtop.pdf | PDF dated 16 May 2013, 23 pages |
| FF | Amber File Formats web page | https://ambermd.org/FileFormats.php | fetched 2026-10-02 |
| HUB | AMBER-hub, "Atom Mask Selection Syntax" (cpptraj docs) | https://amberhub.chpc.utah.edu/atom-mask-selection-syntax/ | fetched 2026-10-02 |
| CPPSRC | cpptraj source, `src/MaskToken.cpp`, `src/NameType.cpp`, `src/Parm_Amber.cpp`, `src/ArgList.cpp` | https://github.com/Amber-MD/cpptraj/blob/master/src/MaskToken.cpp (and the others in the same folder) | `master` on 2026-10-02. MaskToken.cpp last changed in commit 44dba30 (2024-06-14). Latest GitHub release tag v7.00.0 (2026-03-06). The AmberTools26 binary I ran reports "CPPTRAJ: Version V7.6.2 (AmberTools)". |
| PMSRC | pmemd source, `src/pmemd/src/findmask.F90`, `mdin_ctrl_dat.F90`, `master_setup.F90` | local: `~/Downloads/pmemd26_src/src/pmemd/src/` (the Amber26 pmemd source tarball, which is distributed through https://ambermd.org/GetAmber.php, not on a public URL) | Amber26 pmemd, as built at `~/Downloads/pmemd26` |
| PEDOC | ParmEd docs: "The Amber file classes" and "Using parmed" | https://parmed.github.io/ParmEd/html/amber.html#amber-mask-syntax and https://parmed.github.io/ParmEd/html/parmed.html#atom-selection-masks | fetched 2026-10-02 (the page reports itself as `0+untagged.3319.g7a6168d`) |
| PESRC | ParmEd source, `parmed/amber/mask.py` | https://github.com/ParmEd/ParmEd/blob/master/parmed/amber/mask.py | `master`, last changed in commit 917343a (2021-02-08). Latest release 4.3.1. |

What I executed: pmemd from the Amber26 build at `~/Downloads/pmemd26/bin/pmemd`; ParmEd 4.3.1 from
PyPI in a throwaway `uv` environment; and ambmask, cpptraj (V7.6.2) and sander from the conda-forge `ambertools` 26.0 package (osx-arm64), installed into `scratchpad/at26` for this purpose. The system for every run was the Single Particle solvated
protein (`complex.parm7` and `heat-2.rst7` in
`~/Downloads/Single Particle/Single Particle/phase3-explicit-solvent-md/_archive/submit-output-20260618/`):
27,356 atoms and 6,401 residues, of which 6,244 are WAT. It has 13 ALA residues (130 atoms) and 154 atoms
named CA. Its prmtop has an `ATOMIC_NUMBER` section and no `RESIDUE_CHAINID` or `RESIDUE_NUMBER`
section. For pmemd and sander, each probe put the mask into `restraintmask` with `ntr=1` (`imin=1`), and
the result is the engine's own line `Mask <string>; matches N atoms`. For cpptraj it is `select <mask>`
after `parm` and `reference`; for ambmask `-prnlev 1 -out short`; for ParmEd `sum(AmberMask(parm,
mask).Selection())` with the restart's coordinates loaded.

---

## 1. The Amber mask syntax in the Reference Manual (AM26 Chapter 25, pp. 509-512)

**Three selection languages exist.** "There are three ways to select atoms and residues in
AMBER-related routines: the AMBER "mask" notation, used by most programs, the cpptraj "atom
expressions", which are described under "General concepts" in the cpptraj chapter, and an older
"GROUP" specification used in sander and pmemd." AM26 p. 509, section 25. READ. So the manual itself
treats cpptraj's syntax as a different language.

The chapter's main text is the ambmask manual page (25.1.1, pp. 510-512). Section 25.1 says: "The
following lines are partially copied from the original AMBER documentation. For more details, refer
to the entire section of that documentation describing the ambmask utility." AM26 p. 509. READ.

### 1.1 Residue (`:`) and atom (`@`) selectors, lists, ranges, names and numbers

- "These start with ":" to select by residues, or "@" to select by atoms. Residues can be selected by
  numbers (given as numbers separated by commas, or as ranges separated by a dash) or by names (given
  as a list of residue names separated by commas). The same holds true for atom selections by atom
  numbers or atom names." AM26 p. 509, 25.1. READ.
- Examples given: `:1-10`, `:1,3,5`, `:1-3,5,7-9`, `:LYS`, `:ARG,ALA,GLY`, `@12,17`, `@54-85`,
  `@12,54-85,90`, `@CA`, `@CA,C,O,N,H`. AM26 pp. 509-510. READ.
- **Numbers are sequential topology numbers.** "Note that these masks use the actual sequential numbers
  of atoms in the file. This is tricky and a serious source of error. ... Do not use the original atom
  numbers from the raw PDB file you started with." AM26 p. 509. READ. Likewise for names: "Atom and
  residue names and numbers are taken from the Amber topology. Beware that the selection string works
  on those names and not the ones from the original PDB file." AM26 p. 510, 25.1.1. READ.
- **All atoms and all residues.** "":*" means all residues and "@*" means all atoms." AM26 p. 510. READ.
- **Compound form.** "[:1-10@CA] is equivalent to [:1-10 & @CA]". AM26 p. 511. READ.
- **Case.** ambmask: "Selections are case insensitive." AM26 p. 510. READ. The manual's BUGS note gives
  the consequence: "there is no way to distinguish some atom names: alpha carbon CA and a calcium ion
  Ca are a notorious example of that." AM26 p. 512. READ. EXECUTED in pmemd: `:ala` and `:ALA` both
  match 130 atoms, and `@ca` matches the same 154 atoms as `@CA`.
- **Not documented: what a mixed name-and-number list means.** The manual shows lists that are either
  all numbers or all names. pmemd's rule (READ-SRC, `findmask.F90` `selectElemMask`): "if there is a
  letter in it, it is NAMELIST", so every entry in a list that contains any letter is read as a name.
  EXECUTED in pmemd: `:ALA,1` matches 130 atoms (residue 1 is not added; "1" is read as a residue
  name), and `@1-5,CA` matches 154 atoms (atoms 1-5 are not added). ParmEd reads the same strings
  differently; see section 6.
- **Not documented: numbers out of range, and reversed ranges.** EXECUTED in pmemd: `:9999` (the system
  has 6,401 residues) and `:10-1` each "match 0 atoms", with no error and the run continuing.

### 1.2 Atom types (`@%`)

"In addition, atoms can be selected by AMBER atom type, in which case "@" must be immediately followed
by "%"." AM26 p. 509. READ. Examples `@%CT` and `@%N*,N3`, with the warning: "Note that in the above
example, N* is actually an atom type. The * is not a wild card meaning "all N-something types"!" AM26
p. 510. READ. EXECUTED in pmemd: `@%C*` matches 4 atoms (the literal type `C*`), and `@%CT` matches 130.

### 1.3 Element selection (`@/`)

**The Amber-mask chapter (25.1) does not describe `@/`.** It appears in AM26 only in the cpptraj
chapter: "@/{atom_element_name} e.g. '@/N'" (AM26 p. 728, 38.3.2. READ), plus one cpptraj example on
p. 813. I grepped the whole PDF text for `@/` and found nothing else. pmemd rejects it. READ-SRC: `/` is
not in pmemd's `isOperand` list. EXECUTED: `restraintmask='@/C'` stops pmemd with "Error in group
input::atommask.f::tokenize / illegal symbol in maskstr:/". ParmEd accepts it (section 6).

The manual's own substitute for element selection is the `=` prefix wildcard: "[@H=] would match all
atom names starting with H (which are effectively all hydrogens)". AM26 p. 511. READ.

### 1.4 Wildcards (`=`, `*`, `?`)

- **`=` is a prefix match only.** "A wildcard "=" in an atom or residue name matches any name starting
  with a given character (or characters). For example, [:AS=] would match all aspartic acid residues
  (ASP), and asparagines (ASN) ... It cannot be used to match the end part of names (such as [:=A])."
  AM26 p. 511. READ.
- **What `:=A` actually does in pmemd: it selects everything.** READ-SRC: `isNameMatch` blanks every
  character from the `=` onward in both strings, so with `=` in position 1 every name compares equal.
  EXECUTED: `restraintmask=':=A'` matches 27,356 atoms, the whole system, with no warning. sander,
  ambmask and cpptraj also give 27,356 (EXECUTED). ParmEd gives a different answer (130; section 6).
- **`@C=` is not "all carbons".** The manual's example "[@C= & !@CA,C] .. all carbons except backbone
  alpha and carbonyl carbon" (AM26 p. 511. READ) assumes it is. EXECUTED: `@C=` matches 761 atoms in
  pmemd, ambmask, cpptraj and ParmEd, but the element selection `@/C` (cpptraj, ParmEd) matches 759. The
  two extra atoms are the chloride ions, named `Cl-` (cpptraj `atoms "@C=&!@/C"` lists atoms 2379 and
  2380, both `Cl-`). This is the same name-prefix hazard as the manual's CA/Ca bug.
- **`*` means "all" only as `:*` or `@*`.** The manual mentions no `*` wildcard inside names. READ-SRC:
  pmemd's atom and residue name parsers do not allow `*` inside a name. EXECUTED: `@C*` stops pmemd with
  "atom_namelist / unknown symbol:*". A bare `*` is accepted. READ-SRC comment: "this is here just for
  compatibility with ptraj's notion of selecting all residues by '*' as opposed to ":*"". EXECUTED: `*`
  matches 27,356 atoms.
- **`?` is not in the Amber-mask syntax.** It is not in chapter 25. READ-SRC: the pmemd source lists it
  as a TODO ("'?' wildcard: a simple form of '?' in the function isNameMatch should not be difficult
  but I don't see much use for it"). EXECUTED: `@C?` gives "illegal symbol in maskstr:?".

### 1.5 Operators, precedence, parentheses

"These "elementary selections" can be combined into more complex selections using binary operators
"&" (and) and "|" (or), unary operator "!" (negation), distance binary operators "<:", ">:", "<@",
">@", and parentheses. Spaces around operators are irrelevant. Parentheses have the highest priority,
followed by distance operators ("<:", ">:", "<@", ">@"), "!" (negation), "&" (and) and "|" (or) in
order of descending priority." AM26 p. 511. READ.

- READ-SRC: the pmemd `priority()` function uses `<`,`>` = 6, `!` = 5, `&` = 4, `|` = 3, `(` = 2,
  matching the manual. The file header says "precedence: ! > & > |".
- EXECUTED in pmemd: `:1-10 & !@H= | :20` matches 92 atoms and `:1-10 & (!@H= | :20)` matches 76,
  so `&` binds tighter than `|`. `!:1<:3.0` and `!(:1<:3.0)` both match 27,287, so the distance
  operator binds tighter than `!`.
- READ-SRC: pmemd's tokenizer skips every blank, not only blanks around operators, so
  `:1 <: 3.0` works (EXECUTED: 69 atoms, the same as `:1<:3.0`). The manual's own abf-QM/MM example uses
  `qmmask=':112, 1129, 1824, 2395'`. AM26 p. 215. READ.
- Error messages are not always informative. EXECUTED in pmemd: `(:1-10` gives "eval / unknown symbol
  while evaluating RPN", `:1-10&` gives "pop_evalstack" and nothing more, and `WAT` (no `:`) gives
  "elementary mask does not start with : or @".

### 1.6 Distance selection

- **Syntax.** The operators are `<:`, `>:`, `<@`, `>@` followed by a number (p. 511, quoted above).
  Examples: "[:5 <@4.5] .. all atoms within 4.5A from residue 5" and "[(:1-55 <:3.0) & :WAT] .. all
  water molecules within 3A from residues 1-55". AM26 p. 511. READ.
- **`:` gives whole residues and `@` gives atoms.** Chapter 25 implies this only through the "all
  water molecules" example. It is explicit in the DL-Find section: "one would often set
  active="QMMASK" or active="QMMASK<:3.0", ... The second form selects the QM atoms and any MM residues
  within 3 Angstroms of the QM region." AM26 p. 547. READ. READ-SRC (`noneq`): "if at least one atom in a
  residue is selected (from the previous step), select the whole residue". The pmemd source header
  gives the same examples: ":1-5<@2.5 ... all *atoms* within 2.5A from residues 1-5" and
  "(:1-5&:ALA)<:8 ... all *residues* within 8A of all alanines in residues 1-5".
- **The result includes the starting selection** (distance 0 is below the cutoff). Not stated in the
  manual; the DL-Find sentence above ("selects the QM atoms and any MM residues") implies it. READ-SRC.
- **`>` is the exact complement of `<`.** READ-SRC (`noneq`): "if you want atoms/residues further away
  than 'dist', select atoms/residues that are closer than 'dist' and neg this selection." So `>` means
  "not within", that is, distance >= cutoff from every atom of the starting selection. EXECUTED:
  `:1<:3.0` matches 69, and `:1>:3.0` matches 27,287 = 27,356 − 69. ParmEd differs (section 6).
- **Plain Cartesian distance, no periodic imaging.** READ-SRC: `noneq` computes
  `(crd(ii+1)-crd(jj+1))**2 + ...` from raw coordinates. The manual says nothing about imaging.
- **Only `:` and `@` after `<`/`>`.** EXECUTED in pmemd: `:1<^3.0` gives "illegal symbol in
  maskstr:^", and `:1<;3.0` gives "pop_evalstack". (cpptraj accepts both; section 4.)

### 1.7 What is evaluated when

- **The Reference Manual does not say when sander or pmemd evaluate a mask, or which coordinates a
  distance mask uses.** I found no sentence on it in chapters 23, 24, 25 or 27.
- **ambmask** needs coordinates: "The program needs an Amber topology file and coordinates (restrt
  format)." AM26 p. 511. READ.
- **DL-Find** (sander's `&dlfind`): "refcrd ... If present, then Amber masks specified in the &dlfind
  namelist will be interpreted using the coordinates within refcrd. If refcrd is not specified, then
  the input coordinates (as specified with the -c command line option) will be used." AM26 p. 547. READ.
- **pmemd: once, at setup, from the `-c` input coordinates.** READ-SRC (`master_setup.F90`):
  `restraintmask` and `bellymask` are each passed to `atommask(...)` once during setup, with `atm_crd`
  (the `-c` coordinates). With `mask_from_ref > 0` they use the `-ref` coordinates instead ("Antoine
  Marion :: base mask on reference coordinates"). The same one-time setup call is made for the TI
  masks, `crgmask`, `mcwatmask`, the RAMD masks and others (`ti_init_mask`, `ti_crgmask`,
  `init_mcwat_mask`, `init_ramd_mask`). `mask_from_ref` is not in AM26 (no hit in the PDF text).
- **EXECUTED, pmemd and sander alike:** with `-c heat-2.rst7` and a different `-ref min1.rst7`,
  `restraintmask=':1<@6.0'` matched 132 atoms with `mask_from_ref=0` (the `-c` coordinates) and 143
  atoms with `mask_from_ref=1` (the `-ref` coordinates). Both engines print the `Mask ... matches` line
  once, at setup. I did not test whether a mask is ever re-evaluated during dynamics. The source says no
  for pmemd.
- **cpptraj is different.** See section 4.4.

### 1.8 Length limits

| Where | Limit | Source |
|---|---|---|
| sander `restraintmask`, `bellymask` | "Note that these mask strings are limited to a maximum of 256 characters." | AM26 p. 433, 23.6.4. READ |
| ambmask `-find` | "The length of "maskstr" is limited to 80 characters." | AM26 p. 512. READ |
| sander `&rst` `restraint` string | "There is a 256 character limit on RESTRAINT" | AM26 p. 671. READ |
| sander API `qmmask`, `coremask`, `buffermask`, `centermask` | "(character array, 8192)" | AM26 p. 481, 23.14 (the sander API's `qmmm_input_options` type, not the mdin namelist). READ |
| pmemd mdin masks | declared `character(1024)` (restraintmask, bellymask, timask1/2, crgmask, noshakemask, scmask1/2, the sc_* masks, ti_vdw_mask, reaf_mask1/2, sgmask, rmsd_mask(4), ldcr_mask(2), ...), and findmask's buffer `BUFLEN = 1024` | READ-SRC `mdin_ctrl_dat.F90` lines 294-302. The findmask header comment still says "this limits the length of selection string to 256 chars" (stale). |
| pmemd in practice | a 255-char and a 300-char `restraintmask` both work (88 and 102 residues); an 1,100-char one stops with "pop_evalstack" | EXECUTED |
| sander in practice | 255 chars works; 300 and 1,100 chars stop with "pop_evalstack" | EXECUTED |
| ambmask in practice | 78 chars works; 84 chars stops with "pop_evalstack" | EXECUTED |

So the manual's 256-character limit applies to sander, and sander enforces it. pmemd allows 1,024, and
ambmask allows 80 (enforced). Past its limit, each program fails with the same uninformative "Error in
group input::atommask.f::pop_evalstack". A mask that pmemd accepts can therefore be too long for sander
or for ambmask.

### 1.9 Quoting masks in `&cntrl`

- "Letter case is ignored in all character comparisons, but case is preserved in string constants.
  String constants must be enclosed by single quotes ('). If the text string itself contains single
  quotes, indicate them by two consecutive single quotes, e.g. C1' becomes 'C1''' as a character string
  constant." AM26 p. 429, 23.4 (Namelist Input Syntax). READ. This matters for nucleic-acid atom names
  that contain a prime, such as `C5'`.
- The manual's own examples also use double quotes: `tgtfitmask=":1,2,3"` (p. 536) and
  `restraint = "distance( (45) (49) )"` (p. 671). READ. EXECUTED in pmemd: `restraintmask=":1-10"`
  matches the same 145 atoms as `':1-10'`. The Single Particle `min1.in`, which pmemd ran, also uses
  double quotes.
- EXECUTED in pmemd: an unquoted `restraintmask=:1-10,` gives "Fortran runtime error: Cannot match
  namelist object name :1-10", and an unclosed quote (`restraintmask=':1-10,`) gives "Fortran runtime
  error: End of file".
- **A published example with an unclosed quote.** The LiGaMD3 example in AM26 p. 530 reads
  `timask1 = ':84-91', scmask1 = ':84-91, bgpro2atm=1, edpro2atm=1453,`. READ. The quote after
  `:84-91` is never closed, so the rest of the line becomes part of the mask string.
- **A stale cross-reference.** The `noshakemask` entry says "The syntax for this string is given in
  Chap. 13.5" (AM26 p. 440. READ), but section 13.5 of AM26 is "reduce" (p. 238).
- For the ambmask command line (shell quoting, not mdin): "it is recommended that the operand of the
  negation operator always be enclosed in parentheses so that "!" is always followed by a "(" ... For
  example, [@C= & !(@CA,C)]". AM26 p. 512. READ.

---

## 2. ambmask (AM26 25.1.1, pp. 510-512)

- **Name and purpose.** "ambmask - test group input FIND mask (or mask string given in the &cntrl
  section) and dump the resulting atom selection in a given format". AM26 p. 510. READ.
- **Usage.** `ambmask -p prmtop -c inpcrd -prnlev [0-3] -out [short| pdb| amber] -find [maskstr]`.
  AM26 p. 510. READ.
- **Inputs.** "The program needs an Amber topology file and coordinates (restrt format). ... If -p or -c
  options are not given, the program expects that files "prmtop" and/or "inpcrd" exist in the current
  directory ... If no command line options are given, the program prints the usage statement." AM26
  p. 511. READ.
- **`-find`.** "If this option is left out, it defaults to ":*", which selects all atoms in the given
  topology file. The length of "maskstr" is limited to 80 characters." AM26 p. 512. READ.
- **`-prnlev`.** "If it is 0, only selected atoms are printed. ... 1 prints original "maskstr" in its
  tokenized (with operands enclosed in square brackets) and postfix (or Reverse Polish Notation) forms;
  number of atoms and residues in the topology file and number of selected atoms are also printed to
  stdout. 2 prints the resulting mask array, ... Value of 3, in addition, prints mask arrays as they are
  pushed or popped from the stack". AM26 p. 511. READ.
- **`-out`.** ""short" means a condensed output using residue (:) and atom (@) designators followed by
  residue ranges and atom names. "pdb" (default) prints atoms in Amber-style PDB format with the
  original "maskstr" printed as a REMARK at the top of the PDB file, and "amber" prints atom/residue
  ranges in the format suitable for copying into group input section of Amber input file." AM26 p. 512.
  READ.
- **Output goes to stdout.** "Resulting (i.e. selected) atoms are written to stdout." AM26 p. 512. READ.
- **Known bug.** CA vs Ca, quoted in 1.1. AM26 p. 512. READ.
- **Program behaviour.** EXECUTED (AmberTools26 ambmask, `-prnlev 1 -out short`):
  - It gave the same atom count or the same error as pmemd for every one of the 34 probe strings (table
    at the end), with the same messages ("Error in group input::atommask.f::..."). In practice it is a
    faithful offline check of the sander/pmemd parser, within its 80-character limit.
  - When nothing matches it prints "Warning: no atoms selected" and still exits 0 (`:9999`, `:10-1`,
    `:;5`). Parse errors exit 1.
  - `-c` must be an ASCII restart. A NetCDF restart (this system's `heat-2.rst7`) fails with "STOP error
    reading natom from inpcrd", and I converted it with cpptraj first. Long file paths are cut short
    ("Error opening unit 10: File ".../phase3-explicit-solve" is missing or unreadable"), so I ran it
    from a short directory.
  - `-out short` on `:1>@3.0` printed "27331 atoms selected" and then crashed with "Fortran runtime
    error: End of record" while writing the short listing. The selection was right but the exit code
    was 2.

---

## 3. mdin variables that take a mask

Columns: where the variable lives, which engine reads it according to the manual, and what it
selects. "pmemd namelist" means the variable is in pmemd's `&cntrl` namelist declaration
(`mdin_ctrl_dat.F90` lines 390-485. READ-SRC).

### 3.1 `&cntrl`, general MD

| Variable | Engine | What it selects | Source |
|---|---|---|---|
| `restraintmask` | sander, pmemd | "String that specifies the restrained atoms when ntr = 1." Used with `restraint_wt` and the `-ref` coordinates. | AM26 p. 433. READ |
| `bellymask` | sander, pmemd | "String that specifies the moving atoms when ibelly=1." | AM26 p. 433. READ |
| `noshakemask` | sander, pmemd | "String that specifies atoms that are not to be shaken (assuming that ntc>1). ... The code enforces this by setting ntf to 1 when a noshakemask string is present in the input." | AM26 p. 440. READ (pmemd namelist: READ-SRC) |
| `tgtfitmask`, `tgtrmsmask` | sander (targeted MD, `itgtmd=1`); both engines for NEB | Targeted MD: the atoms fitted to the reference and the atoms whose RMSD is restrained. NEB: "Flag which sets atoms to RMS fit each image's neighbor to itself" / "Flag which sets atoms to decouple NEB forces for PNEB". | AM26 pp. 531-532, 536. READ. pmemd: "itgtmd!=0 In &cntrl. Targeted molecular dynamics is not supported." AM26 p. 498. READ. "A partial NEB (PNEB) implementation is available both in sander and pmemd". AM26 p. 535. READ |
| `sgmask` | SGLD (manual lists it with SGLD; it is in the pmemd namelist) | "The atom mask for selecting atoms between isgsta and isgend to apply guiding forces (default=':*')." | AM26 p. 517. READ |
| `mcwatmask` | pmemd.cuda (and its REMD) | the atoms whose centre of mass defines the water Monte Carlo region | AM26 p. 457. READ |
| `ramdligmask` | pmemd, pmemd.cuda ("Ramd is a pmemd and pmemd.cuda only feature") | "Amber selection mask for what is considered the ligand that needs to be boosted in ramd." | AM26 pp. 458-459. READ |
| `ramdprotmask` (manual name) / `ramdproteinmask` (pmemd name) | pmemd | "Amber selection mask for what is considered the protein that is used to calculate the distance the ligand has moved." | AM26 p. 459. READ. **The names disagree.** The pmemd namelist has `ramdproteinmask`. EXECUTED: `ramdprotmask=':1'` stops pmemd26 with "Fortran runtime error: Cannot match namelist object name ramdprotmask", and `ramdproteinmask=':1'` runs. |
| `decompmask`, `ligmask`, `proteinmask` | pmemd.decomp (`ntwd=1`) | atoms printed to decomp.log; ligand, protein (and "cofactor") regions for TI decomposition | AM26 p. 458. READ. The heading for proteinmask is misprinted "proteinmas". |
| `cofactormask` (manual heading) / `cofacmask` (manual body text and pmemd) | pmemd.decomp | cofactor region | AM26 p. 458 uses both spellings. READ. EXECUTED: `cofactormask` is rejected by pmemd26 ("Cannot match namelist object name cofactormask"), and `cofacmask` runs. |
| `ldcr_mask(2)` | pmemd | (not documented) | In the pmemd namelist (READ-SRC); no hit in AM26 |
| `mask_from_ref` | pmemd | not a mask: integer flag; if > 0, `restraintmask`/`bellymask` are evaluated on the `-ref` coordinates | READ-SRC `master_setup.F90`; no hit in AM26; EXECUTED (accepted) |
| `iwrap_mask` | sander only (undocumented) | — | Not in AM26 (no hit in the PDF text), not in the pmemd26 namelist, and a web search for "iwrap_mask" amber sander returned no Amber page about it. EXECUTED: pmemd26 rejects it ("Cannot match namelist object name iwrap_mask"). **sander26 accepts it.** EXECUTED: `iwrap=1, iwrap_mask=':1'` in sander's `&cntrl` runs through setup, while a misspelled `iwrap_maskx` gives "error in reading namelist cntrl". So `iwrap_mask` is a real but undocumented sander namelist variable. I could not establish what it does. Only `iwrap` (an integer flag) is documented: AM26 p. 432. |

### 3.2 `&cntrl`, free energy (TI/FEP), GaMD and REAF

| Variable | Engine | What it selects | Source |
|---|---|---|---|
| `timask1`, `timask2` | pmemd ("Input flags specific to PMEMD"); the AT26 sander namelist accepts them too (EXECUTED) | "Specifies the atoms unique to V0 in ambmask format." / "...unique to V1..." | AM26 p. 553, 27.1.4.2. READ |
| `scmask` | sander ("Input flags specific to Sander") | "Specifies the unique (soft core) atoms for this process in ambmask format." | AM26 p. 557, 27.1.6.1. READ. But the AmberTools26 sander rejects `scmask` (EXECUTED; see 3.5). |
| `scmask1`, `scmask2` | pmemd | "Specifies the unique (soft core) atoms for V0 [V1] in ambmask format. It is valid to set scmask1 to an empty string." | AM26 p. 557, 27.1.6.2. READ |
| `crgmask` | sander and pmemd (listed under the shared flags) | "Specifies a number of atoms (in ambmask format) that will have their atomic partial charges set to zero." | AM26 p. 557. READ. READ-SRC: pmemd ignores it when `sigma_max > 0` ("WARNING: crgmask is ignored when sigma_max > 0.") |
| `ti_vdw_mask` | pmemd.cuda (GTI) | "Mask selection to zero out vDW interactions. (In the standard AMBER mask language, similar to crgmask)" | AM26 p. 567. READ |
| `sc_bond_mask1/2`, `sc_angle_mask1/2`, `sc_torsion_mask1/2` | pmemd.cuda (GTI), when `gti_bat_sc=2` | the cross common/softcore bond, angle and torsion terms not scaled with λ. "All must be in the AMBER standard mask language." | AM26 p. 562. READ |
| `gti_sc_scale_dihedral`, `gti_sc_noscale_dihedral` | pmemd.cuda (GTI), `aces26=1` | "List of pairs of single-atom Amber masks. Each pair must correspond to the j and k atoms of proper dihedrals i, j,k,l." | AM26 p. 563. READ. pmemd declares these `character(256)` arrays of 1024 entries (READ-SRC). |
| `gti_sc_sc_energy_terms`, `gti_sc_cc_energy_terms` | pmemd.cuda | **not masks**: they take energy-term keywords (Table 27.4), although pmemd declares them in its "Amber masks" block | AM26 p. 563. READ; READ-SRC |
| `rmsd_mask` | pmemd.cuda (GTI build, `icfe=1`) only | "An array of up to 4 Amber mask strings specifying the atoms for each RMSD set." Also: "A maximum of 4 RMSD sets are supported simultaneously, with up to 200 atoms per set." | AM26 pp. 572-573. READ |
| `reaf_mask1`, `reaf_mask2` | pmemd (REAF, a GTI feature) | "The REAF region for a plain MD simulation or the λ =0 state" / "...for the λ =1 state" | AM26 p. 595. READ |
| `timask1`, `scmask1` (reused) | pmemd GaMD (LiGaMD, Pep-GaMD, PPI-GaMD) | ligand, peptide or first protein, "in ambmask format when igamd = 10, 11, 14, 15, 16, 17 or 18" | AM26 p. 526. READ |
| `lrtmask` | sander ("sander contains rudimentary facilities ... linear interaction energy") | "The 'solute'. Interaction Energies between the atoms in lrtmask and the remainder of the system are computed." | AM26 p. 573. READ |

### 3.3 Other namelists

| Variable | Namelist, engine | What it selects | Source |
|---|---|---|---|
| `qmmask` | `&qmmm`, sander (pmemd: "ifqnt!=0 ... QM/MM methods are not supported", p. 498) | "Mask specifying the quantum atoms. E.g. :1-2, = residues 1 and 2." Alternative to `iqmatoms`. | AM26 p. 172. READ |
| `coremask`, `qmmask`, `buffermask` (+ `centermask`, `ext_coremask_subset`, `ext_qmmask_subset`, `ext_buffermask_subset`) | `&qmmm` with `abfqmmm=1`, sander | the core, QM and buffer regions for adaptive buffered force-mixing QM/MM, "in ambmask format" | AM26 pp. 215-218. READ |
| `mask` | `&dprc`, sander QM/MM+DPRc | "The Amber selection of those atoms whose energies and forces should be corrected with the DPRc potential." | AM26 p. 205. READ |
| `active`, `wtmask` | `&dlfind`, sander | "An amber mask indicating which atoms are allowed to move, default="@*"" and the weighted-RMS overlay atoms for dimer/NEB | AM26 pp. 547, 549. READ |
| `atmask` | `&emap`, sander and pmemd ("Sander and PMEMD can be used...") | "The atom mask for selecting atoms to be restrained (default=':*')." | AM26 pp. 695-696. READ |
| `mtmdmask` | `&tgt` (separate MTMD file), sander only ("multiply-targeted MD is now available in Amber (sander only)") | atoms for both fitting and RMSD in multiply-targeted MD | AM26 pp. 532-533. READ |
| `restraint` | `&rst` (NMR restraints), "New as of Amber 10 (sander only)" | not a mask, but a restraint string whose atoms "may be defined either with an explicit atom number or by using ambmask format, namely :(residue#)@(atom name)". 256-character limit. | AM26 p. 671. READ |
| `masktitrres` | `&phmdin` (continuous CpHMD) | **not a mask**: "The names of the titratable residues." | AM26 p. 662. READ |
| `chngmask` | `&ewald` | **not a mask**: an integer flag for extra-point exclusions | AM26 p. 462. READ |

Outside mdin, these programs also take masks: MMPBSA.py (`ligand_mask`, `receptor_mask`,
`strip_mask`; AM26 pp. 949-951), ParmEd actions (AM26 ch. 15) and cpptraj (ch. 38).

### 3.4 Do sander and pmemd differ?

- **Different TI variable names, per the manual.** sander uses one `scmask` per group file, while pmemd
  uses `timask1/2` and `scmask1/2`. "In thermodynamic integration calculations, the input format is
  different from SANDER." AM26 p. 501. READ. **Execution disagrees for sander:** the AmberTools26
  sander rejects `scmask` ("error in reading namelist cntrl") and accepts `timask1/2` and `scmask1/2`
  (EXECUTED, table 3.5). The string `scmask` does not appear in the sander binary, while `scmask1`,
  `timask1` and `crgmask` do (`strings`, EXECUTED). So the manual's sander TI section (27.1.4.1,
  27.1.6.1) appears to be out of date for this build.
- **Different features.** Only sander reads QM/MM, DL-Find, MTMD, LIE and `&rst restraint` masks
  (manual; for `lrtmask`, pmemd's namelist rejects it, 3.5). Only pmemd or pmemd.cuda reads GTI, REAF,
  RMSD, RAMD, MC-water and decomposition masks (manual; sander's namelist rejects each one, 3.5). pmemd
  lists no targeted MD (p. 498), although NEB in pmemd still reads `tgtfitmask` and `tgtrmsmask`
  (p. 535).
- **Different length limits**: 256 for sander (manual) and 1,024 for pmemd (source; EXECUTED).
  EXECUTED: sander rejects a 300-character mask that pmemd accepts.
- **Different namelists**: sander26 accepts `iwrap_mask` and pmemd26 rejects it (EXECUTED). Both accept
  the undocumented `mask_from_ref` (EXECUTED).
- **The same parser.** READ-SRC: pmemd's `findmask.F90` header says the module "takes "atomic
  expression" loosely using Chimera/Midas syntax", is credited "VH; Dec 30, 2003", and prints its
  errors as "Error in group input::atommask.f::...", which is the ambmask/sander lineage. I did not
  read sander's source. EXECUTED: on the 12 strings I gave both engines (`:1-10` in single and
  double quotes, `:ala`, `::A`, `@/C`, `@C*`, `:=A`, `:;5`, `:ALA,1`, `@%C*`, `:1>:3.0`, `:9999`), sander
  and pmemd returned identical counts and identical error messages.

### 3.5 Which engine's `&cntrl` namelist accepts each variable (EXECUTED)

Each variable was set alone (to `''`, or `0` for `mask_from_ref`) in an otherwise valid `&cntrl`. pmemd
is the Amber26 build. sander is from the conda-forge `ambertools` 26.0 package. "rejected" means the
Fortran namelist read failed: pmemd prints "Cannot match namelist object name ...", and sander prints
"error in reading namelist cntrl". This tests only that the name is known, not that the feature works.

| Variable | pmemd26 | sander (AT26) |
|---|---|---|
| `noshakemask`, `tgtfitmask`, `tgtrmsmask`, `sgmask`, `crgmask` | accepted | accepted |
| `timask1`, `timask2`, `scmask1`, `scmask2` | accepted | accepted |
| `scmask` | accepted (READ-SRC comment: "not actually used...") | **rejected** |
| `ti_vdw_mask`, `sc_bond_mask1`, `reaf_mask1`, `rmsd_mask`, `ldcr_mask` | accepted | rejected |
| `ramdligmask`, `ramdproteinmask`, `mcwatmask` | accepted | rejected |
| `decompmask`, `ligmask`, `proteinmask`, `cofacmask` | accepted | rejected |
| `ramdprotmask`, `cofactormask` (the manual's spellings) | **rejected** | rejected |
| `iwrap_maskx` (control: a name that exists nowhere) | rejected | rejected |
| `lrtmask` | rejected | accepted |
| `iwrap_mask` | rejected | accepted |
| `mask_from_ref` | accepted | accepted |

---

## 4. cpptraj's mask syntax and how it differs from sander/pmemd

Primary text: AM26 38.3.2 "Atom Mask Selection Syntax", pp. 728-730. The same text is on HUB. Code:
CPPSRC.

### 4.1 What the cpptraj docs list

"The mask syntax is similar to ptraj. ... All masks are case-sensitive. Either names or numbers can be
used. Masks can contain ranges (denoted with '-') and comma separated lists. The logical operands
'&' (and), '|' (or), and '!' (not) are also supported." AM26 p. 728. READ.

The elementary selections listed (AM26 p. 728. READ):
`@{atom numlist}`, `@{atom namelist}`, `@%{atom type name}`, `@/{atom_element_name} e.g. '@/N'`,
`:{residue numlist}`, `:{residue namelist}`,
"`::{chain id} e.g. '::B', '::A,D'. Requires chain ID information be present in the topology.`",
"`:;{pdb residue number} e.g. ':;2-4,8'. Requires a PDB loaded as topology, or Amber topology with
embedded PDB information (see 15.2.2.5 on page 295).`",
"`^{molecule numlist} e.g. '^1-10', ':23,84,111'`" (the second example is printed as `:23,...` in the
manual, apparently a typo for `^`),
and `<mask><distance operator><distance>`.

Wildcards: "'*' Zero or more characters. '=' Same as '*' '?' One character. The wildcards can also be
used with numbers or other mask characters, e.g. ':?0' means ":10,20,30,40,50,60,70,80,90"". To match a
literal `*`, escape it: "atoms @C?\* ... would only select C4*". AM26 pp. 728-729. READ.

HUB adds chain-plus-residue examples: "`::A,B,C:1-10`" and "`::A,B:2-20@CA,C,O,N`". READ.

### 4.2 Differences from sander/pmemd/ambmask

| Feature | sander/pmemd/ambmask (AM26 ch. 25; pmemd EXECUTED) | cpptraj (AM26 38.3.2; CPPSRC) |
|---|---|---|
| Case | "Selections are case insensitive" (p. 510); pmemd `:ala` = `:ALA` | "All masks are case-sensitive" (p. 728). READ |
| Element `@/` | not documented; pmemd error | documented. READ. READ-SRC: matches against each atom's element name |
| Molecule `^` | not documented; pmemd error | `^1-10`; molecule *numbers* only (READ-SRC: "Molecule name not yet supported") |
| Chain `::` | not documented; pmemd error "residue_namelist / unknown symbol::" | `::A,D`; needs chain IDs in the topology. READ |
| Original (PDB) residue number `:;` | not documented. **pmemd silently selects nothing**: EXECUTED `restraintmask=':;5'` → "matches 0 atoms", no error (READ-SRC: pmemd appends `;` as its end-of-string marker and stops reading at the first `;`) | `:;2-4,8`; needs `RESIDUE_NUMBER` or a PDB. READ |
| `*` inside a name | pmemd error "unknown symbol:*" | wildcard. READ-SRC (`NameType::Match`): a `*` returns a match immediately, so anything after the `*` is ignored |
| `?` | pmemd error | one-character wildcard. READ |
| `=` | prefix wildcard, "cannot be used to match the end part of names" (p. 511) | "Same as '*'" (p. 728). READ-SRC: the tokenizer rewrites every `=` to `*`; a `*` in the first position of a list entry makes the token "select all" |
| `@%N*` | literal type `N*` (p. 510); pmemd `@%C*` → 4 atoms | `*` is a wildcard, so `@%N*` matches every type starting with N; write `@%N\*` for the literal type. READ (escape rule p. 728-729) |
| Distance operators | `<:` `>:` `<@` `>@` | adds `<^`/`>^` (whole molecules) and `<;`/`>;` (residue geometric centre): "{<\|>}{@\|:\|;\|^}". AM26 p. 729. READ |
| `>` meaning | complement of `<` (READ-SRC; EXECUTED) | "Distances greater than or equal to <distance> will be selected." AM26 p. 729. READ. READ-SRC: also implemented as the complement |
| Whole residue for `:` | yes (p. 547; READ-SRC) | "if any atom in that residue/molecule meets the given distance criterion, the entire residue/molecule is selected." AM26 p. 729. READ |
| Precedence | `()` > distance > `!` > `&` > `\|` (p. 511) | not stated in the docs. READ-SRC `OperatorPriority`: `<`,`>` 6, `!` 5, `&` 4, `\|` 3, the same order as pmemd |
| Out-of-range numbers | pmemd: 0 atoms, silently (EXECUTED) | prints "Warning: Select residues: res 1 out of range (9999 > 6401)" and selects 0 (EXECUTED); a range end past the last residue is clipped (READ-SRC) |
| Reversed range `:10-1` | 0 atoms, silently (EXECUTED) | error "Mask range, second num (1) less than first (10)" (EXECUTED) |
| Empty starting set for a distance | READ-SRC pmemd: no check | READ-SRC: "Error: Mask_SelectDistance: No atoms in prior selection." |
| Periodic imaging in distance | none (READ-SRC) | none: `DIST2_NoImage` (READ-SRC) |

**EXECUTED (cpptraj V7.6.2, `parm`, `reference`, then `select <mask>`):**

- `:ala` 0 and `@ca` 0 (case-sensitive), against 130 and 154 in pmemd.
- `@/C` 759, `@/c` 0 (lower case is not an error, just no match), `^1` 2,377 (molecule 1, the protein),
  `@C?` 434, `@C*` 761, `@%C*` 478 (wildcard), `@%C\*` 4 (the escaped literal type, matching pmemd's
  `@%C*`).
- `:=A` 27,356, so cpptraj also selects everything, like pmemd.
- `:ALA,1` 142 and `@1-5,CA` 158: cpptraj reads each list entry on its own (number or name), unlike
  pmemd (130 and 154).
- `::A` 0 atoms with no warning: this topology has no chain IDs, so the selector silently matches nothing.
- `:;5` 19 atoms, the same as `:5`. This topology has no `RESIDUE_NUMBER`, and cpptraj fell back to the
  sequential number. pmemd gives 0 for the same string.
- Distances: `:1<:3.0` 69, `:1<@3.0` 25, `:1>:3.0` 27,287, `:1>@3.0` 27,331 (all the same as pmemd);
  `:1<^3.0` 2,377 and `:1<;3.0` 23 (cpptraj-only operators).
- `:9999` prints "Warning: Select residues: res 1 out of range (9999 > 6401)" and selects 0.
  **`:10-1` is an error in cpptraj** ("Mask range, second num (1) less than first (10)"), where pmemd
  silently selects 0.
- `(:1-10` gives "Mask::ToRPN: unbalanced parentheses", and `:1-10&` gives "Misplaced operator OP_AND".
- **Spaces end a mask on a cpptraj command line.** `select :1-10 & !@H= | :20` selected 145 atoms (only
  `:1-10` was read), and the quoted `select ":1-10 & !@H= | :20"` selected 92, the same as pmemd. With
  quotes, both precedence probes agree with pmemd (92 and 76). This is cpptraj's argument splitting, not
  its mask grammar.
- **A word with no `:`, `@` or `*` is not taken as a mask.** `select WAT` selected all 27,356 atoms
  instead of failing (pmemd: "elementary mask does not start with : or @"). READ-SRC
  (`ArgList::GetMaskNext`): "A mask MUST include one of the following: ':' residue '@' atom '*'
  everything". `MaskTokenArray::SetMaskString` turns an empty mask into `*`.

### 4.3 What cpptraj accepts that pmemd rejects, and the reverse

- Accepted by cpptraj, error in pmemd: `@/`, `^`, `::`, `?`, `*` inside names, `<^`, `<;`. pmemd
  EXECUTED as above.
- **Accepted by both, with different meanings** (all EXECUTED):
  - `:;5`: cpptraj gives 19 atoms (original residue 5, or residue 5 when there is no `RESIDUE_NUMBER`);
    pmemd gives 0, without an error.
  - `@%C*`: cpptraj gives 478 (wildcard); pmemd gives 4 (the literal type `C*`).
  - `:ala` / `@ca`: cpptraj gives 0 (case-sensitive); pmemd gives 130 / 154.
  - `:ALA,1` / `@1-5,CA`: cpptraj gives 142 / 158 (each entry read on its own); pmemd gives 130 / 154 (the
    whole list read as names).
  - `:=A`: both give 27,356 (everything). This agrees, but neither matches the manual's description of
    `=`.
  - `WAT` (no `:`): cpptraj `select` gives all atoms; pmemd stops with an error.
- **Accepted by pmemd, rejected by cpptraj** (EXECUTED): a reversed range such as `:10-1`. cpptraj
  errors, while pmemd, sander and ambmask silently select 0 atoms.

### 4.4 When cpptraj evaluates distance masks

"There are two very important things to keep in mind when using distance based masks: 1.
Distance-based masks that update each frame are currently only supported by the mask action. 2.
Selection by distance for everything but the mask action requires defining a reference frame with
reference; distances are then calculated using the specified reference frame only. This reference
frame can be changed using the activeref command." AM26 p. 729. READ (same text on HUB). The strip
example repeats it: "Note that with the exception of the mask command, distance-based masks do not
update on a per-frame basis." AM26 p. 882. READ. To test a mask: "select <mask> Prints the number of
selected atoms corresponding to the given mask". AM26 p. 775. READ.

---

## 5. Does the prmtop store chain IDs or original residue numbers?

- **The format documents do not list them.** Neither PRMTOP (2013) nor FF lists `RESIDUE_CHAINID`,
  `RESIDUE_NUMBER` or `RESIDUE_ICODE`. FF does list `%FLAG ATOMIC_NUMBER` ("ATNUM : the atomic number
  of each atom."). READ (I grepped both texts for these names; FF lists flags from TITLE through
  POLARIZABILITY).
- **They are optional sections, added by tools.** ParmEd's `addPDB` "reads in a PDB file <filename> and
  adds the following new sections to the topology file: RESIDUE_CHAINID The chain ID of each residue
  (if it was added by tleap and not in the PDB file, a * is used) RESIDUE_ICODE PDB insertion code
  RESIDUE_NUMBER The original residue number of this residue in the PDB file". AM26 p. 295, 15.2.2.5.
  READ. "Residues not in the PDB will be assigned a CHAINID of '*' and a RESIDUE_NUMBER of 0." AM26
  p. 296. READ. The `deletePDB` action "Deletes the flags that are added by addPDB". AM26 p. 306. READ.
- **tleap (off by default).** "The ChainId and ResId may be retained from PDB input and save to the
  PRMTOP in the format used by addPdb and cpptraj. This is off by default in this release, and can be
  enabled with "set default keep_chainid on"." AM26 p. 270. READ. Also: "keep_chainid If this is set to
  "on", the ChainId and ResId values taken from an input PDB file will be stored in the resulting
  prmtop file. ... Default is "off"." AM26 p. 272. READ.
- **cpptraj writes them.** "CPPTRAJ retains PDB information (chain ID, original residue number,
  Bfactor/Occupancy etc) which is printed to the output Topology." AM26 p. 747. READ. HUB: "CPPTRAJ will
  use/add the RESIDUE_NUMBER flag to an Amber topology file, which tracks the "original" residue
  number." READ.

**Which programs read them:**

- **cpptraj** reads `RESIDUE_NUMBER`, `RESIDUE_CHAINID`, `RESIDUE_ICODE` and also `ATOM_ALTLOC`,
  `ATOM_BFACTOR`, `ATOM_OCCUPANCY`, `ATOM_NUMBER`. READ-SRC `Parm_Amber.cpp` lines 142-149 (comment "PDB
  extra info"). Its `::` and `:;` masks use them (AM26 p. 728. READ).
- **ParmEd** writes them (`addPDB`). Its `outCIF <file> [norenumber]` action "will respect the numbering
  in the original PDB file" if addPDB was used. AM26 p. 311. READ. Its mask parser has no chain or
  original-number selector (PESRC; section 6).
- **pmemd** reads `RESIDUE_NUMBER` and `RESIDUE_CHAINID` only in its X-ray module
  (`xray_interface_impl_cpu.F90`, `nxtsec(... 'RESIDUE_CHAINID' ...)`). READ-SRC. Its mask parser
  (`findmask.F90`) takes only atom names, atom types, residue labels, residue pointers and coordinates
  (the `atommask` argument list). READ-SRC. So no pmemd mask can select by chain or by original residue
  number.
- **sander**: I did not read its source and AM26 does not say. Not established.
- The test system here has neither section (READ: grep of `complex.parm7`), which is normal for a plain
  tleap build because `keep_chainid` is off by default.

---

## 6. ParmEd's mask parser (`parmed.amber.mask.AmberMask`)

### 6.1 What the docs say

- "The Amber programs use a selection syntax very similar to Chimera's selection syntax, referred to as
  an Amber mask." PEDOC amber.html, "Amber mask syntax". READ.
- **Mixed name/number lists are documented as supported.** ":ALA,LYS,10 Select all residues with names
  ALA or LYS, and residue 10" and "@CA,C,10-15 Select all atoms whose names are CA or C, and 6 atoms
  10-15". PEDOC amber.html. READ. "The residues you wish to select may be a comma-separated list of
  numbers, number ranges, names, or a mixed list of both." PEDOC parmed.html. READ.
- **Element selection, case-sensitive.** "@/C Select all carbon atoms ... @/Fe Select all iron atoms. Be
  careful, though! These element names are case-sensitive, and bad element names will cause the mask
  parser to raise an exception." PEDOC amber.html. READ.
- **Wildcards.** "The "=" character works as a wild-card, as does the '*' ... If either '=' or '*' is
  part of the atom name, you can use the "\" character to escape it". PEDOC parmed.html. READ.
- **Distance.** "When selecting residues, the whole residue is selected if any atom satisfies the
  distance criteria." Examples: ":8<@5.0 All atoms that are LESS THAN 5 Angstroms away from any atom in
  residue 8" and ":1>:10.0 All atoms in any residue in which one atom is MORE THAN 10 angstroms away
  from residue 1". PEDOC amber.html. READ. (The "Distance-based masks" subsection of parmed.html stops
  after its first paragraph and gives no syntax.)
- **The docs state no differences from sander.** parmed.html: "The selection syntax is described in
  detail in the Amber user's manual, with numerous examples in the cpptraj and ambmask sections." READ.
- **AM26 is out of date on ParmEd.** "The mask parser implemented in Python here is (mostly) a copy of
  ptraj's mask parser implemented in C ... Note, distance-based criteria is not yet implemented in this
  parser." AM26 p. 313, printDetails. READ. ParmEd 4.3.1 does evaluate distance masks (PESRC
  `_selectDistd`; EXECUTED below).

### 6.2 Behaviour, from the source and from execution (ParmEd 4.3.1, same system)

| Mask | pmemd (EXECUTED) | ParmEd (EXECUTED) | Why (PESRC) |
|---|---|---|---|
| `:ala` | 130 | 0 | `_nameMatch` is an exact or regex match with no case folding |
| `@ca` | 154 | 0 | same |
| `@/C` | error | 759 | ELEMLIST, compared through `AtomicNum[...]` with the atom's atomic number |
| `@/c` | error | MaskError "Unknown element c" | |
| `^1`, `::A`, `:;5` | error, error, 0 atoms | MaskError each | `^` and `;` are not operands; `::` gives "empty token in infix" |
| `@C?` | error | 434 | `?` becomes regex `\S` |
| `@C*` | error | 761 | `*` becomes regex `\S*` |
| `:=A` | 27,356 (everything) | 130 (= the ALA residues) | `=` becomes `*`, i.e. regex `\S*A`, which makes it a **suffix** match |
| `:ALA,1` | 130 | 142 (ALA + residue 1) | `_resname_select`: an all-digit entry is also tried as a residue number |
| `@1-5,CA` | 154 | 158 | mixed list as documented |
| `@%C*` | 4 (literal `C*`) | 478 | `*` is a wildcard in type lists too |
| `@%C\*` | not run (ambmask: error, "illegal symbol in maskstr:\") | 181 | the escaped `*` turns back into a regex quantifier, so the escape does not give the literal type `C*` either (cpptraj's escape gives 4) |
| `:1<:3.0` / `:1<@3.0` | 69 / 25 | 69 / 25 | same |
| `:1>:3.0` | 27,287 | **27,356** | ParmEd's `>` selects an atom if it is farther than the cutoff from **any one** atom of the starting set (`cmp(d2, distance)` then `break`); pmemd's `>` is "not within" |
| `:1>@3.0` | not run (ambmask and cpptraj: 27,331 = 27,356 − 25) | 27,355 | same reason |
| `!:1<:3.0` | 27,287 | 27,287 | same precedence |
| `:1<^3.0` | error | MaskError "Bad syntax" | only `:` and `@` after `<`/`>` |
| `:1-10 & !@H= \| :20` / with parentheses | 92 / 76 | 92 / 76 | same precedence: `<`,`>` 6, `!` 5, `&` 4, `\|` 3 (`_priority`) |
| `(:1-10`, `:1-10&`, `WAT` | errors | MaskError each | |
| `:9999`, `:10-1` | 0, 0 | 0, 0 | |
| `*` | 27,356 | 27,356 | |

Also from PESRC: distance masks raise "<,> operators require coordinates" when the structure has
none, and distances use raw coordinates (`atomi.xx - atomj.xx`), with no periodic imaging.

---

## Summary table

### Feature table

| Feature | pmemd / sander | ambmask | cpptraj | ParmEd | Source |
|---|---|---|---|---|---|
| `:` residues, `@` atoms; numbers, names, `-` ranges, `,` lists | yes | yes | yes | yes | AM26 pp. 509-511 (R); AM26 p. 728 (R); PEDOC (R); E all |
| Numbers are sequential topology numbers, not PDB numbers | yes | yes | yes, except `:;` | yes | AM26 p. 509 (R); PEDOC parmed.html (R) |
| Mixed name/number list (`:ALA,1`, `@1-5,CA`) | whole list read as names: 130, 154 | same: 130, 154 | each entry on its own: 142, 158 | each entry on its own: 142, 158 (documented) | E; S pmemd `selectElemMask`; PEDOC (R) |
| Case of names | insensitive | insensitive | **sensitive** | **sensitive** | AM26 p. 510 (R), p. 728 (R); E (`:ala` 130/130/0/0) |
| Atom type `@%` | yes; `*` is literal (`@%C*` = 4) | same (4) | yes; `*` is a wildcard (478), `\*` is literal (4) | yes; `*` is a wildcard (478), and `\*` does not give the literal (181) | AM26 p. 510 (R), pp. 728-729 (R); E |
| Element `@/` | **error** (not in AM26 ch. 25) | **error** | yes (`@/C` 759) | yes, case-sensitive symbol (`@/C` 759, `@/c` error) | AM26 p. 728 (R); PEDOC (R); E |
| Molecule `^` | **error** | **error** | yes (`^1` 2,377) | **error** | AM26 p. 728 (R); E |
| Chain ID `::` | **error** | **error** | yes if the topology has chain IDs; 0 atoms silently if not | **error** | AM26 p. 728 (R); E |
| Original PDB residue number `:;` | **0 atoms, no error** | 0 atoms + "Warning: no atoms selected" | yes (needs `RESIDUE_NUMBER`; falls back to the sequential number: 19) | **error** | AM26 p. 728 (R); E |
| `=` wildcard | prefix only, per the manual; `:=A` selects **everything** | same (everything) | "same as `*`"; `:=A` everything | regex; `:=A` is a **suffix** match (130) | AM26 p. 511 (R), p. 728 (R); E |
| `*` inside a name | **error** | **error** | wildcard; anything after the `*` is ignored (S) | regex `\S*` | E; S `NameType::Match`, `_nameMatch` |
| `?` one-character wildcard | **error** | **error** | yes (434) | yes (434) | AM26 p. 728 (R); E |
| `:*`, `@*`, bare `*` | all | all | all | all | AM26 p. 510 (R); E |
| `&` `\|` `!` `()` | yes | yes | yes | yes | AM26 p. 511 (R), p. 728 (R); PEDOC (R) |
| Precedence | `()` > distance > `!` > `&` > `\|` | same | same order (S); not stated in its docs | same order (S) | AM26 p. 511 (R); E (92 vs 76 in all four) |
| Distance operators | `<:` `>:` `<@` `>@` | same | adds `<^` `>^` (molecule), `<;` `>;` (residue centre) | `<:` `>:` `<@` `>@` | AM26 p. 511 (R), p. 729 (R); E |
| `<:` returns whole residues | yes (69 vs 25 for `<@`) | yes | yes | yes | AM26 p. 547 (R), p. 729 (R); PEDOC (R); E |
| Meaning of `>` | complement of `<` (27,287) | same | complement, ">= distance" (27,287) | **farther than any one** starting atom (27,356) | S; AM26 p. 729 (R); E |
| Coordinates used by distance masks | `-c` at setup; `-ref` if `mask_from_ref=1` (undocumented) | the `-c` file | the active `reference` frame; only the `mask` action updates per frame | the structure's coordinates; error if it has none | S; E (132 vs 143); AM26 p. 511, p. 729 (R); PESRC |
| Periodic imaging in distances | no | not checked | no | no | S (`noneq`, `DIST2_NoImage`, `_selectDistd`) |
| Out-of-range number (`:9999`) | 0 atoms, no message | 0 + warning | 0 + warning | 0 | E |
| Reversed range (`:10-1`) | 0 atoms, no message | 0 + warning | **error** | 0 | E |
| Bare word without `:`/`@` (`WAT`) | error | error | `select WAT` gives **all atoms** (not read as a mask) | error | E; S `ArgList::GetMaskNext` |
| Spaces | ignored anywhere | ignored | ignored inside the mask, but a space ends a command-line argument unless the mask is quoted | ignored | S; E |
| Maximum length | sander 256 (documented and enforced); pmemd 1,024 (source; 300 works) | 80 (documented and enforced) | not documented, not tested | not documented | AM26 p. 433, p. 512 (R); S; E |
| Quoting in mdin | single quotes per manual, `''` for a literal `'`; double quotes also work; unquoted or unclosed is a Fortran namelist error | n/a (shell quoting; use `!(`) | n/a | n/a | AM26 p. 429, p. 512 (R); E |
| Reads `RESIDUE_CHAINID` / `RESIDUE_NUMBER` | pmemd: X-ray module only, never in masks (S); sander: not established | no (not in its syntax) | yes | writes them (`addPDB`); mask has no selector for them | S; AM26 pp. 295, 728 (R) |

R = READ, S = READ-SRC, E = EXECUTED.

### Executed atom counts per mask (test system, 27,356 atoms)

"err" = the parser stopped with an error. "–" = not run. cpptraj masks with spaces were quoted.

| Mask | pmemd | sander | ambmask | cpptraj | ParmEd |
|---|---|---|---|---|---|
| `:1-10` | 145 | 145 | 145 | 145 | 145 |
| `:ala` | 130 | 130 | 130 | 0 | 0 |
| `::A` | err | err | err | 0 | err |
| `@/C` | err | err | err | 759 | 759 |
| `^1` | err | – | err | 2,377 | err |
| `@C?` | err | – | err | 434 | 434 |
| `@C*` | err | err | err | 761 | 761 |
| `@C=` | 761 | – | 761 | 761 | 761 |
| `:=A` | 27,356 | 27,356 | 27,356 | 27,356 | 130 |
| `:9999` | 0 | 0 | 0 | 0 | 0 |
| `:ALA,1` | 130 | 130 | 130 | 142 | 142 |
| `@1-5,CA` | 154 | – | 154 | 158 | 158 |
| `@ca` | 154 | – | 154 | 0 | 0 |
| `@%C*` | 4 | 4 | 4 | 478 | 478 |
| `@%C\*` | – | – | err | 4 | 181 |
| `:1<:3.0` | 69 | 69 | 69 | 69 | 69 |
| `:1<@3.0` | 25 | – | 25 | 25 | 25 |
| `:1>:3.0` | 27,287 | 27,287 | 27,287 | 27,287 | 27,356 |
| `:1>@3.0` | – | – | 27,331 | 27,331 | 27,355 |
| `!:1<:3.0` | 27,287 | – | 27,287 | 27,287 | 27,287 |
| `:1<^3.0` | err | – | err | 2,377 | err |
| `:1<;3.0` | err | – | err | 23 | – |
| `:;5` | 0 | 0 | 0 | 19 | err |
| `:1-10 & !@H= \| :20` | 92 | – | 92 | 92 | 92 |
| `:1-10 & (!@H= \| :20)` | 76 | – | 76 | 76 | 76 |
| `(:1-10` | err | – | err | err | err |
| `:1-10&` | err | – | err | err | err |
| `WAT` | err | – | err | 27,356 | err |
| `*` | 27,356 | – | 27,356 | 27,356 | 27,356 |
| `:10-1` | 0 | – | 0 | err | 0 |

## Things I could not establish

- sander's own source (mask parser, declared lengths, which coordinates its distance masks use).
  What sander does is EXECUTED above for 17 cases, but not read in its source.
- Whether cpptraj reads elements for `@/` from `ATOMIC_NUMBER` or guesses them from names and masses.
  I did not open that part of cpptraj.
- What `iwrap_mask` does. sander26 accepts it (EXECUTED), pmemd26 rejects it (EXECUTED), and there is no
  documentation and no search hit.
- Whether any mask is re-evaluated during a sander run (pmemd: no, by its source).

## Files I produced in this directory (other files here belong to other tasks)

- `Amber26.pdf`, `Amber26.txt` (pdftotext -layout), `Amber26.pageidx.txt` (each line prefixed with its PDF page)
- `prmtop.pdf`, `prmtop.txt`, `FileFormats.html/.txt`, `amberhub_mask.html/.txt`, `parmed/*.html/.txt`
- `cpptraj/*.cpp` (CPPSRC copies), `parmed/mask.py` (PESRC copy)
- `run_masks.py`, `cases1.txt`, `cases2.txt`, `pmemd_probe1.log`, `pmemd_probe2.log` (pmemd probes)
- `parmed_probe.py`, `parmed_probe.log` (ParmEd probes)
- `namelist_probe.py`, `namelist_probe.log` (which `&cntrl` names pmemd26 and sander accept; table 3.5)
- `adhoc_probes.py`, `adhoc_probes.log` (cpptraj with quoted masks, `select WAT`, `@C=` vs `@/C`, the ambmask
  length limit, and the `-c` vs `-ref` distance-mask test, 132 vs 143)
- `run_tools.py`, `cases_sander.txt`, `ambmask_probe.log`, `cpptraj_probe.log`, `sander_probe.log`
  (AmberTools26 probes; `sys/` holds copies of the test topology and restarts, plus an ASCII restart
  made by cpptraj for ambmask)
