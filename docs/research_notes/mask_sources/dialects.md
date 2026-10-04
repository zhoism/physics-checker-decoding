# Atom-selection dialects vs the AMBER mask

2026-10-02. This note supports the AMBER-mask study (`docs/research_notes/masks_scout.md`). No repository was edited.

**Executed:** ambmask and cpptraj V6.24.0 (prime-amber env) were run on a scratch copy of the gold system
(`masks/pilot/system/complex.parm7` + `ascii.rst7`, 27,356 atoms). Every [EXEC] row below comes from
those runs. **Read:** the official selection pages for each tool, plus parser source code where the docs are
silent ([READ-src]). **Unverified:** anything marked [LEAD] (seen only in a search snippet) or "not stated".

Legend: **[READ]** I read it on the official page and the quote is verbatim. **[READ-src]** I read it in the
tool's own source code, at master/main on 2026-10-02. **[EXEC]** I ran it. **[LEAD]** search snippet only.

## Sources

| tool | official page read | version seen |
|---|---|---|
| AMBER mask (sander/pmemd/ambmask) | Amber 2026 Reference Manual ch. 25 "Atom and Residue Selections", https://ambermd.org/doc12/Amber26.pdf (pp. 509–512) | Amber26 PDF, 2026-08-31 |
| cpptraj | same PDF, §38.3.2 "Atom Mask Selection Syntax" (pp. 728–729); mirror at https://amberhub.chpc.utah.edu/atom-mask-selection-syntax/ ; source https://github.com/Amber-MD/cpptraj (src/MaskToken.cpp, ArgList.cpp, StringRoutines.cpp) | V6.24.0 executed |
| VMD | User's Guide 1.9.4 "Selection Methods", https://www.ks.uiuc.edu/Research/vmd/vmd-1.9.4/ug/node90.html, keywords node91, booleans node92, quoting node94, regex node95, comparison node97, within/same node98 | UG 1.9.4 |
| MDAnalysis | https://docs.mdanalysis.org/stable/documentation_pages/selections.html ; source package/MDAnalysis/core/selection.py | 2.10.0 |
| PyMOL | PyMOL Wiki (community wiki, which is PyMOL's de facto manual): https://pymolwiki.org/index.php/Selection_Algebra , /Selection_Macros , /Property_Selectors , /Atom_name_wildcard , /Selection_Language_Comparison | wiki pages edited 2017–2019 |
| MDTraj | https://mdtraj.org/1.9.4/atom_selection.html (newer doc URLs returned 403 to curl); source mdtraj/core/selection.py at master (latest release 1.11.1) | docs 1.9.4, source master |
| GROMACS gmx select | https://manual.gromacs.org/current/onlinehelp/selections.html ; default groups https://manual.gromacs.org/current/reference-manual/analysis/using-groups.html ; source src/gromacs/selection/sm_simple.cpp, parser.y | 2026.4 |
| GROMACS make_ndx | https://manual.gromacs.org/current/onlinehelp/gmx-make_ndx.html ; editor help text in src/gromacs/tools/make_ndx.cpp | 2026.4 |
| CHARMM | https://academiccharmm.org/documentation/latest/select | page served c49b2 |
| ChimeraX (extra: the dialect closest to AMBER) | https://www.cgl.ucsf.edu/chimerax/docs/user/commands/atomspec.html | current |

## Decisive lines per tool

**AMBER mask (sander, pmemd, ambmask)** [READ, Amber26 §25.1 and §25.1.1]
- "These start with ":" to select by residues, or "@" to select by atoms." ... "atoms can be selected by AMBER atom type, in which case "@" must be immediately followed by "%". The notation ":*" means all residues and "@*" means all atoms."
- "A wildcard "=" in an atom or residue name matches any name starting with a given character (or characters) ... It cannot be used to match the end part of names (such as [:=A])."
- "Note that in the above example, N* is actually an atom type. The * is not a wild card meaning "all N-something types"!"
- "binary operators "&" (and) and "|" (or), unary operator "!" (negation), distance binary operators "<:", ">:", "<@", ">@", and parentheses. ... Parentheses have the highest priority, followed by distance operators ..., "!" (negation), "&" (and) and "|" (or) in order of descending priority."
- "[:5 <@4.5] .. all atoms within 4.5A from residue 5"; "[:* & !@H=] or [!@H=] .. all heavy atoms"; "@CA,C,O,N,H = ... (i.e., the entire protein backbone)".
- "Atom and residue names and numbers are taken from the Amber topology. Beware that the selection string works on those names and not the ones from the original PDB file." Atom numbers are "the actual sequential numbers of atoms in the file".
- "(The "maskstr" selection string is similar syntactically to UCSF Chimera/Midas.)" "Selections are case insensitive." BUGS: "there is no way to distinguish ... alpha carbon CA and a calcium ion Ca".

**cpptraj** [READ, Amber26 §38.3.2]
- "All masks are case-sensitive." (ambmask says the opposite; see the executed checks below.)
- Extra elementary selections: "@/{atom_element_name} e.g. '@/N'", "::{chain id} e.g. '::B'", ":;{pdb residue number}", "^{molecule numlist}".
- "'*' Zero or more characters. '=' Same as '*' '?' One character." Escape with backslash: "@C?\*".
- Distance operator "{<|>}{@|:|;|^}"; "Selection by distance for everything but the mask action requires defining a reference frame".
- [READ-src] Operator priority in MaskToken.cpp: `<`,`>` = 6, `!` = 5, `&` = 4, `|` = 3, the same order as ambmask. Distance selection uses `DIST2_NoImage`, so periodic images are not considered.
- [READ-src] `ArgList::GetMaskNext`: "A mask MUST include one of the following: ':' residue '@' atom '*' everything". `StrIsMask` also accepts `^` and `=` (after any leading `!` or `(`). Any other argument is not read as a mask.

**VMD** [READ, UG 1.9.4]
- Examples: "name CA", "resid 35", "backbone", "not protein", "within 5 of name FE", "exwithin 3 of protein", "same resname as (protein within 5 of nucleic)".
- "VMD has operator precedence similar to C so ... name CA or name CB and mass 12 to 17 actually selects all atoms named CA or those that are named CB and have the appropriate mass."
- "if neither and nor or are located after a boolean keyword, then an implicit and is inserted" ("protein name CA").
- Keyword table: "index | num | the atom number, starting at 0"; "serial | num | the atom number, starting at 1"; "backbone | the C, N, CA, and O atoms of a protein and the equivalent atoms in a nucleic acid"; "hydrogen | name "[0-9]?H.*""; "water ... resname H2O, HH0, OHH, HOH, OH2, SOL, WAT, TIP, TIP2, TIP3 or TIP4"; "protein | a residue with atoms named C, N, CA, and O".
- Wildcards are regexes in double quotes: "name "C.*"". VMD "automatically prepends "^(" and appends ")$"". The lexer "cannot handle an unquoted asterisk (* conflicts with multiplication ...)".
- "within <number> of <selection> ... selects all atoms within the specified distance (in Å) from a selection, including the selection itself."

**MDAnalysis** [READ, 2.10.0]
- "using a syntax very similar to CHARMM's atom selection syntax". "Keywords are case sensitive." "Selections are parsed left to right".
- "resid ... A range consists of two numbers separated by a colon (inclusive) such as resid 1:5." Integer attributes also accept "0 - 2", "0:2", or "0 to 2".
- Glob patterns (fnmatch): `?`, `*`, `[seq]`, `[!seq]`.
- "around 3.5 protein selects all atoms not belonging to protein that are within 3.5 Angstroms from the protein". "By default periodicity is taken into account".
- "bynum ... (1-based)"; "index ... (0-based)"; "id corresponds to the serial number in the PDB format".
- [READ-src] `AndOperation` and `OrOperation` both have `precedence = 3`, so `A or B and C` parses as `(A or B) and C`. `not` = 5. `around`, `byres` and `same` = 1, so they take everything to their right. `backbone` = `{"N", "CA", "C", "O"}`.

**PyMOL** [READ, PyMOL Wiki]
- Operators `not`/`!`, `and`/`&`, `or`/`|`. "S1 S2 | implicit or". "All "by"-operators have a weak priority, so (byres S1 or S2) is actually identical to (byres (S1 or S2))".
- Identifiers: "resi 100-200", "resn ALA", "name CA", "chain C", "segi S", "elem C", "hydrogens | h.", "backbone | bb.", "solvent | sol. | Water molecules", "polymer.protein", "polymer.nucleic", "inorganic | Non-polymer inorganic atoms/ions", "%sele | Named selection".
- Lists use plus signs: "The items in a list of identifiers are separated by plus signs (+) only." Example: "name CA+CB+CG+CD".
- Distances: "S1 within 12.3 of S2" (it includes s2 "if matches s1"); "around" and "near_to" never include it.
- Macros: "/object-name/segi-identifier/chain-identifier/resi-identifier/name-identifier".
- Atom_name_wildcard: "This setting controls whether or not PyMOL will respect wildcards ("*")".
- "names and keywords are case-insensitive unless ignore_case is set".

**MDTraj** [READ, 1.9.4 docs]
- "MDTaj's trajectory analysis functions use 0-based arrays of "atom indices"".
- Keyword table: "index | Atom index (0-based)"; "residue | resSeq | Residue Sequence record (generally 1-based, but depends on topology)"; "resid | resi | Residue index (0-based)"; "chainid | Chain index (0-based)"; "type | element, symbol | 1 or 2-letter chemical symbols".
- Example "top.select("resid 10 to 30")". Regex is "=~" with "native python Regex syntax". C-style "&&, ||, !".
- [READ-src] There is no `nucleic` keyword (the line is commented out in the source). Bare literals are `Word(alphas, alphanums)` or quoted strings, so a glob like `H*` is not a literal. `not` binds tightest. Inside the binary operators, precedence follows the alphabetical sort of the operator tokens, so `and` binds tighter than `or`, but `&&` and `and` sit at different levels. Use parentheses.

**GROMACS gmx select** [READ, 2026.4]
- "it is possible to use wildcards (name "C*") or regular expressions (e.g., resname "R[AB]"). The match type is automatically guessed ... To force the matching to use literal string matching, use name = "C*"".
- "resnr selects atoms using the residue numbering in the input file. resid is synonym for this keyword for VMD compatibility. resindex N selects the N th residue starting from the beginning of the input file." "group NR, where NR is a zero-based index of the group".
- Distances are in nm: "All atoms of a residue LIG within 0.5 nm of a protein ... resname LIG and within 0.5 of group "Protein"".
- There is no `protein`, `water`, `backbone`, `element` or `hydrogen` keyword in the keyword list. Those come from default index groups: "Backbone | protein backbone atoms; N, Cα and C"; "MainChain | ... N, Cα, C and O"; "Protein-H | protein atoms excluding hydrogens"; "Water"; "Ion"; "DNA"; "RNA".
- [READ-src] `atomnr` = index + 1 and `resindex` = index + 1 (sm_simple.cpp), so both are 1-based. parser.y declares `%left OR XOR`, `%left AND`, `%left NOT`, which gives not > and > or.

**GROMACS make_ndx** [READ, page plus the editor help text in source]
- "The atom numbering in the editor and the index file starts at 1."
- "'a' name1[*] ... : selects atoms by name(s), '?' matches any char, wildcard '*' allowed at the end of a name." "'r' nr1 - nr2 : selects residues in the range". "'ri' ... residue indices, 1-indexed". "'chain' ch1".
- "& | : AND and OR ... the input is processed from left to right." Example: "a C* & !a C CA".

**CHARMM SELEct** [READ, c49b2]
- Operators are dotted words: ".OR.", ".AND.", ".NOT.", ".AROUND.", ".BYRES.". "Listed in priority order (low to high)": .OR. < .AND. < .AROUND./.SUBSET. < .NOT./.BONDED./.BYRES./.BYGROUP.
- "RESId <resid1> : <resid2>" (ranges use a colon). "TYPE <type>*" is the atom name ("'SELTYPE' - Atom name of first selected atom"). The force-field type is "CHEMical".
- Wildcards: "* matches any string ..., % matches any single character, # matches any string of digits ..., + matches any single digit."
- "The token HYDRogen selects all hydrogens (based on a mass selection)." "sele bynu 1 : 100 end !will include atoms number 1 to 100."
- `@I` is script-variable substitution ("COOR DIST SELE INTERESTING .SUBSET. @I END").

**ChimeraX** [READ] (not requested, but it is the dialect AMBER says it resembles)
- Hierarchy symbols: "# model", "/ chain", ": residue", "@ atom". Names are case-insensitive. Wildcards are `*` and `?`.
- The zone operator puts the level symbol first: "@nz @< 3.8 – atoms within 3.8 Å of atoms named NZ". AMBER writes it the other way round: `@NZ<@3.8`. Negation is "~" (AMBER uses `!`). "& has higher priority" than "|".
- Built-in classes: "solvent, ions, ligand, main", "protein", "nucleic", "backbone ... peptide N, CA, C, O ... and any directly attached hydrogens", and bare element symbols ("C, Fe, etc.").

## Concept table

Notes: numbers in the AMBER and cpptraj columns are sequential topology numbers. "—" means no such keyword in the docs I read.

| concept | AMBER mask (sander/pmemd) | cpptraj | VMD | MDAnalysis | PyMOL | MDTraj | gmx select | make_ndx | CHARMM |
|---|---|---|---|---|---|---|---|---|---|
| residue by number | `:10` | `:10`; `:;10` = PDB number | `resid 10` | `resid 10` | `resi 10` | `resSeq 10` (file); `resid 9` (0-based index) | `resnr 10` = `resid 10` | `r 10` | `RESId 10` |
| residue range | `:10-20` | `:10-20` | `resid 10 to 20` | `resid 10:20`, `10 - 20`, `10 to 20` | `resi 10-20` | `resSeq 10 to 20` | `resnr 10 to 20` | `r 10 - 20` | `RESId 10 : 20` |
| residue by name | `:LYS`, `:ARG,ALA` | same | `resname ALA PHE` | `resname LYS` | `resn ASP+GLU` | `resname ALA` | `resname RA RB` | `r SOL` | `RESName ALA` |
| atom by name | `@CA`, `@CA,C,O` | same | `name CA CB` | `name CA` | `name CA+CB` | `name CA` | `name CA` | `a CA` | `TYPE CA` (TYPE = atom name) |
| name wildcard | `=` prefix only (`@H=`); `*` only alone (`:*`, `@*`) | `*`, `=`, `?` anywhere; `\*` escapes | regex in double quotes, auto-anchored (`name "H.*"`); no unquoted `*` | glob `*` `?` `[seq]` | `*` (atom_name_wildcard) | regex `name =~ 'H.*'`; no glob | `name "H*"`, `?`; regex auto-detected; `name = "C*"` is literal | trailing `*`, `?` | `*` `%` `#` `+` |
| element | — | `@/N` | `element N` | `element N` | `elem N` | `element N` = `type N` = `symbol N` | — | — | — |
| FF atom type | `@%CT` | `@%CT` | `type` | `type` | `text_type` / `tt.` | — (`type` is element) | `type` = `atomtype` | `t` (needs .tpr) | `CHEMical` |
| hydrogens | `@H=` (by name). `@H` is only atoms named exactly H | `@H=`, `@H*`, `@/H` | `hydrogen` (name regex `[0-9]?H.*`), `element H` | `element H`, `name H*` | `hydrogens` / `h.` | `element H` | `name "H*"` | `a H*` | `HYDRogen` (by mass) |
| heavy atoms | `!@H=` | `!@H=`, `!@/H` | `not hydrogen` (`noh` macro: [LEAD]) | `not element H` | `not hydrogens` | `not element H` | `not name "H*"`; group `Protein-H` | `! a H*` | `.NOT. HYDRogen` |
| backbone | — (manual example `@CA,C,O,N,H`) | — (manual example `@CA,C,O,N,H`) | `backbone` = C, N, CA, O | `backbone` = N, CA, C, O | `bb.` (atoms not listed) | `backbone` (atoms not listed) | group `Backbone` = N, CA, C; `MainChain` = N, CA, C, O | group by name | — |
| protein | — (residue range) | — | `protein` | `protein` (fixed list of residue names) | `polymer.protein` | `protein` | group `"Protein"` | `"Protein"` | — (`DEFIne`) |
| nucleic | — | — | `nucleic` | `nucleic` | `polymer.nucleic` | — | groups `DNA`, `RNA` | groups | — |
| water | — (`:WAT`) | — (`:WAT`) | `water` (includes WAT, HOH, TIP3 ...) | `water` (same kind of list) | `solvent` | `water` | group `Water` / `SOL` | `"Water"` | — |
| ions | — (names, e.g. `:Na+,Cl-`) | — | `ion` macro [LEAD] | — | `inorganic`, `metals` | — | group `Ion` | `"Ion"` | — |
| chain / segment | — | `::A` (needs chain IDs in the topology) | `chain A`, `segname` | `chainID A`, `segid` | `chain A`, `segi` | `chainid 0` (0-based integer) | `chain A` | `chain A` | `SEGId PROA` |
| within d of X | `X<@5.0` atoms, `X<:5.0` whole residues, `>` = beyond. Å. Reference included [EXEC] | same, plus `<;` (residue centre) and `<^` (molecule). Needs a reference frame. No PBC | `within 5 of X` (includes X); `exwithin` (excludes X) | `around 5 X` (excludes X; PBC on) | `S1 within 5 of S2` (includes S2 if it matches S1); `around` and `near_to` exclude | — | `within 0.5 of X` (**nm**) | — | `X .AROUND. 5.0` |
| same residue as | via `<:` only | via `<:` only | `same residue as X` | `byres X`, `same residue as X` | `byres` / `br.` (weak priority) | — | `same residue as X` | — | `.BYRES. X` |
| booleans | `!` `&` `\|` | same | `not` `and` `or` | `not` `and` `or` | `not`/`!`, `and`/`&`, `or`/`\|`; adjacent selections are OR | `not`/`!`, `and`/`&&`, `or`/`\|\|` | `not` `and` `or` (and `xor` in source) | `!` `&` `\|` | `.NOT.` `.AND.` `.OR.` |
| precedence | () > distance > ! > & > \| | same [READ-src] | C-like (and before or); implicit **and** after a boolean keyword | **and = or**, left to right [READ-src] | not stated; "by" ops weak | not > and > or (quirky) [READ-src] | not > and > or [READ-src] | left to right, no precedence | .OR. < .AND. < .AROUND. < .NOT./.BYRES. |
| numbering base | 1-based sequential topology numbers, not PDB numbers | same; `:;` gives PDB numbers | `index` 0, `serial` 1, `resid` from file | `index` 0, `bynum` 1, `id` and `resid` from file | `resi` and `id` from file; `index` internal (base not stated) | `index` 0, `resid` 0 (index), `resSeq` from file, `chainid` 0 | `atomnr` 1, `resindex` 1, `resnr` from file, group number 0 | atoms 1, `ri` 1, `r` from file | `BYNU` 1, `IRES` sequential, `RESId` is a label |
| case | insensitive | **sensitive** | (not checked) | keywords case-sensitive | insensitive by default | (not checked) | (not checked) | `case` toggle | (not checked) |

## Executed checks (ambmask vs cpptraj, gold system, 27,356 atoms)

| mask | ambmask (= pmemd engine, per scout) | cpptraj `select` | note |
|---|---|---|---|
| `@CA` / `@ca` | 154 / 154 | 154 / **0** | ambmask ignores case; cpptraj is case-sensitive |
| `:WAT` / `:wat` / `:HOH` | 24,976 / (same) / **"Warning: no atoms selected"** | 24,976 / **0** / **0** | HOH is the PDB and VMD water name; AMBER uses WAT. An empty selection is not an error |
| `@H=` / `@H*` / `@/H` | 13,676 / **error** / **error** | 13,676 / 13,676 / 13,676 | `@H*` and `@/H` are cpptraj-only |
| `@H` | 148 | 148 | only atoms named exactly "H" (amide H), not all hydrogens |
| `:5` / `:5<@3.0` / `(:5<@3.0)&!:5` | 19 / 43 / 24 | 19 / 43 / 24 | distance masks include the reference residue (VMD `within` semantics, not MDAnalysis `around`) |
| `:5<:3.0` | 134 | 134 | whole residues |
| `:HID,:HIE` / `:HID,HIE` | **error** / 85 | 85 / 85 | repeating `:` inside a list is cpptraj-only |
| `@(N,CA,C,O)` | **error** | **error** | |
| `:1:10` (colon range, CHARMM/MDAnalysis style) | **error** | **22 atoms = residues 1 and 10 only** (`:1-10` = 145) | cpptraj silently reads it as a list |
| `protein and name CA`, `resname HOH`, `name H*` | **error** | **27,356 = every atom**, no error | [READ-src] cpptraj only treats an argument as a mask if it starts with `@ : ^ * =` (after `!` or `(`). Otherwise the mask is empty and `select` uses all atoms |
| `resid 10 to 20` | **error** | error ("Topology index 10 not found": the `10` was read as a parm index) | |

The `select` all-atoms fallback is the one I executed. I did not check whether other cpptraj actions (`rms`, `strip`) also fall back silently. cpptraj issue #697 (closed 2019, [READ]) reports a related case: "CPPTRAJ sometimes does not exit with error for bad masks".

## Where the observed small-model strings come from

| model wrote | valid in | AMBER mask |
|---|---|---|
| `protein and name CA` | VMD, MDAnalysis, MDTraj (gmx select needs `group "Protein" and name CA`; PyMOL needs `polymer.protein`) | `@CA`. AMBER has no protein keyword. Restrict by residue range if needed |
| `resname HOH` | VMD, MDAnalysis, MDTraj, gmx select | `:WAT`. `:HOH` is legal but selects nothing |
| `@H*` | cpptraj (and ParmEd, per scout) | `@H=` |
| `name H*` | MDAnalysis, PyMOL, gmx select (docs say to quote it: `name "H*"`), make_ndx `a H*`, CHARMM `TYPE H*`. **Not** VMD (needs `name "H.*"`) and **not** MDTraj (needs `=~`) | `@H=` |
| `resid 10 to 20` | VMD, MDAnalysis, gmx select. MDTraj also accepts it, but there it means 0-based residue **indices** 10–20, which are file residues 11–21 when the file numbers residues contiguously from 1 | `:10-20` |

## Confusions an AMBER mask writer is likely to make, by source dialect

**From VMD**
1. Word operators `and/or/not` instead of `& | !`.
2. Keywords AMBER masks lack: `protein`, `backbone`, `water`, `hydrogen`, `nucleic`, `ion`.
3. `resid A to B` instead of `:A-B`.
4. Regex wildcards (`"C.*"`) instead of the prefix `=` (`@C=`).
5. Infix distance `within 5 of X` instead of postfix `X<@5`. The reference goes first in AMBER. Both VMD `within` and AMBER `<@` include X, so a translation of VMD `exwithin` needs `&!X`.
6. `same residue as (within 5 of X)` maps to `X<:5`. AMBER has no general byres.
7. PDB/VMD water name HOH instead of WAT. It fails silently.
8. `chain A`: ambmask has no chain selector, and cpptraj `::A` needs chain IDs in the topology.
9. Implicit AND after a boolean keyword (`protein name CA`). PyMOL's implicit operator is OR.
10. `index N` is 0-based; AMBER `@N` is 1-based.

**From MDAnalysis**
1. Glob `*`, `?` and `[...]` in names. Only `=` (prefix) works in pmemd.
2. Colon ranges `resid 1:5`. In AMBER `:` is the residue prefix, and cpptraj silently reads `:1:5` as residues 1 and 5.
3. `around` excludes the reference; AMBER `<@` includes it.
4. `and` and `or` have equal precedence, left to right. A literal translation of `A or B and C` into `A|B&C` changes the meaning, because AMBER `&` binds tighter.
5. `type` means the force-field type, as AMBER `@%` does. In MDTraj `type` is the element, and in CHARMM `TYPE` is the atom name.
6. `segid` / `chainID` have no pmemd equivalent.

**From PyMOL**
1. `+` list separators (`name CA+CB`, `resi 1+2`). AMBER uses commas, and `+` appears literally in AMBER ion names such as `Na+`.
2. Keywords `elem`, `hydro`, `bb.`, `solvent`, `polymer.protein`, `inorganic`, and dotted short forms (`r.`, `n.`, `i.`).
3. Implicit OR between adjacent terms.
4. `%sele` is a named selection in PyMOL; `@%` is atom type in AMBER.
5. Slash macros `A/10/CA`; in cpptraj `@/` is the element selector.
6. `within` vs `around` vs `near_to`, with different inclusion of the reference.

**From MDTraj**
1. `resid` and `index` are 0-based, so a mask built from MDTraj numbers is off by one in AMBER.
2. `type` = element.
3. `chainid` is a 0-based integer.
4. Regex through `=~`, and C-style `&&` / `||`.
5. No distance keyword in the DSL.

**From GROMACS**
1. `within 0.5 of` is in nm (= 5 Å). Copying the number into an AMBER mask (`<@0.5`) would give a cutoff 10× too small, because AMBER uses Å.
2. `resid` here means the file number, but `residue` is a 1-based index.
3. Default groups (`"Protein"`, `"Backbone"` = N, CA, C) are not mask syntax. Backbone membership also differs between tools (GROMACS N, CA, C; VMD and MDAnalysis add O; the AMBER manual example adds O and H).
4. `=` forces literal matching in gmx select (`name = "C*"`) but is the wildcard in AMBER.
5. make_ndx `r 10-20` / `a CA` look close to AMBER but have no `:` or `@`. make_ndx `& |` are read strictly left to right.
6. GROMACS water is `SOL`, not `WAT`.

**From CHARMM**
1. Dotted operators `.AND.` / `.OR.` / `.NOT.`.
2. `TYPE` = atom name, while AMBER `@%type` = force-field type (CHARMM's `CHEMical`). A model could write `@%CA` meaning atom name CA.
3. `RESId 1 : 10` colon ranges.
4. `%` is a one-character wildcard in CHARMM but the type selector in AMBER. `+` matches one digit in CHARMM but is literal in AMBER ion names.
5. `@name` is variable substitution in CHARMM scripts.
6. `HYDRogen` is mass-based; AMBER `@H=` is name-based.

**From cpptraj (inside the AMBER family)**
1. `@H*`, `?`, `@/H`, `::A`, `:;N`, `^N`, `<;` and `:A,:B` are all valid in cpptraj and rejected by pmemd/ambmask.
2. Case: cpptraj is case-sensitive (`@ca` gives 0 atoms); ambmask is not.
3. ambmask's `=` matches prefixes only (`:=A` is invalid); cpptraj's `=` is a full wildcard.
4. In a cpptraj command, a VMD-style string is not read as a mask at all, and `select` falls back to every atom.

**General (not tied to one dialect)**
- `@H` selects only atoms named exactly "H", not all hydrogens. The scout's 7B wrote `!@H` for "non-hydrogen".
- AMBER residue numbers are tleap's sequential 1-based numbers, not the PDB's. MDAnalysis/VMD `resid` and PyMOL `resi` carry file numbers.

## Same symbol, different meaning

| symbol | AMBER mask | elsewhere |
|---|---|---|
| `:` | residue selector; `<:` residue-level distance; cpptraj `::` chain and `:;` PDB number | range separator in MDAnalysis (`resid 1:5`) and CHARMM (`RESId 1 : 10`); residue level in ChimeraX |
| `@` | atom selector; `<@` atom-level distance | atom level in ChimeraX (`@CA`) and the zone operator `@<` (reversed order); variable substitution in CHARMM (`@I`); not a selection operator in PyMOL (PyMOL's `@script` runner: [LEAD]) |
| `*` | only alone (`:*`, `@*`) in pmemd; a literal character inside type names (`@%N*`); a wildcard in cpptraj | glob in MDAnalysis, PyMOL, gmx select, make_ndx (trailing only), CHARMM; multiplication unquoted and a regex quantifier quoted in VMD; `*` alone = `all` in PyMOL |
| `=` | prefix wildcard (pmemd); full wildcard (cpptraj) | equality in VMD and MDTraj; literal-match operator in gmx select (`name = "C*"`); comparison in PyMOL (`fc. = -1`) |
| `%` | `@%` = force-field atom type | named selection in PyMOL (`%sele`); one-character wildcard in CHARMM and X-PLOR (VMD UG table 6.10) |
| `?` | invalid in pmemd; one-character wildcard in cpptraj | one-character glob in MDAnalysis, gmx select, make_ndx, ChimeraX; "named selection or empty" in PyMOL (`?sele`) |
| `+` | literal in residue names (`:Na+`) | list separator in PyMOL; one-digit wildcard in CHARMM; "any digit" in the X-PLOR wildcards that VMD lists |
| `#` | — | any digit string in CHARMM; model in ChimeraX |
| `/` | invalid in pmemd; `@/N` = element in cpptraj | macro field separator in PyMOL; chain in ChimeraX (`/A`) |
| `^` | molecule in cpptraj (`^1`); distance level `<^` | regex anchor in VMD; exponent in gmx select |
| `-` | range (`:1-10`) | range in PyMOL `resi`, make_ndx and MDAnalysis (`0 - 2`); negative numbers elsewhere |
| `<` `>` | distance operators (`<@`, `>:`) | numeric comparison in VMD, MDTraj, MDAnalysis `prop`, PyMOL `b < 50` |
| `!` | not | not in PyMOL, MDTraj, make_ndx; part of `!=` in VMD and MDTraj; ChimeraX uses `~` for not |
| `&` `\|` | and / or | the same in PyMOL and make_ndx; MDTraj uses `&&` / `\|\|` |
| `.` | — | short-form suffix in PyMOL (`r.`, `n.`); operator delimiters in CHARMM (`.AND.`); chain in Chimera (`:32.A`, PyMOL wiki comparison table) |

## Published evidence that LLMs confuse these languages

I found no paper or benchmark that measures cross-dialect confusion in atom selections. The closest work:
- **MDCrow** (Campbell et al., arXiv 2502.09565) [READ]. Its analysis tools are built on MDTraj: "for anything related to analyses, you will use MDTraj". A text search of the PDF for selection, mask, VMD, MDAnalysis and PyMOL turned up no analysis of selection-syntax errors.
- **NAMD-Agent** (arXiv 2507.07887) [READ]. Analysis uses MDTraj and VMD. Selection errors are not discussed.
- **MDGym** (arXiv 2605.08941) [READ, partial]. Most agents that started a simulation "could not recover from scripting or configuration errors". The errors are not broken down by selection syntax.
- **LLM-generated LAMMPS scripts** (Holbrook, Verduzco, Strachan, arXiv 2603.20630) [READ, passages]. "most common errors involve incorrect pair style usage, malformed math expressions, and invalid region or group definitions"; "models also struggle with ... consistent definition of regions, groups". LAMMPS `group` is a selection language, and LAMMPS is this repo's second testbed.
- A PDF text search of MDAgent2 (2601.02075), MDForge (2606.12916), ChemGraph (2506.06363), the agentic atomistic frameworks (2606.09422, 2607.22596), and the reviews 2608.18508 and 2608.23104 found no selection-syntax error analysis [READ, grep only].
- Agentic PyMOL, ChatMol and pymol-chat (LLM → PyMOL command tools) exist, with execute-and-retry loops. I found no error analysis [LEAD].
- The Gohlke-lab JCIM viewpoint "Chat-Driven Computational (Bio)chemistry" uses LLMs on AMBER code (LEaP speed-ups), not masks [READ].

The strongest direct evidence is this repo's own scout (`masks_scout.md`): Qwen 7B went 29/30 rejected for "VMD/MDAnalysis syntax, right intent", and Haiku repeated `@H*`, `:HID,:HIE`, `@(N,CA,C,O)` and distance-syntax errors. The cpptraj-only forms among those (`@H*`, `:HID,:HIE`) suggest some errors come from the AMBER family itself (cpptraj or ParmEd), not only from VMD.
