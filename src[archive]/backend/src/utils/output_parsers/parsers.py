"""
다양한 출력 파서 구현
"""
import json
import re
from typing import Any, Dict, List, Type, Optional, Union, TypeVar, Generic
from .base import BaseOutputParser

try:
    from pydantic import BaseModel, create_model, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


class JSONOutputParser(BaseOutputParser[Dict[str, Any]]):
    """
    JSON 형식의 텍스트를 파싱하는 파서
    """
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        JSON 형식의 텍스트를 파싱하여 딕셔너리로 변환합니다.
        
        Args:
            text (str): 파싱할 JSON 형식의 텍스트
            
        Returns:
            Dict[str, Any]: 파싱된 JSON 객체
            
        Raises:
            ValueError: JSON 파싱에 실패한 경우
        """
        # JSON 코드 블록 추출 시도
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            text = json_match.group(1).strip()
        
        # 중괄호로 둘러싸인 부분 추출 시도
        if not text.strip().startswith('{'):
            json_match = re.search(r'({[\s\S]*})', text)
            if json_match:
                text = json_match.group(1).strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 파싱 오류: {e}\n원본 텍스트: {text}")
    
    def get_format_instructions(self) -> str:
        """
        JSON 출력 형식 지침을 반환합니다.
        
        Returns:
            str: JSON 출력 형식 지침
        """
        return "응답은 유효한 JSON 형식으로 작성해주세요. 예: {\"key\": \"value\"}"


class ListOutputParser(BaseOutputParser[List[str]]):
    """
    리스트 형식의 텍스트를 파싱하는 파서
    """
    
    def __init__(self, separator: str = "\n"):
        """
        ListOutputParser 초기화
        
        Args:
            separator (str, optional): 리스트 항목을 구분하는 구분자. 기본값은 개행문자("\n")입니다.
        """
        self.separator = separator
    
    def parse(self, text: str) -> List[str]:
        """
        텍스트를 파싱하여 문자열 리스트로 변환합니다.
        
        Args:
            text (str): 파싱할 텍스트
            
        Returns:
            List[str]: 파싱된 문자열 리스트
        """
        # 리스트 항목 추출
        items = text.split(self.separator)
        
        # 빈 항목 제거 및 공백 제거
        return [item.strip() for item in items if item.strip()]
    
    def get_format_instructions(self) -> str:
        """
        리스트 출력 형식 지침을 반환합니다.
        
        Returns:
            str: 리스트 출력 형식 지침
        """
        return f"응답은 각 항목을 '{self.separator}'로 구분된 리스트 형식으로 작성해주세요."


class CommaSeparatedListOutputParser(ListOutputParser):
    """
    쉼표로 구분된 리스트 형식의 텍스트를 파싱하는 파서
    """
    
    def __init__(self):
        """
        CommaSeparatedListOutputParser 초기화
        """
        super().__init__(separator=",")
    
    def get_format_instructions(self) -> str:
        """
        쉼표로 구분된 리스트 출력 형식 지침을 반환합니다.
        
        Returns:
            str: 쉼표로 구분된 리스트 출력 형식 지침
        """
        return "응답은 쉼표로 구분된 리스트 형식으로 작성해주세요. 예: 항목1, 항목2, 항목3"


class StructuredOutputParser(BaseOutputParser[Dict[str, Any]]):
    """
    구조화된 출력 형식의 텍스트를 파싱하는 파서
    """
    
    def __init__(self, schema: Dict[str, str]):
        """
        StructuredOutputParser 초기화
        
        Args:
            schema (Dict[str, str]): 출력 스키마 (키: 필드 이름, 값: 필드 설명)
        """
        self.schema = schema
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        텍스트를 파싱하여 구조화된 딕셔너리로 변환합니다.
        
        Args:
            text (str): 파싱할 텍스트
            
        Returns:
            Dict[str, Any]: 파싱된 구조화된 딕셔너리
            
        Raises:
            ValueError: 파싱에 실패한 경우
        """
        # JSON 형식으로 파싱 시도
        try:
            return JSONOutputParser().parse(text)
        except ValueError:
            # JSON 파싱 실패 시 필드별 추출 시도
            result = {}
            for field_name in self.schema.keys():
                pattern = rf"{field_name}:\s*(.*?)(?:\n|$)"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result[field_name] = match.group(1).strip()
            
            # 필드가 하나도 추출되지 않은 경우
            if not result:
                raise ValueError(f"구조화된 출력 파싱 실패: {text}")
            
            return result
    
    def get_format_instructions(self) -> str:
        """
        구조화된 출력 형식 지침을 반환합니다.
        
        Returns:
            str: 구조화된 출력 형식 지침
        """
        instructions = "다음 형식으로 응답해주세요:\n"
        for field_name, field_desc in self.schema.items():
            instructions += f"{field_name}: {field_desc}\n"
        return instructions


