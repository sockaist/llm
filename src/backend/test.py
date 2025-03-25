from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser
from src.chatbot import ChatBot
from src.chain import LLMChain, SequentialChain
from src.memory import ConversationBufferWindowMemory
import json


# 2.1. 사용자 쿼리 목적 확인 프롬프트
purpose_check_prompt = InstructionConfig(
    instruction="사용자의 다음 질문이 심리 상담과 관련된 내용인지 판단해주세요. 관련 있다면 'yes', 아니면 'no'라고 답해주세요.\n\n사용자 질문: {query}",
    input_variables=["query"]
)
purpose_check_chatbot = ChatBot(
    system_instruction="당신은 심리 상담 관련 질문인지 여부를 판단하는 전문가입니다."
)
purpose_check_chain = LLMChain(
    chatbot=purpose_check_chatbot,
    prompt=purpose_check_prompt,
    output_key="purpose_check"
)

# 2.2. 상담 응답 생성 및 우울증 척도 판단 프롬프트
counseling_prompt = InstructionConfig(
    instruction="""
사용자의 다음 질문에 대해 심리 상담사로서 답변해주세요.
답변과 함께 사용자의 우울증 척도를 0에서 100 사이의 숫자로 판단하고, 그 판단 근거를 간략하게 설명해주세요.
결과는 JSON 형식으로 출력해야 합니다.

사용자 질문: {query}

출력 형식:
{{
  "answer": "상담 답변 내용",
  "depression_scale": (0~100 사이의 숫자),
  "reasoning": "우울증 척도 판단 근거"
}}
""",
    input_variables=["query"],
    output_parser=JSONOutputParser()
)
counseling_chatbot = ChatBot(
    system_instruction="당신은 숙련된 심리 상담사입니다."
)
counseling_chain = LLMChain(
    chatbot=counseling_chatbot,
    prompt=counseling_prompt,
    output_key="counseling_response"
)

verification_prompt = InstructionConfig(
    instruction="""
다음 사용자 입력, 심리 상담 챗봇의 답변, 그리고 우울증 척도 판단 근거가 적절한지 검토해주세요.

사용자 입력: {user_input}
챗봇 답변: {chatbot_response}
판단 근거: {reasoning}

다음 기준에 따라 판단하고, 문제가 있다면 구체적인 지적과 함께 '올바르지 않음'이라고 답해주세요. 모든 것이 적절하다면 '올바름'이라고 답해주세요.

- 사용자 입력이 심리 상담 주제에 적합한가?
- 챗봇의 답변이 사용자의 질문에 적절하고 도움이 되는가?
- 우울증 척도 판단이 답변 내용 및 사용자 입력과 일관성이 있는가?
- 답변 형식이 JSON 형식에 맞게 출력되었는가?
""",
    input_variables=["user_input", "chatbot_response", "reasoning"]
)
verification_chatbot = ChatBot(
    system_instruction="당신은 심리 상담 답변의 적절성을 검토하는 전문가입니다."
)
verification_chain = LLMChain(
    chatbot=verification_chatbot,
    prompt=verification_prompt,
    output_key="verification_result"
)
def psychological_counseling_pipeline(query):
    # 1. 사용자 쿼리 목적 확인
    purpose_check_result = purpose_check_chain.run({"query": query})
    if purpose_check_result["purpose_check"].lower() != 'yes':
        return "죄송합니다. 해당 질문은 심리 상담과 관련이 없는 것 같습니다."

    # 2. 상담 응답 생성 및 우울증 척도 판단 (최대 3번 재시도)
    for attempt in range(3):
        counseling_result = counseling_chain.run({"query": query})
        counseling_data = counseling_result["counseling_response"]

        # 3. 검증 챗봇에게 전달할 정보 추출
        user_input = query
        chatbot_response = counseling_data.get("answer", "")
        reasoning = counseling_data.get("reasoning", "")

        # 4. 검증
        verification_result = verification_chain.run({
            "user_input": user_input,
            "chatbot_response": chatbot_response,
            "reasoning": reasoning
        })

        if "올바름" in verification_result["verification_result"]:
            return counseling_data
        else:
            print(f"검증 실패 (시도 {attempt + 1}): {verification_result['verification_result']}")
            # 필요하다면 실패 이유를 바탕으로 프롬프트를 조정하거나 로깅할 수 있습니다.

    return {"error": "상담 답변 검증에 실패했습니다. 전문가의 도움이 필요할 수 있습니다."}

# 5. 실행 예시
if __name__ == "__main__":
    while True:
        user_query = input("상담이 필요하신 내용을 말씀해주세요 ('종료' 입력 시 종료): ")
        if user_query.lower() == '종료':
            break

        result = psychological_counseling_pipeline(user_query)
        print(json.dumps(result, ensure_ascii=False, indent=2))