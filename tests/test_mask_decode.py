"""decode.py's PrefixLM gives what an uncached forward gives, whatever the next query does to the cached
sequence: extend it, branch off it at the checkpoint, or start over. Run on two tiny random models: a Qwen2
(attention only) and a Qwen3.5 (hybrid: linear-attention layers keep a running state that cannot be cut
back, hence snapshots). The Qwen2.5 tokenizer comes from the local Hugging Face cache; skips without it or
without the built systems (decode.py imports blind.py)."""
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
    torch.manual_seed(0)
    if kind == "qwen2":
        return Qwen2ForCausalLM(Qwen2Config(vocab_size=vocab, hidden_size=32, intermediate_size=64, num_hidden_layers=2,
                                            num_attention_heads=4, num_key_value_heads=2)).eval()
    return Qwen3_5ForCausalLM(Qwen3_5TextConfig(
        vocab_size=vocab, hidden_size=32, intermediate_size=64, num_hidden_layers=4, num_attention_heads=4,
        num_key_value_heads=2, head_dim=8, linear_num_key_heads=2, linear_num_value_heads=4, linear_key_head_dim=8,
        linear_value_head_dim=8, full_attention_interval=2)).eval()


@pytest.mark.parametrize("kind", ["qwen2", "qwen3_5"])
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
