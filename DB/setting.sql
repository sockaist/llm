-- =========================================================
-- Schema: KAIST SoC Knowledge Graph (PostgreSQL)
-- rule_type reference table 반영한 전체 테이블 생성 스크립트
-- =========================================================

BEGIN;

-- =========================================================
-- 0) Extensions
-- =========================================================
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- =========================================================
-- 1) ENUM TYPES
-- =========================================================

-- node_type
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'node_type') THEN
    CREATE TYPE node_type AS ENUM (
      'DEPARTMENT',
      'COURSE',
      'COURSE_TYPE',
      'TRACK',
      'DETAIL',
      'TAG',
      'PROFESSOR',
      'LABORATORY',
      'FIELD'
    );
  END IF;
END$$;

-- relation_type
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'relation_type') THEN
    CREATE TYPE relation_type AS ENUM (
      'SUBSTITUTES',
      'EQUIVALENT_TO',
      'COUNTS_AS',
      'INCLUDES',
      'EXCLUDES',
      'REQUIRES',
      'CAPS',
      'RESEARCHES_IN',
      'AFFILIATED_WITH'
    );
  END IF;
END$$;

-- =========================================================
-- 2) BASE TABLES
-- =========================================================

-- nodes (all KG entities)
CREATE TABLE IF NOT EXISTS nodes (
  node_id   BIGSERIAL PRIMARY KEY,
  node_type node_type NOT NULL
);

-- evidences (citations)
CREATE TABLE IF NOT EXISTS evidences (
  evidence_id BIGSERIAL PRIMARY KEY,
  link        TEXT,
  doc_name    TEXT,
  ref_page    INT,
  ref_content TEXT
);

-- rule_types (reference table for extensible rule categories)
CREATE TABLE IF NOT EXISTS rule_types (
  rule_type_id BIGSERIAL PRIMARY KEY,
  code         TEXT UNIQUE NOT NULL,
  description  TEXT,
  is_active    BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO rule_types (code, description) VALUES
  ('MIN_CREDITS', NULL),
  ('MAX_CREDITS', NULL),
  ('CREDITS_RANGE', NULL),
  ('EXACT_CREDITS', NULL),
  ('MIN_COURSES', NULL),
  ('MAX_COURSES', NULL),
  ('COURSES_RANGE', NULL),
  ('EXACT_COURSES', NULL),
  ('AT_LEAST_ONE_OF', NULL),
  ('K_OF_N', NULL),
  ('ALL_OF', NULL),
  ('MUTUALLY_EXCLUSIVE', NULL),
  ('FORBIDS', NULL),
  ('PREREQUISITE', NULL),
  ('COREQUISITE', NULL),
  ('CUSTOM', NULL)
ON CONFLICT (code) DO NOTHING;

-- rules (only detail_requirements + relations can reference rules)
CREATE TABLE IF NOT EXISTS rules (
  rule_id     BIGSERIAL PRIMARY KEY,
  rule_type_id BIGINT NOT NULL REFERENCES rule_types(rule_type_id),
  condition   JSONB NOT NULL DEFAULT '{}'::jsonb,
  action      JSONB NOT NULL,
  priority    INT DEFAULT 0,
  evidence_id BIGINT NULL REFERENCES evidences(evidence_id)
);

CREATE INDEX IF NOT EXISTS rules_rule_type_id_idx
ON rules (rule_type_id);

CREATE INDEX IF NOT EXISTS rules_condition_gin
ON rules USING GIN (condition jsonb_path_ops);

-- =========================================================
-- 3) NODE SUB-TABLES
-- =========================================================

-- departments
CREATE TABLE IF NOT EXISTS departments (
  node_id          BIGINT PRIMARY KEY REFERENCES nodes(node_id) ON DELETE CASCADE,
  department_code  TEXT UNIQUE NOT NULL,   -- CS, MAS, ALL
  department_name  TEXT UNIQUE NOT NULL    -- School of Computing, ALL
);

-- seed default departments
DO $$
DECLARE
  v_cs_node_id  BIGINT;
  v_all_node_id BIGINT;
