"""Cross-encoder reranker 관리 유틸리티."""

from __future__ import annotations

from functools import lru_cache
from typing import Tuple

from llm_backend.vectorstore.reranker_module import load_cross_encoder
from llm_backend.utils.logger import logger


@lru_cache(maxsize=2)
def get_cross_encoder(model_name: str = "Dongjin-kr/ko-reranker") -> Tuple[object, object]:
	"""모델 이름에 따라 토크나이저와 모델을 1회만 로드한다."""

	tokenizer, model = load_cross_encoder(model_name)
	logger.info(f"[Reranker] Loaded cross-encoder '{model_name}' (cached)")
	return tokenizer, model
