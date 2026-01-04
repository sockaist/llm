# -*- coding: utf-8 -*-
"""
Sparse Engine for Vector Store.
Combines BM25 (TF-IDF) and SPLADE sparse vector operations.
Consolidated from legacy sparse_helper.py and bm25_service.py.
"""

import os
import json
import joblib
import warnings
import numpy as np
from typing import Union, List, Dict, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
from llm_backend.vectorstore.config import BM25_PATH

# Suppress common warnings
warnings.filterwarnings("ignore", message="BertForMaskedLM has generative capabilities")

# --- Global State for BM25 ---
_vectorizer = None
_bm25_fitted = False


# ==========================================================
# BM25 (TF-IDF based) Core Logic
# ==========================================================

def bm25_fit(corpus: List[str], save_path: str = BM25_PATH):
    """학습 데이터를 기반으로 BM25(TF-IDF) 벡터라이저를 학습하고 저장합니다."""
    global _vectorizer, _bm25_fitted
    try:
        trace(f"Fitting BM25 vectorizer on {len(corpus)} documents")
        vec = TfidfVectorizer(
            max_features=60000, 
            ngram_range=(1, 2), 
            sublinear_tf=True, 
            stop_words=None
        )
        vec.fit(corpus)
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(vec, save_path)
        
        _vectorizer = vec
        _bm25_fitted = True
        logger.info(f"[BM25] Vectorizer fitted and saved to {save_path}")
    except Exception as e:
        logger.error(f"[BM25] Fitting failed: {e}")
        raise


def bm25_load(load_path: str = BM25_PATH):
    """저장된 BM25 모델을 디스크에서 로드합니다."""
    global _vectorizer, _bm25_fitted
    if os.path.exists(load_path):
        try:
            _vectorizer = joblib.load(load_path)
            _bm25_fitted = True
            logger.info(f"[BM25] Model loaded successfully from {load_path}")
        except Exception as e:
            logger.error(f"[BM25] Failed to load model from {load_path}: {e}")
            _bm25_fitted = False
    else:
        logger.warning(f"[BM25] No saved model found at {load_path}")
        _bm25_fitted = False


def _ensure_bm25_ready():
    """BM25 벡터라이저가 로드되어 있는지 확인하고 필요시 로드합니다."""
    global _bm25_fitted
    if not _bm25_fitted:
        bm25_load()
        if not _bm25_fitted:
            raise RuntimeError("[BM25] Vectorizer is not initialized. Please fit or load a model first.")


def bm25_encode(text: Union[str, List[str]]) -> Union[Dict[int, float], List[Dict[int, float]]]:
    """텍스트를 BM25 희소 벡터(인덱스-값 쌍)로 변환합니다."""
    try:
        _ensure_bm25_ready()
    except RuntimeError:
        # Cold start: Allow ingestion without sparse vectors if model not trained
        is_batch = isinstance(text, list)
        if is_batch:
            return [{} for _ in text]
        return {}

    is_batch = isinstance(text, list)
    texts = text if is_batch else [text]
    if not texts:
        return [] if is_batch else {}

    try:
        vecs = _vectorizer.transform(texts)
        results = []
        for i in range(vecs.shape[0]):
            row = vecs.getrow(i).tocoo()
            # 1e-8 이하의 작은 값은 제거하여 희소성 유지
            encoded = {int(idx): float(val) for idx, val in zip(row.col, row.data) if val > 1e-8}
            results.append(encoded)

        return results if is_batch else results[0]
    except Exception as e:
        logger.error(f"[BM25] Encoding failed: {e}")
        return [] if is_batch else {}


# ==========================================================
# Higher-level Sparse Engine Services (Legacy bm25_service)
# ==========================================================

def fit_from_folder(base_path: str) -> int:
    """JSON 파일들이 위치한 폴더를 스캔하여 텍스트를 수집하고 BM25를 학습합니다."""
    trace(f"Fitting sparse engine from folder: {base_path}")
    all_texts = []

    for root, _, files in os.walk(base_path):
        for fname in files:
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(root, fname), "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                    content = data.get("content") or data.get("contents")
                    if content:
                        all_texts.append(content)
                except Exception:
                    continue

    if not all_texts:
        logger.warning(f"[Sparse] No valid text found in {base_path}")
        return 0

    bm25_fit(all_texts)
    return len(all_texts)


