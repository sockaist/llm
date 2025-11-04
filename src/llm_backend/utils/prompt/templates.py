"""
다양한 프롬프트 템플릿 구현
"""
import json
import re
from typing import Dict, List, Any, Optional, Union
from .base import StringPromptTemplate

try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


class SimplePromptTemplate(StringPromptTemplate):
    """
    Python의 format 메서드를 사용하는 간단한 프롬프트 템플릿
    """
    
    def format(self, **kwargs) -> str:
        """
        프롬프트 템플릿에 변수를 채워 최종 프롬프트 문자열을 생성합니다.
        
        Args:
            **kwargs: 프롬프트 템플릿에 사용될 변수와 값 (키-값 쌍)
            
        Returns:
            str: 변수가 채워진 최종 프롬프트 문자열
            
        Raises:
            ValueError: 필요한 변수가 제공되지 않은 경우
        """
        self._validate_variables(**kwargs)
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"프롬프트 템플릿에 필요한 변수 '{e}'가 제공되지 않았습니다.")


class Jinja2PromptTemplate(StringPromptTemplate):
    """
    Jinja2 템플릿 엔진을 사용하는 프롬프트 템플릿
    """
    
    def __init__(self, template: str, input_variables: List[str]):
        """
        Jinja2PromptTemplate 초기화
        
        Args:
            template (str): Jinja2 형식의 프롬프트 템플릿 문자열
            input_variables (List[str]): 프롬프트 템플릿에 필요한 입력 변수 목록
            
        Raises:
            ImportError: Jinja2가 설치되지 않은 경우
        """
        super().__init__(template, input_variables)
        if not JINJA2_AVAILABLE:
            raise ImportError(
                "Jinja2PromptTemplate을 사용하려면 jinja2를 설치해야 합니다. "
                "pip install jinja2 명령으로 설치할 수 있습니다."
            )
        self._env = jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )
        self._template_obj = self._env.from_string(template)
    
    def format(self, **kwargs) -> str:
        """
        Jinja2 템플릿에 변수를 채워 최종 프롬프트 문자열을 생성합니다.
        
        Args:
            **kwargs: 프롬프트 템플릿에 사용될 변수와 값 (키-값 쌍)
            
        Returns:
            str: 변수가 채워진 최종 프롬프트 문자열
            
        Raises:
            ValueError: 필요한 변수가 제공되지 않은 경우
        """
        self._validate_variables(**kwargs)
        try:
            return self._template_obj.render(**kwargs)
        except Exception as e:
            raise ValueError(f"Jinja2 템플릿 렌더링 중 오류 발생: {e}")


class InstructionConfig:
    """
    기존 InstructionConfig 클래스를 확장한 프롬프트 템플릿 구현
    """
    
    def __init__(
        self, 
        instruction: str, 
        output_format: Optional[Dict[str, Any]] = None, 
        examples: Optional[List[Dict[str, str]]] = None, 
        input_variables: Optional[List[str]] = None,
        output_parser: Optional[Any] = None,
        template_type: str = "simple"
    ):
        """
        InstructionConfig 초기화
        
        Args:
            instruction (str): 기본 시스템 명령어 템플릿
            output_format (Dict[str, Any], optional): 원하는 출력 형식 (예: JSON 스키마)
            examples (List[Dict[str, str]], optional): few-shot 학습을 위한 입력-출력 예시 리스트
            input_variables (List[str], optional): instruction 템플릿에 사용될 입력 변수 목록
            output_parser (Any, optional): 출력 결과를 파싱할 파서 객체
            template_type (str, optional): 템플릿 유형 ("simple" 또는 "jinja2")
        """
        self.instruction = instruction
        self.output_format = output_format
        self.examples = examples
        self.input_variables = input_variables if input_variables is not None else []
        self.output_parser = output_parser
        self.template_type = template_type
        
        # 템플릿 유형에 따라 적절한 템플릿 객체 생성
        if template_type == "simple":
            self._template = SimplePromptTemplate(instruction, input_variables or [])
        elif template_type == "jinja2":
            if not JINJA2_AVAILABLE:
                raise ImportError(
                    "Jinja2 템플릿을 사용하려면 jinja2를 설치해야 합니다. "
                    "pip install jinja2 명령으로 설치할 수 있습니다."
                )
            self._template = Jinja2PromptTemplate(instruction, input_variables or [])
        else:
            raise ValueError(f"지원하지 않는 템플릿 유형입니다: {template_type}")
    
    def format(self, **kwargs) -> str:
        """
        instruction 템플릿에 변수 값을 채워넣어 최종 instruction 문자열을 생성합니다.
        
        Args:
            **kwargs: instruction 템플릿에 사용될 변수와 값 (키-값 쌍)
            
        Returns:
            str: 변수가 채워진 최종 instruction 문자열
        """
        return self._template.format(**kwargs)
    
    def format_instruction(self, **kwargs) -> str:
        """
        모델에 전달할 최종 instruction 문자열을 생성합니다.
        출력 형식 정보가 있다면 instruction에 추가합니다.
        
        Args:
            **kwargs: instruction 템플릿에 사용될 변수와 값 (키-값 쌍)
            
        Returns:
            str: 변수가 채워진 최종 instruction 문자열 (출력 형식 포함)
        """
        formatted_instruction = self.format(**kwargs)
        if self.output_format:
            formatted_instruction += "\n\n출력 형식은 다음과 같습니다:\n" + json.dumps(self.output_format, ensure_ascii=False, indent=2)
        
        # 출력 파서가 있는 경우 파서의 형식 지침 추가
        if self.output_parser:
            if hasattr(self.output_parser, "get_format_instructions"):
                parser_instructions = self.output_parser.get_format_instructions()
                formatted_instruction += f"\n\n{parser_instructions}"
        
        return formatted_instruction
    
    def format_examples(self) -> str:
        """
        few-shot 학습 예시들을 문자열 형태로 생성합니다.
        
        Returns:
            str: 예시 문자열
        """
        if self.examples:
            example_str = "\n\n다음은 몇 가지 예시입니다:\n"
            for example in self.examples:
                example_str += f"사용자 입력: {example['input']}\n챗봇 출력: {example['output']}\n\n"
            return example_str
        return ""
    
    def format_complete_prompt(self, **kwargs) -> str:
        """
        완전한 프롬프트를 생성합니다 (instruction + 출력 형식 + 예시).
        
        Args:
            **kwargs: instruction 템플릿에 사용될 변수와 값 (키-값 쌍)
            
        Returns:
            str: 완전한 프롬프트 문자열
        """
        formatted_instruction = self.format_instruction(**kwargs)
        examples = self.format_examples()
        return formatted_instruction + examples
    
    @classmethod
    def from_template(cls, template: str, **kwargs):
        """
        템플릿 문자열로부터 InstructionConfig 객체를 생성합니다.
        
        Args:
            template (str): 프롬프트 템플릿 문자열
            **kwargs: InstructionConfig 초기화에 필요한 추가 인자
            
        Returns:
            InstructionConfig: 생성된 InstructionConfig 객체
        """
        # 템플릿에서 입력 변수 추출
        input_variables = re.findall(r'\{([^{}]*)\}', template)
        
        # 중복 제거 및 정렬
        input_variables = sorted(set(input_variables))
        
        return cls(
            instruction=template,
            input_variables=input_variables,
            **kwargs
        )
