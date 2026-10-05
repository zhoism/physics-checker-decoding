# Mask bench: 125 realistic mask tasks, and what fixes a cheap model's failures

2026-10-02. This follows `masks_scout.md`. Its question: does a cheap model fail at least 20% of
realistic AMBER mask requests, and which fixes those failures: a grammar, grounding, or targeted
hints? 2026-10-03 adds decoding arms on an open 7B and 14B: is the checker better inside the decoder
or after it? 2026-10-04 adds Qwen3.8-27B and Gemma-4-31B, the semi-reliable models where it could matter. The failure categories and their sources are in `mask_catalogue.md`. Tables:
`masks/bench/results/report.md`, rebuilt by `.venv/bin/python masks/bench/report.py >
masks/bench/results/report.md`.

## What was built (`masks/bench/`)

- **Four systems**, rebuilt by `build.sh` (prime-amber, AmberTools 24.8). Each is checked against
  `SHA256SUMS`; tleap and packmol rebuilds were byte-identical apart from the date line.
  - `bnbs`: barnase–barstar, 1BRS chains A+D. Barnase starts at Val3. Barstar is missing Glu64–Asn65,
    so pdb4amber split it into two segments. Some protonation states were set by hand.
    ff14SB, TIP3P, Na⁺/Cl⁻.
  - `tryp`: trypsin, 3PTB with benzamidine removed. Chymotrypsin numbering with skips and insertion
    codes, a Ca²⁺, 62 crystal waters. ff14SB, SPC/E, NA/CL.
  - `dna`: the 1BNA dodecamer. OL21, OPC (EPW extra points), K⁺/Cl⁻.
  - `memb`: a POPC:POPE 3:1 Lipid21 bilayer from packmol-memgen, TIP3P, K⁺/Cl⁻. Packmol did not fully
    converge, which is fine for masks; see the build script.
- **Views** (`view.py`): what the model is shown. It gets the leap input, cpptraj's `parminfo`,
  `molinfo` and `resinfo` of every non-water residue, and the atom names and types of each residue
  kind. For the three PDB systems it also gets the residues of the PDB chains used. Nothing is
  hand-written, unlike the pilot's summary. The **grounding** add-on (`views/<id>.map.txt`) maps every
  PDB residue to its topology number, following tleap's real order. pdb4amber's renum file drops
  insertion codes and misses the crystal waters moved past the ions.
- **Tasks** (`tasks.py` → `tasks.jsonl`): 125 plain-English requests over 14 categories and 3
  difficulties. The gold is the atom set ambmask selects with the reference mask. 41 tasks are held
  out (`test`), a third of each category chosen by hash. `tests/test_mask_bench.py` checks on every
  push that every gold reproduces on the checksummed systems.
  - ambmask reads at most 79 characters. `select` scores a longer mask as a union of short pieces.
- **Grammar v2** (`mask_grammar2.py`; v1 is `masks/pilot/mask_grammar.py`): a 79-character cap (a
  prefix passes only if it can still be finished in time), no lists mixing numbers and names, `@%` lists
  of the types ambmask's parser reads (no `+`/`-`, no wildcard), and `=` after at most 3 characters.
  Every reference is in it. Of 1,200 random v2 masks ambmask rejected one, which exposed the wildcard
  rule since added; 500 more from the final grammar all passed (`tests/test_mask_grammar2.py`).
- **GPU decoding** (`decode.py`, run by `colab/arms.ipynb` on Kaggle's two T4s with the bundle from
  `colab/bundle.sh`). `PrefixLM` keeps the KV cache of the last query, so a system's view is prefilled
  once and each step runs one token (`tests/test_mask_decode.py`).

## Protocol

- **Claude** (`blind.py`): `claude -p --tools "" --strict-mcp-config --no-session-persistence` from a
  fresh empty directory. One prompt per system holds the view and all of that system's tasks; the
  model answers a sheet. Canaries (Haiku, Sonnet) asked the model to read the answer file. Neither
  could; both wrote a fake tool call as text.
  - Each first-try failure gets two independent repairs. **checker** is the pilot's message: ambmask's
    verdict, where the grammar stops, the atom count. **lint** is that plus `lint.py`'s hints, which
    are computed from the mask and topology alone.
