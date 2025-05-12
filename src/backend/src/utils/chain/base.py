"""
체인 기능의 기본 클래스 구현
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, Callable

class Chain(ABC):
    """
    모든 체인의 기본 추상 클래스
    """
    
    @abstractmethod
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        체인을 실행합니다.
        
        Args:
            inputs (Dict[str, Any]): 체인에 전달할 입력 데이터
            
        Returns:
            Dict[str, Any]: 체인의 출력 데이터
        """
        pass
    
    def __call__(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        체인을 함수처럼 호출할 수 있게 합니다.
        
        Args:
            inputs (Dict[str, Any]): 체인에 전달할 입력 데이터
            
        Returns:
            Dict[str, Any]: 체인의 출력 데이터
        """
        return self.run(inputs)
