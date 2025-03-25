"""
다양한 메모리 시스템 구현
"""
from typing import Any, Dict, List, Optional, Union, Deque
from collections import deque
import json
from .base import Memory

class BufferMemory(Memory):
    """
    단순한 버퍼 기반 메모리 시스템
    """
    
    def __init__(
        self, 
        memory_key: str = "history",
        input_key: str = "input",
        output_key: str = "output",
        return_messages: bool = False
    ):
        """
        BufferMemory 초기화
        
        Args:
            memory_key (str, optional): 메모리 변수 키 이름. 기본값은 "history"입니다.
            input_key (str, optional): 입력 데이터 키 이름. 기본값은 "input"입니다.
            output_key (str, optional): 출력 데이터 키 이름. 기본값은 "output"입니다.
            return_messages (bool, optional): 메시지 객체 형태로 반환할지 여부. 기본값은 False입니다.
        """
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key
        self.return_messages = return_messages
        self.buffer = []
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        대화 컨텍스트를 저장합니다.
        
        Args:
            inputs (Dict[str, Any]): 입력 데이터
            outputs (Dict[str, Any]): 출력 데이터
        """
        if self.input_key not in inputs:
            raise ValueError(f"입력 키 '{self.input_key}'가 입력 데이터에 없습니다.")
        if self.output_key not in outputs:
            raise ValueError(f"출력 키 '{self.output_key}'가 출력 데이터에 없습니다.")
        
        input_str = inputs[self.input_key]
        output_str = outputs[self.output_key]
        
        self.buffer.append({"input": input_str, "output": output_str})
    
    def load_memory_variables(self) -> Dict[str, Any]:
        """
        저장된 메모리 변수를 로드합니다.
        
        Returns:
            Dict[str, Any]: 메모리 변수
        """
        if self.return_messages:
            return {self.memory_key: self.buffer}
        else:
            # 문자열 형태로 변환
            result = ""
            for interaction in self.buffer:
                result += f"Human: {interaction['input']}\nAI: {interaction['output']}\n"
            return {self.memory_key: result}
    
    def clear(self) -> None:
        """
        메모리를 초기화합니다.
        """
        self.buffer = []


class ConversationBufferWindowMemory(Memory):
    """
    최근 k개의 대화만 기억하는 윈도우 기반 메모리 시스템
    """
    
    def __init__(
        self, 
        k: int = 5,
        memory_key: str = "history",
        input_key: str = "input",
        output_key: str = "output",
        return_messages: bool = False
    ):
        """
        ConversationBufferWindowMemory 초기화
        
        Args:
            k (int, optional): 기억할 최근 대화의 수. 기본값은 5입니다.
            memory_key (str, optional): 메모리 변수 키 이름. 기본값은 "history"입니다.
            input_key (str, optional): 입력 데이터 키 이름. 기본값은 "input"입니다.
            output_key (str, optional): 출력 데이터 키 이름. 기본값은 "output"입니다.
            return_messages (bool, optional): 메시지 객체 형태로 반환할지 여부. 기본값은 False입니다.
        """
        self.k = k
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key
        self.return_messages = return_messages
        self.buffer = deque(maxlen=k)
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        대화 컨텍스트를 저장합니다.
        
        Args:
            inputs (Dict[str, Any]): 입력 데이터
            outputs (Dict[str, Any]): 출력 데이터
        """
        if self.input_key not in inputs:
            raise ValueError(f"입력 키 '{self.input_key}'가 입력 데이터에 없습니다.")
        if self.output_key not in outputs:
            raise ValueError(f"출력 키 '{self.output_key}'가 출력 데이터에 없습니다.")
        
        input_str = inputs[self.input_key]
        output_str = outputs[self.output_key]
        
        self.buffer.append({"input": input_str, "output": output_str})
    
    def load_memory_variables(self) -> Dict[str, Any]:
        """
        저장된 메모리 변수를 로드합니다.
        
        Returns:
            Dict[str, Any]: 메모리 변수
        """
        if self.return_messages:
            return {self.memory_key: list(self.buffer)}
        else:
            # 문자열 형태로 변환
            result = ""
            for interaction in self.buffer:
                result += f"Human: {interaction['input']}\nAI: {interaction['output']}\n"
            return {self.memory_key: result}
    
    def clear(self) -> None:
        """
        메모리를 초기화합니다.
        """
        self.buffer.clear()