- **Qwen2.5-7B-Instruct-4bit** (`qwen.py`, MLX): the same prompt and sheet. `free` samples it. `grammar`
  holds the sheet to its headers and every mask to the system's mask grammar (AWRS).
- **Qwen2.5-7B/14B-Instruct, nf4** (`decode.py`, Kaggle): one prompt per task, built from
  `blind.system_prompt` and `blind.FORMAT` with that one task (`sheet` keeps the whole-system prompt).
  Temperature 0.7, 3 runs. `free` samples. `grammar1`/`grammar2` hold the reply to its header and the mask
  to grammar v1/v2 (AWRS, one particle, `proper_weights=False`, no rejection limit). `checked` is grammar2,
  and when a mask ends ambmask must read it and select at least one atom: the checker inside the decoder.
  Each first-try failure gets blind.py's lint repair, decoded the same way. Kaggle's ambmask (the same
  AmberTools 24.8 build) reproduced all 125 golds before decoding; `report.py` rescores every row here.

## Results

| arm | first try | + checker repair | + lint repair |
|---|---|---|---|
| Haiku 4.5, view (3 runs × 125) | 220/375 (59%) | 262/375 (70%) | 329/375 (88%) |
| Haiku 4.5, view + map | 253/375 (67%) | 281/375 (75%) | 327/375 (87%) |
| Sonnet 5, view (2 runs) | 240/250 (96%) | 249/250 | 249/250 |
| Qwen 7B MLX free, sheet (2 runs) | 2/250 (1%) | – | – |
| Qwen 7B MLX grammar v1, sheet (1 sheet: bnbs, 41 tasks) | 0/41 | – | 0/41 |
| Qwen 7B nf4 free, one task per prompt (3 runs) | 4/375 (1%) | – | 5/375 (1%) |
| Qwen 7B nf4 grammar v1 | 37/375 (10%) | – | 55/375 (15%) |
| Qwen 7B nf4 grammar v2 | 35/375 (9%) | – | 47/375 (13%) |
| Qwen 7B nf4 grammar v2 + checker potential | 32/375 (9%) | – | 45/375 (12%) |
| Qwen 7B nf4 grammar v2, sheet | 33/375 (9%) | – | 41/375 (11%) |
| Qwen 14B nf4 free, one task per prompt | 0/375 (22 re-parsed) | – | 0/375 (28 re-parsed) |
| Qwen3.8-27B via OpenRouter, thinking off (3 runs) | 104/375 (28%) | 131/375 (35%) | 206/375 (55%) |
| Qwen3.8-27B nf4 free, sheet (Kaggle, 3 runs) | 147/375 (39%) | – | 226/375 (60%) |
| Qwen3.8-27B nf4 grammar v2, sheet | 187/375 (50%) | – | 239/375 (64%) |
| Qwen3.8-27B nf4 grammar v2 + checker potential, sheet | 128/375 (34%) | – | 145/375 (39%) |
| Qwen3.8-27B picks among its 3 grammar v2 samples, shown their selections (`pick.py`) | 77/125 (62%) | – | – |
| Qwen3.8-27B nf4 grammar v2, one task per prompt (1 run, after the `qwen.Sheet` fix) | 46/125 (37%) | – | 62/125 (50%) |
| Qwen3.8-27B nf4 grammar v2 + checker potential, one task per prompt (1 run, after the fix) | 46/125 (37%) | – | 66/125 (53%) |
| Gemma-4-31B via OpenRouter, thinking off (3 runs) | 171/375 (46%) | 191/375 (51%) | 268/375 (71%) |
| Gemma-4-31B bf16 free, sheet (A100, 3 runs) | 172/375 (46%) | – | 278/375 (74%) |
| Gemma-4-31B bf16 grammar v2, sheet | 239/375 (64%) | – | 267/375 (71%) |
| Gemma-4-31B bf16 grammar v2 + checker potential, one task per prompt | 223/375 (59%) | – | 253/375 (67%) |

