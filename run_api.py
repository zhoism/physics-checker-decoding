"""Hosted-model arms on a prompt set, judged and logged exactly as run_arms.py judges and logs.

    uv run python run_api.py --provider gemini --list-models
    uv run python run_api.py --provider gemini --model <name> --prompts prompts/amber_phase1.jsonl --out results/x.jsonl
    uv run python run_arms.py --table results/x.jsonl

An API gives no next-token distribution, so the grammar, SMC and mask arms cannot run here.
Two arms can, and they are where checkers sit in shipped simulation agents:
  api-free    one completion
  api-repair  up to --rounds more completions, each told what the grammar, the checker and
              pmemd rejected in the last one: checker after decoding, with feedback
Keys are read from .env (git-ignored): GEMINI_API_KEY, DEEPSEEK_API_KEY or OPENROUTER_API_KEY.
"""
import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from run_arms import SYSTEM, judge, strip_fences

PROVIDERS = {  # all three speak the OpenAI chat-completions format
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "deepseek": ("https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
}


def key(name: str) -> str:
    env = Path(__file__).resolve().parent / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        k, _, v = line.partition("=")
        if k.strip() == name and v.strip():
            return v.strip()
    raise SystemExit(f"no {name} in .env")


def call(provider: str, path: str, body: dict | None = None) -> dict:
    base, var = PROVIDERS[provider]
    req = urllib.request.Request(
        f"{base}/{path}", data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key(var)}", "Content-Type": "application/json"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 5:  # rate limit or overload: back off
                time.sleep(2 ** attempt * 5)
                continue
            raise RuntimeError(f"HTTP {e.code}: {e.read()[:300]!r}") from None
    raise RuntimeError("unreachable")


def feedback(text: str, rec: dict) -> str:
    """What a repair loop is told: where the grammar stops, the checker's FAILs, pmemd's error."""
    from checkers import amber
    from checkers.amber_grammar import prefix_in_language

    body = strip_fences(text)
    notes = []
    if rec["truncated"]:
        notes.append("The file was cut off at the length limit before it ended.")
    if not rec["grammar"]:
        i = next((i for i in range(1, len(body) + 1) if not prefix_in_language(body[:i])), len(body))
        line = body[:i].rsplit("\n", 1)[-1] + body[i:].split("\n", 1)[0]
        notes.append(f"The file breaks the allowed mdin format at this line: {line.strip()!r} "
                     "(unknown keyword, wrong value type, comment, or bad structure).")
    notes += [f"{f.rule}: {f.detail}" for f in amber.ca.check_amber_in(amber._Text(body)).findings
              if f.level == "FAIL"]
    notes += [f"Each keyword may appear only once: {d}" for d in rec["duplicates"]]
    if not rec["pmemd"] and rec["pmemd_error"] != "truncated":
        notes.append(f"pmemd rejects the file: {rec['pmemd_error']}")
    return "The file has these problems:\n- " + "\n- ".join(notes) + "\nReply with the corrected file only."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=PROVIDERS, required=True)
    ap.add_argument("--model")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--prompts", default="prompts/amber_phase1.jsonl")
    ap.add_argument("--out")
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--rounds", type=int, default=3, help="repair rounds after the first try")
    ap.add_argument("--max-tokens", type=int, default=4096, help="room for a thinking model's reasoning")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--limit", type=int, help="first N prompts only")
    args = ap.parse_args()
    if args.list_models:
        for m in call(args.provider, "models")["data"]:
            print(m["id"])
        return
    prompts = [json.loads(line) for line in Path(args.prompts).read_text().splitlines() if line]
    prompts = prompts[: args.limit]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tokens = 0
    for seed in range(args.seeds):
        for p in prompts:
            msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": p["text"]}]
            t0, error, calls, used = time.time(), "", 0, 0
            history = []  # (record, text) per round; round 0 is api-free
            try:
                for _ in range(1 + args.rounds):
                    r = call(args.provider, "chat/completions", {
                        "model": args.model, "messages": msgs, "temperature": args.temperature,
                        "max_tokens": args.max_tokens})  # no seed: Gemini refuses the field
                    calls += 1
                    used += r.get("usage", {}).get("total_tokens", 0)
                    choice = r["choices"][0]
                    text = choice["message"].get("content") or ""
                    # APIs trim trailing whitespace, and pmemd needs a newline after the last '/'
                    text = text if not text or text.endswith("\n") else text + "\n"
                    rec = judge(text, choice.get("finish_reason") == "length")
                    history.append((rec, text, round(time.time() - t0, 2), calls, used))
                    if rec["valid"] and rec["pmemd"]:
                        break
                    msgs += [{"role": "assistant", "content": text},
                             {"role": "user", "content": feedback(text, rec)}]
            except Exception as e:  # an API failure counts as a failed sample, logged
                error = repr(e)[:300]
                if not history:
                    history.append((judge("", True), "", round(time.time() - t0, 2), calls, used))
            tokens += used
            for arm, (rec, text, secs, n, tok) in (("api-free", history[0]), ("api-repair", history[-1])):
                row = {"prompt": p["id"], "arm": arm, "seed": seed, "model": f"{args.provider}/{args.model}",
                       "temperature": args.temperature, "max_rejects": None, "n_particles": 1, **rec,
                       "logw": 0.0, "sampler_error": error, "particles_valid": int(rec["valid"]),
                       "llm_calls": n, "checker_calls": n, "tokens": tok, "seconds": secs, "text": text}
                with out.open("a") as f:
                    f.write(json.dumps(row) + "\n")
            last = history[-1][0]
            print(f"{p['id']:<26} seed={seed} rounds={calls} valid={last['valid']!s:<5} "
                  f"pmemd={last['pmemd']!s:<5} first-try valid={history[0][0]['valid']!s:<5} "
                  f"tokens={used} {error[:80]}", flush=True)
    print(f"total tokens: {tokens}")


if __name__ == "__main__":
    main()
