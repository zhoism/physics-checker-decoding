# Mask bench: 125 realistic mask tasks, and what fixes a cheap model's failures

2026-10-02. This follows `masks_scout.md`. Its question: does a cheap model fail at least 20% of
realistic AMBER mask requests, and which fixes those failures: a grammar, grounding, or targeted
hints? 2026-10-03 adds decoding arms on an open 7B and 14B: is the checker better inside the decoder
or after it? 2026-10-04 adds Qwen3.8-27B and Gemma-4-31B, and 2026-10-05 Qwen3.5-122B-A10B: the
semi-reliable models where it could matter. The failure categories and their sources are in `mask_catalogue.md`. Tables:
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
| Qwen3.8-27B nf4 grammar v2, sheet (runs 0–2; all 5: 314/625 and 390/625) | 187/375 (50%) | – | 239/375 (64%) |
| Qwen3.8-27B nf4 grammar v2 + checker potential, sheet | 128/375 (34%) | – | 145/375 (39%) |
| Qwen3.8-27B picks among its 3 grammar v2 samples, shown their selections (`pick.py`) | 77/125 (62%) | – | – |
| Qwen3.8-27B nf4 grammar v2, one task per prompt (1 run, after the `qwen.Sheet` fix) | 46/125 (37%) | – | 62/125 (50%) |
| Qwen3.8-27B nf4 grammar v2 + checker potential, one task per prompt (1 run, after the fix) | 46/125 (37%) | – | 66/125 (53%) |
| Gemma-4-31B via OpenRouter, thinking off (3 runs) | 171/375 (46%) | 191/375 (51%) | 268/375 (71%) |
| Gemma-4-31B bf16 free, sheet (A100, 3 runs) | 172/375 (46%) | – | 278/375 (74%) |
| Gemma-4-31B bf16 grammar v2, sheet | 239/375 (64%) | – | 267/375 (71%) |
| Gemma-4-31B bf16 grammar v2, one task per prompt | 223/375 (59%) | – | 249/375 (66%) |
| Gemma-4-31B bf16 grammar v2 + checker potential, one task per prompt | 223/375 (59%) | – | 253/375 (67%) |
| Qwen3.5-122B-A10B fp8 free, sheet (H200, 3 runs) | 119/375 (32%) | – | 191/375 (51%) |
| Qwen3.5-122B-A10B fp8 grammar v2, sheet | 169/375 (45%) | – | 197/375 (53%) |

Held-out split, first try → after lint repair: Haiku view 73/123 (59%) → 111/123 (90%). Qwen 7B nf4:
free 2 → 3, grammar v1 14 → 23 (19%), grammar v2 15 → 19, checked 15 → 21, sheet 16 → 16 (of 123).
Qwen3.8-27B: OpenRouter 36 → 67, nf4 free 46 → 75, grammar v2 56 → 75 (runs 0–2), checked 36 → 43 (of 123).
Gemma-4-31B: OpenRouter 54 → 91, bf16 free 52 → 90, bf16 grammar v2 76 → 87 (of 123). The nf4 Gemma arms
and the per-task arms are in the Gemma section. Qwen3.5-122B-A10B: OpenRouter 13 → 22 (of 41), fp8 free
35 → 64, fp8 grammar v2 51 → 70 (of 123).

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

## Checker in the decoder or after it: the answer across three models

Decoded locally, 3 runs × 125 tasks each, sheet layout. The 27B's grammar rates are its runs 0–2, decoded
before the `qwen.Sheet` fix; Gemma's and the 122B's ran after it. The pick column is one judge pass.

| model | free, first try | grammar v2, first try | free + lint repair | grammar + lint repair | picks among 3 grammar samples |
|---|---|---|---|---|---|
| Qwen3.8-27B, nf4 (Kaggle) | 39% | 50% | 60% | 64% | 62% |
| Gemma-4-31B, bf16 (A100) | 46% | 64% | 74% | 71% | 66% |
| Qwen3.5-122B-A10B, fp8 (H200) | 32% | 45% | 51% | 53% | 54% |

- **Inside the decoder, the grammar raises the first try 11–18 points** on every model (pooled over 3 runs;
  higher in every run, by 6–18 points), with nothing added to the prompt and no second turn.
