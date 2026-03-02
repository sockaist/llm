import json
import os
import re
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

import psycopg

try:
    from .config import (
        POSTGRES_DSN,
        POSTGRES_HOST,
        POSTGRES_PORT,
        POSTGRES_DB,
        POSTGRES_USER,
        POSTGRES_PASSWORD,
        PGVECTOR_TABLE,
        VECTOR_SIZE,
    )
    from .embedding import content_embedder, embed_query
except ImportError:
    from config import (  # type: ignore
        POSTGRES_DSN,
        POSTGRES_HOST,
        POSTGRES_PORT,
        POSTGRES_DB,
        POSTGRES_USER,
        POSTGRES_PASSWORD,
        PGVECTOR_TABLE,
        VECTOR_SIZE,
    )
    from embedding import content_embedder, embed_query  # type: ignore


def _safe_ident(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def _vector_literal(vector: List[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vector) + "]"


@dataclass
class SearchHit:
    id: int
    score: float
    payload: Dict[str, Any]


class PGVectorClient:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or POSTGRES_DSN or self._build_dsn()

    def _build_dsn(self) -> str:
        return (
            f"host={POSTGRES_HOST} port={POSTGRES_PORT} dbname={POSTGRES_DB} "
            f"user={POSTGRES_USER} password={POSTGRES_PASSWORD}"
        )

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn)


def get_pgvector_client() -> PGVectorClient:
    return PGVectorClient()


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None

    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    # ISO-like: 2025-02-13, 2025-02-13T00:00:00Z
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    # Dot-separated: 2025.02.13
    m = re.match(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    # Slash-separated: 2025/02/13
    m = re.match(r"^(\d{4})/(\d{1,2})/(\d{1,2})", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    # Korean date: 2025년 2월 13일
    m = re.match(r"^(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일$", text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None

    return None


def _metadata_date_fields(metadata: Dict[str, Any]) -> tuple[Optional[date], Optional[date], Optional[date]]:
    event_date = _parse_date(metadata.get("date"))
    start_date = _parse_date(metadata.get("start"))
    end_date = _parse_date(metadata.get("finish"))
    return event_date, start_date, end_date


def ensure_schema(client: PGVectorClient) -> None:
    table = _safe_ident(PGVECTOR_TABLE)
    dim = int(VECTOR_SIZE)

    with client.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id BIGSERIAL PRIMARY KEY,
                    collection TEXT NOT NULL,
                    source_id TEXT,
                    chunk_index INTEGER NOT NULL,
                    embedding VECTOR({dim}) NOT NULL,
                    content TEXT NOT NULL,
                    event_date DATE,
                    start_date DATE,
                    end_date DATE,
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(collection, source_id, chunk_index)
                );
                """
            )
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS event_date DATE;")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS start_date DATE;")
            cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS end_date DATE;")
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {table}_collection_idx ON {table} (collection);"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {table}_source_id_idx ON {table} (source_id);"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {table}_event_date_idx ON {table} (event_date);"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {table}_start_date_idx ON {table} (start_date);"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS {table}_end_date_idx ON {table} (end_date);"
            )
            cur.execute(
                f"""
                CREATE INDEX IF NOT EXISTS {table}_embedding_ivfflat_idx
                ON {table}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
                """
            )

            # Existing rows backfill: metadata 내 date/start/finish를 날짜 컬럼에 반영
            cur.execute(
                f"""
                SELECT id, metadata
                FROM {table}
                WHERE (event_date IS NULL OR start_date IS NULL OR end_date IS NULL)
                  AND (metadata ? 'date' OR metadata ? 'start' OR metadata ? 'finish');
                """
            )
            rows = cur.fetchall()
            for row_id, metadata in rows:
                meta = metadata if isinstance(metadata, dict) else {}
                event_date, start_date, end_date = _metadata_date_fields(meta)
                cur.execute(
                    f"""
                    UPDATE {table}
                    SET event_date = COALESCE(event_date, %s),
                        start_date = COALESCE(start_date, %s),
                        end_date = COALESCE(end_date, %s)
                    WHERE id = %s;
                    """,
                    (event_date, start_date, end_date, row_id),
                )
        conn.commit()


def initialize_col(client: PGVectorClient, col_name: str) -> None:
    table = _safe_ident(PGVECTOR_TABLE)
    with client.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {table} WHERE collection = %s;", (col_name,))
        conn.commit()


def _extract_raw_text(data: Dict[str, Any]) -> str:
    for key in ("content", "contents", "etc"):
        value = data.get(key, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def create_doc_upsert(client: PGVectorClient, col_name: str, data: Dict[str, Any]) -> None:
    if not data:
        print("Warning: Empty data provided to create_doc_upsert")
        return

    raw_text = _extract_raw_text(data)
    if not raw_text:
        print(f"Warning: Empty content in data for collection {col_name}")
        return

    chunks = content_embedder(raw_text)
    if not chunks:
        print(f"Warning: No chunks generated for collection {col_name}")
        return

    source_id = str(
        data.get("source_path")
        or data.get("id")
        or data.get("link")
        or ""
    )
    metadata = dict(data)
    metadata.pop("content", None)
    metadata.pop("contents", None)
    metadata.pop("etc", None)
    # date 키가 없는 문서도 스키마 일관성을 위해 null로 통일
    if "date" not in metadata:
        metadata["date"] = None
    event_date, start_date, end_date = _metadata_date_fields(metadata)

    table = _safe_ident(PGVECTOR_TABLE)
    with client.connect() as conn:
        with conn.cursor() as cur:
            if source_id:
                cur.execute(
                    f"DELETE FROM {table} WHERE collection = %s AND source_id = %s;",
                    (col_name, source_id),
                )

            for chunk_index, (chunk_text, vector) in enumerate(chunks):
                cur.execute(
                    f"""
                    INSERT INTO {table}
                    (collection, source_id, chunk_index, embedding, content, event_date, start_date, end_date, metadata)
                    VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s, %s::jsonb);
                    """,
                    (
                        col_name,
                        source_id or None,
                        chunk_index,
                        _vector_literal(vector),
                        chunk_text,
                        event_date,
                        start_date,
                        end_date,
                        json.dumps(metadata, ensure_ascii=False),
                    ),
                )
        conn.commit()


def read_doc(client: PGVectorClient, col_name: str, source_id: str) -> Optional[Dict[str, Any]]:
    table = _safe_ident(PGVECTOR_TABLE)
    with client.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, collection, source_id, chunk_index, content, metadata, created_at
                FROM {table}
                WHERE collection = %s AND source_id = %s
                ORDER BY chunk_index ASC;
                """,
                (col_name, str(source_id)),
            )
            rows = cur.fetchall()

    if not rows:
        return None

    return {
        "collection": rows[0][1],
        "source_id": rows[0][2],
        "chunks": [
            {"id": row[0], "chunk_index": row[3], "content": row[4], "metadata": row[5]}
            for row in rows
        ],
    }


def update_doc(client: PGVectorClient, col_name: str, source_id: str, updated_data: Dict[str, Any]) -> None:
    if "id" not in updated_data:
        updated_data["id"] = source_id
    create_doc_upsert(client, col_name, updated_data)


def delete_doc(client: PGVectorClient, col_name: str, source_id: str) -> None:
    table = _safe_ident(PGVECTOR_TABLE)
    with client.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {table} WHERE collection = %s AND source_id = %s;",
                (col_name, str(source_id)),
            )
        conn.commit()