Held-out split, first try → after lint repair: Haiku view 73/123 (59%) → 111/123 (90%). Qwen 7B nf4:
free 2 → 3, grammar v1 14 → 23 (19%), grammar v2 15 → 19, checked 15 → 21, sheet 16 → 16 (of 123).
Qwen3.8-27B: OpenRouter 36 → 67, nf4 free 46 → 75, grammar v2 56 → 75, checked 36 → 43 (of 123).
Gemma-4-31B: OpenRouter 54 → 91, bf16 free 52 → 90, bf16 grammar v2 76 → 87 (of 123). The nf4 Gemma arms
and the per-task arms are in the Gemma section.

## The answer

**Does a cheap model fail at least 20%?** Yes, on every arm.
- Haiku fails 41% on the first try (33% with the map).
- Qwen 7B fails 99%: its sheets are VMD syntax (`resname DC5 … -and- chain B`).
- Sonnet fails 4%. Its 10 misses are `@H*` (×4), `@/C`, one barstar Trp left out, and the silent mixed
  list `:1,TRP` / `:1,PRO` (4 of 4 tries). pmemd reads that list as names only and drops residue 1.

**Grammar.**
- 104 of Haiku's 155 first-try failures (67%) are masks ambmask rejects, so a grammar would block
  them. Grammar-constrained decoding can't run on Haiku (no logits), so whether it then lands on the
  right atoms is unmeasured.
- On the 7B, v1 in the MLX sheet run was valid but meaningless (`!:A= & :WAT & :Na+ & :Cl-`), then
  looped `& :H=` until it ran out of tokens, leaving 36 of 41 tasks unanswered. With v2's length cap and
  3 runs on a GPU, the grammar takes the 7B from 1% to 9–10%, all of it on easy tasks (next section).
- The pilot's 9/30 was on easy tasks with a hand-written summary. A model that does not know the
  language gets no knowledge from a grammar.
- On models that know the language it pays on the first try: Qwen3.8-27B 39% → 50%, Gemma-4-31B 46% → 64%
  (bf16). After one lint repair the free model catches up both times (sections below).

**Grounding (the PDB→topology map).**
- First try rose 8 points (59% → 67%). That is within the noise: the membrane, whose prompt is
  identical in both arms, scored anywhere from 4/23 to 20/23 depending on the sheet.
- The view already grounds the numbering. Haiku's residue numbers were nearly always right (Ser195
  → `:177`). Only 3 "numbering" failures were mapping errors (the barstar gap, the 218
  skip), out of 14 numbering failures in the view arm. The rest were syntax (`:40,:84`, `(:7,137)@SG`)
  or `!@H`.

**Targeted hints.**
- A repair with lint hints recovers most failures: 59% → 88%, against 70% for the pilot's generic
  checker message. It works on the held-out split too (59% → 90%).
- lint v2 fixed a v1 bug and spelled out the distance syntax. That took distance tasks after repair
  from 6 of 66 (v1, both arms) to 32 of 66. With the buggy v1, the view arm reached 82%; those rows are kept as
  `haiku_*.lint1.jsonl`.
- After lint, 46 failures remain in the view arm: 36 wrong atoms, 9 still rejected, 1 empty. They are
  mostly distance (18), termini (6) and atom names (6), which is semantics, not syntax.

## Checker in the decoder or after it: Qwen 7B, 3 runs × 125

These arms ran before `qwen.Sheet` was fixed (2026-10-04): a constrained reply could end only after a
newline that followed its last mask. A model that wanted to stop after its mask could not, and when a
newline was less likely than ` &` it kept writing toward the 79-character cap. In one task per prompt
every answer is a last answer (128 of grammar v2's 375 masks and 174 of the checked arm's are 60
characters or longer); in a sheet only the last task is (its median length is 79, against 23 for the
others). So the constrained 7B numbers below measure that too. The 27B rerun after the fix is the clean
comparison of grammar and checker.

