"""BM25 관리 유틸리티.

VectorDBManager의 BM25 초기화/재학습을 공통 진입점으로 묶어준다.
"""

from __future__ import annotations

from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.utils.logger import logger


def retrain_bm25(base_path: str = "./data", force_retrain: bool = True) -> int:
	"""재학습을 수행하고 학습 문서 수를 반환한다."""

	with acquire_manager() as mgr:
		if hasattr(mgr, "init_bm25"):
			mgr.init_bm25(base_path=base_path, force_retrain=force_retrain)
			logger.info(f"[BM25] retrain completed (force={force_retrain})")
			return 0

		# fallback: 구버전 인터페이스
		count = mgr.fit_bm25_from_json_folder(base_path)
		logger.info(f"[BM25] trained on {count} docs (fallback)")
		return count


def ensure_bm25_ready(base_path: str = "./data") -> None:
	"""기존 모델이 없으면 학습, 있으면 로드하도록 한다."""

	with acquire_manager() as mgr:
		if hasattr(mgr, "init_bm25"):
			mgr.init_bm25(base_path=base_path, force_retrain=False)
			return

		try:
			mgr.fit_bm25_from_json_folder(base_path)
		except Exception as exc:  # noqa: BLE001
			logger.error(f"[BM25] initialization failed: {exc}")
