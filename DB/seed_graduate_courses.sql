BEGIN;

-- Ensure required course_types exist
DO $$
DECLARE
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'COMMON_REQUIRED';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'COMMON_REQUIRED');
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'GENERAL_ELECTIVE');
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'REQUIRED_ELECTIVE');
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'RESEARCH';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'RESEARCH');
  END IF;
END$$;

-- CC.50010 (공통필수)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CC.50010';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CC.50010', NULL, '', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'COMMON_REQUIRED';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'COMMON_REQUIRED';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50000 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50000';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50000', NULL, 'Building on undergraduate CS.30000 (Introduction to Algorithms), the graduate-level course CS.50000 revolves around advanced aspects of algorithms. More specifically we discuss, design, and analyze algorithms with respect to various cost measures beyond traditional (=sequential) runtime, such as: memory use, parallel time/depth, size=#CPUs/gates, communication volume, #coin flips etc. And we discuss, design, and analyze algorithms in various modes beyond the traditional worst-case, such as: average-case, expected, amortized, competitive (ratio), approximation ratio etc. The practical impact of these algorithms is demonstrated in selected implementations.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Building on undergraduate CS.30000 (Introduction to Algorithms), the graduate-level course CS.50000 revolves around advanced aspects of algorithms. More specifically we discuss, design, and analyze algorithms with respect to various cost measures beyond traditional (=sequential) runtime, such as: memory use, parallel time/depth, size=#CPUs/gates, communication volume, #coin flips etc. And we discuss, design, and analyze algorithms in various modes beyond the traditional worst-case, such as: average-case, expected, amortized, competitive (ratio), approximation ratio etc. The practical impact of these algorithms is demonstrated in selected implementations.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50004 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50004';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50004', NULL, 'Computational geometry studies algorithms and data structures for processing and storing geometric objects. This courses discusses algorithm design techniques such as plane sweep and geometric divide & conquer; data structures such as point location structures, interval trees, segment trees, and BSP trees; and geometric structures such as arrangements, triangulations, Voronoi diagrams, and Delaunay triangulations.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Computational geometry studies algorithms and data structures for processing and storing geometric objects. This courses discusses algorithm design techniques such as plane sweep and geometric divide & conquer; data structures such as point location structures, interval trees, segment trees, and BSP trees; and geometric structures such as arrangements, triangulations, Voronoi diagrams, and Delaunay triangulations.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50100 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50100';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50100', NULL, 'This goal of this course is to provide the student with an understanding of (i) the architectural aspect of the performance issues, and (ii) investigation of the full spectrum of design alternatives and their trade-offs.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This goal of this course is to provide the student with an understanding of (i) the architectural aspect of the performance issues, and (ii) investigation of the full spectrum of design alternatives and their trade-offs.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50200 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50200';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50200', NULL, 'This course reviews design principles and implementation techniques of various programming languages. This course also introduces a wide spectrum of programming paradigms such as functional programming, logic programming, and object-oriented programming.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course reviews design principles and implementation techniques of various programming languages. This course also introduces a wide spectrum of programming paradigms such as functional programming, logic programming, and object-oriented programming.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50202 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50202';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50202', NULL, 'This course is intended to understand the current theories of deterministic parsing of context-free grammars. Two basic parsing schemes, LR(k) and LL(k) parsing, are considered and the practical SLR(1) and LALR(1) techniques are discussed. The syntactic error recovery in LR-based parsing is also discussed.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course is intended to understand the current theories of deterministic parsing of context-free grammars. Two basic parsing schemes, LR(k) and LL(k) parsing, are considered and the practical SLR(1) and LALR(1) techniques are discussed. The syntactic error recovery in LR-based parsing is also discussed.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50204 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50204';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50204', NULL, 'This course introduces a technique called program analysis that estimates the behavior of programs before running them. Instead of running programs with infinite inputs, program analysis statically estimates runtime behaviors of programs within a finite time. The course will cover fundamental theories, designs and implementations of program analysis including semantic formalism and the theory of abstract interpretation.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course introduces a technique called program analysis that estimates the behavior of programs before running them. Instead of running programs with infinite inputs, program analysis statically estimates runtime behaviors of programs within a finite time. The course will cover fundamental theories, designs and implementations of program analysis including semantic formalism and the theory of abstract interpretation.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50300 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50300';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50300', NULL, 'The main focus of this course is to understand the concurrency features of modern operating systems. Concurrent programming is dealt with in detail to simulate various parts of an OS. Other topics that are required to understand the process-oriented OS structure are also discussed.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The main focus of this course is to understand the concurrency features of modern operating systems. Concurrent programming is dealt with in detail to simulate various parts of an OS. Other topics that are required to understand the process-oriented OS structure are also discussed.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50400 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50400';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50400', NULL, 'The goal of this course is to provide students with an understanding on the following topics. (1) the concept of layered architectures, (2) the design and implementation of communication protocols, (3) the multimedia communication protocol, and (4) the design of high-speed protocols. The course also covers many aspects of protocol engineering: design, implementation and test of communication protocols.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to provide students with an understanding on the following topics. (1) the concept of layered architectures, (2) the design and implementation of communication protocols, (3) the multimedia communication protocol, and (4) the design of high-speed protocols. The course also covers many aspects of protocol engineering: design, implementation and test of communication protocols.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50402 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50402';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50402', NULL, 'This course reviews the state-of-the-art of today''s Internet system as well as service architectures, describes the challenges facing them, and discusses emerging approaches. In particular, the course covers issues around Internet traffic characterization; protocols; server architectures and performance; mobile and pervasive services and systems, virtualization; content distribution; peer-to-peer architecture, quality of services (QoS); and architectural alternatives for applications and services. The goal of the course is to gain understanding of the current research issues and a vision of the next generation Internet system and service architecture.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course reviews the state-of-the-art of today''s Internet system as well as service architectures, describes the challenges facing them, and discusses emerging approaches. In particular, the course covers issues around Internet traffic characterization; protocols; server architectures and performance; mobile and pervasive services and systems, virtualization; content distribution; peer-to-peer architecture, quality of services (QoS); and architectural alternatives for applications and services. The goal of the course is to gain understanding of the current research issues and a vision of the next generation Internet system and service architecture.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50403 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50403';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50403', NULL, 'This course provides theoretical knowledge and hands-on experience with distributed systems'' design and implementation. The course will focus on the principles underlying modern distributed systems such as networking, naming, security, distributed sychronization, concurrency, fault tolerance, etc. along with case studies. Emphasis will be on evaluating and critiquing approaches and ideas. (Prerequisite: CS510, CS530)', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course provides theoretical knowledge and hands-on experience with distributed systems'' design and implementation. The course will focus on the principles underlying modern distributed systems such as networking, naming, security, distributed sychronization, concurrency, fault tolerance, etc. along with case studies. Emphasis will be on evaluating and critiquing approaches and ideas. (Prerequisite: CS510, CS530)', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50406 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50406';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50406', NULL, 'This course is intended for graduate students who want to understand Wireless Mobile Internet. It provides a comprehensive technical guide covering introductory concepts, fundamental techniques, recent advances and open issues in ad hoc networks and wireless mesh networks. The course consists of lectures, exams and term project.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course is intended for graduate students who want to understand Wireless Mobile Internet. It provides a comprehensive technical guide covering introductory concepts, fundamental techniques, recent advances and open issues in ad hoc networks and wireless mesh networks. The course consists of lectures, exams and term project.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50408 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50408';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50408', NULL, 'The main objective of this course is to provide students with comprehensive knowledge of information security. The course helps students to build profound understanding of information security by teaching the fundamentals of information security, which include, but are not limited to: cipher, access control, protocol, and software engineering. The primary fous of the course is on the general concept of information security.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The main objective of this course is to provide students with comprehensive knowledge of information security. The course helps students to build profound understanding of information security by teaching the fundamentals of information security, which include, but are not limited to: cipher, access control, protocol, and software engineering. The primary fous of the course is on the general concept of information security.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50500 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50500';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50500', NULL, 'This course covers fundamental concepts required in developing reliable softwares in a cost-effective manner.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers fundamental concepts required in developing reliable softwares in a cost-effective manner.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50502 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50502';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50502', NULL, 'For long time, computer scientists have investigated the problem of automating software development from a specification to its program. So far the efforts were not fully successful but much of the results can be fruitfully applied to development of small programs and critical small portions of large programs. In this course, we study the important results of such efforts and, for that, we learn how to model software systems with formal description techniques, how to model software systems such that the various properties expected of the software systems are verifiable and how to verify various properties of software systems though the models.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'For long time, computer scientists have investigated the problem of automating software development from a specification to its program. So far the efforts were not fully successful but much of the results can be fruitfully applied to development of small programs and critical small portions of large programs. In this course, we study the important results of such efforts and, for that, we learn how to model software systems with formal description techniques, how to model software systems such that the various properties expected of the software systems are verifiable and how to verify various properties of software systems though the models.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50504 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50504';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50504', NULL, 'Development of software and systems requires to understand engineering design paradigms and methods for bridging the gap between a problem to be solved and a working system. This course teaches how to understand problems and to design, architect, and evaluate software solutions.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Development of software and systems requires to understand engineering design paradigms and methods for bridging the gap between a problem to be solved and a working system. This course teaches how to understand problems and to design, architect, and evaluate software solutions.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50600 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50600';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50600', NULL, 'This course addresses current technologies of various aspects of database systems. The main objective of this course is to study the design and implementation issues of high performance and high functionality database systems. Through this course, the students will have concrete concepts on database systems and will have in-depth knowledge on most issues of advanced database researches.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course addresses current technologies of various aspects of database systems. The main objective of this course is to study the design and implementation issues of high performance and high functionality database systems. Through this course, the students will have concrete concepts on database systems and will have in-depth knowledge on most issues of advanced database researches.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50602 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50602';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50602', NULL, 'The goal of this course is to establish a consistent framework for database design. Practical database design methodology, major principles, tools and analysis techniques for various phases of database design process are studied.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to establish a consistent framework for database design. Practical database design methodology, major principles, tools and analysis techniques for various phases of database design process are studied.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50604 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50604';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50604', NULL, 'The ability to handle big data and statistically analyse them is crucial for data scientists. This course covers social data basics and tools to handle, analyze, and visualize such data via utilizing key analysis packages in R.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The ability to handle big data and statistically analyse them is crucial for data scientists. This course covers social data basics and tools to handle, analyze, and visualize such data via utilizing key analysis packages in R.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50700 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50700';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50700', NULL, 'Classical artificial intelligence algorithms and introduction to machine learning based on probability and statistics.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Classical artificial intelligence algorithms and introduction to machine learning based on probability and statistics.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50702 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50702';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50702', NULL, 'The goal of this course is to provide students with state-of-the-art technologies in intelligent robotics. Major topics include sensing, path planning, and navigation, as well as artificial intelligence and neural networks for robotics.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to provide students with state-of-the-art technologies in intelligent robotics. Major topics include sensing, path planning, and navigation, as well as artificial intelligence and neural networks for robotics.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50704 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50704';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50704', NULL, 'As a typical application of symbolic AI machine translation (M.T) addresses the major issues involving computational linguistics, rules base, and more fundamentally knowledge representation and inference. In this regard, the goal of the course is to provide students with first-hand experience with a real AI problem. The topics include application of M.T., basic problems in M.T., and classical approaches to the problems.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'As a typical application of symbolic AI machine translation (M.T) addresses the major issues involving computational linguistics, rules base, and more fundamentally knowledge representation and inference. In this regard, the goal of the course is to provide students with first-hand experience with a real AI problem. The topics include application of M.T., basic problems in M.T., and classical approaches to the problems.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50706 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50706';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50706', NULL, 'The goal of this course is to provide students with theory and application of computer vision. Major topics include digital image fundamentals, binary vision, gray-level vision, 3-D vision, motion detection and analysis, computer vision system hardware and architecture, CAD-based vision, knowledge-based vision, neural-network-based vision.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to provide students with theory and application of computer vision. Major topics include digital image fundamentals, binary vision, gray-level vision, 3-D vision, motion detection and analysis, computer vision system hardware and architecture, CAD-based vision, knowledge-based vision, neural-network-based vision.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50709 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50709';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50709', NULL, 'This course focuses on universal models for languages, especially English and Korean. For computational study, issues on knowledge representation, generalized explanation on linguistic phenomena are discussed. When these models are applied to natural language processing, properties needed for computational models and their implementation methodologies are studied.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course focuses on universal models for languages, especially English and Korean. For computational study, issues on knowledge representation, generalized explanation on linguistic phenomena are discussed. When these models are applied to natural language processing, properties needed for computational models and their implementation methodologies are studied.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50800 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50800';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50800', NULL, 'We will study fundamentals of computer graphics and their applications to games, movies, and other related areas. In particular, we will study different branches, fundamentals, rendering, animation, and modeling, of computer graphics. Also, CS580 can be taken by students who have not taken any computer graphics related courses in their undergraduate courses.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'We will study fundamentals of computer graphics and their applications to games, movies, and other related areas. In particular, we will study different branches, fundamentals, rendering, animation, and modeling, of computer graphics. Also, CS580 can be taken by students who have not taken any computer graphics related courses in their undergraduate courses.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50804 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50804';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50804', NULL, '본 과목은 다음 세 가지 목표를 추구한다. 1) 실증적 HCI 연구를 위한 과학적 기반과 연구방법을 교육하고, 2) 다양한 사용자 인터페이스 기술 및 사례를 교육하고, 3) 새로운 사용자 인터페이스 아이디어를 구현하고 평가하는 경험 체득할 수 있는 기회를 제공한다.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '본 과목은 다음 세 가지 목표를 추구한다. 1) 실증적 HCI 연구를 위한 과학적 기반과 연구방법을 교육하고, 2) 다양한 사용자 인터페이스 기술 및 사례를 교육하고, 3) 새로운 사용자 인터페이스 아이디어를 구현하고 평가하는 경험 체득할 수 있는 기회를 제공한다.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50900 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50900';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50900', NULL, '"Semantic Web" allows machines to process and integrate Web resources intelligently. Beyond enabling quick and accurate web search, this technology may also allow the development of intelligent internet agents and facilitate communication between a multitude of heterogeneous web-accessible devices.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '"Semantic Web" allows machines to process and integrate Web resources intelligently. Beyond enabling quick and accurate web search, this technology may also allow the development of intelligent internet agents and facilitate communication between a multitude of heterogeneous web-accessible devices.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60100 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60100';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60100', NULL, 'This course discusses both parallel software and parallel architectures. It starts with an overview of the basic foundations such as hardware technology, applications and, computational models. An overview of parallel software and their limitations is provided. Some existing parallel machines and proposed parallel architectures are also covered.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course discusses both parallel software and parallel architectures. It starts with an overview of the basic foundations such as hardware technology, applications and, computational models. An overview of parallel software and their limitations is provided. Some existing parallel machines and proposed parallel architectures are also covered.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60302 (필수선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60302';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60302', NULL, 'The goal of this course is to provide in-depth design concepts and implementation skills required for designing and developing embedded operating systems. Topics covered include boot loader, process management, memory management, I/O device management, and file systems in embedded operating systems.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to provide in-depth design concepts and implementation skills required for designing and developing embedded operating systems. Topics covered include boot loader, process management, memory management, I/O device management, and file systems in embedded operating systems.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'REQUIRED_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'REQUIRED_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50401 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50401';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50401', NULL, 'The course is intended for graduate students to understand and develop smart business application running on smart phones. It provides a comprehensive guide covering programming technology on Mobile Internet, Mobile Security and Payment, Location based and Context Aware Services, Social Network Services, and Business Model Development Method through Case Study, Value Chain Analysis and Economic Feasibility Study. An application is proposed and developed by students as team consisting of business and engineering areas for the purpose of creating new application services and businesses.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The course is intended for graduate students to understand and develop smart business application running on smart phones. It provides a comprehensive guide covering programming technology on Mobile Internet, Mobile Security and Payment, Location based and Context Aware Services, Social Network Services, and Business Model Development Method through Case Study, Value Chain Analysis and Economic Feasibility Study. An application is proposed and developed by students as team consisting of business and engineering areas for the purpose of creating new application services and businesses.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50605 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50605';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50605', NULL, 'The goal of this course is to learn the basics of how to use sensor data for designing intelligent IoT services. The course covers the entire process of IoT data science for ubiquitous computing: i.e., data collection, pre-processing, feature extraction, and machine learning modeling. Mobile, wearable, and smart sensors will be used, and the types of sensor data covered include motion (e.g., vibration/acceleration, GPS), physiological signals (e.g., heart rate, skin temperature), and interaction data (e.g., app usage). Students will learn the basic digital signal processing and feature extraction techniques. Basic machine learning techniques (e.g., clustering, supervised learning, time-series learning, and deep learning) will be reviewed, and students will master these techniques with in-class practices with Google Co-lab and IoT devices. A final mini-project will help students to apply the techniques learned in the class to solve real-world IoT data science problems.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to learn the basics of how to use sensor data for designing intelligent IoT services. The course covers the entire process of IoT data science for ubiquitous computing: i.e., data collection, pre-processing, feature extraction, and machine learning modeling. Mobile, wearable, and smart sensors will be used, and the types of sensor data covered include motion (e.g., vibration/acceleration, GPS), physiological signals (e.g., heart rate, skin temperature), and interaction data (e.g., app usage). Students will learn the basic digital signal processing and feature extraction techniques. Basic machine learning techniques (e.g., clustering, supervised learning, time-series learning, and deep learning) will be reviewed, and students will master these techniques with in-class practices with Google Co-lab and IoT devices. A final mini-project will help students to apply the techniques learned in the class to solve real-world IoT data science problems.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50705 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50705';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50705', NULL, 'Recent progress in AI technologies and research have raised concerns about data privacy and protection, misuse of AI to harm people and society, bias in data and trained models, and AI divide that benefits the rich people and nations more than the poor. It is thus very important to learn about the ethical issues of AI including bias, fairness, privacy, trust, interpretability, and societal impact.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Recent progress in AI technologies and research have raised concerns about data privacy and protection, misuse of AI to harm people and society, bias in data and trained models, and AI divide that benefits the rich people and nations more than the poor. It is thus very important to learn about the ethical issues of AI including bias, fairness, privacy, trust, interpretability, and societal impact.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50707 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50707';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50707', NULL, 'This course will introduce graduate students to the emerging area of robot learning and interaction toward human-centered robotics. The course overviews each robotic learning and interaction areas including learning from demonstration (LfD), (inverse) reinforcement learning (RL), natural language interaction, interactive perception, etc. We will then review the state-of-the-art technologies and exercise a part of technologies using simulated robotic manipulators via Robot Operating System (ROS). Finally, we will exercise the learned techniques via final individual/team projects.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course will introduce graduate students to the emerging area of robot learning and interaction toward human-centered robotics. The course overviews each robotic learning and interaction areas including learning from demonstration (LfD), (inverse) reinforcement learning (RL), natural language interaction, interactive perception, etc. We will then review the state-of-the-art technologies and exercise a part of technologies using simulated robotic manipulators via Robot Operating System (ROS). Finally, we will exercise the learned techniques via final individual/team projects.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50708 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50708';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50708', NULL, 'We aim to study neural signal modellings through the integration of AI, control theory, neuroscience, biomechanics and robot design, and go over technologies of the human-robot interaction by using neural signals in the aspect of both software and hardware engineering. Discussion on the current and future trends and search about interdisciplinary approaches are planned. Various application examples will be demonstrated to promote students'' understanding.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'We aim to study neural signal modellings through the integration of AI, control theory, neuroscience, biomechanics and robot design, and go over technologies of the human-robot interaction by using neural signals in the aspect of both software and hardware engineering. Discussion on the current and future trends and search about interdisciplinary approaches are planned. Various application examples will be demonstrated to promote students'' understanding.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50806 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50806';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50806', NULL, 'In this class we will discuss various techniques of motion and path planning for various robots. We go over various classic techniques such as visibility graphs and cell decomposition. In particular, we will study probabilistic techniques that have been used for a wide variety of robots and extensively investigated in recent years.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this class we will discuss various techniques of motion and path planning for various robots. We go over various classic techniques such as visibility graphs and cell decomposition. In particular, we will study probabilistic techniques that have been used for a wide variety of robots and extensively investigated in recent years.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50808 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50808';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50808', NULL, 'In this class we will discuss various techniques related to image/video search. Especially, we will go over deep learning image/video features, their indexing data structures, and runtime query algorithms. We will also study recent learning based techniques that can handle various multi-modal data in addition to looking into novel applications of them.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this class we will discuss various techniques related to image/video search. Especially, we will go over deep learning image/video features, their indexing data structures, and runtime query algorithms. We will also study recent learning based techniques that can handle various multi-modal data in addition to looking into novel applications of them.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.50901 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.50901';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.50901', NULL, 'As the importance of software in the overall industrial economy grows, and as the software industry undergoes important transformations, this course reviews software technology and the issues that surround its dissemination and use from a number of relevant perspectives. This includes the perpectives from the user, the creator, manager, software supply industry, software creation industry, government.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'As the importance of software in the overall industrial economy grows, and as the software industry undergoes important transformations, this course reviews software technology and the issues that surround its dissemination and use from a number of relevant perspectives. This includes the perpectives from the user, the creator, manager, software supply industry, software creation industry, government.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.59900 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.59900';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.59900', NULL, '본 과목은 급변하는 전산학의 다양한 주제들을 새로운 방향으로 다루어, 학생들에게 최신 기술 발전 동향을 교육하도록 한다. 또한 기존의 과목과는 다른 전산학의 토픽을 발굴하고, 향후 정규 과목으로 발전할 수 있는 가능성을 입증할 수 있도록 하는데 목적을 둔다.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '본 과목은 급변하는 전산학의 다양한 주제들을 새로운 방향으로 다루어, 학생들에게 최신 기술 발전 동향을 교육하도록 한다. 또한 기존의 과목과는 다른 전산학의 토픽을 발굴하고, 향후 정규 과목으로 발전할 수 있는 가능성을 입증할 수 있도록 하는데 목적을 둔다.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60000 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60000';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60000', NULL, 'This course is intended as a first course in graph theory. It covers the basic theory and applications of trees, networks, Euler graphs, Hamiltonian graphs, matchings, colorings, planar graphs, and network flow.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course is intended as a first course in graph theory. It covers the basic theory and applications of trees, networks, Euler graphs, Hamiltonian graphs, matchings, colorings, planar graphs, and network flow.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60102 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60102';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60102', NULL, 'This course is intended for graduate students. This course introduces the fundamentals of social network aware ubiquitous computing. The first half of the course focuses on the main components of ubiquitous computing and social networking. The core concepts of social network aware ubiquitous computing will be explained by analysis of and discussion on existing approaches. Students will be asked to participate in prototyping of a social network aware ubiquitous computing application and/or system.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course is intended for graduate students. This course introduces the fundamentals of social network aware ubiquitous computing. The first half of the course focuses on the main components of ubiquitous computing and social networking. The core concepts of social network aware ubiquitous computing will be explained by analysis of and discussion on existing approaches. Students will be asked to participate in prototyping of a social network aware ubiquitous computing application and/or system.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60200 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60200';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60200', NULL, 'This course''s goal is to expose students to some research issues in modern programming language implementation. Topics include conventional data-flow analysis techniques, semantics-based flow analysis, type inference, type-based program analysis, and garbage collection.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course''s goal is to expose students to some research issues in modern programming language implementation. Topics include conventional data-flow analysis techniques, semantics-based flow analysis, type inference, type-based program analysis, and garbage collection.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60304 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60304';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60304', NULL, 'This course aims to provide 1) broad understanding on real-time systems, 2) in-depth knowledge on real-time scheduling theories, and 3) hands-on experience on real-time operating systems. In particular, it will deal with real-time issues on smartphone operating systems.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course aims to provide 1) broad understanding on real-time systems, 2) in-depth knowledge on real-time scheduling theories, and 3) hands-on experience on real-time operating systems. In particular, it will deal with real-time issues on smartphone operating systems.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60306 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60306';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60306', NULL, 'This course provides a studio-oriented eduction for designing and prototyping UX-oriented SW platforms. Based on user study and creative concept development method, students will learn to extract system requirements, design a platform, and implement the proposed system. This course will emphasize design and implementation aspects for user-oriented SW systems, in addition to basic theoretical aspects for creative concept.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course provides a studio-oriented eduction for designing and prototyping UX-oriented SW platforms. Based on user study and creative concept development method, students will learn to extract system requirements, design a platform, and implement the proposed system. This course will emphasize design and implementation aspects for user-oriented SW systems, in addition to basic theoretical aspects for creative concept.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60404 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60404';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60404', NULL, 'This course serves to provide a more complete understanding of network architecture. In particular, these topics are discussed: internet architecture, architecture components, and architectural implication of new technologies and non-technical issues. The course is composed of lectures, invited presentations and term projects.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course serves to provide a more complete understanding of network architecture. In particular, these topics are discussed: internet architecture, architecture components, and architectural implication of new technologies and non-technical issues. The course is composed of lectures, invited presentations and term projects.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60406 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60406';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60406', NULL, 'In this course, the technology related with the contents security is studied. Various security issues of the multimedia including image, video and audio are covered.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this course, the technology related with the contents security is studied. Various security issues of the multimedia including image, video and audio are covered.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60500 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60500';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60500', NULL, 'In this course, the fundamental concepts of object-orientation are covered from requirement analysis to implementation with various object-oriented methods including OMT, Booch method, and UML. In addition, several advanced topics in the field of object-orientation are also covered. These advanced topics include parallel and distributed object system, real-time issues, and so on.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this course, the fundamental concepts of object-orientation are covered from requirement analysis to implementation with various object-oriented methods including OMT, Booch method, and UML. In addition, several advanced topics in the field of object-orientation are also covered. These advanced topics include parallel and distributed object system, real-time issues, and so on.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60502 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60502';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60502', NULL, 'In contrast that traditional software engineering has been focussed on single systems, software & systems product line (SSPL) is applicable to family of software systems and embedded systems. Students will understand the SSPL paradigms and will learn how to realize & evaluate SSPL. The key knowledge areas in this course include reference model, scoping, commonality, variability, domain and application engineering.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In contrast that traditional software engineering has been focussed on single systems, software & systems product line (SSPL) is applicable to family of software systems and embedded systems. Students will understand the SSPL paradigms and will learn how to realize & evaluate SSPL. The key knowledge areas in this course include reference model, scoping, commonality, variability, domain and application engineering.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60504 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60504';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60504', NULL, 'Software process is an important leverage point from which to address software quality and productivity issues. Students will learn theoretical foundations on software process, the methods of defining process, and how to apply the process concepts to improve software quality and productivity.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Software process is an important leverage point from which to address software quality and productivity issues. Students will learn theoretical foundations on software process, the methods of defining process, and how to apply the process concepts to improve software quality and productivity.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60505 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60505';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60505', NULL, 'Today''s information systems are getting more complex, and need for automation systems is ever increasing. In this course we address basic modelling methods in system analysis and study static and dynamic analysis of systems using Petri Nets.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Today''s information systems are getting more complex, and need for automation systems is ever increasing. In this course we address basic modelling methods in system analysis and study static and dynamic analysis of systems using Petri Nets.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60506 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60506';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60506', NULL, 'The primary objectives of this course are to enable the students to understand the fundamental principles underlying software management and economics; to analyze management situations via case studies; to analyze software cost/schedule tradeoff issues via software cost estimation tools and microeconomic techniques; and to apply the principles and techniques to practical situations', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The primary objectives of this course are to enable the students to understand the fundamental principles underlying software management and economics; to analyze management situations via case studies; to analyze software cost/schedule tradeoff issues via software cost estimation tools and microeconomic techniques; and to apply the principles and techniques to practical situations', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60600 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60600';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60600', NULL, 'This course covers content analysis and indexing, file organization and record classification for information storage, query formulation, retrieval models, search or selection process, and application systems on question-answering systems, on-line information services, library automation, and other information systems.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers content analysis and indexing, file organization and record classification for information storage, query formulation, retrieval models, search or selection process, and application systems on question-answering systems, on-line information services, library automation, and other information systems.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60602 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60602';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60602', NULL, 'The goal of this course is to study the theory, algorithms and methods that underlie distributed database management systems.', 3, 'graduate', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to study the theory, algorithms and methods that underlie distributed database management systems.', credits = 3, division = 'graduate', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60604 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60604';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60604', NULL, 'The goal of this course is to study the formal foundation of database systems. The course covers advanced topics such as deductive databases, relational database theory, fixed point theory, stratified negation, closed-world assumption, safety, multivalved dependency, generalized dependency and crash recovery.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to study the formal foundation of database systems. The course covers advanced topics such as deductive databases, relational database theory, fixed point theory, stratified negation, closed-world assumption, safety, multivalved dependency, generalized dependency and crash recovery.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60605 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60605';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60605', NULL, 'Mining big data helps us find useful patterns and anomalies which lead to high impact applications including fraud detection, recommendation system, cyber security, etc. This course covers advanced algorithms for mining big data.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Mining big data helps us find useful patterns and anomalies which lead to high impact applications including fraud detection, recommendation system, cyber security, etc. This course covers advanced algorithms for mining big data.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60700 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60700';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60700', NULL, 'The aim of this course is to introduce basic concepts and knowledge of the fuzzy theory and its applications. This course also covers some important intelligent systems including the neural network model and genetic algorithm, and the fusion of the different techniques will be discussed.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The aim of this course is to introduce basic concepts and knowledge of the fuzzy theory and its applications. This course also covers some important intelligent systems including the neural network model and genetic algorithm, and the fusion of the different techniques will be discussed.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60701 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60701';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60701', NULL, 'This course will cover advanced and state-of-the-art machine learning such as graphical models, Bayesian inference, and nonparametric models.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course will cover advanced and state-of-the-art machine learning such as graphical models, Bayesian inference, and nonparametric models.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60702 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60702';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60702', NULL, 'This course covers reinforcement learning, which is one of the core research areas in machine learning and artificial intelligence. Reinforcement learning has various applications, such as robot navigation/control, intelligent user interfaces, and network routing. Students will be able to understand the fundamental concepts, and capture the recent research trends.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers reinforcement learning, which is one of the core research areas in machine learning and artificial intelligence. Reinforcement learning has various applications, such as robot navigation/control, intelligent user interfaces, and network routing. Students will be able to understand the fundamental concepts, and capture the recent research trends.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60704 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60704';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60704', NULL, 'The goal of this course is to provide students with current topics in natural language processing (NLP). Students are expected to get acquainted with various leading-edge ideas and techniques in NLP.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to provide students with current topics in natural language processing (NLP). Students are expected to get acquainted with various leading-edge ideas and techniques in NLP.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60706 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60706';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60706', NULL, 'Through this course, students are expected to acquire general ideas of pattern recognition and its application. Three fields (character, speech and image processing) will be studied in which pattern recognition techniques can be successfully applied.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Through this course, students are expected to acquire general ideas of pattern recognition and its application. Three fields (character, speech and image processing) will be studied in which pattern recognition techniques can be successfully applied.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60800 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60800';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60800', NULL, 'In this class we will discuss various advanced computer graphics, virtual reality, and interaction techniques. More specifically, we will look into rendering, visibility culling, multi-resolution, cache-coherent methods, and data compression techniques for rasterization, global illumination and collision detection.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this class we will discuss various advanced computer graphics, virtual reality, and interaction techniques. More specifically, we will look into rendering, visibility culling, multi-resolution, cache-coherent methods, and data compression techniques for rasterization, global illumination and collision detection.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60801 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60801';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60801', NULL, 'This course provides an introduction to color in computer graphics, with an in-depth look at two fundamental topics: digital color imaging techniques and numerical visual perception models. Students will work on an individual project on color of their choice.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course provides an introduction to color in computer graphics, with an in-depth look at two fundamental topics: digital color imaging techniques and numerical visual perception models. Students will work on an individual project on color of their choice.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.60802 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.60802';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.60802', NULL, 'The need for a computational approach to storytelling is growing due to the digitalization of all media types - text, image, and sound. Regardless of media types, the story forms the underlying deep structure. This course is concerned with computational aspects of storytelling: building a computational model for storytelling, narrative design, and applications of the computational model to the Web, games, e-books, and animation. Students are expected to build a coherent perspective on designing, implementing, and analyzing digital media.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The need for a computational approach to storytelling is growing due to the digitalization of all media types - text, image, and sound. Regardless of media types, the story forms the underlying deep structure. This course is concerned with computational aspects of storytelling: building a computational model for storytelling, narrative design, and applications of the computational model to the Web, games, e-books, and animation. Students are expected to build a coherent perspective on designing, implementing, and analyzing digital media.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.70900 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.70900';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.70900', NULL, 'The ability to communicate about technical matters is critical for IT professionals. The purpose of this course is to develop the student''s technical communication skills, primarily in writing, but also in oral communication. Students practice the skills necessary for writing technical papers. Through active discussions and reviews, students work on their ability to convey technical ideas in a concise and well-organized manner.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The ability to communicate about technical matters is critical for IT professionals. The purpose of this course is to develop the student''s technical communication skills, primarily in writing, but also in oral communication. Students practice the skills necessary for writing technical papers. Through active discussions and reviews, students work on their ability to convey technical ideas in a concise and well-organized manner.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79900 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79900';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79900', NULL, 'Students study recent papers or books in the area of Theory of Computation.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Students study recent papers or books in the area of Theory of Computation.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79901 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79901';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79901', NULL, 'This course covers recently developed, new computer architectures. Students study and analyze new computational models, high-level languages, computer architectures etc.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers recently developed, new computer architectures. Students study and analyze new computational models, high-level languages, computer architectures etc.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79902 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79902';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79902', NULL, 'In this course, students study parallel processing architectures, algorithms, and languages, especially their use in 5th generation computers. The course is based on recent papers, and can be seen as a continuation of Parallel Processing (CS610).', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this course, students study parallel processing architectures, algorithms, and languages, especially their use in 5th generation computers. The course is based on recent papers, and can be seen as a continuation of Parallel Processing (CS610).', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79904 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79904';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79904', NULL, 'This course covers recent research topics related to programming languages, such as theory, new paradigms, programming language design & implementation etc.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers recent research topics related to programming languages, such as theory, new paradigms, programming language design & implementation etc.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79905 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79905';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79905', NULL, 'The goal of this course is to develop abilities related to role and performance of operating systems. Students study and debate topics such as designing and implementing a new operating systems for a new environment, utilizing an existing operating systems effectively, OS architecture, ways of evaluating OS performance, file systems, threads, parallel operating systems, etc.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to develop abilities related to role and performance of operating systems. Students study and debate topics such as designing and implementing a new operating systems for a new environment, utilizing an existing operating systems effectively, OS architecture, ways of evaluating OS performance, file systems, threads, parallel operating systems, etc.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79906 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79906';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79906', NULL, 'In this course, students learn about the structure of computer systems through individual projects and experiments related to user interfaces and object-oriented architectures.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this course, students learn about the structure of computer systems through individual projects and experiments related to user interfaces and object-oriented architectures.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79907 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79907';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79907', NULL, 'The goal of this course is to discuss with the research trends and hot issues on information security and suggest the best security practices on new emerging IT services or systems as the security expertise.', 3, 'graduate', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to discuss with the research trends and hot issues on information security and suggest the best security practices on new emerging IT services or systems as the security expertise.', credits = 3, division = 'graduate', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79908 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79908';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79908', NULL, 'Students study advanced topics in software engineering, such as formal specification, reuse, software development environments, theory of testing, proving program correctness, etc.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Students study advanced topics in software engineering, such as formal specification, reuse, software development environments, theory of testing, proving program correctness, etc.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79909 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79909';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79909', NULL, 'In this course, students study and discuss recent developments and topics in database systems.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this course, students study and discuss recent developments and topics in database systems.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79910 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79910';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79910', NULL, 'This course consists of lectures about major topics related to computer vision, seminars, and projects. Recent major topics are motion detection and analysis, parallel computer vision systems, CAD-based 3-D vision, knowledge-based vision, neural network-based vision, etc.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course consists of lectures about major topics related to computer vision, seminars, and projects. Recent major topics are motion detection and analysis, parallel computer vision systems, CAD-based 3-D vision, knowledge-based vision, neural network-based vision, etc.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79911 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79911';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79911', NULL, 'This course covers the theory of natural language processing and recent developments in practice. Students study the theory of language, parsing, situational semantics, belief models etc. They practice by designing and developing utilities and systems.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers the theory of natural language processing and recent developments in practice. Students study the theory of language, parsing, situational semantics, belief models etc. They practice by designing and developing utilities and systems.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79912 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79912';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79912', NULL, 'The goal of this course is to provide students with recent theory of AI and its application. It covers information representation. heuristic search, logic and logic language, robot planning, AI languages, expert system, distributed AI system, uncertainty problem and so on.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to provide students with recent theory of AI and its application. It covers information representation. heuristic search, logic and logic language, robot planning, AI languages, expert system, distributed AI system, uncertainty problem and so on.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79913 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79913';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79913', NULL, 'This course defines humans'' cognitive ability, and then studies a variety of methodologies by which cognitive psychology, artificial intelligence, computer science, linguistics, and philosophy apply this ability to machines. This course focuses on ''neural networks'' as a computational model of the brain and as a method for approaching fields that computers cannot solve efficiently, such as pattern recognition, voice recognition and natural language processing.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course defines humans'' cognitive ability, and then studies a variety of methodologies by which cognitive psychology, artificial intelligence, computer science, linguistics, and philosophy apply this ability to machines. This course focuses on ''neural networks'' as a computational model of the brain and as a method for approaching fields that computers cannot solve efficiently, such as pattern recognition, voice recognition and natural language processing.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79915 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79915';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79915', NULL, 'This course covers advanced topics of computer graphics such as modeling geometric objects, rendering and processing three-dimensional objects, and manipulating motion. The course surveys and analyzes recent results, and discusses the research focus for the future.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers advanced topics of computer graphics such as modeling geometric objects, rendering and processing three-dimensional objects, and manipulating motion. The course surveys and analyzes recent results, and discusses the research focus for the future.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.79917 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.79917';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.79917', NULL, 'This course focuses on technical problems in the interaction between humans and computers. Human-Computer interaction (HCI) is related to somatology, sociology, psychology as well as software and hardware. Through this course, students survey and analyze recent research tendencies, and discuss the future developments.', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course focuses on technical problems in the interaction between humans and computers. Human-Computer interaction (HCI) is related to somatology, sociology, psychology as well as software and hardware. Through this course, students survey and analyze recent research tendencies, and discuss the future developments.', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.89900 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.89900';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.89900', NULL, '', 1, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 1, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.89901 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.89901';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.89901', NULL, '', 2, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 2, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.89902 (일반선택)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.89902';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.89902', NULL, '', 3, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 3, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'GENERAL_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'GENERAL_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.91200 (연구)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.91200';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.91200', NULL, '', 0, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 0, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'RESEARCH';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'RESEARCH';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.92100 (연구)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.92100';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.92100', NULL, '', 0, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 0, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'RESEARCH';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'RESEARCH';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.92200 (연구)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.92200';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.92200', NULL, '', 0, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 0, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'RESEARCH';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'RESEARCH';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.93100 (연구)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.93100';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.93100', NULL, '', 1, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 1, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'RESEARCH';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'RESEARCH';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.93200 (연구)
DO $$
DECLARE
  v_dept_id BIGINT;
  v_course_id BIGINT;
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_dept_id FROM departments WHERE department_code = 'CS';
  IF v_dept_id IS NULL THEN
    RAISE EXCEPTION 'Department % not found in departments table', 'CS';
  END IF;
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.93200';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.93200', NULL, '', 1, 'graduate', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 1, division = 'graduate', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'RESEARCH';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'RESEARCH';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

COMMIT;
