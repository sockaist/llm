"""
ChatBot 사용 예제
"""
import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.chatbot import ChatBot
from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser, ListOutputParser

def basic_chatbot_example():
    """
    기본 ChatBot 사용 예제
    """
    print("\n=== 기본 ChatBot 사용 예제 ===")
    
    # 기본 시스템 명령어로 ChatBot 생성
    chatbot = ChatBot(
        system_instruction="당신은 친절하고 도움이 되는 챗봇입니다."
    )
    
    # 채팅 시작
    chatbot.start_chat()
    
    # 메시지 전송
    response = chatbot.send_message("안녕하세요!")
    print(f"사용자: 안녕하세요!")
    print(f"챗봇: {response}")
    
    response = chatbot.send_message("오늘 날씨 어때요?")
    print(f"사용자: 오늘 날씨 어때요?")
    print(f"챗봇: {response}")
    
    # 대화 기록 확인
    print("\n대화 기록:")
    for message in chatbot.get_conversation_history():
        print(f"{message['role']}: {message['content']}")


def chatbot_with_instruction_config_example():
    """
    InstructionConfig를 사용한 ChatBot 예제
    """
    print("\n=== InstructionConfig를 사용한 ChatBot 예제 ===")
    
    # JSON 출력 형식을 가진 InstructionConfig 생성
    json_instruction_config = InstructionConfig(
        instruction="당신은 {product}에 대한 정보를 JSON 형식으로 제공하는 챗봇입니다.",
        output_format={
            "product_name": "제품 이름 (문자열)",
            "description": "제품 설명 (문자열)",
            "price": "제품 가격 (숫자)"
        },
        examples=[
            {"input": "최신 스마트폰 정보 알려줘", "output": '{"product_name": "갤럭시 S24", "description": "삼성의 최신 플래그십 스마트폰입니다.", "price": 1200000}'},
        ],
        input_variables=["product"],
        output_parser=JSONOutputParser()
    )
    
    # InstructionConfig를 사용한 ChatBot 생성
    chatbot = ChatBot(
        instruction_config=json_instruction_config
    )
    
    # 채팅 시작
    chatbot.start_chat()
    
    # 메시지 전송 (변수 값 포함)
    response = chatbot.send_message("최신 노트북 정보 알려줘", product="노트북")
    print(f"사용자: 최신 노트북 정보 알려줘")
    print(f"챗봇: {response}")


def chatbot_with_output_parser_example():
    """
    출력 파서를 사용한 ChatBot 예제
    """
    print("\n=== 출력 파서를 사용한 ChatBot 예제 ===")
    
    # 리스트 출력 파서를 사용한 InstructionConfig 생성
    list_instruction_config = InstructionConfig(
        instruction="당신은 사용자의 질문에 대해 항목별로 답변하는 챗봇입니다. 각 항목은 새 줄로 구분해주세요.",
        input_variables=[],
        output_parser=ListOutputParser()
    )
    
    # 출력 파서를 사용한 ChatBot 생성
    chatbot = ChatBot(
        instruction_config=list_instruction_config
    )
    
    # 채팅 시작
    chatbot.start_chat()
    
    # 메시지 전송
    response = chatbot.send_message("서울에서 가볼만한 관광지 추천해줘")
    print(f"사용자: 서울에서 가볼만한 관광지 추천해줘")
    print(f"챗봇 (리스트 형식): {response}")


if __name__ == "__main__":
    basic_chatbot_example()
    chatbot_with_instruction_config_example()
    chatbot_with_output_parser_example()
