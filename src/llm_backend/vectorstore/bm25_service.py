"""BM25 초기화 및 재학습 유틸리티."""

from __future__ import annotations

import json
import os

from llm_backend.utils.debug import trace
from llm_backend.utils.logger import logger
from llm_backend.vectorstore.config import BM25_PATH
from llm_backend.vectorstore.sparse_helper import bm25_fit, bm25_load


def fit_bm25_from_json_folder(base_path: str) -> int:
    """지정 폴더 아래 JSON 파일에서 텍스트를 수집해 BM25를 학습한다."""

    trace(f"fit_bm25_from_json_folder({base_path})")
    all_texts: list[str] = []

    for root, _, files in os.walk(base_path):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(root, fname), "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                txt = data.get("content") or data.get("contents")
                if txt:
                    all_texts.append(txt)
            except Exception:  # noqa: BLE001
                continue

    if not all_texts:
        raise RuntimeError("No data for BM25 fitting")

    bm25_fit(all_texts)
    logger.info(f"[BM25] Trained on {len(all_texts)} docs.")
    return len(all_texts)


def init_bm25(base_path: str = "./data", force_retrain: bool = False) -> int:
    """BM25 모델을 준비한다. force_retrain 시 기존 모델 삭제 후 재학습."""

    trace(f"init_bm25(base_path={base_path}, force_retrain={force_retrain})")

    if force_retrain and os.path.exists(BM25_PATH):
        os.remove(BM25_PATH)
        logger.warning(f"[BM25] Existing model at {BM25_PATH} removed (force_retrain=True)")

    if os.path.exists(BM25_PATH):
        bm25_load()
        logger.info(f"[BM25] Loaded existing model from {BM25_PATH}")
        return 0

    logger.info("[BM25] No existing model found. Training new BM25 vectorizer...")
    num_docs = fit_bm25_from_json_folder(base_path)
    logger.info(f"[BM25] Trained on {num_docs} documents and saved to {BM25_PATH}")
    return num_docs