class ConversationSummaryMemory(Memory):
    """
    대화 내용을 요약하여 저장하는 메모리 시스템
    """
    
    def __init__(
        self, 
        chatbot,
        memory_key: str = "history_summary",
        input_key: str = "input",
        output_key: str = "output"
    ):
        """
        ConversationSummaryMemory 초기화
        
        Args:
            chatbot: 요약에 사용할 챗봇 인스턴스
            memory_key (str, optional): 메모리 변수 키 이름. 기본값은 "history_summary"입니다.
            input_key (str, optional): 입력 데이터 키 이름. 기본값은 "input"입니다.
            output_key (str, optional): 출력 데이터 키 이름. 기본값은 "output"입니다.
        """
        self.chatbot = chatbot
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key
        self.buffer = []
        self.summary = ""
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        대화 컨텍스트를 저장합니다.
        
        Args:
            inputs (Dict[str, Any]): 입력 데이터
            outputs (Dict[str, Any]): 출력 데이터
        """
        if self.input_key not in inputs:
            raise ValueError(f"입력 키 '{self.input_key}'가 입력 데이터에 없습니다.")
        if self.output_key not in outputs:
            raise ValueError(f"출력 키 '{self.output_key}'가 출력 데이터에 없습니다.")
        
        input_str = inputs[self.input_key]
        output_str = outputs[self.output_key]
        
        # 버퍼에 대화 추가
        self.buffer.append({"input": input_str, "output": output_str})
        
        # 버퍼가 일정 크기 이상이면 요약 생성
        if len(self.buffer) >= 5:
            self._summarize()
    
    def _summarize(self) -> None:
        """
        버퍼에 있는 대화를 요약합니다.
        """
        if not self.buffer:
            return
        
        # 현재 대화 내용 생성
        conversation = ""
        for interaction in self.buffer:
            conversation += f"Human: {interaction['input']}\nAI: {interaction['output']}\n"
        
        # 요약 프롬프트 생성
        if self.summary:
            prompt = f"다음은 이전 대화의 요약입니다:\n{self.summary}\n\n다음은 새로운 대화입니다:\n{conversation}\n\n이전 요약과 새로운 대화를 종합하여 전체 대화의 간결한 요약을 작성해주세요."
        else:
            prompt = f"다음 대화의 간결한 요약을 작성해주세요:\n{conversation}"
        
        # 챗봇을 사용하여 요약 생성
        try:
            self.summary = self.chatbot.send_message(prompt)
            # 버퍼 초기화
            self.buffer = []
        except Exception as e:
            print(f"대화 요약 중 오류 발생: {e}")
    
    def load_memory_variables(self) -> Dict[str, Any]:
        """
        저장된 메모리 변수를 로드합니다.
        
        Returns:
            Dict[str, Any]: 메모리 변수
        """
        # 버퍼에 대화가 있으면 요약 업데이트
        if self.buffer:
            self._summarize()
        
        return {self.memory_key: self.summary}
    
    def clear(self) -> None:
        """
        메모리를 초기화합니다.
        """
        self.buffer = []
        self.summary = ""


class ConversationTokenBufferMemory(Memory):
    """
    토큰 수를 기준으로 대화를 관리하는 메모리 시스템
    """
    
    def __init__(
        self, 
        max_token_limit: int = 2000,
        memory_key: str = "history",
        input_key: str = "input",
        output_key: str = "output",
        return_messages: bool = False
    ):
        """
        ConversationTokenBufferMemory 초기화
        
        Args:
            max_token_limit (int, optional): 최대 토큰 수 제한. 기본값은 2000입니다.
            memory_key (str, optional): 메모리 변수 키 이름. 기본값은 "history"입니다.
            input_key (str, optional): 입력 데이터 키 이름. 기본값은 "input"입니다.
            output_key (str, optional): 출력 데이터 키 이름. 기본값은 "output"입니다.
            return_messages (bool, optional): 메시지 객체 형태로 반환할지 여부. 기본값은 False입니다.
        """
        self.max_token_limit = max_token_limit
        self.memory_key = memory_key
        self.input_key = input_key
        self.output_key = output_key
        self.return_messages = return_messages
        self.buffer = []
        self.current_token_count = 0
    
    def _count_tokens(self, text: str) -> int:
        """
        텍스트의 토큰 수를 대략적으로 계산합니다.
        
        Args:
            text (str): 계산할 텍스트
            
        Returns:
            int: 대략적인 토큰 수
        """
        # 간단한 구현: 공백으로 분할하여 단어 수 계산
        # 실제 구현에서는 토크나이저를 사용해야 합니다.
        return len(text.split())
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> None:
        """
        대화 컨텍스트를 저장합니다.
        
        Args:
            inputs (Dict[str, Any]): 입력 데이터
            outputs (Dict[str, Any]): 출력 데이터
        """
        if self.input_key not in inputs:
            raise ValueError(f"입력 키 '{self.input_key}'가 입력 데이터에 없습니다.")
        if self.output_key not in outputs:
            raise ValueError(f"출력 키 '{self.output_key}'가 출력 데이터에 없습니다.")
        
        input_str = inputs[self.input_key]
        output_str = outputs[self.output_key]
        
        # 새 대화의 토큰 수 계산
        input_tokens = self._count_tokens(input_str)
        output_tokens = self._count_tokens(output_str)
        new_tokens = input_tokens + output_tokens
        
        # 새 대화 추가
        self.buffer.append({"input": input_str, "output": output_str, "tokens": new_tokens})
        self.current_token_count += new_tokens
        
        # 토큰 제한 초과 시 오래된 대화부터 제거
        while self.current_token_count > self.max_token_limit and self.buffer:
            removed = self.buffer.pop(0)
            self.current_token_count -= removed["tokens"]
    
    def load_memory_variables(self) -> Dict[str, Any]:
        """
        저장된 메모리 변수를 로드합니다.
        
        Returns:
            Dict[str, Any]: 메모리 변수
        """
        if self.return_messages:
            # 토큰 수 정보 제외하고 반환
            clean_buffer = [{"input": item["input"], "output": item["output"]} for item in self.buffer]
            return {self.memory_key: clean_buffer}
        else:
            # 문자열 형태로 변환
            result = ""
            for interaction in self.buffer:
                result += f"Human: {interaction['input']}\nAI: {interaction['output']}\n"
            return {self.memory_key: result}
    
    def clear(self) -> None:
        """
        메모리를 초기화합니다.
        """
        self.buffer = []
        self.current_token_count = 0