- **The grammar in the decoder helps, a little.** First try goes from 1% (free) to 9–10% under every
  grammar arm, in each of the 3 runs (7–15 right per run against 1–2) and in all 4 systems, so it is
  not one sheet. All of it is easy tasks: difficulty 1 goes from 3% to 23–31%, difficulty 2 from 0% to
  3–5%, difficulty 3 stays 0. The masks it gets right are one-name selections (`:Na+`, `:K+`, `:CL`,
  `!:WAT`, `:HIP`, `@EPW`). Free, the model nearly writes these but wraps them in junk or invalid syntax
  (`@K+ 25-47 49-57`, `.:WAT`, `O EPW`). The reply format is a small part of it: scored on the first
  mask of each reply under any header, free gets 6/375.
- **The checker potential adds nothing on top.** grammar2 + checker scores 32/375 against grammar2's 35.
  With one particle the decoder cannot back out of a mask that will select nothing: the model keeps
  writing to the 79-character cap and strands there (76 of 375 first tries), still selecting nothing.
  Some of those strandings are the forced newline above.
- **The checker after decoding works only on valid masks.** The lint repair takes free from 4 to 5, and
  the grammar arms up by 8 to 18 (best: grammar v1, 37 → 55, 15%). So the two combine, modestly: the
  grammar makes the masks AMBER, then the hints have something to act on.
- **v2 against v1, and per task against sheet: no difference.** v1 37, v2 35. The cap ended v1's runaway
  masks (96 of v1's first tries ran out of tokens, none of v2's) without changing accuracy. The sheet
  scored like one task per prompt (33 against 35), so the uncapped grammar, not the layout, sank the
  MLX run.
- **Picking among samples has little to pick from.** Under a grammar arm 16–20 tasks are right in at
  least one of the 3 runs (4–7 in all three), so choosing the right sample of 3 could add about 5 points.
- **The 14B does not follow the answer format.** It writes `===`, the id, then the mask on its own line
  in 368 of 375 replies, so the protocol's parser finds nothing (0/375). Re-parsed leniently (the line
  after the id), it gets 22/375 (6%) first try and 28 (7%) after lint: above the 7B free (4), far below
  Haiku (59%). A grammar would force the format; whether it also lifts the masks is untested.

**Answer.** For an open 7B, the checker inside the decoder (the grammar) beats the checker after it
(lint repair alone does nothing), but only on easy tasks. The checker potential on finished masks adds
nothing with one particle. The two combine to 11–15%. That is far from usable, and a 14B prompted alone
is not much better, so the model where decoding could matter is larger.

## Qwen3.8-27B: a semi-reliable model, decoded

Chosen by a rule fixed before the runs: first try roughly 40–90%, most failures of a kind a grammar or
checker can see, and small enough to decode on two T4s (4-bit). Prompted through OpenRouter's free
endpoint (bf16, thinking off) it gets 28% first try and 55% after the lint repair, and 200 of its 271
first-try failures are masks ambmask rejects or that select nothing. Its residue numbers are mostly right
(Glu73 → `:71`); its syntax is not (`(@OE1+@OE2)&:71`, `within 5.0`). Decoded on Kaggle: the sheet
layout, 3 runs, nf4 across two T4s, `PrefixLM` snapshots for its hybrid linear-attention layers.

- **The grammar in the decoder raises the first try 11 points**: 147 → 187 of 375 (39% → 50%), higher in
  each run (49/51/47 → 71/58/58) and in 3 of 4 systems (bnbs 55 → 65, memb 27 → 36, tryp 13 → 33, dna
  52 → 53). One trypsin sheet (5 → 19) is 14 of the 40. Held-out: 37% → 46%. Two more grammar runs (66,
  61) keep it at 50% over 5 runs (314/625).
- **After one lint repair the grammar barely matters**: 226 → 239 (60% → 64%), and 75 → 75 held out; over
  5 grammar runs, 62%. The checker after decoding recovers most of what the checker inside recovers; the
  grammar saves the turn.