class XMLOutputParser(BaseOutputParser[Dict[str, Any]]):
    """
    XML 형식의 텍스트를 파싱하는 파서
    """
    
    def __init__(self, root_tag: str = "response", tags: List[str] = None):
        """
        XMLOutputParser 초기화
        
        Args:
            root_tag (str, optional): XML 루트 태그 이름. 기본값은 "response"입니다.
            tags (List[str], optional): 파싱할 태그 목록. 기본값은 None으로, 모든 태그를 파싱합니다.
        """
        self.root_tag = root_tag
        self.tags = tags
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        XML 형식의 텍스트를 파싱하여 딕셔너리로 변환합니다.
        
        Args:
            text (str): 파싱할 XML 형식의 텍스트
            
        Returns:
            Dict[str, Any]: 파싱된 XML 객체
            
        Raises:
            ValueError: XML 파싱에 실패한 경우
        """
        result = {}
        
        # 태그 목록이 지정된 경우
        if self.tags:
            for tag in self.tags:
                pattern = rf"<{tag}>(.*?)</{tag}>"
                matches = re.findall(pattern, text, re.DOTALL)
                if matches:
                    # 여러 개의 태그가 있는 경우 리스트로 저장
                    if len(matches) > 1:
                        result[tag] = [match.strip() for match in matches]
                    # 하나의 태그만 있는 경우 문자열로 저장
                    else:
                        result[tag] = matches[0].strip()
        # 태그 목록이 지정되지 않은 경우 모든 태그 파싱
        else:
            pattern = r"<(\w+)>(.*?)</\1>"
            matches = re.findall(pattern, text, re.DOTALL)
            for tag, content in matches:
                # 이미 해당 태그가 있는 경우 리스트로 변환
                if tag in result:
                    if isinstance(result[tag], list):
                        result[tag].append(content.strip())
                    else:
                        result[tag] = [result[tag], content.strip()]
                # 처음 등장하는 태그인 경우
                else:
                    result[tag] = content.strip()
        
        # 파싱 결과가 없는 경우
        if not result:
            raise ValueError(f"XML 파싱 실패: {text}")
        
        return result
    
    def get_format_instructions(self) -> str:
        """
        XML 출력 형식 지침을 반환합니다.
        
        Returns:
            str: XML 출력 형식 지침
        """
        instructions = f"응답은 다음과 같은 XML 형식으로 작성해주세요:\n<{self.root_tag}>\n"
        if self.tags:
            for tag in self.tags:
                instructions += f"  <{tag}>내용</{tag}>\n"
        else:
            instructions += "  <태그>내용</태그>\n"
        instructions += f"</{self.root_tag}>"
        return instructions


class RegexParser(BaseOutputParser[Dict[str, str]]):
    """
    정규 표현식을 사용하여 텍스트를 파싱하는 파서
    """
    
    def __init__(self, regex_pattern: str, output_keys: List[str]):
        """
        RegexParser 초기화
        
        Args:
            regex_pattern (str): 파싱에 사용할 정규 표현식 패턴
            output_keys (List[str]): 정규 표현식 그룹에 대응하는 출력 키 목록
        """
        self.regex_pattern = regex_pattern
        self.output_keys = output_keys
        
        # 정규 표현식 컴파일
        try:
            self.regex = re.compile(regex_pattern, re.DOTALL)
        except re.error as e:
            raise ValueError(f"정규 표현식 컴파일 오류: {e}")
        
        # 정규 표현식 그룹 수와 출력 키 수 검증
        if self.regex.groups != len(output_keys):
            raise ValueError(
                f"정규 표현식 그룹 수({self.regex.groups})와 출력 키 수({len(output_keys)})가 일치하지 않습니다."
            )
    
    def parse(self, text: str) -> Dict[str, str]:
        """
        정규 표현식을 사용하여 텍스트를 파싱합니다.
        
        Args:
            text (str): 파싱할 텍스트
            
        Returns:
            Dict[str, str]: 파싱된 결과
            
        Raises:
            ValueError: 정규 표현식 매칭에 실패한 경우
        """
        match = self.regex.search(text)
        if not match:
            raise ValueError(f"정규 표현식 매칭 실패: {text}")
        
        result = {}
        for i, key in enumerate(self.output_keys):
            result[key] = match.group(i + 1).strip()
        
        return result
    
    def get_format_instructions(self) -> str:
        """
        정규 표현식 출력 형식 지침을 반환합니다.
        
        Returns:
            str: 정규 표현식 출력 형식 지침
        """
        return f"응답은 다음 형식에 맞게 작성해주세요: {self.regex_pattern}"


if PYDANTIC_AVAILABLE:
    class PydanticOutputParser(BaseOutputParser):
        """
        Pydantic 모델을 사용하여 텍스트를 파싱하는 파서
        """
        
        def __init__(self, pydantic_model: Type[BaseModel]):
            """
            PydanticOutputParser 초기화
            
            Args:
                pydantic_model (Type[BaseModel]): 파싱에 사용할 Pydantic 모델 클래스
            """
            self.pydantic_model = pydantic_model
        
        def parse(self, text: str) -> BaseModel:
            """
            텍스트를 파싱하여 Pydantic 모델 인스턴스로 변환합니다.
            
            Args:
                text (str): 파싱할 텍스트
                
            Returns:
                BaseModel: 파싱된 Pydantic 모델 인스턴스
                
            Raises:
                ValueError: 파싱에 실패한 경우
            """
            # JSON 파싱 시도
            try:
                json_data = JSONOutputParser().parse(text)
                return self.pydantic_model.parse_obj(json_data)
            except Exception as e:
                raise ValueError(f"Pydantic 모델 파싱 오류: {e}\n원본 텍스트: {text}")
        
        def get_format_instructions(self) -> str:
            """
            Pydantic 모델 출력 형식 지침을 반환합니다.
            
            Returns:
                str: Pydantic 모델 출력 형식 지침
            """
            schema = self.pydantic_model.schema()
            schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
            return f"응답은 다음 JSON 스키마에 맞게 작성해주세요:\n{schema_str}"
