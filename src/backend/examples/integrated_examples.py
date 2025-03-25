"""
통합 사용 예제 - 모든 기능을 함께 사용하는 예제
"""
import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser, ListOutputParser
from src.chatbot import ChatBot
from src.chain import LLMChain, SequentialChain, TransformChain
from src.memory import BufferMemory, ConversationBufferWindowMemory

def integrated_example():
    """
    모든 기능을 통합한 예제 - 질문 응답 시스템
    """
    print("\n=== 통합 사용 예제: 질문 응답 시스템 ===")
    
    # 1. 메모리 시스템 설정
    memory = ConversationBufferWindowMemory(
        k=5,
        memory_key="chat_history",
        input_key="input",
        output_key="output",
        return_messages=True
    )
    
    # 2. 질문 분석을 위한 체인 설정
    question_analysis_prompt = InstructionConfig(
        instruction="다음 질문을 분석하여 주요 키워드를 추출해주세요: {question}",
        input_variables=["question"],
        output_parser=ListOutputParser()
    )
    
    question_analysis_chatbot = ChatBot(
        system_instruction="당신은 텍스트 분석 전문가입니다."
    )
    
    question_analysis_chain = LLMChain(
        chatbot=question_analysis_chatbot,
        prompt=question_analysis_prompt,
        output_key="keywords"
    )
    
    # 3. 답변 생성을 위한 체인 설정
    answer_prompt = InstructionConfig(
        instruction="""
다음 질문에 대한 답변을 JSON 형식으로 작성해주세요:
질문: {question}

추출된 키워드: {keywords}

이전 대화 내용:
{chat_history}
""",
        input_variables=["question", "keywords", "chat_history"],
        output_parser=JSONOutputParser(),
        output_format={
            "answer": "질문에 대한 답변",
            "sources": "참고 자료 (있는 경우)",
            "confidence": "답변의 확신도 (0-100)"
        }
    )
    
    answer_chatbot = ChatBot(
        system_instruction="당신은 지식이 풍부한 도우미입니다."
    )
    
    answer_chain = LLMChain(
        chatbot=answer_chatbot,
        prompt=answer_prompt,
        output_key="response"
    )
    
    # 4. 변환 체인 설정 (메모리 업데이트 및 결과 포맷팅)
    def transform_func(inputs):
        # 메모리 업데이트
        memory.save_context(
            inputs={"input": inputs["question"]},
            outputs={"output": inputs["response"]["answer"]}
        )
        
        # 결과 포맷팅
        return {
            "formatted_answer": f"답변: {inputs['response']['answer']}\n"
                               f"확신도: {inputs['response']['confidence']}%\n"
                               f"참고 자료: {inputs['response']['sources']}"
        }
    
    transform_chain = TransformChain(
        transform_func=transform_func,
        input_variables=["question", "response"],
        output_variables=["formatted_answer"]
    )
    
    # 5. 전체 체인 설정
    qa_chain = SequentialChain(
        chains=[question_analysis_chain, answer_chain, transform_chain],
        input_variables=["question"],
        output_variables=["keywords", "response", "formatted_answer"]
    )
    
    # 6. 시스템 실행
    print("질문 응답 시스템을 시작합니다. 종료하려면 '종료'를 입력하세요.")
    
    while True:
        question = input("\n질문: ")
        if question.lower() == '종료':
            break
        
        # 메모리에서 대화 기록 로드
        chat_history = memory.load_memory_variables()["chat_history"]
        chat_history_str = ""
        
        if chat_history:
            for msg in chat_history:
                chat_history_str += f"사용자: {msg['input']}\n시스템: {msg['output']}\n"
        
        # 체인 실행
        result = qa_chain.run({
            "question": question,
            "chat_history": chat_history_str
        })
        
        # 결과 출력
        print(result["formatted_answer"])
        
        # 키워드 출력 (디버깅용)
        print(f"\n[디버깅] 추출된 키워드: {result['keywords']}")

