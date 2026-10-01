"""Grammar-constrained sampling of masks: the mask grammar as a genlm-control potential (AWRS).
Same model, prompt, temperature and tries as gen.py. Writes samples_grammar.jsonl."""
import asyncio
import json
import sys
import time
from pathlib import Path

from genlm.control import AWRS, Potential, PromptedLLM

sys.path.insert(0, str(Path(__file__).parent))
from mask_grammar import MaskLanguage  # noqa: E402

HERE = Path(__file__).parent
MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"
N = 3
SYSTEM = ("You write AMBER atom-selection masks in the syntax that pmemd and ambmask accept. Reply with the "
          "mask only: no quotes, no code fences, no explanation.\n" + (HERE / "system.txt").read_text())
LANG = MaskLanguage(HERE / "system" / "complex.parm7")


class MaskGrammar(Potential):
    def __init__(self):
        super().__init__(vocabulary=list(range(256)))

    async def complete(self, context):
        b = bytes(context)
        return 0.0 if b.isascii() and LANG.accepts(b.decode()) else float("-inf")

    async def prefix(self, context):
        b = bytes(context)
        return 0.0 if b.isascii() and LANG.accepts_prefix(b.decode()) else float("-inf")


async def main():
    t0 = time.time()
    llm = PromptedLLM.from_name(MODEL, backend="mlx", temperature=0.7)
    grammar = MaskGrammar().coerce(llm, f=b"".join)
    tok = llm.model.tokenizer
    print(f"model loaded in {time.time() - t0:.1f}s", flush=True)
    tasks = [json.loads(line) for line in (HERE / "tasks.jsonl").read_text().splitlines()]
    with (HERE / "samples_grammar.jsonl").open("w") as f:
        for t in tasks:
            ids = tok.apply_chat_template([{"role": "system", "content": SYSTEM},
                                           {"role": "user", "content": f"Select {t['text']}."}],
                                          add_generation_prompt=True)
            llm.prompt_ids = list(ids["input_ids"] if hasattr(ids, "keys") else ids)
            for s in range(N):
                t1 = time.time()
                seqs = await AWRS(llm, grammar, proper_weights=False, max_rejects=2000).smc(
                    n_particles=1, ess_threshold=0.0, max_tokens=48)
                ctx, lw = seqs.contexts[0], float(seqs.log_weights[0])
                mask = b"".join(x for x in ctx if isinstance(x, bytes)).decode("utf-8", "replace")
                f.write(json.dumps({"id": t["id"], "sample": s, "mask": mask, "dead": lw == float("-inf"),
                                    "seconds": round(time.time() - t1, 2)}) + "\n")
                print(f"{t['id']:16s} {s} {mask!r:40s} dead={lw == float('-inf')} {time.time() - t1:.1f}s", flush=True)
    print(f"total {time.time() - t0:.1f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
