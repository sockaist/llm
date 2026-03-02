"""
SQL 구조화 검색 + 요약 + 키워드 재생성 모듈.

목표:
1) 입력 질의를 보고 LLM이 안전한 SELECT SQL을 생성
2) SoC 관계형 DB에서 SQL 실행
3) 결과를 작은 모델로 요약
4) SQL 요약을 반영해 vector 검색용 키워드를 재생성
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import openai
import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo


SOC_SCHEMA_PROMPT = """
[DB 개요]
- 이 DB는 KAIST SoC(전산학부) 지식 그래프를 관계형 테이블로 저장한다.
- 질의에 필요한 핵심 테이블은 professors, laboratories, fields, relations, relation_types, nodes 이다.

[핵심 테이블 스키마 설명]
1) nodes
- node_id (PK)
- node_type (enum): DEPARTMENT, COURSE, COURSE_TYPE, TRACK, DETAIL_REQ, TAG, PROFESSOR, LABORATORY, FIELD
- description

2) professors
- node_id (PK, FK -> nodes.node_id)
- name, email, major, degree, web, phone, office, source_ref, exp, description

3) laboratories
- node_id (PK, FK -> nodes.node_id)
- name, web, email, phone, office, intro, etc, description

4) fields
- node_id (PK, FK -> nodes.node_id)
- field_name (아래 canonical 값 중 하나)
- description

field_name canonical 목록 (고정):
- Computing Theory (컴퓨팅 이론)
- Systems-Networks (시스템-네트워크)
- Software Design (소프트웨어 설계)
- Secure Computing (보안 컴퓨팅)
- Visual Computing (비주얼 컴퓨팅)
- AI-Information Service (AI-정보 서비스)
- Social Computing (소셜 컴퓨팅)
- Interactive Computing (인터랙티브 컴퓨팅)

5) relation_types
- relation_type_id (PK)
- code (관계 코드)
- description
- 대표 code:
  - RESEARCHES_IN: 연구 분야 연관
  - AFFILIATED_WITH: 소속/연계
  - REQUIRES, INCLUDES, EXCLUDES, EQUIVALENT_TO, SUBSTITUTES, COUNTS_AS, CAPS

6) relations
- relation_id (PK)
- relation_type_id (FK -> relation_types.relation_type_id)
- src_node_id (FK -> nodes.node_id)
- dst_node_id (FK -> nodes.node_id)
- valid_years, rule_id, evidence_id, description

[조회 규칙]
- 반드시 SELECT 또는 WITH ... SELECT 만 생성
- 조인 시 relation_types.code로 관계 의미를 식별
- 교수/연구실/연구분야 매핑 예시:
  - 교수의 연구분야: professors p -> relations r -> relation_types rt(code='RESEARCHES_IN') -> fields f
  - 교수-연구실 소속: professors p -> relations r -> relation_types rt(code='AFFILIATED_WITH') -> laboratories l
- 연구실 정보를 붙일 때는 반드시 AFFILIATED_WITH 관계로만 조인한다.
- 결과는 사용자가 읽기 좋은 컬럼 alias를 사용(name, field_name, laboratory_name, web, office, exp 등)
- 기본적으로 장문 컬럼(exp, etc, intro, description)은 SELECT에서 제외한다.
  (사용자 질문이 해당 상세 설명을 직접 요구할 때만 포함)
- research field 필터는 fields.field_name의 canonical 값으로 비교한다.
  - 예: '머신러닝', 'AI', '인공지능' -> 'AI-Information Service'
  - 예: '시스템', '네트워크' -> 'Systems-Networks'
  - 예: '보안' -> 'Secure Computing'
  - 예: '비전', '그래픽스' -> 'Visual Computing'
  - 예: 'HCI', '인터랙션' -> 'Interactive Computing'
  - 예: '이론' -> 'Computing Theory'
- 사용자 질문에 '전산학부/전산'이 들어가도 professors.major='전산학부' 같은 하드 필터는 기본적으로 넣지 않는다.
  - major는 자유 텍스트 전공/연구설명일 수 있으므로, 질문이 명시적으로 major 비교를 요구할 때만 사용한다.
