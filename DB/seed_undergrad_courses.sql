BEGIN;

-- Ensure required course_types exist
DO $$
DECLARE
  v_type_id BIGINT;
BEGIN
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'BASIC_ELECTIVE';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'BASIC_ELECTIVE');
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'BASIC_REQUIRED';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'BASIC_REQUIRED');
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'MAJOR_ELECTIVE');
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_REQUIRED';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'MAJOR_REQUIRED');
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'RESEARCH';
  IF v_type_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE_TYPE') RETURNING node_id INTO v_type_id;
    INSERT INTO course_types (node_id, type_name) VALUES (v_type_id, 'RESEARCH');
  END IF;
END$$;

-- CS.10001 (기초필수)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.10001';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.10001', NULL, 'The course teaches the basic technique of computer programming and the basic knowledge in the computer structure, and use of the elective programming language to resolve given problems in structural programming. Based on the elective programming language, it teaches the data structure, input and output, flow control and incidental program, and by using the systematic division of problem solution and concept of module to solve the problems in numerical value field and non-numerical value field with the program experiment.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The course teaches the basic technique of computer programming and the basic knowledge in the computer structure, and use of the elective programming language to resolve given problems in structural programming. Based on the elective programming language, it teaches the data structure, input and output, flow control and incidental program, and by using the systematic division of problem solution and concept of module to solve the problems in numerical value field and non-numerical value field with the program experiment.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'BASIC_REQUIRED';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'BASIC_REQUIRED';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.10009 (기초선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.10009';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.10009', NULL, 'In this course students who have taken CS101 but who have otherwise little programming experience can develop their programming skills. The course introduces basic concepts of programming and computer science, such as dynamic and static typing, dynamic memory allocation, objects and methods, binary representation of numbers, using an editor and compiler from the command line, running programs with arguments from the commmand line, graphical user interfaces and event-based programming, using libraries, and the use of basic data structures such as arrays, lists, stacks, sets, and maps.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this course students who have taken CS101 but who have otherwise little programming experience can develop their programming skills. The course introduces basic concepts of programming and computer science, such as dynamic and static typing, dynamic memory allocation, objects and methods, binary representation of numbers, using an editor and compiler from the command line, running programs with arguments from the commmand line, graphical user interfaces and event-based programming, using libraries, and the use of basic data structures such as arrays, lists, stacks, sets, and maps.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'BASIC_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'BASIC_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.20002 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.20002';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.20002', NULL, 'This course is about methods for problem solving and algorithm development. Through various lab work, students learn good programming practice in design, coding, debugging, and documentation.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course is about methods for problem solving and algorithm development. Through various lab work, students learn good programming practice in design, coding, debugging, and documentation.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.20101 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.20101';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.20101', NULL, 'This course provides students with an understanding of digital systems as building blocks of modern digital computers. This course puts emphasis on providing students with hands-on experience on digital systems. The course includes both lecture and laboratory work on the topics of: boolean algebra, binary system, combinatorial logic, asynchronous sequential circuits, algorithmic state machine, asynchronous sequential circuits, VHDL, CAD tools and FPGAs.', 4, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course provides students with an understanding of digital systems as building blocks of modern digital computers. This course puts emphasis on providing students with hands-on experience on digital systems. The course includes both lecture and laboratory work on the topics of: boolean algebra, binary system, combinatorial logic, asynchronous sequential circuits, algorithmic state machine, asynchronous sequential circuits, VHDL, CAD tools and FPGAs.', credits = 4, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.20200 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.20200';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.20200', NULL, 'This course''s goal is to provide students with programming principles and a good feel for the elements of style and the aesthetics of programming, which are necessary in controlling the intellectual complexity of large yet robust software systems. The covered topics include: induction and recursion, data abstraction and representation, values and applicative programming, objects and imperative programming, streams and demand-driven programming, modularity and hierarchy, exceptions and advanced control, and higher-order functions and continuations.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course''s goal is to provide students with programming principles and a good feel for the elements of style and the aesthetics of programming, which are necessary in controlling the intellectual complexity of large yet robust software systems. The covered topics include: induction and recursion, data abstraction and representation, values and applicative programming, objects and imperative programming, streams and demand-driven programming, modularity and hierarchy, exceptions and advanced control, and higher-order functions and continuations.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.20300 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.20300';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.20300', NULL, 'This course''s goal is to provide students with programming techniques necessary in dealing with "systems" development. The covered topics include low-level machine oriented programming, device-control programming, and other various programming techniques for computer operating environment.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course''s goal is to provide students with programming techniques necessary in dealing with "systems" development. The covered topics include low-level machine oriented programming, device-control programming, and other various programming techniques for computer operating environment.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.20700 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.20700';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.20700', NULL, 'This course aims to provide an opportunity for sophomores to experience creative system design using Lego mindstorm NXT kit and URBI robot software platform. In lectures, robotic CS is introduced and various examples are demonstrated to bring out students'' interests. In lab hours, students build own intelligent robot system creatively. Students are educated to integrate hardware and software designs, and make presentations at the end of semester.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course aims to provide an opportunity for sophomores to experience creative system design using Lego mindstorm NXT kit and URBI robot software platform. In lectures, robotic CS is introduced and various examples are demonstrated to bring out students'' interests. In lab hours, students build own intelligent robot system creatively. Students are educated to integrate hardware and software designs, and make presentations at the end of semester.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30100 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30100';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30100', NULL, 'Embedded systems are found everywhere. The goal of this course is to develop a comprehensive understanding of the technologies behind the embedded computer systems, including hardware and software components. Students will gain hands-on experience in designing a embedded system using CAD tools and FPGAs. (Prerequisite: CS211)', 4, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Embedded systems are found everywhere. The goal of this course is to develop a comprehensive understanding of the technologies behind the embedded computer systems, including hardware and software components. Students will gain hands-on experience in designing a embedded system using CAD tools and FPGAs. (Prerequisite: CS211)', credits = 4, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30202 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30202';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30202', NULL, 'This course covers various types of finite automata, properties of language classes recognizable by automata, context-free grammar, pushdown automata, the Turing machine, and computability. (Prerequisite: CS204)', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers various types of finite automata, properties of language classes recognizable by automata, context-free grammar, pushdown automata, the Turing machine, and computability. (Prerequisite: CS204)', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30401 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30401';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30401', NULL, 'The goal of this course is to provide students with sound understanding of fundamental concepts and problems in networking and to train them in network programming. We begin with an introduction to key applications in today''s Internet and then cover the reliable transfer protocol, TCP, and its congestion control; and the IP layer that covers the diversity in physical layer technologies and provides an end-to-end abstraction. Finally, we include key concepts in multimedia networking and security in communication networks. (Prerequisite: CS230)', 4, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to provide students with sound understanding of fundamental concepts and problems in networking and to train them in network programming. We begin with an introduction to key applications in today''s Internet and then cover the reliable transfer protocol, TCP, and its congestion control; and the IP layer that covers the diversity in physical layer technologies and provides an end-to-end abstraction. Finally, we include key concepts in multimedia networking and security in communication networks. (Prerequisite: CS230)', credits = 4, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30408 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30408';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30408', NULL, 'This course covers the overall contents of information security. Students will be exposed to fundamental concepts in information security including cryptography, system security, software security, web security and network security. This course introduces how security attacks occur in the modern computing environments. Students will also have opportunities to understand techniques to discover and disable such security attacks.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers the overall contents of information security. Students will be exposed to fundamental concepts in information security including cryptography, system security, software security, web security and network security. This course introduces how security attacks occur in the modern computing environments. Students will also have opportunities to understand techniques to discover and disable such security attacks.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30500 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30500';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30500', NULL, 'This course provides students with basic concepts in software engineering in order to develop high-quality software economically. Key concepts are life cycle models, development techniques, automation tools, project management skills, and software metrics.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course provides students with basic concepts in software engineering in order to develop high-quality software economically. Key concepts are life cycle models, development techniques, automation tools, project management skills, and software metrics.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30600 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30600';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30600', NULL, 'This is an introductory-level course to database systems. Students learn about various models, such as E-R models, relational models, and object-oriented models; query languages such as SQL, relational calculus, and QBE; and file and indexing systems for data storage. Advanced topics, such as data inheritance, database design issues using functional and multivalued dependencies, database security, and access rights, are also covered. (Prerequisite: CS206)', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This is an introductory-level course to database systems. Students learn about various models, such as E-R models, relational models, and object-oriented models; query languages such as SQL, relational calculus, and QBE; and file and indexing systems for data storage. Advanced topics, such as data inheritance, database design issues using functional and multivalued dependencies, database security, and access rights, are also covered. (Prerequisite: CS206)', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30601 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30601';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30601', NULL, 'Data science is an inter-disciplinary field focused on extracting knowledge from typically large data sets. This course aims at teaching basic skills in data science for undergraduate students. It covers basic probability and statistics theories required for data science; exploratory data analysis (EDA) required for understanding a given data set; and predictive analysis based on statistical or machine learning techniques. Additionally, it discusses recent big data processing techniques and various data science applications. The students will learn how to implement the methodologies using the Python language.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Data science is an inter-disciplinary field focused on extracting knowledge from typically large data sets. This course aims at teaching basic skills in data science for undergraduate students. It covers basic probability and statistics theories required for data science; exploratory data analysis (EDA) required for understanding a given data set; and predictive analysis based on statistical or machine learning techniques. Additionally, it discusses recent big data processing techniques and various data science applications. The students will learn how to implement the methodologies using the Python language.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30700 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30700';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30700', NULL, 'Students learn LISP and PROLOG, the two most commonly used programming languages in artificial intelligence. The basic programming concepts, grammar, and symbol manipulation are covered in the course. Using intelligent problem solving methods, students build natural language processing systems, database programs, pattern matching programs, learning programs, expert systems, etc.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Students learn LISP and PROLOG, the two most commonly used programming languages in artificial intelligence. The basic programming concepts, grammar, and symbol manipulation are covered in the course. Using intelligent problem solving methods, students build natural language processing systems, database programs, pattern matching programs, learning programs, expert systems, etc.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30701 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30701';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30701', NULL, 'This is an undergraduate-level introductory course for deep learning. There have been enormous advances in the field of artificial intelligence over the past few decades, especially based on deep learning. However, it is not easy to see what frontiers the current deep learning is facing and what underlying methods are used to enable these advances. This course aims to provide an overview of traditional/emerging topics and applications in deep learning, and basic skill sets to understand/implement some of the latest algorithms.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This is an undergraduate-level introductory course for deep learning. There have been enormous advances in the field of artificial intelligence over the past few decades, especially based on deep learning. However, it is not easy to see what frontiers the current deep learning is facing and what underlying methods are used to enable these advances. This course aims to provide an overview of traditional/emerging topics and applications in deep learning, and basic skill sets to understand/implement some of the latest algorithms.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30702 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30702';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30702', NULL, 'The course offers students a practical introduction to natural language processing with the Python programming language, helping the students to learn by example, write real programs, and grasp the value of being able to test an idea through implementation, with an extensive collection of linguistic algorithms and data structures in robust language processing software.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The course offers students a practical introduction to natural language processing with the Python programming language, helping the students to learn by example, write real programs, and grasp the value of being able to test an idea through implementation, with an extensive collection of linguistic algorithms and data structures in robust language processing software.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30704 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30704';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30704', NULL, 'This course introduces fundamental concepts, theories, and methods for designing, prototyping, implementing, and evaluating user interfaces. Students apply these lessons to a practical problem in a team project, which follows a user-centered design process.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course introduces fundamental concepts, theories, and methods for designing, prototyping, implementing, and evaluating user interfaces. Students apply these lessons to a practical problem in a team project, which follows a user-centered design process.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30706 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30706';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30706', NULL, 'Machine learning, a sub-field of computer science, has been popular with the era of intelligent softwares and attracted huge attentions from computer vision, natural language processing, healthcare and finance communities to name a few. In this introductory course, we will cover various basic topics in the area including some recent supervised and unsupervised learning algorithms.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Machine learning, a sub-field of computer science, has been popular with the era of intelligent softwares and attracted huge attentions from computer vision, natural language processing, healthcare and finance communities to name a few. In this introductory course, we will cover various basic topics in the area including some recent supervised and unsupervised learning algorithms.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30707 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30707';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30707', NULL, 'This course introduces the fundamental concepts of reinforcement learning and the basic principles of deep reinforcement learning, which combines these concepts with deep neural networks. Students will learn key algorithms such as Q-learning, Policy Gradient, and Actor-Critic, and explore advanced deep reinforcement learning techniques like DQN, A3C, and PPO. The course places a strong emphasis on programming and project-based practice, particularly in applying reinforcement learning to real-world problems. Additionally, the course provides a brief overview of the major challenges in reinforcement learning and discusses recent trends in the field.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course introduces the fundamental concepts of reinforcement learning and the basic principles of deep reinforcement learning, which combines these concepts with deep neural networks. Students will learn key algorithms such as Q-learning, Policy Gradient, and Actor-Critic, and explore advanced deep reinforcement learning techniques like DQN, A3C, and PPO. The course places a strong emphasis on programming and project-based practice, particularly in applying reinforcement learning to real-world problems. Additionally, the course provides a brief overview of the major challenges in reinforcement learning and discusses recent trends in the field.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30800 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30800';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30800', NULL, 'The goal of this course is for students to acquire theory and hands-on experience in computer graphics. Topics covered are: basic functions and principles of input and output devices used in computer graphics, architectures and features of graphics systems, basic geometric models and their generation algorithms, theories and practice behind 2D and 3D conversion. Basic ideas of hidden line and surface removal and color models are introduced.', 4, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is for students to acquire theory and hands-on experience in computer graphics. Topics covered are: basic functions and principles of input and output devices used in computer graphics, architectures and features of graphics systems, basic geometric models and their generation algorithms, theories and practice behind 2D and 3D conversion. Basic ideas of hidden line and surface removal and color models are introduced.', credits = 4, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40002 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40002';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40002', NULL, 'This course is about basics of logic used in computer programming. Topics covered in this course are: propositional calculus, predicate calculus, axiomatic theories, skolemization, unification, and resolution.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course is about basics of logic used in computer programming. Topics covered in this course are: propositional calculus, predicate calculus, axiomatic theories, skolemization, unification, and resolution.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40006 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40006';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40006', NULL, 'The main interest for computer scientist is how to compute a solution of the given problem with limited computation resources. This constraint leads to a unique set of mathematical tools for computer scientists. Hence I would like to introduce a class which conveys mathematical tools and their underlying concepts suitable for computer scientists in general.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The main interest for computer scientist is how to compute a solution of the given problem with limited computation resources. This constraint leads to a unique set of mathematical tools for computer scientists. Hence I would like to introduce a class which conveys mathematical tools and their underlying concepts suitable for computer scientists in general.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40008 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40008';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40008', NULL, 'Students learn project management and large-system programming skills that are not usually covered in any single course. Students form teams, and execute one of project ideas suggested by a professor. The scope of the project must cover multiple areas in computer science and be of a magnitude sufficient for a team project.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Students learn project management and large-system programming skills that are not usually covered in any single course. Students form teams, and execute one of project ideas suggested by a professor. The scope of the project must cover multiple areas in computer science and be of a magnitude sufficient for a team project.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40009 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40009';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40009', NULL, 'This course aims to help students internalize project-based competencies that are essentially needed in the software industries. First of all, they get to figure out the fundamentals and philosophies of software engineering through panel discussions with the reading list. Also, they are asked to be organized into teams with mentors from the industry companies, and to conduct their own software project based on the infrastructures and tools that are really used in the field, minimizing the gap between academia and practitioners.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course aims to help students internalize project-based competencies that are essentially needed in the software industries. First of all, they get to figure out the fundamentals and philosophies of software engineering through panel discussions with the reading list. Also, they are asked to be organized into teams with mentors from the industry companies, and to conduct their own software project based on the infrastructures and tools that are really used in the field, minimizing the gap between academia and practitioners.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40101 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40101';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40101', NULL, 'Tremendous success of Artificial Intelligence (AI) can be attributed to two primary reasons: (1) significant advances in ML algorithms with great emphasis on Deep Learning, and (2) high-performance computing mainly fueled by hardware accelerators such as GPU and specialized software systems. This course focuses on the second reason and look at AI in the system perspective. This course will look into the entire computing stack built solely for AI, particularly Machine Learning and Deep Learning, This stack constitutes domain-specific programming interface and platforms (e.g., Tensorflow), DNN compilers (e.g., TVM), and hardware accelerators (e.g., GPU and TPU).', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Tremendous success of Artificial Intelligence (AI) can be attributed to two primary reasons: (1) significant advances in ML algorithms with great emphasis on Deep Learning, and (2) high-performance computing mainly fueled by hardware accelerators such as GPU and specialized software systems. This course focuses on the second reason and look at AI in the system perspective. This course will look into the entire computing stack built solely for AI, particularly Machine Learning and Deep Learning, This stack constitutes domain-specific programming interface and platforms (e.g., Tensorflow), DNN compilers (e.g., TVM), and hardware accelerators (e.g., GPU and TPU).', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40200 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40200';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40200', NULL, 'Through this course, students study basic rules and implementation considerations in implementing a programming language. More details on grammar checks for program syntax, implementation optimization, relations between programming languages and compilers, the role of interpreters, run-time systems, and semantically accurate expressions are also covered.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Through this course, students study basic rules and implementation considerations in implementing a programming language. More details on grammar checks for program syntax, implementation optimization, relations between programming languages and compilers, the role of interpreters, run-time systems, and semantically accurate expressions are also covered.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40202 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40202';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40202', NULL, 'This course deals with models of computation, computable and incomputable functions, temporal and spatial complexities, tractable and intractable functions.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course deals with models of computation, computable and incomputable functions, temporal and spatial complexities, tractable and intractable functions.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40203 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40203';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40203', NULL, 'The course aims at teaching students techniques from machine learning and programming languages that enable the design and implementation of a programming language for easily writing advanced probabilistic models from machine learning. We will cover a wide range of general-purpose algorithms for probabilistic inference, and discuss how these algorithms can be used to build programming languages and systems for developing models from machine learning. We will also study a mathematical foundation of those languages using tools from measure-theoretic probability theory.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The course aims at teaching students techniques from machine learning and programming languages that enable the design and implementation of a programming language for easily writing advanced probabilistic models from machine learning. We will cover a wide range of general-purpose algorithms for probabilistic inference, and discuss how these algorithms can be used to build programming languages and systems for developing models from machine learning. We will also study a mathematical foundation of those languages using tools from measure-theoretic probability theory.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40204 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40204';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40204', NULL, 'This course covers both theoretical principles and practical applications for ensuring the safety and reliability of software. It first delves into fundamental programming language theory and logic. Based on this foundation, it explores techniques such as “program verification” which automatically checks whether a given program meets specified conditions, and “program synthesis”, which automatically generates programs that meet given conditions.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers both theoretical principles and practical applications for ensuring the safety and reliability of software. It first delves into fundamental programming language theory and logic. Based on this foundation, it explores techniques such as “program verification” which automatically checks whether a given program meets specified conditions, and “program synthesis”, which automatically generates programs that meet given conditions.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40301 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40301';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40301', NULL, 'This course teaches concurrent programming techniques for efficiently controlling parallel resources in order to maximize performance, and verification techniques for such programs. In old days, sequential processing was default while parallel processing was exceptional; nowadays, the other way around. Such tendancy is accelerated by the advent of big data processing. This course aims to help students acculumate a grounding in efficient control of parallel resources with theory and programming practices.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course teaches concurrent programming techniques for efficiently controlling parallel resources in order to maximize performance, and verification techniques for such programs. In old days, sequential processing was default while parallel processing was exceptional; nowadays, the other way around. Such tendancy is accelerated by the advent of big data processing. This course aims to help students acculumate a grounding in efficient control of parallel resources with theory and programming practices.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40400 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40400';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40400', NULL, 'This course covers basic principles in data communications, such as LAN, WAN, multimedia (e.g., voice and video) transmission. It introduces students to key elements and concepts in network construction. Compared to CS441, emphasis is placed on lower layer protocols and network topologies.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers basic principles in data communications, such as LAN, WAN, multimedia (e.g., voice and video) transmission. It introduces students to key elements and concepts in network construction. Compared to CS441, emphasis is placed on lower layer protocols and network topologies.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40402 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40402';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40402', NULL, 'We cover fundamental concepts and problems in mobile and wireless networking and teach system design and implementation in mobile computing. Topics we cover are: introduction to data communications, CDMA, WiFi, and WiBro/WiMAX. Issues related to mobile computing platforms as well as systems comprising sensor networks are also covered. The term project involves application design and development for mobile computing.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'We cover fundamental concepts and problems in mobile and wireless networking and teach system design and implementation in mobile computing. Topics we cover are: introduction to data communications, CDMA, WiFi, and WiBro/WiMAX. Issues related to mobile computing platforms as well as systems comprising sensor networks are also covered. The term project involves application design and development for mobile computing.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40403 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40403';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40403', NULL, 'The goal of this course is to provide students with theoretical basis of distributed system design and hands-on experience with distributed systems. The course will start with introduction to functional programming, and then proceed to the MapReduce-like cloud computing framework. Then we expose students to distributed algorithms. Students learn how to program massively parallel jobs in a cloud computing environment and build theoretical underpinnings to expand MapReduce experience to a greater diversity of cloud computing applications. (Prerequisite: CS330, CS341)', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to provide students with theoretical basis of distributed system design and hands-on experience with distributed systems. The course will start with introduction to functional programming, and then proceed to the MapReduce-like cloud computing framework. Then we expose students to distributed algorithms. Students learn how to program massively parallel jobs in a cloud computing environment and build theoretical underpinnings to expand MapReduce experience to a greater diversity of cloud computing applications. (Prerequisite: CS330, CS341)', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40407 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40407';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40407', NULL, 'The course introduces web attacks that trigger various vulnerabilities in web services. It covers SQL injection, cross-site scripting, and cross-site request forgery, which constitute core web attacks, as well as same-origin policy. The course also provides a lab session for each week, which helps students practice actual attacks in a simulated web environment. The goal of the course is to let students learn and understand various web threats via conducting the covered attacks by themselves.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The course introduces web attacks that trigger various vulnerabilities in web services. It covers SQL injection, cross-site scripting, and cross-site request forgery, which constitute core web attacks, as well as same-origin policy. The course also provides a lab session for each week, which helps students practice actual attacks in a simulated web environment. The goal of the course is to let students learn and understand various web threats via conducting the covered attacks by themselves.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40503 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40503';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40503', NULL, 'This class covers basics of automated software testing techniques with regard to practical applications. These automated testing techniques can provide high reliability for complex embedded software compared to traditional testing methods in a more productive way. This class utilizes various automated software testing tools and learn about their underlying mechanisms for maximal benefit.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This class covers basics of automated software testing techniques with regard to practical applications. These automated testing techniques can provide high reliability for complex embedded software compared to traditional testing methods in a more productive way. This class utilizes various automated software testing tools and learn about their underlying mechanisms for maximal benefit.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40504 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40504';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40504', NULL, 'This course aims to introduce the operations and applications of metaheuristic and bio-inspired algorithms, including genetic algorithm, swarm optimization, and artificial immune system. By considering diverse problems ranging from combinatorial ones to performance improvement of complex software system, students are expected to learn how to apply computational intelligence to unseen problems.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course aims to introduce the operations and applications of metaheuristic and bio-inspired algorithms, including genetic algorithm, swarm optimization, and artificial immune system. By considering diverse problems ranging from combinatorial ones to performance improvement of complex software system, students are expected to learn how to apply computational intelligence to unseen problems.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40507 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40507';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40507', NULL, 'This course is designed to learn requirements engineering concepts and techniques for developing software systems in modern smart computing environments such as the World Wide Web, Internet of Things (IoT), and mobile computing environments. In this course, students learn the core concepts and techniques of software requirements engineering, the key characteristics of the Web, IoT and mobile computing environments, and practical methods to elicit, model, analyze and manage requirements for developing software systems in the modern computing environments.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course is designed to learn requirements engineering concepts and techniques for developing software systems in modern smart computing environments such as the World Wide Web, Internet of Things (IoT), and mobile computing environments. In this course, students learn the core concepts and techniques of software requirements engineering, the key characteristics of the Web, IoT and mobile computing environments, and practical methods to elicit, model, analyze and manage requirements for developing software systems in the modern computing environments.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40508 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40508';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40508', NULL, 'This class teaches automated SW testing technique s that analyze target source code to automatically generate various test inputs which explore diverse behaviors of a target program. This class guides students to use various open-source software testing tools and learn the underlying mechanisms of the tools to maximize the performance of automated testing.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This class teaches automated SW testing technique s that analyze target source code to automatically generate various test inputs which explore diverse behaviors of a target program. This class guides students to use various open-source software testing tools and learn the underlying mechanisms of the tools to maximize the performance of automated testing.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40509 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40509';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40509', NULL, 'This course is designed to learn technologies and strategies for modeling and building service oriented architecture and service applications in various computing environments such as Internet of Things, mobile computing and cloud computing environments to integrate various computing resources and capabilities in users’ point of views.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course is designed to learn technologies and strategies for modeling and building service oriented architecture and service applications in various computing environments such as Internet of Things, mobile computing and cloud computing environments to integrate various computing resources and capabilities in users’ point of views.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40700 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40700';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40700', NULL, 'This course introduces basic concepts and design techniques of artificial intelligence, and later deals with knowledge representation and inference techniques. Students are to design, implement, and train knowledge-based systems.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course introduces basic concepts and design techniques of artificial intelligence, and later deals with knowledge representation and inference techniques. Students are to design, implement, and train knowledge-based systems.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40701 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40701';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40701', NULL, 'Graphs are fundamental tools for modeling relationships between objects, enabling us to model diverse real-world problems and data. Graph machine learning and graph mining techniques are utilized in many modern AI and big data analytics domains. This course introduces various graph-based machine learning and mining techniques, including graph neural networks (applying deep learning ideas to graphs), knowledge graphs (representing human knowledge as graphs), graph representation learning (converting graphs into feature vectors), random walks and centrality measures on graphs, graph clustering, and graph anomaly detection. Also, this course introduces how these techniques are applied in information retrieval, natural language understanding, computer vision & graphics, robotics, and bioinformatics.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Graphs are fundamental tools for modeling relationships between objects, enabling us to model diverse real-world problems and data. Graph machine learning and graph mining techniques are utilized in many modern AI and big data analytics domains. This course introduces various graph-based machine learning and mining techniques, including graph neural networks (applying deep learning ideas to graphs), knowledge graphs (representing human knowledge as graphs), graph representation learning (converting graphs into feature vectors), random walks and centrality measures on graphs, graph clustering, and graph anomaly detection. Also, this course introduces how these techniques are applied in information retrieval, natural language understanding, computer vision & graphics, robotics, and bioinformatics.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40703 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40703';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40703', NULL, 'Computing today no longer only concerns a single user in front of their computer. An increasing number of modern systems are inherently social, involving a large group of users to collaborate, discuss, ideate, solve problems, and make decisions together via social interaction. This course aims to introduce major concepts, real-world examples, design issues, and computational techniques in social computing. Students apply the lessons to a practical problem via a semester-long team project.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Computing today no longer only concerns a single user in front of their computer. An increasing number of modern systems are inherently social, involving a large group of users to collaborate, discuss, ideate, solve problems, and make decisions together via social interaction. This course aims to introduce major concepts, real-world examples, design issues, and computational techniques in social computing. Students apply the lessons to a practical problem via a semester-long team project.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40704 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40704';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40704', NULL, 'This course will introduce the essential techniques of text mining, understand as the process of deriving high-quality information from unstructured text. The techniques include: the process of analyzing and structuring the input text with natural language processing, deriving patterns with machine learning, and evaluating and interpreting the output. The course will cover some typical text mining tasks such as text categorization, text clustering, document summarization, and relation discovery between entities.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course will introduce the essential techniques of text mining, understand as the process of deriving high-quality information from unstructured text. The techniques include: the process of analyzing and structuring the input text with natural language processing, deriving patterns with machine learning, and evaluating and interpreting the output. The course will cover some typical text mining tasks such as text categorization, text clustering, document summarization, and relation discovery between entities.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40705 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40705';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40705', NULL, 'This course will cover important problems and concepts in natural language processing and the machine learning models used in those problems. Students will learn the theory and practice of ML methods for NLP, read and conduct research based on latest research publications.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course will cover important problems and concepts in natural language processing and the machine learning models used in those problems. Students will learn the theory and practice of ML methods for NLP, read and conduct research based on latest research publications.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40707 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40707';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40707', NULL, 'This course will introduce students to the basics of embodied intelligence called intelligent robotics. The course aims to study the fundamental concepts in intelligent robotic system that can sense, plan, and act in the world. To do that, we will discuss 1) the basic concepts, such as control, kinematics, in traditional robotics and 2) state-of-the-art technologies, such as task-and-motion planning and machine learning theories, toward intelligent robotic system. The course will include a brief review of basic tools, such as Robot Operating System (ROS), and also overview contemporary techniques. It will also include individual exercise and final (individual/team) projects.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course will introduce students to the basics of embodied intelligence called intelligent robotics. The course aims to study the fundamental concepts in intelligent robotic system that can sense, plan, and act in the world. To do that, we will discuss 1) the basic concepts, such as control, kinematics, in traditional robotics and 2) state-of-the-art technologies, such as task-and-motion planning and machine learning theories, toward intelligent robotic system. The course will include a brief review of basic tools, such as Robot Operating System (ROS), and also overview contemporary techniques. It will also include individual exercise and final (individual/team) projects.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40709 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40709';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40709', NULL, '3D Data are widely used in many applications in computer vision, computer graphics, and robotic. In this course, we will cover the recent advances in machine learning techniques for processing and analyzing 3D data and discuss the remaining challenges. Most of the course material will be less-than 5-year-old research papers in several sub-fields including Computer Vision, Computer Graphics, and Machine Learning. The course will be project-oriented (no exam, no paper-and-pencil homework, but easy programming assignments) and consist of seminar-style reading group presentations.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '3D Data are widely used in many applications in computer vision, computer graphics, and robotic. In this course, we will cover the recent advances in machine learning techniques for processing and analyzing 3D data and discuss the remaining challenges. Most of the course material will be less-than 5-year-old research papers in several sub-fields including Computer Vision, Computer Graphics, and Machine Learning. The course will be project-oriented (no exam, no paper-and-pencil homework, but easy programming assignments) and consist of seminar-style reading group presentations.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40801 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40801';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40801', NULL, 'Data visualization techniques help data scientists to interact with data to extract insightful information, examine hypotheses, and perform data storytelling for decision making. This course covers the fundamental concepts of data visualization, such as design principles, representation, perception, color, and data storytelling. Besides, it will provide in-depth tutorials and practices on the entire visualization process (i.e., ideation, prototyping, and usability testing) by building a web-based interactive service with Python and JavaScript. The course will be delivered in an active learning format such that concept learning is followed by in-class activities and programming practices. Furthermore, there will be programming sessions (e.g., Web programming, Python data processing, and visualization) and design studio sessions (e.g., design process and peer feedback). A final project on building real-world visual analytics solutions will help students to use the techniques learned in the class (e.g., exploring a mobile and wearable sensor dataset on the web).', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Data visualization techniques help data scientists to interact with data to extract insightful information, examine hypotheses, and perform data storytelling for decision making. This course covers the fundamental concepts of data visualization, such as design principles, representation, perception, color, and data storytelling. Besides, it will provide in-depth tutorials and practices on the entire visualization process (i.e., ideation, prototyping, and usability testing) by building a web-based interactive service with Python and JavaScript. The course will be delivered in an active learning format such that concept learning is followed by in-class activities and programming practices. Furthermore, there will be programming sessions (e.g., Web programming, Python data processing, and visualization) and design studio sessions (e.g., design process and peer feedback). A final project on building real-world visual analytics solutions will help students to use the techniques learned in the class (e.g., exploring a mobile and wearable sensor dataset on the web).', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40802 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40802';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40802', NULL, 'With advances in computing environment, we can get high quality rendering of 3D virtual world in realtime. This course is designed for understanding practical algorithms for realizing 3D computer graphics and visualization essential for not only computer animation but also in various interactive applications including computer games, simulation, and virtual reality. This is a projects-oriented class that will introduce the concepts of interactive computer graphics. Students are expected to work on a team to develop their own project.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'With advances in computing environment, we can get high quality rendering of 3D virtual world in realtime. This course is designed for understanding practical algorithms for realizing 3D computer graphics and visualization essential for not only computer animation but also in various interactive applications including computer games, simulation, and virtual reality. This is a projects-oriented class that will introduce the concepts of interactive computer graphics. Students are expected to work on a team to develop their own project.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40803 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40803';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40803', NULL, '3D content creation is a crucial part of many industries such as graphics, AR/VR, CAD/CAM, and digital fabrication, which tasks typically include designing and creating virtual objects/scenes or reconstructing a real environment. Processing scanned 3D data is also an important problem in many applications as 3D scanning technology is being widely applied, for example, in autonomous driving, robot navigation, and 3D object replication. In this course, we discuss fundamental mathematical methods for geometric 3D modeling and geometric data processing, which can be used (not only in graphics-related fields but) in many other areas in science and engineering.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '3D content creation is a crucial part of many industries such as graphics, AR/VR, CAD/CAM, and digital fabrication, which tasks typically include designing and creating virtual objects/scenes or reconstructing a real environment. Processing scanned 3D data is also an important problem in many applications as 3D scanning technology is being widely applied, for example, in autonomous driving, robot navigation, and 3D object replication. In this course, we discuss fundamental mathematical methods for geometric 3D modeling and geometric data processing, which can be used (not only in graphics-related fields but) in many other areas in science and engineering.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40804 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40804';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40804', NULL, 'In this course, students will learn the basic principles and techniques of image processing. Expanding the foundations of image processing, they will learn 3-dimensional image processing from camera images and also techniques for deep learning-based image understanding, combined with artificial intelligence. To this end, the curriculum of this course consists of three parts: (1) the basic principles and understanding of image processing, (2) the basic principles and understanding of 3D image processing, and (3) the basic principles and understanding of image processing using artificial intelligence. Students learn and experience basic principles for computer vision and various image processing applications based on the deep understanding of computer vision.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this course, students will learn the basic principles and techniques of image processing. Expanding the foundations of image processing, they will learn 3-dimensional image processing from camera images and also techniques for deep learning-based image understanding, combined with artificial intelligence. To this end, the curriculum of this course consists of three parts: (1) the basic principles and understanding of image processing, (2) the basic principles and understanding of 3D image processing, and (3) the basic principles and understanding of image processing using artificial intelligence. Students learn and experience basic principles for computer vision and various image processing applications based on the deep understanding of computer vision.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40805 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40805';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40805', NULL, 'The course studies concepts, theories and state-of-the-art methods for visual learning and recognition. This module is unique focusing on a broader set of machine learning, for computer vision, in an optimisation perspective.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The course studies concepts, theories and state-of-the-art methods for visual learning and recognition. This module is unique focusing on a broader set of machine learning, for computer vision, in an optimisation perspective.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40806 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40806';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40806', NULL, 'As computer forms and utilization environments become diverse, various user interfaces are evolving beyond the traditional GUI. Especially with the advancement of AR/VR platforms, the importance of wearable user interfaces is increasing. This course aims to understand various genres of wearable user interfaces, major prototyping techniques for researching them, and multi-modal channels for proposing new wearable interfaces.', 3, 'bachelor', NULL, 'S', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'As computer forms and utilization environments become diverse, various user interfaces are evolving beyond the traditional GUI. Especially with the advancement of AR/VR platforms, the importance of wearable user interfaces is increasing. This course aims to understand various genres of wearable user interfaces, major prototyping techniques for researching them, and multi-modal channels for proposing new wearable interfaces.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'S', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.40809 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.40809';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.40809', NULL, 'Computers have had a significant impact on our life, more so than any other machine before. In this course, we discuss social problems that computers have caused and ethical issues that challenge technical experts.', 3, 'bachelor', NULL, 'F', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Computers have had a significant impact on our life, more so than any other machine before. In this course, we discuss social problems that computers have caused and ethical issues that challenge technical experts.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'F', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.49900 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.49900';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.49900', NULL, 'The goal of this course is to expose undergraduate students to recent research problems and results in the selected area of research.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'The goal of this course is to expose undergraduate students to recent research problems and results in the selected area of research.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.49901 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.49901';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.49901', NULL, '', 1, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 1, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.49902 (전공선택)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.49902';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.49902', NULL, '', 2, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 2, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_ELECTIVE';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_ELECTIVE';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.20004 (전공필수)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.20004';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.20004', NULL, 'This course covers mathematical concepts that are frequently employed in computer science: sets, relations, propositional logic, predicative logic, graphs, trees, recurrences, recursion, and fundamental notions in abstract algebra such as groups and rings.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course covers mathematical concepts that are frequently employed in computer science: sets, relations, propositional logic, predicative logic, graphs, trees, recurrences, recursion, and fundamental notions in abstract algebra such as groups and rings.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_REQUIRED';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_REQUIRED';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.20006 (전공필수)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.20006';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.20006', NULL, 'This course provides students with fundamental concepts in data structures and algorithms in a broad context of solving problems using computers.', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course provides students with fundamental concepts in data structures and algorithms in a broad context of solving problems using computers.', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_REQUIRED';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_REQUIRED';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30000 (전공필수)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30000';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30000', NULL, 'This course introduces the basic concepts of design and analysis of computer algorithms: the basic principles and techniques of computational complexity (worst-case and average behavior, space usage, and lower bounds on the complexity of a problem), and algorithms for fundamental problems. It also introduces the areas of NP-completeness and parallel algorithms. (Prerequisite: CS204, CS206)', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course introduces the basic concepts of design and analysis of computer algorithms: the basic principles and techniques of computational complexity (worst-case and average behavior, space usage, and lower bounds on the complexity of a problem), and algorithms for fundamental problems. It also introduces the areas of NP-completeness and parallel algorithms. (Prerequisite: CS204, CS206)', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_REQUIRED';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_REQUIRED';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30101 (전공필수)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30101';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30101', NULL, 'This course provides students with a basic understanding of computer organization and architecture. It is concerned mostly with the hardware aspects of computer systems: structural organization and hardware design of digital computer systems, underlying design principles and their impact on computer performance, and software impact on computer. (Prerequisite: CS211)', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course provides students with a basic understanding of computer organization and architecture. It is concerned mostly with the hardware aspects of computer systems: structural organization and hardware design of digital computer systems, underlying design principles and their impact on computer performance, and software impact on computer. (Prerequisite: CS211)', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_REQUIRED';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_REQUIRED';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30200 (전공필수)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30200';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30200', NULL, 'This course provides students with the necessary underlying principles in the design and implementation of programming languages. Lectures use a variety of existing general-purpose programming languages from different programming paradigms: imperative, functional, logical, and object-oriented programming. (Prerequisite: CS206)', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'This course provides students with the necessary underlying principles in the design and implementation of programming languages. Lectures use a variety of existing general-purpose programming languages from different programming paradigms: imperative, functional, logical, and object-oriented programming. (Prerequisite: CS206)', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_REQUIRED';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_REQUIRED';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.30300 (전공필수)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.30300';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.30300', NULL, 'In this course, students learn about basic concepts of operating systems, with an emphasis on multi-tasking, and time-sharing. We choose one specific operating system, and study in detail its organization and functions. Students are also required to program a simple operating system, and to develop performance improvement techniques.', 4, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'In this course, students learn about basic concepts of operating systems, with an emphasis on multi-tasking, and time-sharing. We choose one specific operating system, and study in detail its organization and functions. Students are also required to program a simple operating system, and to develop performance improvement techniques.', credits = 4, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'MAJOR_REQUIRED';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'MAJOR_REQUIRED';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.91000 (연구)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.91000';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.91000', NULL, '', 3, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 3, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'RESEARCH';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'RESEARCH';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.91100 (연구)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.91100';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.91100', NULL, '', 1, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = '', credits = 1, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
  END IF;
  SELECT node_id INTO v_type_id FROM course_types WHERE type_name = 'RESEARCH';
  IF v_type_id IS NULL THEN
    RAISE EXCEPTION 'course_type % not found', 'RESEARCH';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM course_mappings WHERE course_node_id = v_course_id AND type_node_id = v_type_id AND valid_years = '[,]'::int4range) THEN
    INSERT INTO course_mappings (course_node_id, type_node_id, valid_years, evidence_id) VALUES (v_course_id, v_type_id, '[,]'::int4range, NULL);
  END IF;
END$$;

-- CS.93000 (연구)
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
  SELECT node_id INTO v_course_id FROM courses WHERE course_num = 'CS.93000';
  IF v_course_id IS NULL THEN
    INSERT INTO nodes (node_type) VALUES ('COURSE') RETURNING node_id INTO v_course_id;
    INSERT INTO courses (node_id, course_num, history, exp, credits, division, mutual, semester, department_node_id) VALUES (v_course_id, 'CS.93000', NULL, 'Domestic and international researchers are invited to give talks on various topics and future directions in computer science and to get involved in discussion with students.', 1, 'bachelor', NULL, 'A', v_dept_id);
  ELSE
    UPDATE courses SET history = NULL, exp = 'Domestic and international researchers are invited to give talks on various topics and future directions in computer science and to get involved in discussion with students.', credits = 1, division = 'bachelor', mutual = NULL, semester = 'A', department_node_id = v_dept_id WHERE node_id = v_course_id;
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
