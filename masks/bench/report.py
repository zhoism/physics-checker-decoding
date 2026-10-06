"""The mask-bench tables, rebuilt from the logged masks in results/*.jsonl (never typed by hand), each
mask judged again by ambmask against the current tasks.jsonl.
    .venv/bin/python masks/bench/report.py > masks/bench/results/report.md
Every rate is exact matches / tasks attempted, summed over runs; n and runs are printed with it."""
import functools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from blind import TASKS, verdict  # noqa: E402
from tasks import from_ranges  # noqa: E402

GOLD = {t["id"]: from_ranges(t["gold"]) for t in TASKS}


@functools.lru_cache(maxsize=None)
def judge(system, tid, mask):
    return verdict(system, mask, GOLD[tid])


def rescore(r):
    """Verdicts from the stored masks against today's gold, so a corrected gold reaches every table. A first
    try that is now right would not have been sent to repair, so its repair stages count as right too."""
    r["verdict"] = judge(r["system"], r["id"], r["mask"])
    for stage in ("checker", "lint"):
        if f"{stage}_mask" in r:
            again = judge(r["system"], r["id"], r[f"{stage}_mask"])
            r[f"{stage}_verdict"] = "EXACT" if r["verdict"] == "EXACT" else again
    if "verify_mask" in r:  # the selection loop sees right answers too, and can break them: judged on its own
        r["verify_verdict"] = judge(r["system"], r["id"], r["verify_mask"])
    return r


FILES = {  # label -> results file, in table order
    "Haiku 4.5, view": "haiku_view.jsonl",
    "Haiku 4.5, view + map": "haiku_map.jsonl",
    "Sonnet 5, view": "sonnet_view.jsonl",
    **{f"{name} (OpenRouter), view": f"{name.lower()}_view.jsonl"  # blind.py openrouter:<id>, the Claude protocol
       for name in ("Qwen3.8-27B", "Qwen3.5-122B-A10B", "Qwen3.5-397B-A17B", "Gemma-4-31B-it",
                    "Nemotron-3-Super-120B-A12B", "Nemotron-3-Ultra-550B-A55B")},
    "Nemotron-3-Ultra-550B picks among its 3 samples (pick.py)": "nemotron-3-ultra-550b-a55b_pick.jsonl",
    **{f"Qwen3.8-27B nf4 {decode}, sheet": f"qwen3.8-27b-nf4_{decode}_sheet.jsonl" for decode in ("free", "grammar2", "checked")},
    "Qwen3.8-27B picks among 3 grammar v2 samples (pick.py)": "qwen3.8-27b_pick_grammar2.jsonl",
    "Qwen3.8-27B picks among 5 grammar v2 samples (pick.py)": "qwen3.8-27b_pick_grammar2_5.jsonl",
    "Qwen3.8-27B nf4 checked, task, newline forced before the end": "qwen3.8-27b-nf4_checked_task_forced-newline.jsonl",
    **{f"Qwen3.8-27B nf4 {decode}, task": f"qwen3.8-27b-nf4_{decode}_task.jsonl" for decode in ("grammar2", "checked")},
    **{f"Gemma-4-31B nf4 {decode}, sheet": f"gemma-4-31b-it-nf4_{decode}_sheet.jsonl" for decode in ("free", "grammar2")},
    "Gemma-4-31B picks among 3 nf4 grammar v2 samples (pick.py)": "gemma-4-31b-it_pick_grammar2.jsonl",
    "Gemma-4-31B picks among 3 bf16 grammar v2 samples (pick.py)": "gemma-4-31b-it_pick_grammar2_bf16.jsonl",
    **{f"Gemma-4-31B bf16 {decode}, {layout}": f"gemma-4-31b-it-bf16_{decode}_{layout}.jsonl"  # modal_app.py, A100
       for decode, layout in (("free", "sheet"), ("grammar2", "sheet"), ("grammar2", "task"), ("checked", "task"))},
    **{f"Qwen3.5-122B-A10B fp8 {decode}, sheet": f"qwen3.5-122b-a10b-fp8-fp8_{decode}_sheet.jsonl"  # modal_app.py, H200
       for decode in ("free", "grammar2")},
    "Qwen3.5-122B-A10B picks among 3 fp8 grammar v2 samples (pick.py)": "qwen3.5-122b-a10b_pick_grammar2.jsonl",
    **{f"{name} {start} first try + selection loop (verify.py)": f"{stem}_verify_{start}.jsonl"
       for name, stem in (("Gemma-4-31B bf16", "gemma-4-31b-it"), ("Qwen3.5-122B-A10B fp8", "qwen3.5-122b-a10b"),
                          ("Qwen3.8-27B nf4", "qwen3.8-27b"))
       for start in ("free", "grammar2")},
    **{f"{name} {start} first try + selection loop, {label}": f"{stem}_verify_{start}_{suffix}.jsonl"
       for name, stem in (("Gemma-4-31B bf16", "gemma-4-31b-it"), ("Qwen3.5-122B-A10B fp8", "qwen3.5-122b-a10b"),
                          ("Qwen3.8-27B nf4", "qwen3.8-27b"))
       for start in ("free", "grammar2")
       for suffix, label in (("pdb5", "PDB numbers shown, 5 rounds"), ("plain5", "5 rounds"))},  # plain5: 27B only
    **{f"Gemma-4-31B bf16 {start} first try + selection loop, reasoning on": f"gemma-4-31b-it_verify_{start}_think.jsonl"
       for start in ("free", "grammar2")},
    "Gemma-4-31B-it (OpenRouter), view, reasoning on": "gemma-4-31b-it_think_view.jsonl",
    **{f"Gemma-4-31B bf16 reasons, then answers {d} (think.py; 307 of 375 rows)": f"gemma-4-31b-it-bf16_think-{d}_sheet.jsonl"
       for d in ("free", "grammar2")},
    "Qwen3.8-27B picks among grammar v2 + free samples (pick.py)": "qwen3.8-27b_pick_both.jsonl",
    "Qwen2.5-7B-4bit free, view": "qwen_free_view.jsonl",
    "Qwen2.5-7B-4bit grammar, view": "qwen_grammar_view.jsonl",
    "Qwen2.5-7B-4bit grammar, view + map": "qwen_grammar_map.jsonl",
    **{f"Qwen2.5-{size} nf4 {decode}, {layout}": f"qwen2.5-{size.lower()}-instruct-nf4_{decode}_{layout}.jsonl"  # decode.py
       for size in ("7B", "14B")
       for decode, layout in (("free", "task"), ("grammar1", "task"), ("grammar2", "task"), ("checked", "task"),
                              ("grammar2", "sheet"))},
    **{f"Qwen2.5-7B nf4 {decode}, task, after the qwen.Sheet fix": f"qwen2.5-7b-instruct-nf4_{decode}_task_fixed.jsonl"
       for decode in ("grammar1", "grammar2", "checked")},  # grammar1: 218 of 375 rows (Kaggle quota)
}
STAGES = [("verdict", "first try"), ("checker_verdict", "+ checker repair"), ("lint_verdict", "+ lint repair"),
          ("verify_verdict", "+ selection loop (verify.py)")]