- **After the decoder, one lint repair reaches the same place** (within 4 points either way). The two do
  not add up: grammar + lint is not distinguishable from free + lint (+3.5, −2.9 and +1.6 points).
- **The grammar makes every remaining failure silent.** Free + lint leaves some masks pmemd would reject (5
  to 73 of 375); grammar + lint leaves none, and more valid masks on the wrong atoms.
- **A checker potential on finished masks** (ambmask must read the mask and select something) adds nothing
  over the grammar: 46 against 46 of 125 on the 27B and 223 against 223 of 375 on Gemma, one task per prompt.
  It strands masks whose conjunction already selects nothing.
- **A check that shows the selection, used to choose among 3 of the model's own grammar samples,** comes
  within 8 points of one repair without a repair turn, at the cost of 3 samples and one judge call that
  carries each candidate's selection (62% against 60–64% on the 27B, 66% against 71–74% on Gemma, 54%
  against 51–53% on the 122B). It leaves fewer silent failures than any grammar arm (22–26%, against 29–47%
  for grammar + lint), most clearly where the samples disagree; on the 27B, free + lint leaves fewer still
  (20%), plus 19% that pmemd would reject.

So the decoder is the place for the checker when the pipeline cannot spend a turn or context on it; given
a turn, after the decoder does as well, and some of the failures it leaves are ones pmemd rejects (5 to 73
of 375) rather than none, though most are silent either way. The lint repairs in this table were given only
to tasks the gold marked wrong, which a pipeline cannot do; the selection loop (its own section below)
needs no gold, shows every answer what it selects, and ends higher: 66%, 76% and 52% from the free first
try, and for Gemma 93% with its reasoning on for the check. Without that, none of these makes a
semi-reliable model reliable.

## Checker in the decoder or after it: Qwen 7B, 3 runs × 125

These arms ran before `qwen.Sheet` was fixed (2026-10-04): a constrained reply could end only after a
newline that followed its last mask, which pushed a model that wanted to stop toward the 79-character
cap (every answer in one task per prompt, the last of each sheet). The per-task arms were rerun after the
fix with the same seeds (`*_task_fixed.jsonl`; grammar v1 has 218 of 375 rows, when Kaggle's weekly
quota ran out) and barely moved: grammar v2 35 → 33, grammar v2 + checker 32 → 33 (still 76 stranded),
grammar v1 26 → 26 on the same 218 rows. Masks of 60 characters or more: 128 → 121 and 174 → 171. The 7B's
runaway masks are its own; the 27B's were mostly the newline (80 stranded → 17).

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
  They are not the forced newline: after the fix the arm strands the same 76, and the two arms tie at 33
  against 33, each right on 11 (run, task) pairs the other misses.
- **The checker after decoding works only on valid masks.** The lint repair takes free from 4 to 5, and
  the grammar arms up by 8 to 18 (best: grammar v1, 37 → 55, 15%). So the two combine, modestly: the
  grammar makes the masks AMBER, then the hints have something to act on.
- **v2 against v1: no difference.** v1 37, v2 35. The cap ended v1's runaway masks (96 of v1's first
  tries ran out of tokens, none of v2's) without changing accuracy. The sheet scored like one task per
  prompt (33 against 35), but every per-task answer carried the forced newline and only each sheet's
  last one did, so that comparison is confounded.
- **Picking among samples has little to pick from.** Under a grammar arm 16–20 tasks are right in at
  least one of the 3 runs (4–7 in all three), so choosing the right sample of 3 could add about 5 points.
- **The 14B does not follow the answer format.** It writes `===`, the id, then the mask on its own line
  in 368 of 375 replies, so the protocol's parser finds nothing (0/375). Re-parsed leniently (the line
  after the id), it gets 22/375 (6%) first try and 28 (7%) after lint: above the 7B free (4), far below
  Haiku (59%). A grammar would force the format; whether it also lifts the masks is untested.

**Answer.** For an open 7B, the checker inside the decoder (the grammar) beats the checker after it
(lint repair alone does nothing), but only on easy tasks. The checker potential on finished masks adds
nothing with one particle. The two combine to 11–15%. That is far from usable, and a 14B prompted alone
is not much better, so the model where decoding could matter is larger. (A rerun after the forced-newline
fix gives the same numbers.)

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
- **The layout matters about as much as the grammar.** Grammar v2 scores 46/125 (37%) one task per prompt
  (1 run, after the fix) and 314/625 (50%) in a sheet (5 runs of 58–71, before the fix): 13 points from
  one run, so the size is uncertain. A sheet is also one prompt per system instead of one per task.
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
  samples give 76/125: a right candidate is in 87 pools (4 more than with 3), and the judge gets 2 of those
  and loses 3 tasks it had right with 3 samples.
  What it still gets wrong is semantic: barstar's numbering gap (`:109-171`), `GLH` among the histidines.

