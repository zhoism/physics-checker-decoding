"""Run each decoding arm on each prompt; log validity and cost; print the arm table.

    uv run python run_arms.py --prompts prompts/amber_smoke.jsonl --n 8 --out results/amber_smoke.jsonl
    uv run python run_arms.py --table results/amber_smoke.jsonl
    uv run python run_arms.py --verify results/amber_smoke.jsonl   # ship check

Arms, all from the same prompt:
  free     plain sampling
  grammar  grammar mask only (AWRS, grammar potential)
  bestofn  n grammar-masked samples, keep one the checker passes: checker after decoding
  smc      n particles, grammar mask, checker as SMC critic: checker during decoding
  mask     grammar x checker as one token-level mask (AWRS): checker inside every token
Best-of-N and SMC share the grammar proposal and differ in where the checker sits, and also
in weighting: SMC's AWRS proposals are properly weighted and resampled, best-of-N's are plain
constrained samples. "valid" is md-param-check's verdict; the duplicate-key ban is a decoding
requirement and is logged as its own column, and pmemd's verdict is the gold column.
"""
import argparse
import asyncio
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

SYSTEM = (
    "You write AMBER pmemd input files (mdin). Reply with the file only: no code fences, "
    "no commentary. The file is a one-line title, then a &cntrl namelist of lowercase "
    "AMBER keywords, each used once, closed by a line holding /, then any &wt namelists "
    "the run needs. The format, shown for an energy minimization (other runs need other "
    "keys):\n\nMinimization\n &cntrl\n  imin = 1, maxcyc = 2000, ncyc = 1000,\n"
    "  cut = 8.0, ntb = 1,\n /\n"
)
ARMS = ["free", "grammar", "bestofn", "smc", "mask"]


def strip_fences(text: str) -> str:
    if "```" not in text:
        return text
    lines = text.split("\n")
    fences = [i for i, line in enumerate(lines) if line.strip().startswith("```")]
    end = fences[1] if len(fences) > 1 else len(lines)
    return "\n".join(lines[fences[0] + 1:end]) + "\n"


def judge(text: str, truncated: bool) -> dict:
    """valid is the checker's verdict; pmemd is the gold one, kept in its own column."""
    from checkers import amber, pmemd_gold
    from checkers.amber_grammar import in_language

    body = strip_fences(text)
    fails = amber.failures(body)
    rec = {"truncated": truncated, "grammar": in_language(body),
           "failures": [f for f in fails if not f.startswith(amber.DUP_RULE)],
           "duplicates": [f for f in fails if f.startswith(amber.DUP_RULE)]}
    rec["checker"] = not rec["failures"]
    rec["valid"] = not truncated and rec["grammar"] and rec["checker"]
    ok, err = pmemd_gold.accepts(body) if not truncated else (False, "truncated")
    rec["pmemd"], rec["pmemd_error"] = ok, err
    return rec


class Counter:
    """Counts LLM next-token queries by wrapping the backend call."""

    def __init__(self, llm):
        self.calls = 0
        inner = llm.model.next_token_logprobs

        async def counted(*args, **kwargs):
            self.calls += 1
            return await inner(*args, **kwargs)

        llm.model.next_token_logprobs = counted