def advanced_integrated_example():
    """
    고급 통합 예제 - 다중 도메인 지식 시스템
    """
    print("\n=== 고급 통합 예제: 다중 도메인 지식 시스템 ===")
    
    # 1. 도메인 라우팅 함수
    def domain_router(inputs):
        query = inputs.get("query", "").lower()
        
        if any(word in query for word in ["과학", "물리", "화학", "생물"]):
            return "science"
        elif any(word in query for word in ["역사", "사건", "인물", "시대"]):
            return "history"
        elif any(word in query for word in ["기술", "컴퓨터", "프로그래밍", "코딩"]):
            return "technology"
        else:
            return "general"
    
    # 2. 각 도메인별 체인 설정
    # 2.1 과학 도메인
    science_prompt = InstructionConfig(
        instruction="다음 과학 관련 질문에 답변해주세요: {query}",
        input_variables=["query"],
        output_format={
            "answer": "과학적 답변",
            "field": "관련 과학 분야 (물리학, 화학, 생물학 등)",
            "confidence": "답변의 확신도 (0-100)"
        },
        output_parser=JSONOutputParser()
    )
    
    science_chatbot = ChatBot(
        system_instruction="당신은 과학 전문가입니다."
    )
    
    science_chain = LLMChain(
        chatbot=science_chatbot,
        prompt=science_prompt,
        output_key="result"
    )
    
    # 2.2 역사 도메인
    history_prompt = InstructionConfig(
        instruction="다음 역사 관련 질문에 답변해주세요: {query}",
        input_variables=["query"],
        output_format={
            "answer": "역사적 답변",
            "period": "관련 시대 또는 연도",
            "confidence": "답변의 확신도 (0-100)"
        },
        output_parser=JSONOutputParser()
    )
    
    history_chatbot = ChatBot(
        system_instruction="당신은 역사 전문가입니다."
    )
    
    history_chain = LLMChain(
        chatbot=history_chatbot,
        prompt=history_prompt,
        output_key="result"
    )
    
    # 2.3 기술 도메인
    technology_prompt = InstructionConfig(
        instruction="다음 기술 관련 질문에 답변해주세요: {query}",
        input_variables=["query"],
        output_format={
            "answer": "기술적 답변",
            "tech_area": "관련 기술 분야",
            "confidence": "답변의 확신도 (0-100)"
        },
        output_parser=JSONOutputParser()
    )
    
    technology_chatbot = ChatBot(
        system_instruction="당신은 기술 전문가입니다."
    )
    
    technology_chain = LLMChain(
        chatbot=technology_chatbot,
        prompt=technology_prompt,
        output_key="result"
    )
    
    # 2.4 일반 도메인
    general_prompt = InstructionConfig(
        instruction="다음 질문에 답변해주세요: {query}",
        input_variables=["query"],
        output_format={
            "answer": "일반적인 답변",
            "topic": "관련 주제",
            "confidence": "답변의 확신도 (0-100)"
        },
        output_parser=JSONOutputParser()
    )
    
    general_chatbot = ChatBot(
        system_instruction="당신은 다양한 지식을 갖춘 도우미입니다."
    )
    
    general_chain = LLMChain(
        chatbot=general_chatbot,
        prompt=general_prompt,
        output_key="result"
    )
    
    # 3. 도메인 라우터 체인 설정
    from src.chain import RouterChain
    
    router_chain = RouterChain(
        router_func=domain_router,
        destination_chains={
            "science": science_chain,
            "history": history_chain,
            "technology": technology_chain,
            "general": general_chain
        }
    )
    
    # 4. 결과 포맷팅 체인
    def format_result(inputs):
        result = inputs["result"]
        domain = inputs.get("_router_key", "unknown")
        
        formatted_answer = f"[도메인: {domain}]\n"
        formatted_answer += f"답변: {result['answer']}\n"
        formatted_answer += f"확신도: {result['confidence']}%\n"
        
        if domain == "science":
            formatted_answer += f"과학 분야: {result['field']}"
        elif domain == "history":
            formatted_answer += f"시대/연도: {result['period']}"
        elif domain == "technology":
            formatted_answer += f"기술 분야: {result['tech_area']}"
        elif domain == "general":
            formatted_answer += f"관련 주제: {result['topic']}"
        
        return {"formatted_answer": formatted_answer, "_router_key": domain}
    
    format_chain = TransformChain(
        transform_func=format_result,
        input_variables=["result", "_router_key"],
        output_variables=["formatted_answer", "_router_key"]
    )
    
    # 5. 전체 체인 설정
    from src.chain import SequentialChain
    
    knowledge_chain = SequentialChain(
        chains=[router_chain, format_chain],
        input_variables=["query"],
        output_variables=["formatted_answer", "_router_key"]
    )
    
    # 6. 시스템 실행
    print("다중 도메인 지식 시스템을 시작합니다. 종료하려면 '종료'를 입력하세요.")
    print("도메인: 과학, 역사, 기술, 일반")
    
    while True:
        query = input("\n질문: ")
        if query.lower() == '종료':
            break
        
        # 체인 실행
        result = knowledge_chain.run({"query": query})
        
        # 결과 출력
        print(result["formatted_answer"])

if __name__ == "__main__":
    integrated_example()
    advanced_integrated_example()
