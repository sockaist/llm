#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = PROJECT_ROOT / "data"
DEFAULT_OUTPUT_ROOT = DEFAULT_DATA_ROOT / "courses" / "CS"
DEFAULT_SEED_FILES = [
    Path(__file__).resolve().with_name("seed_undergrad_courses.sql"),
    Path(__file__).resolve().with_name("seed_graduate_courses.sql"),
]

DO_BLOCK_RE = re.compile(r"DO\s+\$\$(?P<body>.*?)END\$\$;", re.IGNORECASE | re.DOTALL)
INSERT_COURSE_RE = re.compile(
    r"""
    INSERT\s+INTO\s+courses
    \s*\(
      \s*node_id\s*,\s*course_num\s*,\s*history\s*,\s*exp\s*,\s*credits\s*,\s*division\s*,\s*mutual\s*,\s*semester\s*,\s*department_node_id\s*
    \)
    \s*VALUES\s*\(
      \s*v_course_id\s*,(?P<values>.*?)\s*,\s*v_dept_id\s*
    \)\s*;
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)
COURSE_TYPE_RE = re.compile(
    r"SELECT\s+node_id\s+INTO\s+v_type_id\s+FROM\s+course_types\s+WHERE\s+type_name\s*=\s*'(?P<type>[^']+)';",
    re.IGNORECASE,
)


@dataclass
class CourseRecord:
    course_num: str
    history: Optional[str]
    exp: Optional[str]
    credits: Optional[float]
    division: Optional[str]
    mutual: Optional[str]
    semester: Optional[str]
    course_type: Optional[str]
    source_sql: str
    source_kind: str

    def to_json(self, department_code: str) -> Dict[str, Any]:
        return {
            "entity_name": self.course_num,
            "course_num": self.course_num,
            "department_code": department_code,
            "history": self.history,
            "exp": self.exp,
            "credits": self.credits,
            "division": self.division,
            "mutual": self.mutual,
            "semester": self.semester,
            "course_type": self.course_type,
            "source_sql": self.source_sql,
            "source_kind": self.source_kind,
        }


def parse_sql_literal(token: str) -> Any:
    value = token.strip()
    if value.upper() == "NULL":
        return None
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        return value[1:-1].replace("''", "'")
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value


def split_sql_values(values_text: str) -> List[str]:
    items: List[str] = []
    current: List[str] = []
    in_quote = False
    i = 0

    while i < len(values_text):
        ch = values_text[i]
        if in_quote:
            current.append(ch)
            if ch == "'":
                if i + 1 < len(values_text) and values_text[i + 1] == "'":
                    current.append(values_text[i + 1])
                    i += 2
                    continue
                in_quote = False
            i += 1
            continue

        if ch == "'":
            in_quote = True
            current.append(ch)
            i += 1
            continue
        if ch == ",":
            items.append("".join(current).strip())
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1

    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return items


def source_kind_for_path(path: Path) -> str:
    lower = path.name.lower()
    if "undergrad" in lower:
        return "undergraduate"
    if "graduate" in lower:
        return "graduate"
    return "unknown"


def parse_courses_from_sql(sql_path: Path) -> List[CourseRecord]:
    sql_text = sql_path.read_text(encoding="utf-8")
    source_kind = source_kind_for_path(sql_path)
    records: List[CourseRecord] = []

    for block_match in DO_BLOCK_RE.finditer(sql_text):
        block = block_match.group("body")
        insert_match = INSERT_COURSE_RE.search(block)
        if not insert_match:
            continue

        values = split_sql_values(insert_match.group("values"))
        if len(values) != 7:
            continue

        course_num = parse_sql_literal(values[0])
        if not isinstance(course_num, str) or not course_num.strip():
            continue

        history = parse_sql_literal(values[1])
        exp = parse_sql_literal(values[2])
        credits_raw = parse_sql_literal(values[3])
        division = parse_sql_literal(values[4])
        mutual = parse_sql_literal(values[5])
        semester = parse_sql_literal(values[6])

        course_type_match = COURSE_TYPE_RE.search(block)
        course_type = course_type_match.group("type") if course_type_match else None

        credits: Optional[float]
        if isinstance(credits_raw, int):
            credits = float(credits_raw)
        elif isinstance(credits_raw, float):
            credits = credits_raw
        else:
            credits = None

        records.append(
            CourseRecord(
                course_num=course_num,
                history=history if isinstance(history, str) or history is None else str(history),
                exp=exp if isinstance(exp, str) or exp is None else str(exp),
                credits=credits,
                division=division if isinstance(division, str) or division is None else str(division),
                mutual=mutual if isinstance(mutual, str) or mutual is None else str(mutual),
                semester=semester if isinstance(semester, str) or semester is None else str(semester),
                course_type=course_type,
                source_sql=sql_path.name,
                source_kind=source_kind,
            )
        )

    return records


def iter_existing_seed_files(seed_files: Iterable[Path]) -> Iterable[Path]:
    for path in seed_files:
        if path.exists():
            yield path
        else:
            print(f"[WARN] seed file not found, skip: {path}")


def write_course_jsons(
    *,
    courses: Dict[str, CourseRecord],
    output_root: Path,
    department_code: str,
) -> int:
    output_root.mkdir(parents=True, exist_ok=True)
    written = 0
    for course_num in sorted(courses.keys()):
        record = courses[course_num]
        course_dir = output_root / course_num
        course_dir.mkdir(parents=True, exist_ok=True)
        output_path = course_dir / "course.json"
        output_path.write_text(
            json.dumps(record.to_json(department_code), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written += 1
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate course entities under llm/data/courses/CS from seed_*_courses.sql.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Data root (default: llm/data)",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Target root for generated course entity folders (default: llm/data/courses/CS)",
    )
    parser.add_argument(
        "--department-code",
        default="CS",
        help="Department code to include in course.json (default: CS)",
    )
    parser.add_argument(
        "--seed-sql",
        action="append",
        default=None,
        help="Seed SQL file path (can be repeated). Defaults to DB/seed_undergrad_courses.sql and DB/seed_graduate_courses.sql.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    data_root = args.data_root.resolve()
    if not data_root.exists():
        raise FileNotFoundError(f"Data root not found: {data_root}")

    output_root = args.output_root.resolve()
    seed_files = [Path(p).resolve() for p in args.seed_sql] if args.seed_sql else DEFAULT_SEED_FILES
    existing_seed_files = list(iter_existing_seed_files(seed_files))
    if not existing_seed_files:
        raise FileNotFoundError("No seed SQL files found for course entity generation.")

    courses: Dict[str, CourseRecord] = {}
    total_parsed = 0
    for sql_path in existing_seed_files:
        parsed = parse_courses_from_sql(sql_path)
        total_parsed += len(parsed)
        for record in parsed:
            # If duplicated course codes exist across files, the later file wins.
            courses[record.course_num] = record

    written_count = write_course_jsons(
        courses=courses,
        output_root=output_root,
        department_code=args.department_code,
    )

    print(f"Seed files used: {len(existing_seed_files)}")
    print(f"Courses parsed:  {total_parsed}")
    print(f"Unique courses:  {len(courses)}")
    print(f"JSON written:    {written_count}")
    print(f"Output root:     {output_root}")


if __name__ == "__main__":
    main()
