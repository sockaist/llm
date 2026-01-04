"""
vectorstore 패키지 초기화 모듈
----------------------------------
Qdrant 벡터 DB 관련 주요 기능 (manager, helper, init 등)을 통합 인터페이스로 제공
"""

from qdrant_client import QdrantClient
from .config import QDRANT_URL, QDRANT_API_KEY

# 서브모듈 불러오기
from .vector_db_manager import VectorDBManager
from .vector_db_helper import upsert_folder, query_unique_docs
from . import auto_init  # 새로 이름 바꾼 파일

# 로깅 & 디버깅
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace, profile

__all__ = [
    "QdrantClient",
    "VectorDBManager",
    "upsert_folder",
    "query_unique_docs",
    "auto_init",
    "get_default_client",
    "init_vectorstore",
]


def get_default_client() -> QdrantClient:
    """환경변수 기반 기본 Qdrant 클라이언트"""
    trace("Creating default Qdrant client")
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        logger.info(f"Connected to Qdrant @ {QDRANT_URL}")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Qdrant: {e}")
        raise


def init_vectorstore():
    """
    VectorStore 자동 초기화
    - 컬렉션 스키마 검증 및 필요시 재생성
    """
    trace("Initializing VectorStore")
    with profile("VectorStore init"):
        try:
            client = get_default_client()
            auto_init.auto_recreate_collections(client)
            logger.info("VectorStore initialized successfully.")
        except Exception as e:
            logger.error(f"VectorStore initialization failed: {e}")
            raise
