"""Ten plain-English -> AMBER mask tasks on the gold system, with gold atom sets from ambmask.
Run in the prime-amber conda env (ambmask). Writes tasks.jsonl."""
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
M = HERE / "system"  # complex.parm7 + ascii.rst7, git-ignored; ambmask runs with cwd here (it truncates long paths)

SYSTEM_DESC = ("System: a solvated protein. Residues 1-154 are the protein (AMBER residue names; disulfide "
               "cysteines are CYX, histidines are HID or HIE). Residue 155 is a Mg2+ ion (residue name MG), "
               "residues 156-157 are chloride ions (residue name Cl-), and every other residue is a 4-point "
               "water (residue name WAT, atoms O, H1, H2, EPW).")
TASKS = [  # id, request, reference mask (the gold is the atom set it selects)
    ("protein-heavy", "all heavy (non-hydrogen) atoms of the protein", ":1-154&!@H="),
    ("backbone", "the protein backbone atoms N, CA and C", ":1-154@N,CA,C"),
    ("ca-10-20", "the alpha carbons of residues 10 through 20", ":10-20@CA"),
    ("mg", "the magnesium ion", ":MG"),
    ("chloride", "all chloride ions", ":Cl-"),
    ("histidines", "all histidine residues, in any protonation state", ":HID,HIE"),
    ("disulfide-cys", "all disulfide-bonded cysteine residues", ":CYX"),
    ("near-mg", "every residue with any atom within 5 Angstroms of the magnesium ion, not counting the ion itself",
     "(:MG<:5.0)&!:MG"),
    ("solute", "everything except the water and the chloride ions", "!:WAT,Cl-"),
    ("sidechain-heavy", "the heavy atoms of the protein side chains (everything but the backbone N, CA, C and O, "
     "and no hydrogens)", ":1-154&!@H=&!@N,CA,C,O"),
]


def select(mask: str) -> tuple[list[int] | None, str]:
    """Atom serials ambmask selects, or (None, its error) if it rejects the mask."""
    r = subprocess.run(["ambmask", "-p", "complex.parm7", "-c", "ascii.rst7", "-out", "pdb", "-find", mask],
                       cwd=M, capture_output=True, text=True, timeout=120)
    out = r.stdout + r.stderr
    atoms = [int(line[6:11]) for line in out.splitlines() if line.startswith("ATOM")]
    bad = [line.strip() for line in out.splitlines()
           if any(w in line.lower() for w in ("unknown", "error", "illegal", "syntax", "stop"))]
    return (None, bad[0]) if bad and not atoms else (atoms, "")


if __name__ == "__main__":
    rows = []
    for tid, text, ref in TASKS:
        atoms, err = select(ref)
        assert atoms, (tid, err)
        rows.append({"id": tid, "text": text, "reference": ref, "gold": atoms})
        print(f"{tid:16s} {ref:28s} {len(atoms):6d} atoms")
    (HERE / "tasks.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (HERE / "system.txt").write_text(SYSTEM_DESC)
