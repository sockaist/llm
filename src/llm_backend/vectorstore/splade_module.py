from transformers import AutoModelForMaskedLM, AutoTokenizer
import torch
import numpy as np
import warnings
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace

warnings.filterwarnings("ignore", message="BertForMaskedLM has generative capabilities")

_MODEL_NAME = "naver/splade-cocondenser-ensembledistil"

# --------------------------------------------------------
# 모델 로드
# --------------------------------------------------------
trace(f"Initializing SPLADE model '{_MODEL_NAME}'")

try:
    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME)
    model = AutoModelForMaskedLM.from_pretrained(_MODEL_NAME)
    model.eval()
    logger.info(f"[SPLADE] Model loaded successfully: '{_MODEL_NAME}'")
except Exception as e:
    logger.error(f"[SPLADE] Failed to load model '{_MODEL_NAME}': {e}")
    tokenizer, model = None, None


# --------------------------------------------------------
# SPLADE 인코딩 함수
# --------------------------------------------------------

@torch.no_grad()
def splade_encode(text: str, max_length: int = 256, threshold: float = 0.01) -> dict:
    """
    SPLADE 방식으로 희소 벡터 생성
    - 토큰별 중요도(log(1 + ReLU(logits)))의 max-pooling 기반
    - threshold 이하의 값은 0으로 잘라냄
    - Qdrant 호환을 위해 key를 문자열(str)로 변환
    """
    if not text or not text.strip():
        logger.warning("[SPLADE] Empty or whitespace-only text received.")
        return {}

    if tokenizer is None or model is None:
        logger.error("[SPLADE] Model not initialized. Cannot encode text.")
        raise RuntimeError("SPLADE model not initialized properly.")

    try:
        trace("Encoding text with SPLADE")
        tokens = tokenizer(text, return_tensors="pt", truncation=True, max_length=max_length)
        logits = model(**tokens).logits.squeeze(0)  # (seq_len, vocab_size)
        weights = torch.log1p(torch.relu(logits)).max(dim=0).values  # (vocab_size,)
        weights = weights.cpu().numpy()

        # threshold 이상인 값만 추출
        idxs = np.nonzero(weights > threshold)[0]
        vals = weights[idxs]

        encoded = {str(i): float(v) for i, v in zip(idxs, vals)}
        logger.debug(f"[SPLADE] Encoded vector with {len(encoded)} nonzero entries.")
        return encoded

    except Exception as e:
        logger.error(f"[SPLADE] Encoding failed: {e}")
        return {}


@torch.no_grad()
def splade_batch_encode(texts, max_length: int = 256, threshold: float = 0.01):
    """
    여러 문장을 한 번에 SPLADE 인코딩
    """
    if tokenizer is None or model is None:
        logger.error("[SPLADE] Model not initialized. Cannot perform batch encoding.")
        raise RuntimeError("SPLADE model not initialized properly.")

    trace(f"Batch SPLADE encoding started for {len(texts)} texts.")
    results = []

    for idx, text in enumerate(texts):
        try:
            results.append(splade_encode(text, max_length=max_length, threshold=threshold))
        except Exception as e:
            logger.warning(f"[SPLADE] Skipping text #{idx} due to error: {e}")

    logger.debug(f"[SPLADE] Batch encoding complete ({len(results)} items).")
    return results