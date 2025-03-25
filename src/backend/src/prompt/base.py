"""
기본 프롬프트 템플릿 시스템 구현
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union


class BasePromptTemplate(ABC):
    """
    모든 프롬프트 템플릿의 기본 추상 클래스
    """
    
    @abstractmethod
    def format(self, **kwargs) -> str:
        """
        프롬프트 템플릿에 변수를 채워 최종 프롬프트 문자열을 생성합니다.
        
        Args:
            **kwargs: 프롬프트 템플릿에 사용될 변수와 값 (키-값 쌍)
            
        Returns:
            str: 변수가 채워진 최종 프롬프트 문자열
        """
        pass
    
    @property
    @abstractmethod
    def input_variables(self) -> List[str]:
        """
        프롬프트 템플릿에 필요한 입력 변수 목록을 반환합니다.
        
        Returns:
            List[str]: 입력 변수 목록
        """
        pass


class StringPromptTemplate(BasePromptTemplate):
    """
    문자열 기반 프롬프트 템플릿의 기본 클래스
    """
    
    def __init__(self, template: str, input_variables: List[str]):
        """
        StringPromptTemplate 초기화
        
        Args:
            template (str): 프롬프트 템플릿 문자열
            input_variables (List[str]): 프롬프트 템플릿에 필요한 입력 변수 목록
        """
        self._template = template
        self._input_variables = input_variables
    
    @property
    def template(self) -> str:
        """
        프롬프트 템플릿 문자열을 반환합니다.
        
        Returns:
            str: 프롬프트 템플릿 문자열
        """
        return self._template
    
    @property
    def input_variables(self) -> List[str]:
        """
        프롬프트 템플릿에 필요한 입력 변수 목록을 반환합니다.
        
        Returns:
            List[str]: 입력 변수 목록
        """
        return self._input_variables
    
    def _validate_variables(self, **kwargs) -> None:
        """
        제공된 변수가 프롬프트 템플릿에 필요한 모든 변수를 포함하는지 검증합니다.
        
        Args:
            **kwargs: 프롬프트 템플릿에 사용될 변수와 값 (키-값 쌍)
            
        Raises:
            ValueError: 필요한 변수가 제공되지 않은 경우
        """
        missing_vars = set(self.input_variables) - set(kwargs.keys())
        if missing_vars:
            raise ValueError(f"프롬프트 템플릿에 필요한 변수 {missing_vars}가 제공되지 않았습니다.")