BEGIN
  SELECT node_id INTO v_cs_node_id FROM departments WHERE department_code = 'CS';
  IF v_cs_node_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('DEPARTMENT') RETURNING node_id INTO v_cs_node_id;
    INSERT INTO departments (node_id, department_code, department_name)
    VALUES (v_cs_node_id, 'CS', 'School of Computing');
  ELSE
    UPDATE departments
    SET department_name = 'School of Computing'
    WHERE node_id = v_cs_node_id;
  END IF;

  SELECT node_id INTO v_all_node_id FROM departments WHERE department_code = 'ALL';
  IF v_all_node_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('DEPARTMENT') RETURNING node_id INTO v_all_node_id;
    INSERT INTO departments (node_id, department_code, department_name)
    VALUES (v_all_node_id, 'ALL', 'ALL');
  ELSE
    UPDATE departments
    SET department_name = 'ALL'
    WHERE node_id = v_all_node_id;
  END IF;
END$$;

-- courses
CREATE TABLE IF NOT EXISTS courses (
  node_id             BIGINT PRIMARY KEY REFERENCES nodes(node_id) ON DELETE CASCADE,
  course_num          TEXT UNIQUE NOT NULL,  -- CS.40008 etc
  history             TEXT,                  -- opened semesters (optional free text)
  exp                 TEXT,                  -- description (optional)
  credits             INT NOT NULL,
  division            TEXT,                  -- Bachelor / Graduate etc
  mutual              BOOLEAN,
  semester            TEXT,                  -- offered semesters (S, F, A)
  department_node_id  BIGINT NOT NULL REFERENCES departments(node_id)
);

CREATE INDEX IF NOT EXISTS courses_dept_idx ON courses(department_node_id);

-- course_types
CREATE TABLE IF NOT EXISTS course_types (
  node_id    BIGINT PRIMARY KEY REFERENCES nodes(node_id) ON DELETE CASCADE,
  type_name  TEXT UNIQUE NOT NULL  -- MAJOR_REQUIRED, MAJOR_ELECTIVE...
);

-- seed default course types (undergraduate + graduate)
DO $$
DECLARE
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'BASIC_REQUIRED';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'BASIC_REQUIRED');
  END IF;

  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'BASIC_ELECTIVE';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'BASIC_ELECTIVE');
  END IF;

  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_REQUIRED';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'MAJOR_REQUIRED');
  END IF;

  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'MAJOR_ELECTIVE');
  END IF;

  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'COMMON_REQUIRED';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'COMMON_REQUIRED');
  END IF;

  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'REQUIRED_ELECTIVE');
  END IF;

  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'GENERAL_ELECTIVE');
  END IF;

  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'RESEARCH';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'RESEARCH');
  END IF;
END$$;

-- graduate_tracks
CREATE TABLE IF NOT EXISTS graduate_tracks (
  node_id             BIGINT PRIMARY KEY REFERENCES nodes(node_id) ON DELETE CASCADE,
  track_name          TEXT NOT NULL, -- CS_MAJOR, MINOR, DOUBLE_MAJOR, AI_TRACK...
  department_node_id  BIGINT NOT NULL REFERENCES departments(node_id)
);

CREATE INDEX IF NOT EXISTS tracks_dept_idx ON graduate_tracks(department_node_id);

-- detail_requirements
CREATE TABLE IF NOT EXISTS detail_requirements (
  node_id       BIGINT PRIMARY KEY REFERENCES nodes(node_id) ON DELETE CASCADE,
  track_node_id BIGINT NOT NULL REFERENCES graduate_tracks(node_id) ON DELETE CASCADE,
  detail_name   TEXT NOT NULL,        -- English, Major, Research...
  is_required   BOOLEAN NOT NULL,
  valid_years   int4range NOT NULL DEFAULT int4range(NULL, NULL, '[]'),
  rule_id       BIGINT NULL REFERENCES rules(rule_id)
);

CREATE INDEX IF NOT EXISTS detail_track_idx  ON detail_requirements(track_node_id);
CREATE INDEX IF NOT EXISTS detail_years_gist ON detail_requirements USING GIST (valid_years);

-- 같은 track에서 같은 detail_name이 기간 겹치면 막기
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'detail_no_overlap') THEN
    ALTER TABLE detail_requirements
    ADD CONSTRAINT detail_no_overlap
    EXCLUDE USING GIST (
      track_node_id WITH =,
      detail_name WITH =,
      valid_years WITH &&
    );
  END IF;
END$$;

-- tags
CREATE TABLE IF NOT EXISTS tags (
  node_id      BIGINT PRIMARY KEY REFERENCES nodes(node_id) ON DELETE CASCADE,
  tag_key      TEXT UNIQUE NOT NULL,     -- COE_ELECTIVE_ALLOWED, AI_TRACK_COURSES...
  description  TEXT
);

-- =========================================================
-- 4) MAPPINGS / RELATIONS
-- =========================================================