- **The grammar turns loud failures into silent ones.** Free, 154 first tries are masks ambmask rejects
  (pmemd would stop) and 74 are valid but wrong or empty. Under the grammar none is rejected and 188 are
  valid but wrong or empty. After the lint repair: free leaves 73 loud and 76 silent failures, grammar v2
  0 loud and 136 silent. In a pipeline, where a rejected mask stops the run and a wrong one does not,
  that is a cost.
- **The checker potential in the sheet layout fails for a layout reason.** When it strands a mask at the
  79-character cap (no way to finish selects atoms), the one particle dies and takes the rest of the sheet
  with it: 177 of 375 tasks never answered, every trypsin sheet among them.
- **One task per prompt, the checker potential ties the grammar** (after the `qwen.Sheet` fix, 1 run):
  grammar v2 46/125 first try and 62 after lint, grammar v2 + checker 46 and 66. Each is right on 15 tasks
  the other misses. The checker turns 5 of the grammar's empty selections into right answers, and still
  strands 17 masks at the cap: a conjunction that already selects nothing (`:73@CD&@OE1,OE2&...&:A=,A=,...`)
  cannot be rescued by more `&` terms, and AWRS has no way to back out. Before the fix the same arm scored
  118/375 with a median mask of 77 characters; after it, 15.
- **The layout matters more than either.** The same model on the same 125 tasks scores 37% one task per
  prompt and 57% in a sheet (grammar v2, run 0), and a sheet is one prompt per system instead of one per task.
- **Picking among samples has room here.** 83 of 125 tasks are right in at least one of the 3 grammar
  runs (44 in all three), against 50% per run; after lint, 99. Over 5 runs, 87. On the 7B it was 16–20.
- **The served model and the local one differ.** Free, OpenRouter's bf16 scored 28% and the local nf4
  39%, with OpenRouter's runs at 25, 30 and 49 of 125. Decoding arms are compared with the local free arm.

- **Showing the selection and letting the model pick does best** (`pick.py`). For each task the candidates
  are the distinct selections among the grammar arm's 3 samples, each shown with what ambmask selects
  (atom count, residues, atom names); the 27B (OpenRouter, temperature 0) answers a letter or NONE. It is
  right on 77/125 (62%; held-out 24/41), says NONE on 19 and picks a wrong candidate on 29. Against one
  grammar sample (50% right, 50% silent) and grammar plus lint repair (64% right, 36% silent), it matches
  the repair without a repair turn and cuts silent failures to 23%. With a right candidate in the pool
  (83 tasks) it picked it 77 times; with none (42) it said NONE 17 times. Adding the free arm's samples
  (up to 6 candidates) gives 76/125: the right answer was already among the grammar samples. Five grammar
  samples also give 76/125: a right candidate is in 87 pools, and the judge does not find the 4 new ones.
  What it still gets wrong is semantic: barstar's numbering gap (`:109-171`), `GLH` among the histidines.

**Answer for the 27B.** The grammar inside the decoder lifts the first try from 39% to 50%, consistently,
but after one repair the gain is 2–4 points, and it trades rejected masks for silent wrong ones. A checker
potential on finished masks adds nothing over the grammar. A check that shows the selection, used to
choose among the model's own samples, reaches the repair's accuracy and halves the silent failures that
remain. None of it makes the 27B reliable (Haiku is 59% → 88%).

**For the tool.** The order of value for a cheap model is a checker that shows the selection, then
system-aware hints, then a grammar. Grounding beyond a cpptraj listing showed no measurable value. A
grammar alone does not rescue an open 7B model on realistic tasks.

## The open-model ladder: prompting only, through OpenRouter

The Claude protocol unchanged (`blind.py openrouter:<id>`: one sheet per system, then the checker and lint
repairs), thinking off, temperature 0.7. Free endpoints where they exist, paid otherwise. Models that fit two
T4s could be decoded on Kaggle; the rest are scored by API only.

