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
from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser
from src.chatbot import ChatBot

class inputChecker:
    def __init__(self, api_key: str):
        """

        Args:
            api_key (str): Google API 키
        """
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

        # JSON 출력 파서 생성
        self.json_parser = JSONOutputParser()

        # 시스템 프롬프트 설정
        self.checker_config = InstructionConfig(
                        instruction="""당신은 KAIST(한국과학기술원)의 전산학부 집행위원회에서 개발한, 학생들을 위해 정보를 제공하는 챗봇을 구성하는 파이프라인중 하나입니다.

            당신의 역할은 파이프라인에서, 사용자의 입력이 전산학부 집행위원회에서 개발한 챗봇의 목적에 부합하는지를 확인하는 것입니다. 챗봇의 주요 목적은 다음과 같습니다.

            전산학부 학사 과정 및 교과 과정 정보 제공
            전산학부 행사 및 프로그램 안내
            전산학부 내 학생 지원 시스템 정보 제공
            전산학부 관련 자주 묻는 질문 답변
            이제 사용자의 입력을 받았습니다. 이 입력이 위에서 언급된 챗봇의 목적에 부합하는지 판단하고, 그 결과에 따라 다음과 같이 처리해야 합니다.

            입력이 부적절한 경우:

            사용자의 입력이 챗봇의 목적과 명백히 관련이 없는 경우 (예: 개인적인 질문, 일반적인 잡담, 학부 외 다른 분야 문의 등)에는 "false" 와 같은 판단 결과를 반환하고, 추가적인 답변이나 처리를 중단합니다.
            입력 및 챗봇의 대답 수준에 부합하는 경우:

            사용자의 입력이 챗봇의 목적에 부합하는 질문 또는 요청이라고 판단되는 경우 (예: "컴퓨터 구조 과목의 선수 과목은 무엇인가요?", "이번 학기 전산학부 MT 일정은 어떻게 되나요?", "전산학부 학생 상담 프로그램에 대해 알려주세요.")에는 "true" 와 같은 판단 결과를 반환하고, 사용자의 입력을 다음 파이프라인 단계로 전달합니다.

            JSON 형식으로 응답하세요.
            """,
            output_parser=self.json_parser,
            output_format={
                "is_valid": "사용자의 입력이 본 챗봇의 목절에 맞는지 여부 (true/false)",
            },
            examples=[
                {
                    "input": "컴퓨터 과학부 학부 과정에 대해 알려주세요.",
                    "output": {"is_valid": "true"}  # "output" 키 추가
                },
                {
                    "input": "오늘 날씨가 어떤가요?",
                    "output": {"is_valid": "false"} # "output" 키 추가
                },
                {
                    "input": "인공지능 과목의 졸업 요건이 무엇인가요?",
                    "output": {"is_valid": "true"}  # "output" 키 추가
                },
                {
                    "input": "어제 저녁에 먹은 닭갈비 레시피 좀 알려줄래?",
                    "output": {"is_valid": "false"} # "output" 키 추가
                },
                {
                    "input": "전산학부에서 진행하는 2025년 여름 인턴십 프로그램에 대해 알려주세요.",
                    "output": {"is_valid": "true"}  # "output" 키 추가
                },
                {
                    "input": "나는 지금 너무 힘들어.",
                    "output": {"is_valid": "false"} # "output" 키 추가
                },
                {
                    "input": "전산학부 학생들을 위한 튜터링 시스템이 있나요?",
                    "output": {"is_valid": "true"}  # "output" 키 추가
                }
                ]
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
                    "message": "죄송합니다. 응답 처리 중 오류가 발생했습니다."
                }

        return response


