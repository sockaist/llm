# kg_db.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Dict, Tuple, Literal
import os

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json


NodeType = Literal[
    "DEPARTMENT", "COURSE", "COURSE_TYPE", "TRACK", "DETAIL", "TAG",
    "PROFESSOR", "LABORATORY", "FIELD",
]
RelationType = Literal[
    "SUBSTITUTES", "EQUIVALENT_TO", "COUNTS_AS", "INCLUDES", "EXCLUDES", "REQUIRES", "CAPS",
    "RESEARCHES_IN", "AFFILIATED_WITH",
]
RuleType = Literal[
    "MIN_CREDITS", "MAX_CREDITS", "CREDITS_RANGE", "EXACT_CREDITS",
    "MIN_COURSES", "MAX_COURSES", "COURSES_RANGE", "EXACT_COURSES",
    "AT_LEAST_ONE_OF", "K_OF_N", "ALL_OF",
    "MUTUALLY_EXCLUSIVE", "FORBIDS",
    "PREREQUISITE", "COREQUISITE",
    "CUSTOM",
]


@dataclass(frozen=True)
class DBConfig:
    dsn: str  # e.g. "postgresql://user:pass@host:5432/kaist_soc"


def connect(cfg: DBConfig) -> psycopg.Connection:
    # autocommit False: we manage transactions per function (safe + consistent)
    return psycopg.connect(cfg.dsn, row_factory=dict_row)


# ------------------------------------------------------------
# Core helpers
# ------------------------------------------------------------
def _fetchone_val(cur, key: str):
    row = cur.fetchone()
    if row is None:
        return None
    return row[key]


def add_node_type(conn: psycopg.Connection, node_type: str) -> None:
    """
    Add a value to PostgreSQL enum type `node_type` if it does not exist.
    """
    with conn.cursor() as cur:
        cur.execute(
            "ALTER TYPE node_type ADD VALUE IF NOT EXISTS %s;",
            (node_type,),
        )
    conn.commit()


def add_relation_type(conn: psycopg.Connection, relation_type: str) -> None:
    """
    Add a value to PostgreSQL enum type `relation_type` if it does not exist.
    """
    with conn.cursor() as cur:
        cur.execute(
            "ALTER TYPE relation_type ADD VALUE IF NOT EXISTS %s;",
            (relation_type,),
        )
    conn.commit()


def create_node(conn: psycopg.Connection, node_type: NodeType) -> int:
    """
    Create a row in nodes and return node_id.
    """
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO nodes (node_type) VALUES (%s) RETURNING node_id;",
            (node_type,),
        )
        node_id = _fetchone_val(cur, "node_id")
    conn.commit()
    return int(node_id)


