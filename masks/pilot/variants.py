"""Mask generation arms on the 10 pilot tasks: prompt (plain | cheat) x decoding (free | grammar).
    .venv/bin/python variants.py <plain|cheat> <free|grammar> <n> <out.jsonl>"""
import asyncio
import json
import sys
import time
from pathlib import Path

from genlm.control import AWRS, PromptedLLM, direct_token_sampler

sys.path.insert(0, str(Path(__file__).parent))
from grammar_arm import MaskGrammar  # noqa: E402  (also defines LANG from the topology)

HERE = Path(__file__).parent
MODEL = "mlx-community/Qwen2.5-7B-Instruct-4bit"
BASE = ("You write AMBER atom-selection masks in the syntax that pmemd and ambmask accept. Reply with the "
        "mask only: no quotes, no code fences, no explanation.\n")
# Every rule and example below was checked against ambmask; no example is a test answer.
CHEAT = """AMBER mask syntax:
- ':' selects residues by number, range or name: ':5', ':3-40', ':ALA,GLY', ':2,7,10-12'
- '@' selects atoms by name, number or (with %) atom type: '@CB', '@CB,CG', '@20-80', '@%CT'
- residues then atoms: ':3-40@CB' is the CB atoms of residues 3 to 40
- '=' is the wildcard for the rest of a name: '@C=' is every atom whose name starts with C, ':GL=' is GLU and GLY.
  '*' alone means everything (':*', '@*'). There is no other wildcard: '?' and 'H*' are errors.
- '!' is not, '&' is and, '|' is or, and parentheses group: ':3-40&!@C=' is the atoms of residues 3-40 whose names do not start with C
- distance: '<' or '>' then ':' (whole residues) or '@' (atoms) then a cutoff in Angstrom: ':ALA<:4.0' is every residue within 4 A of an alanine
- this is not VMD or MDAnalysis syntax: no words like protein, name, resname, resid, and, or, not, within
"""


async def main(prompt_kind, decode, n, out):
    system = BASE + (CHEAT if prompt_kind == "cheat" else "") + (HERE / "system.txt").read_text()
    t0 = time.time()
    llm = PromptedLLM.from_name(MODEL, backend="mlx", temperature=0.7)
    grammar = MaskGrammar().coerce(llm, f=b"".join)
    tok = llm.model.tokenizer
    tasks = [json.loads(line) for line in (HERE / "tasks.jsonl").read_text().splitlines()]
    with open(out, "w") as f:
        for t in tasks:
            ids = tok.apply_chat_template([{"role": "system", "content": system},
                                           {"role": "user", "content": f"Select {t['text']}."}],
                                          add_generation_prompt=True)
            llm.prompt_ids = list(ids["input_ids"] if hasattr(ids, "keys") else ids)
            for s in range(n):
                sampler = (AWRS(llm, grammar, proper_weights=False, max_rejects=2000) if decode == "grammar"
                           else direct_token_sampler(llm))
                seqs = await sampler.smc(n_particles=1, ess_threshold=0.0, max_tokens=48)
                ctx, lw = seqs.contexts[0], float(seqs.log_weights[0])
                mask = b"".join(x for x in ctx if isinstance(x, bytes)).decode("utf-8", "replace").strip()
                f.write(json.dumps({"id": t["id"], "sample": s, "mask": mask, "dead": lw == float("-inf")}) + "\n")
    print(f"{prompt_kind}/{decode}: {len(tasks) * n} masks in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]))