class queryMaker:
    def __init__(self, api_key: str):
        """

        Args:
            api_key (str): Google API 키
        """
        self.api_key = api_key
        genai.configure(api_key=self.api_key)

        # JSON 출력 파서 생성
        self.json_parser = JSONOutputParser()

        # 쿼리 제작자
        self.query_maker_config = InstructionConfig(
                        instruction="""당신은 KAIST(한국과학기술원) 전산학부 챗봇 파이프라인의 일부로, 사용자의 질문을 분석하여 정보 검색에 필요한 자연어 쿼리를 생성하는 역할을 수행합니다.
            당신의 목표는 사용자의 질문에서 핵심 키워드를 추출하고, 핵심 키워드별로 챗봇의 지식 베이스 또는 외부 검색 엔진에서 관련 정보를 효율적으로 찾을 수 있는 5개의 다양한 자연어 쿼리를 생성하는 것입니다.
            각 쿼리는 사용자의 원래 질문의 의미를 정확하게 반영하면서도, 다양한 검색 결과가 나올 수 있도록 키워드의 조합이나 표현을 약간씩 변경해야 합니다.
            JSON 형식으로 응답하세요.
                        """,
                        output_parser=self.json_parser,
                        output_format={
                            "queries":''# 타입 힌트 대신 빈 리스트 사용
                        },
                        examples=[
            {
                "input": "전산학부 학사 과정 로드맵 좀 알려줘.",
                "output": {
                "queries": [
                    "전산학부 학사 과정 로드맵",
                    "컴퓨터 과학 학부 로드맵",
                    "KAIST 전산 학사 과정 안내",
                    "전산학부 졸업 과정",
                    "컴퓨터 과학 학부 교육 과정"
                ]
                }
            },
            {
                "input": "이번 학기 인공지능 개론 수업 시간과 장소는?",
                "output": {
                "queries": [
                    "이번 학기 인공지능 개론 시간",
                    "인공지능 개론 수업 장소",
                    "2025년 1학기 인공지능 개론 강의실",
                    "이번 학기 인공지능 개론 스케줄",
                    "인공지능 개론 수업 시간표"
                ]
                }
            },
            {
                "input": "전산학부 학생 상담 프로그램 신청 방법이 궁금합니다.",
                "output": {
                "queries": [
                    "전산학부 학생 상담 신청",
                    "컴퓨터 과학부 상담 프로그램",
                    "KAIST 전산 학생 상담 방법",
                    "전산학부 상담 서비스 이용",
                    "학생 상담 프로그램 신청 절차"
                ]
                }
            },
            {
                "input": "운영체제 과목의 교수님은 누구신가요?",
                "output": {
                "queries": [
                    "운영체제 과목 교수",
                    "운영체제 담당 교수님",
                    "전산학부 운영체제 교수 정보",
                    "운영체제 강의 교수",
                    "KAIST 운영체제 교수진"
                ]
                }
            },
            {
                "input": "전산학부 MT는 언제, 어디서 하나요?",
                "output": {
                "queries": [
                    "전산학부 MT 일정",
                    "컴퓨터 과학부 MT 장소",
                    "KAIST 전산 MT 날짜",
                    "전산학부 가을 MT 계획",
                    "MT 개최 장소 및 시기"
                ]
                }
            },
            {
                "input": "학부 연구생 프로그램에 참여하고 싶은데 어떻게 해야 하나요?",
                "output": {
                "queries": [
                    "전산학부 학부 연구생 신청",
                    "컴퓨터 과학 학부 연구 프로그램",
                    "KAIST 학부 연구생 참여 방법",
                    "전산학부 연구 인턴십",
                    "학부생 연구 활동 지원"
                ]
                }
            },
            {
                "input": "데이터베이스 과목의 시험 범위가 어떻게 되나요?",
                "output": {
                "queries": [
                    "데이터베이스 시험 범위",
                    "데이터베이스 중간고사 범위",
                    "전산학부 데이터베이스 시험 내용",
                    "데이터베이스 기말고사 범위",
                    "데이터베이스 평가 범위"
                ]
                }
            }
            ]
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
                    "message": "죄송합니다. 응답 처리 중 오류가 발생했습니다."
                }

        return response
    
