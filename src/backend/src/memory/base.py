"""
메모리 시스템의 기본 클래스 구현
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

class Memory(ABC):
    """
    모든 메모리 시스템의 기본 추상 클래스
    """
    
    @abstractmethod
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        대화 컨텍스트를 저장합니다.
        
        Args:
            inputs (Dict[str, Any]): 입력 데이터
            outputs (Dict[str, Any]): 출력 데이터
        """
        pass
    
    @abstractmethod
    def load_memory_variables(self) -> Dict[str, Any]:
        """
        저장된 메모리 변수를 로드합니다.
        
        Returns:
            Dict[str, Any]: 메모리 변수
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """
        메모리를 초기화합니다.
        """
        pass
