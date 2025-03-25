"""
심리 상담사 챗봇 구현 - ChatBot 클래스를 활용한 간소화 버전
"""
import os
import sys
import json
from typing import Dict, Any, List

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Google Gemini API 임포트
import google.generativeai as genai

# 프롬프트 템플릿과 출력 파서 임포트
from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser
from src.chatbot import ChatBot

class SimplePsychologicalCounselor:
    """
    ChatBot 클래스를 활용한 간소화된 심리 상담사 챗봇
    """
    def __init__(self, api_key: str):
        """
        심리 상담사 챗봇 초기화
        
        Args:
            api_key (str): Google API 키
        """
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        
        # JSON 출력 파서 생성
        self.json_parser = JSONOutputParser()
        
        # 심리 상담사 시스템 프롬프트 설정
        self.counselor_config = InstructionConfig(
            instruction="""
당신은 공감적이고 전문적인 심리 상담사입니다. 사용자의 메시지를 분석하고 적절한 상담과 지원을 제공해야 합니다.

작업 순서:
1. 사용자의 입력이 심리 상담 목적에 맞는지 검증하세요.
   - 심리적 문제, 감정, 정신 건강 관련 질문인지
   - 상담이나 조언을 구하는 내용인지
   - 자해, 자살 등 위험한 내용이 있는지 (있다면 긴급하게 표시)

2. 사용자의 메시지가 심리 상담 목적에 맞지 않으면, 이유를 설명하고 적절한 안내를 제공하세요.

3. 사용자의 메시지가 심리 상담 목적에 맞으면, 다음을 포함한 상담을 제공하세요:
   - 공감적이고 지지적인 응답
   - 사용자의 우울증 척도 평가 (0-100)
   - 평가 근거
   - 추천 조치

4. 응답의 품질을 자체 검증하세요:
   - 상담 응답이 사용자의 질문/상황에 적절한지
   - 우울증 척도 평가가 근거에 기반하여 합리적인지
   - 평가 근거가 충분하고 명확한지
   - 추천 조치가 적절하고 도움이 되는지

5. 검증 결과 문제가 있으면 응답을 개선하세요.

우울증 척도 기준:
- 0-20: 우울감이 거의 없음
- 21-40: 경미한 우울감
- 41-60: 중등도 우울감
- 61-80: 심각한 우울감
- 81-100: 매우 심각한 우울감

JSON 형식으로 응답하세요.
""",
            output_parser=self.json_parser,
            output_format={
                "is_valid": "심리 상담 목적에 맞는지 여부 (true/false)",
                "reason": "유효하지 않은 경우 이유 설명",
                "counseling_response": "사용자에게 전달할 상담 메시지 (유효한 경우)",
                "depression_score": "우울증 척도 (0-100) (유효한 경우)",
                "assessment_basis": "평가 근거 (유효한 경우)",
                "recommended_actions": "추천 조치 (유효한 경우)"
            }
        )
        
        # 심리 상담사 챗봇 생성
        self.counselor = ChatBot(
            model_name="gemini-2.0-flash",
            temperature=0.2,  # 일관된 응답을 위해 낮은 온도 설정
            max_output_tokens=1024,
            instruction_config=self.counselor_config,
            api_key=self.api_key
        )
        
        # API 연결 확인
        self._verify_api_connection()
    
    def _verify_api_connection(self):
        """
        API 연결 확인
        """
        print("\n===== API 연결 확인 중 =====")
        try:
            self.counselor.start_chat()
            response = self.counselor.send_message("Hello")
            print(f"API 연결 성공! 응답: {response[:50]}..." if len(str(response)) > 50 else response)
            return True
        except Exception as e:
            print(f"API 연결 실패: {e}")
            return False
    
    def process_query(self, user_message: str) -> Dict[str, Any]:
        """
        사용자 쿼리 처리
        
        Args:
            user_message (str): 사용자 메시지
            
        Returns:
            Dict[str, Any]: 상담 응답
        """
        # 챗봇이 실행 중이 아니면 시작
        if not self.counselor.is_running():
            self.counselor.start_chat()
        
        # 사용자 메시지 처리
        response = self.counselor.send_message(user_message)
        
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

def main():
    """
    메인 함수
    """
    print("\n===== 심리 상담사 챗봇 =====")
    
    # API 키 설정
    api_key = input("Google API 키를 입력하세요: ")
    
    try:
        # 심리 상담사 챗봇 초기화
        print("\n챗봇 시스템을 초기화하는 중입니다. 잠시만 기다려주세요...")
        counselor = SimplePsychologicalCounselor(api_key=api_key)
        
        print("\n===== 심리 상담사 챗봇 =====")
        print("종료하려면 'exit' 또는 '종료'를 입력하세요.\n")
        
        while True:
            # 사용자 입력 받기
            user_message = input("\n사용자: ")
            
            # 종료 조건
            if user_message.lower() in ["exit", "종료"]:
                print("상담을 종료합니다.")
                break
            
            # 쿼리 처리
            try:
                result = counselor.process_query(user_message)
                
                # 유효하지 않은 쿼리인 경우
                if not result.get("is_valid", False):
                    print(f"\n상담사: 죄송합니다. 이 질문은 심리 상담 목적에 맞지 않습니다.")
                    print(f"이유: {result.get('reason', '알 수 없는 이유')}")
                    continue
                
                # 상담 응답 출력
                print(f"\n상담사: {result.get('counseling_response', '')}")
                print(f"\n[분석 정보]")
                print(f"우울증 척도: {result.get('depression_score', 0)}/100")
                print(f"평가 근거: {result.get('assessment_basis', '')}")
                print(f"추천 조치: {result.get('recommended_actions', '')}")
                
            except Exception as e:
                print(f"오류 발생: {e}")
    
    except Exception as e:
        print(f"\n시스템 초기화 중 오류 발생: {e}")
        print("프로그램을 종료합니다.")

if __name__ == "__main__":
    main()
