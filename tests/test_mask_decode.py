"""decode.py's PrefixLM gives what an uncached forward gives, whatever the next query does to the cached
sequence: extend it, branch off it at the checkpoint, or start over. Run on three tiny random models: a Qwen2
(attention only), a Qwen3.5 (hybrid: linear-attention layers keep a running state that cannot be cut
back, hence snapshots) and a Gemma 4 (sliding-window layers keep only the last few tokens; 8 here, so the
prompts run past the window). The Qwen2.5 tokenizer comes from the local Hugging Face cache; skips without it
or without the built systems (decode.py imports blind.py). Also: the GPU split places every weight."""
import os
import sys
from pathlib import Path

import pytest
import torch

os.environ.setdefault("HF_HUB_OFFLINE", "1")
BENCH = Path(__file__).resolve().parent.parent / "masks" / "bench"
sys.path.insert(0, str(BENCH))


def tiny(kind, vocab):
    from transformers import Qwen2Config, Qwen2ForCausalLM
    from transformers.models.qwen3_5.configuration_qwen3_5 import Qwen3_5TextConfig
    from transformers.models.qwen3_5.modeling_qwen3_5 import Qwen3_5ForCausalLM
    from transformers.models.gemma4.configuration_gemma4 import Gemma4TextConfig
    from transformers.models.gemma4.modeling_gemma4 import Gemma4ForCausalLM
    torch.manual_seed(0)
    if kind == "qwen2":
        return Qwen2ForCausalLM(Qwen2Config(vocab_size=vocab, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                                            num_attention_heads=4, num_key_value_heads=2)).eval()
    if kind == "gemma4":  # the 31B's layout, shrunk: global layers with their own head size, keys used as values
        return Gemma4ForCausalLM(Gemma4TextConfig(
            vocab_size=vocab, hidden_size=32, intermediate_size=64, num_hidden_layers=4, num_attention_heads=4,
            num_key_value_heads=2, head_dim=8, global_head_dim=16, num_global_key_value_heads=1, attention_k_eq_v=True,
            sliding_window=8, layer_types=["sliding_attention", "full_attention"] * 2, hidden_size_per_layer_input=0,
            final_logit_softcapping=30.0)).eval()
    return Qwen3_5ForCausalLM(Qwen3_5TextConfig(
        vocab_size=vocab, hidden_size=32, intermediate_size=64, num_hidden_layers=4, num_attention_heads=4,
        num_key_value_heads=2, head_dim=8, linear_num_key_heads=2, linear_num_value_heads=4, linear_key_head_dim=8,
        linear_value_head_dim=8, full_attention_interval=2)).eval()


@pytest.mark.parametrize("kind", ["qwen2", "qwen3_5", "gemma4"])
def test_prefix_cache_matches_an_uncached_forward(kind):
    from transformers import AutoTokenizer
    if not all((BENCH / "systems" / s / "sys.parm7").exists() for s in ("bnbs", "tryp", "dna", "memb")):
        pytest.skip("systems not built: bash masks/bench/build.sh")
    try:
        tok = AutoTokenizer.from_pretrained("mlx-community/Qwen2.5-7B-Instruct-4bit")
    except OSError:
        pytest.skip("no Qwen2.5 tokenizer in the Hugging Face cache")
    from decode import PrefixLM
    model = tiny(kind, len(tok))
    lm = PrefixLM(model, tok, chunk=16)
    a = list(range(1000, 1050))
    b = a[:30] + [7, 8, 9]
    lm.checkpoint(a[:30])
    for q in (a, a + [5], a + [5, 6], b, b + [4], a, a[:1], a + [5], a + [5], a):
        with torch.no_grad():
            want = torch.log_softmax(model(torch.tensor([q])).logits[0, -1].float(), -1)
        assert torch.allclose(lm.next_token_logprobs_sync(q), want, atol=1e-5), q[-3:]


@pytest.mark.parametrize("name", ["google/gemma-4-31B-it", "Qwen/Qwen3.8-27B"])
def test_device_map_places_every_weight_and_balances_two_gpus(name):
    """Gemma 4 nests its text model under model.language_model, carries a vision tower and ties its output
    layer to the embedding: the split must still give every weight a GPU, and each GPU about the same bytes."""
    from transformers import AutoConfig, AutoModelForCausalLM
    try:
        config = AutoConfig.from_pretrained(name)
    except OSError:
        pytest.skip(f"no {name} config in the Hugging Face cache")
    from decode import PrefixLM
    dm = PrefixLM.device_map(name, 2, "nf4")
    with torch.device("meta"):
        model = AutoModelForCausalLM.from_config(config)
    load, seen = [0, 0], set()
    for n, p in model.named_parameters(remove_duplicate=False):
        key = n
        while key and key not in dm:
            key = key.rpartition(".")[0]
        assert key, f"{n} has no GPU"
        if id(p) not in seen:
            seen.add(id(p))
            load[dm[key]] += p.numel() * (2 if "embed_tokens" in n or n.startswith("lm_head") else 0.5)  # nf4
    assert min(load) / max(load) > 0.9, load