class FilterGenerator:
    def __init__(self, api_key: str):
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

        # 필터 생성자 시스템 프롬프트 설정
        self.filter_generator_config = InstructionConfig(
            instruction=f"""오늘 날짜는 {today}입니다. 당신은 KAIST(한국과학기술원) 전산학부 챗봇 파이프라인의 일부로, 사용자의 질문을 분석하여 정보 검색을 위한 필터를 생성하는 역할을 수행합니다.

            당신의 목표는 사용자의 질문에서 검색 결과를 좁힐 수 있는 특정 기간(시작 날짜와 끝 날짜)과 최대 3개의 필터 단어를 추출하는 것입니다.

            - 기간은 'YYYY-MM-DD' 형식의 시작 날짜와 끝 날짜로 표현해야 합니다. 만약 기간이 명확히 언급되지 않았다면, 기간 필드는 None으로 처리합니다.
            - 필터 단어는 사용자의 질문에서 중요한 키워드를 기반으로 추출하며, 최대 3개까지 추출할 수 있습니다. 필터 단어가 없다면 빈 리스트로 처리합니다.

            JSON 형식으로 응답하세요.
            """,
            output_parser=self.json_parser,
            output_format={
                "start_date": "검색 시작 날짜 (YYYY-MM-DD 형식, 없을 경우 None)",
                "end_date": "검색 끝 날짜 (YYYY-MM-DD 형식, 없을 경우 None)",
                "filter_words": ["필터 단어 1", "필터 단어 2", "필터 단어 3"]
            },
            examples=[
                {
                    "input": "2024년 전산학부 행사 알려줘.",
                    "output": {
                        "start_date": "2024-01-01",
                        "end_date": "2024-12-31",
                        "filter_words": ["행사"]
                    }
                },
                {
                    "input": "최근 3개월 동안의 전산학부 소식 궁금해.",
                    "output": {
                        "start_date": "2024-12-25",
                        "end_date": "2025-03-25",
                        "filter_words": ["소식"]
                    }
                },
                {
                    "input": "컴퓨터 구조 수업의 지난 학기 기말고사 범위 알려줘.",
                    "output": {
                        "start_date": None,
                        "end_date": None,
                        "filter_words": ["컴퓨터 구조", "기말고사", "범위"]
                    }
                },
                {
                    "input": "전산학부 MT 일정.",
                    "output": {
                        "start_date": None,
                        "end_date": None,
                        "filter_words": ["MT", "일정"]
                    }
                },
                {
                    "input": "2023년 10월 15일부터 2024년 5월 30일까지의 전산학부 세미나 정보.",
                    "output": {
                        "start_date": "2023-10-15",
                        "end_date": "2024-05-30",
                        "filter_words": ["세미나"]
                    }
                },
                {
                    "input": "오늘 이후의 전산학부 채용 공고 알려줘.",
                    "output": {
                        "start_date": "2025-03-25(today 날짜 사용)",
                        "end_date": None,
                        "filter_words": ["채용", "공고"]
                    }
                }
                ]
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
                    "message": "죄송합니다. 응답 처리 중 오류가 발생했습니다."
                }

        return response

    

def main():
    """
    inputChecker, queryMaker, FilterGenerator를 사용하는 메인 함수
    """
    api_key = "GOOGLE_API_KEY"  # 환경 변수에서 API 키 가져오기
    if not api_key:
        print("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        return

    checker = inputChecker(api_key=api_key)
    maker = queryMaker(api_key=api_key)
    filter_generator = FilterGenerator(api_key=api_key)

    while True:
        user_input = input("사용자 질문 (종료하려면 'exit' 입력): ")
        if user_input.lower() == 'exit':
            break

        # 입력 검사
        check_result = checker.process_query(user_input)
        print("\n입력 검사 결과:")
        print(json.dumps(check_result, indent=4, ensure_ascii=False))

        if check_result.get("is_valid"):
            # 쿼리 생성
            query_result = maker.process_query(user_input)
            print("\n쿼리 생성 결과:")
            print(json.dumps(query_result, indent=4, ensure_ascii=False))

            # 필터 생성
            filter_result = filter_generator.process_query(user_input)
            print("\n필터 생성 결과:")
            print(json.dumps(filter_result, indent=4, ensure_ascii=False))

        else:
            print("\n부적절한 입력으로 인해 쿼리 및 필터 생성을 중단합니다.")

if __name__ == "__main__":
    main()