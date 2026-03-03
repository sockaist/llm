"""
ChatBot 서비스 클래스
계층형 노드 검색(level0/entity.md 기반) 중심 파이프라인.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from ..llm import (
    OpenAIInputChecker,
    OpenAIInputNormalizer,
    VectorSearcher,
    OpenAIChatBot,
)
from ..llm.web_fallback_search import WebFallbackSearcher
from ..llm.hierarchical_node_search import (
    HierarchicalNodeSearchOrchestrator,
    HierarchicalSearchResult,
)
from ..llm.query_date_filter import QueryDateFilterExtractor


class ChatBotService:
    """
    ChatBot 서비스 클래스
    서버 시작시 한 번만 초기화되고, 이후 요청에 대해 빠르게 응답
    """

    def __init__(self):
        self.is_initialized = False
        self.checker = None
        self.normalizer = None
        self.vector_searcher = None
        self.openai_chatbot = None
        self.date_filter_extractor = None
        self.hierarchical_search_orchestrator = None
        self.web_fallback_searcher = None
        self.web_search_fallback_enabled = False
        self.web_search_fallback_max_results = 5

        self.hierarchy_max_depth = 4
        # 0이면 자식 노드 확장 수 제한 없음(unlimited)
        self.hierarchy_max_children_per_node = 0
        self.hierarchy_max_workers = 24
        self.hierarchy_node_top_k = 20
        self.hierarchy_final_doc_limit = 60
        self.hierarchy_final_context_docs = 16
        self.hierarchy_final_context_max_chars = 50000
        self.hierarchy_final_context_max_chars_per_doc = 2600
        self.hierarchy_max_root_nodes = 4
        self.hierarchy_child_model = "gpt-4o-mini"
        self.project_root = Path(__file__).resolve().parents[3]
        self.hierarchy_trace_log_enabled = False
        self.hierarchy_trace_console_enabled = False
        self.hierarchy_trace_log_path = self.project_root / "logs" / "hierarchy_search_trace.log"
        self.hierarchy_trace_console_max_lines = 40

        self.debug_hierarchy_search = (
            os.getenv("DEBUG_HIERARCHY_SEARCH") == "1"
            or os.getenv("DEBUG_MULTI_TURN") == "1"
        )

        self._initialize()

    def _initialize(self):
        """
        ChatBot 컴포넌트들 초기화
        서버 시작시 한 번만 실행됨
        """
        try:
            load_dotenv()

            self.hierarchy_max_depth = max(1, int(os.getenv("HIERARCHY_MAX_DEPTH", "4")))
            # 요구사항: child 확장 제한을 완전히 제거한다.
            self.hierarchy_max_children_per_node = 0
            self.hierarchy_max_workers = max(1, int(os.getenv("HIERARCHY_MAX_WORKERS", "24")))
            self.hierarchy_node_top_k = max(1, int(os.getenv("HIERARCHY_NODE_TOP_K", "20")))
            self.hierarchy_final_doc_limit = max(1, int(os.getenv("HIERARCHY_FINAL_DOC_LIMIT", "60")))
            self.hierarchy_final_context_docs = max(
                1,
                min(
                    int(os.getenv("HIERARCHY_FINAL_CONTEXT_DOCS", "16")),
                    self.hierarchy_final_doc_limit,
                ),
            )
            self.hierarchy_final_context_max_chars = max(
                4000,
                int(os.getenv("HIERARCHY_FINAL_CONTEXT_MAX_CHARS", "50000")),
            )
            self.hierarchy_final_context_max_chars_per_doc = max(
                400,
                int(os.getenv("HIERARCHY_FINAL_CONTEXT_MAX_CHARS_PER_DOC", "2600")),
            )
            self.hierarchy_max_root_nodes = max(1, int(os.getenv("HIERARCHY_MAX_ROOT_NODES", "4")))
            self.hierarchy_child_model = os.getenv("HIERARCHY_CHILD_MODEL", "gpt-4o-mini")
            self.debug_hierarchy_search = (
                os.getenv("DEBUG_HIERARCHY_SEARCH") == "1"
                or os.getenv("DEBUG_MULTI_TURN") == "1"
            )
            self.hierarchy_trace_log_enabled = os.getenv("HIERARCHY_TRACE_LOG", "1") == "1"
            self.hierarchy_trace_console_enabled = os.getenv("HIERARCHY_TRACE_CONSOLE", "0") == "1"
            self.hierarchy_trace_console_max_lines = max(
                1,
                int(os.getenv("HIERARCHY_TRACE_CONSOLE_MAX_LINES", "40")),
            )
            trace_log_path_text = os.getenv(
                "HIERARCHY_TRACE_LOG_PATH",
                "logs/hierarchy_search_trace.log",
            ).strip()
            trace_log_path = Path(trace_log_path_text)
            if not trace_log_path.is_absolute():
                trace_log_path = (self.project_root / trace_log_path).resolve()
            self.hierarchy_trace_log_path = trace_log_path

            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

            self.web_search_fallback_enabled = (
                os.getenv("WEB_SEARCH_FALLBACK_ENABLED", "1") == "1"
            )
            self.web_search_fallback_max_results = max(
                1,
                min(int(os.getenv("WEB_SEARCH_FALLBACK_MAX_RESULTS", "5")), 10),
            )

            print("🚀 ChatBot 서비스 초기화 중...")

            self.checker = OpenAIInputChecker(api_key=openai_api_key)
            self.normalizer = OpenAIInputNormalizer(api_key=openai_api_key)
            self.vector_searcher = VectorSearcher()
            self.openai_chatbot = OpenAIChatBot(
                api_key=openai_api_key,
                model=os.getenv("HIERARCHY_TOP_MODEL", "gpt-4.1"),
                vector_searcher=self.vector_searcher,
            )
            self.date_filter_extractor = QueryDateFilterExtractor(
                api_key=openai_api_key,
                model=os.getenv("DATE_FILTER_MODEL", "gpt-4o-mini"),
            )

            self.hierarchical_search_orchestrator = HierarchicalNodeSearchOrchestrator(
                api_key=openai_api_key,
                vector_searcher=self.vector_searcher,
                child_model=self.hierarchy_child_model,
                max_depth=self.hierarchy_max_depth,
                max_children_per_node=self.hierarchy_max_children_per_node,
                max_workers=self.hierarchy_max_workers,
                node_top_k=self.hierarchy_node_top_k,
                final_doc_limit=self.hierarchy_final_doc_limit,
                max_root_nodes=self.hierarchy_max_root_nodes,
                debug=self.debug_hierarchy_search,
            )

            if self.web_search_fallback_enabled:
                self.web_fallback_searcher = WebFallbackSearcher(
                    timeout_sec=max(4, int(os.getenv("WEB_SEARCH_TIMEOUT_SEC", "8"))),
                    region=os.getenv("WEB_SEARCH_REGION", "kr-kr"),
                    debug=self.debug_hierarchy_search,
                )

            print("🔄 시스템 워밍업 중...")
            boot_input = "이 메세지는 백엔드 서버 부팅 시 llm의 부팅 및 JSON 파싱을 위해 사용됩니다. 해당 메세지를 무시하세요."
            try:
                self.normalizer.normalize_input(boot_input)
                self.checker.check_input(boot_input)
                print("✅ 시스템 워밍업 완료!")
            except Exception as e:
                print(f"⚠️ 워밍업 중 경고: {e}")

            self.is_initialized = True
            print("✅ ChatBot 서비스 초기화 완료!")
        except Exception as e:
            print(f"❌ ChatBot 서비스 초기화 실패: {e}")
            raise e

    def get_health_status(self) -> Dict[str, str]:
        components = {
            "chatbot_service": "healthy" if self.is_initialized else "unhealthy",
            "input_checker": "healthy" if self.checker is not None else "unhealthy",
            "input_normalizer": "healthy" if self.normalizer is not None else "unhealthy",
            "vector_searcher": (
                "healthy"
                if (self.vector_searcher is not None and getattr(self.vector_searcher, "search_available", False))
                else "unhealthy"
            ),
            "openai_chatbot": "healthy" if self.openai_chatbot is not None else "unhealthy",
            "date_filter_extractor": "healthy" if self.date_filter_extractor is not None else "unhealthy",
            "hierarchical_search": (
                "healthy" if self.hierarchical_search_orchestrator is not None else "unhealthy"
            ),
            "sql_context_retriever": "disabled",
        }
        return components

    @staticmethod
    def _dedupe_keep_order(items: List[str], max_items: int) -> List[str]:
        out: List[str] = []
        for item in items:
            cleaned = " ".join(str(item).split()).strip()
            if not cleaned or cleaned in out:
                continue
            out.append(cleaned)
            if len(out) >= max_items:
                break
        return out

    @staticmethod
    def _sanitize_keywords(keywords: List[str], max_keywords: int = 8) -> List[str]:
        stopwords = {"최근", "요즘", "이번", "최신", "정보", "질문", "알려줘", "알려주세요", "문의"}
        deduped = ChatBotService._dedupe_keep_order(keywords, max_items=max_keywords * 2)
        out: List[str] = []
        for keyword in deduped:
            if len(keyword) < 2:
                continue
            if keyword in stopwords:
                continue
            out.append(keyword)
            if len(out) >= max_keywords:
                break
        return out

    @staticmethod
    def _extract_literal_keywords(text: str, max_keywords: int = 8) -> List[str]:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9._/-]{1,}|[가-힣]{2,}", text or "")
        return ChatBotService._dedupe_keep_order(tokens, max_items=max_keywords)

    @staticmethod
    def _summarize_hierarchy_trace(trace: List[Dict[str, Any]], max_lines: int = 40) -> List[str]:
        lines: List[str] = []
        for item in trace:
            if not isinstance(item, dict):
                continue
            if item.get("phase") == "root_plan":
                entity_id = str(item.get("entity_id", "")).strip()
                keywords = item.get("keywords", []) if isinstance(item.get("keywords"), list) else []
                reason = str(item.get("reason", "")).strip()
                lines.append(f"[root] entity={entity_id} keywords={keywords} reason={reason}")
            else:
                entity_id = str(item.get("entity_id", "")).strip()
                depth = item.get("depth")
                local_hit_count = item.get("local_hit_count")
                selected_doc_count = item.get("selected_doc_count")
                is_relevant = item.get("is_relevant")
                is_sufficient = item.get("is_sufficient")
                next_children = item.get("next_children", [])
                next_child_ids: List[str] = []
                if isinstance(next_children, list):
                    for child in next_children:
                        if not isinstance(child, dict):
                            continue
                        child_id = str(child.get("entity_id", "")).strip()
                        if child_id:
                            next_child_ids.append(child_id)
                reason = str(item.get("reason", "")).strip()
                lines.append(
                    "[node] depth={depth} entity={entity} hits={hits} selected={selected} "
                    "relevant={relevant} sufficient={sufficient} next={next_children} reason={reason}".format(
                        depth=depth,
                        entity=entity_id,
                        hits=local_hit_count,
                        selected=selected_doc_count,
                        relevant=is_relevant,
                        sufficient=is_sufficient,
                        next_children=next_child_ids,
                        reason=reason,
                    )
                )
            if len(lines) >= max_lines:
                break
        return lines

    def _log_hierarchy_search_trace(
        self,
        *,
        trace_id: str,
        user_input: str,
        normalized_query: str,
        hierarchy_query: str,
        planner_seed_keywords: List[str],
        start_date,
        end_date,
        hierarchy_result: HierarchicalSearchResult,
        vector_context_len: int,
    ) -> None:
        if not self.hierarchy_trace_log_enabled and not self.hierarchy_trace_console_enabled:
            return

        now_kst = datetime.now(ZoneInfo("Asia/Seoul")).isoformat()
        summary_lines = self._summarize_hierarchy_trace(
            hierarchy_result.trace,
            max_lines=self.hierarchy_trace_console_max_lines,
        )
        text_lines: List[str] = []
        text_lines.append("=" * 100)
        text_lines.append(f"timestamp_kst: {now_kst}")
        text_lines.append(f"trace_id: {trace_id}")
        text_lines.append(f"user_input: {user_input}")
        text_lines.append(f"normalized_query: {normalized_query}")
        text_lines.append(f"hierarchy_query: {hierarchy_query}")
        text_lines.append(f"planner_seed_keywords: {planner_seed_keywords}")
        text_lines.append(
            "date_filter: start={start} end={end}".format(
                start=start_date.isoformat() if start_date else "None",
                end=end_date.isoformat() if end_date else "None",
            )
        )
        text_lines.append(
            "result: doc_id_count={count} vector_context_len={context_len}".format(
                count=len(hierarchy_result.final_doc_ids),
                context_len=vector_context_len,
            )
        )
        text_lines.append(f"result.used_entities: {hierarchy_result.used_entities}")
        text_lines.append(f"result.used_keywords: {hierarchy_result.used_keywords}")
        text_lines.append(
            "result.doc_ids: {doc_ids}".format(
                doc_ids=hierarchy_result.final_doc_ids,
            )
        )
        text_lines.append("trace:")
        for line in summary_lines:
            text_lines.append(f"  - {line}")
        text_lines.append("")
        log_block = "\n".join(text_lines)

        if self.hierarchy_trace_console_enabled:
            print(f"🧭 검색 트레이스(trace_id={trace_id})")
            for line in summary_lines:
                print(f"   {line}")
            print(
                "   final_doc_ids({count}): {doc_ids}".format(
                    count=len(hierarchy_result.final_doc_ids),
                    doc_ids=hierarchy_result.final_doc_ids[:20],
                )
            )

        if self.hierarchy_trace_log_enabled:
            try:
                self.hierarchy_trace_log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.hierarchy_trace_log_path.open("a", encoding="utf-8") as fp:
                    fp.write(log_block)
            except Exception as e:
                print(f"⚠️ hierarchy trace 파일 기록 실패: {e}")

    def _fallback_vector_context(
        self,
        query: str,
        keywords: List[str],
        start_date,
        end_date,
    ) -> str:
        if self.vector_searcher is None:
            return ""
        results = self.vector_searcher.search_with_keywords(
            query,
            keywords=keywords,
            top_k=min(20, self.hierarchy_node_top_k),
            start_date=start_date,
            end_date=end_date,
        )
        doc_ids = self._dedupe_keep_order(
            [str(item.get("doc_id", "")).strip() for item in results],
            max_items=self.hierarchy_final_context_docs,
        )
        docs = self.vector_searcher.fetch_full_documents_by_doc_ids(
            doc_ids,
            max_docs=self.hierarchy_final_context_docs,
        )
        return self.vector_searcher.format_full_documents_context(
            docs,
            max_docs=self.hierarchy_final_context_docs,
            max_chars_per_doc=self.hierarchy_final_context_max_chars_per_doc,
            max_total_chars=self.hierarchy_final_context_max_chars,
        )

    def _fallback_web_context(
        self,
        query: str,
        keywords: List[str],
    ) -> str:
        if not self.web_search_fallback_enabled or self.web_fallback_searcher is None:
            return ""

        merged_keywords = self._dedupe_keep_order(keywords, max_items=4)
        search_query = query
        if merged_keywords:
            search_query = f"{query} {' '.join(merged_keywords)}".strip()

        kaist_scoped_query = f"{search_query} site:kaist.ac.kr".strip()
        web_results = self.web_fallback_searcher.search(
            kaist_scoped_query,
            max_results=self.web_search_fallback_max_results,
        )
        if not web_results:
            web_results = self.web_fallback_searcher.search(
                search_query,
                max_results=self.web_search_fallback_max_results,
            )
        if not web_results:
            return ""

        lines: List[str] = []
        lines.append("=== 외부 웹 검색 결과(내부 문서 부재로 fallback) ===")
        lines.append("아래 정보는 외부 웹에서 수집된 참고 자료이며, 최신성/정확성을 교차 확인해야 합니다.")
        for idx, item in enumerate(web_results, start=1):
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            snippet = str(item.get("snippet", "")).strip()
            lines.append(f"[웹 문서 {idx}]")
            if title:
                lines.append(f"title: {title}")
            if url:
                lines.append(f"link: {url}")
            if snippet:
                lines.append(f"snippet: {snippet}")
            lines.append("-" * 50)
        return "\n".join(lines).strip()

    @staticmethod
    def _to_non_negative_int(value: Any, default: int = 0) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return max(0, default)
        return max(0, parsed)

    @staticmethod
    def _normalize_entity_id(value: Any) -> str:
        return " ".join(str(value or "").split()).strip()

    @staticmethod
    def _normalize_parent_id(value: Any) -> Optional[str]:
        text = " ".join(str(value or "").split()).strip()
        if not text:
            return None
        lowered = text.lower()
        if lowered in {"none", "null"}:
            return None
        return text

    def get_ontology_tree(self) -> Dict[str, Any]:
        data_root = (self.project_root / "data").resolve()
        if not data_root.exists():
            raise FileNotFoundError(f"data 폴더가 없습니다: {data_root}")

        entity_json_paths = sorted(data_root.rglob("entity.json"))
        if not entity_json_paths:
            raise FileNotFoundError("entity.json이 없습니다. rebuild.sh를 먼저 실행하세요.")

        nodes_by_id: Dict[str, Dict[str, Any]] = {}
        for entity_json_path in entity_json_paths:
            try:
                payload = json.loads(entity_json_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue

            entity_id = self._normalize_entity_id(payload.get("entity_id"))
            if not entity_id:
                continue

            relative_path = " ".join(str(payload.get("relative_path", "")).split()).strip()
            if not relative_path:
                try:
                    relative_path = entity_json_path.parent.relative_to(data_root).as_posix()
                except ValueError:
                    relative_path = "."
                if relative_path == ".":
                    relative_path = "."

            node = {
                "entity_id": entity_id,
                "name": " ".join(str(payload.get("name", entity_json_path.parent.name)).split()).strip(),
                "relative_path": relative_path,
                "description": str(payload.get("description", "")).strip(),
                "doc_count": self._to_non_negative_int(payload.get("doc_count"), default=0),
                "parent_entity_id": self._normalize_parent_id(payload.get("parent_entity_id")),
                "children": [],
            }
            nodes_by_id[entity_id] = node

        if not nodes_by_id:
            raise FileNotFoundError("유효한 entity.json을 찾지 못했습니다. rebuild.sh를 먼저 실행하세요.")

        for node in nodes_by_id.values():
            parent_id = node.get("parent_entity_id")
            if parent_id and parent_id in nodes_by_id:
                nodes_by_id[parent_id]["children"].append(node)

        def sort_node_children(node: Dict[str, Any]) -> None:
            node["children"].sort(
                key=lambda child: (
                    str(child.get("relative_path", "")),
                    str(child.get("name", "")),
                )
            )
            for child in node["children"]:
                sort_node_children(child)

        for node in nodes_by_id.values():
            if node["children"]:
                sort_node_children(node)

        roots = [
            node
            for node in nodes_by_id.values()
            if not node.get("parent_entity_id") or node.get("parent_entity_id") not in nodes_by_id
        ]
        roots.sort(key=lambda node: (str(node.get("relative_path", "")), str(node.get("name", ""))))

        root_node = None
        for node in roots:
            if str(node.get("relative_path", "")) == ".":
                root_node = node
                break

        if root_node is None and roots:
            root_node = {
                "entity_id": "virtual_root",
                "name": "data",
                "relative_path": ".",
                "description": "",
                "doc_count": 0,
                "parent_entity_id": None,
                "children": roots,
            }

        return {
            "success": True,
            "generated_at_kst": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
            "entity_count": len(nodes_by_id),
            "root": root_node,
            "top_level_entities": roots if root_node is None or root_node.get("entity_id") == "virtual_root" else root_node.get("children", []),
        }

    def process_message(self, user_input: str, use_vector_search: bool = True) -> Dict[str, Any]:
        if not self.is_initialized:
            return {
                "success": False,
                "response": "서비스가 초기화되지 않았습니다.",
                "error": "Service not initialized",
            }

        try:
            trace_id = uuid4().hex[:12]
            print(f"📝 사용자 질문 처리 중(trace_id={trace_id}): {user_input}")

            # 1) 정규화
            search_keywords: List[str] = []
            normalized_query = user_input
            try:
                normalized_result = self.normalizer.normalize_input_with_keywords(user_input)
                normalized_query = normalized_result.get("output", user_input)
                search_keywords = normalized_result.get("keywords", []) or []
                print(f"📝 정규화된 질문: {normalized_query}")
            except Exception as e:
                print(f"⚠️ 입력 정규화 중 오류: {e}")

            effective_keywords = self._sanitize_keywords(search_keywords, max_keywords=8)
            if effective_keywords:
                print(f"🔑 검색 키워드: {effective_keywords}")
            literal_keywords = self._extract_literal_keywords(user_input, max_keywords=8)
            planner_seed_keywords = self._sanitize_keywords(
                effective_keywords + literal_keywords,
                max_keywords=10,
            )

            # 2) 유효성 검사
            try:
                is_valid = self.checker.check_input(user_input)
                if not is_valid and self._looks_like_soc_query(user_input):
                    print("⚠️ inputChecker가 false를 반환했지만 SoC 관련 키워드가 있어 통과시킵니다.")
                    is_valid = True
                if not is_valid:
                    return {
                        "success": False,
                        "response": (
                            "죄송합니다. 해당 질문은 KAIST 전산학부 관련 질문이 아닌 것 같습니다. "
                            "전산학부 학사과정, 행사, 교수진, 시설 등에 대해 질문해주세요."
                        ),
                        "error": "Invalid input",
                    }
            except Exception as e:
                print(f"⚠️ 입력 검증 중 오류: {e}")
                print("⚠️ 입력 검증을 건너뛰고 계속 진행합니다.")

            # 3) 날짜 필터 추출
            today_kst = datetime.now(ZoneInfo("Asia/Seoul")).date()
            date_filter = (
                self.date_filter_extractor.extract(user_input, today=today_kst)
                if self.date_filter_extractor
                else None
            )
            start_date = date_filter.start_date if date_filter else None
            end_date = date_filter.end_date if date_filter else None
            if date_filter and date_filter.has_filter():
                print(f"🗓️ 날짜 필터 적용: {start_date} ~ {end_date}")

            # 4) 계층형 검색 (SQL 완전 비활성)
            vector_context = ""
            used_doc_ids: List[str] = []
            hierarchy_result: Optional[HierarchicalSearchResult] = None
            hierarchy_query = normalized_query
            if normalized_query.strip() != user_input.strip():
                hierarchy_query = f"{normalized_query}\n원문 질의: {user_input}"
            if use_vector_search and self.hierarchical_search_orchestrator is not None:
                try:
                    hierarchy_result = self.hierarchical_search_orchestrator.search(
                        query=hierarchy_query,
                        seed_keywords=planner_seed_keywords,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    used_doc_ids = hierarchy_result.final_doc_ids

                    if self.debug_hierarchy_search:
                        print(
                            "🔎 계층 검색 결과:",
                            {
                                "doc_id_count": len(hierarchy_result.final_doc_ids),
                                "used_entities": hierarchy_result.used_entities,
                                "used_keywords": hierarchy_result.used_keywords,
                            },
                        )

                    docs = self.vector_searcher.fetch_full_documents_by_doc_ids(
                        hierarchy_result.final_doc_ids,
                        max_docs=self.hierarchy_final_context_docs,
                    )
                    vector_context = self.vector_searcher.format_full_documents_context(
                        docs,
                        max_docs=self.hierarchy_final_context_docs,
                        max_chars_per_doc=self.hierarchy_final_context_max_chars_per_doc,
                        max_total_chars=self.hierarchy_final_context_max_chars,
                    )
                    self._log_hierarchy_search_trace(
                        trace_id=trace_id,
                        user_input=user_input,
                        normalized_query=normalized_query,
                        hierarchy_query=hierarchy_query,
                        planner_seed_keywords=planner_seed_keywords,
                        start_date=start_date,
                        end_date=end_date,
                        hierarchy_result=hierarchy_result,
                        vector_context_len=len(vector_context),
                    )
                except FileNotFoundError as e:
                    # level0.md/entity.md 계약 위반 시 명시적 에러
                    return {
                        "success": False,
                        "response": str(e),
                        "error": "Hierarchy metadata missing",
                    }
                except Exception as e:
                    print(f"⚠️ 계층형 검색 실패: {e}")
                    vector_context = self._fallback_vector_context(
                        normalized_query,
                        planner_seed_keywords,
                        start_date,
                        end_date,
                    )
            elif use_vector_search:
                vector_context = self._fallback_vector_context(
                    normalized_query,
                    planner_seed_keywords,
                    start_date,
                    end_date,
                )

            if use_vector_search and not vector_context.strip():
                web_context = self._fallback_web_context(
                    normalized_query,
                    planner_seed_keywords,
                )
                if web_context:
                    current_kst_date = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
                    response = self.openai_chatbot.generate_response(
                        user_query=user_input,
                        use_vector_search=False,
                        start_date=start_date,
                        end_date=end_date,
                        search_keywords=effective_keywords,
                        sql_context=None,
                        vector_context=web_context,
                        current_date_text=current_kst_date,
                    )
                    return {
                        "success": True,
                        "response": response,
                        "message": "외부 웹 검색 fallback 응답",
                    }

                return {
                    "success": True,
                    "response": (
                        "현재 질의에 대해 신뢰할 만한 근거 문서를 찾지 못했습니다. "
                        "엔티티 이름(예: csweb/news/notion/portal 세부 주제), 기간, 키워드를 더 구체화해 다시 질문해 주세요."
                    ),
                    "message": "근거 문서 없음",
                }

            # 5) 최종 답변 생성 (상위 고성능 모델, max_tokens 미지정)
            current_kst_date = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d")
            response = self.openai_chatbot.generate_response(
                user_query=user_input,
                use_vector_search=False,
                start_date=start_date,
                end_date=end_date,
                search_keywords=effective_keywords,
                sql_context=None,
                vector_context=vector_context,
                current_date_text=current_kst_date,
            )

            debug_message = "답변 생성 완료"
            if self.debug_hierarchy_search and used_doc_ids:
                debug_message = f"답변 생성 완료 (doc_ids={len(used_doc_ids)})"

            return {
                "success": True,
                "response": response,
                "message": debug_message,
            }

        except Exception as e:
            print(f"❌ 메시지 처리 중 예상치 못한 오류: {e}")
            return {
                "success": False,
                "response": f"메시지 처리 중 오류가 발생했습니다: {str(e)}",
                "error": str(e),
            }

    @staticmethod
    def _looks_like_soc_query(text: str) -> bool:
        keywords = [
            "전산학부",
            "soc",
            "kaist",
            "학생회",
            "집행위",
            "학사",
            "교수",
            "수강",
            "행사",
            "공지",
        ]
        lowered = (text or "").lower()
        return any(k in lowered for k in keywords)


# 전역 서비스 인스턴스 (서버 시작시 한 번만 생성)
chatbot_service = None


def get_chatbot_service() -> ChatBotService:
    """
    ChatBot 서비스 인스턴스 반환
    FastAPI dependency injection에서 사용
    """
    global chatbot_service
    if chatbot_service is None:
        chatbot_service = ChatBotService()
    return chatbot_service