def get_department_id(conn: psycopg.Connection, department_code: str) -> Optional[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT node_id FROM departments WHERE department_code=%s;", (department_code,))
        row = cur.fetchone()
    return int(row["node_id"]) if row else None


def get_course_id(conn: psycopg.Connection, course_num: str) -> Optional[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT node_id FROM courses WHERE course_num=%s;", (course_num,))
        row = cur.fetchone()
    return int(row["node_id"]) if row else None


def get_course_type_id(conn: psycopg.Connection, type_name: str) -> Optional[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT node_id FROM course_types WHERE type_name=%s;", (type_name,))
        row = cur.fetchone()
    return int(row["node_id"]) if row else None


def get_track_id(conn: psycopg.Connection, track_name: str, department_code: Optional[str] = None) -> Optional[int]:
    with conn.cursor() as cur:
        if department_code is None:
            cur.execute(
                "SELECT node_id FROM graduate_tracks WHERE track_name=%s ORDER BY node_id DESC LIMIT 1;",
                (track_name,),
            )
        else:
            cur.execute(
                """
                SELECT gt.node_id
                FROM graduate_tracks gt
                JOIN departments d ON d.node_id = gt.department_node_id
                WHERE gt.track_name=%s AND d.department_code=%s
                ORDER BY gt.node_id DESC
                LIMIT 1;
                """,
                (track_name, department_code),
            )
        row = cur.fetchone()
    return int(row["node_id"]) if row else None


def get_tag_id(conn: psycopg.Connection, tag_key: str) -> Optional[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT node_id FROM tags WHERE tag_key=%s;", (tag_key,))
        row = cur.fetchone()
    return int(row["node_id"]) if row else None


# ------------------------------------------------------------
# Evidence / Rules
# ------------------------------------------------------------
def create_evidence(
    conn: psycopg.Connection,
    link: Optional[str] = None,
    doc_name: Optional[str] = None,
    ref_page: Optional[int] = None,
    ref_content: Optional[str] = None,
) -> int:
    """
    Insert an evidence and return evidence_id.
    (Evidence는 보통 immutable이라 upsert 대신 단순 insert 권장)
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO evidences (link, doc_name, ref_page, ref_content)
            VALUES (%s, %s, %s, %s)
            RETURNING evidence_id;
            """,
            (link, doc_name, ref_page, ref_content),
        )
        evidence_id = _fetchone_val(cur, "evidence_id")
    conn.commit()
    return int(evidence_id)


def create_rule(
    conn: psycopg.Connection,
    rule_type: RuleType,
    condition: Dict[str, Any],
    action: Dict[str, Any],
    priority: int = 0,
    evidence_id: Optional[int] = None,
) -> int:
    """
    Insert a rule and return rule_id.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT rule_type_id FROM rule_types WHERE code=%s;",
            (rule_type,),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(
                f"Unknown rule_type: {rule_type}. "
                "Insert it into rule_types first."
            )
        rule_type_id = int(row["rule_type_id"])

        cur.execute(
            """
            INSERT INTO rules (rule_type_id, condition, action, priority, evidence_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING rule_id;
            """,
            (rule_type_id, Json(condition), Json(action), priority, evidence_id),
        )
        rule_id = _fetchone_val(cur, "rule_id")
    conn.commit()
    return int(rule_id)


# ------------------------------------------------------------
# Node creators (idempotent upsert)
# ------------------------------------------------------------
def create_department(
    conn: psycopg.Connection,
    department_code: str,
    department_name: str,
) -> int:
    """
    Upsert department by department_code, return node_id.
    """
    existing = get_department_id(conn, department_code)
    if existing is not None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE departments
                SET department_name=%s
                WHERE node_id=%s;
                """,
                (department_name, existing),
            )
        conn.commit()
        return existing

    node_id = create_node(conn, "DEPARTMENT")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO departments (node_id, department_code, department_name)
            VALUES (%s, %s, %s);
            """,
            (node_id, department_code, department_name),
        )
    conn.commit()
    return node_id


def create_course_type(conn: psycopg.Connection, type_name: str) -> int:
    existing = get_course_type_id(conn, type_name)
    if existing is not None:
        return existing

    node_id = create_node(conn, "COURSE_TYPE")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO course_types (node_id, type_name) VALUES (%s, %s);",
            (node_id, type_name),
        )
    conn.commit()
    return node_id


def create_tag(conn: psycopg.Connection, tag_key: str, description: Optional[str] = None) -> int:
    existing = get_tag_id(conn, tag_key)
    if existing is not None:
        with conn.cursor() as cur:
            cur.execute("UPDATE tags SET description=%s WHERE node_id=%s;", (description, existing))
        conn.commit()
        return existing

    node_id = create_node(conn, "TAG")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO tags (node_id, tag_key, description) VALUES (%s, %s, %s);",
            (node_id, tag_key, description),
        )
    conn.commit()
    return node_id


def create_track(conn: psycopg.Connection, track_name: str, department_code: str) -> int:
    existing = get_track_id(conn, track_name, department_code)
    if existing is not None:
        return existing

    dept_id = get_department_id(conn, department_code)
    if dept_id is None:
        raise ValueError(f"Department not found: {department_code}. Create it first.")

    node_id = create_node(conn, "TRACK")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO graduate_tracks (node_id, track_name, department_node_id)
            VALUES (%s, %s, %s);
            """,
            (node_id, track_name, dept_id),
        )
    conn.commit()
    return node_id


def create_course(
    conn: psycopg.Connection,
    course_num: str,
    credits: int,
    department_code: str,
    history: Optional[str] = None,
    exp: Optional[str] = None,
    division: Optional[str] = None,
    mutual: Optional[bool] = None,
) -> int:
    """
    Upsert by course_num, return node_id.
    """
    existing = get_course_id(conn, course_num)
    dept_id = get_department_id(conn, department_code)
    if dept_id is None:
        raise ValueError(f"Department not found: {department_code}. Create it first.")

    if existing is not None:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE courses
                SET history=%s, exp=%s, credits=%s, division=%s, mutual=%s, department_node_id=%s
                WHERE node_id=%s;
                """,
                (history, exp, credits, division, mutual, dept_id, existing),
            )
        conn.commit()
        return existing

    node_id = create_node(conn, "COURSE")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, department_node_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """,
            (node_id, course_num, history, exp, credits, division, mutual, dept_id),
        )
    conn.commit()
    return node_id


def create_detail_requirement(
    conn: psycopg.Connection,
    track_node_id: int,
    detail_name: str,
    is_required: bool,
    valid_years: str = "[,]",  # int4range literal: "[2024,)" etc. default all years
    rule_id: Optional[int] = None,
) -> int:
    """
    Insert a detail_requirement and return node_id.
    Note: detail_no_overlap constraint may reject overlapping inserts.
    """
    node_id = create_node(conn, "DETAIL")
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO detail_requirements (node_id, track_node_id, detail_name, is_required, valid_years, rule_id)
            VALUES (%s, %s, %s, %s, %s::int4range, %s);
            """,
            (node_id, track_node_id, detail_name, is_required, valid_years, rule_id),
        )
    conn.commit()
    return node_id


# ------------------------------------------------------------
# Course mappings
# ------------------------------------------------------------
def add_course_mapping(
    conn: psycopg.Connection,
    course_node_id: int,
    type_node_id: int,
    valid_years: str = "[,]",
    evidence_id: Optional[int] = None,
) -> int:
    """
    Insert course_mappings row; return mapping_id.
    Overlap constraint may reject.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id)
            VALUES (%s, %s, %s::int4range, %s)
            RETURNING mapping_id;
            """,
            (course_node_id, type_node_id, valid_years, evidence_id),
        )
        mapping_id = _fetchone_val(cur, "mapping_id")
    conn.commit()
    return int(mapping_id)


# ------------------------------------------------------------
# Relations
# ------------------------------------------------------------
def create_relation(
    conn: psycopg.Connection,
    relation_type: RelationType,
    src_node_id: int,
    dst_node_id: int,
    valid_years: str = "[,]",
    rule_id: Optional[int] = None,
    evidence_id: Optional[int] = None,
) -> int:
    """
    Insert relation; return relation_id.
    Overlap constraint may reject.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO relations (relation_type, src_node_id, dst_node_id, valid_years, rule_id, evidence_id)
            VALUES (%s, %s, %s, %s::int4range, %s, %s)
            RETURNING relation_id;
            """,
            (relation_type, src_node_id, dst_node_id, valid_years, rule_id, evidence_id),
        )
        relation_id = _fetchone_val(cur, "relation_id")
    conn.commit()
    return int(relation_id)


def create_equivalent_pair(
    conn: psycopg.Connection,
    a_node_id: int,
    b_node_id: int,
    valid_years: str = "[,]",
    rule_id: Optional[int] = None,
    evidence_id: Optional[int] = None,
) -> Tuple[int, int]:
    """
    Convenience: insert both directions for EQUIVALENT_TO if you want it explicit.
    (스키마 자체는 단일 edge로도 '양방향 성격'을 의미할 수 있으나,
     검색 단순화를 위해 양쪽을 다 넣는 방식을 지원)
    """
    r1 = create_relation(conn, "EQUIVALENT_TO", a_node_id, b_node_id, valid_years, rule_id, evidence_id)
    r2 = create_relation(conn, "EQUIVALENT_TO", b_node_id, a_node_id, valid_years, rule_id, evidence_id)
    return r1, r2


# ------------------------------------------------------------
# Example usage
# ------------------------------------------------------------
if __name__ == "__main__":
    cfg = DBConfig(dsn=os.environ.get("DATABASE_URL", "postgresql://user:pass@localhost:5432/kaist_soc"))
    conn = connect(cfg)

    # departments
    create_department(conn, "ALL", "ALL")
    create_department(conn, "CS", "School of Computing")

    # course types
    major_req = create_course_type(conn, "MAJOR_REQUIRED")
    major_elec = create_course_type(conn, "MAJOR_ELECTIVE")

    # course
    cs204 = create_course(conn, "CS.204", credits=3, department_code="CS", exp="Data Structures", division="Bachelor", mutual=False)

    # mapping
    ev = create_evidence(conn, link="https://example.com/handbook", doc_name="Handbook", ref_page=12, ref_content="CS.204 is required")
    add_course_mapping(conn, course_node_id=cs204, type_node_id=major_req, valid_years="[2024,)", evidence_id=ev)

    # rule + relation(CAPS)
    rule = create_rule(
        conn,
        rule_type="CREDITS_RANGE",
        condition={"scope_tag": "COE_ELECTIVE_ALLOWED", "track": "CS_MAJOR"},
        action={"min": None, "max": 6, "counts_as": "MAJOR_ELECTIVE"},
        priority=10,
        evidence_id=ev,
    )

    # tag + track
    tag = create_tag(conn, "COE_ELECTIVE_ALLOWED", "CoE elective 인정 과목")
    track = create_track(conn, "CS_MAJOR", "CS")

    create_relation(conn, "CAPS", src_node_id=tag, dst_node_id=track, valid_years="[2024,)", rule_id=rule, evidence_id=ev)

    conn.close()
