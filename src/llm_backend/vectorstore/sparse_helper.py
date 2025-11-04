# -*- coding: utf-8 -*-
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import torch
import os
import joblib
from transformers import AutoTokenizer, AutoModelForMaskedLM
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
import warnings
from transformers.utils import logging as hf_logging

warnings.filterwarnings("ignore", message="BertForMaskedLM has generative capabilities")
hf_logging.set_verbosity_error()  # huggingface 전용 로거 수준 조정

# ==========================================================
# BM25 (TF-IDF 기반)
# ==========================================================

BM25_PATH = "./models/bm25_vectorizer.pkl"

vectorizer = None  # 동적으로 로드됨
_fitted = False


def bm25_fit(corpus, save_path: str = BM25_PATH):
    """
    전체 코퍼스 기준 BM25 벡터라이저 학습 및 저장
    """
    global vectorizer, _fitted
    try:
        trace("Fitting BM25 vectorizer on corpus")
        vectorizer = TfidfVectorizer(
            max_features=60000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            stop_words=None
        )
        vectorizer.fit(corpus)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(vectorizer, save_path)
        _fitted = True
        logger.info(f"[BM25] Vectorizer fitted & saved → {save_path}")
    except Exception as e:
        logger.error(f"[BM25] Fitting failed: {e}")
        raise


def bm25_load(load_path: str = BM25_PATH):
    """
    저장된 BM25 모델을 로드
    """
    global vectorizer, _fitted
    if os.path.exists(load_path):
        vectorizer = joblib.load(load_path)
        _fitted = True
        logger.info(f"[BM25] Loaded from {load_path}")
    else:
        logger.warning(f"[BM25] No saved model found at {load_path}. Need to fit manually.")
        _fitted = False


def ensure_bm25_loaded():
    """
    BM25 벡터라이저가 로드되어 있지 않으면 자동 로드
    """
    global _fitted
    if not _fitted:
        bm25_load()
        if not _fitted:
            raise RuntimeError("[BM25] Vectorizer not fitted or loaded.")


def bm25_encode(text: str) -> dict:
    """
    단일 텍스트를 BM25 희소 벡터(dict 형태)로 인코딩
    """
    ensure_bm25_loaded()
    try:
        trace("Encoding single text with BM25")
        vec = vectorizer.transform([text])
        coo = vec.tocoo()
        encoded = {int(i): float(v) for i, v in zip(coo.col, coo.data) if v > 1e-8}
        logger.debug(f"[BM25] Encoded vector with {len(encoded)} nonzero entries")
        return encoded
    except Exception as e:
        logger.error(f"[BM25] Encoding failed: {e}")
        return {}


def bm25_batch_encode(texts):
    """
    여러 문서를 한 번에 인코딩 (업서트용)
    """
    ensure_bm25_loaded()
    try:
        trace(f"[BM25] Encoding batch of {len(texts)} texts")
        vecs = vectorizer.transform(texts)
        coo = vecs.tocoo()
        res = [{} for _ in texts]
        for i, j, v in zip(coo.row, coo.col, coo.data):
            if v > 1e-8:
                res[i][int(j)] = float(v)
        logger.debug(f"[BM25] Batch encoding completed ({len(texts)} items)")
        return res
    except Exception as e:
        logger.error(f"[BM25] Batch encoding failed: {e}")
        return []

# ==========================================================
# SPLADE 희소 인코더
# ==========================================================

trace("Loading SPLADE tokenizer and model")
try:
    _tokenizer = AutoTokenizer.from_pretrained("naver/splade-cocondenser-ensembledistil")
    _model = AutoModelForMaskedLM.from_pretrained("naver/splade-cocondenser-ensembledistil")
    _model.eval()
    logger.info("SPLADE model successfully loaded: 'naver/splade-cocondenser-ensembledistil'")
except Exception as e:
    logger.error(f"[SPLADE] Model load failed: {e}")
    _tokenizer, _model = None, None


def splade_encode(text: str) -> dict:
    """
    SPLADE 모델을 이용해 단일 텍스트를 희소 벡터(dict 형태)로 변환
    """
    if not _tokenizer or not _model:
        raise RuntimeError("[SPLADE] Model not initialized properly.")
    try:
        trace("Encoding single text with SPLADE")
        with torch.no_grad():
            inputs = _tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
            logits = _model(**inputs).logits[0]
            activation = torch.log(1 + torch.relu(logits))
            values, _ = torch.max(activation, dim=0)
            coo = values.squeeze().cpu().numpy()
            nonzero = np.nonzero(coo > 1e-6)[0]
            encoded = {int(i): float(coo[i]) for i in nonzero}
            logger.debug(f"[SPLADE] Encoded vector with {len(encoded)} nonzero entries")
            return encoded
    except Exception as e:
        logger.error(f"[SPLADE] Encoding failed: {e}")
        return {}


def splade_batch_encode(texts):
    """
    여러 문서를 한 번에 SPLADE 희소 벡터로 변환
    """
    if not _tokenizer or not _model:
        logger.error("SPLADE model not initialized properly.")
        raise RuntimeError("SPLADE model not initialized properly.")

    trace(f"Encoding batch of {len(texts)} texts with SPLADE")
    results = []
    for t in texts:
        try:
            results.append(splade_encode(t))
        except Exception as e:
            logger.warning(f"SPLADE batch encode skipped a text due to error: {e}")
    logger.debug(f"SPLADE batch encoding completed ({len(results)} items)")
    return results