""".strip()


SQL_GENERATION_PROMPT = """
너는 SQL 쿼리 생성기다.

다음 스키마를 기반으로 사용자 질문에 답하기 위한 SQL을 만들어라.
{schema}

반드시 JSON으로만 답하라:
{{
  "sql": "SELECT ...",
  "reason": "왜 이 SQL이 질문에 맞는지 한 줄 설명"
}}

제약:
- SELECT/CTE SELECT만 허용.
- 단일 statement만 허용.
- 반드시 LIMIT {max_rows} 이하를 포함.
- 위험 명령(INSERT/UPDATE/DELETE/DDL/트랜잭션 등) 금지.
- 입력으로 주어진 base_keywords와 additional_context에서 얻은 단서를 SQL WHERE/JOIN에 반영하라.
""".strip()


SQL_SUMMARY_PROMPT = """
너는 SQL 결과를 사용자 질문에 맞춰 요약하는 어시스턴트다.

반드시 JSON으로만 답하라:
{{
  "summary": "사용자가 바로 이해할 수 있는 2~5문장 요약",
  "facts": [
    {{"name": "핵심 엔티티 이름", "detail": "연관 설명"}}
  ],
  "suggested_keywords": ["벡터 검색에 유용한 키워드1", "키워드2"]
}}

규칙:
- summary는 개수 정보(예: 총 n명)를 포함하라.
- facts는 최대 8개.
- suggested_keywords는 1~8개, 중복 없이.
- 시간 표현(최근/요즘/이번 학기 등)은 suggested_keywords에서 제외.
""".strip()


KEYWORD_REFINEMENT_PROMPT = """
너는 벡터 검색 키워드 재작성기다.

반드시 JSON으로만 답하라:
{{
  "keywords": ["키워드1", "키워드2"]
}}

