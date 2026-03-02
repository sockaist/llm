"""
PostgreSQL + pgvector 검색 모듈
"""

import os
import re
from datetime import date
from typing import List, Dict, Any, Optional, Tuple

from ..vector_db.config import FORMATS, PGVECTOR_TABLE
from ..vector_db.vector_db_helper import (
    get_pgvector_client,
    ensure_schema,
    search_doc,
    search_doc_by_entities,
    fetch_full_doc_by_source,
    fetch_full_doc_by_chunk_id,
)


class VectorSearcher:
    """pgvector에서 유사한 정보를 검색하는 클래스"""

    def __init__(self):
        self.client = None
        self.search_available = False
        self.entity_search_keyword_limit = max(
            1,
            int(os.getenv("HIERARCHY_ENTITY_SEARCH_KEYWORD_LIMIT", "3")),
        )

        try:
            self.client = get_pgvector_client()
            ensure_schema(self.client)
            self.search_available = True
            print("✅ PostgreSQL(pgvector) 연결 및 스키마 확인 완료")
        except Exception as e:
            print(f"❌ PostgreSQL(pgvector) 초기화 실패: {e}")
            self.client = None
            self.search_available = False

    def search_similar_documents(
        self,
        query: str,
        top_k: int = 30,
        start_date: date | None = None,
        end_date: date | None = None,
        exclude_doc_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.search_available or not self.client:
            print("⚠️ Vector DB 검색을 사용할 수 없습니다.")
            return []

        try:
            all_results = []
            excluded_ids = set(self._sanitize_doc_ids(exclude_doc_ids))
            collections = self._list_collections()
            if not collections:
                return []
            per_collection_k = max(1, top_k // max(1, len(collections)) + 5)

            for collection in collections:
                try:
                    results = search_doc(
                        self.client,
                        query,
                        collection,
                        per_collection_k,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    for result in results:
                        payload = result.payload or {}
                        source_id = payload.get("source_id")
                        chunk_db_id = payload.get("chunk_db_id") or result.id
                        doc_id = self._normalize_doc_id(
                            collection=collection,
                            source_id=source_id,
                            chunk_db_id=chunk_db_id,
                            doc_id=payload.get("doc_id"),
                        )
                        if doc_id in excluded_ids:
                            continue

                        if payload.get("content"):
                            payload_content = payload.get("content", "")
                        elif payload.get("contents"):
                            payload_content = payload.get("contents", "")
                        elif payload.get("etc"):
                            payload_content = payload.get("etc", "")
                        else:
                            payload_content = ""

                        all_results.append(
                            {
                                "doc_id": doc_id,
                                "source_id": source_id,
                                "chunk_db_id": chunk_db_id,
                                "content": payload_content,
                                "score": result.score,
                                "collection": collection,
                                "metadata": {
                                    "title": payload.get("title", ""),
                                    "date": payload.get("date", ""),
                                    "start_date": payload.get("start_date", ""),
                                    "end_date": payload.get("end_date", ""),
                                    "link": payload.get("link", "") or payload.get("url", ""),
                                    "author": payload.get("author", ""),
                                    "name": payload.get("name", ""),
                                    "position": payload.get("position", ""),
                                    "field": payload.get("field", ""),
                                    "id": payload.get("id", ""),
                                },
                            }
                        )
                except Exception as e:
                    print(f"컬렉션 {collection} 검색 중 오류: {e}")
                    continue

            all_results.sort(key=lambda x: x["score"], reverse=True)
            return all_results[:top_k]
        except Exception as e:
            print(f"검색 중 오류 발생: {e}")
            return []

    @staticmethod
    def _safe_table_ident(name: str) -> str:
        table = str(name or "").strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table):
            return table
        return "documents"

    def _list_collections(self) -> List[str]:
        if not self.search_available or not self.client:
            return list(FORMATS.keys())

        table = self._safe_table_ident(PGVECTOR_TABLE)
        try:
            with self.client.connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT DISTINCT collection FROM {table} ORDER BY collection ASC;")
                    rows = cur.fetchall()
            collections = [str(row[0]).strip() for row in rows if row and str(row[0]).strip()]
            if collections:
                return collections
        except Exception as e:
            print(f"⚠️ collection 목록 조회 실패, FORMATS fallback 사용: {e}")
        return list(FORMATS.keys())

    def _convert_search_hit_to_result(
        self,
        result: Any,
        fallback_collection: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = result.payload or {}
        collection = str(payload.get("collection") or fallback_collection or "unknown")
        source_id = payload.get("source_id")
        chunk_db_id = payload.get("chunk_db_id") or result.id
        doc_id = self._normalize_doc_id(
            collection=collection,
            source_id=source_id,
            chunk_db_id=chunk_db_id,
            doc_id=payload.get("doc_id"),
        )

        if payload.get("content"):
            payload_content = payload.get("content", "")
        elif payload.get("contents"):
            payload_content = payload.get("contents", "")
        elif payload.get("etc"):
            payload_content = payload.get("etc", "")
        else:
            payload_content = ""

        return {
            "doc_id": doc_id,
            "source_id": source_id,
            "chunk_db_id": chunk_db_id,
            "content": payload_content,
            "score": result.score,
            "collection": collection,
            "metadata": {
                "title": payload.get("title", ""),
                "date": payload.get("date", ""),
                "start_date": payload.get("start_date", ""),
                "end_date": payload.get("end_date", ""),
                "link": payload.get("link", "") or payload.get("url", ""),
                "author": payload.get("author", ""),
                "name": payload.get("name", ""),
                "position": payload.get("position", ""),
                "field": payload.get("field", ""),
                "id": payload.get("id", ""),
                "entity_id": payload.get("entity_id", ""),
                "event_date": payload.get("event_date", ""),
            },
        }

    @staticmethod
    def _sanitize_keywords(keywords: Optional[List[str]], max_keywords: int = 5) -> List[str]:
        if not keywords:
            return []

        normalized: List[str] = []
        for keyword in keywords:
            if not isinstance(keyword, str):
                continue
            cleaned = " ".join(keyword.split()).strip()
            if len(cleaned) < 2:
                continue
            if cleaned in normalized:
                continue
            normalized.append(cleaned)
            if len(normalized) >= max_keywords:
                break
        return normalized

    @staticmethod
    def _result_identity(result: Dict[str, Any]) -> str:
        doc_id = result.get("doc_id")
        if isinstance(doc_id, str) and doc_id:
            return f"doc:{doc_id}"
        metadata = result.get("metadata", {}) or {}
        link = metadata.get("link")
        if isinstance(link, str) and link:
            return f"link:{link}"
        title = metadata.get("title", "")
        collection = result.get("collection", "")
        content_head = (result.get("content", "") or "")[:120]
        return f"{collection}|{title}|{content_head}"

    @staticmethod
    def _sanitize_doc_ids(doc_ids: Optional[List[str]]) -> List[str]:
        if not doc_ids:
            return []
        out: List[str] = []
        for item in doc_ids:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            if not cleaned or cleaned in out:
                continue
            out.append(cleaned)
        return out

    @staticmethod
    def _normalize_doc_id(
        collection: str,
        source_id: Any = None,
        chunk_db_id: Any = None,
        doc_id: Any = None,
    ) -> str:
        if isinstance(doc_id, str) and doc_id.strip():
            return doc_id.strip()
        if source_id is not None and str(source_id).strip():
            return f"{collection}::{str(source_id).strip()}"
        return f"{collection}::chunk:{chunk_db_id}"

    @staticmethod
    def _parse_doc_id(doc_id: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
        # 반환: (collection, source_id, chunk_id)
        text = (doc_id or "").strip()
        if not text or "::" not in text:
            return None, None, None
        collection, tail = text.split("::", 1)
        if not collection:
            return None, None, None
        if tail.startswith("chunk:"):
            raw_chunk_id = tail.replace("chunk:", "", 1).strip()
            try:
                return collection, None, int(raw_chunk_id)
            except ValueError:
                return collection, None, None
        return collection, tail, None

    def search_with_keywords(
        self,
        query: str,
        keywords: Optional[List[str]] = None,
        top_k: int = 30,
        start_date: date | None = None,
        end_date: date | None = None,
        exclude_doc_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        keyword_list = self._sanitize_keywords(keywords)
        excluded_doc_ids = self._sanitize_doc_ids(exclude_doc_ids)
        debug_vector_search = os.getenv("DEBUG_VECTOR_SEARCH") == "1"
        # 우선순위: 키워드가 있으면 키워드만 검색한다.
        # 키워드가 비어 있을 때만 전체 질문으로 fallback 한다.
        if keyword_list:
            search_queries = keyword_list
        else:
            query_text = " ".join((query or "").split()).strip()
            search_queries = [query_text] if query_text else []

        if debug_vector_search:
            print(
                "🔎 search_with_keywords:",
                {
                    "query": query,
                    "keywords": keyword_list,
                    "search_queries": search_queries,
                    "top_k": top_k,
                    "start_date": str(start_date) if start_date else None,
                    "end_date": str(end_date) if end_date else None,
                    "search_available": self.search_available,
                    "exclude_doc_ids": excluded_doc_ids,
                },
            )

        if not search_queries:
            return []

        if len(search_queries) == 1:
            single_results = self.search_similar_documents(
                search_queries[0],
                top_k=top_k,
                start_date=start_date,
                end_date=end_date,
                exclude_doc_ids=excluded_doc_ids,
            )
            if debug_vector_search:
                print(f"🔎 single query result count: {len(single_results)}")
            return single_results

        merged: Dict[str, Dict[str, Any]] = {}
        per_query_k = max(5, top_k // len(search_queries) + 3)

        for search_query in search_queries:
            query_results = self.search_similar_documents(
                search_query,
                top_k=per_query_k,
                start_date=start_date,
                end_date=end_date,
                exclude_doc_ids=excluded_doc_ids,
            )
            if debug_vector_search:
                print(f"🔎 query='{search_query}' result count: {len(query_results)}")
            for result in query_results:
                merged_result = dict(result)

                result_id = self._result_identity(merged_result)
                prev = merged.get(result_id)
                if prev is None or float(merged_result["score"]) > float(prev["score"]):
                    merged[result_id] = merged_result

        final_results = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
        if final_results:
            if debug_vector_search:
                print(f"🔎 merged result count: {len(final_results)}")
            return final_results[:top_k]

        # 키워드별 검색이 모두 0건이면, 키워드를 한 문장으로 합쳐 한 번 더 시도한다.
        # (전체 정규화 질문이 아닌 키워드만 사용)
        if keyword_list and len(keyword_list) > 1:
            combined_query = " ".join(keyword_list).strip()
            if combined_query:
                if debug_vector_search:
                    print(f"🔎 combined keyword retry: '{combined_query}'")
                combined_results = self.search_similar_documents(
                    combined_query,
                    top_k=top_k,
                    start_date=start_date,
                    end_date=end_date,
                    exclude_doc_ids=excluded_doc_ids,
                )
                if debug_vector_search:
                    print(f"🔎 combined query result count: {len(combined_results)}")
                return combined_results[:top_k]

        return []

    def search_in_entity(
        self,
        entity_id: str,
        query: str,
        keywords: Optional[List[str]] = None,
        top_k: int = 20,
        start_date: date | None = None,
        end_date: date | None = None,
        exclude_doc_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not self.search_available or not self.client:
            return []

        normalized_entity_id = str(entity_id).strip()
        if not normalized_entity_id:
            return []

        excluded_ids = set(self._sanitize_doc_ids(exclude_doc_ids))
        keyword_list = self._sanitize_keywords(
            keywords,
            max_keywords=self.entity_search_keyword_limit,
        )
        query_text = " ".join((query or "").split()).strip()
        if keyword_list:
            search_queries = keyword_list
        elif query_text:
            search_queries = [query_text]
        else:
            return []

        merged: Dict[str, Dict[str, Any]] = {}
        per_query_k = max(5, top_k // max(1, len(search_queries)) + 4)
        for search_query in search_queries:
            try:
                hits = search_doc_by_entities(
                    self.client,
                    query=search_query,
                    entity_ids=[normalized_entity_id],
                    k=per_query_k,
                    start_date=start_date,
                    end_date=end_date,
                )
            except Exception as e:
                print(f"entity 검색 오류(entity_id={normalized_entity_id}): {e}")
                continue

            for hit in hits:
                item = self._convert_search_hit_to_result(hit)
                doc_id = str(item.get("doc_id", "")).strip()
                if doc_id and doc_id in excluded_ids:
                    continue
                identity = self._result_identity(item)
                prev = merged.get(identity)
                if prev is None or float(item.get("score", 0.0)) > float(prev.get("score", 0.0)):
                    merged[identity] = item

        results = sorted(merged.values(), key=lambda x: float(x.get("score", 0.0)), reverse=True)
        return results[:top_k]

    def fetch_full_documents_by_doc_ids(
        self,
        doc_ids: Optional[List[str]],
        max_docs: int = 20,
    ) -> List[Dict[str, Any]]:
        if not self.search_available or not self.client:
            return []

        sanitized = self._sanitize_doc_ids(doc_ids)[: max(1, max_docs)]
        documents: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for doc_id in sanitized:
            collection, source_id, chunk_id = self._parse_doc_id(doc_id)
            if not collection:
                continue

            doc: Optional[Dict[str, Any]] = None
            try:
                if source_id:
                    doc = fetch_full_doc_by_source(self.client, collection, source_id)
                elif chunk_id is not None:
                    doc = fetch_full_doc_by_chunk_id(self.client, chunk_id)
            except Exception as e:
                print(f"⚠️ full_content 조회 실패({doc_id}): {e}")
                continue

            if not doc:
                continue
            normalized_doc_id = str(doc.get("doc_id", "")).strip() or doc_id
            if normalized_doc_id in seen:
                continue
            seen.add(normalized_doc_id)
            documents.append(doc)

        return documents

    @staticmethod
    def format_full_documents_context(
        docs: List[Dict[str, Any]],
        max_docs: int = 20,
        max_chars_per_doc: int = 3000,
        max_total_chars: int = 50000,
    ) -> str:
        if not docs:
            return ""

        lines: List[str] = []
        total_chars = 0
        for idx, doc in enumerate(docs[:max_docs], start=1):
            metadata = doc.get("metadata", {}) or {}
            section_lines: List[str] = []
            section_lines.append(f"[문서 {idx}]")
            section_lines.append(f"doc_id: {doc.get('doc_id', '')}")
            section_lines.append(f"collection: {doc.get('collection', '')}")
            if doc.get("source_id"):
                section_lines.append(f"source_id: {doc.get('source_id')}")
            if metadata.get("title"):
                section_lines.append(f"title: {metadata.get('title')}")
            if metadata.get("name"):
                section_lines.append(f"name: {metadata.get('name')}")
            if metadata.get("field"):
                section_lines.append(f"field: {metadata.get('field')}")
            if metadata.get("date"):
                section_lines.append(f"date: {metadata.get('date')}")
            if metadata.get("event_date"):
                section_lines.append(f"event_date: {metadata.get('event_date')}")
            if metadata.get("start_date"):
                section_lines.append(f"start_date: {metadata.get('start_date')}")
            if metadata.get("end_date"):
                section_lines.append(f"end_date: {metadata.get('end_date')}")
            if metadata.get("link"):
                section_lines.append(f"link: {metadata.get('link')}")

            content = str(doc.get("full_content", "")).strip()
            if max_chars_per_doc > 0 and len(content) > max_chars_per_doc:
                content = content[: max_chars_per_doc - 15] + "...[truncated]"

            section_lines.append("full_content:")
            section_lines.append(content)
            section_lines.append("-" * 50)

            section_text = "\n".join(section_lines)
            if max_total_chars > 0 and total_chars + len(section_text) > max_total_chars:
                remaining = max_total_chars - total_chars
                if remaining <= 0:
                    break
                section_text = section_text[:remaining]
                lines.append(section_text)
                total_chars += len(section_text)
                break

            lines.append(section_text)
            total_chars += len(section_text)
        return "\n".join(lines).strip()

    def format_search_results(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return "관련 정보를 찾을 수 없습니다."

        formatted_text = "=== 관련 정보 ===\n\n"
        for i, result in enumerate(results, 1):
            formatted_text += f"[정보 {i}]\n"
            metadata = result["metadata"]

            if metadata.get("title"):
                formatted_text += f"제목: {metadata['title']}\n"
            if metadata.get("author"):
                formatted_text += f"작성자: {metadata['author']}\n"
            if metadata.get("name"):
                formatted_text += f"이름: {metadata['name']}\n"
            if metadata.get("position"):
                formatted_text += f"직책: {metadata['position']}\n"
            if metadata.get("field"):
                formatted_text += f"분야: {metadata['field']}\n"
            if metadata.get("date"):
                formatted_text += f"날짜: {metadata['date']}\n"
            if metadata.get("start_date"):
                formatted_text += f"시작일: {metadata['start_date']}\n"
            if metadata.get("end_date"):
                formatted_text += f"종료일: {metadata['end_date']}\n"
            if metadata.get("link"):
                formatted_text += f"링크: {metadata['link']}\n"

            content = result["content"]
            if len(content) > 300:
                content = content[:300] + "..."

            formatted_text += f"내용: {content}\n"
            formatted_text += f"유사도 점수: {result['score']:.4f}\n"
            formatted_text += f"출처: {result['collection']}\n"
            formatted_text += "-" * 50 + "\n\n"

        return formatted_text
