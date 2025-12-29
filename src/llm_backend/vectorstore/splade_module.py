from transformers import AutoModelForMaskedLM, AutoTokenizer
import torch
import numpy as np
import warnings
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
from llm_backend.vectorstore.config import (
    SPLADE_MODEL_NAME,
    SPLADE_MAX_LENGTH,
    SPLADE_THRESHOLD,
    SPLADE_DEVICE,
    SPLADE_TOP_K,
)

warnings.filterwarnings("ignore", message="BertForMaskedLM has generative capabilities")

# Lazy-loaded handles
tokenizer = None
model = None


def _ensure_model():
    """Load SPLADE model/tokenizer on first use with configured device."""
    global tokenizer, model
    if tokenizer is not None and model is not None:
        return

    trace(f"Loading SPLADE model '{SPLADE_MODEL_NAME}' on {SPLADE_DEVICE}")
    try:
        tok = AutoTokenizer.from_pretrained(SPLADE_MODEL_NAME)
        mdl = AutoModelForMaskedLM.from_pretrained(SPLADE_MODEL_NAME)
        if SPLADE_DEVICE:
            mdl = mdl.to(SPLADE_DEVICE)
        mdl.eval()
        tokenizer, model = tok, mdl
        logger.info(f"[SPLADE] Model ready: '{SPLADE_MODEL_NAME}' on {SPLADE_DEVICE}")
    except Exception as e:  # noqa: BLE001
        logger.error(f"[SPLADE] Failed to load model '{SPLADE_MODEL_NAME}': {e}")
        tokenizer, model = None, None
        raise


# --------------------------------------------------------
# SPLADE 인코딩 함수
# --------------------------------------------------------

from typing import Optional, Union, List, Dict

@torch.no_grad()
def splade_encode(
    text: Union[str, List[str]],
    max_length: Optional[int] = None,
    threshold: Optional[float] = None,
    top_k: Optional[int] = None,
) -> Union[Dict[str, float], List[Dict[str, float]]]:

    """
    SPLADE 방식으로 희소 벡터 생성
    - str 입력 시: Dict[str, float] 반환
    - List[str] 입력 시: List[Dict[str, float]] 반환
    """
    if not text:
        return {} if isinstance(text, str) else []

    _ensure_model()

    max_len = max_length or SPLADE_MAX_LENGTH
    th = SPLADE_THRESHOLD if threshold is None else threshold
    cap = top_k or SPLADE_TOP_K
    
    is_batch = isinstance(text, list)
    texts = text if is_batch else [text]
    
    # Empty check
    if all(not t.strip() for t in texts):
         return [] if is_batch else {}

    try:
        trace(f"Encoding text with SPLADE (Batch={len(texts)})")
        # Batch Tokenization
        tokens = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=max_len)
        tokens = {k: v.to(model.device) if hasattr(v, "to") else v for k, v in tokens.items()}
        
        logits = model(**tokens).logits  # (batch, seq, vocab)
        # Log(1 + ReLU(logits)) -> Max over sequence dimension (dim=1)
        weights = torch.log1p(torch.relu(logits)).max(dim=1).values  # (batch, vocab)
        weights = weights.cpu().numpy()

        results = []
        for i in range(weights.shape[0]):
            row_weights = weights[i]
            # Thresholding
            idxs = np.nonzero(row_weights > th)[0]
            vals = row_weights[idxs]

            # Top K Cap
            if cap and len(idxs) > cap:
                top_idx = np.argpartition(vals, -cap)[-cap:]
                idxs = idxs[top_idx]
                vals = vals[top_idx]

            encoded = {str(idx): float(val) for idx, val in zip(idxs, vals)}
            results.append(encoded)

        logger.debug(f"[SPLADE] Encoded batch of {len(results)} texts.")
        return results if is_batch else results[0]

    except Exception as e:
        logger.error(f"[SPLADE] Encoding failed: {e}")
        return [] if is_batch else {}


@torch.no_grad()
def splade_batch_encode(texts, max_length: int = 256, threshold: float = 0.01):
    """
    여러 문장을 한 번에 SPLADE 인코딩
    """
    _ensure_model()

    max_len = max_length or SPLADE_MAX_LENGTH
    th = SPLADE_THRESHOLD if threshold is None else threshold
    cap = SPLADE_TOP_K

    trace(f"Batch SPLADE encoding started for {len(texts)} texts.")
    results = []

    for idx, text in enumerate(texts):
        try:
            results.append(splade_encode(text, max_length=max_len, threshold=th, top_k=cap))
        except Exception as e:
            logger.warning(f"[SPLADE] Skipping text #{idx} due to error: {e}")

    logger.debug(f"[SPLADE] Batch encoding complete ({len(results)} items).")
    return results