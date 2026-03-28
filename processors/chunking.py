from typing import Iterable, List

import tiktoken
from transformers import AutoTokenizer


def chunk_text_tiktoken(text: str, model_name: str = "gpt-4", chunk_size: int = 2048) -> Iterable[str]:
    enc = tiktoken.encoding_for_model(model_name)
    token_ids = enc.encode(text)
    for i in range(0, len(token_ids), chunk_size):
        yield enc.decode(token_ids[i : i + chunk_size])


def chunk_text_hf(
    text: str,
    tokenizer_name: str = "bert-base-uncased",
    chunk_size: int = 2048,
    stride: int = 0,
) -> List[str]:
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
    ids = tokenizer.encode(text, add_special_tokens=False)
    chunks = []
    step = max(1, chunk_size - stride)
    for i in range(0, len(ids), step):
        piece = ids[i : i + chunk_size]
        chunks.append(tokenizer.decode(piece, skip_special_tokens=True))
    return chunks
