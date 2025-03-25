"""
메모리 시스템 사용 예제
"""
import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.memory import (
    BufferMemory,
    ConversationBufferWindowMemory,
    ConversationSummaryMemory,
    ConversationTokenBufferMemory
)
from src.chatbot import ChatBot

def buffer_memory_example():
    """
    BufferMemory 사용 예제
    """
    print("\n=== BufferMemory 사용 예제 ===")
    
    # BufferMemory 생성
    memory = BufferMemory(
        memory_key="chat_history",
        input_key="input",
        output_key="output"
    )
    
    # 대화 컨텍스트 저장
    memory.save_context(
        inputs={"input": "안녕하세요!"},
        outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
    )
    
    memory.save_context(
        inputs={"input": "오늘 날씨 어때요?"},
        outputs={"output": "오늘은 맑고 화창한 날씨입니다."}
    )
    
    # 메모리 변수 로드
    memory_variables = memory.load_memory_variables()
    print(f"메모리 변수 (문자열 형식):\n{memory_variables['chat_history']}")
    
    # 메시지 객체 형식으로 로드
    message_memory = BufferMemory(
        memory_key="chat_history",
        input_key="input",
        output_key="output",
        return_messages=True
    )
    
    message_memory.save_context(
        inputs={"input": "안녕하세요!"},
        outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
    )
    
    message_memory.save_context(
        inputs={"input": "오늘 날씨 어때요?"},
        outputs={"output": "오늘은 맑고 화창한 날씨입니다."}
    )
    
    message_variables = message_memory.load_memory_variables()
    print(f"\n메모리 변수 (메시지 객체 형식):")
    for message in message_variables['chat_history']:
        print(f"입력: {message['input']}, 출력: {message['output']}")
    
    # 메모리 초기화
    memory.clear()
    cleared_variables = memory.load_memory_variables()
    print(f"\n메모리 초기화 후: {cleared_variables['chat_history']}")


def conversation_buffer_window_memory_example():
    """
    ConversationBufferWindowMemory 사용 예제
    """
    print("\n=== ConversationBufferWindowMemory 사용 예제 ===")
    
    # ConversationBufferWindowMemory 생성 (최근 2개 대화만 유지)
    memory = ConversationBufferWindowMemory(
        k=2,
        memory_key="chat_history",
        input_key="input",
        output_key="output"
    )
    
    # 여러 대화 컨텍스트 저장
    memory.save_context(
        inputs={"input": "안녕하세요!"},
        outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
    )
    
    memory.save_context(
        inputs={"input": "당신은 누구인가요?"},
        outputs={"output": "저는 AI 챗봇입니다."}
    )
    
    memory.save_context(
        inputs={"input": "오늘 날씨 어때요?"},
        outputs={"output": "오늘은 맑고 화창한 날씨입니다."}
    )
    
    # 메모리 변수 로드 (최근 2개 대화만 포함)
    memory_variables = memory.load_memory_variables()
    print(f"메모리 변수 (최근 2개 대화):\n{memory_variables['chat_history']}")
    
    # 추가 대화 저장
    memory.save_context(
        inputs={"input": "내일 날씨는 어때요?"},
        outputs={"output": "내일은 비가 올 예정입니다."}
    )
    
    # 메모리 변수 다시 로드 (최근 2개 대화만 포함, 첫 번째 대화는 제외됨)
    updated_variables = memory.load_memory_variables()
    print(f"\n메모리 변수 (추가 대화 후):\n{updated_variables['chat_history']}")


def conversation_token_buffer_memory_example():
    """
    ConversationTokenBufferMemory 사용 예제
    """
    print("\n=== ConversationTokenBufferMemory 사용 예제 ===")
    
    # ConversationTokenBufferMemory 생성 (최대 50 토큰 제한)
    memory = ConversationTokenBufferMemory(
        max_token_limit=50,
        memory_key="chat_history",
        input_key="input",
        output_key="output"
    )
    
    # 여러 대화 컨텍스트 저장
    memory.save_context(
        inputs={"input": "안녕하세요!"},
        outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
    )
    
    memory.save_context(
        inputs={"input": "인공지능에 대해 알려주세요."},
        outputs={"output": "인공지능은 인간의 학습능력, 추론능력, 지각능력을 인공적으로 구현한 컴퓨터 시스템입니다."}
    )
    
    # 메모리 변수 로드 (토큰 제한에 따라 일부 대화만 포함될 수 있음)
    memory_variables = memory.load_memory_variables()
    print(f"메모리 변수 (토큰 제한):\n{memory_variables['chat_history']}")
    
    # 현재 토큰 수 확인
    print(f"현재 토큰 수: {memory.current_token_count}")


def chatbot_with_memory_example():
    """
    메모리 시스템을 사용한 ChatBot 예제
    """
    print("\n=== 메모리 시스템을 사용한 ChatBot 예제 ===")
    
    # ChatBot 생성
    chatbot = ChatBot(
        system_instruction="당신은 친절한 도우미입니다. 이전 대화 내용을 기억하고 참조하세요."
    )
    
    # 채팅 시작
    chatbot.start_chat()
    
    # 첫 번째 메시지
    response1 = chatbot.send_message("안녕하세요! 제 이름은 홍길동입니다.")
    print(f"사용자: 안녕하세요! 제 이름은 홍길동입니다.")
    print(f"챗봇: {response1}")
    
    # 두 번째 메시지 (이전 대화 참조)
    response2 = chatbot.send_message("제 이름이 뭐였죠?")
    print(f"사용자: 제 이름이 뭐였죠?")
    print(f"챗봇: {response2}")
    
    # 대화 기록 확인
    print("\n대화 기록:")
    for message in chatbot.get_conversation_history():
        print(f"{message['role']}: {message['content']}")
    
    # 대화 기록 초기화
    chatbot.clear_conversation_history()
    print("\n대화 기록 초기화 후:")
    print(f"대화 기록 길이: {len(chatbot.get_conversation_history())}")


if __name__ == "__main__":
    buffer_memory_example()
    conversation_buffer_window_memory_example()
    conversation_token_buffer_memory_example()
    chatbot_with_memory_example()