def search_doc(
    client: PGVectorClient,
    query: str,
    col_name: Optional[str],
    k: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    entity_ids: Optional[List[str]] = None,
    metadata_filters: Optional[Dict[str, Any]] = None,
) -> List[SearchHit]:
    query_vector = embed_query(query)
    if not query_vector:
        return []

    table = _safe_ident(PGVECTOR_TABLE)
    query_vector_str = _vector_literal(query_vector)
    where_clauses: List[str] = []
    params: List[Any] = [query_vector_str]

    if col_name:
        where_clauses.append("collection = %s")
        params.append(col_name)

    normalized_entity_ids = [str(entity_id).strip() for entity_id in (entity_ids or []) if str(entity_id).strip()]
    if normalized_entity_ids:
        where_clauses.append("(metadata ->> 'entity_id') = ANY(%s)")
        params.append(normalized_entity_ids)

    if metadata_filters:
        for key in sorted(metadata_filters.keys()):
            value = metadata_filters[key]
            key_text = str(key)
            if isinstance(value, (list, tuple, set)):
                normalized_values = [str(v).strip() for v in value if str(v).strip()]
                if not normalized_values:
                    continue
                where_clauses.append("(metadata ->> %s) = ANY(%s)")
                params.extend([key_text, normalized_values])
            elif value is None:
                where_clauses.append("NOT (metadata ? %s)")
                params.append(key_text)
            else:
                where_clauses.append("(metadata ->> %s) = %s")
                params.extend([key_text, str(value)])

    with client.connect() as conn:
        with conn.cursor() as cur:
            if start_date and end_date:
                where_clauses.append(
                    "COALESCE(end_date, event_date, start_date) >= %s"
                )
                where_clauses.append(
                    "COALESCE(start_date, event_date, end_date) <= %s"
                )
                params.extend([start_date, end_date])
            elif start_date:
                where_clauses.append("COALESCE(end_date, event_date, start_date) >= %s")
                params.append(start_date)
            elif end_date:
                where_clauses.append("COALESCE(start_date, event_date, end_date) <= %s")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            params.extend([query_vector_str, int(k)])
            cur.execute(
                f"""
                SELECT id, collection, content, metadata, source_id, event_date, start_date, end_date, 1 - (embedding <=> %s::vector) AS score
                FROM {table}
                {where_clause}
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                params,
            )
            rows = cur.fetchall()

    results: List[SearchHit] = []
    for row in rows:
        collection_name = str(row[1])
        metadata = row[3] if isinstance(row[3], dict) else {}
        payload = dict(metadata)
        payload["content"] = row[2]
        payload["id"] = payload.get("id", row[4] or row[0])
        payload["source_id"] = row[4]
        payload["chunk_db_id"] = row[0]
        payload["collection"] = collection_name
        if row[4]:
            payload["doc_id"] = f"{collection_name}::{row[4]}"
        else:
            payload["doc_id"] = f"{collection_name}::chunk:{row[0]}"
        payload["event_date"] = row[5].isoformat() if row[5] else payload.get("event_date")
        payload["start_date"] = row[6].isoformat() if row[6] else payload.get("start_date")
        payload["end_date"] = row[7].isoformat() if row[7] else payload.get("end_date")
        results.append(SearchHit(id=row[0], score=float(row[8]), payload=payload))
    return results


def search_doc_by_entities(
    client: PGVectorClient,
    query: str,
    entity_ids: List[str],
    k: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    metadata_filters: Optional[Dict[str, Any]] = None,
) -> List[SearchHit]:
    return search_doc(
        client=client,
        query=query,
        col_name=None,
        k=k,
        start_date=start_date,
        end_date=end_date,
        entity_ids=entity_ids,
        metadata_filters=metadata_filters,
    )


def fetch_full_doc_by_source(
    client: PGVectorClient,
    col_name: str,
    source_id: str,
    max_chunks: int = 600,
) -> Optional[Dict[str, Any]]:
    table = _safe_ident(PGVECTOR_TABLE)
    with client.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, chunk_index, content, metadata, event_date, start_date, end_date
                FROM {table}
                WHERE collection = %s AND source_id = %s
                ORDER BY chunk_index ASC
                LIMIT %s;
                """,
                (col_name, str(source_id), int(max_chunks)),
            )
            rows = cur.fetchall()

    if not rows:
        return None

    first_meta = rows[0][3] if isinstance(rows[0][3], dict) else {}
    metadata = dict(first_meta)
    metadata["event_date"] = rows[0][4].isoformat() if rows[0][4] else metadata.get("event_date")
    metadata["start_date"] = rows[0][5].isoformat() if rows[0][5] else metadata.get("start_date")
    metadata["end_date"] = rows[0][6].isoformat() if rows[0][6] else metadata.get("end_date")

    full_content = "\n".join((row[2] or "") for row in rows if row[2]).strip()
    return {
        "doc_id": f"{col_name}::{source_id}",
        "collection": col_name,
        "source_id": str(source_id),
        "chunk_ids": [int(row[0]) for row in rows],
        "chunk_count": len(rows),
        "full_content": full_content,
        "metadata": metadata,
    }


