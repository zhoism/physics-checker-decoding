"""The decoding arms on a CUDA box: is the checker better in the decoder or after it? Driven by
colab/arms.ipynb, which runs it on Colab or Kaggle; results are scored again locally by report.py.

Qwen2.5-Instruct answers each bench task in its own prompt, built exactly as blind.py builds a sheet
(blind.system_prompt and blind.FORMAT), here with one task. Every prompt for a system starts with the same
view, so PrefixLM prefills the view once and each decoding step runs one token.
Decodes:
  free      the model as it is
  grammar1  each answer held by AWRS to the v1 mask grammar (masks/pilot/mask_grammar.py), as qwen.py did
  grammar2  the same with the v2 grammar (mask_grammar2.py)
  checked   grammar2, and a finished mask must also be read by ambmask and select at least one atom
Every first-try failure then gets one lint repair, decoded the same way. The repair message is blind.py's
'lint' message (the checker's verdict and lint.py's hints). As in blind.py, a failure is judged against the
gold, but the gold is never shown. Layout 'task' is one prompt per task; 'sheet' is qwen.py's whole-system
sheet, the prompt Claude gets.
    python masks/bench/decode.py <hf model> <nf4|fp16|fp32> <runs> <out dir> <tasks per system|all> <decode:layout>...
writes <out dir>/<model>-<quant>_<decode>_<layout>.jsonl, one row per task, appended as it finishes.
"""
import asyncio
import copy
import functools
import hashlib
import json
import sys
import time
from pathlib import Path

import torch
from genlm.backend.llm.base import AsyncLM
from genlm.control import AWRS, PromptedLLM, direct_token_sampler

sys.path.insert(0, str(Path(__file__).parent))
from blind import FORMAT, LANG, TASKS, checker, parse, system_prompt, verdict  # noqa: E402
from lint import lint  # noqa: E402
from mask_grammar2 import MaskLanguage2  # noqa: E402
from qwen import Sheet  # noqa: E402
from tasks import from_ranges, select  # noqa: E402

TEMPERATURE = 0.7
MAX_TOKENS = 128  # per task: a header, a mask of at most 79 characters, and room for a free model to talk


