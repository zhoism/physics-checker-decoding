#!/usr/bin/env bash
# Rebuild the mask-bench systems into masks/bench/systems/<id>/ (git-ignored): sys.parm7 and an
# ASCII sys.rst7 each, built with tleap from RCSB entries (checksummed) or packmol-memgen.
# No ligand needs parameters. Run from anywhere; needs the prime-amber env (AmberTools 24).
#   bash masks/bench/build.sh [bnbs|tryp|dna|memb ...]
# SHA256SUMS records the systems the gold atom sets were computed on (sha256 of sys.parm7 without its
# first line, which carries the build date, then sys.rst7). A rebuild must match it.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
export AMBERHOME="${AMBERHOME:-/opt/homebrew/Caskroom/miniforge/base/envs/prime-amber}"
export PATH="$AMBERHOME/bin:$PATH"

fetch() {  # fetch <PDB id> <sha256>: the entry as deposited, refused if RCSB has changed it
  curl -sfL -o "$1.pdb" "https://files.rcsb.org/download/$1.pdb"
  echo "$2  $1.pdb" | shasum -a 256 -c --quiet
}

bnbs() {  # barnase-barstar, 1BRS chains A (barnase, starts at Val3) and D (barstar, Glu64-Asn65 missing)
  fetch 1BRS 0076aae54252706a8c8c02f7b1e71ce2394b0e928b413590b4ac12aade9e8f6c
  # Protonation states set by renaming residues, chosen to exercise the names, not from a pKa calculation.
  awk '/^ATOM/ && (substr($0,22,1)=="A" || substr($0,22,1)=="D") {c=substr($0,22,1); r=substr($0,23,4)+0; n=substr($0,18,3)
    if (c=="A" && r==18) n="HID"; if (c=="A" && r==102) n="HIP"; if (c=="A" && r==108) n="LYN"
    if (c=="D" && r==39) n="ASH"; if (c=="D" && r==76) n="GLH"
    print substr($0,1,17) n substr($0,21)}' 1BRS.pdb > in.pdb
  pdb4amber -i in.pdb -o prep.pdb > pdb4amber.log 2>&1  # renumbers from 1; TER at the chain break and the barstar gap
  cat > leap.in <<'EOF'
source leaprc.protein.ff14SB
source leaprc.water.tip3p
m = loadpdb prep.pdb
solvateOct m TIP3PBOX 10.0
addIons m Na+ 0
addIons m Na+ 15 Cl- 15
saveAmberParm m sys.parm7 sys.rst7
quit
EOF
}

tryp() {  # bovine trypsin, 3PTB: chymotrypsin numbering 16-245 with skips and insertion codes, a Ca2+ ion
  fetch 3PTB 288f7954d4d013fa8eab3808e1037e2958e2dcd12c9eca65a3f1014404a9f9a2
  grep -E '^(ATOM|HETATM)' 3PTB.pdb | grep -v ' BEN ' > in.pdb  # benzamidine removed: a ligand needs parameters
  # --noter: pdb4amber would break the chain at every numbering skip. The six disulfides come from its CONECT records.
  pdb4amber --noter -i in.pdb -o p4a.pdb > pdb4amber.log 2>&1
  awk '/^HETATM/ && !t {print "TER"; t=1} {print}' p4a.pdb > prep.pdb  # end the chain before the Ca2+ and crystal waters
  cat > leap.in <<'EOF'
source leaprc.protein.ff14SB
source leaprc.water.spce
m = loadpdb prep.pdb
solvateBox m SPCBOX 10.0
addIons m CL 0
addIons m NA 12 CL 12
saveAmberParm m sys.parm7 sys.rst7
quit
EOF
}

dna() {  # the Dickerson-Drew B-DNA dodecamer, 1BNA: strands A (1-12) and B (13-24), in OPC water with KCl
  fetch 1BNA df42f1506792f191b957227b061360652adcf6f813eb69d9ec553067ea584670
  grep -E '^(ATOM|TER)' 1BNA.pdb > in.pdb  # crystal waters dropped
  pdb4amber -i in.pdb -o prep.pdb > pdb4amber.log 2>&1
  cat > leap.in <<'EOF'
source leaprc.DNA.OL21
source leaprc.water.opc
m = loadpdb prep.pdb
solvateOct m OPCBOX 10.0
addIons m K+ 0
addIons m K+ 12 Cl- 12
saveAmberParm m sys.parm7 sys.rst7
quit
EOF
}

memb() {  # a POPC:POPE 3:1 bilayer, Lipid21 + TIP3P + 0.15 M KCl; packmol's default fixed seed.
  # Packmol ends "without perfect packing" here (and with 20% cholesterol, at 40 or 50 A, even with 400 loops) and
  # keeps its best solution, which it calls a reasonable starting configuration. Masks need names, numbers and
  # coarse distances, not a converged packing; minimize before simulating anything.
  packmol-memgen --lipids POPC:POPE --ratio 3:1 --distxy_fix 50 --salt --parametrize --fflip lipid21 \
    --ffwat tip3p --noprogress --overwrite --log memgen.log > memgen.out 2>&1
  cp bilayer_only_lipid.top sys.parm7  # its .crd is NetCDF, which ambmask cannot read: write an ASCII restart
  printf 'trajin bilayer_only_lipid.crd\ntrajout sys.rst7 restart\nrun\n' | cpptraj -p sys.parm7 > cpptraj.log 2>&1
  MEMB_DONE=1
}

for id in "${@:-bnbs tryp dna memb}"; do
  for one in $id; do
    mkdir -p "$HERE/systems/$one" && cd "$HERE/systems/$one"
    MEMB_DONE=0
    "$one"
    [ "$MEMB_DONE" = 1 ] || { tleap -f leap.in > leap.log 2>&1; grep -q 'Errors = 0' leap.log; }
    got=$(tail -n +2 sys.parm7 | cat - sys.rst7 | shasum -a 256 | cut -c1-64)
    want=$(awk -v id="$one" '$2 == id {print $1}' "$HERE/SHA256SUMS")
    [ "$got" = "$want" ] && echo "built $one: matches SHA256SUMS" || echo "built $one: $got differs from SHA256SUMS" >&2
  done
done