| model (open weights) | runs | first try | + checker repair | + lint repair | held-out, first → lint |
|---|---|---|---|---|---|
| Qwen3.8-27B (free endpoint) | 3 | 104/375 (28%) | 131 (35%) | 206 (55%) | 36 → 67 of 123 |
| Gemma-4-31B-it | 3 | 171/375 (46%) | 191 (51%) | 268 (71%) | 54 → 91 of 123 |
| Nemotron-3-Super-120B-A12B (free) | 1 | 42/125 (34%) | 42 | 53 (42%) | 13 → 18 of 41 |
| Qwen3.5-122B-A10B | 1 | 42/125 (34%) | 43 | 60 (48%) | 13 → 22 of 41 |
| Qwen3.5-397B-A17B | 1 | 67/125 (54%) | 91 (73%) | 79 (63%) | 25 → 29 of 41 |
| Nemotron-3-Ultra-550B-A55B (free) | 3 | 221/375 (59%) | 243 (65%) | 263 (70%) | 77 → 94 of 123 |

- **Size alone is not the lever.** Qwen3.5-122B (an older generation, 10B active) is no better than
  Qwen3.8-27B; the 397B is better on the first try.
- **Nemotron-3-Ultra matches Haiku's first try (59%), but repairs help it less** (70% after lint against 88%):
  more of its failures are valid masks on the wrong atoms (65 of 154), which a syntax hint does not fix.
  Picking among its 3 samples (`pick.py`, the Ultra as judge): 82/125 right (66%), 19 NONE, 24 wrong picks
  (held-out 29/41). It is consistent: for 76 tasks its 3 samples select the same atoms, which leaves pick
  only to accept or flag.
- **Gemma-4-31B is the best candidate for decoding.** 46% first try, and 109 of its 204 failures are masks
  ambmask rejects, mostly `@H*` and distances written `(:1-195)<6` without the `:` or `@`: what grammar v2
  removes. It fits two T4s, and it is decoded below.

## Gemma-4-31B: the grammar's best case, decoded

Picked from the ladder: semi-reliable (46% first try by API) with most failures of the kind a grammar
removes. Decoded twice with the 27B's protocol (sheet layout, 3 runs × 125, temperature 0.7, thinking
off): in nf4 on Kaggle's two T4s (fp16 compute; no overflow), and unquantized in bf16 on one A100 80GB
(`colab/modal_app.py`, Modal).

| Gemma-4-31B-it, 3 runs × 125 | first try | + lint repair | first tries ambmask rejects | silent failures after lint | held-out, first → lint |
|---|---|---|---|---|---|
| free, OpenRouter (served bf16) | 171 (46%) | 268 (71%) | 109 | 89 | 54 → 91 |
| free, nf4 (Kaggle) | 154 (41%) | 254 (68%) | 97 | 106 | 49 → 86 |
| free, bf16 (A100) | 172 (46%) | 278 (74%) | 104 | 92 | 52 → 90 |
| grammar v2, nf4 | 195 (52%) | 244 (65%) | 0 | 131 | 64 → 83 |
| grammar v2, bf16 | 239 (64%) | 267 (71%) | 0 | 108 | 76 → 87 |
| grammar v2, bf16, one task per prompt | 223 (59%) | 249 (66%) | 0 | 126 | 79 → 86 |
| grammar v2 + checker potential, bf16, one task per prompt | 223 (59%) | 253 (67%) | 0 | 122 | 79 → 86 |

- **The local bf16 model reproduces the served one** (46% first try each), and nf4 costs it 5 points.
  Quantization was hiding part of the grammar's effect: in nf4 it adds 11 points, in bf16 18.
- **In bf16 the grammar takes the first try from 46% to 64%**, in every run (56–59 → 78–82 of 125) and
  every system (bnbs 57 → 75, dna 60 → 74, memb 21 → 51, tryp 34 → 39); held-out 42% → 62%. That is
  Haiku's first try (59%), from an open 31B model in one call, with nothing added to the prompt.
