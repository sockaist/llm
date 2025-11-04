import os
import sys
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Google Gemini API 임포트
import google.generativeai as genai

# 프롬프트 템플릿과 출력 파서 임포트
from ..utils.prompt import InstructionConfig
from ..utils.output_parsers import JSONOutputParser
from ..utils.chatbot import ChatBot

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
            config_file_path = os.path.join(os.path.dirname(__file__), "utils/inputchecker.json")

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
            config_file_path = os.path.join(os.path.dirname(__file__), "utils/inputNormalizer.json")

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
            config_file_path = os.path.join(os.path.dirname(__file__), "utils/queryMaker.json")

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
            config_file_path = os.path.join(os.path.dirname(__file__), "utils/filterGenerator.json")

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