**Answer for the 27B.** The grammar inside the decoder lifts the first try from 39% to 50%, consistently,
but after one repair the gain is 2–4 points, and it trades rejected masks for silent wrong ones. A checker
potential on finished masks adds nothing over the grammar. A check that shows the selection, used to
choose among the model's own samples, reaches the repair's accuracy and halves the silent failures that
remain. None of it makes the 27B reliable (Haiku is 59% → 88%).

**For the tool.** A model that does not know the language (the 7B) is not rescued by any of these. For
one that does (the 27B, Gemma), each placement buys something different: the grammar a first-try lift
(11–18 points) at no extra context, the lint hints the most accuracy given a repair turn (they fix the
rejected masks), and showing the selection NONE flags that turn some silent failures loud. Grounding
beyond a cpptraj listing showed no measurable value.

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

- **The local bf16 model reproduces the served one** (46% first try each). The nf4 run scored 5 points
  lower, and the grammar's lift was 11 points there against 18 in bf16. Both gaps are under the noise rule,
  and nf4 is confounded with the hardware (fp16 compute on T4s against bf16 on an A100) and with the
  forced newline (the nf4 sheets were decoded before the fix, the bf16 arms after).
- **In bf16 the grammar takes the first try from 46% to 64%**, in every run (56–59 → 78–82 of 125) and
  every system (bnbs 57 → 75, dna 60 → 74, memb 21 → 51, tryp 34 → 39); held-out 42% → 62%. That is
  Haiku's first try (59%), from an open 31B model in one call, with nothing added to the prompt.
- **After one lint repair the grammar adds nothing**: free 74%, grammar 71% (bf16); 68% and 65% (nf4).
  The free model's rejected masks are what the lint hints fix best, and the grammar has already spent
  them. Free + lint ends with 5 loud and 92 silent failures, grammar + lint with 0 loud and 108 silent.
- **One task per prompt costs Gemma less**: 59% against 64% in a sheet (3 runs each, both after the fix;
  73–75 against 78–82 per run), under the noise rule. The 27B's gap was 13 points.
- **The checker potential adds nothing here either** (one task per prompt, 3 runs): 223/375 first try, the
  same as grammar alone, and 253 against 249 after lint. Each is right on 10 of the 375 (run, task) pairs
  where the other is wrong. It turns 2 of
  the grammar's 14 empty selections into right answers, strands 12 masks at the cap
  (`:109-195&(:1-108@*)&(:1-108@*)&...`), and takes half again as long to decode (45 min against 30).
- **Picking among its own samples matches the repair without a turn** (`pick.py`, the served model as
  judge at temperature 0, the 3 bf16 grammar samples): 83/125 (66%; held-out 27/41), with 27 silent
  failures (22%) against 36% for one grammar sample and 29% after its lint repair. For 93 of 125 tasks the
  samples select the same atoms, so pick mostly accepts or flags: a right candidate was there for 85 and
  picked in 83; with none (40) it said NONE 10 times. On the nf4 samples (oracle 70) it scored 68/125,
  with 4 of its replies misread by the old parser (it matched the article "a"; fixed, and rescored with
  the fix the 27B and Ultra passes are unchanged).

**Answer for Gemma.** The grammar inside the decoder makes this 31B model's first try as good as Haiku's,
in one call with no repair turn and no extra context, which is where the grammar earns its place in a
pipeline. Given a turn, the checker after decoding gets the most right (free + lint repair, 74%), and a
check that shows the selection, choosing among 3 grammar samples, leaves the fewest silent failures
(22%, against 25% for free + lint). Either way about a quarter of the masks are still wrong.

## Qwen3.5-122B-A10B: one size up, decoded