- **After one lint repair the grammar adds nothing**: free 74%, grammar 71% (bf16); 68% and 65% (nf4).
  The free model's rejected masks are what the lint hints fix best, and the grammar has already spent
  them. Free + lint ends with 5 loud and 92 silent failures, grammar + lint with 0 loud and 108 silent.
- **Gemma does not need the sheet**: one task per prompt it scores 59%, against 64% in a sheet. The 27B
  lost 20 points the same way (37% against 57%).
- **The checker potential adds nothing here either** (one task per prompt, 3 runs): 223/375 first try, the
  same as grammar alone, and 253 against 249 after lint. Each wins 10 tasks the other misses. It turns 2 of
  the grammar's 14 empty selections into right answers, strands 12 masks at the cap
  (`:109-195&(:1-108@*)&(:1-108@*)&...`), and takes half again as long to decode (45 min against 30).
- **Pick among its own samples has little to pick from** (`pick.py`, the served model as judge, the 3 nf4
  grammar samples): 68/125 (54%). For 80 of 125 tasks the samples select the same atoms. A right
  candidate was there for 70 tasks and was picked in 68; with none (55) it said NONE 20 times.

**Answer for Gemma.** The grammar inside the decoder makes this 31B model's first try as good as Haiku's,
in one call with no repair turn and no extra context, which is where the grammar earns its place in a
pipeline. Given a turn, the checker after decoding (lint repair) does as well or better, and leaves fewer
silent failures. Either way, after the repair 26–29% of the masks are still wrong.

## Caveats

- **Sheets cluster.** A model's failures move together within one sheet (one system, one sample), so
  the effective sample is about 12 sheets per Haiku arm, not 375 tasks. Gaps under about 10 points
  are not established.
- **The held-out split is not clean for lint.** The smoke run that suggested three of v1's hints
  covered both splits, and v2 was written after the full run.
- **The MLX Qwen grammar arm is one sheet.** It was stopped because Qwen 7B with 10–12k-token prompts
  filled the laptop's RAM and swap (DEVLOG `watch:`). The free arm ran 2 of 3 planned runs.
- **report.py rescores every stored mask with ambmask on each run**, now about 10 minutes.
- **The ladder's single-run rows are triage**, not results: one sample of each of 4 sheets.
- **The forced newline.** Every constrained arm decoded before 2026-10-04's `qwen.Sheet` fix had to write
  a newline before its reply could end: all of a 'task' arm, the last task of each sheet. The 7B
  constrained arms and the 27B checked arm marked "newline forced" carry it; the 27B and Gemma sheets carry
  it on 4 of 125 tasks, and those do not move either grammar arm (the 27B gets 12 of its 20 sheet-last
  answers right; Gemma's grammar arm is 52% with them and without them).
- **The 27B per-task comparison after the fix is one run** (n = 125 per arm).
- **The pick result is one judge pass** (n = 125, one per task), and the judge is the served 27B while the
  candidates come from the local nf4 run.
- **Two 4-bit schemes.** The GPU runs use bitsandbytes nf4, the MLX runs MLX 4-bit. Their free arms agree
  (1% each).
- **The 14B's re-parse is not the protocol** Claude was held to. Its sheet arm ran out of GPU memory
  (14.5 of 14.6 GiB) after one sheet, written in the same broken format, and is not counted.
- **Cost.** At batch size 1 on a T4 a token takes 0.1–0.25 s, more with a longer view; the 7B's five arms
  took about 8 hours on two T4s.
- **The scorer cut long masks at 80 characters, which ambmask rejects** (it reads 79). Until 2026-10-02,
  17 distinct right Haiku answers, mostly long residue lists for the membrane, scored "rejected"; 15 of them
  are exact. Every table above is rescored.
- One gold was wrong (`bnbs-trp-ring` omitted barstar's third Trp, which Sonnet included). It was fixed,
  and `report.py` rescores every stored mask against the current gold.
- Two Haiku calls came back with `num_turns` 2 and no tool use. With `--tools ""` no turn can read a
  file, so they were kept.
