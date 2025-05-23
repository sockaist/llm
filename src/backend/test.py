from src.utils.chain import RouterChain, LLMChain
from src.utils.chatbot import ChatBot
from src.utils.output_parsers import JSONOutputParser
from src.utils.prompt import InstructionConfig
import google.generativeai as genai
from typing import Dict, Any, List, Optional
import json
import os
from datetime import datetime

class InputChecker:
    """
    Checks and validates user input using a chatbot powered by the Google Gemini API.
    This class loads configuration from a JSON file and uses a chatbot to process and validate user queries.
    """
    def __init__(self, api_key: str, config_file_path: str = None):
        """
\ㅣ
        Args:
            api_key (str): Google API 키
        """
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

        # JSON 출력 파서 생성
        self.json_parser = JSONOutputParser()
        
        # 기본 설정 파일 경로 설정
        if config_file_path is None:
            config_file_path = os.path.join(os.path.dirname(__file__), "/Users/bagjimin/Desktop/project/chatbot/src/backend/src/llm/utils_json/inputchecker.json")

        # 설정 파일 로드
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 시스템 프롬프트 설정
        self.checker_config = InstructionConfig(
            instruction=config['instruction'],
            output_parser=self.json_parser,
            output_format=config['output_format'],
            examples=config['examples']
        )

        self.checker = ChatBot(
                    model_name="gemini-2.0-flash",
                    temperature=0.5,  # 일관된 응답을 위해 낮은 온도 설정
                    max_output_tokens=1024,
                    instruction_config=self.checker_config,
                    api_key=self.api_key
                )

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """
        사용자 쿼리 처리

        Args:
            user_message (str): 사용자 메시지

        Returns:
            Dict[str, Any]: 상담 응답
        """
        # 챗봇이 실행 중이 아니면 시작
        if not self.checker.is_running():
            self.checker.start_chat()

        # 사용자 메시지 처리
        response = self.checker.send_message(user_message)

        # 응답이 딕셔너리가 아니면 변환
        if not isinstance(response, dict):
            try:
                response = json.loads(response)
            except:
                return {
                    "is_valid": False,
                    "reason": "응답 형식 오류",
                    "message": "죄송합니다. 응답 처리 중 오류가 발생했습니다.",
                    "response": response
                }

        return response

class InputNormalizer:
    def __init__(self, api_key: str, config_file_path: str = None):
        """

        Args:
            api_key (str): Google API 키
            config_file_path (str): 설정 JSON 파일 경로
        """
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

        # JSON 출력 파서 생성
        self.json_parser = JSONOutputParser()
        
        # 기본 설정 파일 경로 설정
        if config_file_path is None:
            config_file_path = os.path.join(os.path.dirname(__file__), "/Users/bagjimin/Desktop/project/chatbot/src/backend/src/llm/utils_json/inputNormalizer.json")

        # 설정 파일 로드
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)


        # 시스템 프롬프트 설정
        self.normalizer_config = InstructionConfig(
            instruction=config['instruction'],
            output_parser=self.json_parser,
            output_format=config['output_format'],
            examples=config['examples']
        )
        self.normalizer = ChatBot(
                    model_name="gemini-2.0-flash",
                    temperature=0.5,  # 일관된 응답을 위해 낮은 온도 설정
                    max_output_tokens=1024,
                    instruction_config=self.normalizer_config,
                    api_key=self.api_key
                )

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """
        사용자 쿼리 처리

        Args:
            user_message (str): 사용자 메시지

        Returns:
            Dict[str, Any]: 상담 응답
        """
        # 챗봇이 실행 중이 아니면 시작
        if not self.normalizer.is_running():
            self.normalizer.start_chat()

        # 사용자 메시지 처리
        response = self.normalizer.send_message(user_message)

        # 응답이 딕셔너리가 아니면 변환
        if not isinstance(response, dict):
            try:
                response = json.loads(response)
            except:
                return {
                    "is_valid": False,
                    "reason": "응답 형식 오류",
                    "message": "죄송합니다. 응답 처리 중 오류가 발생했습니다.",
                    "response": response
                }

        return response