async def run(args):
    import mlx.core as mx
    import numpy as np
    from genlm.control import AWRS, PromptedLLM, direct_token_sampler

    from checkers import amber
    from decoding.potentials import CALLS, AmberChecker, MdinGrammar

    llm = PromptedLLM.from_name(args.model, backend="mlx", temperature=args.temperature)
    counter = Counter(llm)
    grammar = MdinGrammar().coerce(llm, f=b"".join)
    checker = AmberChecker().coerce(llm, f=b"".join)
    both = (MdinGrammar() * AmberChecker()).coerce(llm, f=b"".join)
    # proper_weights=False is plain constrained decoding: every step returns an allowed
    # token. The properly weighted mode sometimes returns a rejected token with weight 0,
    # which is only right when SMC resampling follows, so only the smc arm uses it.
    # max_rejects bounds one step's rejection loop: with a Python checker in the mask, a
    # step whose allowed mass is tiny otherwise tests most of the 152k-token vocabulary
    # (up to 34 min on one prompt). A particle that hits the cap dies.
    samplers = {
        "free": lambda: direct_token_sampler(llm),
        "grammar": lambda: AWRS(llm, grammar, proper_weights=False, max_rejects=args.max_rejects),
        "mask": lambda: AWRS(llm, both, proper_weights=False, max_rejects=args.max_rejects),
    }
    tok = llm.model.tokenizer
    prompts = [json.loads(line) for line in Path(args.prompts).read_text().splitlines() if line]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    for seed in range(args.seeds):
        for p in prompts:
            msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": p["text"]}]
            ids = tok.apply_chat_template(msgs, add_generation_prompt=True)
            llm.prompt_ids = list(ids["input_ids"] if hasattr(ids, "keys") else ids)
            for arm in args.arms:
                random.seed(seed); np.random.seed(seed); mx.random.seed(seed)
                amber.failures.cache_clear(); amber._alive.cache_clear()
                counter.calls = 0
                CALLS.clear()
                t0 = time.time()
                error = ""
                try:
                    if arm in ("free", "grammar", "mask"):
                        seqs = await samplers[arm]().smc(n_particles=1, ess_threshold=0.0,
                                                         max_tokens=args.max_tokens)
                    elif arm == "bestofn":
                        seqs = await samplers["grammar"]().smc(n_particles=args.n, ess_threshold=0.0,
                                                               max_tokens=args.max_tokens)
                    else:  # smc
                        seqs = await AWRS(llm, grammar, max_rejects=args.max_rejects).smc(
                            n_particles=args.n, ess_threshold=0.5, max_tokens=args.max_tokens,
                            critic=checker)
                    contexts, log_weights = seqs.contexts, seqs.log_weights
                except Exception as e:  # a sampler crash counts as a failed sample, logged
                    error, contexts, log_weights = repr(e)[:300], [[]], [float("-inf")]
                seconds = time.time() - t0
                parts = []
                for ctx, lw in zip(contexts, log_weights):
                    # genlm forces EOS at the token budget, so a full-length context was cut off
                    truncated = len(ctx) >= args.max_tokens
                    text = b"".join(t for t in ctx if isinstance(t, bytes)).decode("utf-8", "replace")
                    parts.append((text, judge(text, truncated), float(lw)))
                if arm == "bestofn":
                    pick = next((q for q in parts if q[1]["valid"]), parts[0])
                elif arm == "smc":
                    live = [q for q in parts if q[2] > float("-inf")]
                    w = np.exp(np.array([q[2] for q in live]) - max(q[2] for q in live)) if live else None
                    pick = live[np.random.choice(len(live), p=w / w.sum())] if live else parts[0]
                else:
                    pick = parts[0]
                rec = {"prompt": p["id"], "arm": arm, "seed": seed, "model": args.model,
                       "temperature": args.temperature, "max_rejects": args.max_rejects,
                       "n_particles": len(parts), **pick[1],
                       "logw": pick[2], "sampler_error": error,
                       "particles_valid": sum(q[1]["valid"] for q in parts),
                       "llm_calls": counter.calls, "checker_calls": CALLS["checker"],
                       "seconds": round(seconds, 2), "text": pick[0]}
                with out.open("a") as f:
                    f.write(json.dumps(rec) + "\n")
                print(f"{p['id']:<20} {arm:<8} seed={seed} valid={rec['valid']!s:<5} "
                      f"grammar={rec['grammar']!s:<5} checker={rec['checker']!s:<5} pmemd={rec['pmemd']!s:<5} "
                      f"calls={counter.calls:<5} {seconds:6.1f}s  {rec['failures'][:2]}", flush=True)


def table(path: str):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line]
    by = defaultdict(list)
    for r in rows:
        by[r["arm"]].append(r)
    print(f"{path}: {len({r['prompt'] for r in rows})} prompts, "
          f"{len({r['seed'] for r in rows})} seeds, model {rows[0]['model']}, "
          f"temperature {rows[0].get('temperature', 1.0)}, max_rejects {rows[0].get('max_rejects')}")
    print("| arm | n | valid | grammar ok | checker ok | has duplicate keys | pmemd ok "
          "| valid, pmemd rejects | LLM queries / sample | LLM queries / valid | checker calls "
          "/ sample | s / sample |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for arm in [a for a in ARMS if a in by]:
        rs = by[arm]
        n, v = len(rs), sum(r["valid"] for r in rs)
        calls = sum(r["llm_calls"] for r in rs)
        per_valid = f"{calls / v:.0f}" if v else "inf"
        gap = sum(r["valid"] and not r["pmemd"] for r in rs)
        print(f"| {arm} | {n} | {v}/{n} | {sum(r['grammar'] for r in rs)}/{n} | "
              f"{sum(r['checker'] for r in rs)}/{n} | {sum(bool(r['duplicates']) for r in rs)}/{n} | "
              f"{sum(r['pmemd'] for r in rs)}/{n} | {gap} | {calls / n:.0f} | {per_valid} | "
              f"{sum(r['checker_calls'] for r in rs) / n:.0f} | {sum(r['seconds'] for r in rs) / n:.1f} |")


def verify(path: str) -> int:
    """Re-judge every logged sample with today's grammar, checker and pmemd. A logged
    verdict that no longer reproduces means the table is stale: exit 1."""
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line]
    keys = ["grammar", "checker", "valid", "pmemd", "duplicates"]
    stale = [(r["prompt"], r["arm"], r["seed"], k) for r in rows
             for k, v in [(k, judge(r["text"], r["truncated"])[k]) for k in keys] if r[k] != v]
    for s in stale:
        print("stale:", *s)
    print(f"{len(rows)} logged samples re-judged, {len(stale)} verdicts changed")
    return 1 if stale else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mlx-community/Qwen2.5-7B-Instruct-4bit")
    ap.add_argument("--prompts", default="prompts/amber_smoke.jsonl")
    ap.add_argument("--out", default="results/amber_smoke.jsonl")
    ap.add_argument("--arms", nargs="+", default=ARMS, choices=ARMS)
    ap.add_argument("--n", type=int, default=8, help="particles for bestofn and smc")
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-rejects", type=int, default=2000, help="AWRS cap per token step")
    ap.add_argument("--table", metavar="RESULTS", help="print the table for a results file and exit")
    ap.add_argument("--verify", metavar="RESULTS", help="re-judge a results file; exit 1 if stale")
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if args.verify:
        table(args.verify)
        sys.exit(verify(args.verify))
    elif args.table:
        table(args.table)
    else:
        asyncio.run(run(args))
        table(args.out)