class PrefixLM(AsyncLM):
    """A Hugging Face causal LM serving one sequence at a time. It keeps the cache of the last query, and a
    snapshot taken at checkpoint(): the start every prompt for a system shares (its view). A query that
    extends the last one runs only its new tokens; one that starts with the checkpoint restores a copy of the
    snapshot and runs the rest. A copy, not a crop: a hybrid model (Qwen3.5 and later) keeps a running state
    in its linear-attention layers that cannot be cut back. Only the last position's logits are computed."""

    def __init__(self, model, tokenizer, chunk=256):  # small prefill pieces: the 27B ran out of memory at 1024
        self.model, self.chunk = model, chunk
        self.ids, self.kv, self.logprobs = [], None, None
        self.snap_ids, self.snap_kv = [], None
        super().__init__(tokenizer)

    @classmethod
    def from_name(cls, name, quant="nf4"):
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        q = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                               bnb_4bit_compute_dtype=torch.float16) if quant == "nf4" else None
        dtype = torch.float32 if quant == "fp32" else torch.float16  # a T4 has no bf16
        model = AutoModelForCausalLM.from_pretrained(name, quantization_config=q, dtype=dtype,
                                                     device_map=cls.device_map(name, torch.cuda.device_count()))
        return cls(model.eval(), AutoTokenizer.from_pretrained(name))

    @staticmethod
    def device_map(name, n_gpu):
        """Layers split evenly by hand, the input embedding on the first GPU and the output layer on the last.
        'auto' put 5.4 GiB of the 4-bit 27B on one T4 and filled the other, which then ran out on the first
        prompt; capping each GPU instead made the 4-bit loader refuse to start."""
        if n_gpu < 2:
            return "auto" if n_gpu else None
        from transformers import AutoConfig
        layers = AutoConfig.from_pretrained(name).get_text_config().num_hidden_layers
        return {"model.embed_tokens": 0, "model.rotary_emb": 0, "model.norm": n_gpu - 1, "lm_head": n_gpu - 1,
                **{f"model.layers.{i}": i * n_gpu // layers for i in range(layers)}}

    @torch.no_grad()
    def _run(self, ids, kv):
        for i in range(0, len(ids), self.chunk):
            out = self.model(input_ids=torch.tensor([ids[i:i + self.chunk]], device=self.model.device),
                             past_key_values=kv, use_cache=True, logits_to_keep=1)
            kv = out.past_key_values
        logprobs = torch.log_softmax(out.logits[0, -1].float(), -1)
        assert torch.isfinite(logprobs).any(), "the model returned no finite logits (fp16 overflow?)"
        return kv, logprobs

    def checkpoint(self, ids):
        if list(ids) != self.snap_ids:
            self.snap_ids = list(ids)
            self.snap_kv, _ = self._run(self.snap_ids, None)

    def next_token_logprobs_sync(self, token_ids, lora_name=None):
        ids = list(token_ids)
        if ids == self.ids:
            return self.logprobs
        if self.kv is not None and len(ids) > len(self.ids) and ids[:len(self.ids)] == self.ids:
            kv, start = self.kv, len(self.ids)
        elif self.snap_kv is not None and len(ids) > len(self.snap_ids) and ids[:len(self.snap_ids)] == self.snap_ids:
            kv, start = copy.deepcopy(self.snap_kv), len(self.snap_ids)
        else:
            kv, start = None, 0
        self.kv, self.logprobs = self._run(ids[start:], kv)
        self.ids = ids
        return self.logprobs

    async def next_token_logprobs(self, token_ids, lora_name=None):
        return self.next_token_logprobs_sync(token_ids)


class Checked:
    """The checker in the decoder: grammar v2, and a finished mask must be one ambmask reads and that selects
    at least one atom. A mask is finished when the sheet's newline follows it (qwen.Sheet)."""

    def __init__(self, lang, system):
        self.lang, self.system, self.top = lang, system, lang.top

    def accepts_prefix(self, text):
        return self.lang.accepts_prefix(text)

    @functools.lru_cache(maxsize=65536)
    def accepts(self, text):
        return self.lang.accepts(text) and bool(select(self.system, text)[0])


@functools.cache
def languages(decode):
    if decode == "grammar1":
        return LANG
    v2 = {s: MaskLanguage2(Path(__file__).parent / "systems" / s / "sys.parm7") for s in LANG}
    return v2 if decode == "grammar2" else {s: Checked(v2[s], s) for s in v2}


def first_prompt(system, tasks):
    body = "".join(f"TASK {t['id']}\nSelect {t['text']}.\n\n" for t in tasks)
    return f"{system_prompt(system, 'view')}TASKS\n{body}{FORMAT}"


def repair_prompt(system, rows):
    """blind.py's 'lint' repair, for these failed rows."""
    fb = "".join(f"TASK {r['id']}\nSelect {next(t['text'] for t in TASKS if t['id'] == r['id'])}.\n"
                 f"Your mask: {r['mask']}\nChecker: {checker(system, r['mask'] or '', r['verdict'])}\n"
                 + "".join(f"Hint: {h}\n" for h in r["lint_hints"]) + "\n" for r in rows)
    return (f"{system_prompt(system, 'view')}Your masks for these tasks failed a check. Write a corrected mask "
            f"for each.\n\n{fb}{FORMAT}")


def seed_of(*key) -> int:
    return int(hashlib.sha256("|".join(map(str, key)).encode()).hexdigest()[:8], 16)


def chat_ids(llm, prompt):
    chat = llm.model.tokenizer.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True,
                                                   enable_thinking=False)  # Qwen3 and later answer directly
    return list(chat["input_ids"] if hasattr(chat, "keys") else chat)


_HEADS = {}


def head_ids(llm, system):
    """The token ids every prompt for this system starts with (its view): PrefixLM's checkpoint."""
    if system not in _HEADS:
        t = next(t for t in TASKS if t["system"] == system)
        a = chat_ids(llm, first_prompt(system, [t]))
        b = chat_ids(llm, repair_prompt(system, [{"id": t["id"], "mask": None, "verdict": "missing", "lint_hints": []}]))
        _HEADS[system] = a[:next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))]
    return _HEADS[system]


async def answer(llm, decode, system, prompt, ids, seed):
    """One reply: (answers by id, raw text, sampler weight is -inf, tokens generated, sampler error). The weight
    is -inf when a grammar arm reached max_tokens unfinished (genlm then forces EOS, which the grammar refuses;
    'truncated' in the row), or when no token was valid. With the grammar alone that cannot happen; with the
    checker it can, at the length cap, when every way to finish the mask selects nothing. The reply then ends
    on a rejected token, which is dropped, so the answer is the model's own last valid prefix."""
    llm.prompt_ids = chat_ids(llm, prompt)
    llm.model.checkpoint(head_ids(llm, system))
    torch.manual_seed(seed)
    if decode == "free":
        sampler = direct_token_sampler(llm)
    else:
        # No rejection limit: one particle cannot recover from a dead step, and the grammar never strands a
        # prefix (tests/test_mask_grammar2.py), so the search always ends on a valid token. With qwen.py's 2000,
        # the Kaggle smoke run lost answers whose only valid next token was EOS, kept far down by the model.
        sampler = AWRS(llm, Sheet(languages(decode)[system], ids).coerce(llm, f=b"".join), proper_weights=False,
                       max_rejects=float("inf"), seed=seed)
    try:
        seqs = await sampler.smc(n_particles=1, ess_threshold=0.0, max_tokens=MAX_TOKENS * len(ids))
    except torch.cuda.OutOfMemoryError:
        raise
    except Exception as e:  # logged as this answer's failure (DEVLOG: recursive_awrs once crashed on an assert)
        return {}, "", True, 0, repr(e)
    ctx, lw = seqs.contexts[0], float(seqs.log_weights[0])
    dead, n = lw == float("-inf"), len(ctx)
    if dead and n < MAX_TOKENS * len(ids) and ctx and isinstance(ctx[-1], bytes):
        ctx = ctx[:-1]
    text = b"".join(x for x in ctx if isinstance(x, bytes)).decode("utf-8", "replace")
    return parse(text), text, dead, n, None


