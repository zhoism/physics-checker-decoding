# Constrained / Structured Decoding for LLMs (state as of Sep 2026): beyond-CFG constraints and distribution-faithful methods

Scope note: this pass used about 20 search/fetch calls. Items marked **[verified]** were read from a primary page (arXiv abstract/HTML, GitHub README, official docs) during this pass. Items marked **[training knowledge, unverified]** come from my prior knowledge and were not re-checked; treat them as leads. Dates of sources are given where they matter, because this field moves every few months.

---

## 1. Grammar-constrained decoding (GCD) tools: state in 2026, overheads, constraint classes

### Takeaway
Masking tokens against JSON Schema, regex and CFG constraints is a solved commodity problem in 2026. XGrammar (now XGrammar-2) and llguidance are the two main engines. Both are built into vLLM and SGLang, and their per-token mask cost is in microseconds. None of these engines expresses semantic or non-local constraints: they check syntax only, prefix by prefix, and all of them use greedy local masking, so they carry the distribution distortion described in section 2.

### Cited Findings
- **XGrammar-2** (arXiv 2601.04426; appears in the ACM CAIS 2026 program) is described as a "dynamic and efficient structured generation engine for agentic LLMs". It adds "Structural Tag", a composable JSON protocol covering tool calling, reasoning channels and harmony format, plus TagDispatch for switching structure when a tag fires and a Cross-Grammar Cache that reuses substructures across grammars. The authors claim ">6x faster compilation than prior structured generation engines" and "near-zero end-to-end overhead" in serving systems, and name xAI, Databricks and DeepSeek as adopters. **[verified via search snippets of the arXiv page + MLC blog 2026-05-04]** — [arXiv 2601.04426](https://arxiv.org/abs/2601.04426); [MLC blog](https://blog.mlc.ai/2026/05/04/xgrammar-2-fast-customizable-structured-generation); [CAIS 2026](https://www.caisconf.org/program/2026/papers/xgrammar-dynamic-and-efficient-structured-generation-engine-for-agentic-llms/)
- Original XGrammar paper: arXiv 2411.15100 (Nov 2024) — [arXiv](https://arxiv.org/pdf/2411.15100). Repo: [mlc-ai/xgrammar](https://github.com/mlc-ai/xgrammar)
- **llguidance** (Microsoft / guidance-ai) enforces CFGs. Its mask computation averages "under 50 microseconds per token for a 128k tokenizer" with negligible startup cost; a full mask for a typical JSON schema takes about 1.5 ms before optimizations. It accepts a large subset of JSON Schema, regex, and a Lark-like CFG format that can embed JSON schemas and regexes. Integrations listed: OpenAI Structured Outputs, llama.cpp, vLLM (>=0.8.2), SGLang (>=0.4.4), Chromium, Guidance, mistral.rs, onnxruntime-genai. The README reports v1.0.0 released 2025-06-23 (there may be later releases; I did not check the releases page). **[verified, README]** — [guidance-ai/llguidance](https://github.com/guidance-ai/llguidance)
- **SynCode** (Ugare, Suresh, Kang, Misailovic, Singh; published in TMLR 2025) is a CFG decoder that is sound and complete with respect to the grammar. It precomputes an offline "DFA mask store". For Llama-2-7B-chat that store took 113.72 s to build and uses 181 MB. **[verified, search snippet of arXiv/TMLR]** — [arXiv 2403.01632](https://arxiv.org/abs/2403.01632); [repo structuredllm/syncode](https://github.com/structuredllm/syncode)
- **DOMINO** (Beurer-Kellner, Fischer, Vechev, ICML 2024) handles subword/constraint misalignment ("token misalignment"). The authors say it adds "virtually no overhead", and in some cases runs almost 2x faster than unconstrained decoding because it uses speculative decoding. Template-based Guidance with invasive constraining lost up to 11 accuracy points. DOMINO scored 0.418 on GSM8K with Mistral-7B against 0.415 unconstrained. Its token-healing preprocessing takes about 20 s offline and adds about 22% online overhead for a simplified C grammar of ~70 rules. **[verified, search snippets of PMLR/arXiv]** — [arXiv 2403.06988](https://arxiv.org/abs/2403.06988); [PMLR](https://proceedings.mlr.press/v235/beurer-kellner24a.html); [eth-sri/domino](https://github.com/eth-sri/domino)
- **JSONSchemaBench** (Geng, Cooper, Moskal, …, Nori; arXiv 2501.10868, Jan 2025) compares Guidance, Outlines, llama.cpp, XGrammar, OpenAI and Gemini on 10,000 real-world JSON schemas plus the official JSON Schema Test Suite. It measures efficiency, coverage and output quality. **[verified, abstract]** — [arXiv 2501.10868](https://arxiv.org/abs/2501.10868). Its per-framework numbers are not captured here (see Gaps).
- A 2025 alternative engine: "Flexible and Efficient Grammar-Constrained Decoding" (arXiv 2502.05111) — [arXiv](https://arxiv.org/pdf/2502.05111). Found by search; not read.
- **Outlines + MLX**: Outlines supports the `mlx_lm` runtime. `mlx_lm`'s `generate_step` accepts logits processors, and that hook is where the mask is applied. **[search snippet, secondary]** — [LibreChat MLX blog (2024)](https://www.librechat.ai/blog/2024-05-01_mlx). Flag: the source dates from 2024.
- **llama.cpp**: llguidance is listed as integrated with llama.cpp (see above). llama.cpp's own GBNF grammars run on Metal/Apple Silicon **[training knowledge, unverified in this pass]**.
- **[training knowledge, unverified]**: vLLM structured outputs (the `guided_decoding` backends `xgrammar` / `guidance` / `outlines`) and SGLang (default backend XGrammar, with llguidance and Outlines as options) both support JSON schema, regex, EBNF/CFG and choice lists. Outlines (dottxt) compiles regex and JSON schema to FSMs and supports CFGs through a Lark-based path. Its core has been rewritten in Rust as `outlines-core`.

### Inferences
- Constraint classes available in production engines stop at regular and context-free languages, plus some JSON Schema features that compile to those, such as enum and const. Cross-field, non-local and semantic constraints (for example "atom count matches formula" or "residue index exists in topology") cannot be written in any of them. A domain checker has to sit outside the engine: as a custom logits processor, in an SMC framework, or as a post-hoc rerank.
- For a checker project, a sensible stack uses XGrammar or llguidance for the cheap syntactic layer (microseconds per token) and puts the domain checker in a separate, more expensive layer. Section 4 shows this is the same two-tier split Loula et al. use (Φ_eff vs Φ_exp).

### Gaps
- I did not verify current release numbers or dates for Outlines, SynCode, XGrammar-2 or llguidance after 1.0.0.
- I did not extract JSONSchemaBench's per-engine coverage and compliance numbers or its quality-impact numbers.
- No MLX-native grammar engine status (for example whether XGrammar ships an MLX kernel) was verified.

---

## 2. The distribution-distortion problem (GAD / ASAp and follow-ups)

### Takeaway
Greedy per-token masking samples from a locally renormalized distribution, not from the LM's distribution conditioned on the constraint. In other words, it does not sample from P(x | x ∈ L). Exact alternatives now exist: ASAp (NeurIPS 2024), SMC with weight correction (Loula 2025), AWRS (COLM 2025) and CARS (ICML 2026). The practical cost of distortion depends on the task. It is large when the constraint cuts away most of the model's probability mass, as in fuzzing, low-prior domains and small models, and small for well-prompted JSON.

### Cited Findings
- **Grammar-Aligned Decoding** (Park, Wang, Berg-Kirkpatrick, Polikarpova, D'Antoni; NeurIPS 2024; arXiv 2405.21047). The paper says GCD "distorts the LLM's distribution, leading to outputs that are grammatical but appear with likelihoods that are not proportional to the ones given by the LLM". Its fix, ASAp (Adaptive Sampling with Approximate expected futures), uses earlier samples to soundly over-approximate how likely each prefix is to reach a grammatical completion. ASAp "provably" converges to the grammar-conditioned distribution and "often produces outputs with higher likelihood" than GCD. Evaluation covered code generation and structured NLP tasks. **[verified, abstract]** — [arXiv](https://arxiv.org/abs/2405.21047); [NeurIPS PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/2bdc2267c3d7d01523e2e17ac0a754f3-Paper-Conference.pdf)
- **[training knowledge, unverified]**: ASAp converges asymptotically, because it learns expected-future corrections across repeated samples of the *same* prompt. That makes it a many-samples-per-prompt method, not a single-shot decoder.
- **CARS: Constrained Adaptive Rejection Sampling** (arXiv 2510.01902; ICML 2026 poster). The method starts from unconstrained LM sampling. Each time a continuation violates the constraint, CARS records the violating prefix in a trie and subtracts its probability mass from later draws, so invalid prefixes are never revisited, acceptance rates improve monotonically, and samples "exactly follow the constrained distribution". Evaluation covered program fuzzing and molecular generation, with efficiency measured as LM forward passes per valid sample. In XML fuzzing, plain rejection sampling did not reach 100 valid samples within a 2,000-sample budget, while CARS reached 100 in 440 generations. The paper reports better diversity than GCD and than approximate methods such as GAD. **[verified, search snippet]** — [OpenReview](https://openreview.net/forum?id=OhndOnT4Ih); [ICML 2026 poster](https://icml.cc/virtual/2026/poster/62468)
- **Stateful CARS** (arXiv 2608.08282, Aug 2026) is titled "Exact Cross-History Reuse for Policy-Constrained LLM Agents". **[title only; not read]** — [arXiv](https://arxiv.org/pdf/2608.08282)
- Loula et al. 2025 say greedy local masking produces "greedy approximations that badly distort the distribution". They also report that methods sitting closer to the global product-of-experts target, measured by their KL-divergence estimates, do better downstream (details in section 4). **[verified, HTML]** — [arXiv 2504.13139](https://arxiv.org/html/2504.13139)
- Size of the effect in practice, from Loula et al. (Llama 3.1 8B-Instruct, Spider text-to-SQL): weight correction lifted execution accuracy from 0.597 to 0.618, and resampling added nothing. On molecules and goal inference, correction plus resampling gave large gains (see section 4). **[verified, HTML]** — [arXiv 2504.13139](https://arxiv.org/html/2504.13139)
- Evidence on the other side: DOMINO reports that well-aligned constrained decoding matches or beats unconstrained accuracy on GSM8K (0.418 vs 0.415, Mistral-7B). That suggests most practical accuracy loss comes from token misalignment and invasive templates rather than from the conditional-distribution mismatch. **[verified snippet]** — [PMLR](https://proceedings.mlr.press/v235/beurer-kellner24a.html)

### Inferences
- Distortion matters most when the constraint is **low-prior** under the model, meaning the model rarely produces valid output unaided. Validity checks from a scientific domain checker probably fall in that category for small models, which favours SMC, AWRS or CARS over plain masking.
- If the project only needs "a valid output", plain GCD is fine. If it needs calibrated or representative samples (for example diversity across candidate structures, or estimating how likely a class of outputs is), it needs an exact method.

### Gaps
- I did not extract ASAp's quantitative KL and likelihood tables.
- I found no 2025–26 large-scale study that quantifies distortion for JSON-schema workloads specifically.

---

## 3. Semantic / non-local constraints: monitors, type-constrained decoding, incremental checkers

### Takeaway
The dominant pattern for semantic constraints is an **incremental prefix checker**: a static analyzer, type checker or language server that decides whether a partial output can still be completed validly, and whose answer is turned into a token mask. The best-established examples are Monitor-Guided Decoding (NeurIPS 2023) and type-constrained decoding (Mündler et al., PLDI 2025). Both require building a *prefix-sound* checker, which is the main engineering cost.

### Cited Findings
- **Monitor-Guided Decoding** (Agrawal, Kanade, Goyal, Lahiri, Rajamani; NeurIPS 2023). A "monitor" runs static analysis through a Language Server Protocol server and steers decoding toward type-consistent object dereferences in repository-level Java method completion. The paper introduced the PragmaticCode dataset and the `multispy` LSP client library, and reports that MGD "consistently improves compilation rates" across model scales. Code: [microsoft/monitors4codegen](https://github.com/microsoft/monitors4codegen). **[verified, search snippets of NeurIPS pages]** — [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2023/hash/662b1774ba8845fc1fa3d1fc0177ceeb-Abstract-Conference.html)
  - **[training knowledge, unverified]**: MGD triggers the monitor only at specific points (after `.` dereferences) and masks tokens against the identifiers the LSP returns. A monitor that fires at sparse "trigger points" rather than on every token is a useful design pattern for expensive checkers.
- **Type-Constrained Code Generation** (Mündler, He, Wang, Sen, Song, Vechev; arXiv 2504.09246, Apr 2025; PLDI 2025 per the user's brief, venue not re-verified here). It uses "novel prefix automata and a search over inhabitable types" to enforce well-typedness during decoding. The approach is formalized on a simply-typed language and extended to TypeScript. On HumanEval and MBPP it cut compilation errors by more than half and improved functional correctness in synthesis, translation and repair, across model families up to open-weight 30B+ models. **[verified, abstract]** — [arXiv 2504.09246](https://arxiv.org/abs/2504.09246)
- **"Correctness-Guaranteed Code Generation via Constrained Decoding"** (arXiv 2508.15866, 2025) is another semantic-constraint code paper. **[title only; not read]** — [arXiv](https://arxiv.org/pdf/2508.15866)
- **"Decode-Time Grammars: Constrained LLM Generation over a Refinement Order of Grammar Fragments"** (arXiv 2607.18357, Jul 2026). **[title only; not read]** — [arXiv](https://arxiv.org/pdf/2607.18357)
- A 2026 decoding survey that may help locate further work: "Beyond Tokens: A Survey on Decoding Methods for LLMs and VLMs" (arXiv 2608.14797). **[title only]** — [arXiv](https://arxiv.org/pdf/2608.14797)
- DOMINO (section 1) concerns token/constraint alignment and is not a semantic-constraint method. It is relevant because any checker operating on characters or bytes has to be lifted to subword tokens. genlm-control handles that step with `.coerce()` (section 4).

### Inferences
- Hard masking with a semantic checker requires the checker to answer "can this prefix still be completed validly?". The answer must be **sound**, meaning it never rejects a completable prefix. Otherwise masking can dead-end or bias the output. Type inhabitation search in Mündler et al. exists to make exactly that prefix question decidable.
- A checker that can only judge complete outputs cannot drive masking. It can still serve as a potential that SMC applies at the end, or at semantic boundaries (section 4).
- Masking with a semantic checker also inherits the distortion from section 2, and probably more severely, because semantic constraints are more restrictive than syntactic ones.

### Gaps
- I did not find or verify details on "DOMINO" as a semantic method. DOMINO turned out to be a subword-alignment method (above), so if the brief meant a different "DOMINO", it was not located.
- No quantitative runtime overhead figure for Mündler et al. or MGD was captured.
- I found no general-purpose library that turns an arbitrary incremental checker into a mask for vLLM or llama.cpp other than hand-written logits processors. genlm-control is the closest.

---

## 4. SMC / probabilistic-programming steering (LLaMPPL, Loula et al., genlm-control, AWRS, twisted SMC): plugging in a checker

### Takeaway
genlm-control (MIT Probabilistic Computing Project / ETH / JHU and others) is the maintained stack. A domain checker becomes a `Potential` subclass with async `prefix(context)` and `complete(context)` methods. It is used either inside the token sampler (AWRS, for cheap constraints) or as a `critic` that reweights particles between resampling steps (for expensive constraints). A checker that only judges complete outputs still works as a critic, but the method then reduces toward importance sampling, i.e. sample-and-rerank, and loses SMC's early reallocation of compute.

### Cited Findings
- **LLaMPPL** (Lew, Zhi-Xuan, Grand, Mansinghka; arXiv 2306.03081, June 2023). It frames constrained generation as posterior inference in "Feynman-Kac Transformer models" and replaces decoding with SMC. The library applied to infilling, constrained generation and prompt intersection at "a cost similar to that of beam search", targeting LLaMA-family models. **[verified, search snippet of arXiv]** — [arXiv 2306.03081](https://arxiv.org/abs/2306.03081). Flag: from 2023; genlm-control supersedes it in practice **[inference]**.
- **Loula et al.** "Syntactic and Semantic Control of Large Language Models via Sequential Monte Carlo" (arXiv 2504.13139, Apr 2025; the user's brief says ICLR 2025, but arXiv lists it only as cs.CL and I did not confirm the venue). Authors include Loula, LeBrun, Du, Lipkin, Pasti, Grand, Liu, Emara, Freedman, Eisner, Cotterell, Mansinghka, Lew, Vieira and O'Donnell. **[verified, abstract/HTML]** — [arXiv](https://arxiv.org/abs/2504.13139); [HTML](https://arxiv.org/html/2504.13139)
  - It splits potentials into **Φ_eff** (cheap, incremental grammar potentials such as SQL/Python CFG and SMILES syntax) and **Φ_exp** (expensive semantic potentials, "evaluated post-generation or at meaningful boundaries"):
    - Goal inference: "run a simulation with a ground-truth plan and check whether the resulting state conforms to the predicted (partial) goal".
    - Data science (DS-1000): run Python test cases and check for runtime errors.
    - Text-to-SQL: check column and table aliases against the schema.
    - Molecules: check partial SMILES validity.
  - Seven methods are ablated: base LM; locally constrained decoding (grammar mask); grammar plus weight correction (IS); grammar plus resampling; grammar plus Φ_exp as sample-rerank; Full IS; and Full SMC (grammar, Φ_exp, weight correction and resampling).
  - Results (Full SMC): goal inference 0.419 accuracy; DS-1000 0.407 test accuracy; Spider 0.620 execution accuracy; GDB-17 molecules QED 0.577.
  - The expensive potential alone raises goal inference from 0.063 to 0.289 (via sample-rerank). Resampling raises goal inference from 0.257 (IS) to 0.419 (SMC) and molecules from 0.404 to 0.577. Full SMC needs 5–10x fewer particles than Full IS for the same performance.
  - Headline claim: small open models match or beat models "over 8x larger" and closed-source fine-tuned systems.
  - Overhead: expensive potentials "often incur ~30ms per token". This is reduced by evaluating only at semantic boundaries and running the potentials on CPU.
  - KL-divergence estimates show Full SMC approximates the global target more closely than local decoding in every domain.
- **AWRS: "Fast Controlled Generation from Language Models with Adaptive Weighted Rejection Sampling"** (Lipkin, LeBrun, Hoover Vigly, Loula, MacIver, Du, Eisner, Cotterell, Mansinghka, O'Donnell, Lew, Vieira; COLM 2025; arXiv 2504.05410). The paper argues that locally constrained decoding (a) is costly because it evaluates the constraint on every token of a vocabulary of 100k+ and (b) distorts the global distribution. AWRS instead samples tokens and rejects the ones the constraint rules out, adaptively. It needs "orders of magnitude fewer constraint evaluations" and yields **unbiased importance-weight estimates** that SMC can use to correct distortion. The speedup grows with the divergence between the unconstrained and constrained models, and is larger for better models. Evaluated on text-to-SQL, molecular synthesis, goal inference, pattern matching and JSON. **[verified, abstract]** — [arXiv 2504.05410](https://arxiv.org/abs/2504.05410)
  - **Inference, important for checker design**: AWRS queries the constraint on one candidate token at a time instead of the whole vocabulary. That makes a *slow* Python domain checker usable at the token level, which vocabulary-wide masking would not be.
- **genlm-control API** **[verified, docs]** — [repo](https://github.com/genlm/genlm-control); [getting started](https://genlm.org/genlm-control/getting_started/)
  - Install with `pip install genlm-control`.
  - A custom potential subclasses `Potential`, declares a `vocabulary` in `super().__init__(vocabulary=...)` (for example `list(range(256))` for bytes), and implements async `prefix(context)` and `complete(context)`. `batch_prefix` and `batch_complete` can be overridden for speed.
  - Potentials compose with `*` (product) and are lifted to the LM's token type with `.coerce(target, f=b"".join)`.
  - A token sampler is built as `AWRS(llm, coerced_potential)`. Sampling runs as `await token_sampler.smc(n_particles=..., ess_threshold=0.5, max_tokens=..., critic=...)`, where the critic "will reweight samples at each step". Critics are wrapped in `AutoBatchedPotential` unless `autobatch=False`.
  - LLMs load with `PromptedLLM.from_name("meta-llama/Llama-3.2-1B-Instruct")`.
  - **[training knowledge, unverified]**: `logw_next` (next-token log-weights) has a default derived from `prefix`/`complete`. The docs specify how `prefix` should relate to `complete` (a prefix potential should upper-bound or aggregate over completions) for correct weighting. Check the API reference before relying on this.
- **genlm-backend** supports vLLM (with automatic KV caching), SGLang (`[sgl]` extra), Hugging Face Transformers (the default) and **MLX-LM "for inference on Apple silicon"**. **[verified, README]** — [genlm/genlm-backend](https://github.com/genlm/genlm-backend)
- **Twisted SMC** (Zhao, Brekelmans, Makhzani, Grosse; ICML 2024 oral; arXiv 2404.17546). It casts RLHF, red-teaming, infilling and similar tasks as sampling from an unnormalized target defined by a potential over the *full sequence*. It learns **twist functions** that estimate the expected future potential of each partial sequence, using a contrastive twist-learning method connected to soft RL. **[verified, search snippet]** — [arXiv](https://arxiv.org/abs/2404.17546); [PMLR](https://proceedings.mlr.press/v235/zhao24c.html)

### Inferences (how to plug in a deterministic domain checker)
1. **Checker with a sound prefix test** ("can this prefix still become valid?"): implement it as `prefix()` returning 0 or -inf in log space, with `complete()` giving the full verdict. Use it inside AWRS so each token is exact-checked lazily, and let SMC weights correct the distortion. This is the strongest setting.
2. **Checker that only judges complete outputs**: `prefix()` returns 0 (neutral) and `complete()` returns 0 or -inf. Pass it as the `critic`. SMC cannot prune before end-of-sequence, so this is effectively importance sampling or rejection, i.e. the "sample-rerank" and "Full IS" rows in Loula et al. It still helps (0.063 to 0.289 on goal inference), but it needs many more particles.
3. **Middle ground**: evaluate the checker at *semantic boundaries* such as the end of a statement, line, record or field, as Loula et al. do. Alternatively, build a cheap approximate prefix proxy. If the proxy is not sound it must be used as a soft critic weight, not a hard mask. A learned twist (Zhao et al.) is the principled version of "estimate future validity from a prefix", but it needs training data.
4. **Two-tier layout**: a grammar or format layer as Φ_eff (fast, token level), with the domain checker as Φ_exp at boundaries, running on CPU.

### Gaps
- I did not confirm exact genlm-control release numbers or dates, or the exact contract `prefix` must satisfy relative to `complete`.
- I did not confirm Loula et al.'s venue (ICLR 2025).
- I did not extract twisted SMC's model sizes or metrics.

---

## 5. Hardware: Apple Silicon (MLX / llama.cpp / MPS) vs CUDA; typical model sizes

### Takeaway
The SMC stack can run on Apple Silicon through genlm-backend's MLX-LM backend. The papers themselves, however, ran on NVIDIA A100/H100 with 8B–70B Llama models. GCD engines run on Apple Silicon through llama.cpp and through Outlines logits processors in `mlx_lm`. vLLM's fast paths are CUDA-first; a vLLM-metal plugin exists.

### Cited Findings
- genlm-backend explicitly supports MLX-LM on Apple silicon. **[verified]** — [genlm-backend](https://github.com/genlm/genlm-backend)
- Loula et al. hardware: an A100 GPU with 12 vCPUs as standard, and 4x H100 with 64 vCPUs for DS-1000. Models: Llama 3.1 8B (goal inference, molecules), Llama 3.1 8B-Instruct (Spider), Llama 3 70B (DS-1000). **[verified, HTML]** — [arXiv HTML](https://arxiv.org/html/2504.13139)
- The genlm-control README example uses `gpt2` and `Llama-3.2-1B-Instruct`. **[verified]** — [repo](https://github.com/genlm/genlm-control)
- Mündler et al. evaluate model families "ranging from open-weight 30B+" models (per the abstract). **[verified]** — [arXiv](https://arxiv.org/abs/2504.09246)
- DOMINO evaluates Mistral-7B among others; SynCode reports Llama-2-7B mask-store costs. **[verified snippets]** — [PMLR](https://proceedings.mlr.press/v235/beurer-kellner24a.html); [arXiv](https://arxiv.org/abs/2403.01632)
- vLLM-metal is described as an official MLX-based vLLM plugin for Apple Silicon. **[secondary, search snippet; not verified at source]** — [arXiv 2601.19139](https://arxiv.org/html/2601.19139v2)
- `mlx_lm.generate_step` accepts logits processors, which is the hook that Outlines-style masking uses. **[secondary, 2024]** — [LibreChat blog](https://www.librechat.ai/blog/2024-05-01_mlx)

### Inferences
- A laptop prototype is feasible: a 1–8B model on MLX with genlm-control, a few to tens of particles, and a CPU domain checker. Compute is dominated by particles × tokens × forward passes. MLX-LM batching of particles is probably weaker than vLLM's prefix-sharing KV cache, so expect slower runs than the paper numbers **[unverified; no benchmark found]**.
- A deterministic checker running on CPU fits Apple Silicon's unified memory well, and Loula et al. already run Φ_exp on CPU.

### Gaps
- I found no benchmark of genlm-control on MLX versus vLLM.
- I did not verify whether XGrammar or llguidance ship MLX integrations.

---

## 6. Evaluation metrics used in this literature

### Takeaway
Papers report (a) **validity or compliance rate**, (b) **downstream task accuracy** (execution accuracy, test pass, compile rate, QED), (c) **distribution faithfulness**: KL to the constrained target, LM likelihood of outputs, sample diversity, and (d) **cost**: runtime, per-token overhead, constraint evaluations, LM forward passes per valid sample, particles needed.

### Cited Findings
- Loula et al.: accuracy against ground-truth PDDL goals (goal inference), test-case accuracy (DS-1000), execution accuracy (Spider), QED drug-likeness (GDB-17 molecules), KL-divergence estimates to the global product-of-experts target, particles needed (SMC vs IS), and about 30 ms/token potential overhead. **[verified]** — [arXiv HTML](https://arxiv.org/html/2504.13139)
- AWRS: runtime and the number of constraint evaluations, alongside task performance. **[verified abstract]** — [arXiv](https://arxiv.org/abs/2504.05410)
- CARS: LM forward passes per valid sample, and sample diversity. **[verified snippet]** — [OpenReview](https://openreview.net/forum?id=OhndOnT4Ih)
- GAD/ASAp: likelihood of outputs under the LM compared with GCD, and convergence to the grammar-conditioned distribution. **[verified abstract]** — [arXiv](https://arxiv.org/abs/2405.21047)
- Type-constrained decoding: compilation-error reduction (>50%) and functional correctness (pass@k on HumanEval/MBPP). **[verified abstract]** — [arXiv](https://arxiv.org/abs/2504.09246)
- MGD: compilation rate (plus next-identifier match) on PragmaticCode. **[verified snippet for compilation rate]** — [NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2023/hash/662b1774ba8845fc1fa3d1fc0177ceeb-Abstract-Conference.html)
- DOMINO: downstream accuracy (GSM8K etc.) versus unconstrained, and throughput/overhead. **[verified snippet]** — [PMLR](https://proceedings.mlr.press/v235/beurer-kellner24a.html)
- JSONSchemaBench: efficiency, coverage and quality of generated outputs. **[verified abstract]** — [arXiv](https://arxiv.org/abs/2501.10868)

### Inferences
- For a domain-checker project, a defensible evaluation grid is:
  - validity rate (the checker passes);
  - task quality (a domain metric independent of the checker);
  - faithfulness (KL or likelihood against a gold constrained sampler; on small problems exact enumeration or long-run rejection sampling can supply ground truth, as CARS does);
  - diversity (to catch mode collapse);
  - cost (wall-clock time, checker calls, forward passes per valid sample).
- Report both the "LCD only" and "Full SMC" rows so the contribution of distribution correction is separated from the contribution of constraint enforcement.

### Gaps
- There is no standard benchmark for *semantic* constrained decoding comparable to JSONSchemaBench for syntax. Each paper uses its own domains.
