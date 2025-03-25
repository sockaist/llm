"""
체인 기능 사용 예제
"""
import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.chain import Chain, LLMChain, SequentialChain, RouterChain, TransformChain
from src.chatbot import ChatBot
from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser, ListOutputParser

def llm_chain_example():
    """
    LLMChain 사용 예제
    """
    print("\n=== LLMChain 사용 예제 ===")
    
    # 프롬프트 템플릿 생성
    prompt = InstructionConfig(
        instruction="다음 주제에 대한 세 가지 핵심 포인트를 알려주세요: {topic}",
        input_variables=["topic"],
        output_parser=ListOutputParser()
    )
    
    # ChatBot 생성
    chatbot = ChatBot(
        system_instruction="당신은 교육 콘텐츠 전문가입니다."
    )
    
    # LLMChain 생성
    chain = LLMChain(
        chatbot=chatbot,
        prompt=prompt,
        output_key="points"
    )
    
    # 체인 실행
    result = chain.run({"topic": "인공지능의 미래", "user_input": "인공지능의 미래에 대해 알려주세요"})
    print(f"입력: 인공지능의 미래")
    print(f"출력 (points): {result['points']}")


def sequential_chain_example():
    """
    SequentialChain 사용 예제
    """
    print("\n=== SequentialChain 사용 예제 ===")
    
    # 첫 번째 체인: 주제에 대한 핵심 포인트 생성
    points_prompt = InstructionConfig(
        instruction="다음 주제에 대한 세 가지 핵심 포인트를 알려주세요: {topic}",
        input_variables=["topic"],
        output_parser=ListOutputParser()
    )
    
    points_chatbot = ChatBot(
        system_instruction="당신은 교육 콘텐츠 전문가입니다."
    )
    
    points_chain = LLMChain(
        chatbot=points_chatbot,
        prompt=points_prompt,
        output_key="points"
    )
    
    # 두 번째 체인: 핵심 포인트를 바탕으로 요약 생성
    summary_prompt = InstructionConfig(
        instruction="다음 핵심 포인트를 바탕으로 {topic}에 대한 간결한 요약을 작성해주세요:\n{points}",
        input_variables=["topic", "points"]
    )
    
    summary_chatbot = ChatBot(
        system_instruction="당신은 전문 작가입니다."
    )
    
    summary_chain = LLMChain(
        chatbot=summary_chatbot,
        prompt=summary_prompt,
        output_key="summary"
    )
    
    # SequentialChain 생성
    sequential_chain = SequentialChain(
        chains=[points_chain, summary_chain],
        input_variables=["topic"],
        output_variables=["points", "summary"]
    )
    
    # 체인 실행
    result = sequential_chain.run({"topic": "기후 변화"})
    print(f"입력: 기후 변화")
    print(f"중간 출력 (points): {result['points']}")
    print(f"최종 출력 (summary): {result['summary']}")


def router_chain_example():
    """
    RouterChain 사용 예제
    """
    print("\n=== RouterChain 사용 예제 ===")
    
    # 라우팅 함수 정의
    def router_func(inputs):
        query = inputs.get("query", "").lower()
        if "날씨" in query or "기온" in query:
            return "weather"
        elif "뉴스" in query or "소식" in query:
            return "news"
        else:
            return "general"
    
    # 날씨 체인
    weather_prompt = InstructionConfig(
        instruction="다음 지역의 날씨 정보를 제공해주세요: {query}",
        input_variables=["query"]
    )
    
    weather_chatbot = ChatBot(
        system_instruction="당신은 기상 정보 전문가입니다."
    )
    
    weather_chain = LLMChain(
        chatbot=weather_chatbot,
        prompt=weather_prompt,
        output_key="response"
    )
    
    # 뉴스 체인
    news_prompt = InstructionConfig(
        instruction="다음 주제에 대한 최신 뉴스를 알려주세요: {query}",
        input_variables=["query"]
    )
    
    news_chatbot = ChatBot(
        system_instruction="당신은 뉴스 기자입니다."
    )
    
    news_chain = LLMChain(
        chatbot=news_chatbot,
        prompt=news_prompt,
        output_key="response"
    )
    
    # 일반 체인
    general_prompt = InstructionConfig(
        instruction="다음 질문에 답변해주세요: {query}",
        input_variables=["query"]
    )
    
    general_chatbot = ChatBot(
        system_instruction="당신은 친절한 도우미입니다."
    )
    
    general_chain = LLMChain(
        chatbot=general_chatbot,
        prompt=general_prompt,
        output_key="response"
    )
    
    # RouterChain 생성
    router_chain = RouterChain(
        router_func=router_func,
        destination_chains={
            "weather": weather_chain,
            "news": news_chain,
            "general": general_chain
        }
    )
    
    # 체인 실행 (날씨 질문)
    weather_result = router_chain.run({"query": "서울 날씨 어때요?"})
    print(f"입력: 서울 날씨 어때요?")
    print(f"출력 (weather): {weather_result['response']}")
    
    # 체인 실행 (뉴스 질문)
    news_result = router_chain.run({"query": "최신 기술 뉴스 알려줘"})
    print(f"입력: 최신 기술 뉴스 알려줘")
    print(f"출력 (news): {news_result['response']}")
    
    # 체인 실행 (일반 질문)
    general_result = router_chain.run({"query": "파이썬이란 무엇인가요?"})
    print(f"입력: 파이썬이란 무엇인가요?")
    print(f"출력 (general): {general_result['response']}")


def transform_chain_example():
    """
    TransformChain 사용 예제
    """
    print("\n=== TransformChain 사용 예제 ===")
    
    # 변환 함수 정의
    def transform_func(inputs):
        text = inputs.get("text", "")
        
        # 단어 수 계산
        word_count = len(text.split())
        
        # 문자 수 계산
        char_count = len(text)
        
        # 문장 수 계산
        sentence_count = len([s for s in text.split('.') if s.strip()])
        
        return {
            "word_count": word_count,
            "char_count": char_count,
            "sentence_count": sentence_count,
            "text": text  # 원본 텍스트도 유지
        }
    
    # TransformChain 생성
    transform_chain = TransformChain(
        transform_func=transform_func,
        input_variables=["text"],
        output_variables=["word_count", "char_count", "sentence_count", "text"]
    )
    
    # 체인 실행
    text = "이것은 예시 문장입니다. 이 문장은 텍스트 분석을 위한 것입니다. 파이썬으로 텍스트를 분석해봅시다."
    result = transform_chain.run({"text": text})
    
    print(f"입력 텍스트: {text}")
    print(f"단어 수: {result['word_count']}")
    print(f"문자 수: {result['char_count']}")
    print(f"문장 수: {result['sentence_count']}")


if __name__ == "__main__":
    llm_chain_example()
    sequential_chain_example()
    router_chain_example()
    transform_chain_example()