The ladder's 122B (34% first try by API, one run; an older generation than Qwen3.8-27B, 10B of its 122B
parameters active). bitsandbytes cannot pack its experts (3D tensors, not Linear layers), so it ran from
Qwen's own FP8 checkpoint on one H200 (Modal, 115 GiB loaded): sheet layout, 3 runs × 125, after the fix.

| Qwen3.5-122B-A10B | first try | + lint repair | first tries ambmask rejects | silent failures after lint | held-out, first → lint |
|---|---|---|---|---|---|
| free, OpenRouter (1 run × 125) | 42 (34%) | 60 (48%) | 50 | 36 | 13 → 22 of 41 |
| free, fp8 (3 runs × 125) | 119 (32%) | 191 (51%) | 125 | 124 | 35 → 64 of 123 |
| grammar v2, fp8 | 169 (45%) | 197 (53%) | 0 | 178 | 51 → 70 of 123 |
| picks among its 3 grammar samples (`pick.py`, the served 122B judging) | 67/125 (54%) | – | – | 32 | 22 of 41 |

- **The local FP8 model matches the served one** (32% against 34% first try).
- **The grammar raises the first try 13 points** (32% → 45%), in every run (31/44/44 → 51/57/61) and every
  system (bnbs 34 → 45, dna 43 → 58, memb 22 → 29, tryp 20 → 37); held-out 28% → 41%.
- **After one lint repair the grammar adds nothing**: 51% free, 53% grammar. Free + lint leaves 60 loud and 124
  silent failures, grammar + lint 0 loud and 178 silent.
- **Some of its free failures are another tool's syntax**: 19 of its 125 rejected first tries use `around` or
  `within` (VMD-style distance: `around 5.0 :102`), which the grammar removes. Lint repaired none of the 19;
  of the 31 rejected distance-task masks it fixed one.
- **Picking among its own samples does as well as a repair**: 67/125 (54%) against 51–53%, one judge pass,
  with 26% silent. Its samples disagree more than Gemma's (56 of 125 pools hold one distinct selection,
  against 95), so there is more to choose from. A right
  candidate was there for 70 tasks and was picked in 67; with none (55) it said NONE 24 times.

**Answer for the 122B.** The same pattern as the 27B and Gemma, on a weaker model: the grammar lifts the
first try 13 points, one repair catches up, and choosing among samples with the selection shown does as
well as a repair (54%) with the fewest silent failures (26%). About half its masks are still wrong.

## The selection loop: a check that needs no answer key

