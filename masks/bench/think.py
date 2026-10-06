"""Think, then answer: does the grammar still add something once the model has reasoned?

The model (Gemma-4-31B, its thinking mode on) writes its reasoning for a whole sheet (blind.py's prompt)
freely. From that same reasoning the answer is decoded twice, free and held to grammar v2 (decode.answer,
AWRS), so the two answers share their thought and differ only in the decoder. First tries only, no repair.
Served with reasoning on (blind.py openrouter-think:), Gemma's first tries were 64% right and 22% rejected.
    python masks/bench/think.py <hf model> <bf16|nf4> <runs> <out dir> <tasks per system|all> [ignored...]
writes <out dir>/<model>-<quant>_think-free_sheet.jsonl and ..._think-grammar2_sheet.jsonl.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).parent))
from blind import LANG, TASKS, verdict  # noqa: E402
from decode import TEMPERATURE, answer, first_prompt, load, seed_of  # noqa: E402
from tasks import from_ranges  # noqa: E402

THOUGHT_MAX = 12000  # tokens of reasoning; past this the answer is made to start


def thought(llm, prompt, seed):
    """The prompt's ids with thinking on, and the model's reasoning through its end-of-thought token."""
    tok, model = llm.model.tokenizer, llm.model.model
    chat = tok.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True,
                                   enable_thinking=True)
    ids = list(chat["input_ids"] if hasattr(chat, "keys") else chat)
    close = tok.convert_tokens_to_ids("<channel|>")
    torch.manual_seed(seed)
    with torch.no_grad():  # plain sampling at the bench's temperature: no top-k or top-p from the model's config
        out = model.generate(torch.tensor([ids], device=model.device), max_new_tokens=THOUGHT_MAX, do_sample=True,
                             temperature=TEMPERATURE, top_k=0, top_p=1.0, eos_token_id=[close],
                             pad_token_id=tok.pad_token_id)
    gen = out[0, len(ids):].tolist()
    if not gen or gen[-1] != close:
        gen.append(close)
    return ids, gen


async def sheet(llm, tag, run, system, tasks):
    t0 = time.time()
    ids = [t["id"] for t in tasks]
    prompt_ids, gen = thought(llm, first_prompt(system, tasks), seed_of("think", run, *ids))
    t_think = time.time() - t0
    out = {}
    for decode in ("free", "grammar2"):
        got, text, dead, n, err = await answer(llm, decode, system, prompt_ids + gen, ids,
                                               seed_of("think", decode, run, *ids))
        out[decode] = [{"model": tag, "decode": f"think-{decode}", "arm": "view", "layout": "sheet", "run": run,
                        "system": system, "id": t["id"], "category": t["category"], "difficulty": t["difficulty"],
                        "split": t["split"], "mask": got.get(t["id"]),
                        "verdict": verdict(system, got.get(t["id"]), from_ranges(t["gold"])), "dead": dead,
                        "error": err, "raw": text, "tokens": n, "thought_tokens": len(gen),
                        "thought": llm.model.tokenizer.decode(gen) if t is tasks[0] else None,
                        "think_seconds": round(t_think, 1), "seconds": round(time.time() - t0, 1)} for t in tasks]
    return out


async def main(name, quant, runs, out_dir, limit):
    llm, tag = load(name, quant), f"{name.split('/')[-1].lower()}-{quant}"
    files = {d: Path(out_dir) / f"{tag}_think-{d}_sheet.jsonl" for d in ("free", "grammar2")}
    done = [{(r["run"], r["system"]) for r in map(json.loads, f.read_text().splitlines())} if f.exists() else set()
            for f in files.values()]
    for system in sorted(LANG):
        tasks = [t for t in TASKS if t["system"] == system][:limit]
        for run in range(runs):
            if all((run, system) in d for d in done):
                continue
            rows = await sheet(llm, tag, run, system, tasks)
            for d, f in files.items():
                with f.open("a") as fh:
                    fh.write("".join(json.dumps(x) + "\n" for x in rows[d]))
            print(f"{tag} think run {run} {system}: thought {rows['free'][0]['thought_tokens']} tokens in "
                  f"{rows['free'][0]['think_seconds']}s; free {sum(x['verdict'] == 'EXACT' for x in rows['free'])}, "
                  f"grammar2 {sum(x['verdict'] == 'EXACT' for x in rows['grammar2'])} of {len(tasks)}", flush=True)


if __name__ == "__main__":
    name, quant, runs, out_dir, limit = sys.argv[1:6]
    asyncio.run(main(name, quant, int(runs), out_dir, None if limit == "all" else int(limit)))
