"""What a model is shown for each system: what an agent that built it would have in front of it.
The leap input, the topology as cpptraj lists it, and the residues of the PDB entry it came from.
Nothing hand-written. Writes views/<id>.txt, and views/<id>.map.txt (the grounding aid: PDB residue
numbers mapped to topology numbers).
    python masks/bench/view.py      (prime-amber env: cpptraj; systems built by build.sh)"""
import re
import subprocess
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
SOURCES = {"bnbs": ("1BRS", "AD"), "tryp": ("3PTB", "A"), "dna": ("1BNA", "AB"), "memb": None}


def cpptraj(sid: str, cmd: str) -> str:
    out = subprocess.run(["cpptraj", "-p", "sys.parm7"], input=cmd + "\n", cwd=HERE / "systems" / sid,
                         capture_output=True, text=True, check=True).stdout
    return out.split(f"[{cmd}]\n", 1)[1].split("TIME:", 1)[0].rstrip()


def ranges(nums: list[int]) -> str:
    runs, start = [], nums[0]
    for a, b in zip(nums, nums[1:] + [None]):
        if b != a + 1:
            runs.append(f"{start}" if start == a else f"{start}-{a}")
            start = b
    return ",".join(runs)


def atom_table(sid: str) -> str:
    """atominfo condensed: one line per residue name and atom list, with the residues that have it."""
    rows = [line.split() for line in cpptraj(sid, "atominfo !:WAT").splitlines()[2:]]
    rows += [line.split() for line in cpptraj(sid, "atominfo :WAT").splitlines()[2:]]
    atoms = defaultdict(list)  # residue number -> [(name, type)]
    names = {}
    for r in rows:
        atoms[int(r[2])].append(f"{r[1]}({r[5]})")
        names[int(r[2])] = r[3]
    groups = defaultdict(list)
    for res, a in atoms.items():
        groups[(names[res], tuple(a))].append(res)
    if any(n == "WAT" for n, _ in groups):  # the one water printed stands for all of them
        (key,) = [k for k in groups if k[0] == "WAT"]
        groups[key] = [int(x) for x in re.findall(r"^\s*(\d+) WAT", cpptraj(sid, "resinfo :WAT"), re.M)]
    lines = []
    for (name, a), res in sorted(groups.items(), key=lambda kv: kv[1][0]):
        where = ranges(res) if len(res) <= 40 else f"{ranges(res)[:60]}... ({len(res)} residues)"
        lines.append(f"{name:4s} residues {where}\n     {' '.join(a)}")
    return "\n".join(lines)


def pdb_residues(path: Path, chains: str | None = None) -> str:
    """The residues of a PDB file per chain; chains: the ones to list (every chain in the file when None)."""
    records = [line for line in path.read_text().splitlines() if line[:6] in ("ATOM  ", "HETATM")]
    chains = chains or "".join(dict.fromkeys(line[21] for line in records))
    seen, water = defaultdict(list), defaultdict(int)
    for line in records:
        if line[21] in chains:
            name, num, chain = line[17:20].strip(), line[22:27].strip(), line[21]
            if name == "HOH":
                water[chain] += line[12:16].strip() == "O"
            elif not seen[chain] or seen[chain][-1] != f"{name}{num}":
                seen[chain].append(f"{name}{num}")
    out = [f"chain {c}: {' '.join(seen[c])}" + (f"  (+ {water[c]} HOH)" if water[c] else "") for c in chains]
    return f"$ residues of chain(s) {', '.join(chains)} in {path.name} (ATOM and HETATM records)\n" + "\n".join(out)


def numbering_map(sid: str) -> str:
    """Each residue of the PDB file tleap read, with the topology residue it became. tleap keeps the file's
    order and puts the ions addIons adds after the last non-water residue, ahead of any crystal waters.
    Every pair is checked by residue name. pdb4amber's renum file drops insertion codes and misses the shift."""
    label = (HERE / "systems" / sid / "sys.parm7").read_text().split("%FLAG RESIDUE_LABEL")[1].split("%FLAG")[0]
    label = "".join(label.splitlines()[2:])
    names = [label[i:i + 4].strip() for i in range(0, len(label), 4)]  # names[k] is topology residue k + 1
    pdb, seen = [], set()
    for line in (HERE / "systems" / sid / "in.pdb").read_text().splitlines():
        key = (line[21], line[17:20].strip(), line[22:27].strip())
        if line[:6] in ("ATOM  ", "HETATM") and key not in seen:
            seen.add(key)
            pdb.append(key)
    solute = [k for k in pdb if k[1] != "HOH"]
    first_wat = names.index("WAT") + 1
    lines = defaultdict(list)
    for k in pdb:
        top = solute.index(k) + 1 if k[1] != "HOH" else first_wat + [w for w in pdb if w[1] == "HOH"].index(k)
        assert names[top - 1] == {"HOH": "WAT", "HIS": "HIE"}.get(k[1], k[1]) or names[top - 1][:2] == k[1][:2], (k, top)
        lines[k[0]].append(f"{k[1]}{k[2]}={top}")
    return (f"PDB residue -> topology residue number, for every residue tleap read from {SOURCES[sid][0]}\n"
            + "\n".join(f"chain {c}: {' '.join(v)}" for c, v in lines.items()) + "\n")


def view(sid: str) -> str:
    leap = (HERE / "systems" / sid / "leap.in")
    parts = [f"The topology sys.parm7 and coordinates sys.rst7 were built with AmberTools tleap"
             + (f" from PDB entry {SOURCES[sid][0]}, chain(s) {', '.join(SOURCES[sid][1])}." if SOURCES[sid]
                else " by packmol-memgen.")]
    if leap.exists():
        parts.append("$ cat leap.in\n" + leap.read_text().rstrip())
    parts += topology(sid)
    if SOURCES[sid]:
        parts.append(pdb_residues(HERE / "systems" / sid / f"{SOURCES[sid][0]}.pdb", SOURCES[sid][1]))
    return "\n\n".join(parts) + "\n"


def topology(sid: str) -> list[str]:
    """cpptraj's listings of sys.parm7, the part of the view every system has. sid is a bench id, or the absolute
    path of any directory holding sys.parm7 (pathlib lets an absolute path replace HERE / "systems")."""
    parts = ["$ cpptraj -p sys.parm7"]
    for cmd in ("parminfo", "molinfo :* short", "resinfo !:WAT"):
        parts.append(f"> {cmd}\n{cpptraj(sid, cmd)}")
    wat = [int(x) for x in re.findall(r"^\s*(\d+) WAT", cpptraj(sid, "resinfo :WAT"), re.M)]
    if wat:  # an implicit-solvent system has none
        parts.append(f"> resinfo :WAT   (condensed)\nWAT residues {ranges(wat)}")
    parts.append(f"> atominfo   (condensed: atom name(type) for each residue name; residues with the same atoms "
                 f"grouped)\n{atom_table(sid)}")
    return parts


if __name__ == "__main__":
    (HERE / "views").mkdir(exist_ok=True)
    for sid in SOURCES:
        if (HERE / "systems" / sid / "sys.parm7").exists():
            text = view(sid)
            (HERE / "views" / f"{sid}.txt").write_text(text)
            print(f"{sid}: {len(text)} chars")
            if SOURCES[sid]:
                (HERE / "views" / f"{sid}.map.txt").write_text(numbering_map(sid))
