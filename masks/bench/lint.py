"""Targeted hints for a mask, from the mask and the topology alone (never the gold): what a checking
tool could tell an agent. Each hint names one failure from docs/research_notes/mask_catalogue.md."""
import re

VERSION = 2  # 2: a ':' repeated in a list was misreported as a mixed list; distance syntax spelled out

VMD_WORDS = re.compile(r"\b(and|or|not|resname|resid|resi|name|within|around|protein|backbone|water|chain|segid|"
                       r"index|element|same|byres|hydrogen)\b", re.I)
FAMILIES = [{"HIS", "HID", "HIE", "HIP"}, {"ASP", "ASH"}, {"GLU", "GLH"}, {"LYS", "LYN"}, {"CYS", "CYX", "CYM"}]


def _lists(mask: str, sigil: str) -> list[list[str]]:
    """The comma lists after each ':' or '@' (atom types after '@%' are skipped)."""
    out = []
    for m in re.finditer(rf"{re.escape(sigil)}(%?)([^&|!()<>:@\s]+)", mask):
        if not m.group(1) and not (sigil == ":" and m.start() and mask[m.start() - 1] in "<>"):
            out.append(m.group(2).split(","))
    return out


def lint(mask: str, top: dict) -> list[str]:
    hints = []
    if VMD_WORDS.search(mask):
        hints.append("This is VMD/MDAnalysis/PyMOL syntax. AMBER masks use ':' for residues, '@' for atoms, '&' '|' '!' "
                     "for and/or/not, and '<:' or '<@' for distances.")
    if re.search(r"[*?]", mask.replace(":*", "").replace("@*", "")):
        hints.append("AMBER's only wildcard is '=' at the end of a name ('@H=' is every name starting with H). '*' only "
                     "stands alone (':*', '@*'), and '?' is not allowed.")
    if "@/" in mask:
        hints.append("pmemd has no element selector; '@/' is cpptraj only. Select by name ('@H=') or type ('@%').")
    if "^" in mask or "::" in mask or ":;" in mask:
        hints.append("pmemd has no molecule ('^'), chain ('::') or original-number (':;') selector; those are cpptraj "
                     "only. Use topology residue numbers.")
    if re.search(r",\s*[:@]", mask):
        hints.append("pmemd rejects a ':' or '@' repeated inside a list (':40,:84' is cpptraj only). Write one list "
                     "(':40,84', '@SG,SD'), or join two selections with '|' (':1-12@CA|:20').")
    residues, atoms = set(top["residues"]), set(top["atoms"])
    for kind, sigil, known in (("Residue", ":", residues), ("Atom", "@", atoms)):
        for items in _lists(mask, sigil):
            nums = [x for x in items if re.fullmatch(r"\d+(-\d+)?", x)]
            names = [x for x in items if x not in nums and x not in ("*", "")]
            if nums and names:
                hints.append(f"pmemd ignores the numbers in a list that also has names ('{sigil}{','.join(items)}' "
                             f"selects only {','.join(names)}). Join them with '|' instead.")
            upper = {k.upper() for k in known}  # ambmask ignores case
            for n in names:
                stem = n.rstrip("=").upper()
                if re.search(r"[*?/]", n) or (any(k.startswith(stem) for k in upper) if n.endswith("=") else stem in upper):
                    continue
                listing = f" Its residue names: {' '.join(sorted(residues))}." if sigil == ":" else ""
                if sigil == "@" and n.upper() in {t.upper() for t in top["types"]}:
                    listing = f" '{n}' is an atom type here: select types with '@%{n}'."
                hints.append(f"{kind} name '{n}' does not exist in this topology.{listing}")
            for n in names:
                fam = next((f for f in FAMILIES if n.upper() in f), None)
                variants = sorted((fam & residues) - {n.upper()}) if fam and sigil == ":" else []
                variants += sorted(r for r in residues if sigil == ":" and r != n and r.rstrip("53") == n)
                if variants:
                    hints.append(f"This topology also has residues named {', '.join(variants)} (another protonation "
                                 f"state or a terminus of {n}). Include them if the request covers them.")
    if any("H" in items for items in _lists(mask, "@")):
        hints.append("'@H' selects only atoms named exactly H (backbone amide hydrogens). Every hydrogen is '@H='.")
    if re.search(r"\)\s*@", mask):
        hints.append("An atom list after ')' is not limited to the residues in the parentheses: '(:7,137)@SG' selects "
                     "every SG atom in the system. Write ':7,137@SG'.")
    bare = [m.group(1).split(",") for m in re.finditer(r"(?:^|[&|!(\s])@([^&|!()<>:@\s]+)", mask)]
    if "CA" in residues and any("CA" in items for items in bare):
        hints.append("'@CA' also matches the calcium ion, whose atom is named CA. Restrict it to the protein residues "
                     "if you mean alpha carbons.")
    if re.search(r"[<>][:@]", mask):
        hints.append("'<:' selects whole residues with any atom within the cutoff, '<@' single atoms; both include "
                     "the reference atoms themselves.")
    if "<" in mask or ">" in mask:
        hints.append("A distance selection is <reference><operator><cutoff>, with the operator '<:' or '<@' written "
                     "directly before the number: ':100<:5.0' is the residues within 5 A of residue 100. Restrict it "
                     "with '&': '(:100<:5.0)&:WAT'.")
    if "&" in mask and "|" in mask and "(" not in mask:
        hints.append("'&' binds tighter than '|': ':1-3|:5-7&@CA' means ':1-3|(:5-7&@CA)'. Add parentheses if you "
                     "meant otherwise.")
    return list(dict.fromkeys(hints))
