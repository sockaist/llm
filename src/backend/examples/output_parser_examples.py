"""
출력 파서 사용 예제
"""
import sys
import os
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


def json_output_parser_example():
    """
    JSONOutputParser 사용 예제
    """
    print("\n=== JSONOutputParser 사용 예제 ===")
    
    parser = JSONOutputParser()
    
    # 정상적인 JSON 파싱
    json_text = '{"name": "홍길동", "age": 30, "city": "서울"}'
    result = parser.parse(json_text)
    print(f"정상 JSON 파싱 결과: {result}")
    
    # 코드 블록 내 JSON 파싱
    json_with_codeblock = '```json\n{"name": "홍길동", "age": 30, "city": "서울"}\n```'
    result = parser.parse(json_with_codeblock)
    print(f"코드 블록 JSON 파싱 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def list_output_parser_example():
    """
    ListOutputParser 사용 예제
    """
    print("\n=== ListOutputParser 사용 예제 ===")
    
    parser = ListOutputParser()
    
    # 개행으로 구분된 리스트 파싱
    list_text = "항목1\n항목2\n항목3"
    result = parser.parse(list_text)
    print(f"개행 구분 리스트 파싱 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")
    
    # 사용자 정의 구분자 사용
    custom_parser = ListOutputParser(separator="|")
    list_text = "항목1|항목2|항목3"
    result = custom_parser.parse(list_text)
    print(f"사용자 정의 구분자 리스트 파싱 결과: {result}")
    print(f"사용자 정의 구분자 형식 지침: {custom_parser.get_format_instructions()}")


def comma_separated_list_parser_example():
    """
    CommaSeparatedListOutputParser 사용 예제
    """
    print("\n=== CommaSeparatedListOutputParser 사용 예제 ===")
    
    parser = CommaSeparatedListOutputParser()
    
    # 쉼표로 구분된 리스트 파싱
    list_text = "항목1, 항목2, 항목3"
    result = parser.parse(list_text)
    print(f"쉼표 구분 리스트 파싱 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def structured_output_parser_example():
    """
    StructuredOutputParser 사용 예제
    """
    print("\n=== StructuredOutputParser 사용 예제 ===")
    
    schema = {
        "name": "이름",
        "age": "나이",
        "city": "도시"
    }
    parser = StructuredOutputParser(schema=schema)
    
    # JSON 형식 파싱
    json_text = '{"name": "홍길동", "age": 30, "city": "서울"}'
    result = parser.parse(json_text)
    print(f"JSON 형식 파싱 결과: {result}")
    
    # 키-값 형식 파싱
    key_value_text = "name: 홍길동\nage: 30\ncity: 서울"
    result = parser.parse(key_value_text)
    print(f"키-값 형식 파싱 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def xml_output_parser_example():
    """
    XMLOutputParser 사용 예제
    """
    print("\n=== XMLOutputParser 사용 예제 ===")
    
    parser = XMLOutputParser(root_tag="person", tags=["name", "age", "city"])
    
    # XML 파싱
    xml_text = "<person><name>홍길동</name><age>30</age><city>서울</city></person>"
    result = parser.parse(xml_text)
    print(f"XML 파싱 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")
    
    # 태그 지정 없이 모든 태그 파싱
    general_parser = XMLOutputParser()
    xml_text = "<data><item>항목1</item><item>항목2</item><info>추가 정보</info></data>"
    result = general_parser.parse(xml_text)
    print(f"일반 XML 파싱 결과: {result}")


def regex_parser_example():
    """
    RegexParser 사용 예제
    """
    print("\n=== RegexParser 사용 예제 ===")
    
    # 이메일과 전화번호 추출 정규식
    parser = RegexParser(
        regex_pattern=r"이메일: ([\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,}), 전화번호: (\d{2,3}-\d{3,4}-\d{4})",
        output_keys=["email", "phone"]
    )
    
    # 정규식 패턴 매칭
    text = "사용자 정보 - 이메일: user@example.com, 전화번호: 010-1234-5678"
    result = parser.parse(text)
    print(f"정규식 파싱 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def markdown_output_parser_example():
    """
    MarkdownOutputParser 사용 예제
    """
    print("\n=== MarkdownOutputParser 사용 예제 ===")
    
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
    print(f"마크다운 파싱 결과 (특정 헤더만):\n{result}")
    
    # 모든 헤더 포함
    full_parser = MarkdownOutputParser()
    result = full_parser.parse(markdown_text)
    print(f"마크다운 파싱 결과 (모든 헤더):\n{result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def csv_output_parser_example():
    """
    CSVOutputParser 사용 예제
    """
    print("\n=== CSVOutputParser 사용 예제 ===")
    
    parser = CSVOutputParser(column_names=["이름", "나이", "도시"])
    
    # CSV 파싱
    csv_text = """
이름,나이,도시
홍길동,30,서울
김철수,25,부산
이영희,35,대전
"""
    result = parser.parse(csv_text)
    print(f"CSV 파싱 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def datetime_output_parser_example():
    """
    DatetimeOutputParser 사용 예제
    """
    print("\n=== DatetimeOutputParser 사용 예제 ===")
    
    parser = DatetimeOutputParser()
    
    # 날짜 및 시간 파싱
    text = "회의는 2023-05-15 14:30에 시작합니다."
    result = parser.parse(text)
    print(f"날짜 및 시간 파싱 결과: {result}")
    
    # 다른 형식의 날짜
    text = "회의는 05/15/2023 14:30에 시작합니다."
    result = parser.parse(text)
    print(f"다른 형식 날짜 파싱 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def custom_function_output_parser_example():
    """
    CustomFunctionOutputParser 사용 예제
    """
    print("\n=== CustomFunctionOutputParser 사용 예제 ===")
    
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
    print(f"사용자 정의 함수 파싱 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def combining_output_parser_example():
    """
    CombiningOutputParser 사용 예제
    """
    print("\n=== CombiningOutputParser 사용 예제 ===")
    
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
    print(f"조합 파서 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def auto_fix_output_parser_example():
    """
    AutoFixOutputParser 사용 예제
    """
    print("\n=== AutoFixOutputParser 사용 예제 ===")
    
    # JSON 파서를 자동 수정 기능으로 감싸기
    base_parser = JSONOutputParser()
    parser = AutoFixOutputParser(parser=base_parser)
    
    # 오류가 있는 JSON 파싱 시도
    invalid_json = '{"name": "홍길동", "age": 30, "city": "서울",}'  # 후행 쉼표 오류
    try:
        result = parser.parse(invalid_json)
        print(f"자동 수정된 JSON 파싱 결과: {result}")
    except ValueError as e:
        print(f"자동 수정 실패: {e}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def pydantic_output_parser_example():
    """
    PydanticOutputParser 사용 예제 (Pydantic이 설치된 경우)
    """
    if not PYDANTIC_AVAILABLE:
        print("\n=== PydanticOutputParser 예제 ===")
        print("Pydantic이 설치되지 않았습니다. pip install pydantic 명령으로 설치할 수 있습니다.")
        return
    
    print("\n=== PydanticOutputParser 사용 예제 ===")
    
    # Pydantic 모델 정의
    class Person(BaseModel):
        name: str = Field(description="사람의 이름")
        age: int = Field(description="사람의 나이")
        city: str = Field(description="거주 도시")
    
    parser = PydanticOutputParser(pydantic_model=Person)
    
    # JSON을 Pydantic 모델로 파싱
    json_text = '{"name": "홍길동", "age": 30, "city": "서울"}'
    result = parser.parse(json_text)
    print(f"Pydantic 파싱 결과: {result}")
    print(f"이름: {result.name}, 나이: {result.age}, 도시: {result.city}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


def yaml_output_parser_example():
    """
    YAMLOutputParser 사용 예제 (PyYAML이 설치된 경우)
    """
    if not YAML_AVAILABLE:
        print("\n=== YAMLOutputParser 예제 ===")
        print("PyYAML이 설치되지 않았습니다. pip install pyyaml 명령으로 설치할 수 있습니다.")
        return
    
    print("\n=== YAMLOutputParser 사용 예제 ===")
    
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
    print(f"YAML 파싱 결과: {result}")
    
    # 형식 지침 출력
    print(f"형식 지침: {parser.get_format_instructions()}")


if __name__ == "__main__":
    json_output_parser_example()
    list_output_parser_example()
    comma_separated_list_parser_example()
    structured_output_parser_example()
    xml_output_parser_example()
    regex_parser_example()
    markdown_output_parser_example()
    csv_output_parser_example()
    datetime_output_parser_example()
    custom_function_output_parser_example()
    combining_output_parser_example()
    auto_fix_output_parser_example()
    pydantic_output_parser_example()
    yaml_output_parser_example()