-- course_mappings: course -> course_type with validity range
CREATE TABLE IF NOT EXISTS course_mappings (
  mapping_id      BIGSERIAL PRIMARY KEY,
  course_node_id  BIGINT NOT NULL REFERENCES courses(node_id) ON DELETE CASCADE,
  type_node_id    BIGINT NOT NULL REFERENCES course_types(node_id) ON DELETE CASCADE,
  valid_years     int4range NOT NULL DEFAULT int4range(NULL, NULL, '[]'),
  evidence_id     BIGINT NULL REFERENCES evidences(evidence_id)
);

CREATE INDEX IF NOT EXISTS course_map_course_idx ON course_mappings(course_node_id);
CREATE INDEX IF NOT EXISTS course_map_type_idx   ON course_mappings(type_node_id);
CREATE INDEX IF NOT EXISTS course_map_years_gist ON course_mappings USING GIST (valid_years);

-- =========================================================
-- 5) professors / laboratories / fields
-- =========================================================

-- professors (node_type='PROFESSOR')
CREATE TABLE IF NOT EXISTS professors (
  node_id     BIGINT PRIMARY KEY REFERENCES nodes(node_id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  email       TEXT UNIQUE,
  major       TEXT,
  degree      TEXT,
  web         TEXT,
  phone       TEXT,
  office      TEXT,
  source_ref  TEXT,
  exp         TEXT
);

CREATE INDEX IF NOT EXISTS professors_name_idx ON professors(name);

-- fields (node_type='FIELD')
CREATE TABLE IF NOT EXISTS fields (
  node_id     BIGINT PRIMARY KEY REFERENCES nodes(node_id) ON DELETE CASCADE,
  field_name  TEXT UNIQUE NOT NULL
);

-- laboratories (node_type='LABORATORY')
CREATE TABLE IF NOT EXISTS laboratories (
  node_id     BIGINT PRIMARY KEY REFERENCES nodes(node_id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  web         TEXT,
  email       TEXT,
  phone       TEXT,
  office      TEXT,
  intro       TEXT,
  etc         TEXT
);

CREATE INDEX IF NOT EXISTS laboratories_name_idx ON laboratories(name);

-- 관계는 relations 테이블을 사용:
-- professor/laboratory -(RESEARCHES_IN)-> field
-- professor -(AFFILIATED_WITH)-> laboratory

-- 완전 동일 중복 방지
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'course_map_uniq'
  ) THEN
    CREATE UNIQUE INDEX course_map_uniq
    ON course_mappings(course_node_id, type_node_id, valid_years);
  END IF;
END$$;

-- 동일 course/type 기간 겹치면 막기
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'course_map_no_overlap') THEN
    ALTER TABLE course_mappings
    ADD CONSTRAINT course_map_no_overlap
    EXCLUDE USING GIST (
      course_node_id WITH =,
      type_node_id WITH =,
      valid_years WITH &&
    );
  END IF;
END$$;

-- relations: general KG edges across nodes
CREATE TABLE IF NOT EXISTS relations (
  relation_id    BIGSERIAL PRIMARY KEY,
  relation_type  relation_type NOT NULL,
  src_node_id    BIGINT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
  dst_node_id    BIGINT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
  valid_years    int4range NOT NULL DEFAULT int4range(NULL, NULL, '[]'),
  rule_id        BIGINT NULL REFERENCES rules(rule_id),
  evidence_id    BIGINT NULL REFERENCES evidences(evidence_id)
);

-- 1-hop 최적화: outbound / inbound
CREATE INDEX IF NOT EXISTS rel_out_idx
ON relations (src_node_id, relation_type, dst_node_id);

CREATE INDEX IF NOT EXISTS rel_in_idx
ON relations (dst_node_id, relation_type, src_node_id);

-- 연도 포함 검색 최적화
CREATE INDEX IF NOT EXISTS rel_years_gist
ON relations USING GIST (valid_years);

-- 완전 동일 중복 방지
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relname = 'rel_uniq'
  ) THEN
    CREATE UNIQUE INDEX rel_uniq
    ON relations (relation_type, src_node_id, dst_node_id, valid_years);
  END IF;
END$$;

-- 동일 src-dst-type 기간 겹치면 막기(선택 강력)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'rel_no_overlap') THEN
    ALTER TABLE relations
    ADD CONSTRAINT rel_no_overlap
    EXCLUDE USING GIST (
      relation_type WITH =,
      src_node_id WITH =,
      dst_node_id WITH =,
      valid_years WITH &&
    );
  END IF;
END$$;

COMMIT;