def init_sparse_engine(data_path: str = "./data", force_retrain: bool = False):
    """희소 엔진을 초기화하고 필요한 경우 재학습을 수행합니다."""
    if force_retrain and os.path.exists(BM25_PATH):
        os.remove(BM25_PATH)
        logger.info("[Sparse] Existing BM25 model removed for retraining")

    if not os.path.exists(BM25_PATH):
        logger.info("[Sparse] Initial training starting...")
        fit_from_folder(data_path)
    else:
        bm25_load()


# ==========================================================
# SPLADE (Sparse Lexical and Expansion) Core Logic
# ==========================================================

_splade_tokenizer = None
_splade_model = None


def _ensure_splade_ready():
    """SPLADE 모델과 토크나이저가 준비되도록 합니다 (지연 로드)."""
    global _splade_tokenizer, _splade_model
    if _splade_tokenizer is not None and _splade_model is not None:
        return

    from llm_backend.vectorstore.config import (
        SPLADE_MODEL_NAME, SPLADE_MAX_LENGTH, SPLADE_DEVICE
    )
    from transformers import AutoModelForMaskedLM, AutoTokenizer
    import torch

    trace(f"Loading SPLADE model '{SPLADE_MODEL_NAME}' on {SPLADE_DEVICE}")
    try:
        _splade_tokenizer = AutoTokenizer.from_pretrained(SPLADE_MODEL_NAME)
        _splade_model = AutoModelForMaskedLM.from_pretrained(SPLADE_MODEL_NAME)
        if SPLADE_DEVICE:
            _splade_model = _splade_model.to(SPLADE_DEVICE)
        _splade_model.eval()
        logger.info(f"[SPLADE] Model ready: '{SPLADE_MODEL_NAME}' on {SPLADE_DEVICE}")
    except Exception as e:
        logger.error(f"[SPLADE] Failed to load model '{SPLADE_MODEL_NAME}': {e}")
        raise


def splade_encode(
    text: Union[str, List[str]], 
    max_length: Optional[int] = None, 
    threshold: Optional[float] = None, 
    top_k: Optional[int] = None
) -> Union[Dict[str, float], List[Dict[str, float]]]:
    """SPLADE 방식을 사용하여 텍스트를 고차원 희소 벡터로 변환합니다."""
    if not text:
        return {} if isinstance(text, str) else []

    _ensure_splade_ready()
    import torch
    from llm_backend.vectorstore.config import (
        SPLADE_MAX_LENGTH, SPLADE_THRESHOLD, SPLADE_TOP_K
    )

    max_len = max_length or SPLADE_MAX_LENGTH
    th = SPLADE_THRESHOLD if threshold is None else threshold
    cap = top_k or SPLADE_TOP_K

    is_batch = isinstance(text, list)
    texts = text if is_batch else [text]

    try:
        tokens = _splade_tokenizer(
            texts, return_tensors="pt", padding=True, truncation=True, max_length=max_len
        )
        tokens = {k: v.to(_splade_model.device) for k, v in tokens.items()}

        with torch.no_grad():
            logits = _splade_model(**tokens).logits
            weights = torch.log1p(torch.relu(logits)).max(dim=1).values
            weights = weights.cpu().numpy()

        results = []
        for i in range(weights.shape[0]):
            row_weights = weights[i]
            idxs = np.nonzero(row_weights > th)[0]
            vals = row_weights[idxs]

            if cap and len(idxs) > cap:
                top_idx = np.argpartition(vals, -cap)[-cap:]
                idxs = idxs[top_idx]
                vals = vals[top_idx]

            encoded = {str(idx): float(val) for idx, val in zip(idxs, vals)}
            results.append(encoded)

        return results if is_batch else results[0]
    except Exception as e:
        logger.error(f"[SPLADE] Encoding failed: {e}")
        return [] if is_batch else {}


def splade_batch_encode(texts: List[str]) -> List[Dict[str, float]]:
    """여러 텍스트를 한 번에 SPLADE 인코딩합니다."""
    return splade_encode(texts)
