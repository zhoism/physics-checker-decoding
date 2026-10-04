"""The mask bench: plain-English requests on the built systems (build.sh), each with a reference mask.
The gold is the atom set ambmask selects with the reference; any mask that selects exactly those
atoms is right. Run in the prime-amber env (ambmask); writes tasks.jsonl.
    python masks/bench/tasks.py
Every reference was checked against the system's view (views/<id>.txt, what the model is shown):
PDB numbers map to topology numbers through the residue listings there."""
import hashlib
import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
AMBER = Path(os.environ.get("AMBERHOME", "/opt/homebrew/Caskroom/miniforge/base/envs/prime-amber"))
CATEGORIES = {
    "dialect": "a selection whose natural wording pulls toward VMD, MDAnalysis, PyMOL or cpptraj syntax",
    "operators": "precedence of ! & |, parentheses, and lists that mix numbers and names",
    "numbering": "PDB residue numbers (offsets, gaps, insertion codes) mapped to topology numbers",
    "chain": "a chain or strand, which a prmtop has no selector for",
    "atom-names": "AMBER atom names: OXT, H1-H3, HA2/HA3, CD1, and the CA atom vs the CA residue",
    "protonation": "residue names that encode protonation or bonding: HID HIE HIP ASH GLH LYN CYX",
    "termini": "N- and C-terminal residues and 5'/3' nucleotides",
    "ion": "ion residue names (Na+ vs NA, Cl- vs CL, K+, the CA calcium)",
    "water": "water residue and atom names, extra points, crystal waters",
    "nucleic": "nucleic-acid residue and atom names (DG3, OP1, primes)",
    "lipid": "Lipid21 lipids, split into head and tail residues",
    "distance": "distance selections (<: <@) and what they include",
    "type": "AMBER atom types (@%)",
    "context": "a mask for a named program or variable: restraintmask, scmask, MMPBSA, a cpptraj mask to translate",
}

