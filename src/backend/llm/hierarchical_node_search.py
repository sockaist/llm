"""
level0/entity.md 기반 계층형 노드 검색 오케스트레이터.
"""

from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import openai

from .vector_searcher import VectorSearcher


DEFAULT_LLM_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_ROOT = DEFAULT_LLM_ROOT / "data"

MAX_DEPTH_DEFAULT = 4
# 0 이하 값은 자식 노드 확장 개수 제한 없음(unlimited)으로 해석한다.
MAX_CHILDREN_PER_NODE_DEFAULT = 0
MAX_WORKERS_DEFAULT = 24
NODE_TOP_K_DEFAULT = 20
FINAL_DOC_LIMIT_DEFAULT = 60
MAX_ROOT_NODES_DEFAULT = 4


PLANNER_SYSTEM_PROMPT = """
너는 계층형 검색 루트 노드 선택기다.
질문과 level0 카탈로그를 보고, 검색을 시작할 최상위 노드와 각 노드의 초기 키워드를 선택하라.

반드시 JSON 객체만 출력:
{
  "nodes": [
    {
      "entity_id": "문자열",
      "keywords": ["키워드1", "키워드2"],
      "reason": "선택 근거"
    }
  ],
  "reason": "전체 계획 근거"
}

규칙:
- nodes는 top_level_entities 안의 entity_id만 사용.
- 최대 {max_root_nodes}개.
- keywords는 1~6개, 구체명 위주.
- 질문과 무관한 노드는 선택하지 않는다.
""".strip()


NODE_JUDGE_SYSTEM_PROMPT = """
너는 계층형 노드 탐색 판단기다.
현재 엔티티의 로컬 벡터 검색 결과(local_vector_hits)와 하위 엔티티 정보를 보고,
해당 노드 탐색을 중단할지/충분한지/어떤 하위 노드를 확장할지 결정하라.

반드시 JSON 객체만 출력:
{
  "is_relevant": true,
  "is_sufficient": false,
  "selected_doc_ids": ["doc_id1", "doc_id2"],
  "next_children": [
    {
      "entity_id": "child_entity_id",
      "keywords": ["키워드1", "키워드2"]
    }
  ],
  "reason": "판단 근거"
}

규칙:
- is_relevant=false면 selected_doc_ids/next_children는 비워도 된다.
- selected_doc_ids는 local_vector_hits에 나온 doc_id만 사용.
- next_children는 child_entities에 있는 entity_id만 사용.
- 질문과의 관련성이 낮으면 과감히 중단한다.
""".strip()


@dataclass
class EntityNode:
    entity_id: str
    name: str
    relative_path: str
    parent_entity_id: Optional[str]
    child_entity_ids: List[str]
    description: str
    relation_types: List[Dict[str, str]]
    entity_md_path: Path
    entity_json_path: Path
    entity_md_text: str
    entity_json: Dict[str, Any]


@dataclass
class Level0Catalog:
    generated_at: str
    root_path: str
    relation_types: List[Dict[str, str]]
    top_level_entities: List[Dict[str, str]]
    entities_by_id: Dict[str, EntityNode]


@dataclass
class RootNodePlan:
    entity_id: str
    keywords: List[str]
    reason: str = ""


@dataclass
class NodeSearchResult:
    doc_ids: List[str] = field(default_factory=list)
    score_by_doc_id: Dict[str, float] = field(default_factory=dict)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    used_entities: Set[str] = field(default_factory=set)
    used_keywords: Set[str] = field(default_factory=set)


@dataclass
class HierarchicalSearchResult:
    final_doc_ids: List[str] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    used_entities: List[str] = field(default_factory=list)
    used_keywords: List[str] = field(default_factory=list)


