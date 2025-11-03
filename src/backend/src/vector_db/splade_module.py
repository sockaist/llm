# splade_module.py
from transformers import AutoModelForMaskedLM, AutoTokenizer
import torch
import numpy as np
import warnings
warnings.filterwarnings("ignore", message="BertForMaskedLM has generative capabilities")

_MODEL_NAME = "naver/splade-cocondenser-ensembledistil"

print(f"[SPLADE] Loading model '{_MODEL_NAME}' ...")
tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
model = AutoModelForMaskedLM.from_pretrained(_MODEL_NAME)
model.eval()

@torch.no_grad()
def splade_encode(text: str, max_length: int = 256, threshold: float = 0.01) -> dict:
    """
    SPLADE 방식으로 희소 벡터 생성
    - 토큰별 중요도(log(1 + ReLU(logits)))의 max-pooling 기반
    - threshold 이하의 값은 0으로 잘라냄
    - Qdrant 호환을 위해 key를 문자열(str)로 변환
    """
    if not text or not text.strip():
        return {}

    tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)
    logits = model(**tokens).logits.squeeze(0)  # (seq_len, vocab_size)
    weights = torch.log1p(torch.relu(logits)).max(dim=0).values  # (vocab_size,)
    weights = weights.cpu().numpy()

    # threshold 이상인 값만 추출
    idxs = np.nonzero(weights > threshold)[0]
    vals = weights[idxs]

    return {str(i): float(v) for i, v in zip(idxs, vals)}


@torch.no_grad()
def splade_batch_encode(texts, max_length: int = 256, threshold: float = 0.01):
    """
    여러 문장을 한 번에 SPLADE 인코딩
    """
    res = []
    for text in texts:
        res.append(splade_encode(text, max_length=max_length, threshold=threshold))
    return res