async def attempt(llm, model, decode, layout, run, system, tasks):
    """First try for these tasks (one prompt), then one lint repair of the failures (one prompt)."""
    t0 = time.time()
    ids = [t["id"] for t in tasks]
    got, text, dead, n, err = await answer(llm, decode, system, first_prompt(system, tasks), ids,
                                           seed_of(decode, layout, run, *ids))
    rows = []
    for t in tasks:
        m = got.get(t["id"])
        rows.append({"model": model, "decode": decode, "arm": "view", "layout": layout, "run": run,
                     "system": system, "id": t["id"], "category": t["category"], "difficulty": t["difficulty"],
                     "split": t["split"], "mask": m, "verdict": verdict(system, m, from_ranges(t["gold"])),
                     "dead": dead, "truncated": n >= MAX_TOKENS * len(tasks), "error": err, "raw": text,
                     "tokens": n})
    bad = [r for r in rows if r["verdict"] != "EXACT"]
    for r in bad:
        r["lint_hints"] = lint(r["mask"] or "", LANG[system].top)
    if bad:
        got, text, dead, n, err = await answer(llm, decode, system, repair_prompt(system, bad),
                                               [r["id"] for r in bad], seed_of(decode, layout, run, "lint", *ids))
    for r, t in zip(rows, tasks):
        if r in bad:
            r["lint_mask"] = got.get(r["id"], r["mask"])  # left out of the reply: kept unchanged, as in blind.py
            r["lint_verdict"] = verdict(system, r["lint_mask"], from_ranges(t["gold"]))
            r.update(lint_dead=dead, lint_truncated=n >= MAX_TOKENS * len(bad), lint_error=err, lint_raw=text,
                     lint_tokens=n)
        else:
            r["lint_mask"], r["lint_verdict"] = r["mask"], r["verdict"]
        r["seconds"] = round(time.time() - t0, 1)
    return rows


async def run(llm, model, decode, layout, runs, out, limit=None):
    """Append rows to out, skipping those already there, so a lost session resumes. Systems outermost, so
    the cached view is reused across runs."""
    out = Path(out)
    done = {(r["run"], r["id"]) for r in map(json.loads, out.read_text().splitlines())} if out.exists() else set()
    for system in sorted(LANG):
        tasks = [t for t in TASKS if t["system"] == system][:limit]
        for r in range(runs):
            todo = [t for t in tasks if (r, t["id"]) not in done]
            for group in ([todo] if layout == "sheet" and todo else [[t] for t in todo]):
                rows = await attempt(llm, model, decode, layout, r, system, group)
                with out.open("a") as f:
                    f.write("".join(json.dumps(x) + "\n" for x in rows))
                ok = sum(x["verdict"] == "EXACT" for x in rows)
                fixed = sum(x["lint_verdict"] == "EXACT" for x in rows)
                print(f"{model} {decode} {layout} run {r} {group[0]['id']}{'..' if len(group) > 1 else ''}: "
                      f"{ok}/{len(rows)} exact, {fixed} after lint repair, {rows[0]['seconds']}s", flush=True)


def load(name, quant):
    return PromptedLLM(PrefixLM.from_name(name, quant), temperature=TEMPERATURE)


async def main(name, quant, runs, out_dir, limit, arms):
    llm, tag = load(name, quant), f"{name.split('/')[-1].lower()}-{quant}"
    gib = (lambda f: f"{f() / 2**30:.1f} GiB") if torch.cuda.is_available() else (lambda f: "")
    placed = sorted(set(map(str, getattr(llm.model.model, "hf_device_map", {}).values())))
    print(tag, "loaded:", [gib(lambda: torch.cuda.memory_allocated(i)) for i in range(torch.cuda.device_count())],
          "placed on:", placed, flush=True)  # 'cpu' or 'disk' here would make it crawl
    for arm in arms:
        decode, layout = arm.split(":")
        await run(llm, tag, decode, layout, runs, Path(out_dir) / f"{tag}_{decode}_{layout}.jsonl", limit)
    print(tag, "done; peak", [gib(lambda: torch.cuda.max_memory_allocated(i)) for i in range(torch.cuda.device_count())],
          flush=True)


if __name__ == "__main__":
    name, quant, runs, out_dir, limit, *arms = sys.argv[1:]
    asyncio.run(main(name, quant, int(runs), out_dir, None if limit == "all" else int(limit), arms))