def fetch_full_doc_by_chunk_id(
    client: PGVectorClient,
    chunk_id: int,
) -> Optional[Dict[str, Any]]:
    table = _safe_ident(PGVECTOR_TABLE)
    with client.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, collection, source_id, chunk_index, content, metadata, event_date, start_date, end_date
                FROM {table}
                WHERE id = %s
                LIMIT 1;
                """,
                (int(chunk_id),),
            )
            row = cur.fetchone()

    if not row:
        return None

    source_id = row[2]
    if source_id:
        return fetch_full_doc_by_source(client, col_name=row[1], source_id=str(source_id))

    metadata = row[5] if isinstance(row[5], dict) else {}
    payload = dict(metadata)
    payload["event_date"] = row[6].isoformat() if row[6] else payload.get("event_date")
    payload["start_date"] = row[7].isoformat() if row[7] else payload.get("start_date")
    payload["end_date"] = row[8].isoformat() if row[8] else payload.get("end_date")

    return {
        "doc_id": f"{row[1]}::chunk:{row[0]}",
        "collection": row[1],
        "source_id": None,
        "chunk_ids": [int(row[0])],
        "chunk_count": 1,
        "full_content": row[4] or "",
        "metadata": payload,
    }


def upsert_folder(client: PGVectorClient, folder_path: str, col_name: str, n: int = 0) -> None:
    if not os.path.exists(folder_path):
        print(f"Error: Folder path {folder_path} does not exist")
        return

    json_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
    if not json_files:
        print(f"Warning: No JSON files found in {folder_path}")
        return

    limit = n if n > 0 else len(json_files)
    for idx, filename in enumerate(json_files[:limit], start=1):
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "id" not in data:
                data["id"] = os.path.splitext(filename)[0]
            create_doc_upsert(client, col_name, data)
            print(f"Uploaded {idx}/{limit}: {filename} -> {col_name}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")