규칙:
- SQL 요약/사실을 우선 반영하라.
- 너무 일반적인 단어는 제외하고 구체명(교수명, 연구실명, field_name, 관계명)을 우선한다.
- 1~8개, 중복 없이.
- 시간 표현(최근/요즘/이번/최신 등) 제외.
""".strip()


ALLOWED_TABLES = {
    "nodes",
    "professors",
    "laboratories",
    "fields",
    "relations",
    "relation_types",
    "departments",
    "courses",
    "course_types",
    "graduate_tracks",
    "detail_requirements",
    "tags",
    "course_mappings",
}

BLOCKED_SQL_PATTERN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|grant|revoke|create|"
    r"comment|copy|call|do|begin|commit|rollback|vacuum|analyze|refresh)\b",
    re.IGNORECASE,
)


@dataclass
class SQLContextResult:
    sql: Optional[str] = None
    reason: Optional[str] = None
    row_count: int = 0
    rows: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    facts: List[Dict[str, str]] = field(default_factory=list)
    refined_keywords: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def has_context(self) -> bool:
        return bool(self.summary or self.facts or self.row_count)


class SQLContextRetriever:
    """LLM 기반 SQL 보조 검색기."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        summary_model: str = "gpt-4o-mini",
        keyword_model: str = "gpt-4o-mini",
        soc_db_dsn: Optional[str] = None,
        max_rows: int = 100,
    ):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.summary_model = summary_model
        self.keyword_model = keyword_model
        self.max_rows = max(1, min(max_rows, 200))
        self.debug = os.getenv("DEBUG_SQL_CONTEXT") == "1"
        self.soc_db_dsn = self._resolve_soc_db_dsn(soc_db_dsn)

    def _resolve_soc_db_dsn(self, explicit_dsn: Optional[str]) -> Optional[str]:
        candidates: List[str] = []
        if explicit_dsn:
            candidates.append(explicit_dsn)

        env_dsn = os.getenv("SOC_DB_DSN") or os.getenv("SOC_DATABASE_URL")
        if env_dsn:
            candidates.append(env_dsn)

        base_dsn = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
        if base_dsn:
            candidates.append(base_dsn)
            alt_dsn = self._replace_dbname(base_dsn, "kaist_soc")
            if alt_dsn:
                candidates.append(alt_dsn)

        deduped: List[str] = []
        for dsn in candidates:
            if dsn and dsn not in deduped:
                deduped.append(dsn)

        for dsn in deduped:
            if self._has_required_tables(dsn):
                if self.debug:
                    print(f"✅ SQLContextRetriever DSN 선택 완료: {self._mask_dsn(dsn)}")
                return dsn

        if self.debug and deduped:
            print("⚠️ SQLContextRetriever: required 테이블을 찾지 못해 첫 DSN을 사용합니다.")
        return deduped[0] if deduped else None

    @staticmethod
    def _replace_dbname(dsn: str, dbname: str) -> Optional[str]:
        try:
            info = conninfo_to_dict(dsn)
            info["dbname"] = dbname
            return make_conninfo(**info)
        except Exception:
            return None

    @staticmethod
    def _mask_dsn(dsn: str) -> str:
        return re.sub(r"(password=)[^\s]+", r"\1****", dsn)

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value if isinstance(value, (str, int, float, bool, type(None))) else str(value)

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
    def _sanitize_keywords(raw_keywords: Any, max_keywords: int = 8) -> List[str]:
        if not isinstance(raw_keywords, list):
            return []
        stopwords = {"최근", "요즘", "이번", "최신", "정보", "질문", "알려줘", "알려주세요"}
        out: List[str] = []
        for item in raw_keywords:
            if not isinstance(item, str):
                continue
            cleaned = " ".join(item.split()).strip()
            if len(cleaned) < 2:
                continue
            if cleaned in stopwords:
                continue
            if cleaned in out:
                continue
            out.append(cleaned)
            if len(out) >= max_keywords:
                break
        return out

    def _has_required_tables(self, dsn: str) -> bool:
        try:
            with psycopg.connect(dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                          to_regclass('public.professors') IS NOT NULL,
                          to_regclass('public.laboratories') IS NOT NULL,
                          to_regclass('public.fields') IS NOT NULL,
                          to_regclass('public.relations') IS NOT NULL,
                          to_regclass('public.relation_types') IS NOT NULL;
                        """
                    )
                    row = cur.fetchone()
                    return bool(row and all(row))
        except Exception:
            return False

    def _generate_sql(
        self,
        user_query: str,
        normalized_query: str,
        base_keywords: Optional[List[str]] = None,
        additional_context: str = "",
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        try:
            system_prompt = SQL_GENERATION_PROMPT.format(
                schema=SOC_SCHEMA_PROMPT,
                max_rows=self.max_rows,
            )
            keyword_text = ", ".join(base_keywords or [])
            compact_context = " ".join((additional_context or "").split())
            if len(compact_context) > 1800:
                compact_context = compact_context[:1800] + "..."
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"원문 질문: {user_query}\n"
                        f"정규화 질문: {normalized_query}\n"
                        f"base_keywords: [{keyword_text}]\n"
                        f"additional_context: {compact_context}\n"
                        "JSON으로만 응답."
                    ),
                },
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                max_tokens=280,
            )
            raw = (response.choices[0].message.content or "").strip()
            payload = self._extract_json_object(raw)
            if not payload:
                return None, None, f"SQL 생성 JSON 파싱 실패: {raw}"
            sql = payload.get("sql")
            reason = payload.get("reason")
            return sql if isinstance(sql, str) else None, reason if isinstance(reason, str) else None, None
        except Exception as e:
            return None, None, str(e)

    def _validate_sql(self, sql: str) -> tuple[Optional[str], Optional[str]]:
        if not isinstance(sql, str):
            return None, "SQL이 문자열이 아닙니다."

        cleaned = sql.strip().strip(";")
        if not cleaned:
            return None, "SQL이 비어 있습니다."
        if "--" in cleaned or "/*" in cleaned:
            return None, "주석이 포함된 SQL은 허용되지 않습니다."
        if BLOCKED_SQL_PATTERN.search(cleaned):
            return None, "허용되지 않는 SQL 명령이 포함되었습니다."
        if not re.match(r"^\s*(select|with)\b", cleaned, flags=re.IGNORECASE):
            return None, "SELECT/CTE SELECT만 허용됩니다."

        # 다중 statement 방지
        if ";" in cleaned:
            return None, "단일 statement만 허용됩니다."

        cte_names = {
            match.group(1).lower()
            for match in re.finditer(
                r"(?:\bwith\b|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s+as\s*\(",
                cleaned,
                flags=re.IGNORECASE,
            )
        }

        table_refs = re.findall(r"\b(?:from|join)\s+([A-Za-z_][A-Za-z0-9_\.]*)", cleaned, flags=re.IGNORECASE)
        for ref in table_refs:
            table = ref.split(".")[-1].strip().strip('"')
            if table.lower() in cte_names:
                continue
            if table.lower() not in ALLOWED_TABLES:
                return None, f"허용되지 않은 테이블 참조: {table}"

        # LIMIT 강제/보정
        limit_match = re.search(r"\blimit\s+(\d+)\b", cleaned, flags=re.IGNORECASE)
        if not limit_match:
            cleaned = f"{cleaned} LIMIT {self.max_rows}"
        else:
            requested = int(limit_match.group(1))
            if requested > self.max_rows:
                cleaned = re.sub(
                    r"\blimit\s+\d+\b",
                    f"LIMIT {self.max_rows}",
                    cleaned,
                    count=1,
                    flags=re.IGNORECASE,
                )

        return cleaned, None

    def _execute_sql(self, sql: str) -> tuple[List[Dict[str, Any]], Optional[str]]:
        if not self.soc_db_dsn:
            return [], "SoC DB DSN이 설정되지 않았습니다."

        try:
            with psycopg.connect(self.soc_db_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    if cur.description is None:
                        return [], "SELECT 결과가 없습니다."

                    col_names = [desc[0] for desc in cur.description]
                    fetched = cur.fetchmany(self.max_rows)
                    rows = []
                    for row in fetched:
                        row_dict = {}
                        for idx, value in enumerate(row):
                            row_dict[col_names[idx]] = self._to_jsonable(value)
                        rows.append(row_dict)
                    return rows, None
        except Exception as e:
            return [], str(e)

    def _summarize_rows(
        self,
        user_query: str,
        normalized_query: str,
        sql: str,
        rows: List[Dict[str, Any]],
    ) -> tuple[str, List[Dict[str, str]], List[str]]:
        try:
            preview_rows = self._rows_for_summary(rows, max_rows=15)
            input_payload = {
                "user_query": user_query,
                "normalized_query": normalized_query,
                "sql": sql,
                "row_count": len(rows),
                "rows_preview": preview_rows,
            }
            messages = [
                {"role": "system", "content": SQL_SUMMARY_PROMPT},
                {"role": "user", "content": json.dumps(input_payload, ensure_ascii=False)},
            ]
            response = self.client.chat.completions.create(
                model=self.summary_model,
                messages=messages,
                temperature=0.1,
                max_tokens=420,
            )
            raw = (response.choices[0].message.content or "").strip()
            payload = self._extract_json_object(raw) or {}

            summary = payload.get("summary")
            summary_text = summary.strip() if isinstance(summary, str) else ""
            facts_raw = payload.get("facts")
            facts: List[Dict[str, str]] = []
            if isinstance(facts_raw, list):
                for item in facts_raw[:8]:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name", "")).strip()
                    detail = str(item.get("detail", "")).strip()
                    if name or detail:
                        facts.append({"name": name, "detail": detail})
            suggested = self._sanitize_keywords(payload.get("suggested_keywords"))

            if not summary_text:
                summary_text = self._fallback_summary(rows)
            if not facts:
                facts = self._fallback_facts(rows, max_facts=8)
            if not suggested:
                suggested = self._fallback_keywords_from_rows(rows)
            return summary_text, facts, suggested
        except Exception:
            return (
                self._fallback_summary(rows),
                self._fallback_facts(rows),
                self._fallback_keywords_from_rows(rows),
            )

    @staticmethod
    def _rows_for_summary(rows: List[Dict[str, Any]], max_rows: int = 15) -> List[Dict[str, Any]]:
        excluded_keys = {"exp", "etc", "intro", "description", "content"}
        cleaned_rows: List[Dict[str, Any]] = []
        for row in rows[:max_rows]:
            cleaned: Dict[str, Any] = {}
            for key, value in row.items():
                if key in excluded_keys or value is None:
                    continue
                text = " ".join(str(value).split()).strip()
                if not text:
                    continue
                if len(text) > 120:
                    text = text[:117] + "..."
                cleaned[key] = text
            cleaned_rows.append(cleaned if cleaned else row)
        return cleaned_rows

    @staticmethod
    def _fallback_summary(rows: List[Dict[str, Any]]) -> str:
        if not rows:
            return "SQL 검색 결과가 없습니다."
        names: List[str] = []
        for row in rows:
            for key in ("name", "professor_name", "laboratory_name", "field_name", "title"):
                value = row.get(key)
                if isinstance(value, str) and value.strip():
                    names.append(value.strip())
                    break
            if len(names) >= 5:
                break
        preview = ", ".join(names) if names else "대표 항목 없음"
        return f"SQL 검색으로 총 {len(rows)}건을 찾았습니다. 대표 항목: {preview}"

    @staticmethod
    def _fallback_facts(rows: List[Dict[str, Any]], max_facts: Optional[int] = 8) -> List[Dict[str, str]]:
        facts: List[Dict[str, str]] = []
        hard_limit = max_facts if max_facts is not None else len(rows)

        def shorten(text: str, limit: int = 90) -> str:
            compact = " ".join(text.split()).strip()
            if len(compact) <= limit:
                return compact
            return compact[: limit - 3] + "..."

        for row in rows:
            name = ""
            for key in ("name", "professor_name", "laboratory_name", "field_name", "title"):
                value = row.get(key)
                if isinstance(value, str) and value.strip():
                    name = value.strip()
                    break

            detail_parts: List[str] = []
            for key in ("field_name", "laboratory_name", "office", "email", "web", "exp"):
                value = row.get(key)
                if isinstance(value, str) and value.strip():
                    detail_parts.append(f"{key}: {shorten(value)}")
            detail = ", ".join(detail_parts)[:260]

            if not name and not detail:
                continue
            facts.append({"name": name, "detail": detail})
            if len(facts) >= hard_limit:
                break
        return facts

    @staticmethod
    def _fallback_keywords_from_rows(rows: List[Dict[str, Any]], max_keywords: int = 8) -> List[str]:
        candidates: List[str] = []
        for row in rows[:20]:
            for key in ("name", "professor_name", "laboratory_name", "field_name"):
                value = row.get(key)
                if isinstance(value, str) and value.strip():
                    candidates.append(value.strip())
        deduped: List[str] = []
        for keyword in candidates:
            if keyword not in deduped:
                deduped.append(keyword)
            if len(deduped) >= max_keywords:
                break
        return deduped

    def _refine_keywords(
        self,
        user_query: str,
        normalized_query: str,
        base_keywords: List[str],
        summary: str,
        facts: List[Dict[str, str]],
        suggested_keywords: List[str],
    ) -> List[str]:
        try:
            payload = {
                "user_query": user_query,
                "normalized_query": normalized_query,
                "base_keywords": base_keywords,
                "sql_summary": summary,
                "sql_facts": facts[:8],
                "sql_suggested_keywords": suggested_keywords,
            }
            messages = [
                {"role": "system", "content": KEYWORD_REFINEMENT_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ]
            response = self.client.chat.completions.create(
                model=self.keyword_model,
                messages=messages,
                temperature=0.1,
                max_tokens=180,
            )
            raw = (response.choices[0].message.content or "").strip()
            parsed = self._extract_json_object(raw) or {}
            refined = self._sanitize_keywords(parsed.get("keywords"))
            if refined:
                return refined
        except Exception:
            pass

        # fallback: LLM suggested + base keywords를 합친다.
        merged: List[str] = []
        for keyword in suggested_keywords + base_keywords:
            if keyword not in merged:
                merged.append(keyword)
            if len(merged) >= 8:
                break
        return merged

    def retrieve_and_refine(
        self,
        user_query: str,
        normalized_query: str,
        base_keywords: Optional[List[str]] = None,
        additional_context: str = "",
    ) -> SQLContextResult:
        result = SQLContextResult(refined_keywords=list(base_keywords or []))
        base_keywords_list = list(base_keywords or [])

        sql, reason, sql_error = self._generate_sql(
            user_query,
            normalized_query,
            base_keywords=base_keywords_list,
            additional_context=additional_context,
        )
        result.sql = sql
        result.reason = reason
        if sql_error:
            result.error = f"SQL 생성 실패: {sql_error}"
            return result

        validated_sql, validation_error = self._validate_sql(sql or "")
        if validation_error:
            result.error = f"SQL 검증 실패: {validation_error}"
            return result

        result.sql = validated_sql
        rows, exec_error = self._execute_sql(validated_sql or "")
        if exec_error:
            result.error = f"SQL 실행 실패: {exec_error}"
            return result

        result.rows = rows
        result.row_count = len(rows)
        summary, facts, suggested_keywords = self._summarize_rows(
            user_query=user_query,
            normalized_query=normalized_query,
            sql=validated_sql or "",
            rows=rows,
        )
        result.summary = summary
        result.facts = facts
        result.refined_keywords = self._refine_keywords(
            user_query=user_query,
            normalized_query=normalized_query,
            base_keywords=base_keywords_list,
            summary=summary,
            facts=facts,
            suggested_keywords=suggested_keywords,
        )

        if self.debug:
            print(
                "🧭 SQLContextRetriever 결과:",
                {
                    "sql": result.sql,
                    "reason": result.reason,
                    "row_count": result.row_count,
                    "summary": result.summary,
                    "refined_keywords": result.refined_keywords,
                    "error": result.error,
                },
            )
        return result

    @staticmethod
    def build_context_text(result: SQLContextResult) -> str:
        if not result or not result.has_context():
            return ""

        lines: List[str] = []
        if result.summary:
            lines.append(result.summary)
        if result.facts:
            lines.append("핵심 항목:")
            for idx, fact in enumerate(result.facts, start=1):
                name = fact.get("name", "").strip()
                detail = fact.get("detail", "").strip()
                if name and detail:
                    lines.append(f"{idx}. {name}: {detail}")
                elif name:
                    lines.append(f"{idx}. {name}")
                elif detail:
                    lines.append(f"{idx}. {detail}")

        # LLM 요약 항목과 별개로, SQL 원본 결과 전건을 축약 형식으로 반드시 포함한다.
        if result.rows:
            lines.append(f"전체 SQL 결과 ({result.row_count}건):")
            for idx, row in enumerate(result.rows, start=1):
                lines.append(f"{idx}. {SQLContextRetriever._compact_row_text(row)}")
        return "\n".join(lines).strip()

    @staticmethod
    def _compact_row_text(row: Dict[str, Any], max_value_len: int = 80) -> str:
        preferred_keys = [
            "name",
            "professor_name",
            "field_name",
            "laboratory_name",
            "office",
            "email",
            "web",
            "phone",
        ]
        parts: List[str] = []
        used: set[str] = set()
        excluded_keys = {"exp", "etc", "intro", "description", "content"}

        def short(v: Any) -> str:
            text = " ".join(str(v).split()).strip()
            if len(text) <= max_value_len:
                return text
            return text[: max_value_len - 3] + "..."

        for key in preferred_keys:
            value = row.get(key)
            if value is None:
                continue
            value_str = short(value)
            if not value_str:
                continue
            parts.append(f"{key}={value_str}")
            used.add(key)

        for key, value in row.items():
            if key in used or key in excluded_keys or value is None:
                continue
            value_str = short(value)
            if not value_str:
                continue
            parts.append(f"{key}={value_str}")
            if len(parts) >= 10:
                break

        return ", ".join(parts) if parts else "(empty row)"
