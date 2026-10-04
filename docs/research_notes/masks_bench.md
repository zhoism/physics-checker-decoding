# Mask bench: 125 realistic mask tasks, and what fixes a cheap model's failures

2026-10-02. This follows `masks_scout.md`. Its question: does a cheap model fail at least 20% of
realistic AMBER mask requests, and which fixes those failures: a grammar, grounding, or targeted
hints? 2026-10-03 adds decoding arms on an open 7B and 14B: is the checker better inside the decoder
or after it? The failure categories and their sources are in `mask_catalogue.md`. Tables:
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

Held-out split, first try → after lint repair: Haiku view 73/123 (59%) → 111/123 (90%). Qwen 7B nf4:
free 2 → 3, grammar v1 14 → 23 (19%), grammar v2 15 → 19, checked 15 → 21, sheet 16 → 16 (of 123).
Qwen3.8-27B: OpenRouter 36 → 67, nf4 free 46 → 75, grammar v2 56 → 75, checked 36 → 43 (of 123).

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
  52 → 53). One trypsin sheet (5 → 19) is 14 of the 40. Held-out: 37% → 46%.
- **After one lint repair the grammar barely matters**: 226 → 239 (60% → 64%), and 75 → 75 held out. The
  checker after decoding recovers most of what the checker inside recovers; the grammar saves the turn.
- **The grammar turns loud failures into silent ones.** Free, 154 first tries are masks ambmask rejects
  (pmemd would stop) and 74 are valid but wrong or empty. Under the grammar none is rejected and 188 are
  valid but wrong or empty. After the lint repair: free leaves 73 loud and 76 silent failures, grammar v2
  0 loud and 136 silent. In a pipeline, where a rejected mask stops the run and a wrong one does not,
  that is a cost.
- **The checker potential in the sheet layout fails for a layout reason.** When it strands a mask at the
  79-character cap (no way to finish selects atoms), the one particle dies and takes the rest of the sheet
  with it: 177 of 375 tasks never answered, every trypsin sheet among them. One task per prompt would
  confine a stranding to its task; that arm has not been run on the 27B.
- **Picking among samples has room here.** 83 of 125 tasks are right in at least one of the 3 grammar
  runs (44 in all three), against 50% per run; after lint, 99. On the 7B it was 16–20.
- **The served model and the local one differ.** Free, OpenRouter's bf16 scored 28% and the local nf4
  39%, with OpenRouter's runs at 25, 30 and 49 of 125. Decoding arms are compared with the local free arm.

- **Showing the selection and letting the model pick does best** (`pick.py`). For each task the candidates
  are the distinct selections among the grammar arm's 3 samples, each shown with what ambmask selects
  (atom count, residues, atom names); the 27B (OpenRouter, temperature 0) answers a letter or NONE. It is
  right on 77/125 (62%; held-out 24/41), says NONE on 19 and picks a wrong candidate on 29. Against one
  grammar sample (50% right, 50% silent) and grammar plus lint repair (64% right, 36% silent), it matches
  the repair without a repair turn and cuts silent failures to 23%. With a right candidate in the pool
  (83 tasks) it picked it 77 times; with none (42) it said NONE 17 times. Adding the free arm's samples
  (up to 6 candidates) gives 76/125: the right answer was already among the grammar samples. What it
  still gets wrong is semantic: barstar's numbering gap (`:109-171`), `GLH` among the histidines.

**Answer for the 27B.** The checker inside the decoder lifts the first try from 39% to 50%, consistently,
but after one repair the gain is 4 points, and it trades rejected masks for silent wrong ones. A check that
shows the selection, used to choose among the model's own samples, reaches the repair's accuracy and
halves the silent failures that remain. None of it makes the 27B reliable (Haiku is 59% → 88%).

**For the tool.** The order of value for a cheap model is a checker that shows the selection, then
system-aware hints, then a grammar. Grounding beyond a cpptraj listing showed no measurable value. A
grammar alone does not rescue an open 7B model on realistic tasks.

## Caveats

- **Sheets cluster.** A model's failures move together within one sheet (one system, one sample), so
  the effective sample is about 12 sheets per Haiku arm, not 375 tasks. Gaps under about 10 points
  are not established.
- **The held-out split is not clean for lint.** The smoke run that suggested three of v1's hints
  covered both splits, and v2 was written after the full run.
- **The MLX Qwen grammar arm is one sheet.** It was stopped because Qwen 7B with 10–12k-token prompts
  filled the laptop's RAM and swap (DEVLOG `watch:`). The free arm ran 2 of 3 planned runs.
- **report.py rescores every stored mask with ambmask on each run**, now about 10 minutes.
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
