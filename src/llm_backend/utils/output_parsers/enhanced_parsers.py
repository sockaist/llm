"""
확장된 출력 파서 구현
"""
import json
import re
import csv
import io
from typing import Any, Dict, List, Type, Optional, Union, TypeVar, Generic, Callable
from ..output_parsers.base import BaseOutputParser

try:
    from pydantic import BaseModel, create_model, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class MarkdownOutputParser(BaseOutputParser[str]):
    """
    마크다운 형식의 텍스트를 파싱하는 파서
    """
    
    def __init__(self, headers_to_include: Optional[List[str]] = None):
        """
        MarkdownOutputParser 초기화
        
        Args:
            headers_to_include (List[str], optional): 포함할 헤더 목록. 기본값은 None으로, 모든 헤더를 포함합니다.
        """
        self.headers_to_include = headers_to_include
    
    def parse(self, text: str) -> str:
        """
        마크다운 형식의 텍스트를 파싱합니다.
        
        Args:
            text (str): 파싱할 마크다운 텍스트
            
        Returns:
            str: 파싱된 마크다운 텍스트
        """
        if not self.headers_to_include:
            return text
        
        # 헤더별로 텍스트 분할
        sections = {}
        current_header = None
        current_content = []
        
        for line in text.split('\n'):
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                # 이전 헤더의 내용 저장
                if current_header:
                    sections[current_header] = '\n'.join(current_content)
                
                # 새 헤더 설정
                current_header = header_match.group(2).strip()
                current_content = []
            elif current_header:
                current_content.append(line)
        
        # 마지막 헤더의 내용 저장
        if current_header:
            sections[current_header] = '\n'.join(current_content)
        
        # 지정된 헤더만 포함
        result = []
        for header in self.headers_to_include:
            if header in sections:
                result.append(f"# {header}\n{sections[header]}")
        
        return '\n\n'.join(result)
    
    def get_format_instructions(self) -> str:
        """
        마크다운 출력 형식 지침을 반환합니다.
        
        Returns:
            str: 마크다운 출력 형식 지침
        """
        if self.headers_to_include:
            headers_str = ', '.join([f"'{h}'" for h in self.headers_to_include])
            return f"응답은 마크다운 형식으로 작성해주세요. 다음 헤더를 포함해야 합니다: {headers_str}"
        else:
            return "응답은 마크다운 형식으로 작성해주세요."


class CSVOutputParser(BaseOutputParser[List[Dict[str, str]]]):
    """
    CSV 형식의 텍스트를 파싱하는 파서
    """
    
    def __init__(self, column_names: Optional[List[str]] = None):
        """
        CSVOutputParser 초기화
        
        Args:
            column_names (List[str], optional): CSV 열 이름 목록. 기본값은 None으로, 첫 번째 행을 열 이름으로 사용합니다.
        """
        self.column_names = column_names
    
    def parse(self, text: str) -> List[Dict[str, str]]:
        """
        CSV 형식의 텍스트를 파싱하여 딕셔너리 리스트로 변환합니다.
        
        Args:
            text (str): 파싱할 CSV 형식의 텍스트
            
        Returns:
            List[Dict[str, str]]: 파싱된 CSV 데이터
            
        Raises:
            ValueError: CSV 파싱에 실패한 경우
        """
        # CSV 코드 블록 추출 시도
        csv_match = re.search(r'```(?:csv)?\s*([\s\S]*?)\s*```', text)
        if csv_match:
            text = csv_match.group(1).strip()
        
        try:
            # CSV 파싱
            csv_file = io.StringIO(text)
            if self.column_names:
                reader = csv.DictReader(csv_file, fieldnames=self.column_names)
                # 첫 번째 행이 열 이름과 같으면 건너뛰기
                first_row = next(reader, None)
                if first_row and all(first_row[col].strip() == col for col in self.column_names):
                    result = list(reader)
                else:
                    result = [first_row] + list(reader) if first_row else []
            else:
                reader = csv.DictReader(csv_file)
                result = list(reader)
            
            return result
        except Exception as e:
            raise ValueError(f"CSV 파싱 오류: {e}\n원본 텍스트: {text}")
    
    def get_format_instructions(self) -> str:
        """
        CSV 출력 형식 지침을 반환합니다.
        
        Returns:
            str: CSV 출력 형식 지침
        """
        if self.column_names:
            columns_str = ', '.join(self.column_names)
            return f"응답은 다음 열을 포함하는 CSV 형식으로 작성해주세요: {columns_str}"
        else:
            return "응답은 CSV 형식으로 작성해주세요. 첫 번째 행은 열 이름이어야 합니다."