# id, category, difficulty (1 one step; 2 one trap or one mapping; 3 several), request, reference mask
TASKS = {
    "bnbs": [
        ("barnase-all", "chain", 1, "every atom of barnase (chain A of 1BRS)", ":1-108"),
        ("barstar-ca", "chain", 1, "the alpha carbons of barstar (chain D of 1BRS)", ":109-195@CA"),
        ("barstar-heavy", "chain", 2, "the heavy (non-hydrogen) atoms of barstar", ":109-195&!@H="),
        ("backbone", "dialect", 1, "the backbone atoms N, CA, C and O of both proteins", ":1-195@N,CA,C,O"),
        ("his102", "numbering", 2, "barnase His102 (PDB numbering), all atoms", ":100"),
        ("glu73-oe", "numbering", 2, "the two carboxylate oxygens of barnase Glu73 (PDB numbering)", ":71@OE1,OE2"),
        ("arg83-87", "numbering", 2, "the guanidinium nitrogens NE, NH1 and NH2 of barnase Arg83 and Arg87 "
         "(PDB numbering)", ":81,85@NE,NH1,NH2"),
        ("d35-d39", "numbering", 2, "the side-chain carboxyl oxygens OD1 and OD2 of barstar Asp35 and Asp39 "
         "(chain D, PDB numbering)", ":143,147@OD1,OD2"),
        ("barstar-66-89", "numbering", 3, "barstar residues 66 through 89 in PDB numbering", ":172-195"),
        ("barstar-60-70", "numbering", 3, "barstar residues 60 to 70 as numbered in the PDB entry", ":168-176"),
        ("barstar-trp", "numbering", 2, "barstar Trp38 and Trp44 (PDB numbering), all atoms", ":146,152"),
        ("barnase-56-60-ca", "numbering", 2, "the alpha carbons of barnase residues 56 to 60 in PDB numbering",
         ":54-58@CA"),
        ("his-all", "protonation", 2, "all histidine residues, in whatever protonation state", ":HID,HIE,HIP"),
        ("hip", "protonation", 1, "the doubly protonated (positively charged) histidine", ":HIP"),
        ("neutral-acids", "protonation", 2, "the aspartate and glutamate residues that were set up protonated "
         "(neutral)", ":ASH,GLH"),
        ("acidic-all", "protonation", 2, "all aspartate and glutamate residues, charged or protonated",
         ":ASP,GLU,ASH,GLH"),
        ("lys-nz", "protonation", 2, "the side-chain nitrogen NZ of every lysine, including the neutral one",
         ":LYS,LYN@NZ"),
        ("sodium", "ion", 1, "all sodium ions", ":Na+"),
        ("ions", "ion", 1, "all the ions, of both kinds", ":Na+,Cl-"),
        ("not-solvent", "ion", 1, "everything except the water and the ions", "!:WAT,Na+,Cl-"),
        ("nterm-h", "termini", 3, "the hydrogens on every N-terminal amino group of the protein", "@H1,H2,H3&!:WAT"),
        ("oxt", "termini", 1, "every C-terminal OXT oxygen", "@OXT"),
        ("cterm-res", "termini", 2, "the C-terminal residue of every protein segment in the topology, all atoms",
         ":108,171,195"),
        ("amide-h", "atom-names", 2, "the backbone amide hydrogen of every barnase residue that has one",
         ":1-108@H"),
        ("trp-ring", "atom-names", 2, "the ring carbons of barstar's tryptophans (both rings of the indole)",
         ":146,152,161@CG,CD1,CD2,CE2,CE3,CZ2,CZ3,CH2"),
        ("near-his102", "distance", 3, "the protein residues (in either protein) with any atom within 5 Angstrom of "
         "barnase His102 (PDB numbering), not counting His102 itself", "(:100<:5.0)&:1-195&!:100"),
        ("interface-water", "distance", 2, "the water molecules, whole, with any atom within 3 Angstrom of barstar",
         "(:109-195<:3.0)&:WAT"),
        ("barstar-interface", "distance", 3, "the barstar residues with any atom within 4 Angstrom of barnase",
         "(:1-108<:4.0)&:109-195"),
        ("ions-near-protein", "distance", 2, "the ions within 6 Angstrom of any protein atom",
         "(:1-195<:6.0)&:Na+,Cl-"),
        ("sidechains-or-50", "operators", 3, "heavy atoms only: the side chains of topology residues 40 to 45 "
         "(everything but N, CA, C and O), together with the whole of topology residue 50",
         "(:40-45&!@N,CA,C,O|:50)&!@H="),
        ("res1-and-trp", "operators", 2, "topology residue 1 together with every tryptophan residue", ":1|:TRP"),
        ("h-1-10-20-30", "operators", 1, "the hydrogens of topology residues 1 to 10 and 20 to 30",
         ":1-10,20-30&@H="),
        ("restraint-adapt", "context", 2, "the atoms a restraintmask should hold to do in this system what a "
         "tutorial's '!@H= & !:NA,CL,MG,WAT' does in its own: the solute heavy atoms, and no water or ion",
         ":1-195&!@H="),
        ("bellymask", "context", 2, "the bellymask for a run in which barstar moves and every other atom is frozen",
         ":109-195"),
        ("scmask-h102a", "context", 3, "the softcore region (scmask1) for a TI mutation of barnase His102 (PDB "
         "numbering) to alanine: the histidine side-chain atoms beyond CB, hydrogens included",
         ":100@CG,ND1,CE1,NE2,CD2,HD1,HE1,HE2,HD2"),
        ("cpptraj-h", "context", 2, "the atoms of the cpptraj mask ':1-108&@/H', in a mask pmemd accepts", ":1-108&@H="),
        ("vmd-ca", "dialect", 1, "the atoms of the VMD selection 'protein and name CA and resid 10 to 20', where resid is the "
         "topology residue number", ":10-20@CA"),
        ("mda-around", "dialect", 3, "the atoms of the MDAnalysis selection 'resname WAT and around 3.5 protein': the water "
         "atoms (not whole molecules) within 3.5 Angstrom of any protein atom", "(:1-195<@3.5)&:WAT"),
        ("ct-barnase", "type", 2, "the barnase atoms of AMBER atom type CT", ":1-108&@%CT"),
        ("water-h", "water", 1, "the hydrogen atoms of every water molecule", ":WAT@H1,H2"),
        ("hg-wildcard", "dialect", 1, "every barnase hydrogen whose name begins with HG", ":1-108@HG="),
    ],
    "tryp": [
        ("ser195", "numbering", 2, "the catalytic serine Ser195 (chymotrypsin numbering, as in the PDB file)", ":177"),
        ("triad-heavy", "numbering", 2, "the heavy atoms of the catalytic triad His57, Asp102 and Ser195 "
         "(PDB numbering)", ":40,84,177&!@H="),
        ("ser195-og", "numbering", 2, "the side-chain oxygen OG of Ser195 (PDB numbering)", ":177@OG"),
        ("oxyanion", "numbering", 2, "the backbone nitrogens of Gly193 and Ser195 (the oxyanion hole), PDB numbering",
         ":175,177@N"),
        ("asp189", "numbering", 2, "Asp189 at the bottom of the S1 pocket (PDB numbering), all atoms", ":171"),
        ("ins-184a", "numbering", 3, "PDB residue 184A, the glycine with insertion code A", ":164"),
        ("ins-188", "numbering", 3, "PDB residues 188A and 188, both of them", ":169,170"),
        ("pdb-30-40", "numbering", 3, "PDB residues 30 to 40", ":15-23"),
        ("pdb-214-221", "numbering", 3, "PDB residues 214 through 221, including 221A", ":192-199"),
        ("s1-heavy", "numbering", 3, "the heavy atoms of PDB residues 189 to 195 and 214 to 220",
         ":171-177,192-197&!@H="),
        ("cys22-157", "numbering", 2, "the two sulfur atoms of the disulfide between Cys22 and Cys157 "
         "(PDB numbering)", ":7,137@SG"),
        ("nterm-ile16", "termini", 2, "the N-terminal nitrogen of Ile16 (PDB numbering) and the three hydrogens "
         "on it", ":1@N,H1,H2,H3"),
        ("cterm-o", "termini", 2, "the two C-terminal carboxylate oxygens of the protein's last residue",
         ":223@O,OXT"),
        ("calcium", "ion", 2, "the calcium ion", ":CA"),
        ("alpha-carbons", "atom-names", 3, "all protein alpha carbons and nothing else", ":1-223@CA"),
        ("chloride", "ion", 1, "all chloride ions", ":CL"),
        ("monovalent", "ion", 2, "the sodium and chloride ions, but not the calcium", ":NA,CL"),
        ("all-ions", "ion", 2, "every ion in the system", ":CA,NA,CL"),
        ("ca-shell", "distance", 2, "the atoms within 3 Angstrom of the calcium ion, not counting the ion itself",
         "(:CA<@3.0)&!:CA"),
        ("ca-residues", "distance", 2, "the protein residues with any atom within 3 Angstrom of the calcium ion",
         "(:CA<:3.0)&:1-223"),
        ("og-8a", "distance", 3, "the heavy atoms of the protein residues with any atom within 8 Angstrom of the "
         "Ser195 OG atom (PDB numbering)", "(:177@OG<:8.0)&:1-223&!@H="),
        ("crystal-waters", "water", 3, "the 62 crystallographic water molecules that came from the PDB file",
         ":257-318"),
        ("cyx-sg", "protonation", 1, "the sulfur atoms of the cysteines that form disulfide bonds", ":CYX@SG"),
        ("his-all", "protonation", 2, "all histidine residues", ":HIE"),
        ("sulfur-all", "atom-names", 2, "every sulfur atom in the system", "@SG,SD"),
        ("type-ca", "type", 2, "all atoms of AMBER atom type CA (aromatic carbons), not the alpha carbons", "@%CA"),
        ("type-ow", "type", 1, "the water oxygens, selected by atom type", "@%OW"),
        ("restraint-solute", "context", 2, "the atoms a restraintmask should hold: the heavy atoms of the protein and "
         "the calcium ion, leaving water, Na+ and Cl- free", ":1-224&!@H="),
        ("res1-and-pro", "operators", 2, "topology residue 1 together with all proline residues", ":1|:PRO"),
        ("ca-1-50-or-ion", "operators", 2, "the alpha carbons of topology residues 1 to 50, plus the calcium ion",
         ":1-50@CA|:CA"),
        ("gly-ha", "atom-names", 2, "the alpha hydrogens of every glycine", ":GLY@HA2,HA3"),
        ("ile-cd", "atom-names", 1, "the delta carbon of every isoleucine side chain", ":ILE@CD1"),
        ("carbons", "atom-names", 3, "every carbon atom in the system", "@C=&!:CA,CL"),
        ("pymol-resi", "dialect", 2, "the atoms of the PyMOL selection 'resi 57+102+195 and name CA', where the numbers are the "
         "PDB residue numbers", ":40,84,177@CA"),
    ],
    "dna": [
        ("strand-b", "chain", 1, "the second strand (chain B in 1BNA)", ":13-24"),
        ("strand-a-p", "nucleic", 2, "the phosphorus atoms of strand A", ":1-12@P"),
        ("guanines", "nucleic", 2, "all guanine nucleotides", ":DG,DG3"),
        ("cytosines", "nucleic", 2, "all cytosine nucleotides", ":DC,DC5"),
        ("five-prime", "termini", 1, "the 5'-terminal nucleotide of each strand", ":1,13"),
        ("ho3", "termini", 2, "the hydrogens of the terminal 3'-hydroxyl groups", "@HO3'"),
        ("bp-a5-t20", "nucleic", 2, "the Watson-Crick hydrogen-bonding atoms of the A5:T20 base pair: N1 and N6 of "
         "A5, N3 and O4 of T20", ":5@N1,N6|:20@N3,O4"),
        ("sugar-a", "nucleic", 2, "the five sugar-ring atoms (C1', C2', C3', C4', O4') of strand A",
         ":1-12@C1',C2',C3',C4',O4'"),
        ("nonbridging", "nucleic", 2, "the non-bridging phosphate oxygens of both strands", "@OP1,OP2"),
        ("thy-methyl", "nucleic", 2, "the thymine methyl carbons", ":DT@C7"),
        ("extra-points", "water", 2, "the massless extra points (virtual sites) of the water model", "@EPW"),
        ("water-o", "water", 1, "the water oxygens", ":WAT@O"),
        ("potassium", "ion", 1, "all potassium ions", ":K+"),
        ("k-near", "distance", 2, "the potassium ions within 6 Angstrom of any DNA atom", "(:1-24<:6.0)&:K+"),
        ("water-o-near", "distance", 3, "the water oxygen atoms that are themselves within 3.5 Angstrom of a DNA atom",
         "(:1-24<@3.5)&:WAT@O"),
        ("heavy-a", "dialect", 1, "the heavy atoms of strand A", ":1-12&!@H="),
        ("dna-h", "dialect", 1, "all hydrogen atoms of the DNA", ":1-24&@H="),
        ("backbone-b", "nucleic", 2, "the backbone atoms P, OP1, OP2, O5', C5', C4', C3' and O3' of strand B",
         ":13-24@P,OP1,OP2,O5',C5',C4',C3',O3'"),
        ("aatt-a", "nucleic", 1, "nucleotides 5 to 8 of strand A (the central AATT)", ":5-8"),
        ("central-6bp", "nucleic", 3, "the nucleotides of the six central base pairs: positions 4 to 9 of strand A "
         "and their partners on strand B", ":4-9,16-21"),
        ("purine-n7", "nucleic", 2, "the N7 atoms of all purines", "@N7"),
        ("not-water", "dialect", 1, "everything except the water", "!:WAT"),
        ("c1-or-20", "operators", 2, "the C1' atoms of strand A, and every atom of nucleotide 20", ":1-12@C1'|:20"),
        ("type-p", "type", 1, "all atoms of AMBER atom type P", "@%P"),
        ("h5-pair", "dialect", 2, "the two hydrogens on every C5' carbon (H5' and H5'')", "@H5',H5''"),
        ("restraint-dna", "context", 1, "the atoms a restraintmask should hold during equilibration: the DNA heavy "
         "atoms, leaving water and ions free",
         ":1-24&!@H="),
        ("strand-b-7th-c1", "chain", 2, "the C1' atom of the seventh nucleotide of strand B", ":19@C1'"),
    ],
    "memb": [
        ("popc-all", "lipid", 3, "every atom of the POPC lipids (head group and both tails)", ":1-87,118-204"),
        ("pope-all", "lipid", 3, "every atom of the POPE lipids (head group and both tails)", ":88-117,205-234"),
        ("pc-heads", "lipid", 1, "the phosphatidylcholine head-group residues", ":PC"),
        ("tails", "lipid", 2, "the acyl chains of every lipid, both tails, without the head groups", ":PA,OL"),
        ("oleoyl", "lipid", 1, "the oleoyl chains", ":OL"),
        ("pope-p", "lipid", 2, "the phosphorus atoms of the POPE lipids", ":PE@P31"),
        ("choline-n", "lipid", 2, "the choline nitrogens of the POPC lipids", ":PC@N31"),
        ("pe-amine-h", "lipid", 2, "the three amine hydrogens on each POPE head group", ":PE@HN1A,HN1B,HN1C"),
        ("double-bond", "lipid", 2, "the two carbons of the cis double bond in every oleoyl chain", ":OL@C19,C110"),
        ("carbonyl-c", "lipid", 3, "the ester carbonyl carbons of every lipid (one per tail)", "@C11,C21"),
        ("pa-c12", "lipid", 2, "the C12 carbon of the palmitoyl chains, and not of the oleoyl chains", ":PA@C12"),
        ("first-lipid", "lipid", 2, "the first lipid molecule in the topology, all of it", ":1-3"),
        ("head-lipid5", "lipid", 2, "the head-group residue of the fifth lipid in the topology", ":14"),
        ("pope-tails", "lipid", 3, "both acyl chains of the POPE lipids, without their head groups",
         ":88-117,205-234&:PA,OL"),
        ("lipid-heavy", "dialect", 1, "the heavy atoms of all lipids", ":1-234&!@H="),
        ("ol-h", "dialect", 1, "the hydrogens of the oleoyl chains", ":OL&@H="),
        ("charmm-p", "dialect", 2, "the atoms of the CHARMM-GUI selection 'resname POPC and name P'", ":PC@P31"),
        ("type-cb", "type", 2, "all atoms of Lipid21 atom type cB", "@%cB"),
        ("water-near-p", "distance", 2, "the water molecules, whole, with any atom within 4 Angstrom of a lipid "
         "phosphorus atom", "(@P31<:4.0)&:WAT"),
        ("k-near-heads", "distance", 2, "the potassium ions within 5 Angstrom of any head-group atom",
         "(:PC,PE<:5.0)&:K+"),
        ("potassium", "ion", 1, "the potassium ions", ":K+"),
        ("not-solvent", "ion", 1, "everything except the water and the ions", "!:WAT,K+,Cl-"),
        ("restraint-p", "context", 1, "the atoms a restraintmask should hold to keep the bilayer in place during "
         "equilibration: the phosphorus atom of every lipid", "@P31"),
    ],
}


