"""Vector search utilities using the current Qdrant-backed manager.

This replaces the legacy archive implementation and keeps the public
interface expected by OpenAIChatBot (search_similar_documents and
format_search_results).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.utils.logger import logger


DEFAULT_COLLECTIONS = [
    "csweb.news",
    "csweb.ai",
    "csweb.admin",
    "csweb.profs",
    "notion.notice",
    "notion.marketing",
    "portal.job",
    "portal.startUp",
]


class VectorSearcher:
    """Lightweight helper that taps into the VectorDBManager via the pool."""

    def __init__(
        self,
        collections: Optional[List[str]] = None,
        default_top_k: int = 30,
    ):
        self.collections = collections or DEFAULT_COLLECTIONS
        self.default_top_k = default_top_k

    def search_similar_documents(
        self, query: str, top_k: Optional[int] = None, collections: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search similar documents across configured collections.

        Returns a list of {content, score, collection, metadata} dicts.
        """

        if not query or not query.strip():
            return []

        search_collections = collections or self.collections
        limit = top_k or self.default_top_k

        try:
            with acquire_manager() as mgr:
                results = mgr.query(
                    query_text=query,
                    top_k=limit,
                    collections=search_collections,
                )
                return self._hydrate_payloads(mgr, results)
        except Exception as exc:
            logger.error(f"[VectorSearcher] search failed: {exc}")
            return []

    def _hydrate_payloads(
        self, mgr, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fetch payload content for returned db_ids to feed the chatbot."""

        hydrated: List[Dict[str, Any]] = []
        if not results:
            return hydrated

        for res in results:
            db_id = res.get("db_id") or res.get("id") or res.get("parent_id")
            col = res.get("collection")
            if not db_id or not col:
                continue

            content = ""
            metadata: Dict[str, Any] = {}
            score = res.get("score") or res.get("avg_score") or 0.0
            title = res.get("title")

            try:
                fetched = mgr.client.retrieve(
                    collection_name=col,
                    ids=[db_id],
                    with_payload=True,
                )
                if fetched:
                    payload = fetched[0].payload or {}
                    content = payload.get("contents") or payload.get("content") or payload.get("text") or ""
                    metadata = {
                        "title": title or payload.get("title", ""),
                        "date": payload.get("date", ""),
                        "link": payload.get("link", ""),
                        "author": payload.get("author", ""),
                        "name": payload.get("name", ""),
                        "position": payload.get("position", ""),
                        "field": payload.get("field", ""),
                    }
                else:
                    logger.debug(f"[VectorSearcher] payload missing for {db_id} in {col}")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[VectorSearcher] payload fetch failed for {db_id} in {col}: {exc}")

            hydrated.append(
                {
                    "content": content,
                    "score": float(score) if score is not None else 0.0,
                    "collection": col,
                    "metadata": metadata,
                }
            )

        # Sort descending by score
        hydrated.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return hydrated

    @staticmethod
    def format_search_results(results: List[Dict[str, Any]]) -> str:
        """Format search results into a readable text block for prompts."""

        if not results:
            return "관련 정보를 찾을 수 없습니다."

        parts: List[str] = ["=== 관련 정보 ===\n"]
        for idx, res in enumerate(results, 1):
            meta = res.get("metadata", {})
            content = res.get("content", "")
            if len(content) > 300:
                content = content[:300] + "..."

            lines = [f"[정보 {idx}]"]
            if meta.get("title"):
                lines.append(f"제목: {meta['title']}")
            if meta.get("author"):
                lines.append(f"작성자: {meta['author']}")
            if meta.get("name"):
                lines.append(f"이름: {meta['name']}")
            if meta.get("position"):
                lines.append(f"직책: {meta['position']}")
            if meta.get("field"):
                lines.append(f"분야: {meta['field']}")
            if meta.get("date"):
                lines.append(f"날짜: {meta['date']}")
            if meta.get("link"):
                lines.append(f"링크: {meta['link']}")

            lines.append(f"내용: {content}")
            score = res.get("score")
            if score is not None:
                lines.append(f"유사도 점수: {float(score):.4f}")
            lines.append(f"출처: {res.get('collection', '')}")
            lines.append("-" * 50)

            parts.append("\n".join(lines) + "\n")

        return "\n".join(parts)
