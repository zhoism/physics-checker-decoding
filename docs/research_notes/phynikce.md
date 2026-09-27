# PhyNiKCE: full-text read (novelty check for idea A)

Source: Fan, Shi, Li, Wen, "PhyNiKCE: A Neurosymbolic Agentic Framework for Autonomous
Computational Fluid Dynamics", [arXiv 2602.11666v1](https://arxiv.org/abs/2602.11666), 12 Feb 2026,
Hong Kong PolyU. I read the full PDF text (sections 1–6 and appendices A–C), not a summary.
There is only a v1. The code repo ([EarlFan/PhyNiKCE](https://github.com/EarlFan/PhyNiKCE)) holds
only a LICENSE and a README. The paper says the code will be released "upon acceptance".

## Verdict: it does not overlap with decode-time checking

PhyNiKCE never touches the decoder, and it has no checker that accepts or rejects an output.
The onboarding report described it as "a symbolic CSP validator applied post-generation". That
description came from the abstract, and it is wrong in the way that matters:

- **"Constraint Satisfaction Problem" is used loosely.** No constraint solver or rule evaluator
  runs over the generated file. The "Deterministic RAG Engine" is five hand-written *retrieval*
  strategies over a JSON index of the ~400 OpenFOAM tutorials. Each entry is keyed by
  (solver, turbulence model, compressibility). The only way it enforces anything is by choosing
  which examples go into the prompt (§3.2, Algorithms 1–4).
- **Its constraints arrive through the prompt.** Stage 2 fills a prompt template (Listing 1)
  with retrieved examples and "rigid physical parameters", then makes one ordinary Gemini
  call. The only enforcement is the sentence "You must adhere to these".
- **The only check after generation is OpenFOAM itself.** Stage 3 runs the case. If it crashes,
  the agent parses the log, pulls out a keyword such as `div(phi,epsilon)`, retrieves snippets
  that contain it, and asks the LLM to fix the file. It repeats this for up to 30 rounds (§3.3.3).
  The validator is the solver's runtime.
- **It cannot touch logits.** The backbone is Gemini-2.5-Pro/Flash through the AI Studio API
  (§4.3).

In this project's terms, PhyNiKCE is **"knowledge in the context" plus "repair after execution"**.
It is not "checker in the decoder". That leaves the placement question open, and PhyNiKCE adds
a fourth placement that the onboarding matrix did not have.

## What it is useful for

1. **A fourth arm: rule-retrieval in the prompt.** The onboarding matrix places the checker in
   the weights, in the decoder, or after the decoder (repair). PhyNiKCE is a clean example of a
   placement *before* the decoder: put the relevant rules and exemplars in the context and hope
   the model complies. That can be added as an arm at almost no cost, by giving the model the
   checker's rule list as text *(inferred)*. It also helps the framing: "does stating the rule
   work as well as enforcing it?"
2. **Evidence that repair is expensive.** The baseline (ChatCFD architecture) averaged
   **22.11 reflection rounds and 181.2k tokens per case**. Full PhyNiKCE averaged **9.06 rounds
   and 151.2k tokens**. Stage 3 repair alone used 113.4k tokens for the baseline and 56.5k for
   PhyNiKCE (§5.1–5.2). This is a real cost number for the repair arm to compare against.
3. **Evidence that "runs" is not "correct".** Execution rate for Full PhyNiKCE was 81%, but
   accuracy was 51%. Of the 49% that failed: 10% ran but were semantically wrong (e.g. an angle
   of attack of 0° instead of 10°), 32% diverged late, beyond the reflection window, and 7% hit
   the 30-round cap (§5.6). This supports keeping checker-pass and gold separate, as in
   `ONBOARDING.md`.
4. **A taxonomy of error types.** About 90% of failures were "complex configuration errors":
   setup format, IC/BCs, discretization schemes and linear solvers (§5.5, Fig. 10). That split is
   a starting point for choosing which OpenFOAM rules the checker encodes.
5. **Concrete cross-field rules**, each a checker candidate:
   - compressible `totalPressure` needs γ and absolute p0;
   - unbounded `Gauss linear` convection with a compressible solver is unstable;
   - k-ε needs synchronized k, ε and wall-function definitions;
   - a compressible solver's fvSolution needs `rho` and `e` entries.

   These are "must be present or compatible" rules, which fit the boundary-check granularity.

## Weaknesses to keep in mind when citing it

- **Small, noisy evaluation.** 13 setups, 5–10 runs each, 100 runs per configuration. The
  cells in Table 1 are 0–8 out of 5–10, and there are no confidence intervals. The "96%
  improvement" is 26% → 51% on those 100 runs.
- **One closed model family**, Gemini 2.5, reached through an API. Nothing on small or open
  models.
- **"Accuracy" is judged by hand** against literature specifications (§5). The procedure is not
  given in detail.
- **An internal inconsistency.** The conclusion says "increasing the accuracy from 51% to 26%",
  which is reversed.
- The evaluation leaves out the tutorials, but the knowledge base is built from those same
  tutorials. The test cases are literature cases (a NACA 0012 airfoil and an SERN nozzle).

## What still needs checking for novelty

PhyNiKCE is cleared. The remaining risk is someone else putting a physics checker inside
decoding. That needs a search of papers citing PhyNiKCE, ChatCFD and Foam-Agent 2.0, plus
anything from the GenLM group on scientific formats. The companion paper, ChatCFD (Fan et al.
2026, *Advanced Intelligent Discovery*), is the same group's earlier system and uses the same
API-only design, so it is unlikely to overlap. I have not read it.