class QueryMaker:
    def __init__(self, api_key: str, config_file_path: str = None):
        """

        Args:
            api_key (str): Google API 키
        """
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

        # JSON 출력 파서 생성
        self.json_parser = JSONOutputParser()
        
        # 기본 설정 파일 경로 설정
        if config_file_path is None:
            config_file_path = os.path.join(os.path.dirname(__file__), "/Users/bagjimin/Desktop/project/chatbot/src/backend/src/llm/utils_json/queryMaker.json")

        # 설정 파일 로드
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)


        # 쿼리 제작자
        # 쿼리 제작자
        # 쿼리 제작자
        # 시스템 프롬프트 설정
        self.query_maker_config = InstructionConfig(
            instruction=config['instruction'],
            output_parser=self.json_parser,
            output_format=config['output_format'],
            examples=config['examples']
        )

        self.query_maker = ChatBot(
                    model_name="gemini-2.0-flash",
                    temperature=0.5,  # 일관된 응답을 위해 낮은 온도 설정
                    max_output_tokens=1024,
                    instruction_config=self.query_maker_config,
                    api_key=self.api_key
                )

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """
        사용자 쿼리 처리

        Args:
            user_message (str): 사용자 메시지

        Returns:
            Dict[str, Any]: 상담 응답
        """
        # 챗봇이 실행 중이 아니면 시작
        if not self.query_maker.is_running():
            self.query_maker.start_chat()

        # 사용자 메시지 처리
        response = self.query_maker.send_message(user_message)

        # 응답이 딕셔너리가 아니면 변환
        if not isinstance(response, dict):
            try:
                response = json.loads(response)
            except:
                return {
                    "is_valid": False,
                    "reason": "응답 형식 오류",
                    "message": "죄송합니다. 응답 처리 중 오류가 발생했습니다.",
                    "response": response
                }

        return response
    
