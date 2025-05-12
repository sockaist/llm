"""
다양한 체인 구현
"""
from typing import Any, Dict, List, Optional, Union, Callable
from .base import Chain
from ..prompt import InstructionConfig
from ..chatbot.chatbot import ChatBot

class LLMChain(Chain):
    """
    LLM을 사용하는 기본 체인
    """
    
    def __init__(
        self, 
        chatbot: ChatBot,
        prompt: InstructionConfig,
        output_key: str = "output"
    ):
        """
        LLMChain 초기화
        
        Args:
            chatbot (ChatBot): 사용할 챗봇 인스턴스
            prompt (InstructionConfig): 사용할 프롬프트 템플릿
            output_key (str, optional): 출력 결과를 저장할 키 이름. 기본값은 "output"입니다.
        """
        self.chatbot = chatbot
        self.prompt = prompt
        self.output_key = output_key
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        체인을 실행합니다.
        
        Args:
            inputs (Dict[str, Any]): 체인에 전달할 입력 데이터
            
        Returns:
            Dict[str, Any]: 체인의 출력 데이터
        """
        # 챗봇이 실행 중이 아니면 시작
        if not self.chatbot.is_running():
            self.chatbot.start_chat()
        
        # 프롬프트 템플릿에 입력 데이터 적용
        user_input = inputs.get("user_input", "")
        
        # 챗봇에 메시지 전송
        response = self.chatbot.send_message(user_input, **inputs)
        
        # 결과 반환
        return {self.output_key: response}


class SequentialChain(Chain):
    """
    여러 체인을 순차적으로 실행하는 체인
    """
    
    def __init__(
        self, 
        chains: List[Chain],
        input_variables: List[str],
        output_variables: List[str]
    ):
        """
        SequentialChain 초기화
        
        Args:
            chains (List[Chain]): 순차적으로 실행할 체인 목록
            input_variables (List[str]): 체인에 필요한 입력 변수 목록
            output_variables (List[str]): 체인에서 생성할 출력 변수 목록
        """
        self.chains = chains
        self.input_variables = input_variables
        self.output_variables = output_variables
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        체인을 실행합니다.
        
        Args:
            inputs (Dict[str, Any]): 체인에 전달할 입력 데이터
            
        Returns:
            Dict[str, Any]: 체인의 출력 데이터
        """
        # 입력 변수 검증
        for var in self.input_variables:
            if var not in inputs:
                raise ValueError(f"입력 변수 '{var}'가 제공되지 않았습니다.")
        
        # 현재 상태 초기화
        current_inputs = inputs.copy()
        
        # 각 체인 순차적으로 실행
        for chain in self.chains:
            outputs = chain.run(current_inputs)
            current_inputs.update(outputs)
        
        # 출력 변수만 추출하여 반환
        return {key: current_inputs[key] for key in self.output_variables if key in current_inputs}


class RouterChain(Chain):
    """
    조건에 따라 다른 체인을 실행하는 라우터 체인
    """
    
    def __init__(
        self, 
        router_func: Callable[[Dict[str, Any]], str],
        destination_chains: Dict[str, Chain],
        default_chain: Optional[Chain] = None
    ):
        """
        RouterChain 초기화
        
        Args:
            router_func (Callable[[Dict[str, Any]], str]): 라우팅 결정을 위한 함수
            destination_chains (Dict[str, Chain]): 라우팅 대상 체인 맵
            default_chain (Chain, optional): 기본 체인. 기본값은 None입니다.
        """
        self.router_func = router_func
        self.destination_chains = destination_chains
        self.default_chain = default_chain
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        체인을 실행합니다.
        
        Args:
            inputs (Dict[str, Any]): 체인에 전달할 입력 데이터
            
        Returns:
            Dict[str, Any]: 체인의 출력 데이터
            
        Raises:
            ValueError: 라우팅 대상 체인이 없고 기본 체인도 없는 경우
        """
        # 라우팅 결정
        destination_key = self.router_func(inputs)
        
        # 대상 체인 선택
        if destination_key in self.destination_chains:
            chain = self.destination_chains[destination_key]
        elif self.default_chain:
            chain = self.default_chain
        else:
            raise ValueError(f"라우팅 대상 '{destination_key}'에 해당하는 체인이 없고 기본 체인도 설정되지 않았습니다.")
        
        # 선택된 체인 실행
        return chain.run(inputs)


class TransformChain(Chain):
    """
    입력 데이터를 변환하는 체인
    """
    
    def __init__(
        self, 
        transform_func: Callable[[Dict[str, Any]], Dict[str, Any]],
        input_variables: List[str],
        output_variables: List[str]
    ):
        """
        TransformChain 초기화
        
        Args:
            transform_func (Callable[[Dict[str, Any]], Dict[str, Any]]): 변환 함수
            input_variables (List[str]): 체인에 필요한 입력 변수 목록
            output_variables (List[str]): 체인에서 생성할 출력 변수 목록
        """
        self.transform_func = transform_func
        self.input_variables = input_variables
        self.output_variables = output_variables
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        체인을 실행합니다.
        
        Args:
            inputs (Dict[str, Any]): 체인에 전달할 입력 데이터
            
        Returns:
            Dict[str, Any]: 체인의 출력 데이터
        """
        # 입력 변수 검증
        for var in self.input_variables:
            if var not in inputs:
                raise ValueError(f"입력 변수 '{var}'가 제공되지 않았습니다.")
        
        # 변환 함수 실행
        outputs = self.transform_func(inputs)
        
        # 출력 변수 검증
        for var in self.output_variables:
            if var not in outputs:
                raise ValueError(f"변환 함수가 필요한 출력 변수 '{var}'를 생성하지 않았습니다.")
        
        # 출력 변수만 추출하여 반환
        return {key: outputs[key] for key in self.output_variables}
