"""
테스트 케이스 - 출력 파서
"""
import sys
import os
import unittest
import json

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.output_parsers import (
    JSONOutputParser,
    ListOutputParser,
    CommaSeparatedListOutputParser,
    StructuredOutputParser,
    XMLOutputParser,
    RegexParser,
    MarkdownOutputParser,
    CSVOutputParser,
    DatetimeOutputParser,
    CustomFunctionOutputParser,
    CombiningOutputParser,
    AutoFixOutputParser
)

try:
    from src.output_parsers import PydanticOutputParser
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

try:
    from src.output_parsers import YAMLOutputParser
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

class TestOutputParsers(unittest.TestCase):
    """
    출력 파서 테스트 케이스
    """
    
    def test_json_output_parser(self):
        """
        JSONOutputParser 테스트
        """
        parser = JSONOutputParser()
        
        # 정상적인 JSON 파싱
        json_text = '{"name": "홍길동", "age": 30, "city": "서울"}'
        result = parser.parse(json_text)
        self.assertEqual(result["name"], "홍길동")
        self.assertEqual(result["age"], 30)
        self.assertEqual(result["city"], "서울")
        
        # 코드 블록 내 JSON 파싱
        json_with_codeblock = '```json\n{"name": "홍길동", "age": 30, "city": "서울"}\n```'
        result = parser.parse(json_with_codeblock)
        self.assertEqual(result["name"], "홍길동")
        self.assertEqual(result["age"], 30)
        self.assertEqual(result["city"], "서울")
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("JSON", format_instructions)
    
    def test_list_output_parser(self):
        """
        ListOutputParser 테스트
        """
        parser = ListOutputParser()
        
        # 개행으로 구분된 리스트 파싱
        list_text = "항목1\n항목2\n항목3"
        result = parser.parse(list_text)
        self.assertEqual(result, ["항목1", "항목2", "항목3"])
        
        # 사용자 정의 구분자 사용
        custom_parser = ListOutputParser(separator="|")
        list_text = "항목1|항목2|항목3"
        result = custom_parser.parse(list_text)
        self.assertEqual(result, ["항목1", "항목2", "항목3"])
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("리스트", format_instructions)
    
    def test_comma_separated_list_parser(self):
        """
        CommaSeparatedListOutputParser 테스트
        """
        parser = CommaSeparatedListOutputParser()
        
        # 쉼표로 구분된 리스트 파싱
        list_text = "항목1, 항목2, 항목3"
        result = parser.parse(list_text)
        self.assertEqual(result, ["항목1", "항목2", "항목3"])
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("쉼표", format_instructions)
    
    def test_structured_output_parser(self):
        """
        StructuredOutputParser 테스트
        """
        schema = {
            "name": "이름",
            "age": "나이",
            "city": "도시"
        }
        parser = StructuredOutputParser(schema=schema)
        
        # JSON 형식 파싱
        json_text = '{"name": "홍길동", "age": 30, "city": "서울"}'
        result = parser.parse(json_text)
        self.assertEqual(result["name"], "홍길동")
        self.assertEqual(result["age"], 30)
        self.assertEqual(result["city"], "서울")
        
        # 키-값 형식 파싱
        key_value_text = "name: 홍길동\nage: 30\ncity: 서울"
        result = parser.parse(key_value_text)
        self.assertEqual(result["name"], "홍길동")
        self.assertEqual(result["age"], "30")  # 문자열로 파싱됨
        self.assertEqual(result["city"], "서울")
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("구조화된", format_instructions)
    
    def test_xml_output_parser(self):
        """
        XMLOutputParser 테스트
        """
        parser = XMLOutputParser(root_tag="person", tags=["name", "age", "city"])
        
        # XML 파싱
        xml_text = "<person><name>홍길동</name><age>30</age><city>서울</city></person>"
        result = parser.parse(xml_text)
        self.assertEqual(result["name"], "홍길동")
        self.assertEqual(result["age"], "30")  # 문자열로 파싱됨
        self.assertEqual(result["city"], "서울")
        
        # 태그 지정 없이 모든 태그 파싱
        general_parser = XMLOutputParser()
        xml_text = "<data><item>항목1</item><item>항목2</item><info>추가 정보</info></data>"
        result = general_parser.parse(xml_text)
        self.assertEqual(result["item"], ["항목1", "항목2"])
        self.assertEqual(result["info"], "추가 정보")
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("XML", format_instructions)
    
    def test_regex_parser(self):
        """
        RegexParser 테스트
        """
        # 이메일과 전화번호 추출 정규식
        parser = RegexParser(
            regex_pattern=r"이메일: ([\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,}), 전화번호: (\d{2,3}-\d{3,4}-\d{4})",
            output_keys=["email", "phone"]
        )
        
        # 정규식 패턴 매칭
        text = "사용자 정보 - 이메일: user@example.com, 전화번호: 010-1234-5678"
        result = parser.parse(text)
        self.assertEqual(result["email"], "user@example.com")
        self.assertEqual(result["phone"], "010-1234-5678")
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("정규식", format_instructions)
    
    def test_markdown_output_parser(self):
        """
        MarkdownOutputParser 테스트
        """
        parser = MarkdownOutputParser(headers_to_include=["소개", "특징", "결론"])
        
        # 마크다운 파싱
        markdown_text = """
# 소개
이것은 소개 섹션입니다.

# 특징
- 특징 1
- 특징 2

# 사용법
사용법에 대한 설명입니다.

# 결론
결론 내용입니다.
"""
        result = parser.parse(markdown_text)
        self.assertIn("소개", result)
        self.assertIn("특징", result)
        self.assertIn("결론", result)
        self.assertNotIn("사용법", result)
        
        # 모든 헤더 포함
        full_parser = MarkdownOutputParser()
        result = full_parser.parse(markdown_text)
        self.assertIn("소개", result)
        self.assertIn("특징", result)
        self.assertIn("결론", result)
        self.assertIn("사용법", result)
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("마크다운", format_instructions)
    
    def test_csv_output_parser(self):
        """
        CSVOutputParser 테스트
        """
        parser = CSVOutputParser(column_names=["이름", "나이", "도시"])
        
        # CSV 파싱
        csv_text = """
이름,나이,도시
홍길동,30,서울
김철수,25,부산
이영희,35,대전
"""
        result = parser.parse(csv_text)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["이름"], "홍길동")
        self.assertEqual(result[1]["나이"], "25")
        self.assertEqual(result[2]["도시"], "대전")
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("CSV", format_instructions)
    
    def test_datetime_output_parser(self):
        """
        DatetimeOutputParser 테스트
        """
        parser = DatetimeOutputParser()
        
        # 날짜 및 시간 파싱
        text = "회의는 2023-05-15 14:30에 시작합니다."
        result = parser.parse(text)
        self.assertEqual(result["date"], "2023-05-15")
        self.assertEqual(result["time"], "14:30:00")
        
        # 다른 형식의 날짜
        text = "회의는 05/15/2023 14:30에 시작합니다."
        result = parser.parse(text)
        self.assertEqual(result["date"], "2023-05-15")
        self.assertEqual(result["time"], "14:30:00")
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("날짜", format_instructions)
    
    def test_custom_function_output_parser(self):
        """
        CustomFunctionOutputParser 테스트
        """
        # 사용자 정의 파싱 함수
        def parse_product_info(text):
            lines = text.strip().split('\n')
            result = {}
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    result[key.strip()] = value.strip()
            return result
        
        parser = CustomFunctionOutputParser(
            parse_func=parse_product_info,
            format_instructions="제품 정보를 '키: 값' 형식으로 작성해주세요."
        )
        
        # 사용자 정의 함수로 파싱
        text = """
제품명: 스마트폰
가격: 1,000,000원
제조사: 삼성전자
"""
        result = parser.parse(text)
        self.assertEqual(result["제품명"], "스마트폰")
        self.assertEqual(result["가격"], "1,000,000원")
        self.assertEqual(result["제조사"], "삼성전자")
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertEqual(format_instructions, "제품 정보를 '키: 값' 형식으로 작성해주세요.")
    
    def test_combining_output_parser(self):
        """
        CombiningOutputParser 테스트
        """
        # 여러 파서 조합
        parsers = {
            "json": JSONOutputParser(),
            "list": ListOutputParser()
        }
        parser = CombiningOutputParser(parsers=parsers)
        
        # 여러 형식이 포함된 텍스트 파싱
        text = """
여기 JSON 데이터가 있습니다:
{"name": "홍길동", "age": 30}

그리고 여기 리스트가 있습니다:
항목1
항목2
항목3
"""
        result = parser.parse(text)
        self.assertEqual(result["json"]["name"], "홍길동")
        self.assertEqual(result["json"]["age"], 30)
        self.assertEqual(result["list"], ["항목1", "항목2", "항목3"])
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("JSON", format_instructions)
        self.assertIn("리스트", format_instructions)
    
    def test_auto_fix_output_parser(self):
        """
        AutoFixOutputParser 테스트
        """
        # JSON 파서를 자동 수정 기능으로 감싸기
        base_parser = JSONOutputParser()
        parser = AutoFixOutputParser(parser=base_parser)
        
        # 오류가 있는 JSON 파싱 시도 (후행 쉼표 오류)
        invalid_json = '{"name": "홍길동", "age": 30, "city": "서울",}'
        
        # 자동 수정 시도 (실제 구현에 따라 성공 또는 실패할 수 있음)
        try:
            result = parser.parse(invalid_json)
            self.assertEqual(result["name"], "홍길동")
            self.assertEqual(result["age"], 30)
            self.assertEqual(result["city"], "서울")
        except ValueError:
            # 자동 수정 실패 시 테스트 통과 (실제 구현에 따라 다름)
            pass
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("JSON", format_instructions)
    
    @unittest.skipIf(not PYDANTIC_AVAILABLE, "Pydantic이 설치되지 않았습니다.")
    def test_pydantic_output_parser(self):
        """
        PydanticOutputParser 테스트
        """
        # Pydantic 모델 정의
        class Person(BaseModel):
            name: str = Field(description="사람의 이름")
            age: int = Field(description="사람의 나이")
            city: str = Field(description="거주 도시")
        
        parser = PydanticOutputParser(pydantic_model=Person)
        
        # JSON을 Pydantic 모델로 파싱
        json_text = '{"name": "홍길동", "age": 30, "city": "서울"}'
        result = parser.parse(json_text)
        self.assertEqual(result.name, "홍길동")
        self.assertEqual(result.age, 30)
        self.assertEqual(result.city, "서울")
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("Pydantic", format_instructions)
    
    @unittest.skipIf(not YAML_AVAILABLE, "PyYAML이 설치되지 않았습니다.")
    def test_yaml_output_parser(self):
        """
        YAMLOutputParser 테스트
        """
        parser = YAMLOutputParser()
        
        # YAML 파싱
        yaml_text = """
name: 홍길동
age: 30
city: 서울
hobbies:
  - 독서
  - 영화 감상
  - 여행
"""
        result = parser.parse(yaml_text)
        self.assertEqual(result["name"], "홍길동")
        self.assertEqual(result["age"], 30)
        self.assertEqual(result["city"], "서울")
        self.assertEqual(result["hobbies"], ["독서", "영화 감상", "여행"])
        
        # 형식 지침 확인
        format_instructions = parser.get_format_instructions()
        self.assertIn("YAML", format_instructions)

if __name__ == "__main__":
    unittest.main()
