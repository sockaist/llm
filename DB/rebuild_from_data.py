#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data"
GENERATED_DOC_NAMES = {"ontology.md", "level0.md", "entity.md", "entity.json"}


@dataclass
class Config:
    dsn: str
    data_root: Path
    reset: bool


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


def iter_directories(data_root: Path) -> Iterable[Path]:
    yield data_root
    for path in sorted(data_root.rglob("*")):
        if path.is_dir():
            yield path


def sort_directories(data_root: Path, directories: Iterable[Path]) -> List[Path]:
    return sorted(
        directories,
        key=lambda p: (
            0 if p == data_root else len(p.relative_to(data_root).parts),
            p.relative_to(data_root).as_posix(),
        ),
    )


def relative_key(data_root: Path, directory: Path) -> str:
    rel = directory.relative_to(data_root).as_posix()
    return "." if rel == "." else rel


def parent_relative_key(rel_key: str) -> Optional[str]:
    if rel_key == ".":
        return None
    if "/" not in rel_key:
        return "."
    return rel_key.rsplit("/", 1)[0]


def count_direct_documents(directory: Path) -> int:
    count = 0
    for child in directory.iterdir():
        if not child.is_file():
            continue
        if child.name.startswith("."):
            continue
        if child.name in GENERATED_DOC_NAMES:
            continue
        count += 1
    return count


def iter_json_documents_for_backfill(data_root: Path) -> Iterable[Path]:
    for path in sorted(data_root.rglob("*.json")):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.name in GENERATED_DOC_NAMES:
            continue
        yield path


