#!/usr/bin/env python3
"""Parse KAIST SoC undergraduate courses HTML and generate SQL seed script.

Rules implemented from user requirements:
- history: always NULL
- exp: filled with "과목 설명"
- division: filled with "과정"
- semester: 봄=S, 가을=F, both=A
- credits: use the last number from "강:실:학(숙)"
- mutual: omitted for Bachelor courses (stored as NULL)
- course_mappings: map from "과목분류"
"""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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
    category: str
    credits: int
    division: str
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
    has_spring = "봄" in v
    has_fall = "가을" in v
    if has_spring and has_fall:
        return "A"
    if has_spring:
        return "S"
    if has_fall:
        return "F"
    raise ValueError(f"Cannot map semester from value: {v!r}")


def parse_credits(raw: str) -> int:
    v = clean_text(raw)
    m = re.search(r"(\d+)\s*$", v)
    if not m:
        raise ValueError(f"Cannot parse credits from value: {v!r}")
    return int(m.group(1))


def parse_division(raw: str) -> str:
    v = clean_text(raw).lower()
    if "학부" in v or "bachelor" in v:
        return "bachelor"
    if "대학원" in v or "graduate" in v:
        return "graduate"
    raise ValueError(f"Cannot map division from value: {v!r}")


def sql_literal(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def parse_courses(html_text: str) -> list[CourseRecord]:
    in_tables = re.findall(
        r'<tr\s+class="inTable"[^>]*>.*?<table>(.*?)</table>.*?</tr>',
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    records: list[CourseRecord] = []
    for block in in_tables:
        # Pull key fields directly from each hidden detail table.
        course_num_m = re.search(r"과목코드</td>\s*<td[^>]*>(.*?)</td>", block, flags=re.DOTALL)
        category_m = re.search(r"과목분류</td>\s*<td[^>]*>(.*?)</td>", block, flags=re.DOTALL)
        credit_m = re.search(r"강:실:학\(숙\)</td>\s*<td[^>]*>(.*?)</td>", block, flags=re.DOTALL)
        division_m = re.search(r"과정</td>\s*<td[^>]*>(.*?)</td>", block, flags=re.DOTALL)
        semester_m = re.search(r"개설학기</td>\s*<td[^>]*>(.*?)</td>", block, flags=re.DOTALL)
        desc_m = re.search(r"과목 설명</td>\s*<td[^>]*>(.*?)</td>", block, flags=re.DOTALL)

        missing = []
        if not course_num_m:
            missing.append("과목코드")
        if not category_m:
            missing.append("과목분류")
        if not credit_m:
            missing.append("강:실:학(숙)")
        if not division_m:
            missing.append("과정")
        if not semester_m:
            missing.append("개설학기")
        if not desc_m:
            missing.append("과목 설명")
        if missing:
            raise ValueError(f"Missing fields {missing} in a course block")

        course_num = clean_text(course_num_m.group(1))
        category = clean_text(category_m.group(1))
        if category not in CATEGORY_TO_TYPE:
            raise ValueError(f"Unknown category {category!r} for course {course_num}")

        records.append(
            CourseRecord(
                course_num=course_num,
                category=category,
                credits=parse_credits(credit_m.group(1)),
                division=parse_division(division_m.group(1)),
                semester=parse_semester(semester_m.group(1)),
                exp=clean_text(desc_m.group(1)),
            )
        )

    # Deduplicate by course_num while preserving order.
    seen: set[str] = set()
    uniq: list[CourseRecord] = []
    for r in records:
        if r.course_num in seen:
            continue
        seen.add(r.course_num)
        uniq.append(r)

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
    for t in type_names:
        out.append(f"  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = {sql_literal(t)};")
        out.append("  IF v_type_id IS NULL THEN")
        out.append("    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;")
        out.append(f"    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, {sql_literal(t)});")
        out.append("  END IF;")
    out.append("END$$;")
    out.append("")

    for r in rows:
        type_name = CATEGORY_TO_TYPE[r.category]
        out.append(f"-- {r.course_num} ({r.category})")
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
        out.append(f"  SELECT node_id INTO v_course_id FROM courses WHERE course_num = {sql_literal(r.course_num)};")
        out.append("  IF v_course_id IS NULL THEN")
        out.append("    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;")
        out.append(
            "    INSERT INTO courses "
            "(node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) "
            "VALUES ("
            f"v_course_id, {sql_literal(r.course_num)}, NULL, {sql_literal(r.exp)}, {r.credits}, "
            f"{sql_literal(r.division)}, NULL, {sql_literal(r.semester)}, v_dept_id);"
        )
        out.append("  ELSE")
        out.append(
            "    UPDATE courses SET "
            f"history = NULL, exp = {sql_literal(r.exp)}, credits = {r.credits}, "
            f"division = {sql_literal(r.division)}, mutual = NULL, semester = {sql_literal(r.semester)}, "
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse courses HTML and generate SQL for courses/course_mappings."
    )
    parser.add_argument(
        "--html",
        default="llm/data/raw/courses.html",
        help="Path to source courses HTML file",
    )
    parser.add_argument(
        "--out",
        default="llm/DB/seed_undergrad_courses.sql",
        help="Output SQL file path",
    )
    parser.add_argument(
        "--department-code",
        default="CS",
        help="department_code value in departments table",
    )
    args = parser.parse_args()

    html_path = Path(args.html)
    out_path = Path(args.out)

    html_text = html_path.read_text(encoding="utf-8")
    records = parse_courses(html_text)
    sql = build_sql(records, args.department_code)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(sql, encoding="utf-8")

    print(f"Parsed {len(records)} courses from {html_path}")
    print(f"Wrote SQL to {out_path}")


if __name__ == "__main__":
    main()
