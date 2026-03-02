#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from backend.vector_db.config import PGVECTOR_TABLE  # noqa: E402
from backend.vector_db.vector_db_helper import (  # noqa: E402
    create_doc_upsert,
    ensure_schema,
    get_pgvector_client,
)


GENERATED_DOC_NAMES = {"ontology.md", "level0.md", "entity.md", "entity.json"}
TEXT_EXTENSIONS = {
    ".json",
    ".txt",
    ".md",
    ".html",
    ".htm",
    ".csv",
    ".yaml",
    ".yml",
    ".xml",
}


def safe_ident(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def iter_files(data_root: Path) -> Iterable[Path]:
    for path in sorted(data_root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.name in GENERATED_DOC_NAMES:
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        yield path


def collection_name_for_file(data_root: Path, file_path: Path) -> str:
    rel_dir = file_path.parent.relative_to(data_root).as_posix()
    if rel_dir == ".":
        return "root"
    return rel_dir.replace("/", ".")


def collect_text_fragments(value: Any, out: List[str]) -> None:
    if isinstance(value, str):
        text = value.strip()
        if text:
            out.append(text)
        return
    if isinstance(value, list):
        for item in value:
            collect_text_fragments(item, out)
        return
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key) in {"content", "contents", "etc", "conent"}:
                continue
            collect_text_fragments(nested, out)


def dedupe_keep_order(items: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for item in items:
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def has_searchable_body(data: Dict[str, Any]) -> bool:
    for key in ("content", "contents", "etc"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


def backfill_content_if_missing(data: Dict[str, Any]) -> bool:
    if has_searchable_body(data):
        return True
    fragments: List[str] = []
    collect_text_fragments(data, fragments)
    merged = "\n".join(dedupe_keep_order(fragments)).strip()
    if not merged:
        return False
    data["content"] = merged
    return True


def load_file_payload(file_path: Path) -> Dict[str, Any]:
    if file_path.suffix.lower() == ".json":
        parsed = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(parsed, dict):
            return dict(parsed)
        return {"content": json.dumps(parsed, ensure_ascii=False)}
    text = file_path.read_text(encoding="utf-8", errors="replace").strip()
    return {"content": text}


def build_dsn() -> str:
    dsn = os.environ.get("POSTGRES_DSN") or os.environ.get("DATABASE_URL")
    if dsn:
        return dsn
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "postgres")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    return f"host={host} port={port} dbname={db} user={user} password={password}"


def fetch_entity_map(dsn: str) -> Dict[str, int]:
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT relative_path, entity_id FROM ontology_entities;")
            rows = cur.fetchall()
    return {str(row[0]): int(row[1]) for row in rows}


def fetch_existing_source_paths(dsn: str) -> Set[str]:
    table = safe_ident(PGVECTOR_TABLE)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT DISTINCT source_id
                FROM {table}
                WHERE source_id IS NOT NULL
                  AND source_id LIKE '%%/%%';
                """
            )
            rows = cur.fetchall()
    return {str(row[0]) for row in rows if row and row[0]}


def delete_stale_source_paths(dsn: str, stale_paths: List[str], batch_size: int = 1000) -> int:
    if not stale_paths:
        return 0
    table = safe_ident(PGVECTOR_TABLE)
    deleted = 0
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            for i in range(0, len(stale_paths), batch_size):
                batch = stale_paths[i : i + batch_size]
                cur.execute(
                    f"DELETE FROM {table} WHERE source_id = ANY(%s);",
                    (batch,),
                )
                deleted += cur.rowcount or 0
        conn.commit()
    return deleted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upsert vectors from llm/data using folder hierarchy metadata "
            "(entity_id/source_path)."
        ),
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=PROJECT_ROOT / "data",
        help="Data root (default: llm/data)",
    )
    parser.add_argument(
        "--no-cleanup-stale",
        action="store_true",
        help="Do not delete stale source_id rows that are no longer present in data root",
    )
    parser.add_argument(
        "--force-reembed-all",
        action="store_true",
        help="Re-embed all files even when source_path already exists in documents",
    )
    parser.add_argument(
        "--limit-files",
        type=int,
        default=None,
        help="Optional processing limit for smoke runs",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    args = parse_args()

    data_root = args.data_root.resolve()
    if not data_root.exists():
        raise FileNotFoundError(f"Data root not found: {data_root}")

    dsn = build_dsn()
    entity_map = fetch_entity_map(dsn)
    if "." not in entity_map:
        raise RuntimeError("ontology_entities has no root ('.'). Run ./DB/rebuild.sh first.")

    desired_files_all: List[Tuple[Path, str, str, int]] = []
    skipped_no_entity = 0
    for file_path in iter_files(data_root):
        rel_file = file_path.relative_to(data_root).as_posix()
        rel_dir = file_path.parent.relative_to(data_root).as_posix()
        rel_dir_key = "." if rel_dir == "." else rel_dir
        entity_id = entity_map.get(rel_dir_key)
        if entity_id is None:
            skipped_no_entity += 1
            continue
        collection = collection_name_for_file(data_root, file_path)
        desired_files_all.append((file_path, rel_file, collection, entity_id))

    desired_source_paths = {item[1] for item in desired_files_all}
    existing_source_paths = fetch_existing_source_paths(dsn)

    stale_paths = sorted(existing_source_paths - desired_source_paths)
    if stale_paths and not args.no_cleanup_stale:
        deleted_rows = delete_stale_source_paths(dsn, stale_paths)
    else:
        deleted_rows = 0

    if args.force_reembed_all:
        target_files = list(desired_files_all)
    else:
        target_files = [item for item in desired_files_all if item[1] not in existing_source_paths]

    if args.limit_files is not None:
        target_files = target_files[: max(0, int(args.limit_files))]

    client = get_pgvector_client()
    ensure_schema(client)

    print(f"data_root: {data_root}")
    print(f"files_discovered: {len(desired_files_all)}")
    print(f"files_skipped_no_entity: {skipped_no_entity}")
    print(f"existing_source_paths: {len(existing_source_paths)}")
    print(f"stale_source_paths: {len(stale_paths)}")
    print(f"stale_rows_deleted: {deleted_rows}")
    print(f"files_to_upsert: {len(target_files)}")

    processed = 0
    skipped_no_body = 0
    failed = 0

    for file_path, rel_file, collection, entity_id in target_files:
        try:
            payload = load_file_payload(file_path)
            if not backfill_content_if_missing(payload):
                skipped_no_body += 1
                continue

            payload["entity_id"] = str(entity_id)
            payload["source_path"] = rel_file
            payload["collection"] = collection
            payload["file_name"] = file_path.name

            create_doc_upsert(client, collection, payload)
            processed += 1
            if processed % 50 == 0:
                print(f"upserted_files: {processed}/{len(target_files)}")
        except Exception as e:
            failed += 1
            print(f"[ERROR] upsert failed: {rel_file} ({e})")

    print("done")
    print(f"processed: {processed}")
    print(f"skipped_no_body: {skipped_no_body}")
    print(f"failed: {failed}")


if __name__ == "__main__":
    main()