def has_nonempty_content_fields(payload: Dict[str, Any]) -> bool:
    for key in ("content", "contents", "etc"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return False


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
    seen = set()
    out: List[str] = []
    for item in items:
        text = item.strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def backfill_missing_content_fields(data_root: Path) -> tuple[int, int, int]:
    scanned = 0
    updated = 0
    invalid = 0

    for path in iter_json_documents_for_backfill(data_root):
        scanned += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            invalid += 1
            continue

        if not isinstance(payload, dict):
            invalid += 1
            continue

        if has_nonempty_content_fields(payload):
            continue

        fragments: List[str] = []
        collect_text_fragments(payload, fragments)
        merged = "\n".join(dedupe_keep_order(fragments)).strip()
        if not merged:
            continue

        payload["content"] = merged
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        updated += 1

    return scanned, updated, invalid


def ensure_hierarchy_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ontology_entities (
              entity_id BIGSERIAL PRIMARY KEY,
              name TEXT NOT NULL,
              relative_path TEXT NOT NULL UNIQUE,
              parent_entity_id BIGINT REFERENCES ontology_entities(entity_id) ON DELETE CASCADE,
              depth INT NOT NULL CHECK (depth >= 0),
              created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
              updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS ontology_entities_parent_idx ON ontology_entities(parent_entity_id);"
        )
    conn.commit()


def reset_hierarchy_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE ontology_entities RESTART IDENTITY CASCADE;")
    conn.commit()


def upsert_entity(
    conn: psycopg.Connection,
    *,
    name: str,
    relative_path: str,
    parent_entity_id: Optional[int],
    depth: int,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ontology_entities
              (name, relative_path, parent_entity_id, depth, updated_at)
            VALUES
              (%s, %s, %s, %s, NOW())
            ON CONFLICT (relative_path)
            DO UPDATE SET
              name = EXCLUDED.name,
              parent_entity_id = EXCLUDED.parent_entity_id,
              depth = EXCLUDED.depth,
              updated_at = NOW()
            RETURNING entity_id;
            """,
            (name, relative_path, parent_entity_id, depth),
        )
        row = cur.fetchone()
    conn.commit()
    return int(row[0])


def delete_stale_entities(conn: psycopg.Connection, valid_relative_paths: List[str]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM ontology_entities
            WHERE NOT (relative_path = ANY(%s));
            """,
            (valid_relative_paths,),
        )
    conn.commit()


def build_children_map(entity_parents: Dict[str, Optional[str]]) -> Dict[str, List[str]]:
    children: Dict[str, List[str]] = {}
    for rel_path, parent_rel in entity_parents.items():
        if parent_rel is None:
            continue
        children.setdefault(parent_rel, []).append(rel_path)
    for rel_paths in children.values():
        rel_paths.sort()
    return children


def json_code_block(payload: Dict[str, object]) -> str:
    return "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```"


def write_ontology_markdown(
    *,
    data_root: Path,
    entity_ids: Dict[str, int],
    entity_names: Dict[str, str],
    entity_parents: Dict[str, Optional[str]],
    entity_depths: Dict[str, int],
    direct_doc_counts: Dict[str, int],
) -> Path:
    output_path = data_root / "ontology.md"
    children = build_children_map(entity_parents)

    ordered_rel_paths = sorted(entity_ids.keys(), key=lambda rel: (entity_depths[rel], rel))
    entities_payload = []
    for rel in ordered_rel_paths:
        parent_rel = entity_parents[rel]
        entities_payload.append(
            {
                "entity_id": entity_ids[rel],
                "name": entity_names[rel],
                "relative_path": rel,
                "parent_entity_id": entity_ids[parent_rel] if parent_rel is not None else None,
                "depth": entity_depths[rel],
                "direct_doc_count": direct_doc_counts.get(rel, 0),
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root_path": data_root.as_posix(),
        "entity_count": len(entity_ids),
        "entities": entities_payload,
    }

    lines: List[str] = []
    lines.append("# Ontology")
    lines.append("")
    lines.append("Generated by `llm/DB/rebuild_from_data.py`.")
    lines.append("")
    lines.append("## JSON")
    lines.append(json_code_block(payload))
    lines.append("")
    lines.append("## Entity Tree")
    lines.append("")

    def render(rel: str, depth: int) -> None:
        indent = "  " * depth
        lines.append(
            f"{indent}- `{entity_names[rel]}` "
            f"(id={entity_ids[rel]}, path=`{rel}`, depth={entity_depths[rel]}, direct_docs={direct_doc_counts.get(rel, 0)})"
        )
        for child_rel in children.get(rel, []):
            render(child_rel, depth + 1)

    if "." in entity_ids:
        render(".", 0)
    else:
        for rel in ordered_rel_paths:
            if entity_parents[rel] is None:
                render(rel, 0)

    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def entity_dir(data_root: Path, relative_path: str) -> Path:
    if relative_path == ".":
        return data_root
    return data_root / relative_path


def entity_md_relative_path(relative_path: str) -> str:
    if relative_path == ".":
        return "entity.md"
    return f"{relative_path}/entity.md"


def entity_json_relative_path(relative_path: str) -> str:
    if relative_path == ".":
        return "entity.json"
    return f"{relative_path}/entity.json"


def read_entity_md_description(md_path: Path) -> str:
    if not md_path.exists():
        return ""
    text = md_path.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    lines = text.splitlines()
    if lines and lines[0].lstrip().startswith("#"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def write_entity_json_files(
    *,
    data_root: Path,
    entity_ids: Dict[str, int],
    entity_names: Dict[str, str],
    entity_parents: Dict[str, Optional[str]],
    entity_depths: Dict[str, int],
    direct_doc_counts: Dict[str, int],
) -> List[Path]:
    children = build_children_map(entity_parents)
    written_paths: List[Path] = []
    ordered_rel_paths = sorted(entity_ids.keys(), key=lambda rel: (entity_depths[rel], rel))

    for rel_path in ordered_rel_paths:
        entity_id = entity_ids[rel_path]
        parent_rel = entity_parents.get(rel_path)
        parent_entity_id = entity_ids.get(parent_rel) if parent_rel is not None else None
        child_entities = [
            {"entity_id": entity_ids[child_rel], "name": entity_names[child_rel]}
            for child_rel in children.get(rel_path, [])
        ]
        md_path = entity_dir(data_root, rel_path) / "entity.md"
        description = read_entity_md_description(md_path)

        payload = {
            "entity_id": entity_id,
            "name": entity_names[rel_path],
            "relative_path": rel_path,
            "parent_entity_id": parent_entity_id,
            "child_entities": child_entities,
            "child_entity_ids": [item["entity_id"] for item in child_entities],
            "description": description,
            "relation_types": [],
            "doc_count": direct_doc_counts.get(rel_path, 0),
            "depth": entity_depths[rel_path],
            "entity_md_path": entity_md_relative_path(rel_path),
        }

        json_path = entity_dir(data_root, rel_path) / "entity.json"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written_paths.append(json_path)

    return written_paths


def write_level0_markdown(
    *,
    data_root: Path,
    entity_ids: Dict[str, int],
    entity_names: Dict[str, str],
    entity_parents: Dict[str, Optional[str]],
    entity_depths: Dict[str, int],
) -> Path:
    output_path = data_root / "level0.md"
    children = build_children_map(entity_parents)
    top_level_rel_paths = children.get(".", [])

    top_level_entities: List[Dict[str, Any]] = []
    for rel_path in top_level_rel_paths:
        entity_id = entity_ids[rel_path]
        md_path = entity_dir(data_root, rel_path) / "entity.md"
        description = read_entity_md_description(md_path)
        top_level_entities.append(
            {
                "entity_id": entity_id,
                "name": entity_names[rel_path],
                "relative_path": rel_path,
                "description": description,
            }
        )

    ordered_rel_paths = sorted(entity_ids.keys(), key=lambda rel: (entity_depths[rel], rel))
    entity_index = [
        {
            "entity_id": entity_ids[rel],
            "relative_path": rel,
            "entity_md_path": entity_md_relative_path(rel),
            "entity_json_path": entity_json_relative_path(rel),
        }
        for rel in ordered_rel_paths
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root_path": data_root.as_posix(),
        "top_level_entities": top_level_entities,
        "relation_types": [],
        "entity_index": entity_index,
    }

    lines: List[str] = []
    lines.append("# Level 0 Catalog")
    lines.append("")
    lines.append("Generated by `llm/DB/rebuild_from_data.py`.")
    lines.append("")
    lines.append("## Top-level Entities")
    if top_level_entities:
        for entity in top_level_entities:
            lines.append(f"- `{entity['name']}` (id={entity['entity_id']}, path=`{entity['relative_path']}`)")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Relation Types")
    lines.append("- (none)")
    lines.append("")
    lines.append("## JSON")
    lines.append(json_code_block(payload))
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def run(config: Config) -> None:
    with psycopg.connect(config.dsn) as conn:
        print("[1/4] Backfilling missing content fields in JSON docs")
        scanned, updated, invalid = backfill_missing_content_fields(config.data_root)
        print(f"      JSON scanned: {scanned}")
        print(f"      JSON updated: {updated}")
        print(f"      JSON invalid/skipped: {invalid}")

        print("[2/4] Ensuring hierarchy schema")
        ensure_hierarchy_schema(conn)
        if config.reset:
            print("      Reset ontology_entities")
            reset_hierarchy_table(conn)

        print("[3/4] Building parent-child hierarchy from folder structure")
        entity_ids: Dict[str, int] = {}
        entity_names: Dict[str, str] = {}
        entity_parents: Dict[str, Optional[str]] = {}
        entity_depths: Dict[str, int] = {}
        direct_doc_counts: Dict[str, int] = {}

        directories = sort_directories(config.data_root, iter_directories(config.data_root))
        for directory in directories:
            rel = relative_key(config.data_root, directory)
            parent_rel = parent_relative_key(rel)
            depth = 0 if rel == "." else rel.count("/") + 1
            name = config.data_root.name if rel == "." else directory.name
            parent_id = entity_ids.get(parent_rel) if parent_rel is not None else None

            entity_id = upsert_entity(
                conn,
                name=name,
                relative_path=rel,
                parent_entity_id=parent_id,
                depth=depth,
            )
            entity_ids[rel] = entity_id
            entity_names[rel] = name
            entity_parents[rel] = parent_rel
            entity_depths[rel] = depth
            direct_doc_counts[rel] = count_direct_documents(directory)

        if config.reset:
            delete_stale_entities(conn, sorted(entity_ids.keys()))

        print(f"      Entities upserted: {len(entity_ids)}")

        print("[4/4] Writing ontology metadata files")
        entity_json_paths = write_entity_json_files(
            data_root=config.data_root,
            entity_ids=entity_ids,
            entity_names=entity_names,
            entity_parents=entity_parents,
            entity_depths=entity_depths,
            direct_doc_counts=direct_doc_counts,
        )
        ontology_path = write_ontology_markdown(
            data_root=config.data_root,
            entity_ids=entity_ids,
            entity_names=entity_names,
            entity_parents=entity_parents,
            entity_depths=entity_depths,
            direct_doc_counts=direct_doc_counts,
        )
        level0_path = write_level0_markdown(
            data_root=config.data_root,
            entity_ids=entity_ids,
            entity_names=entity_names,
            entity_parents=entity_parents,
            entity_depths=entity_depths,
        )
        print(f"      entity.json written: {len(entity_json_paths)}")
        print(f"      ontology.md written: {ontology_path}")
        print(f"      level0.md written: {level0_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build parent-child ontology hierarchy from llm/data into RDB + ontology.md",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Root folder for ontology source (default: llm/data)",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not truncate ontology_entities before rebuild",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    args = parse_args()
    data_root = args.data_root.resolve()
    if not data_root.exists():
        raise FileNotFoundError(f"Data root not found: {data_root}")

    config = Config(
        dsn=build_dsn(),
        data_root=data_root,
        reset=not args.no_reset,
    )
    run(config)


if __name__ == "__main__":
    main()