AMBMASK_MAX = 79  # ambmask rejects 80 characters and more ("pop_evalstack"); pmemd 26 reads up to 1024


def _ambmask(system: str, mask: str) -> tuple[list[int] | None, str]:
    r = subprocess.run([AMBER / "bin" / "ambmask", "-p", "sys.parm7", "-c", "sys.rst7", "-out", "pdb", "-find", mask],
                       cwd=HERE / "systems" / system, capture_output=True, text=True, errors="replace", timeout=120,
                       env={**os.environ, "AMBERHOME": str(AMBER)})
    out = r.stdout + r.stderr
    atoms = [int(line[6:11]) for line in out.splitlines() if line.startswith("ATOM")]
    bad = [line.strip() for line in out.splitlines()
           if any(w in line.lower() for w in ("unknown", "error", "illegal", "syntax", "stop"))]
    return (None, bad[0]) if bad and not atoms else (atoms, "")


def _short_parts(mask: str) -> list[str] | None:
    """A long mask as a union of pieces ambmask can read: split at '|' outside parentheses (the operator
    that binds last), then cut any long ':list[@list]' or '@list' of only numbers or only names."""
    parts, depth, cur = [], 0, ""
    for ch in mask:
        depth += (ch == "(") - (ch == ")")
        if ch == "|" and depth == 0:
            parts, cur = parts + [cur], ""
        else:
            cur += ch
    out = []
    for part in parts + [cur]:
        part = part.strip()
        if len(part) <= AMBMASK_MAX:
            out.append(part)
            continue
        m = re.fullmatch(r"([:@])([^&|!()<>:@\s]+)(@[^&|!()<>:@\s]+)?", part)
        if not m or len(m.group(3) or "") > AMBMASK_MAX // 2:
            return None
        items = m.group(2).split(",")
        if len({bool(re.fullmatch(r"\d+(-\d+)?", x)) for x in items}) > 1:
            return None  # a mixed list means names only to ambmask; cutting it would change that
        chunk = []
        for x in items:
            if chunk and len(m.group(1) + ",".join(chunk + [x]) + (m.group(3) or "")) > AMBMASK_MAX:
                out.append(m.group(1) + ",".join(chunk) + (m.group(3) or ""))
                chunk = []
            chunk.append(x)
        out.append(m.group(1) + ",".join(chunk) + (m.group(3) or ""))
    return out