Every repair above was given only to the tasks the gold marked wrong, and for a valid mask its message
("check that these are the atoms the task asks for") said so. A pipeline cannot single tasks out that way:
it can only see that ambmask rejects a mask. Repairing only those, free + lint is 54% (27B), 66% (Gemma)
and 44% (122B), against 60%, 74% and 51% with the gold choosing; with the grammar nothing is rejected, so
nothing gets a repair. `verify.py` is the check a pipeline could run. Every answer, right or wrong, is shown
what it selects (`pick.card`: the atom count, residues and atom names, or ambmask's rejection) with lint's
hints, and the model answers KEEP or a corrected mask; corrections are shown again, up to 3 rounds. The
first tries are the local ones (3 runs × 125); the loop is the served model at temperature 0.7.

| model | free first try → + loop | grammar first try → + loop | free + lint, gold-chosen / rejected only | broke a right mask |
|---|---|---|---|---|
| Qwen3.8-27B | 39% → 66% (247/375) | 50% → 65% (244) | 60% / 54% | 0, 0 |
| Gemma-4-31B | 46% → 76% (286) | 64% → 73% (275) | 74% / 66% | 0, 0 |
| Qwen3.5-122B-A10B | 32% → 52% (194) | 45% → 53% (199) | 51% / 44% | 2, 3 |

- **The loop matches or beats the gold-chosen repair on every model, without the gold**, and almost never
  breaks a right mask. Most of the gain comes in the first round (Gemma free 172 → 269 → 285 → 286); the
  27B is still rising at round 3 (205 → 230 → 247).
- **It fixes some silent failures, not only syntax.** From Gemma's free start it fixed 72 of 104 rejected
  masks and 42 of 99 valid wrong or empty ones; from its grammar start, 36 of 136 (the gold-chosen repair
  fixed 32 and 28). What it keeps wrong is mostly numbering and protonation: lists of residue numbers the
  selection does not show to be wrong (`:57,85&@NE,NH1,NH2` for Arg83 and Arg87).
- **Decoding and the loop do not stack.** From the grammar's start the loop ends 3 points lower on Gemma and
  the 27B and 1 higher on the 122B: the loop recovers the grammar's syntax gain, and a valid wrong mask is
  harder to doubt than a rejected one (81 of Gemma's grammar-start wrong answers were kept unchanged,
  45 of its free-start ones).
- **What is left after the loop is partly loud.** Its corrections are not held to the grammar, and 72 of
  the 27B's free-start masks and 41 of the 122B's end rejected (Gemma's: 4).
- **Showing PDB numbers and running 5 rounds add a few points at most.** `--pdb` adds each selected
  residue's PDB number to the card, which makes a numbering error visible (`:57,85` for Arg83 and Arg87
  now reads "ARG 57 (PDB A:59) … ARG 85 (PDB A:87)"). With it and 5 rounds: Gemma 286 and 278 (from 286
  and 275), the 122B 198 and 202 (from 194 and 199). The 27B's runs moved to OpenRouter's paid endpoint
  (its free one was withdrawn); there, with 5 rounds, the plain card gives 259 and 249 and the PDB card 283
  and 256, but 8 of the +24 are lipid tasks, where the two cards are identical: run-to-run noise of that
  size. Rounds 4 and 5 add 0–16 (the most on the 27B, still rising at round 3). What stays wrong is mostly kept, not miscorrected: asked for Arg83 and
  Arg87, Gemma keeps `:57,81` though the card says it selects Arg59 and Arg83. The model has the
  information and does not compare it with the task.
- **With reasoning on for the check, Gemma reaches 93% without the gold** (`--think`; the first tries are
  still the local ones, reasoning off). From the free start 172 → 334 → 345 → 347 of 375 (93%), from the
  grammar start 239 → 340 (91%), against 286 and 275 with reasoning off. It broke 1 right mask; 28 and 33
  silent failures remain, and none rejected from the free start. Numbering tasks go from 17 to 47 of 57,
  and masks left wrong and unchanged from 45 to 16. Reasoning alone does not do it: Gemma's first try with
  reasoning on (`blind.py openrouter-think:`, the same protocol, 3 runs) is 241/375 (64%), and its
  gold-chosen lint repair 335 (89%). Haiku's view arm is 59% first try and 88% after the gold-chosen
  repair. Gemma's reasoning costs little ($0.004 a sheet, about 6k tokens); the 27B's
  ran to 41k tokens and $0.13 a sheet. Both Gemma arms cost $0.52.
- **The control: it is the hints and ambmask's verdict, not a second pass, and not the selection summary.**
  Same first tries, reasoning on, 3 rounds, each answer shown alone (`verify.py --show=none`) or with lint's
  hints but not what it selects (`--show=hints`):

  | each answer shown with | right after the loop | rejected first try fixed (of 104) | valid wrong first try fixed (of 99) | rejected / silent after |
  |---|---|---|---|---|
  | nothing: a second pass | 213 (57%) | 0 | 44 | 117 / 45 |
  | lint's hints | 320 (85%) | 66 | 84 | 24 / 31 |
  | hints and what it selects | 347 (93%) | 95 | 81 | 0 / 28 |

  A second pass alone fixes none of the rejected masks: the model cannot see its own syntax errors. The hints
  give most of the gain, and on valid but wrong masks as much as the full card (84 against 81). What the
  selection summary adds is the rejected masks it reports as rejected; numbering, where it should help most,
  is 44, 52 and 47 of 57 (reasoning alone does most of it). Untested: hints plus only ambmask's accept or
  reject. One loop per arm; the card-to-hints gap is 7 points overall but 29 of the 104 rejected masks. The two
  controls cost $0.23.
- **The 122B's and 27B's reasoning loops are partial** (`*_verify_free_think.jsonl`): the OpenRouter key's
  $5 limit stopped 6 of each one's 12 sheets. The 122B still reached 236/375 (63%) from its free start,
  against 194 with reasoning off; the 27B's 167 is not a result (4 sheets never checked). `verify.py`
  resumes them, rerunning only the stopped sheets.

## Think, then answer: the grammar after reasoning

Reasoning fixes meaning but not syntax (Gemma's first try with reasoning on is 64% right and 22% rejected);
the grammar fixes syntax but not meaning. `think.py` tests whether they stack: Gemma-4-31B (bf16, one A100 on
Modal) reasons freely over a whole sheet in its thinking mode, and from that same reasoning the answer is
decoded twice, free and held to grammar v2, so each pair shares its thought. The run stopped at 307 of 375
rows (trypsin runs 1 and 2 missing): reasoning ran at about 8.5 tokens a second, 9k tokens a large sheet.

| Gemma-4-31B, same reasoning, 10 sheets | right | rejected | valid but wrong or empty |
|---|---|---|---|
| answer decoded free | 197/307 (64%) | 82 | 28 |
| answer held to grammar v2 | 206/307 (67%) | 0 | 101 |

- **The local reasoning matches the served one**: 197 against 196 of the same 307 for the OpenRouter run with
  reasoning on.
- **The grammar after reasoning adds a little, and only in one direction**: right where free was wrong on 9
  tasks, wrong where free was right on none. 3 points, under the noise rule, but a 9-to-0 split.
- **Mostly it converts loud failures into silent ones.** Of the 82 free answers ambmask rejects, the grammar
  makes 8 right, 66 valid masks on the wrong atoms and 8 that select nothing: the syntax it forces does not
  carry the meaning the reasoning was after.

So decoding stacks with reasoning only weakly. Its value stays where the earlier sections put it: a first
try with no reasoning and no second turn.

## The recipe as a tool: `masks/mask_tool.py`

The 93% recipe for any AMBER system: a prmtop, an inpcrd (NetCDF is converted) and plain-English requests in;
Gemma's first try (reasoning off), then the selection loop (reasoning on, 3 rounds); each mask out with what it
selects and whether the model kept it. Its prompts are the bench's (`tests/test_mask_tool.py` replays the 93%
run through it and gets that run's masks).

On a system it had never seen (ubiquitin, 1UBQ, ff14SB in implicit solvent, no water), 12 new requests with
references checked in ambmask, 3 runs (`google/gemma-4-31b-it` on OpenRouter; `masks/ubq/`, the table is
`check.py --score`):

| | right | of 36 |
|---|---|---|
| first try | 27 | 75% |
| after the loop | 35 | 97% |

- The loop fixed `@H*` → `@H=` (every run), an invented distance syntax (`.within=6.0`, `%6`) → `<:6.0` in 2
  of 3 runs, and Ile44's side-chain hydrogens. The miss is that distance request in the third run: its
  last correction selects nothing, and the output says so ("selects no atoms", "corrected in round 3, not
  checked again"). It is loud, not silent.
- These requests are easier than the bench (first try 75% here against 46% there), and n is 36 from 12
  requests: a check that the tool works on a new system, not a second measurement of the 93%.
- A run costs under a cent and 4–8 minutes (reasoning rounds of 30–270 s).
- The first live run scored 0: with numbered tasks Gemma writes `=== TASK 1 ===`, which `blind.parse` does not
  read. The tool now reads both. The same headers appear in one round of the 122B's reasoning loop (bnbs run 1,
  round 3): 9 answers counted as no answer, 3 of them corrections, so at most 3 of its partial 236/375 move.

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
  a newline before its reply could end: all of a 'task' arm, the last task of each sheet. Before the fix:
  the 7B constrained arms (its per-task arms rerun after it: no change), the 27B checked arm marked
  "newline forced", all 5 of the 27B's grammar sheets
  and Gemma's nf4 sheets. After it: the 27B per-task pair, every Gemma bf16 arm and the 122B (bundle
  commits in the run logs). On the sheets it acted on 4 of 125 tasks: 8 of the 27B's 20 sheet-last masks run to 76–79
  characters (`bnbs-hg-wildcard` hits 79 in all 5 runs). The rates barely move without those tasks (27B
  50.2% against 49.9%; Gemma nf4 52.0% against 52.1%).
- **The 27B per-task comparison after the fix is one run** (n = 125 per arm).
- **Spend.** Modal's $30 monthly credit ran out during the think.py run, which went 6.7 hours against an
  estimate of 1–2, and $1.25 was billed past the workspace's $0 spend limit before the run was cancelled.
- **Each pick result is one judge pass** (n = 125, one per task). The judges are served models (27B,
  Ultra, Gemma, 122B); the Ultra's candidates are its own served samples, the others' come from local runs.
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
