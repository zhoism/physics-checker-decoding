# AMBER mailing list: real atom-mask mistakes, with sources

Compiled 2026-10-02 from the AMBER mailing-list archive (http://archive.ambermd.org/). Every thread
below was fetched with curl and its message bodies were read (marked **READ**). Search-only hits are
listed separately at the end (marked **LEAD**). No URL here was guessed: each one was fetched or
returned by a `site:archive.ambermd.org` web search.

## How to read this file

- **What a mask is.** An AMBER mask is a short string that picks atoms out of a simulation's topology
  file (prmtop). `:` selects residues by number or name (`:1-10`, `:WAT`). `@` selects atoms by name
  (`@CA`) or by number (`@100-200`). `@%` selects by atom *type*, and `&`, `|` and `!` mean
  and, or and not. `<:` and `>:` select by distance. Masks feed position restraints (`restraintmask`
  with `ntr=1`), frozen atoms (`bellymask` with `ibelly=1`), free-energy regions (`timask`/`scmask`),
  MM-PBSA partitions (`receptor_mask`, `ligand_mask`, `strip_mask`) and every cpptraj analysis.
- **Roles.** Repliers are named by role, not by name: "AMBER lead developer", "cpptraj lead developer",
  "MMPBSA.py developer" and so on. A role comes from the person's well-known AMBER work. Where I am
  less sure, the role says only "list member".
- **Quotes** are verbatim as the archive renders them, cut down with "...". Masks are in code.

### CRITICAL CAVEAT: the archive rewrites `@` as `.` inside masks

The archive's spam protection rewrites most `@` characters as `.`, including the ones inside masks.
So `!@H=` (exclude hydrogens) shows up as `!.H=`, and `:1-185@CA` shows up as `:1-185.CA`. The
rewrite is inconsistent. Some `@` survive, for example after `&` (`:170,185&@CA,C,N` in 201602/0121),
before `%` (`@%ob` in 201903/0153), and as the HTML entity `&#64;` (202307/0122). Pages from 2022
are still rewritten (202207/0011, 202211/0168). I confirmed this in the raw HTML. Two consequences:

1. In at least two threads, a developer's correction of a user who really typed a period is now
   unreadable. In 201501/0087 the wrong mask and the "corrected" mask print identically. In
   201811/0147 the correction reads *'the mask selection character for "atom" in Amber syntax is "."
   (at), not "." (period).'* Both are in raw HTML (201501_0087 lines 92-94; 201811_0147 line 88).
2. **Any corpus scraped from this archive teaches `.` where AMBER needs `@`.** At least three users
   in this sample (2015, 2018, 2018) really typed `.` for atoms. Whether any of them copied it from
   the archive is **unverified**.

In the entries below, a mask is shown as it was originally written. Where the archive shows it
differently, the entry says so with "[archive: ...]".

---

## Threads (READ)

### A. Residue numbering and chains

**M01. "Two chains, what is my restraintmask?"** READ
- URL: http://archive.ambermd.org/201204/0165.html (question), http://archive.ambermd.org/201204/0170.html (answer)
- Date: 2012-04-08
- Problem: *"if I have a protein complex, 1 chain with residue from 1 to 119, the other chain with residue from 1 to 30, will you please tell me the restraintmask?"*
- Mask: `':1-119 & !@H='` [archive: `!.H=`]
- What was wrong: the user thought in PDB chain numbering (two chains, each starting at 1). AMBER has
  no chain concept in sander masks and numbers all residues consecutively.
- Resolution (AMBER lead developer): *"Amber numbers residues consecutively, so the residue part of your restraintmask would probably be :1-149."*

**M02. "Numbering of amino acids got shifted after tleap"** READ
- URL: http://archive.ambermd.org/202106/0035.html, replies 0036, 0037, 0042
- Date: 2021-06-07
- Problem: *"In my initial PDB file, the numbering of amino acid starts with ALA (first amino acid) number 3, but in the topology PDB file ... ALA starts with number 1."*
- Mask: none yet. This is the root cause behind later mask errors.
- What was wrong: tleap renumbers every residue from 1. A PDB residue number is not an AMBER residue
  index.
- Resolution: a list member: *"Amber renumbers all residues ... in a consecutive order starting with residue number 1 ... you have to keep track of the two residue numberings."*
  AMBER lead developer: *"the choice was made to ignore chainId's in Amber codes. In multi-chain proteins, it is only the residue number/chainId pair that is unique ... Amber creates a 'residue index' (starting at 1 ...) but treats that like a 'residue number' ... it's actually the residue number/chainId/insertion code triplet that needs to be unique."*
  The cpptraj lead developer: *"The cpptraj mask parser has the ability to use PDB (original) residue numbering via the ':;' (colon semicolon) operator, and chain IDs via the '::' (colon colon) operator."*
  Those operators are cpptraj's. The sander/pmemd `restraintmask` parser has no chain selector.

**M03. "When and how is leap re-numbering residues?"** READ
- URL: http://archive.ambermd.org/201107/0247.html, reply http://archive.ambermd.org/201107/0296.html
- Date: 2011-07-12
- Problem: *"in a work flow there may be at least three different numbering schemes: 1) the residue numbering from the original PDB file 2) the leap-internal residue numbering directly after invoking loadpdb 3) the numbering of PDB files written by leap after invoking savepdb"*
- What was wrong: the documentation did not explain the three numberings.
- Resolution (AMBER lead developer): *"This is indeed annoying ... [leap] adds some large number to the 'real' residue number of chains beyond the first one ... the final residue numbering is indeed sequential, with no gaps."*

**M04. "Avoiding pdb4amber renumbering"** READ
- URL: http://archive.ambermd.org/201801/0217.html (question quoted inside)
- Date: 2018-01-23
- Problem: *"pdb4amber forces protein's atom numbering to start from 1. I certainly don't want that."*
- Resolution (AMBER lead developer): *"Amber ... internally always numbers atoms and residues starting at 1. It creates a 'renum' file than can be used to map the original numbering scheme to the new one ... there is no option to avoid the renumbering"*. He points to ParmEd `addPdb` and `ambpdb -ext`.

**M05. Same mask string, different atoms after `parmstrip`** READ
- URL: http://archive.ambermd.org/201808/0230.html, reply http://archive.ambermd.org/201808/0231.html
- Date: 2018-08-20
- Problem: *"Error: # selected coords (4959) != eigenvector size (5865) ... I have loaded no new parameter files, and the mask is identical in each case. Seemingly, though, the mask corresponds to a different number of atoms"*
- Mask: `:38-318&!@H=`, used both before and after `parmstrip !(:38-318&!@H=)`. cpptraj echoes the
  mask as `!@H*`, so `=` and `*` act as the same wildcard there.
- What was wrong: stripping residues renumbers the rest from 1, so `:38-318` names different residues
  after the strip.
- Resolution (AMBER/ParmEd developer): *"You have stripped out residues 1-37 and 319-... You now have 244 residues left ... These are now residues 1-244 since cpptraj always numbers residues from 1."*

**M06. Two crystal structures with offset numbering in one cpptraj rmsd** READ
- URL: http://archive.ambermd.org/201811/0040.html (question quoted), http://archive.ambermd.org/201811/0138.html
- Date: 2018-11-06
- Problem: *"Residue 4 in the second structure is residue 1 in the first structure ... The reference does have 159 residues but somehow residues 157,158,159 are cut off before the mask is applied."*
- Mask: `rmsd :1-156@CA :4-159@CA ... reftraj second.inpcrd parm second.prmtop`. cpptraj reported `Reference mask: [:4-159@CA](153)`.
- What was wrong: the reference mask was evaluated against the wrong topology. `parm second.prmtop`
  had never been loaded, and older cpptraj did not trap that error.
- Resolution (cpptraj lead developer): *"'parm' in the 'rmsd' command is referring to a topology that has not yet been loaded ... older version of cpptraj ... was using the wrong topology to set up the reference mask ... add a 'parm second.prmtop'."*

**M07. "leap changes residue order"** READ
- URL: http://archive.ambermd.org/201507/0012.html, http://archive.ambermd.org/201507/0037.html
- Date: 2015-07-01
- Problem: *"Leap keeps on changing the residue order. It seems like it puts all Na+ ions first and then the water molecules without taking into account the input order from the pdb file."*
- What was wrong: tleap deliberately moves solvent to the end, so residue indices are not the PDB order.
- Resolution (AMBER/ParmEd developer): *"Yes, this is intentional. In several places, Amber makes the assumption that all solvent residues appear at the very end of the system ... set default reorder_residues off ... buyer beware."* The user confirmed it worked.

**M08. Residue 9999 is followed by residue 0** READ
- URL: http://archive.ambermd.org/202405/0004.html (question quoted)
- Date: 2024-05-02
- Problem: *"When I save a pdb in cpptraj, it will only use 4 columns for the residue number, so residue 9999 will be followed by residue 0 ... leap will use 5 columns"*
- What was wrong: in large solvated systems, PDB residue numbers wrap around, so they cannot be used
  to build masks.
- Resolution (AMBER lead developer): *"Amber's internal residue number is incremented by one for each new residue, and need not correspond to what is in columns 23-26 of a PDB file. Amber also pretty much ignores chainID's (column 22)."*

### B. Residue and atom names

**M09. CHARMM-GUI membrane system: `TIP3`/`CLA`/`POPC` names; the wrong ligand number** READ
- URL: http://archive.ambermd.org/201704/0428.html, reply http://archive.ambermd.org/201705/0068.html
- Date: 2017-04-28
- Problem: *"ante-MMPBSA.py ... -n":279" -s":TIP3:MEMB:CLA:WAT:POPC" But it turns out that PDB is incorrect and it is actually 277 that is the ligand ... I am not to sure about the -s command so I covered all my bases."*
- What was wrong: the CHARMM residue names (`TIP3`, `CLA`, `POPC`) are not in MMPBSA.py's default
  strip list. The ligand's residue number also differed from the PDB. There were tool bugs as well.
- Resolution (cpptraj lead developer): used `-n ":277" -s ":POPC,WAT,CLA"`, and *"I also had to use a custom mask for mmpbsa.py input to ensure that POPC and CLA were stripped as well, e.g. strip_mask = ':WAT,Cl*,CIO,Cs+,IB,K*,Li+,MG*,Na+,Rb+,CS,RB,NA,F,CL,POPC,CLA'"*. He also suggested `strip !:277`.

**M10. CHAMBER topology with `POT`/`CLA`/`TIP3`** READ (no reply in the archive)
- URL: http://archive.ambermd.org/201710/0094.html
- Date: 2017-10-09
- Problem: *"My solvated.prmtop is generated from CHARMM files using CHAMBER and it has POT and CLA for potassium and chlorine atoms ... TIP3 for water. How would I get them stripped correctly"*
- What was wrong: AMBER names (`K+`, `Cl-`, `WAT`) and CHARMM names (`POT`, `CLA`, `TIP3`) differ.
  A mask written for one silently misses the other.

**M11. MMPBSA default strip list does not know membrane residues** READ
- URL: http://archive.ambermd.org/201107/0384.html (earlier messages quoted)
- Date: 2011-07-17
- Problem: membrane `POP` residues were left in the MM-GBSA trajectory: *"the coordinates for the membrane were never removed from that original mdcrd file, and thus they were improperly included"*
- Resolution (MMPBSA.py developer): *"strip_mask=:WAT:Cl-:POP"* and *"Special residues such as your membrane residues must be specified by the user since we, as the developers, would not be able to predict those residue names."*

**M12. Lipids split into several residues (`PA`/`PC`/`OL`)** READ (partial)
- URL: http://archive.ambermd.org/201708/0360.html, reply http://archive.ambermd.org/201709/0009.html (thread starts 201708/0261)
- Date: 2017-08-30
- Problem: *"how to define mask properly for the lipid e.g POPC? if I use :OL it works good but :OL,PA,PC calculate wrong area"*
- What was wrong: AMBER Lipid14/17 split one POPC lipid into three residues (PA, PC and OL). Which of
  them the mask names changes the count. In this thread the immediate fix was a missing option.
- Resolution (cpptraj lead developer): *"When you use the mask option cpptraj doesn't assume anything about how your lipids are arranged, which is why the 'nlayers' option is also required ... 'nlayers 2' for a bilayer."*
  The thread does not explain why `:OL` alone "worked".

**M13. 4-point water (OPC): extra points `EPW` vanish from PDB output** READ
- URL: http://archive.ambermd.org/201704/0215.html
- Date: 2017-04-16
- Problem: a cpptraj-written PDB could not be read back with the original topology.
- What was wrong: OPC water has a massless 4th site named `EPW`. By default cpptraj leaves it out of
  PDB files, so the atom counts stop matching.
- Resolution (cpptraj lead developer): *"the difference in the number of atoms is exactly equal to the number of solvent molecules - these are the missing extra points ... use the 'include_ep' keyword ... or ... create a new topology with the extra points stripped out (e.g. 'strip @EPW')."*

**M14. `@WAT` used where `:WAT` was meant (nobody caught it)** READ, my reading
- URL: http://archive.ambermd.org/201906/0348.html; replies 0349, 0353, 0355; follow-ups 201907/0036, 0049, 0075
- Date: 2019-06-27
- Problem: *"minimization of protein ligand complex ... with restraint on heavy atoms except water and hydrogen"*. The run then hit LINMIN failure with *"RESTRAINT = 6255.2630"*.
- Mask: `'(:* & !@H=) &!(@WAT | @Na+=)'` [archive: `.WAT`, `.Na+=`. The archive does not rewrite `:`,
  so the user typed `@` or `.` before WAT, not `:`]
- What was wrong (**my reading, not raised in the thread, and unverified because no "matches N atoms"
  line was posted**): `@WAT` asks for atoms *named* WAT, and none exist. Water is the *residue* WAT,
  made of atoms O, H1 and H2. So the water oxygens stay inside `:* & !@H=` and get restrained,
  against the stated intent. The intended mask was `!:WAT`.
- Resolution in thread: the repliers (one list member, then the AMBER lead developer) treated the
  LINMIN message as harmless and later as a bad starting structure. Nobody commented on the mask.

### C. Syntax and operators

**M15. Natural-language "and" versus mask `&`** READ
- URL: http://archive.ambermd.org/200712/0021.html (question quoted), 0023, http://archive.ambermd.org/200712/0037.html, 0047
- Date: 2007-12-04
- Problem: *"I want to restraint protein, ligand, and that part of the lipid membrane. Therefore, it should be '&', if the common meaning of 'or' applies."*
- Mask: `":POP, 77-521 & @%O2, P1, O3, ..."` [archive: `.%O2`]
- What was wrong: the user meant a union and wrote an intersection (`&`). `@%` selects atom *types*,
  not atom names. The user also believed there was an 80-character limit.
- Resolution: a list member: *"you used the 'and' character ('&') when you probably meant the 'or' character ('|'). You also specified selected atom types ('@%') when you probably meant selected atom names ('@')."*
  A second list member: *"it would match atoms that are in residues 77-521 and are also in the list of atoms in the POP residue types ... no atoms will match. You should use the ambmask program"*.

**M16. Operator precedence: `:GLY@CA | !:GLY@CB`** READ
- URL: http://archive.ambermd.org/201010/0206.html, 0208, http://archive.ambermd.org/201010/0226.html
- Date: 2010-10-07
- Problem: *"I am trying to do an rms between only C_betas for all residues except for GLY where I wish to choose C_alpha"*. The ptraj output looked wrong.
- Masks: `":GLY @CA | !:GLY @CB"` and `"(:ALA,ARG,...,VAL @CB) & (:GLY @CA)"` [archive: `.CA`, `.CB`]
- What was wrong: `!` binds tighter than the user expected, and `&` is intersection. ptraj's printed
  echo of the selection was also garbled.
- Resolution: a list member: *"':GLY.CA | !:GLY .CB' means ':GLY.CA| !(:GLY.CB)', which is just '!(:GLY.CB)'. That should be all atoms except ':GLY.CB' ... Your second atom mask should yield no atoms because the '&' means intersection."*
  AMBER/ParmEd developer (then a graduate student): *"Try this : ':GLY@CA | @CB' (note the lack of spaces). Since GLY doesn't have a CB, this should do what you want."* [archive: `.CA`/`.CB`]

**M17. `!` in the wrong place** READ
- URL: http://archive.ambermd.org/201808/0253.html (question quoted)
- Date: 2018-08-22
- Problem: *"is there any difference between having '!' after the residue # or not having '!'"*
- Mask: `restraintmask=':1-300*!*@CA,C,N,O | :301*!*@H= '` [archive: `.CA`, `.H=`]
- Resolution (AMBER lead developer): *"These look like illformed masks. The '!' ('not') character should come in front of a mask ... :301 & !@H= ... I'm not sure what you would get with your original mask, assuming it doesn't give a parsing error. You can use the ambmask program"*.

**M18. Residue list and atom list run together with a comma** READ
- URL: http://archive.ambermd.org/201803/0284.html, http://archive.ambermd.org/201803/0285.html, http://archive.ambermd.org/201803/0286.html
- Date: 2018-03-30
- Problem (RNA hbond): *"It is picking up atoms named O2', O4' etc. as they exist in the sugar ring ... when masking atoms, neither the . nor the "." Are recognized."*
- Mask: `:6-15,36-46,O2,O4,H3`. The user also tried `&!(?')` and `&!(O2')`.
- What was wrong: the atom names were appended to the residue list with a comma instead of `@`. The
  user had also tried a period as the atom operator.
- Resolution: AMBER lead developer: *"You have to separate the residue info from the atom name info."*
  cpptraj lead developer: *"you want: :6-15,36-46@O2,O4,H3 ... use the 'select' or 'atom' commands to test ... Note that a period is not a valid operator for Amber mask syntax."* [archive shows `.O2`]

**M19. Several invalid masks that "kind of" run** READ
- URL: http://archive.ambermd.org/201610/0126.html (question quoted)
- Date: 2016-10-09
- Problem: *"none of them is giving me correct number of residues used in alignment"*
- Masks: `@CA!:110-220`, `@CA&!:110-220`, `:14-109@CA,221-531@CA` [archive: `.CA`]
- Resolution (cpptraj lead developer): *"'@CA!:110-220' This mask is not valid and I think should kick back an error ... ':14-109@CA,221-531@CA' This is also an invalid mask and will probably give you weird behavior ... ':14-109,221-531@CA' This is the correct way"*.

**M20. Period typed for `@`, so 0 atoms selected (correction rendered meaningless by the archive)** READ
- URL: http://archive.ambermd.org/201501/0082.html, http://archive.ambermd.org/201501/0087.html
- Date: 2015-01-08
- Problem: *"Error: unknown symbol ==.== in residue name parsing. Mask [:1-185.CA] represents 0 atoms !!!NO ATOMS DETECTED!!!"*
- Mask: `:1-185.CA` (a real period). The same dimer job also used `rms ref [chain2] :186-366 :1-185`,
  because the reference PDB for chain 2 restarts its numbering at 1.
- Resolution (cpptraj lead developer), as the archive renders it: *"':1-185.CA' is not a valid atom mask. The '.' symbol denotes atoms, so the mask should be ':1-185.CA'."*
  The original must have read "The '@' symbol ... should be ':1-185@CA'". Also: *"I find it helpful after running cpptraj to grep for 'Error' and 'Warning' in my output."*

**M21. `:WAT.O` with a period; correction rendered as "'.' (at), not '.' (period)"** READ
- URL: http://archive.ambermd.org/201811/0131.html, 0132, http://archive.ambermd.org/201811/0147.html
- Date: 2018-11-13
- Problem: *"The selection I made was '(:1-294<:5.0)&:WAT.O'"*. In pytraj the user also wrote
  `pt.closest(x,mask="1-294",...)`, with no `:`.
- What was wrong: a period was used as the atom operator. The user also expected the distance mask to
  update every frame.
- Resolution (cpptraj lead developer), as rendered: *'the mask selection character for "atom" in Amber syntax is "." (at), not "." (period).'* Also: *"All actions (with the exception of 'mask') do not update distance-based masks on a per-frame basis; they use the active reference structure"*, and select molecules with `^1560,523,527`.

**M22. `&CA` used as an atom selector** READ
- URL: http://archive.ambermd.org/201602/0120.html, http://archive.ambermd.org/201602/0121.html
- Date: 2016-02-08
- Problem: *"Error in group input::atommask.f::selectElemMask elementary mask does not start with : or ."* [the original message probably reads `: or @`; my inference] and *"I don't manage to see my mistake"*.
- Mask: `restraintmask = ':170,185,&CA,C,N'`
- Resolution (AMBER/ParmEd developer): *"This is not a valid mask. I suspect you meant ':170,185@CA,C,N', or ':170,185&@CA,C,N' (note these two masks are exactly equivalent)."* The archive shows the first form with `.` and keeps `@` in the second.

**M23. Wildcards and "not": `~` and `@N*,C*,O*` rejected** READ
- URL: http://archive.ambermd.org/200605/0060.html (question quoted)
- Date: 2006-05-04
- Problem: *"restraintmask=':256~@H' I get an error that ~ is an invalid symbol ... restraintmask=':256@N*,C*,O*' I also get an error message that * is an invalid symbol."* [archive: `.H`, `.N*`]
- What was wrong: `~` is not an operator. The sander version of that era also rejected this use of `*`.
- Resolution (AMBER developer): *"try using the following syntax: restraintmask=':256 & !@H='"*.

### D. Distance masks: what they mean and when they are evaluated

**M24. `>:` is not the complement of `<:`** READ
- URL: http://archive.ambermd.org/201308/0130.html, 0133, http://archive.ambermd.org/201308/0146.html, 0158
- Date: 2013-08-07
- Problem: `(:1-27>:25.0)&:COP` selected all 54 counterions in every frame, while `(:1-27<:25.0)&:COP`
  selected 43 to 52. The user expected the two counts to add up to 54.
- What was wrong: `A>:d` means "residues with *any* atom farther than d from *any* atom of A". It is
  not "outside a sphere", and it is not based on the center of mass.
- Resolution (cpptraj lead developer): *"Select an entire residue if any part of it ... is farther than 25.0 Ang. away from any atom in residues 1-27, *not* the center of mass ... for every COP atom there is always an atom in residues 1-27 that is farther away than 25.0 Ang ... better to use the 'within' mask and then subtract."* For a center-of-mass version: *"no way to do this directly yet"*.

**M25. A distance restraint mask is fixed at the start of the run (and bellymask means the opposite)** READ
- URL: http://archive.ambermd.org/201310/0235.html, 0236, http://archive.ambermd.org/201310/0292.html, http://archive.ambermd.org/201310/0293.html
- Date: 2013-10-15
- Problem 1: *"the most economically way I can think to specify the moving atoms ... still far exceeds the 256 character limit"*
- Problem 2: `bellymask=(!@1962-1998,541-547,778-783 < :10.0)` *"allowed me to freeze all residues that are within 10 A of the QM region"* [archive: `.1962`]
- Problem 3: with `restraintmask=':* & (!@1962-1998,... < :10.0)'`, *"the atoms that are included in the restraint are still selected using the coordinate file that is read in at the beginning"*. That gave energy jumps in a QM/MM scan.
- Resolution (AMBER/ParmEd developer): *"bellymask selects atoms that can move, not atoms that are fixed. This will fix all residues within 10 angstroms of your atom selection and allow everything else to move ... belly selections and restraint selections are inverse compared to each other."* For long lists he pointed to GROUP input (`RES 2 10`).

**M26. The distance mask used `-c` coordinates, not the `-ref` coordinates** READ
- URL: http://archive.ambermd.org/201705/0274.html, reply http://archive.ambermd.org/201705/0280.html
- Date: 2017-05-19
- Problem: *"the number of atoms that matches the mask differs from one run to another, although the 'refc' file remains the same ... the mask is systematically based on the input coordinates and not on the reference ones."*
- Mask: `:150@OG<:20` [archive: `.OG`]
- Resolution (AMBER lead developer): *"The piece of the manual you cite was written (long) before we implemented anything like distance-based masks. But it looks like the correct thing to do is to update the code in the manner you suggest"*.

**M27. cpptraj: distance masks are evaluated once, on the reference** READ
- URL: http://archive.ambermd.org/201608/0271.html (question quoted)
- Date: 2016-08-12
- Problem: `mask (:1-1158<:6.0)&:WAT`, then `vector ... (:1-1158<:6.0)&:WAT`. The user asked:
  *"does the Cpptraj update the molecules for each frame?"*
- Resolution (cpptraj lead developer): *"'Distance-based masks that update each frame are currently only supported by the mask action.' Also, the 'mask' command doesn't affect subsequent commands."* He suggested `watershell` plus `closest`.

**M28. A distance mask with no reference set: error, then silent partial selection** READ
- URL: http://archive.ambermd.org/202207/0011.html, http://archive.ambermd.org/202207/0012.html
- Date: 2022-07-15
- Problem: *"Error: Mask stack is not empty ... If I switch the order of the selection, it runs, just omitting all the atoms (there are 17 in total) after the first |"*
- Mask: `:529@ND1|:191@NZ|:528@CD|:97@NE2,OE1|:134<:12&@CA&:1-197` [archive: `.ND1` and so on]
- Resolution (self-resolved, no developer reply): *"in the clustering I didn't add a reference, therefore the distance based mask wasn't working properly. Adding a reference frame fixed it."*

**M29. cpptraj distance mask: "No reference set"** READ
- URL: http://archive.ambermd.org/201509/0346.html (question quoted), 0395, 0398, http://archive.ambermd.org/201509/0399.html
- Date: 2015-09-22
- Problem: *"Error: No reference set for [pro_com.prmtop], cannot select by distance"*, although a
  `reference` line was present.
- Mask: `rmsd rms_test :250<:10&@CA,N,C reference` [archive: `.CA`]
- Resolution (cpptraj lead developer): *"it is a strange bug"*. The workaround was to load a named
  reference `[R1]` after a dummy run, then use `ref [R1]`.

**M30. A distance restraint mask matched 0 atoms, but the run continued** READ
- URL: http://archive.ambermd.org/200502/0261.html, http://archive.ambermd.org/200502/0277.html
- Date: 2005-02-17
- Problem: *"the restrained atoms are not recognized, but the simulation continues with no other errors"*. The output showed *"Mask :* & !:2855<:20.0; matches 0 atoms"*.
- Mask: `restraintmask = ':* & !:2855<:20.0 & !:WAT'`
- Resolution (AMBER developer): *"There was a bug in selections using distance criteria ... The best way to check if the selection works ... is to use utility 'ambmask'"*. The user: *"bugfix.7 fixed my problem."*

### E. Input-file plumbing: quoting, namelists, length

**M31. Unquoted mask: namelist error, and the restraint energy is 0** READ
- URL: http://archive.ambermd.org/201210/0627.html (question quoted), 0638, http://archive.ambermd.org/201210/0643.html
- Date: 2012-10-29
- Problem: *"Cannot match namelist object name .* namelist not terminated with / or &end ... the restraints energy is 0.0000 and no atoms are selected for restraints ... The sytax I used for atom selection is exactly as shown in Amber12 manual"*
- Mask: `restraintmask=:* & !@H=` (no quotes) [archive: `!.H=`]
- Resolution (cpptraj lead developer): *"Try enclosing the string in single quotes, and don't put any spaces ... restraintmask='!@H='"*. The user then got *"Mask !@H=; matches 2189 atoms"*.

**M32. Unquoted distance mask crashes; quoted, it matched 0 atoms in sander but worked in ambmask** READ
- URL: http://archive.ambermd.org/200404/0270.html, http://archive.ambermd.org/200404/0280.html
- Date: 2004-04-21
- Problem: `restraintmask = :534 >:5.0,` gave *"too many values for NAMELIST variable"*. The quoted
  form ran, but *"Mask :534 >:5.0; matches 0 atoms ... With ambmask the selection string ':534 >:5.0' works."*
- Resolution (AMBER developer): *"You have to enclose the expression into quotes ... sander uses the same parsing module (the same code) as ambmask does"*. He asked for the files. There is no public
  resolution.

**M33. Shell quoting for ambmask** READ
- URL: http://archive.ambermd.org/201903/0153.html, http://archive.ambermd.org/201903/0155.html
- Date: 2019-03-15
- Problem: *"-bash: syntax error near unexpected token `('"* and *"it seems that AMBER can not handle it in the input script"*.
- Mask: `:1,2 | :3-6@%ob,cb`, passed to `ambmask ... -find (:1,2 | :3-6@%ob,cb)` without quotes
- Resolution (AMBER lead developer): *"You need to put single quotes around the mask to prevent the shell from interpreting pieces of it as special characters ... parentheses here, which actually don't do anything ... you should have quotes around the mask also even in other programs. If you still have problems, try removing all the spaces"*.

**M34. "The 80-character limit" is only the echo; the real limit is 256** READ
- URL: http://archive.ambermd.org/200903/0140.html, http://archive.ambermd.org/200903/0141.html, 0143
- Date: 2009-03-09
- Problem: *"Is there a way to work around the 'restraint mask length being limited to 80 characters' limitation?"*
- Mask: `RESTRAINTMASK="(:2-150) & ! (:PHE@CE=,CD= | ... | :ASN@ND2,OD1 :GLN@NE2,OE1 | ... | @H= | :150@O)"`. **My observation:** there is no `|` between `:ASN@ND2,OD1` and `:GLN@NE2,OE1`. The thread
  never mentions it, and the user then reported that sander *"stalls after 5. Reference Atom Coordinates."*
- Resolution (AMBER lead developer): *"The restraintmask limit is currently 256 characters in the code ... The code snippet that copies the input file to the output only prints the first 80 characters (we should change this.) But the full line should still be available to the program."*

**M35. A mask over 1,000 characters** READ
- URL: http://archive.ambermd.org/201501/0325.html (question quoted; thread includes 201501/0312)
- Date: 2015-01-22
- Problem: *"for some proteins these mask become very large ... I do not see any chance to get that down to 256 characters"*. The quoted mask is a long residue list ending `...&!@H=,OXT|...&@C,CA,N,O`.
- Resolution (AMBER/ParmEd developer): use the old GROUP input (`FIND ... SEARCH`) cards. *"Note you can do all of this logic just as simply with restraintmask, but you can't assign multiple force constants."*

**M36. `noshakemask` split across two lines** READ
- URL: http://archive.ambermd.org/200612/0033.html, 0038, http://archive.ambermd.org/200612/0045.html, 0053
- Date: 2006-12-03
- Problem: *"Error in group input::atommask.f::tokenize illegal symbol in maskstr"*. On one line, the
  user reports *"its being truncated by sander"*.
- Resolution (AMBER lead developer): *"The string probably needs to all be on one line"* and *"The 'noshakemask' array has a length of 256. It may be that the namelist implementation does not allow such a long string."*

### F. A correct mask that has no effect: missing flags and wrong semantics

**M37. `restraintmask` without `ntr=1`** READ
- URL: http://archive.ambermd.org/202211/0168.html, 0169, 0172, http://archive.ambermd.org/202211/0173.html
- Date: 2022-11-24
- Problem: *"restraint_wt=50.0, restraintmask=':lig' and it does not work at all! ... ibelly = 0, ntr = 0 ... in the MD, it still moves"*
- Mask: `restraintmask='(@CA,CA,N,O & !:WAT)'`, then `':lig'` [archive: `.CA`]. Note that `CA` is
  listed twice.
- Resolution (self): *"the problem was due to the missing ntr=1 in the input file"*. A list member had
  suggested atom number 9281, taken from the PDB. **My note (unverified):** PDB serial numbers need not
  equal prmtop atom indices.

**M38. `restraintmask` without `ntr=1`, then `ntr=1` without `-ref`** READ
- URL: http://archive.ambermd.org/201611/0214.html (question quoted)
- Date: 2016-11-15
- Problem: *"I'm trying to restrain the bases number 1, 10, 11 and 20, but I see in vmd that they are still moving ... I tried to add the line ntr=1 but that gives me an error 'Error opening unit 10: File "refc" is missing or unreadabl'"*
- Mask: `restraintmask=':1,10,11,20'` with `restraint_wt=500.0`
- Resolution (a list member): *"the flag ntr=1 is necessary ... Without the flag, the simulation goes unrestrained ... If you do not give any file name on the command line via the '-ref <name>' input, sander tries to read ... 'refc'"*. Also: *"The weight of your restraints is very large ... (<= 10)."*

**M39. pysander's bellymask picks different atoms from sander's** READ (user report only)
- URL: http://archive.ambermd.org/202302/0130.html, http://archive.ambermd.org/202302/0135.html
- Date: 2023-02-24
- Mask: `bellymask=":CU<:15&!:CU"`
- Problem: *"if ibelly is turned on, the belly mask gives different matched atoms than that of sander program and thus produce different energies. Looks like there are still other bugs for ibelly."* No developer replied.

### G. Free-energy (TI) masks

**M40. `timask2` left empty** READ
- URL: http://archive.ambermd.org/201910/0130.html (question quoted), 0135
- Date: 2019-10-10
- Problem: *"TI Mask 2 matches 0 atoms ... ERROR: timask1/2 must match the same number of atoms for non-softcore"*
- Mask: `timask1 = ':BG6', timask2 = '', ifsc = 0, crgmask = ':BG6'`
- Resolution (experienced TI user from industry): *"you'd want 2 copies of your ligand ... Timask1=':BG6', timask2=':BG7' ... crgmask=':BG7'"*.

**M41. tiMerge on a two-chain protein generated the wrong `timask2`/`scmask2`** READ
- URL: http://archive.ambermd.org/201604/0034.html, http://archive.ambermd.org/201604/0035.html, 0039
- Date: 2016-04-03
- Problem: *"I found the timask2 and scmask2 are wrong atoms ... the mutated residue was attached at the end of the first chain of protein, and the correct atom number should be 1568-1586. So in the following TI run, I got the error message 'Error : Atom 497 does not have match in V1 !'"*. A second attempt gave *"mol1mask and mol2mask must be adjacent in topology."*
- Mask: `tiMerge :1-198 :199-396 :32 :230`, then `:1-99 :199-297 :32 :230`
- Resolution (free-energy tools developer): *"include only the chain with the mutation in the mask"* and *"write the first chain into the topology file such that the second copy immediately follows the first one ... adjust the mask such that they correspond to the new arrangement."*

**M42. tiMerge regions misunderstood** READ
- URL: http://archive.ambermd.org/201412/0292.html (user message quoted)
- Date: 2014-12-17
- Problem: the user believed that *"'1-520,1037-20160'(timask1) minus '116,...'(scmask1) have to equal to '521-1036,20161-39284'(timask2) minus ..."*
- Resolution (free-energy tools developer): *"I think you misunderstand how this is supposed to work. You have up to three regions to define ... You will have to define every vanishing/appearing atom as a softcore atom ... There needs to be a one-to-one correspondence of this subregion and you must make this sure by ordering the atoms accordingly in prmtop."*

**M43. Trimer TI: residue numbers move after tiMerge** READ (the mask was not the final cause)
- URL: http://archive.ambermd.org/202307/0122.html, 0127, 0132, http://archive.ambermd.org/202307/0140.html
- Date: 2023-07-24
- Problem: *"tiMerge :1-3377 :3378-6754 :362 :3739. Parmed moves the mutated res in the merged files right after the 1st chain, so in the relaxation inputs I have to point to 1126 instead"*. The masks were `timask1 = ':362', timask2 = ':1126'`.
- Resolution: a York-group AMBER free-energy developer first suspected an off-by-one in the molecule
  masks: *"had the third ligand :3378 included ... It seemed to me that you intended to do tiMerge :1-3378 :3379-6756 :362 :3740"*. The user explained the masks were deliberate. A second free-energy
  developer then found structural problems (overlapping hydrogens, close contacts).

### H. MMPBSA.py masks

**M44. Receptor and ligand masks must partition the complex; ligand must be contiguous** READ
- URL: http://archive.ambermd.org/201609/0428.html, http://archive.ambermd.org/201609/0431.html, http://archive.ambermd.org/201610/0005.html
- Date: 2016-09-28
- Problem: *"PrmtopError: Couldn't predict mask from topology files! Your ligand residues must be sequential in your complex."* The system was a glycosylated receptor, ordered receptor, ligand,
  glycans.
- Mask: only `receptor_mask=:1-614,662-669` was given.
- Resolution (MMPBSA.py developer): *"Try specifying both receptor_mask=':1-614,662-669' and ligand_mask=':615-661'"*.

**M45. Using masks to "exclude" floppy residues** READ
- URL: http://archive.ambermd.org/201908/0153.html, 0254, http://archive.ambermd.org/201908/0256.html, 0258
- Date: 2019-08-17
- Problem: *"PrmtopError: provided receptor/ligand masks don't select every atom in the complex topology!"*
- Mask: `receptor_mask=':1-39,52-207', ligand_mask=':208'` (meant to drop residues 40-51)
- Resolution (a list member, hedged): *"when creating the complex topology by striping residues from the solvated complex, the residues are probably going to be renumbered ... ligand residue number now becomes 208-12 = 196. Do please verify this, since I am speculating."* The user then hit an ante-MMPBSA.py error with `-s :40-51 -n "!(:208)"`.

**M46. Masks that disagree with the receptor prmtop** READ
- URL: http://archive.ambermd.org/202311/0044.html (question quoted)
- Date: 2023-11-08
- Problem: *"PrmtopError: mismatch in receptor mask and receptor prmtop"*
- Mask: `receptor_mask=":1-381,406,408-1547", ligand_mask=":382-405,407"`. This system has three chains
  with interleaved residues.
- Resolution (MMPBSA.py developer): *"You will need to run ante-MMPBSA.py to create the prmtop files that correspond to your new definitions of receptor and ligand."*

**M47. MMPBSA.py's input parser splits masks at commas** READ
- URL: http://archive.ambermd.org/201002/0176.html, http://archive.ambermd.org/201002/0178.html, 0180
- Date: 2010-02-12
- Problem: with `receptor_mask=':1-468:509-510'`, ptraj logged *"STRIP: 7535 atoms will be removed from trajectory: :1-468"*, which silently dropped the second range. With commas the result was *'Warning: Input error! "509-510" is not recognized. Initialize variables with "="'*.
- Resolution (MMPBSA.py developer): *"an issue with the input parser for MMPBSA.py. The parser is designed such that a comma indicates the end of one variable and the start of the next variable. However, within AMBER, commas are used between noncontinuous residues in a mask."* Workaround: edit
  the generated ptraj inputs. The user reported that this did not help either.

**M48. Decomposition groups read 0 atoms** READ (unresolved in the archive)
- URL: http://archive.ambermd.org/202501/0097.html, 0099, http://archive.ambermd.org/202501/0100.html
- Date: 2025-01-18
- Mask: `strip_mask=":WAT,Na+", receptor_mask=":1-627", ligand_mask=":628"` with `idecomp=1` (a dimer
  plus ligand)
- Problem: sander PB failed on the complex.
- Resolution (PB solver developer): *"there is something wrong in the input of the groups as no atoms were read in for your first and second groups ... Number of atoms in this group = 0"*. The cause was
  not found in-thread.

### Read but weak or not a mask error (kept for completeness)

- http://archive.ambermd.org/201507/0362.html and 0364, 2015-07-24. The mask
  `'(:65,66,...,294-298) & !@H='` looked correct to an AMBER/ParmEd developer: *"This looks ok. Why do you say that the selection is wrong? You can use ambmask"*. Unresolved.
- http://archive.ambermd.org/200812/0209.html, 0210, 0211, 0217, 2008-12-16. The user first posted
  *"Mask :2276-2299; matches 0 atoms"*, then *"I sent the information from the wrong output file ... matches 24 atoms"*. The real problem was using `ntr=1` restraints to pull a structure toward a
  target. AMBER developer: *"you definitely don't want to use ntr=1 with this."*
- http://archive.ambermd.org/201610/0345.html, 2016-10-21. A trajectory stripped of `:WAT`, `:Na+`
  and `:Cl-` was then read with the unstripped topology. This is a topology mismatch, not a mask
  error.

## LEADs (search snippet only, not fetched)

- http://archive.ambermd.org/199907/0009.html: "residue (re)numbering in leap" (1999)
- http://archive.ambermd.org/201905/0151.html and 0147, 0195: "tleap split lipid when it shouldn't". POPC's
  PA/PC/OL are split by TER records. Only 0147 (the user's steps) was read.
- http://archive.ambermd.org/202001/0172.html: "Harmless bug in Lipid11-17 residue libraries causing tleap to split fragments in saved PDB"
- http://archive.ambermd.org/202003/0240.html: "Ambmask Error in group input::atommask.f::pop_evalstack stack underflow"
- http://archive.ambermd.org/201106/0196.html: "Detection of residues within a sphere"
- http://archive.ambermd.org/202108/0173.html: "Need help with MMPBSA-per residue decomp"
- http://archive.ambermd.org/201806/0201.html (read): the old Perl MM-PBSA hard-codes `MG*` in its strip
  list, so Mg2+ was stripped silently. Not written up as a full entry.

## Searched but not found

I found no archive thread specifically about: HIS vs HID/HIE/HIP in a *mask* (only parameter and
protonation threads), nucleic-acid terminal names (DA5/DA3, A5/A3) in masks, N- or C-terminal residue
names in masks, insertion codes in masks, `@H*` vs `@H=` as a source of error, element selection
(`@/H`), or VMD/MDAnalysis selection syntax pasted into AMBER. The HIS case may exist under other
wording. I did not exhaust the archive.

---

## Summary table: problem categories

Each thread is counted once, under its main category. Many have secondary tags.

| Category | Threads | Count |
|---|---|---|
| A. Residue numbering and chains (PDB vs sequential index, no chain selector, pdb4amber/tleap renumbering, solvent reordering, renumbering after strip/tiMerge, PDB overflow, mask applied to the wrong topology) | M01-M08 | 8 |
| B. Names (CHARMM vs AMBER residue/ion/water names, MMPBSA default strip list, lipid split residues, EPW extra points, atom selector used for a residue name) | M09-M14 | 6 |
| C. Syntax and operators (`&` vs `|`, precedence, `!` placement, residue/atom separator, `.` typed for `@`, invalid symbols `~ *`, `@%` type vs name) | M15-M23 | 9 |
| D. Distance masks (meaning of `>:`/`<:`, evaluated once against which coordinates, reference required, bugs that give 0 atoms) | M24-M30 | 7 |
| E. Input plumbing (quotes, namelist errors, line breaks, the 256-character limit, the 80-character echo, shell quoting) | M31-M36 | 6 |
| F. Correct mask with no effect or reversed effect (missing `ntr=1` or `-ref`; bellymask selects *moving* atoms; tool-to-tool differences) | M37-M39 (plus M25's belly part) | 3 |
| G. TI masks (empty `timask2`, tiMerge on multi-chain proteins, misunderstood softcore/common regions, renumbering after merge) | M40-M43 | 4 |
| H. MMPBSA.py masks (masks must partition the complex, ligand must be contiguous, masks must match the prmtops, comma parsing, decomposition groups) | M44-M48 | 5 |
| **Total READ threads with a mask problem** | | **48** |

Cross-cutting tags:
- **Silent failures, where nothing stopped the run:** M05, M06, M14, M24, M25, M28, M30, M31 (the
  namelist error printed but the run continued with 0 restraint energy), M37, M38, M39, M47. That is
  at least 12 threads.
- **Damaged by the archive's `@` to `.` rewrite:** M20 and M21 are made unreadable. Nearly every
  pre-2023 entry is affected cosmetically.
- **Developers' standard advice:** check the "Mask ... matches N atoms" line in mdout, test with
  `ambmask` or cpptraj `--mask`/`select`, and quote the mask. This appears in M01, M09, M15, M17, M18,
  M30, M31, M33 and others.

## The 10 most instructive examples

1. **M21 (201811/0147).** A user typed `:WAT.O`. The developer's correction now reads "'.' (at), not
   '.' (period)". Both the mistake and the archive's corruption of the fix are on one page. The same
   reply says distance masks are not updated per frame.
2. **M20 (201501/0087).** The period typed for `@` leads to *"0 atoms !!!NO ATOMS DETECTED!!!"*. The
   archive prints the "wrong" and "correct" masks identically.
3. **M24 (201308/0146).** `>:25` is not the complement of `<:25`. Distance masks use "any atom to any
   atom", not a sphere or a center of mass, and the developer shows why every ion ends up selected.
4. **M25 (201310/0293).** `bellymask` selects atoms that *move*, the inverse of `restraintmask`. The
   user froze exactly the region he meant to free. The same thread shows a distance mask fixed at
   step 0 causing energy jumps.
5. **M26 (201705/0280).** A distance mask was evaluated on the `-c` input coordinates, not the `-ref`
   file, so the restrained set changed from run to run. The lead developer agreed the code should
   change.
6. **M31 (201210/0627).** An unquoted mask produced a namelist error, yet the run continued with
   *"RESTRAINT = 0.0000"*. The user had copied the syntax "exactly as shown in Amber12 manual".
7. **M16 (201010/0226).** Precedence: `:GLY@CA | !:GLY@CB` means "everything except GLY CB", and `&`
   between disjoint sets selects nothing.
8. **M15 (200712/0037).** "Protein, ligand *and* lipid heads" was written with `&`, so nothing
   matched. Natural-language "and" means union, and `@%` (type) was confused with `@` (name).
9. **M05 (201808/0231).** The same mask string selected different atoms after `parmstrip`, because the
   remaining residues are renumbered from 1.
10. **M02 (202106/0037 and 0042).** The lead developer explains AMBER's "residue index", which ignores
    chain IDs and insertion codes. The cpptraj developer notes that only cpptraj has `:;` (PDB
    number) and `::` (chain) selectors. This is the root of M01, M06, M41, M43 and M45.

Honorable mentions: M47 (the MMPBSA.py parser splits masks at commas, silently dropping a residue
range), M14 (`@WAT` instead of `:WAT`, uncaught on the list; my reading), and M41 (tiMerge on a
two-chain protein produced wrong `timask2`).
