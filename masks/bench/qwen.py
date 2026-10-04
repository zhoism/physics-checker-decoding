"""Qwen2.5-7B-Instruct-4bit (MLX) on the mask bench, given exactly the prompt the Claude runs get
(blind.py): one prompt per system with its view and all its tasks, answered as a sheet.
'free' samples the sheet. 'grammar' holds it to the sheet: every '=== <id> ===' header in order, and
every mask in that system's mask grammar (masks/pilot/mask_grammar.py, compiled from its prmtop), by AWRS.
With 'lint', each sheet's failures get one repair sheet, decoded the same way, told what blind.py's
'lint' repair says (the checker's verdict and lint.py's hints; never the gold).
    .venv/bin/python masks/bench/qwen.py <free|grammar> <runs> <view|map> <out.jsonl> [lint]
"""
import asyncio
import json
import sys
import time
from pathlib import Path

from genlm.control import AWRS, Potential, PromptedLLM, direct_token_sampler

sys.path.insert(0, str(Path(__file__).parent))
from blind import FORMAT, LANG, TASKS, checker, parse, system_prompt, verdict  # noqa: E402
from lint import lint  # noqa: E402
from tasks import from_ranges  # noqa: E402

MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"


class Sheet(Potential):
    """'=== <id> ===\\n<mask>\\n' for every id in order, each mask in the system's grammar, then the end. The
    last newline is optional: the reply may end right after the last mask. When it was required, a model
    that wanted to stop there (most do) could not, and a newline less likely than ' &' made it run on to
    the length cap: every answer in a one-task prompt, and the last of each sheet."""

    def __init__(self, lang, ids):
        super().__init__(vocabulary=list(range(256)))
        self.lang, self.heads = lang, [f"=== {i} ===\n" for i in ids]

    def ok(self, text: str, done: bool) -> bool:
        pos = 0
        for k, head in enumerate(self.heads):
            rest = text[pos:]
            if not rest.startswith(head):
                return not done and head.startswith(rest)
            pos += len(head)
            nl = text.find("\n", pos)
            if nl < 0:
                if done:
                    return k == len(self.heads) - 1 and self.lang.accepts(text[pos:])
                return self.lang.accepts_prefix(text[pos:])
            if not self.lang.accepts(text[pos:nl]):
                return False
            pos = nl + 1
        return pos == len(text)

    async def prefix(self, context):
        b = bytes(context)
        return 0.0 if b.isascii() and self.ok(b.decode(), False) else float("-inf")

    async def complete(self, context):
        b = bytes(context)
        return 0.0 if b.isascii() and self.ok(b.decode(), True) else float("-inf")


async def sheet(llm, decode, system, prompt, ids):
    """One answer sheet for these task ids: (answers, raw text, sampler weight, tokens generated)."""
    chat = llm.model.tokenizer.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True)
    llm.prompt_ids = list(chat["input_ids"] if hasattr(chat, "keys") else chat)
    if decode == "grammar":
        sampler = AWRS(llm, Sheet(LANG[system], ids).coerce(llm, f=b"".join), proper_weights=False, max_rejects=2000)
    else:
        sampler = direct_token_sampler(llm)
    seqs = await sampler.smc(n_particles=1, ess_threshold=0.0, max_tokens=40 * len(ids))
    ctx, lw = seqs.contexts[0], float(seqs.log_weights[0])
    text = b"".join(x for x in ctx if isinstance(x, bytes)).decode("utf-8", "replace")
    return parse(text), text, lw, len(ctx)


async def main(decode, runs, arm, out, repair):
    llm = PromptedLLM.from_name(MODEL, backend="mlx", temperature=0.7)
    rows = []
    for run in range(runs):
        for system in sorted(LANG):
            tasks = [t for t in TASKS if t["system"] == system]
            head = system_prompt(system, arm)
            body = "".join(f"TASK {t['id']}\nSelect {t['text']}.\n\n" for t in tasks)
            t0 = time.time()
            answers, text, lw, n_gen = await sheet(llm, decode, system, f"{head}TASKS\n{body}{FORMAT}",
                                                   [t["id"] for t in tasks])
            new = []
            for t in tasks:
                m = answers.get(t["id"])
                new.append({"model": "qwen2.5-7b-4bit", "decode": decode, "arm": arm, "run": run, "system": system,
                            "id": t["id"], "category": t["category"], "difficulty": t["difficulty"],
                            "split": t["split"], "mask": m, "verdict": verdict(system, m, from_ranges(t["gold"])),
                            "dead": lw == float("-inf")})
            bad = [r for r in new if r["verdict"] != "EXACT"]
            if repair and bad:  # the lint repair blind.py gives Claude, as one more sheet
                fb = "".join(f"TASK {r['id']}\nSelect {next(t['text'] for t in tasks if t['id'] == r['id'])}.\n"
                             f"Your mask: {r['mask']}\nChecker: {checker(system, r['mask'] or '', r['verdict'])}\n"
                             + "".join(f"Hint: {h}\n" for h in lint(r["mask"] or "", LANG[system].top)) + "\n"
                             for r in bad)
                fixed, _, _, _ = await sheet(llm, decode, system, f"{head}Your masks for these tasks failed a check. "
                                             f"Write a corrected mask for each.\n\n{fb}{FORMAT}", [r["id"] for r in bad])
            for r in new:
                if repair:
                    r["lint_mask"] = fixed.get(r["id"], r["mask"]) if r in bad else r["mask"]
                    gold = from_ranges(next(t["gold"] for t in tasks if t["id"] == r["id"]))
                    r["lint_verdict"] = verdict(system, r["lint_mask"], gold) if r in bad else r["verdict"]
            rows += new
            n_ok = sum(r["verdict"] == "EXACT" for r in new)
            n_fix = sum(r.get("lint_verdict") == "EXACT" for r in new)
            print(f"{decode} {arm} run {run} {system}: {n_ok}/{len(tasks)} exact" + (f", {n_fix} after lint repair"
                  if repair else "") + f", {n_gen} tokens generated, {time.time() - t0:.0f}s", flush=True)
            Path(out).write_text("".join(json.dumps(r) + "\n" for r in rows))
            (Path(out).parent / f"{Path(out).stem}.{system}{run}.txt").write_text(text)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5:] == ["lint"]))