if YAML_AVAILABLE:
    class YAMLOutputParser(BaseOutputParser[Dict[str, Any]]):
        """
        YAML 형식의 텍스트를 파싱하는 파서
        """
        
        def parse(self, text: str) -> Dict[str, Any]:
            """
            YAML 형식의 텍스트를 파싱하여 딕셔너리로 변환합니다.
            
            Args:
                text (str): 파싱할 YAML 형식의 텍스트
                
            Returns:
                Dict[str, Any]: 파싱된 YAML 객체
                
            Raises:
                ValueError: YAML 파싱에 실패한 경우
            """
            # YAML 코드 블록 추출 시도
            yaml_match = re.search(r'```(?:yaml|yml)?\s*([\s\S]*?)\s*```', text)
            if yaml_match:
                text = yaml_match.group(1).strip()
            
            try:
                return yaml.safe_load(text)
            except Exception as e:
                raise ValueError(f"YAML 파싱 오류: {e}\n원본 텍스트: {text}")
        
        def get_format_instructions(self) -> str:
            """
            YAML 출력 형식 지침을 반환합니다.
            
            Returns:
                str: YAML 출력 형식 지침
            """
            return "응답은 유효한 YAML 형식으로 작성해주세요."


class DatetimeOutputParser(BaseOutputParser[Dict[str, str]]):
    """
    날짜 및 시간 정보를 파싱하는 파서
    """
    
    def parse(self, text: str) -> Dict[str, str]:
        """
        텍스트에서 날짜 및 시간 정보를 추출합니다.
        
        Args:
            text (str): 파싱할 텍스트
            
        Returns:
            Dict[str, str]: 파싱된 날짜 및 시간 정보
            
        Raises:
            ValueError: 날짜 및 시간 정보 추출에 실패한 경우
        """
        result = {}
        
        # 날짜 패턴 (YYYY-MM-DD, YYYY/MM/DD 등)
        date_patterns = [
            (r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', 'date', '{0}-{1:02d}-{2:02d}'),
            (r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'date', '{2}-{0:02d}-{1:02d}')
        ]
        
        # 시간 패턴 (HH:MM:SS, HH:MM 등)
        time_patterns = [
            (r'(\d{1,2}):(\d{2})(?::(\d{2}))?', 'time', '{0:02d}:{1:02d}:{2:02d}' if '{2}' else '{0:02d}:{1:02d}:00')
        ]
        
        # 날짜 추출
        for pattern, key, format_str in date_patterns:
            match = re.search(pattern, text)
            if match:
                groups = [int(g) for g in match.groups()]
                result[key] = format_str.format(*groups)
                break
        
        # 시간 추출
        for pattern, key, format_str in time_patterns:
            match = re.search(pattern, text)
            if match:
                groups = []
                for g in match.groups():
                    groups.append(int(g) if g is not None else 0)
                result[key] = format_str.format(*groups)
                break
        
        if not result:
            raise ValueError(f"날짜 및 시간 정보 추출 실패: {text}")
        
        return result
    
    def get_format_instructions(self) -> str:
        """
        날짜 및 시간 출력 형식 지침을 반환합니다.
        
        Returns:
            str: 날짜 및 시간 출력 형식 지침
        """
        return "응답에 날짜(YYYY-MM-DD 또는 YYYY/MM/DD 형식)와 시간(HH:MM:SS 또는 HH:MM 형식)을 포함해주세요."


class CustomFunctionOutputParser(BaseOutputParser[Any]):
    """
    사용자 정의 함수를 사용하여 텍스트를 파싱하는 파서
    """
    
    def __init__(self, parse_func: Callable[[str], Any], format_instructions: str = ""):
        """
        CustomFunctionOutputParser 초기화
        
        Args:
            parse_func (Callable[[str], Any]): 텍스트를 파싱하는 함수
            format_instructions (str, optional): 출력 형식 지침. 기본값은 빈 문자열입니다.
        """
        self.parse_func = parse_func
        self._format_instructions = format_instructions
    
    def parse(self, text: str) -> Any:
        """
        사용자 정의 함수를 사용하여 텍스트를 파싱합니다.
        
        Args:
            text (str): 파싱할 텍스트
            
        Returns:
            Any: 파싱된 결과
            
        Raises:
            ValueError: 파싱에 실패한 경우
        """
        try:
            return self.parse_func(text)
        except Exception as e:
            raise ValueError(f"사용자 정의 함수 파싱 오류: {e}\n원본 텍스트: {text}")
    
    def get_format_instructions(self) -> str:
        """
        사용자 정의 출력 형식 지침을 반환합니다.
        
        Returns:
            str: 사용자 정의 출력 형식 지침
        """
        return self._format_instructions


class CombiningOutputParser(BaseOutputParser[Dict[str, Any]]):
    """
    여러 파서를 조합하여 텍스트를 파싱하는 파서
    """
    
    def __init__(self, parsers: Dict[str, BaseOutputParser]):
        """
        CombiningOutputParser 초기화
        
        Args:
            parsers (Dict[str, BaseOutputParser]): 키와 파서의 딕셔너리
        """
        self.parsers = parsers
    
    def parse(self, text: str) -> Dict[str, Any]:
        """
        여러 파서를 사용하여 텍스트를 파싱합니다.
        
        Args:
            text (str): 파싱할 텍스트
            
        Returns:
            Dict[str, Any]: 파싱된 결과
            
        Raises:
            ValueError: 파싱에 실패한 경우
        """
        result = {}
        errors = []
        
        for key, parser in self.parsers.items():
            try:
                result[key] = parser.parse(text)
            except ValueError as e:
                errors.append(f"{key}: {str(e)}")
        
        if not result:
            raise ValueError(f"모든 파서가 파싱에 실패했습니다: {', '.join(errors)}")
        
        return result
    
    def get_format_instructions(self) -> str:
        """
        조합된 출력 형식 지침을 반환합니다.
        
        Returns:
            str: 조합된 출력 형식 지침
        """
        instructions = ["응답은 다음 형식을 모두 만족해야 합니다:"]
        for key, parser in self.parsers.items():
            parser_instructions = parser.get_format_instructions()
            if parser_instructions:
                instructions.append(f"- {key}: {parser_instructions}")
        
        return "\n".join(instructions)


class AutoFixOutputParser(BaseOutputParser[Any]):
    """
    파싱 실패 시 자동으로 수정을 시도하는 파서
    """
    
    def __init__(self, parser: BaseOutputParser, max_retries: int = 3):
        """
        AutoFixOutputParser 초기화
        
        Args:
            parser (BaseOutputParser): 기본 파서
            max_retries (int, optional): 최대 재시도 횟수. 기본값은 3입니다.
        """
        self.parser = parser
        self.max_retries = max_retries
    
    def parse(self, text: str) -> Any:
        """
        텍스트를 파싱하고, 실패 시 자동으로 수정을 시도합니다.
        
        Args:
            text (str): 파싱할 텍스트
            
        Returns:
            Any: 파싱된 결과
            
        Raises:
            ValueError: 모든 재시도 후에도 파싱에 실패한 경우
        """
        # 첫 번째 시도
        try:
            return self.parser.parse(text)
        except ValueError as e:
            original_error = str(e)
        
        # 자동 수정 시도
        for i in range(self.max_retries):
            try:
                # JSON 파서인 경우
                if isinstance(self.parser, JSONOutputParser):
                    fixed_text = self._fix_json(text)
                # XML 파서인 경우
                elif isinstance(self.parser, XMLOutputParser):
                    fixed_text = self._fix_xml(text)
                # CSV 파서인 경우
                elif isinstance(self.parser, CSVOutputParser):
                    fixed_text = self._fix_csv(text)
                # 기타 파서인 경우
                else:
                    # 더 이상 시도하지 않음
                    break
                
                return self.parser.parse(fixed_text)
            except ValueError:
                continue
        
        raise ValueError(f"자동 수정 후에도 파싱 실패: {original_error}")
    
    def _fix_json(self, text: str) -> str:
        """
        JSON 텍스트를 수정합니다.
        
        Args:
            text (str): 수정할 JSON 텍스트
            
        Returns:
            str: 수정된 JSON 텍스트
        """
        # 중괄호 추출
        json_match = re.search(r'({[\s\S]*})', text)
        if json_match:
            text = json_match.group(1).strip()
        
        # 따옴표 수정
        text = re.sub(r'(?<!")(\w+)(?=":)', r'"\1"', text)
        text = re.sub(r'(?<=:\s*)(\w+)(?=,|})', r'"\1"', text)
        
        # 후행 쉼표 수정
        text = re.sub(r',\s*}', '}', text)
        
        return text
    
    def _fix_xml(self, text: str) -> str:
        """
        XML 텍스트를 수정합니다.
        
        Args:
            text (str): 수정할 XML 텍스트
            
        Returns:
            str: 수정된 XML 텍스트
        """
        # XML 태그 추출
        xml_match = re.search(r'<[\s\S]*>', text)
        if xml_match:
            text = xml_match.group(0).strip()
        
        # 닫는 태그 수정
        open_tags = re.findall(r'<(\w+)[^>]*>', text)
        for tag in reversed(open_tags):
            if f"</{tag}>" not in text:
                text += f"</{tag}>"
        
        return text
    
    def _fix_csv(self, text: str) -> str:
        """
        CSV 텍스트를 수정합니다.
        
        Args:
            text (str): 수정할 CSV 텍스트
            
        Returns:
            str: 수정된 CSV 텍스트
        """
        # 줄바꿈 정규화
        text = re.sub(r'\r\n|\r', '\n', text)
        
        # 각 행의 열 수 확인
        lines = text.strip().split('\n')
        if not lines:
            return text
        
        # 첫 번째 행의 열 수를 기준으로 함
        expected_columns = len(lines[0].split(','))
        
        # 각 행의 열 수 조정
        fixed_lines = []
        for line in lines:
            columns = line.split(',')
            if len(columns) < expected_columns:
                # 부족한 열 추가
                columns.extend([''] * (expected_columns - len(columns)))
            elif len(columns) > expected_columns:
                # 초과 열 제거
                columns = columns[:expected_columns]
            fixed_lines.append(','.join(columns))
        
        return '\n'.join(fixed_lines)
    
    def get_format_instructions(self) -> str:
        """
        기본 파서의 출력 형식 지침을 반환합니다.
        
        Returns:
            str: 출력 형식 지침
        """
        return self.parser.get_format_instructions()
