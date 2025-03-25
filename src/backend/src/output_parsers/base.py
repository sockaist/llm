"""
출력 파서 기본 클래스 구현
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type, Optional, Union, TypeVar, Generic

T = TypeVar('T')

class BaseOutputParser(Generic[T], ABC):
    """
    모든 출력 파서의 기본 추상 클래스
    """
    
    @abstractmethod
    def parse(self, text: str) -> T:
        """
        텍스트를 파싱하여 구조화된 출력으로 변환합니다.
        
        Args:
            text (str): 파싱할 텍스트
            
        Returns:
            T: 파싱된 결과
        """
        pass
    
    def get_format_instructions(self) -> str:
        """
        파서에 맞는 출력 형식 지침을 반환합니다.
        
        Returns:
            str: 출력 형식 지침
        """
        return ""