def rate(rows, key="verdict"):
    n = len(rows)
    k = sum(r[key] == "EXACT" for r in rows)
    return f"{k}/{n} ({100 * k / n:.0f}%)" if n else "–"


def main():
    runs = {label: [rescore(json.loads(line)) for line in (HERE / "results" / f).read_text().splitlines()]
            for label, f in FILES.items() if (HERE / "results" / f).exists()}
    out = ["# Mask bench results", "",
           "Generated by `masks/bench/report.py` from the masks in `masks/bench/results/*.jsonl`, rescored by "
           "ambmask against the current gold. A rate is exact atom-set matches over tasks attempted, summed over "
           "runs (runs = independent samples of the whole set).", "",
           "Constrained arms decoded before `qwen.Sheet` was fixed on 2026-10-04 had to write a newline before "
           "the reply could end, which pushed masks on toward the length cap: every answer of a constrained 'task' "
           "arm (the Qwen2.5 grammar and checked task arms, and the 27B arm marked so) and the last task of each "
           "constrained sheet. See docs/research_notes/masks_bench.md.", ""]

    out += ["## Overall", "", "| arm | runs | " + " | ".join(s for _, s in STAGES) + " | first-try failures: rejected / "
            "empty / wrong atoms / missing |", "|---|---|" + "---|" * len(STAGES) + "---|"]
    for label, rows in runs.items():
        cells = [rate(rows, k) if k in rows[0] else "–" for k, _ in STAGES]
        c = Counter(r["verdict"] for r in rows)
        out.append(f"| {label} | {len({r['run'] for r in rows})} | " + " | ".join(cells)
                   + f" | {c['rejected']} / {c['empty']} / {c['wrong atoms']} / {c['missing']} |")

    for split in ("dev", "test"):
        out += ["", f"## First try, lint repair and selection loop, {split} split", "",
                "| arm | first try | + lint repair | + selection loop |", "|---|---|---|---|"]
        for label, rows in runs.items():
            rs = [r for r in rows if r["split"] == split]
            later = [rate(rs, k) if k in rows[0] else "–" for k in ("lint_verdict", "verify_verdict")]
            out.append(f"| {label} | {rate(rs)} | " + " | ".join(later) + " |")

    cats = sorted({r["category"] for rows in runs.values() for r in rows})
    out += ["", "## First try by category", "", "| category | " + " | ".join(runs) + " |",
            "|---|" + "---|" * len(runs)]
    for cat in cats:
        out.append(f"| {cat} | " + " | ".join(rate([r for r in rows if r["category"] == cat]) for rows in runs.values())
                   + " |")

    out += ["", "## First try by difficulty", "", "| difficulty | " + " | ".join(runs) + " |",
            "|---|" + "---|" * len(runs)]
    for d in (1, 2, 3):
        out.append(f"| {d} | " + " | ".join(rate([r for r in rows if r["difficulty"] == d]) for rows in runs.values())
                   + " |")

    out += ["", "## Tasks failed on every first try, per arm", ""]
    for label, rows in runs.items():
        by_id = defaultdict(list)
        for r in rows:
            by_id[r["id"]].append(r)
        never = sorted(i for i, rs in by_id.items() if all(r["verdict"] != "EXACT" for r in rs))
        out.append(f"- **{label}** ({len(never)} of {len(by_id)}): " + ", ".join(f"`{i}`" for i in never))
    print("\n".join(out))


if __name__ == "__main__":
    main()