def select(system: str, mask: str) -> tuple[list[int] | None, str]:
    """Atom serials ambmask selects, or (None, its error) if it rejects the mask. A mask longer than ambmask
    reads is evaluated as a union of short pieces when it can be split exactly."""
    if len(mask) <= AMBMASK_MAX:
        return _ambmask(system, mask)
    parts = _short_parts(mask)
    if parts is None:
        return None, f"too long for ambmask ({len(mask)} > {AMBMASK_MAX} characters) and not splittable"
    atoms = set()
    for part in parts:
        got, err = _ambmask(system, part)
        if got is None:
            return None, err
        atoms.update(got)
    return sorted(atoms), ""


def digest(system: str) -> str:
    """What SHA256SUMS records: sys.parm7 without its first line (the build date), then sys.rst7."""
    d = HERE / "systems" / system
    parm = (d / "sys.parm7").read_bytes()
    return hashlib.sha256(parm[parm.index(b"\n") + 1:] + (d / "sys.rst7").read_bytes()).hexdigest()


def to_ranges(atoms: list[int]) -> str:
    runs, start = [], atoms[0]
    for a, b in zip(atoms, atoms[1:] + [None]):
        if b != a + 1:
            runs.append(f"{start}" if start == a else f"{start}-{a}")
            start = b
    return ",".join(runs)


def from_ranges(s: str) -> set[int]:
    out = set()
    for part in s.split(","):
        a, _, b = part.partition("-")
        out.update(range(int(a), int(b or a) + 1))
    return out


def split(rows: list[dict]) -> None:
    """Held out: a third of each category (rounded), chosen by hash so adding a task moves no other."""
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    for rs in by_cat.values():
        rs.sort(key=lambda r: hashlib.sha256(r["id"].encode()).hexdigest())
        for i, r in enumerate(rs):
            r["split"] = "test" if i < round(len(rs) / 3) else "dev"


if __name__ == "__main__":
    rows = []
    for system, tasks in TASKS.items():
        for tid, cat, diff, text, ref in tasks:
            atoms, err = select(system, ref)
            assert atoms, (system, tid, err)
            rows.append({"id": f"{system}-{tid}", "system": system, "category": cat, "difficulty": diff,
                         "text": text, "reference": ref, "n": len(atoms), "gold": to_ranges(atoms)})
    split(rows)
    (HERE / "tasks.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    for r in rows:
        print(f"{r['id']:28s} {r['category']:11s} {r['difficulty']} {r['split']:4s} {r['reference']:42s} {r['n']:6d}")
