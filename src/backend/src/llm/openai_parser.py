"""
OpenAI 기반 입력 검증 및 정규화 모듈
"""

import openai
import json
import os
import traceback
from typing import Dict, Any

class OpenAIInputChecker:
    """OpenAI API를 사용한 입력 검증 클래스"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        OpenAI 입력 검증기 초기화
        
        Args:
            api_key (str): OpenAI API 키
            model (str): 사용할 모델
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        
        # 시스템 프롬프트 설정
        self.system_prompt = """
당신은 KAIST(한국과학기술원)의 전산학부 집행위원회에서 개발한, 학생들을 위해 정보를 제공하는 챗봇을 구성하는 파이프라인중 하나입니다.

당신의 역할은 파이프라인에서, 사용자의 입력이 전산학부 집행위원회에서 개발한 챗봇의 목적에 부합하는지를 확인하는 것입니다. 챗봇의 주요 목적은 다음과 같습니다.

• 전산학부 학사 과정 및 교과 과정 정보 제공
• 전산학부 행사 및 프로그램 안내
• 전산학부 내 학생 지원 시스템 정보 제공
• 전산학부 관련 자주 묻는 질문 답변
• 챗봇(사용자는 챗봇을 '너' 혹은 유사 단어로 지칭할 수 있음) 사용법과 관련한 질문
• 학교와 관련한 질문(학교와 관련한 질문의 경우 전산과와 상관없어도 됨)

입력이 부적절한 경우:
사용자의 입력이 챗봇의 목적과 명백히 관련이 없는 경우 (예: 개인적인 질문, 일반적인 잡담, 학부 외 다른 분야 문의 등)에는 "false"를 반환하고, 추가적인 답변이나 처리를 중단합니다.

입력 및 챗봇의 대답 수준에 부합하는 경우:
사용자의 입력이 챗봇의 목적에 부합하는 질문 또는 요청이라고 판단되는 경우에는 "true"를 반환하고, 사용자의 입력을 다음 파이프라인 단계로 전달합니다.

반드시 JSON 형식으로 응답하세요: {"is_valid": "true" 또는 "false"}
"""

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """
        사용자 쿼리의 유효성 검사
        
        Args:
            user_message (str): 사용자 메시지
            
        Returns:
            Dict[str, Any]: 검증 결과
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                result = json.loads(result_text)
                return result
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트에서 true/false 추출
                if "true" in result_text.lower():
                    return {"is_valid": "true"}
                else:
                    return {"is_valid": "false"}
                    
        except Exception as e:
            print(f"입력 검증 중 오류: {e}")
            print(f"오류 위치: {traceback.format_exc()}")
            # 기본적으로 유효한 것으로 처리
            return {"is_valid": "true"}
    
    def check_input(self, user_message: str) -> bool:
        """
        main_enhanced.py 호환성을 위한 메소드
        
        Args:
            user_message (str): 사용자 메시지
            
        Returns:
            bool: 유효성 검사 결과
        """
        result = self.process_query(user_message)
        return result.get("is_valid", "true") == "true"


class OpenAIInputNormalizer:
    """OpenAI API를 사용한 입력 정규화 클래스"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        OpenAI 입력 정규화기 초기화
        
        Args:
            api_key (str): OpenAI API 키
            model (str): 사용할 모델
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        
        # 시스템 프롬프트 설정
        self.system_prompt = """
당신은 KAIST 전산학부 챗봇의 입력 정규화 모듈입니다.

역할: 사용자의 질문을 더 명확하고 검색하기 좋은 형태로 변환합니다.

정규화 규칙:
1. 줄임말을 풀어서 쓰기 (예: "컴구"는 "컴퓨터구조"으로, "알고"는 "알고리즘"으로)
2. 문법적으로 완전한 문장으로 만들기
3. 검색 키워드를 명확하게 하기
4. 전산학부 관련 용어를 표준화하기
5. 질문의 의도를 명확하게 하기

예시:
"컴구 뭐야?"는 "컴퓨터구조 수업에 대한 정보를 알려주세요"
"교수님들 누가 있어?"는 "전산학부 교수진 명단을 알려주세요"
"AI 관련 소식 있어?"는 "인공지능 관련 최신 뉴스나 소식을 알려주세요"

반드시 JSON 형식으로 응답하세요: {"output": "정규화된 질문"}
"""

    def process_query(self, user_message: str) -> Dict[str, Any]:
        """
        사용자 쿼리 정규화
        
        Args:
            user_message (str): 사용자 메시지
            
        Returns:
            Dict[str, Any]: 정규화 결과
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=200
            )

            print(f"OpenAI 정규화 응답: {response}")  # 디버그 출력 추가
            
            result_text = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                result = json.loads(result_text)
                return result
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 원본 텍스트 반환
                return {"output": result_text}
                    
        except Exception as e:
            print(f"입력 정규화 중 오류: {e}")
            print(f"오류 위치: {traceback.format_exc()}")
            # 실패 시 원본 메시지 반환
            return {"output": user_message}
    
    def normalize_input(self, user_message: str) -> str:
        """
        main_enhanced.py 호환성을 위한 메소드
        
        Args:
            user_message (str): 사용자 메시지
            
        Returns:
            str: 정규화된 질문
        """
        result = self.process_query(user_message)
        return result.get("output", user_message)