class FilterGenerator:
    def __init__(self, api_key: str, config_file_path: str = None):
        """
        필터 생성자 챗봇 초기화

        Args:
            api_key (str): Google API 키
        """
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

        # JSON 출력 파서 생성
        self.json_parser = JSONOutputParser()

        # 오늘 날짜 가져오기
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 기본 설정 파일 경로 설정
        if config_file_path is None:
            config_file_path = os.path.join(os.path.dirname(__file__), "/Users/bagjimin/Desktop/project/chatbot/src/backend/src/llm/utils_json/filterGenerator.json")

        # 설정 파일 로드
        with open(config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 필터 생성자 시스템 프롬프트 설정
        self.filter_generator_config = InstructionConfig(
            instruction=f"""오늘 날짜는 {today}입니다. 당신은 KAIST(한국과학기술원) 전산학부 챗봇 파이프라인의 일부로, 사용자의 질문을 분석하여 정보 검색을 위한 필터를 생성하는 역할을 수행합니다.

            당신의 목표는 사용자의 질문에서 검색 결과를 좁힐 수 있는 특정 기간(시작 날짜와 끝 날짜)과 최대 3개의 필터 단어를 추출하는 것입니다.

            - 기간은 'YYYY-MM-DD' 형식의 시작 날짜와 끝 날짜로 표현해야 합니다. 만약 기간이 명확히 언급되지 않았다면, 기간 필드는 None으로 처리합니다.
            - 필터 단어는 사용자의 질문에서 중요한 키워드를 기반으로 추출하며, 최대 3개까지 추출할 수 있습니다. 필터 단어가 없다면 빈 리스트로 처리합니다.

            JSON 형식으로 응답하세요.
            """,
            output_parser=self.json_parser,
            output_format=config['output_format'],
            examples=config['examples']
        )

        self.filter_generator = ChatBot(
            model_name="gemini-2.0-flash",
            temperature=0.5,  # 일관된 응답을 위해 낮은 온도 설정
            max_output_tokens=1024,
            instruction_config=self.filter_generator_config,
            api_key=self.api_key
        )

    def process_query(self, user_message: str) -> Dict[str, Optional[Any]]:
        """
        사용자 쿼리를 처리하여 필터 정보를 추출합니다.

        Args:
            user_message (str): 사용자 메시지

        Returns:
            Dict[str, Optional[Any]]: 추출된 필터 정보 (시작 날짜, 끝 날짜, 필터 단어 리스트)
        """
        # 챗봇이 실행 중이 아니면 시작
        if not self.filter_generator.is_running():
            self.filter_generator.start_chat()

        # 사용자 메시지 처리
        response = self.filter_generator.send_message(user_message)

        # 응답이 딕셔너리가 아니면 변환
        if not isinstance(response, dict):
            try:
                response = json.loads(response)
            except:
                return {
                    "start_date": None,
                    "end_date": None,
                    "filter_words":'',
                    "reason": "응답 형식 오류",
                    "message": "죄송합니다. 응답 처리 중 오류가 발생했습니다.",
                    "response": response
                }

        return response

# 라우터 함수: 입력된 질문을 분석하여 해당 도메인을 반환합니다.
def router_func(inputs):
    query = inputs.get("query", "").lower()
    if "날씨" in query:
        return "weather"
    elif "뉴스" in query:
        return "news"
    else:
        return "general"

# [날씨 체인] - 사용자가 '날씨'와 관련된 질문을 입력하면 실행됩니다.
weather_prompt = InstructionConfig(
    instruction="지역과 관련된 날씨 정보를 간결하게 제공해주세요: {query}",
    input_variables=["query"]
)
weather_chatbot = ChatBot(system_instruction="당신은 날씨 정보 전문가입니다.")
weather_chain = LLMChain(
    chatbot=weather_chatbot,
    prompt=weather_prompt,
    output_key="response"
)

# [뉴스 체인] - 사용자가 '뉴스'에 관한 질문을 입력하면 실행됩니다.
news_prompt = InstructionConfig(
    instruction="최신 뉴스를 요약하여 제공해주세요: {query}",
    input_variables=["query"]
)
news_chatbot = ChatBot(system_instruction="당신은 뉴스 전문가입니다.")
news_chain = LLMChain(
    chatbot=news_chatbot,
    prompt=news_prompt,
    output_key="response"
)

# [일반 체인] - 그 외의 질문에 대해 기본적인 답변을 제공합니다.
general_prompt = InstructionConfig(
    instruction="일반 질문에 대해 친절하고 명확하게 답변해주세요: {query}",
    input_variables=["query"]
)
general_chatbot = ChatBot(system_instruction="당신은 친절한 도우미입니다.")
general_chain = LLMChain(
    chatbot=general_chatbot,
    prompt=general_prompt,
    output_key="response"
)

# RouterChain 생성: 라우터 함수와 각 도메인별 체인을 연결합니다.
router_chain = RouterChain(
    router_func=router_func,
    destination_chains={
        "weather": weather_chain,
        "news": news_chain,
        "general": general_chain
    }
)

# 챗봇 실행 함수
def run_chatbot():
    print("다양한 정보를 제공하는 라우터 챗봇에 오신 것을 환영합니다!")
    while True:
        user_input = input("질문을 입력하세요 ('종료' 입력 시 종료): ")
        if user_input.lower() == "종료":
            break
        result = router_chain.run({"query": user_input})
        print("챗봇 답변:", result["response"])

def main():
 # 1) Google Gemini API 키 설정
    api_key = "YOUR_GOOGLE_GEMINI_API_KEY"

    # 2) 챗봇 단계별 클래스 인스턴스 생성
    checker     = InputChecker(api_key)
    normalizer  = InputNormalizer(api_key)
    querier     = QueryMaker(api_key)
    filterer    = FilterGenerator(api_key)

    print("=== 챗봇에 오신 것을 환영합니다! ===")
    print("종료하려면 '종료' 혹은 'exit'을 입력하세요.\n")

    while True:
        user_input = input("사용자: ")
        if user_input.lower() in ("종료", "exit", "quit"):
            print("챗봇을 종료합니다. 다음에 또 만나요! 👋")
            break

        # 3) input 검증
        check_result = checker.process_query(user_input)
        print("\n[입력 검증]")
        print(check_result)

        # 4) input 정규화
        norm_result = normalizer.process_query(user_input)
        print("\n[입력 정규화]")
        print(norm_result)

        # 5) 쿼리 생성
        query_result = querier.process_query(user_input)
        print("\n[쿼리 생성]")
        print(query_result)

        # 6) 필터 생성
        filter_result = filterer.process_query(user_input)
        print("\n[필터 생성]")
        print(filter_result)

        print("\n" + "="*40 + "\n")

if __name__ == "__main__":
    main()