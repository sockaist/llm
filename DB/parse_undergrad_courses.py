#!/usr/bin/env python3
"""Parse KAIST SoC courses HTML and generate:
1) undergrad SQL seed script
2) per-course JSON files under llm/data/courses/CS/<course_code>/course.json
3) per-course entity.md summary files

Source of truth for parsing fields is `llm/data/raw/courses.html`.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


SCRIPT_DIR = Path(__file__).resolve().parent
LLM_ROOT = SCRIPT_DIR.parent
DEFAULT_HTML_PATH = LLM_ROOT / "data" / "raw" / "courses.html"
DEFAULT_SQL_PATH = SCRIPT_DIR / "seed_undergrad_courses.sql"
DEFAULT_DATA_ROOT = LLM_ROOT / "data"
DEFAULT_COURSE_ROOT = DEFAULT_DATA_ROOT / "courses" / "CS"

CATEGORY_TO_TYPE = {
    "기초필수": "BASIC_REQUIRED",
    "기초선택": "BASIC_ELECTIVE",
    "전공필수": "MAJOR_REQUIRED",
    "전공선택": "MAJOR_ELECTIVE",
    "공통필수": "COMMON_REQUIRED",
    "필수선택": "REQUIRED_ELECTIVE",
    "일반선택": "GENERAL_ELECTIVE",
    "연구": "RESEARCH",
}


@dataclass(frozen=True)
class CourseRecord:
    course_num: str
    course_name: str
    category: str
    prerequisite: str
    class_hours_raw: str
    lecture_hours: Optional[int]
    lab_hours: Optional[int]
    credits: int
    division_raw: str
    division: str
    semester_raw: str
    semester: str
    exp: str


def clean_text(raw: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_semester(raw: str) -> str:
    v = clean_text(raw)
    lv = v.lower()

    has_spring = ("봄" in v) or ("spring" in lv)
    has_fall = ("가을" in v) or ("fall" in lv) or ("autumn" in lv)

    if has_spring and has_fall:
        return "A"
    if has_spring:
        return "S"
    if has_fall:
        return "F"
    raise ValueError(f"Cannot map semester from value: {v!r}")


def parse_class_hours(raw: str) -> tuple[Optional[int], Optional[int], int]:
    v = clean_text(raw)
    m = re.match(r"^\s*(\d+)\s*:\s*(\d+)\s*:\s*(\d+)(?:\s*\([^)]*\))?\s*$", v)
    if m:
        lecture = int(m.group(1))
        lab = int(m.group(2))
        credits = int(m.group(3))
        return lecture, lab, credits

    nums = re.findall(r"\d+", v)
    if nums:
        credits = int(nums[-1])
        return None, None, credits
    raise ValueError(f"Cannot parse class hours from value: {v!r}")


def parse_division(raw: str) -> str:
    v = clean_text(raw).lower()
    if "학부" in v or "bachelor" in v:
        return "bachelor"
    if "대학원" in v or "graduate" in v:
        return "graduate"
    raise ValueError(f"Cannot map division from value: {v!r}")


def sql_literal(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def extract_field(block: str, label: str) -> Optional[str]:
    pattern = re.compile(
        rf"{re.escape(label)}</td>\s*<td[^>]*>(.*?)</td>",
        flags=re.DOTALL | re.IGNORECASE,
    )
    m = pattern.search(block)
    if not m:
        return None
    return clean_text(m.group(1))


def parse_courses(html_text: str) -> list[CourseRecord]:
    in_tables = re.findall(
        r'<tr\s+class="inTable"[^>]*>.*?<table>(.*?)</table>.*?</tr>',
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    records: list[CourseRecord] = []
    for block in in_tables:
        course_name = extract_field(block, "과목명")
        course_num = extract_field(block, "과목코드")
        category = extract_field(block, "과목분류")
        prerequisite = extract_field(block, "선수과목") or ""
        class_hours_raw = extract_field(block, "강:실:학(숙)")
        division_raw = extract_field(block, "과정")
        semester_raw = extract_field(block, "개설학기")
        exp = extract_field(block, "과목 설명")

        missing = []
        if not course_name:
            missing.append("과목명")
        if not course_num:
            missing.append("과목코드")
        if not category:
            missing.append("과목분류")
        if not class_hours_raw:
            missing.append("강:실:학(숙)")
        if not division_raw:
            missing.append("과정")
        if not semester_raw:
            missing.append("개설학기")
        if exp is None:
            missing.append("과목 설명")
        if missing:
            raise ValueError(f"Missing fields {missing} in a course block")

        if category not in CATEGORY_TO_TYPE:
            raise ValueError(f"Unknown category {category!r} for course {course_num}")

        lecture_hours, lab_hours, credits = parse_class_hours(class_hours_raw)

        records.append(
            CourseRecord(
                course_num=course_num,
                course_name=course_name,
                category=category,
                prerequisite=prerequisite,
                class_hours_raw=class_hours_raw,
                lecture_hours=lecture_hours,
                lab_hours=lab_hours,
                credits=credits,
                division_raw=division_raw,
                division=parse_division(division_raw),
                semester_raw=semester_raw,
                semester=parse_semester(semester_raw),
                exp=exp or "",
            )
        )

    # Deduplicate by course_num while preserving order.
    seen: set[str] = set()
    uniq: list[CourseRecord] = []
    for rec in records:
        if rec.course_num in seen:
            continue
        seen.add(rec.course_num)
        uniq.append(rec)

    return uniq


def build_sql(records: Iterable[CourseRecord], department_code: str) -> str:
    rows = list(records)
    if not rows:
        raise ValueError("No course rows parsed from HTML")

    type_names = sorted({CATEGORY_TO_TYPE[r.category] for r in rows})

    out: list[str] = []
    out.append("BEGIN;")
    out.append("")
    out.append("-- Ensure required course_types exist")
    out.append("DO $$")
    out.append("DECLARE")
    out.append("  v_type_id BIGINT;")
    out.append("BEGIN")
    for type_name in type_names:
        out.append(f"  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = {sql_literal(type_name)};")
        out.append("  IF v_type_id IS NULL THEN")
        out.append("    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;")
        out.append(f"    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, {sql_literal(type_name)});")
        out.append("  END IF;")
    out.append("END$$;")
    out.append("")

    for rec in rows:
        type_name = CATEGORY_TO_TYPE[rec.category]
        out.append(f"-- {rec.course_num} ({rec.category})")
        out.append("DO $$")
        out.append("DECLARE")
        out.append("  v_dept_id BIGINT;")
        out.append("  v_course_id BIGINT;")
        out.append("  v_type_id BIGINT;")
        out.append("BEGIN")
        out.append(
            f"  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = {sql_literal(department_code)};"
        )
        out.append("  IF v_dept_id IS NULL THEN")
        out.append(
            f"    RAISE EXCEPTION 'Department % not found in departments table', {sql_literal(department_code)};"
        )
        out.append("  END IF;")
        out.append(
            f"  SELECT node_id INTO v_course_id FROM courses WHERE course_num = {sql_literal(rec.course_num)};"
        )
        out.append("  IF v_course_id IS NULL THEN")
        out.append("    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;")
        out.append(
            "    INSERT INTO courses "
            "(node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) "
            "VALUES ("
            f"v_course_id, {sql_literal(rec.course_num)}, NULL, {sql_literal(rec.exp)}, {rec.credits}, "
            f"{sql_literal(rec.division)}, NULL, {sql_literal(rec.semester)}, v_dept_id);"
        )
        out.append("  ELSE")
        out.append(
            "    UPDATE courses SET "
            f"history = NULL, exp = {sql_literal(rec.exp)}, credits = {rec.credits}, "
            f"division = {sql_literal(rec.division)}, mutual = NULL, semester = {sql_literal(rec.semester)}, "
            "department_node_id = v_dept_id "
            "WHERE node_id = v_course_id;"
        )
        out.append("  END IF;")
        out.append(f"  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = {sql_literal(type_name)};")
        out.append("  IF v_type_id IS NULL THEN")
        out.append(f"    RAISE EXCEPTION 'course_type % not found', {sql_literal(type_name)};")
        out.append("  END IF;")
        out.append(
            "  IF NOT EXISTS ("
            "SELECT 1 FROM course_mappings "
            "WHERE course_node_id = v_course_id "
            "AND type_node_id = v_type_id "
            "AND valid_years = '[,]'::int4range"
            ") THEN"
        )
        out.append(
            "    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) "
            "VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);"
        )
        out.append("  END IF;")
        out.append("END$$;")
        out.append("")

    out.append("COMMIT;")
    out.append("")
    return "\n".join(out)


def to_course_json(record: CourseRecord, department_code: str, source_html: str) -> Dict[str, Any]:
    return {
        "entity_name": record.course_num,
        "course_num": record.course_num,
        "course_name": record.course_name,
        "department_code": department_code,
        "category": record.category,
        "course_type": CATEGORY_TO_TYPE.get(record.category),
        "prerequisite": record.prerequisite or None,
        "class_hours_raw": record.class_hours_raw,
        "lecture_hours": record.lecture_hours,
        "lab_hours": record.lab_hours,
        "credits": float(record.credits),
        "division_raw": record.division_raw,
        "division": record.division,
        "semester_raw": record.semester_raw,
        "semester": record.semester,
        "description": record.exp,
        "history": None,
        "exp": record.exp,
        "mutual": None,
        "source_kind": "undergraduate_html",
        "source_html": source_html,
    }


def build_entity_md(*, course_num: str, course_name: str, relative_path: str, category: Optional[str], semester_raw: Optional[str], credits: Optional[float], prerequisite: Optional[str]) -> str:
    summary_parts: list[str] = []
    if category:
        summary_parts.append(f"{category} 분류")
    if semester_raw:
        summary_parts.append(f"{semester_raw} 개설")
    if credits is not None:
        if float(credits).is_integer():
            summary_parts.append(f"{int(credits)}학점")
        else:
            summary_parts.append(f"{credits}학점")
    if prerequisite:
        summary_parts.append(f"선수과목 {prerequisite}")

    summary = ", ".join(summary_parts) if summary_parts else "기본 정보가 정리된"

    lines = [
        f"# Entity: {course_num}(과목코드)",
        f'- relative path: "{relative_path}"',
        f"- 이 엔티티는 전산학부의 수업 {course_name}({course_num}) 입니다. {summary} 과목입니다.",
        "",
    ]
    return "\n".join(lines)


def write_course_entities(
    records: Iterable[CourseRecord],
    *,
    course_root: Path,
    data_root: Path,
    department_code: str,
    source_html: Path,
) -> int:
    source_ref = (
        source_html.relative_to(data_root).as_posix()
        if source_html.is_relative_to(data_root)
        else source_html.as_posix()
    )

    written = 0
    for rec in records:
        course_dir = course_root / rec.course_num
        course_dir.mkdir(parents=True, exist_ok=True)

        payload = to_course_json(rec, department_code=department_code, source_html=source_ref)
        json_path = course_dir / "course.json"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        relative_path = (
            course_dir.relative_to(data_root).as_posix()
            if course_dir.is_relative_to(data_root)
            else course_dir.as_posix()
        )
        entity_md = build_entity_md(
            course_num=rec.course_num,
            course_name=rec.course_name,
            relative_path=relative_path,
            category=rec.category,
            semester_raw=rec.semester_raw,
            credits=float(rec.credits),
            prerequisite=rec.prerequisite or None,
        )
        (course_dir / "entity.md").write_text(entity_md, encoding="utf-8")
        written += 1

    return written


def refresh_entity_md_for_existing_courses(course_root: Path, data_root: Path) -> int:
    refreshed = 0
    for course_json in sorted(course_root.glob("*/course.json")):
        course_dir = course_json.parent
        course_code = course_dir.name
        payload = json.loads(course_json.read_text(encoding="utf-8"))

        course_name = str(payload.get("course_name") or payload.get("entity_name") or course_code)
        category = payload.get("category")
        semester_raw = payload.get("semester_raw") or payload.get("semester")
        credits_raw = payload.get("credits")
        prerequisite = payload.get("prerequisite")

        credits: Optional[float]
        if isinstance(credits_raw, (int, float)):
            credits = float(credits_raw)
        else:
            credits = None

        relative_path = (
            course_dir.relative_to(data_root).as_posix()
            if course_dir.is_relative_to(data_root)
            else course_dir.as_posix()
        )

        entity_md = build_entity_md(
            course_num=course_code,
            course_name=course_name,
            relative_path=relative_path,
            category=str(category) if category else None,
            semester_raw=str(semester_raw) if semester_raw else None,
            credits=credits,
            prerequisite=str(prerequisite) if prerequisite else None,
        )
        (course_dir / "entity.md").write_text(entity_md, encoding="utf-8")
        refreshed += 1

    return refreshed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse courses HTML and generate SQL + course entity JSON/MD files."
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML_PATH,
        help="Path to source courses HTML file",
    )
    parser.add_argument(
        "--out-sql",
        type=Path,
        default=DEFAULT_SQL_PATH,
        help="Output SQL file path",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Data root directory (default: llm/data)",
    )
    parser.add_argument(
        "--course-root",
        type=Path,
        default=DEFAULT_COURSE_ROOT,
        help="Course entity root directory (default: llm/data/courses/CS)",
    )
    parser.add_argument(
        "--department-code",
        default="CS",
        help="department_code value in departments table",
    )
    parser.add_argument(
        "--skip-sql",
        action="store_true",
        help="Skip SQL generation",
    )
    parser.add_argument(
        "--skip-json",
        action="store_true",
        help="Skip course.json + entity.md generation from HTML records",
    )
    parser.add_argument(
        "--refresh-all-entity-md",
        action="store_true",
        help="Also regenerate entity.md for all existing course folders under course-root",
    )
    args = parser.parse_args()

    html_path = args.html.resolve()
    out_sql_path = args.out_sql.resolve()
    data_root = args.data_root.resolve()
    course_root = args.course_root.resolve()

    html_text = html_path.read_text(encoding="utf-8")
    records = parse_courses(html_text)

    if not args.skip_sql:
        sql = build_sql(records, args.department_code)
        out_sql_path.parent.mkdir(parents=True, exist_ok=True)
        out_sql_path.write_text(sql, encoding="utf-8")

    json_written = 0
    if not args.skip_json:
        course_root.mkdir(parents=True, exist_ok=True)
        json_written = write_course_entities(
            records,
            course_root=course_root,
            data_root=data_root,
            department_code=args.department_code,
            source_html=html_path,
        )

    refreshed_md = 0
    if args.refresh_all_entity_md:
        course_root.mkdir(parents=True, exist_ok=True)
        refreshed_md = refresh_entity_md_for_existing_courses(course_root, data_root)

    print(f"Parsed {len(records)} courses from {html_path}")
    if not args.skip_sql:
        print(f"Wrote SQL to {out_sql_path}")
    if not args.skip_json:
        print(f"Wrote course.json + entity.md for {json_written} courses under {course_root}")
    if args.refresh_all_entity_md:
        print(f"Refreshed entity.md for all existing course folders: {refreshed_md}")


if __name__ == "__main__":
    main()