class Level0CatalogLoader:
    def __init__(self, data_root: Optional[Path] = None):
        self.data_root = (data_root or DEFAULT_DATA_ROOT).resolve()

    @staticmethod
    def _normalize_entity_id(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _extract_json_block(text: str) -> Optional[Dict[str, Any]]:
        matched = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if not matched:
            return None
        raw_json = matched.group(1).strip()
        try:
            parsed = json.loads(raw_json)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
        raw = (text or "").strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        matched = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not matched:
            return None
        try:
            parsed = json.loads(matched.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _normalize_relation_types(raw: Any) -> List[Dict[str, str]]:
        if not isinstance(raw, list):
            return []
        out: List[Dict[str, str]] = []
        seen: Set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            code = str(item.get("code", "")).strip()
            if not code or code in seen:
                continue
            seen.add(code)
            out.append(
                {
                    "code": code,
                    "description": str(item.get("description", "")).strip(),
                }
            )
        out.sort(key=lambda x: x["code"])
        return out

    @staticmethod
    def _sanitize_keywords(raw: Any, max_keywords: int = 6) -> List[str]:
        if not isinstance(raw, list):
            return []
        out: List[str] = []
        for item in raw:
            text = " ".join(str(item).split()).strip()
            if len(text) < 2:
                continue
            if text in out:
                continue
            out.append(text)
            if len(out) >= max_keywords:
                break
        return out

    @staticmethod
    def _parse_level0_fallback(text: str) -> Dict[str, Any]:
        top_level_entities: List[Dict[str, str]] = []
        for match in re.finditer(
            r"-\s*`([^`]+)`\s*\(id=([^,\)]+),\s*path=`([^`]+)`\)",
            text,
        ):
            top_level_entities.append(
                {
                    "entity_id": str(match.group(2)).strip(),
                    "name": str(match.group(1)).strip(),
                    "relative_path": str(match.group(3)).strip(),
                    "description": "",
                }
            )

        relation_types: List[Dict[str, str]] = []
        for match in re.finditer(r"-\s*`([^`]+)`:\s*(.+)", text):
            relation_types.append(
                {"code": str(match.group(1)).strip(), "description": str(match.group(2)).strip()}
            )

        return {
            "generated_at": "",
            "root_path": "",
            "top_level_entities": top_level_entities,
            "relation_types": relation_types,
            "entity_index": [],
        }

    @staticmethod
    def _parse_entity_md_fallback(text: str, entity_md_path: Path) -> Dict[str, Any]:
        header_match = re.search(r"^#\s*Entity:\s*(.+)$", text, flags=re.MULTILINE)
        entity_id_match = re.search(r"entity_id:\s*`?([^`\n]+)`?", text)
        rel_path_match = re.search(r"relative_path:\s*`([^`]+)`", text)
        parent_match = re.search(r"parent_entity_id:\s*`?([^`\n]+)`?", text)

        entity_id = str(entity_id_match.group(1)).strip() if entity_id_match else ""
        relative_path = str(rel_path_match.group(1)).strip() if rel_path_match else ""
        parent_raw = str(parent_match.group(1)).strip() if parent_match else ""
        parent_entity_id = (
            None if parent_raw.lower() in {"", "none", "null"} else parent_raw
        )
        name = str(header_match.group(1)).strip() if header_match else entity_md_path.parent.name
        return {
            "entity_id": entity_id,
            "name": name,
            "relative_path": relative_path,
            "parent_entity_id": parent_entity_id,
            "child_entity_ids": [],
            "relation_types": [],
        }

    def _load_level0_payload(self, level0_path: Path) -> Dict[str, Any]:
        text = level0_path.read_text(encoding="utf-8")
        payload = self._extract_json_block(text)
        if payload is not None:
            return payload

        payload = self._extract_json_object(text)
        if payload is not None:
            return payload

        return self._parse_level0_fallback(text)

    def _load_entity_payload(self, entity_md_path: Path) -> Dict[str, Any]:
        text = entity_md_path.read_text(encoding="utf-8")
        payload = self._extract_json_block(text)
        if payload is not None:
            return payload
        payload = self._extract_json_object(text)
        if payload is not None:
            return payload
        return self._parse_entity_md_fallback(text, entity_md_path)

    @staticmethod
    def _load_entity_json_payload(entity_json_path: Path) -> Dict[str, Any]:
        raw = entity_json_path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _load_entity_md_text(entity_md_path: Path) -> str:
        if not entity_md_path.exists():
            return ""
        try:
            return entity_md_path.read_text(encoding="utf-8").strip()
        except Exception:
            return ""

    @staticmethod
    def _normalize_md_description(md_text: str) -> str:
        text = (md_text or "").strip()
        if not text:
            return ""
        lines = text.splitlines()
        if lines and lines[0].lstrip().startswith("#"):
            lines = lines[1:]
        return "\n".join(lines).strip()

    def load(self) -> Level0Catalog:
        level0_path = self.data_root / "level0.md"
        if not level0_path.exists():
            raise FileNotFoundError("level0.md 없음: rebuild 실행 필요")

        level0_payload = self._load_level0_payload(level0_path)
        relation_types = self._normalize_relation_types(level0_payload.get("relation_types", []))

        entity_index_raw = level0_payload.get("entity_index", [])
        entity_entries: List[Dict[str, Any]] = []
        if isinstance(entity_index_raw, list) and entity_index_raw:
            for entry in entity_index_raw:
                if not isinstance(entry, dict):
                    continue
                rel_entity_md = str(entry.get("entity_md_path", "")).strip()
                rel_entity_json = str(entry.get("entity_json_path", "")).strip()
                if not rel_entity_md and not rel_entity_json:
                    continue

                if rel_entity_json:
                    entity_json_path = (self.data_root / rel_entity_json).resolve()
                elif rel_entity_md:
                    entity_json_path = (self.data_root / rel_entity_md).resolve().with_name("entity.json")
                else:
                    entity_json_path = self.data_root / "entity.json"

                if rel_entity_md:
                    entity_md_path = (self.data_root / rel_entity_md).resolve()
                else:
                    entity_md_path = entity_json_path.with_name("entity.md")

                entity_entries.append(
                    {
                        "entry_entity_id": self._normalize_entity_id(entry.get("entity_id")),
                        "entity_json_path": entity_json_path,
                        "entity_md_path": entity_md_path,
                    }
                )
        else:
            json_paths = sorted(self.data_root.rglob("entity.json"))
            if json_paths:
                entity_entries = [
                    {
                        "entry_entity_id": None,
                        "entity_json_path": json_path.resolve(),
                        "entity_md_path": json_path.resolve().with_name("entity.md"),
                    }
                    for json_path in json_paths
                ]
            else:
                md_paths = sorted(self.data_root.rglob("entity.md"))
                entity_entries = [
                    {
                        "entry_entity_id": None,
                        "entity_json_path": md_path.resolve().with_name("entity.json"),
                        "entity_md_path": md_path.resolve(),
                    }
                    for md_path in md_paths
                ]

        if not entity_entries:
            raise FileNotFoundError("entity.json/entity.md 인덱스를 찾을 수 없음: rebuild 실행 필요")

        entities_by_id: Dict[str, EntityNode] = {}
        for entry in entity_entries:
            entry_entity_id = entry.get("entry_entity_id")
            entity_json_path = Path(entry["entity_json_path"])
            entity_md_path = Path(entry["entity_md_path"])

            if entity_json_path.exists():
                payload = self._load_entity_json_payload(entity_json_path)
            elif entity_md_path.exists():
                payload = self._load_entity_payload(entity_md_path)
            else:
                raise FileNotFoundError(f"entity.json/entity.md 없음: {entity_json_path.parent}")

            md_text = self._load_entity_md_text(entity_md_path)

            entity_id = self._normalize_entity_id(payload.get("entity_id"))
            if not entity_id:
                entity_id = self._normalize_entity_id(entry_entity_id)
            if not entity_id:
                continue
            name = str(payload.get("name", "")).strip() or entity_md_path.parent.name
            relative_path = str(payload.get("relative_path", "")).strip()
            if not relative_path:
                try:
                    rel_dir = entity_md_path.parent.relative_to(self.data_root).as_posix()
                    relative_path = rel_dir if rel_dir != "." else "."
                except ValueError:
                    relative_path = "."

            parent_entity_id = self._normalize_entity_id(payload.get("parent_entity_id"))
            child_entity_ids: List[str] = []
            child_entities_raw = payload.get("child_entities", [])
            if isinstance(child_entities_raw, list):
                for item in child_entities_raw:
                    if not isinstance(item, dict):
                        continue
                    child_id = self._normalize_entity_id(item.get("entity_id") or item.get("id"))
                    if child_id and child_id not in child_entity_ids:
                        child_entity_ids.append(child_id)

            if not child_entity_ids:
                child_entity_ids = [
                    child_id
                    for child_id in (
                        self._normalize_entity_id(item) for item in payload.get("child_entity_ids", [])
                    )
                    if child_id
                ]
            description = self._normalize_md_description(md_text)
            if not description:
                description = str(payload.get("description", "")).strip()
            node_relation_types = self._normalize_relation_types(payload.get("relation_types", []))

            entities_by_id[entity_id] = EntityNode(
                entity_id=entity_id,
                name=name,
                relative_path=relative_path,
                parent_entity_id=parent_entity_id,
                child_entity_ids=child_entity_ids,
                description=description,
                relation_types=node_relation_types or relation_types,
                entity_md_path=entity_md_path,
                entity_json_path=entity_json_path,
                entity_md_text=md_text,
                entity_json=payload,
            )

        top_level_entities: List[Dict[str, str]] = []
        top_level_raw = level0_payload.get("top_level_entities", [])
        if isinstance(top_level_raw, list):
            for item in top_level_raw:
                if not isinstance(item, dict):
                    continue
                entity_id = self._normalize_entity_id(item.get("entity_id"))
                if not entity_id or entity_id not in entities_by_id:
                    continue
                top_level_entities.append(
                    {
                        "entity_id": entity_id,
                        "name": str(item.get("name", "")).strip() or entities_by_id[entity_id].name,
                        "relative_path": str(item.get("relative_path", "")).strip()
                        or entities_by_id[entity_id].relative_path,
                        "description": str(item.get("description", "")).strip()
                        or entities_by_id[entity_id].description,
                    }
                )

        if not top_level_entities:
            # fallback: parent가 root('.')로 추정되는 엔티티를 top-level로 간주
            root_candidate_ids = {
                node.entity_id for node in entities_by_id.values() if node.relative_path == "."
            }
            for node in sorted(entities_by_id.values(), key=lambda x: x.relative_path):
                if node.parent_entity_id in root_candidate_ids or node.relative_path.count("/") == 0:
                    if node.relative_path == ".":
                        continue
                    top_level_entities.append(
                        {
                            "entity_id": node.entity_id,
                            "name": node.name,
                            "relative_path": node.relative_path,
                            "description": node.description,
                        }
                    )

        return Level0Catalog(
            generated_at=str(level0_payload.get("generated_at", "")),
            root_path=str(level0_payload.get("root_path", self.data_root.as_posix())),
            relation_types=relation_types,
            top_level_entities=top_level_entities,
            entities_by_id=entities_by_id,
        )


class NodeSearchPlannerLLM:
    KOREAN_PARTICLE_SUFFIXES = (
        "으로서",
        "으로써",
        "으로",
        "에서",
        "에게",
        "한테",
        "까지",
        "부터",
        "처럼",
        "보다",
        "라면",
        "이면",
        "이라고",
        "라고",
        "이며",
        "이고",
        "과",
        "와",
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "의",
        "도",
        "만",
        "에",
        "로",
    )

    def __init__(
        self,
        client: openai.OpenAI,
        model: str = "gpt-4o-mini",
        max_root_nodes: int = MAX_ROOT_NODES_DEFAULT,
        debug: bool = False,
    ):
        self.client = client
        self.model = model
        self.max_root_nodes = max(1, max_root_nodes)
        self.debug = debug

    @staticmethod
    def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
        raw = (text or "").strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        matched = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not matched:
            return None
        try:
            parsed = json.loads(matched.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _normalize_keyword(token: str) -> str:
        cleaned = " ".join((token or "").split()).strip()
        if len(cleaned) < 2:
            return ""
        for suffix in NodeSearchPlannerLLM.KOREAN_PARTICLE_SUFFIXES:
            if cleaned.endswith(suffix) and len(cleaned) - len(suffix) >= 2:
                cleaned = cleaned[: -len(suffix)]
                break
        return cleaned

    @staticmethod
    def _simple_query_keywords(query: str, max_keywords: int = 5) -> List[str]:
        tokens = re.findall(r"[A-Za-z0-9가-힣_+.-]{2,}", query or "")
        out: List[str] = []
        for token in tokens:
            for candidate in (token, NodeSearchPlannerLLM._normalize_keyword(token)):
                if len(candidate) < 2:
                    continue
                if candidate in out:
                    continue
                out.append(candidate)
                if len(out) >= max_keywords:
                    break
            if len(out) >= max_keywords:
                break
        return out

    @staticmethod
    def _compact_text(text: str, max_chars: int = 800) -> str:
        compact = " ".join((text or "").split()).strip()
        if len(compact) <= max_chars:
            return compact
        return compact[: max_chars - 3] + "..."

    @staticmethod
    def _sanitize_keywords(raw: Any, fallback: Optional[List[str]] = None) -> List[str]:
        fallback = fallback or []
        if not isinstance(raw, list):
            return fallback
        out: List[str] = []
        for item in raw:
            cleaned = NodeSearchPlannerLLM._normalize_keyword(str(item))
            if len(cleaned) < 2:
                continue
            if cleaned in out:
                continue
            out.append(cleaned)
            if len(out) >= 6:
                break
        return out or fallback

    @staticmethod
    def _merge_keywords(primary: List[str], secondary: List[str], max_keywords: int = 8) -> List[str]:
        merged: List[str] = []
        for keyword in primary + secondary:
            cleaned = NodeSearchPlannerLLM._normalize_keyword(keyword)
            if len(cleaned) < 2:
                continue
            if cleaned in merged:
                continue
            merged.append(cleaned)
            if len(merged) >= max_keywords:
                break
        return merged

    def plan(
        self,
        *,
        query: str,
        catalog: Level0Catalog,
        seed_keywords: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[RootNodePlan]:
        available_top_ids = {item["entity_id"] for item in catalog.top_level_entities}
        seed = self._sanitize_keywords(seed_keywords or [], fallback=[])
        fallback_keywords = self._merge_keywords(
            seed,
            self._simple_query_keywords(query),
            max_keywords=8,
        )
        if not fallback_keywords:
            fallback_keywords = ["전산학부"]

        enriched_top_level_entities: List[Dict[str, Any]] = []
        for item in catalog.top_level_entities:
            entity_id = str(item.get("entity_id", "")).strip()
            node = catalog.entities_by_id.get(entity_id)
            enriched_top_level_entities.append(
                {
                    "entity_id": entity_id,
                    "name": item.get("name", ""),
                    "relative_path": item.get("relative_path", ""),
                    "description": item.get("description", ""),
                    "entity_md": self._compact_text(node.entity_md_text if node else "", max_chars=700),
                    "entity_json": node.entity_json if node else {},
                }
            )

        payload = {
            "query": query,
            "seed_keywords": seed,
            "date_filter": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
            "top_level_entities": enriched_top_level_entities,
            "relation_types": catalog.relation_types,
        }
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": PLANNER_SYSTEM_PROMPT.replace(
                            "{max_root_nodes}",
                            str(self.max_root_nodes),
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                temperature=0.1,
            )
            raw = (response.choices[0].message.content or "").strip()
            parsed = self._extract_json_object(raw) or {}
        except Exception as e:
            if self.debug:
                print(f"⚠️ NodeSearchPlannerLLM 실패: {e}")
            parsed = {}

        plans: List[RootNodePlan] = []
        raw_nodes = parsed.get("nodes", [])
        if isinstance(raw_nodes, list):
            for item in raw_nodes:
                if not isinstance(item, dict):
                    continue
                entity_id = str(item.get("entity_id", "")).strip()
                if not entity_id or entity_id not in available_top_ids:
                    continue
                keywords = self._sanitize_keywords(item.get("keywords", []), fallback_keywords)
                reason = str(item.get("reason", "")).strip()
                plans.append(RootNodePlan(entity_id=entity_id, keywords=keywords, reason=reason))
                if len(plans) >= self.max_root_nodes:
                    break

        if plans:
            return plans

        fallback: List[RootNodePlan] = []
        for top_entity in catalog.top_level_entities[: self.max_root_nodes]:
            fallback.append(
                RootNodePlan(
                    entity_id=str(top_entity["entity_id"]),
                    keywords=fallback_keywords,
                    reason="planner fallback",
                )
            )
        return fallback


class RecursiveNodeSearcher:
    def __init__(
        self,
        *,
        client: openai.OpenAI,
        vector_searcher: VectorSearcher,
        catalog: Level0Catalog,
        model: str = "gpt-4o-mini",
        max_depth: int = MAX_DEPTH_DEFAULT,
        max_children_per_node: int = MAX_CHILDREN_PER_NODE_DEFAULT,
        max_workers: int = MAX_WORKERS_DEFAULT,
        node_top_k: int = NODE_TOP_K_DEFAULT,
        final_doc_limit: int = FINAL_DOC_LIMIT_DEFAULT,
        debug: bool = False,
    ):
        self.client = client
        self.vector_searcher = vector_searcher
        self.catalog = catalog
        self.model = model
        self.max_depth = max(1, max_depth)
        try:
            parsed_max_children = int(max_children_per_node)
        except (TypeError, ValueError):
            parsed_max_children = 0
        self.max_children_per_node = parsed_max_children if parsed_max_children > 0 else None
        self.max_workers = max(1, max_workers)
        self.node_top_k = max(1, node_top_k)
        self.final_doc_limit = max(1, final_doc_limit)
        self.debug = debug

    def _limit_children(self, items: List[Any]) -> List[Any]:
        if self.max_children_per_node is None:
            return list(items)
        return list(items[: self.max_children_per_node])

    @staticmethod
    def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
        raw = (text or "").strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        matched = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not matched:
            return None
        try:
            parsed = json.loads(matched.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _sanitize_keywords(raw: Any, fallback: List[str]) -> List[str]:
        fallback_sanitized: List[str] = []
        for item in fallback:
            cleaned = " ".join(str(item).split()).strip()
            if len(cleaned) < 2:
                continue
            if cleaned in fallback_sanitized:
                continue
            fallback_sanitized.append(cleaned)
            if len(fallback_sanitized) >= 3:
                break

        if not isinstance(raw, list):
            return fallback_sanitized
        out: List[str] = []
        for item in raw:
            cleaned = " ".join(str(item).split()).strip()
            if len(cleaned) < 2:
                continue
            if cleaned in out:
                continue
            out.append(cleaned)
            if len(out) >= 3:
                break
        return out or fallback_sanitized

    @staticmethod
    def _dedupe_keep_order(items: List[str], max_items: int) -> List[str]:
        out: List[str] = []
        for item in items:
            cleaned = str(item).strip()
            if not cleaned or cleaned in out:
                continue
            out.append(cleaned)
            if len(out) >= max_items:
                break
        return out

    @staticmethod
    def _parse_bool(value: Any, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y"}:
                return True
            if lowered in {"false", "0", "no", "n"}:
                return False
            return default
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    @staticmethod
    def _parse_non_negative_int(value: Any, default: int = 0) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return max(0, default)
        return max(0, parsed)

    @staticmethod
    def _compact_text(text: str, max_chars: int = 900) -> str:
        compact = " ".join((text or "").split()).strip()
        if len(compact) <= max_chars:
            return compact
        return compact[: max_chars - 3] + "..."

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        return {
            token.lower()
            for token in re.findall(r"[A-Za-z0-9가-힣_+.-]{2,}", text or "")
            if len(token) >= 2
        }

    def _rank_child_entities(
        self,
        *,
        query: str,
        keywords: List[str],
        child_entities: List[EntityNode],
    ) -> List[EntityNode]:
        if not child_entities:
            return []

        query_text = f"{query} {' '.join(keywords)}".lower()
        intent_tokens = self._tokenize(query_text)

        def score(child: EntityNode) -> tuple[int, int]:
            child_tokens = self._tokenize(
                f"{child.name} {child.relative_path} {child.description}"
            )
            overlap = len(intent_tokens.intersection(child_tokens))
            name = str(child.name).lower().strip()
            path_leaf = str(child.relative_path).split("/")[-1].lower().strip()
            boost = 0
            if name and name in query_text:
                boost += 2
            if path_leaf and path_leaf in query_text:
                boost += 3
            return (boost + overlap, -len(child.relative_path))

        return sorted(child_entities, key=score, reverse=True)

    def _build_local_hit_summary(self, local_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        summary: List[Dict[str, Any]] = []
        for hit in local_hits[: self.node_top_k]:
            metadata = hit.get("metadata", {}) or {}
            summary.append(
                {
                    "doc_id": str(hit.get("doc_id", "")).strip(),
                    "score": float(hit.get("score", 0.0)),
                    "title": metadata.get("title", ""),
                    "name": metadata.get("name", ""),
                    "date": metadata.get("date", "") or metadata.get("event_date", ""),
                    "snippet": " ".join(str(hit.get("content", "")).split())[:260],
                }
            )
        return summary

    def _llm_node_decision(
        self,
        *,
        query: str,
        entity: EntityNode,
        keywords: List[str],
        local_hits: List[Dict[str, Any]],
        child_entities: List[EntityNode],
        depth: int,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> Dict[str, Any]:
        payload = {
            "query": query,
            "depth": depth,
            "max_depth": self.max_depth,
            "max_children_per_node": self.max_children_per_node,
            "date_filter": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
            "current_entity": {
                "entity_id": entity.entity_id,
                "name": entity.name,
                "relative_path": entity.relative_path,
                "description": entity.description,
                "relation_types": entity.relation_types,
                "entity_md": self._compact_text(entity.entity_md_text, max_chars=1200),
                "entity_json": entity.entity_json,
            },
            "keywords": keywords,
            "local_vector_hits": self._build_local_hit_summary(local_hits),
            "child_entities": [
                {
                    "entity_id": child.entity_id,
                    "name": child.name,
                    "relative_path": child.relative_path,
                    "description": child.description,
                    "entity_md": self._compact_text(child.entity_md_text, max_chars=700),
                    "entity_json": child.entity_json,
                }
                for child in child_entities
            ],
        }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": NODE_JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                temperature=0.1,
            )
            raw = (response.choices[0].message.content or "").strip()
            parsed = self._extract_json_object(raw)
            return parsed if parsed else {}
        except Exception as e:
            if self.debug:
                print(f"⚠️ RecursiveNodeSearcher LLM 실패(entity={entity.entity_id}): {e}")
            return {}

    def _search_node(
        self,
        *,
        query: str,
        entity_id: str,
        keywords: List[str],
        depth: int,
        start_date: Optional[date],
        end_date: Optional[date],
        exclude_doc_ids: Optional[List[str]] = None,
    ) -> NodeSearchResult:
        result = NodeSearchResult()
        entity = self.catalog.entities_by_id.get(entity_id)
        if entity is None:
            result.trace.append(
                {"entity_id": entity_id, "depth": depth, "stopped": True, "reason": "entity_not_found"}
            )
            return result

        result.used_entities.add(entity.entity_id)
        result.used_keywords.update(keywords)

        if depth > self.max_depth:
            result.trace.append(
                {"entity_id": entity_id, "depth": depth, "stopped": True, "reason": "depth_limit_reached"}
            )
            return result

        local_hits = self.vector_searcher.search_in_entity(
            entity_id=entity.entity_id,
            query=query,
            keywords=keywords,
            top_k=self.node_top_k,
            start_date=start_date,
            end_date=end_date,
            exclude_doc_ids=exclude_doc_ids or [],
        )
        local_doc_ids = self._dedupe_keep_order(
            [str(hit.get("doc_id", "")).strip() for hit in local_hits],
            max_items=self.node_top_k,
        )
        local_score_map: Dict[str, float] = {
            str(hit.get("doc_id", "")).strip(): float(hit.get("score", 0.0))
            for hit in local_hits
            if str(hit.get("doc_id", "")).strip()
        }

        child_entities: List[EntityNode] = [
            self.catalog.entities_by_id[child_id]
            for child_id in entity.child_entity_ids
            if child_id in self.catalog.entities_by_id
        ]
        entity_doc_count = self._parse_non_negative_int(entity.entity_json.get("doc_count"), default=0)

        # leaf 노드는 하위 확장 판단이 필요 없으므로 node-judge LLM 호출을 생략한다.
        decision_reason = "fallback"
        decision: Dict[str, Any] = {}
        if child_entities:
            decision = self._llm_node_decision(
                query=query,
                entity=entity,
                keywords=keywords,
                local_hits=local_hits,
                child_entities=child_entities,
                depth=depth,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            decision_reason = "leaf_fast_path"

        default_relevant = bool(local_hits or child_entities)
        default_sufficient = bool(local_hits)
        is_relevant = self._parse_bool(
            decision.get("is_relevant") if decision else None,
            default_relevant,
        )
        is_sufficient = self._parse_bool(
            decision.get("is_sufficient") if decision else None,
            default_sufficient,
        )
        selected_doc_ids_raw = decision.get("selected_doc_ids", []) if decision else []
        selected_doc_ids: List[str] = []
        if isinstance(selected_doc_ids_raw, list):
            for doc_id in selected_doc_ids_raw:
                text = str(doc_id).strip()
                if text and text in local_doc_ids and text not in selected_doc_ids:
                    selected_doc_ids.append(text)
        if not selected_doc_ids:
            selected_doc_ids = local_doc_ids[: min(8, self.node_top_k)]

        next_children_raw = decision.get("next_children", []) if decision else []
        next_children: List[Dict[str, Any]] = []
        child_id_set = {child.entity_id for child in child_entities}
        if isinstance(next_children_raw, list):
            for item in next_children_raw:
                if not isinstance(item, dict):
                    continue
                child_id = str(item.get("entity_id", "")).strip()
                if not child_id or child_id not in child_id_set:
                    continue
                child_keywords = self._sanitize_keywords(item.get("keywords", []), keywords)
                next_children.append({"entity_id": child_id, "keywords": child_keywords})
                if (
                    self.max_children_per_node is not None
                    and len(next_children) >= self.max_children_per_node
                ):
                    break

        if not next_children and not is_sufficient and depth < self.max_depth:
            ranked_children = self._rank_child_entities(
                query=query,
                keywords=keywords,
                child_entities=child_entities,
            )
            for child in self._limit_children(ranked_children):
                next_children.append({"entity_id": child.entity_id, "keywords": keywords})

        force_empty_entity_expansion = (
            entity_doc_count == 0
            and depth < self.max_depth
            and bool(child_entities)
        )
        if force_empty_entity_expansion:
            is_relevant = True
            is_sufficient = False
            if not next_children:
                ranked_children = self._rank_child_entities(
                    query=query,
                    keywords=keywords,
                    child_entities=child_entities,
                )
                for child in self._limit_children(ranked_children):
                    next_children.append({"entity_id": child.entity_id, "keywords": keywords})

        query_context = f"{query} {' '.join(keywords)}".lower()
        root_name = str(entity.name).lower().strip()
        root_path = str(entity.relative_path).split("/")[-1].lower().strip()
        root_hint_in_query = (root_name and root_name in query_context) or (
            root_path and root_path in query_context
        )
        force_root_expansion = (
            depth == 1
            and not is_relevant
            and not local_hits
            and bool(child_entities)
            and root_hint_in_query
            and depth < self.max_depth
        )
        if force_root_expansion:
            if not next_children:
                ranked_children = self._rank_child_entities(
                    query=query,
                    keywords=keywords,
                    child_entities=child_entities,
                )
                for child in self._limit_children(ranked_children):
                    next_children.append({"entity_id": child.entity_id, "keywords": keywords})
            is_relevant = bool(next_children)

        trace_entry: Dict[str, Any] = {
            "entity_id": entity.entity_id,
            "entity_name": entity.name,
            "depth": depth,
            "keywords": keywords,
            "entity_doc_count": entity_doc_count,
            "local_hit_count": len(local_hits),
            "selected_doc_count": len(selected_doc_ids),
            "is_relevant": is_relevant,
            "is_sufficient": is_sufficient,
            "next_children": next_children,
            "reason": str(decision.get("reason", "")).strip() if decision else decision_reason,
            "force_empty_entity_expansion": force_empty_entity_expansion,
            "force_root_expansion": force_root_expansion,
        }
        result.trace.append(trace_entry)

        if not is_relevant:
            return result

        merged_doc_ids: List[str] = list(selected_doc_ids)
        merged_score_map: Dict[str, float] = {doc_id: local_score_map.get(doc_id, 0.0) for doc_id in merged_doc_ids}

        if not is_sufficient and depth < self.max_depth and next_children:
            exclude_set = set(exclude_doc_ids or [])
            exclude_set.update(merged_doc_ids)
            child_jobs = self._limit_children(next_children)
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(child_jobs))) as executor:
                future_map = {
                    executor.submit(
                        self._search_node,
                        query=query,
                        entity_id=job["entity_id"],
                        keywords=job["keywords"],
                        depth=depth + 1,
                        start_date=start_date,
                        end_date=end_date,
                        exclude_doc_ids=list(exclude_set),
                    ): job
                    for job in child_jobs
                }
                for future in as_completed(future_map):
                    child_result = future.result()
                    merged_doc_ids.extend(child_result.doc_ids)
                    for doc_id, score in child_result.score_by_doc_id.items():
                        prev_score = merged_score_map.get(doc_id)
                        if prev_score is None or score > prev_score:
                            merged_score_map[doc_id] = score
                    result.trace.extend(child_result.trace)
                    result.used_entities.update(child_result.used_entities)
                    result.used_keywords.update(child_result.used_keywords)

        deduped_doc_ids = self._dedupe_keep_order(merged_doc_ids, max_items=self.final_doc_limit * 2)
        ranked_doc_ids = sorted(
            deduped_doc_ids,
            key=lambda doc_id: merged_score_map.get(doc_id, 0.0),
            reverse=True,
        )
        result.doc_ids = ranked_doc_ids[: self.node_top_k]
        result.score_by_doc_id = {doc_id: merged_score_map.get(doc_id, 0.0) for doc_id in result.doc_ids}
        return result

    def search(
        self,
        *,
        query: str,
        root_plans: List[RootNodePlan],
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> HierarchicalSearchResult:
        overall_trace: List[Dict[str, Any]] = []
        overall_entities: Set[str] = set()
        overall_keywords: Set[str] = set()
        score_by_doc_id: Dict[str, float] = {}

        if not root_plans:
            return HierarchicalSearchResult()

        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(root_plans))) as executor:
            future_map = {
                executor.submit(
                    self._search_node,
                    query=query,
                    entity_id=plan.entity_id,
                    keywords=plan.keywords,
                    depth=1,
                    start_date=start_date,
                    end_date=end_date,
                    exclude_doc_ids=[],
                ): plan
                for plan in root_plans
            }
            for future in as_completed(future_map):
                plan = future_map[future]
                node_result = future.result()
                overall_trace.append(
                    {
                        "phase": "root_plan",
                        "entity_id": plan.entity_id,
                        "keywords": plan.keywords,
                        "reason": plan.reason,
                    }
                )
                overall_trace.extend(node_result.trace)
                overall_entities.update(node_result.used_entities)
                overall_keywords.update(node_result.used_keywords)
                for doc_id, score in node_result.score_by_doc_id.items():
                    prev = score_by_doc_id.get(doc_id)
                    if prev is None or score > prev:
                        score_by_doc_id[doc_id] = score

        ranked_doc_ids = sorted(score_by_doc_id.keys(), key=lambda doc_id: score_by_doc_id[doc_id], reverse=True)
        final_doc_ids = ranked_doc_ids[: self.final_doc_limit]
        return HierarchicalSearchResult(
            final_doc_ids=final_doc_ids,
            trace=overall_trace,
            used_entities=sorted(overall_entities),
            used_keywords=sorted(overall_keywords),
        )


class HierarchicalNodeSearchOrchestrator:
    def __init__(
        self,
        *,
        api_key: str,
        vector_searcher: VectorSearcher,
        data_root: Optional[Path] = None,
        child_model: str = "gpt-4o-mini",
        max_depth: int = MAX_DEPTH_DEFAULT,
        max_children_per_node: int = MAX_CHILDREN_PER_NODE_DEFAULT,
        max_workers: int = MAX_WORKERS_DEFAULT,
        node_top_k: int = NODE_TOP_K_DEFAULT,
        final_doc_limit: int = FINAL_DOC_LIMIT_DEFAULT,
        max_root_nodes: Optional[int] = None,
        debug: bool = False,
    ):
        self.client = openai.OpenAI(api_key=api_key)
        self.vector_searcher = vector_searcher
        self.child_model = child_model
        self.debug = debug
        self.loader = Level0CatalogLoader(data_root=data_root)
        self.max_depth = max_depth
        self.max_children_per_node = max_children_per_node
        self.max_workers = max_workers
        self.node_top_k = node_top_k
        self.final_doc_limit = final_doc_limit
        if max_root_nodes is None:
            max_root_nodes = int(os.getenv("HIERARCHY_MAX_ROOT_NODES", str(MAX_ROOT_NODES_DEFAULT)))
        self.max_root_nodes = max(1, int(max_root_nodes))

    def search(
        self,
        *,
        query: str,
        seed_keywords: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> HierarchicalSearchResult:
        catalog = self.loader.load()
        planner = NodeSearchPlannerLLM(
            client=self.client,
            model=self.child_model,
            max_root_nodes=self.max_root_nodes,
            debug=self.debug,
        )
        root_plans = planner.plan(
            query=query,
            catalog=catalog,
            seed_keywords=seed_keywords,
            start_date=start_date,
            end_date=end_date,
        )

        searcher = RecursiveNodeSearcher(
            client=self.client,
            vector_searcher=self.vector_searcher,
            catalog=catalog,
            model=self.child_model,
            max_depth=self.max_depth,
            max_children_per_node=self.max_children_per_node,
            max_workers=self.max_workers,
            node_top_k=self.node_top_k,
            final_doc_limit=self.final_doc_limit,
            debug=self.debug,
        )
        return searcher.search(
            query=query,
            root_plans=root_plans,
            start_date=start_date,
            end_date=end_date,
        )
