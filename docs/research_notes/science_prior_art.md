# Constrained / checker-guided decoding for scientific and physics outputs: prior art (as of 2026-09)

Scope: judge novelty of (A) physics-checker-guided SMC decoding of simulation input files (AMBER mdin, LAMMPS, OpenFOAM, GROMACS mdp) versus generate-verify-repair, and (B) units-checked decoding of physics code/equations. Search budget was about 16 queries/fetches; "not found" below means "searched with the stated phrasings and not found", never "confirmed absent".

## Q1. LLM agents for simulation setup outside MD: constrained decoding or post-hoc repair?

### Takeaway
Every simulation-setup agent found (MetaOpenFOAM, OpenFOAMGPT, Foam-Agent, ChatCFD, PhyNiKCE, SIGA, the LAMMPS evaluation work, MDCrow, MDArena) validates **after** generation: validator/solver error → LLM repair loop, or validator as an agent-callable tool / termination gate. None found puts a domain validator inside the decoder (token masking, SMC potential, or reweighting). The closest is PhyNiKCE, which treats setup as a constraint-satisfaction problem, but it validates LLM-proposed parameters after they are proposed and does not constrain decoding.

### Cited Findings
- MetaOpenFOAM: multi-agent LLM framework that takes a natural-language requirement, generates OpenFOAM input files, runs OpenFOAM and returns results. Output format is constrained through the system prompt, not through the decoder. — [MetaOpenFOAM, arXiv 2407.21320](https://arxiv.org/pdf/2407.21320)
- Foam-Agent: end-to-end OpenFOAM automation from one prompt. It has an iterative review-and-correction loop framed as "find the minimal set of file changes that removes errors", repeated up to a user-set limit. Reported executable success is 83.6% (Claude 3.5 Sonnet) against 55.5% for MetaOpenFOAM and 37.3% for OpenFOAMGPT-Alt. Removing error correction causes a 55.4% relative drop, so the repair loop is the component that matters most. — [Foam-Agent, arXiv 2505.04997](https://arxiv.org/html/2505.04997); Foam-Agent 2.0 — [arXiv 2509.18178](https://arxiv.org/pdf/2509.18178)
- OpenFOAMGPT (RAG agent) and OpenFOAMGPT 2.0 ("end-to-end, trustworthy automation") — [ResearchGate](https://www.researchgate.net/publication/389557078_OpenFOAMGPT_A_retrieval-augmented_large_language_model_LLM_agent_for_OpenFOAM-based_computational_fluid_dynamics); [arXiv 2504.19338](https://arxiv.org/pdf/2504.19338)
- ChatCFD: planner / case-setup / runner / debugger agents with a literature-grounded knowledge base on OpenFOAM v2406. The debugger agent means post-hoc repair. — [CFD coding-agent assessment, arXiv 2602.11689](https://arxiv.org/html/2602.11689v1) (search snippet)
- **PhyNiKCE** (nearest neighbour for A on the "deterministic physics rules" side): neurosymbolic CFD agent that "decouples neural planning from symbolic validation". A Symbolic Knowledge Engine treats simulation setup as a Constraint Satisfaction Problem, and a Deterministic RAG Engine "queries these constraints to validate the LLM-generated simulation parameters". Reported: 96% relative improvement over SOTA baselines on non-tutorial OpenFOAM tasks with Gemini-2.5-Pro/Flash, 59% fewer self-correction loops, 17% fewer tokens. — [PhyNiKCE, arXiv 2602.11666](https://arxiv.org/html/2602.11666)
- **SIGA** (Ho, Liu, Chen, Wang, Qin; June 2026): coding-agent adapters for GEOS, OpenFOAM and LAMMPS. The validators are XML-schema checks (GEOS), required-file and dictionary checks (OpenFOAM), and command / reference / force-field / run-control checks (LAMMPS). They are "agent-callable" mid-trajectory, and validation is a mandatory termination condition ("validation-gated termination"). The agent loop itself is unmodified, with no decode-time constraint. GEOS TreeSim improved from 0.720 to 0.789 on harder held-out problems. — [SIGA, arXiv 2606.09774](https://arxiv.org/abs/2606.09774)
- **LAMMPS evaluation** (Holbrook, Verduzco, Strachan; Mar 2026): pipeline of normalization to canonical input, an extensible parser (a lammps-ast-style typed AST) for syntax and semantic checks, a reduced-cost execution stage, then accuracy checks. Eight LLMs, three prompts of increasing complexity. The parser pass rate rose from 74% to 91% over a year, but only 1 of 80 scripts on the hardest prompt was fully correct. Packaged as an "agentic skill" the LLM can invoke during generation, which gave 5 of 6 fully correct. This is post-hoc and tool-invoked, not a decoding constraint. — [arXiv 2603.20630](https://arxiv.org/abs/2603.20630)
- Other simulation-input agents and benchmarks: MDAgent2 / MD-EvalBench (LAMMPS code generation and Q&A) — [arXiv 2601.02075](https://arxiv.org/pdf/2601.02075); PHITSBench (radiation-transport input decks, execution-scored) — [arXiv 2607.09789](https://arxiv.org/pdf/2607.09789); AutoMOOSE (phase-field) — [arXiv 2603.20986](https://arxiv.org/pdf/2603.20986); agentic atomistic orchestration — [arXiv 2607.22596](https://arxiv.org/pdf/2607.22596), [arXiv 2606.09422](https://arxiv.org/pdf/2606.09422); "What do CAE simulation agents need beyond a generic harness" — [arXiv 2609.03718](https://arxiv.org/pdf/2609.03718)
- MD prior art: MDCrow (40+ tools, 25 MD tasks, GROMACS/OpenMM-style protein workflows) — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13033927/); MDGym (GROMACS and LAMMPS agent benchmark) — [arXiv 2605.08941](https://arxiv.org/html/2605.08941); MDArena (July 2026; 50 containerized tasks, 29 systems, 14 protocols; best config 24/50 Strict-Pass@1; agents "fail on the fine-grained details required for reproducible scientific workflows"; the abstract names no constrained generation) — [arXiv 2608.02642](https://arxiv.org/abs/2608.02642); MDDataBench — [GitHub](https://github.com/matsunagalab/MDDataBench)

### Inferences
- The field's default architecture is generate → run/validate → LLM repair. PhyNiKCE and SIGA move the deterministic validator earlier (pre-execution, agent-callable), but still work at whole-file or parameter-set granularity after generation. That makes "validator as an SMC potential at decode time" a real methodological gap in this niche.
- MDArena's finding that agents fail on "fine-grained details" and the LAMMPS finding (91% parse-valid but 1/80 fully correct) together suggest syntax is nearly solved. Cross-field semantic and physics validity is where a decode-time physics potential would have headroom. This is inference, not measured.

### Gaps
- Full texts of PhyNiKCE and ChatCFD were not read. It is unverified whether either uses logit masking or constrained sampling internally. The abstracts describe validation, not decoding.
- FoamGPT (fine-tuned) was only seen as a title; its decoding strategy is unchecked.

## Q2. Constrained generation elsewhere in science (SMILES/SELFIES, CIF/crystals, SMC, formal math)

### Takeaway
Decode-time constraints on scientific strings are well established for **molecules** (grammar and valence, and RDKit as an SMC potential in Loula et al.) and there is a general SMC framework (GenLM, ICLR 2025 oral) built for exactly "checker as potential". Crystal LLMs mostly rely on post-hoc validity filters or MCTS with a learned energy predictor. So the *method* in (A) is established. What is new in (A) is the *domain* (simulation input decks with cross-field physics rules) and the head-to-head against repair loops.

### Cited Findings
- **Loula et al., "Syntactic and Semantic Control of LLMs via SMC"** (ICLR 2025 oral; with Lew, Vieira, O'Donnell, Mansinghka and others): SMC architecture for constrained generation that "can integrate constraints that cannot be incrementally evaluated over the entire token vocabulary, as well as constraints that can only be evaluated at irregular intervals", with user-defined proposals and potentials. Domains: Python data-science code, text-to-SQL, goal inference, **molecule synthesis**. Small open models beat models more than 8× larger. — [arXiv 2504.13139](https://arxiv.org/abs/2504.13139); [GenLM publications](https://genlm.org/publications/)
- Self-distilled twisted SMC for constrained generation — [arXiv 2507.02315](https://arxiv.org/html/2507.02315v1)
- "How to make LLMs generate 100% valid molecules?" (EMNLP 2025): grammar processor applied every decoding step plus a token allowlist. It notes constrained decoding raises validity but "significantly lowers other metrics", a quality-versus-validity tradeoff that (A) must measure. — [arXiv 2509.23099](https://arxiv.org/pdf/2509.23099)
- SMolLM (small LMs learn molecular grammar) — [arXiv 2605.06322](https://arxiv.org/html/2605.06322v1); CFG-constrained decoding of diffusion LLMs — [arXiv 2508.10111](https://arxiv.org/pdf/2508.10111); Constrained Adaptive Rejection Sampling — [arXiv 2510.01902](https://arxiv.org/pdf/2510.01902)
- CrystaLLM: autoregressive LLM over CIF text, sampling improved by MCTS guided by a pretrained GNN formation-energy predictor (a guided search, not a hard validity constraint). — [Nature Comms 2024](https://www.nature.com/articles/s41467-024-54639-7). CrysText: Llama-3.1-8B QLoRA, text-conditioned CIF — [Springer](https://link.springer.com/article/10.1007/s40192-026-00451-8). Review reports about 53% symmetry-valid structures in one LLM study — [npj Comp Mat review](https://www.nature.com/articles/s41524-025-01881-2) (search snippet, study not identified)
- Type-constrained decoding (Mündler et al., PLDI 2025, ETH SRI): prefix automata plus type-inhabitation search enforce well-typedness during decoding for a TypeScript subset. Compilation errors fall by more than half on HumanEval/MBPP. About 94% of TS compile errors are type errors, not syntax. — [arXiv 2504.09246](https://arxiv.org/pdf/2504.09246); [code](https://github.com/eth-sri/type-constrained-code-generation)
- Grammar-constrained decoding for DSLs: Grammar Prompting — [arXiv 2305.19234](https://arxiv.org/pdf/2305.19234); flexible GCD — [arXiv 2502.05111](https://arxiv.org/pdf/2502.05111), [arXiv 2305.13971](https://arxiv.org/abs/2305.13971)

### Inferences
- For (A), GenLM/Loula et al. is the infrastructure to build on and the obvious citation. The contribution must be the physics-validator potential over a config DSL plus the comparison against repair, not "SMC for constrained generation".
- Physics cross-field rules (e.g. dt vs SHAKE) are exactly the "evaluable only at irregular intervals" constraint type Loula et al. handle. A key-value config is only checkable once both fields are emitted, which favours SMC over token masking. This is an inference from the paper's framing.

### Gaps
- Lean/formal-math checker-in-the-loop decoding was not searched in this budget. It is known prior art in general, but no sources are collected here.
- Not checked whether any GenLM follow-up (2025–26) targets scientific config files.

## Q3. LLMs and physical units: benchmarks, and units-aware decoding

### Takeaway
Unit errors are a recognised, tracked LLM failure mode, and at least one benchmark paper explicitly *recommends* embedding dimension/unit checks into decoding. The strongest decode-time precedent is **PhySO**, which enforces dimensional analysis as a live token prior during sequential equation generation. But PhySO is an RL symbolic-regression policy, not an LLM, and its token vocabulary is an expression DSL. No paper was found that applies a units checker (pint, astropy.units, Unitful, F# UoM) as a decode-time constraint on **LLM**-generated code or equations.

### Cited Findings
- **PhySO / Φ-SO** (Tenachi et al.): "constraining the automatic sequential generation of equations to obey the rules of dimensional analysis by construction". `PhysicalUnitsPrior` makes "the next token … physically consistent units-wise with the current program based on current units constraints computed live during program generation". SOTA on SRBench Feynman under noise. — [arXiv 2303.03192](https://arxiv.org/pdf/2303.03192); [arXiv 2312.03612](https://arxiv.org/abs/2312.03612); [docs](https://physo.readthedocs.io/en/latest/r_features.html); [GitHub](https://github.com/WassimTenachi/PhySO)
- CMPhysBench (520 graduate condensed-matter calculation problems) recommends "embedding physics-aware verification into decoding, including dimension/unit checks and conservation laws". This is a suggestion, not an implementation. — [arXiv 2508.18124](https://arxiv.org/pdf/2508.18124)
- "Can theoretical physics research benefit from language agents?" names dimensional-consistency checking as a needed guard (position paper). — [arXiv 2506.06214](https://arxiv.org/pdf/2506.06214)
- GeoMCP: constrained symbolic engine that executes geotechnical methods "with verified dimensional consistency", because LLMs hallucinate formulas and units. This is tool execution, not decoding. — [arXiv 2603.01022](https://arxiv.org/html/2603.01022v1)
- Lean4PHYS / LeanPhysBench: a Lean4 UnitSystem with dimension transformation and 200 hand-written physics theorems. It is a formal units type system usable as a checker. — [arXiv 2510.26094](https://arxiv.org/html/2510.26094v1)
- Unit errors as a benchmark error category: "Unit Error: dimensional inconsistency or incorrect unit conversion" in recent physics benchmarks — [search result, TPS-CalcBench arXiv 2604.17966](https://arxiv.org/pdf/2604.17966) (attribution from snippet; not verified which paper holds the taxonomy). A blog reports 0% on a Bernoulli task because of Pa/atm confusion and notes Sympy+Pint can localise errors — [DEV Community](https://dev.to/valesys/improving-llm-accuracy-in-physics-addressing-incorrect-and-inconsistent-responses-for-reliable-302e) (low-quality source).
- Physical-units type-checking as PL work (non-LLM): Osprey (units for C) and a pluggable kind-of-quantity type checker — [Springer 2025](https://link.springer.com/chapter/10.1007/978-3-031-96841-9_8)
- Units libraries: [pint](https://github.com/hgrecco/pint), [astropy.units](https://docs.astropy.org/en/stable/units/). A search for "units-aware LLM code generation pint astropy" returned no LLM-decoding papers. — [search result set](https://xarray.dev/blog/introducing-pint-xarray)

### Inferences
- (B) splits into two very different projects. (B1) Units-constrained decoding of **equations/expressions** is close to PhySO; the delta is "LLM plus natural-language context" rather than an RL policy. (B2) Units-constrained decoding of **general Python code** (pint/astropy) looks open, but it is technically hard. Python units are dynamic (runtime-checked), so a static prefix checker needs either a typed units DSL, F#/Unitful-style static units, or SMC with partial-execution potentials. Mündler et al.'s type-constrained decoding is the method template: units are a type system.
- The Mündler finding that most compile errors are type errors suggests a measurable analogue: what fraction of SciCode-style physics failures are unit errors? No such measurement was found.

### Gaps
- UGPhysics and PhysicsEval were not located in this search budget. Their unit-error statistics are unverified.
- No explicit search was run on F# units-of-measure or Unitful.jl with LLMs. "Searched and not found" covers only the pint/astropy and general "units LLM decoding" phrasings.

## Q4. (A) Corpora of real simulation input files and existing deterministic validators

### Takeaway
OpenFOAM has the richest ready-made task sets (FoamBench, NL2FOAM with 28,716 pairs, CFDLLMBench). LAMMPS has a curated tutorial set and a published parser/evaluation pipeline. MD benchmarks exist (MDArena, MDGym, MD-EvalBench, MDDataBench). No public AMBER-mdin corpus or cross-field AMBER physics validator was found. This project's `md-param-check` would be a novel artefact there.

### Cited Findings
- FoamBench: Basic split from OpenFOAM tutorial cases plus an Advanced split of 16 expert-authored cases; part of CFDLLMBench (CFDQuery, CFDCodeBench, FoamBench). — [arXiv 2509.20374](https://arxiv.org/pdf/2509.20374); [GitHub](https://github.com/NLR-Theseus/cfdllmbench)
- NL2FOAM: 28,716 NL-description to OpenFOAM-config pairs with CoT annotations, used to fine-tune Qwen2.5-7B. — [search snippet via FoamGPT/AutoCFD](https://github.com/YYgroup/AutoCFD)
- LAMMPS tutorial set (LAMMPS tutorials article v1.0) — [arXiv 2503.14020](https://arxiv.org/html/2503.14020v1); LAMMPS benchmark inputs — [lammps.org/bench](https://www.lammps.org/bench.html); LAMMPS AST parser and normalization pipeline — [arXiv 2603.20630](https://arxiv.org/abs/2603.20630)
- Validators already built: SIGA's per-simulator validators (GEOS XML schema, OpenFOAM dictionary/required-file checks, LAMMPS command/force-field/run-control checks) — [arXiv 2606.09774](https://arxiv.org/abs/2606.09774); PhyNiKCE's symbolic constraint KB for OpenFOAM — [arXiv 2602.11666](https://arxiv.org/html/2602.11666); "Model Input Verification of Large Scale Simulations" (non-LLM input verification) — [arXiv 2409.05768](https://arxiv.org/pdf/2409.05768)
- MD task sets: MDArena 50 tasks — [arXiv 2608.02642](https://arxiv.org/abs/2608.02642); MDGym — [arXiv 2605.08941](https://arxiv.org/html/2605.08941); MD-EvalBench — [arXiv 2601.02075](https://arxiv.org/pdf/2601.02075); PHITSBench — [arXiv 2607.09789](https://arxiv.org/pdf/2607.09789)

### Inferences
- The best testbed for (A) is probably OpenFOAM (FoamBench / NL2FOAM plus the SIGA/PhyNiKCE-style dictionary rules), with LAMMPS second (the Holbrook parser plus tutorials). There, the repair-loop baselines (Foam-Agent, MetaOpenFOAM) are published and reproducible, so "SMC-with-validator vs generate-verify-repair" has a real comparator.
- AMBER mdin is a thin testbed: no public corpus was found. The mdin grammar is Fortran namelist, and cross-field rules such as `dt` ≤ 0.002 with `ntc/ntf=2`, and the thermostat settings, are exactly the rule type in question. It would be a strong illustrative domain but would need a self-built task set (AMBER tutorials, GitHub mining).
- GROMACS `grompp` is itself a deterministic cross-field validator, and plausibly the cheapest ready-made potential. This comes from domain knowledge; I have no source for its specific timestep/constraint warnings.

### Gaps
- No GitHub-mined corpus of AMBER mdin or GROMACS mdp files was found. Unverified whether one exists.
- The exact grompp checks were not verified from the GROMACS docs.

## Q5. (B) Benchmarks with checkable physics coding answers

### Takeaway
SciCode is the main usable one (80 problems, 338 subproblems, scientist-written tests, 16 subdomains). FEM-Bench (33 tasks) and CFDCodeBench are domain-specific alternatives. Lean4PHYS offers a formal units checker as an alternative target.

### Cited Findings
- SciCode: 80 main problems split into 338 subproblems across 16 subdomains (physics, math, materials, biology, chemistry), Python, with gold solutions and domain-specific plus numerical test cases. — [arXiv 2407.13168](https://arxiv.org/abs/2407.13168); [GitHub](https://github.com/scicode-bench/SciCode)
- FEM-Bench: 33 structured finite-element coding tasks, 10 models evaluated. — [arXiv 2512.20732](https://arxiv.org/html/2512.20732)
- CFDCodeBench (inside CFDLLMBench) — [arXiv 2509.20374](https://arxiv.org/pdf/2509.20374)
- CMPhysBench (520 calculation problems, answer-checked, not code) — [arXiv 2508.18124](https://arxiv.org/pdf/2508.18124); LeanPhysBench (200 Lean4 theorems with units) — [arXiv 2510.26094](https://arxiv.org/html/2510.26094v1); TPS-CalcBench (hypersonic TPS calculations) — [arXiv 2604.17966](https://arxiv.org/pdf/2604.17966)

### Inferences
- SciCode tests check numbers, not units. A units-checked decoding study would need either (i) a units-annotated subset (wrap SciCode inputs/outputs in pint quantities) or (ii) an equation-level task (Feynman/SRBench-style with units, as in PhySO) to show the constraint actually binds.

### Gaps
- PhysicsEval and UGPhysics were not found in this budget. Their sizes and unit-error rates are unknown.

## Verdicts

- **(A) Physics-checker-guided SMC decoding of simulation inputs: OPEN (method known, application open).** Nearest neighbours: PhyNiKCE (symbolic CSP validator, post-generation), SIGA (agent-callable validators with validation-gated termination), Holbrook et al. LAMMPS (parser as agent skill), Foam-Agent (repair loop). The method side comes from Loula et al. SMC (checker potentials, including RDKit for molecules). Searched and not found: any work that places a simulation-domain validator inside decoding, or that compares it against repair. Novelty risk: moderate. The framing "GenLM applied to a new DSL" is incremental unless the physics cross-field rules and the repair-vs-SMC cost/quality comparison are the headline.
- **(B) Units-checked decoding: PARTIALLY DONE.** For equations/expressions, PhySO already enforces dimensional analysis as a live decode-time token prior (non-LLM). CMPhysBench explicitly proposes, but does not build, unit checks inside decoding. For LLM-generated *code* with pint/astropy/Unitful/F# UoM enforced during decoding: searched and not found. That sub-idea looks open, with Mündler et al. type-constrained decoding as the method template.
