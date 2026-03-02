#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


SCRIPT_DIR = Path(__file__).resolve().parent
LLM_ROOT = SCRIPT_DIR.parent
DEFAULT_DATA_ROOT = LLM_ROOT / "data"
DEFAULT_PROFS_ROOT = DEFAULT_DATA_ROOT / "csweb" / "profs"

RAW_PROF_JSON_RE = re.compile(r"^[0-9A-F]{8}\.json$")
ID_DIR_RE = re.compile(r"^[0-9A-F]{8}$")
INVALID_DIR_CHARS_RE = re.compile(r'[\\/:*?"<>|]+')
MULTI_SPACE_RE = re.compile(r"\s+")


def iter_raw_prof_json_files(profs_root: Path) -> Iterable[Path]:
    for path in sorted(profs_root.iterdir()):
        if not path.is_file():
            continue
        if not RAW_PROF_JSON_RE.match(path.name):
            continue
        yield path


def iter_prof_entity_dirs(profs_root: Path) -> Iterable[Path]:
    for path in sorted(profs_root.iterdir()):
        if not path.is_dir():
            continue
        if (path / "professor.json").exists():
            yield path


def load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def to_safe_dir_name(name: str) -> str:
    cleaned = clean_text(name)
    cleaned = INVALID_DIR_CHARS_RE.sub("_", cleaned)
    cleaned = MULTI_SPACE_RE.sub(" ", cleaned).strip()
    cleaned = cleaned.rstrip(".")
    return cleaned or "unknown_professor"


def unique_dir_name(profs_root: Path, preferred_name: str, prof_code: str, ignore_path: Path | None = None) -> str:
    if ignore_path is not None and ignore_path.name == preferred_name:
        return preferred_name

    candidate = preferred_name
    if not (profs_root / candidate).exists():
        return candidate

    # Name collision fallback. Keep professor code for uniqueness.
    candidate = f"{preferred_name}_{prof_code}"
    if ignore_path is not None and ignore_path.name == candidate:
        return candidate
    if not (profs_root / candidate).exists():
        return candidate

    idx = 2
    while True:
        candidate = f"{preferred_name}_{prof_code}_{idx}"
        if ignore_path is not None and ignore_path.name == candidate:
            return candidate
        if not (profs_root / candidate).exists():
            return candidate
        idx += 1


def build_entity_md(
    *,
    professor_name: str,
    relative_path: str,
    field: str,
    major: str,
) -> str:
    summary_bits: List[str] = []
    if field:
        summary_bits.append(f"연구분야: {field}")
    if major:
        summary_bits.append(f"세부전공: {major}")

    summary_tail = " ".join(summary_bits) if summary_bits else "교수 소개와 연구 정보를 포함합니다."

    lines = [
        f"# Entity: {professor_name}(교수)",
        f'- relative path: "{relative_path}"',
        f"- 이 엔티티는 전산학부 교수 {professor_name}님의 연구 및 프로필 정보를 담고 있습니다. {summary_tail}",
        "",
    ]
    return "\n".join(lines)


def write_prof_entity_files(
    *,
    entity_dir: Path,
    payload: Dict[str, Any],
    data_root: Path,
) -> None:
    dst_json = entity_dir / "professor.json"
    dst_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    professor_name = clean_text(payload.get("name")) or entity_dir.name
    field = clean_text(payload.get("field"))
    major = clean_text(payload.get("major"))
    relative_path = (
        entity_dir.relative_to(data_root).as_posix()
        if entity_dir.is_relative_to(data_root)
        else entity_dir.as_posix()
    )
    entity_md = build_entity_md(
        professor_name=professor_name,
        relative_path=relative_path,
        field=field,
        major=major,
    )
    (entity_dir / "entity.md").write_text(entity_md, encoding="utf-8")


def entityize_raw_professor_files(*, profs_root: Path, data_root: Path) -> int:
    converted = 0
    for src_json in iter_raw_prof_json_files(profs_root):
        payload = load_json(src_json)
        prof_code = src_json.stem
        preferred_name = to_safe_dir_name(clean_text(payload.get("name")) or prof_code)
        dir_name = unique_dir_name(profs_root, preferred_name, prof_code)

        entity_dir = profs_root / dir_name
        entity_dir.mkdir(parents=True, exist_ok=True)
        write_prof_entity_files(entity_dir=entity_dir, payload=payload, data_root=data_root)

        src_json.unlink()
        converted += 1

    return converted


def rename_existing_entity_dirs_to_name(*, profs_root: Path) -> int:
    renamed = 0
    # Sort deterministic: ID-style first to avoid unnecessary collisions.
    dirs = sorted(
        iter_prof_entity_dirs(profs_root),
        key=lambda p: (0 if ID_DIR_RE.match(p.name) else 1, p.name),
    )

    for src_dir in dirs:
        payload = load_json(src_dir / "professor.json")
        prof_code = clean_text(payload.get("id")) or src_dir.name
        preferred_name = to_safe_dir_name(clean_text(payload.get("name")) or src_dir.name)
        target_name = unique_dir_name(profs_root, preferred_name, str(prof_code), ignore_path=src_dir)
        if src_dir.name == target_name:
            continue
        src_dir.rename(profs_root / target_name)
        renamed += 1

    return renamed


def refresh_all_entity_md(*, profs_root: Path, data_root: Path) -> int:
    refreshed = 0
    for entity_dir in iter_prof_entity_dirs(profs_root):
        payload = load_json(entity_dir / "professor.json")
        write_prof_entity_files(entity_dir=entity_dir, payload=payload, data_root=data_root)
        refreshed += 1
    return refreshed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert llm/data/csweb/profs/*.json into folder-based professor entities "
            "and normalize folder names to professor names."
        ),
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Data root (default: llm/data)",
    )
    parser.add_argument(
        "--profs-root",
        type=Path,
        default=DEFAULT_PROFS_ROOT,
        help="Professor root (default: llm/data/csweb/profs)",
    )
    parser.add_argument(
        "--skip-raw-convert",
        action="store_true",
        help="Skip converting root-level raw JSON files",
    )
    parser.add_argument(
        "--skip-rename-by-name",
        action="store_true",
        help="Skip renaming existing entity folders to professor names",
    )
    parser.add_argument(
        "--skip-refresh-md",
        action="store_true",
        help="Skip regenerating entity.md and professor.json formatting",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_root = args.data_root.resolve()
    profs_root = args.profs_root.resolve()

    if not data_root.exists():
        raise FileNotFoundError(f"Data root not found: {data_root}")
    if not profs_root.exists():
        raise FileNotFoundError(f"Professor root not found: {profs_root}")

    converted = 0
    renamed = 0
    refreshed = 0

    if not args.skip_raw_convert:
        converted = entityize_raw_professor_files(
            profs_root=profs_root,
            data_root=data_root,
        )

    if not args.skip_rename_by_name:
        renamed = rename_existing_entity_dirs_to_name(profs_root=profs_root)

    if not args.skip_refresh_md:
        refreshed = refresh_all_entity_md(
            profs_root=profs_root,
            data_root=data_root,
        )

    print(f"Converted raw professor JSON files: {converted}")
    print(f"Renamed entity folders to professor names: {renamed}")
    print(f"Refreshed professor entity files: {refreshed}")
    print(f"Target root: {profs_root}")


if __name__ == "__main__":
    main()
