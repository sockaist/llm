"""
ChatBot 서비스 클래스
main.py의 기능을 atomic하게 분리하여 FastAPI에서 사용 가능하도록 구성
"""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from ..llm import OpenAIInputChecker, OpenAIInputNormalizer, VectorSearcher, OpenAIChatBot


class ChatBotService:
    """
    ChatBot 서비스 클래스
    서버 시작시 한 번만 초기화되고, 이후 요청에 대해 빠르게 응답
    """
    
    def __init__(self):
        """ChatBot 서비스 초기화"""
        self.is_initialized = False
        self.checker = None
        self.normalizer = None
        self.vector_searcher = None
        self.openai_chatbot = None
        self._initialize()
    
    def _initialize(self):
        """
        ChatBot 컴포넌트들 초기화
        서버 시작시 한 번만 실행됨
        """
        try:
            # 환경 변수 로드
            load_dotenv()
            
            # OpenAI API 키 확인
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
            
            print("🚀 ChatBot 서비스 초기화 중...")
            
            # 컴포넌트 초기화
            self.checker = OpenAIInputChecker(api_key=openai_api_key)
            self.normalizer = OpenAIInputNormalizer(api_key=openai_api_key)
            self.vector_searcher = VectorSearcher()
            self.openai_chatbot = OpenAIChatBot(api_key=openai_api_key)
            
            # 시스템 워밍업
            print("🔄 시스템 워밍업 중...")
            boot_input = "이 메세지는 백엔드 서버 부팅 시 llm의 부팅 및 JSON 파싱을 위해 사용됩니다. 해당 메세지를 무시하세요."
            
            try:
                self.normalizer.normalize_input(boot_input)
                self.checker.check_input(boot_input)
                print("✅ 시스템 워밍업 완료!")
            except Exception as e:
                print(f"⚠️ 워밍업 중 경고: {e}")
            
            self.is_initialized = True
            print("✅ ChatBot 서비스 초기화 완료!")
            
        except Exception as e:
            print(f"❌ ChatBot 서비스 초기화 실패: {e}")
            raise e
    
    def get_health_status(self) -> Dict[str, str]:
        """
        서비스 상태 확인
        
        Returns:
            Dict[str, str]: 각 컴포넌트의 상태
        """
        components = {
            "chatbot_service": "healthy" if self.is_initialized else "unhealthy",
            "input_checker": "healthy" if self.checker is not None else "unhealthy",
            "input_normalizer": "healthy" if self.normalizer is not None else "unhealthy",
            "vector_searcher": "healthy" if self.vector_searcher is not None else "unhealthy",
            "openai_chatbot": "healthy" if self.openai_chatbot is not None else "unhealthy"
        }
        return components
    
    def process_message(self, user_input: str, use_vector_search: bool = True) -> Dict[str, Any]:
        """
        사용자 메시지 처리
        
        Args:
            user_input (str): 사용자 입력
            use_vector_search (bool): Vector DB 검색 사용 여부
            
        Returns:
            Dict[str, Any]: 처리 결과
        """
        if not self.is_initialized:
            return {
                "success": False,
                "response": "서비스가 초기화되지 않았습니다.",
                "error": "Service not initialized"
            }
        
        try:
            print(f"📝 사용자 질문 처리 중: {user_input}")
            
            # 1단계: 입력 정규화
            try:
                normalized_query = self.normalizer.normalize_input(user_input)
                print(f"📝 정규화된 질문: {normalized_query}")
            except Exception as e:
                print(f"⚠️ 입력 정규화 중 오류: {e}")
                normalized_query = user_input
            
            # 2단계: 입력 유효성 검사 (주석 처리됨 - 필요시 활성화)
            # try:
            #     is_valid = self.checker.check_input(user_input)
            #     if not is_valid:
            #         return {
            #             "success": False,
            #             "response": "죄송합니다. 해당 질문은 KAIST 전산학부 관련 질문이 아닌 것 같습니다. 전산학부 학사과정, 행사, 교수진, 시설 등에 대해 질문해주세요.",
            #             "error": "Invalid input"
            #         }
            # except Exception as e:
            #     print(f"⚠️ 입력 검증 중 오류: {e}")
            
            # 3단계: 응답 생성
            print("🔍 관련 정보를 검색하고 답변을 생성하는 중...")
            
            try:
                response = self.openai_chatbot.generate_response(
                    normalized_query, 
                    use_vector_search=use_vector_search
                )
                
                return {
                    "success": True,
                    "response": response,
                    "message": "답변 생성 완료"
                }
                
            except Exception as e:
                print(f"❌ 답변 생성 중 오류: {e}")
                
                # 대안: Vector DB 검색만 수행
                try:
                    print("🔄 대안 검색을 시도합니다...")
                    search_results = self.vector_searcher.search_similar_documents(
                        normalized_query, top_k=5
                    )
                    
                    if search_results:
                        formatted_results = self.vector_searcher.format_search_results(search_results)
                        return {
                            "success": True,
                            "response": f"검색된 관련 정보:\n\n{formatted_results}",
                            "message": "Vector DB 검색 결과 제공"
                        }
                    else:
                        return {
                            "success": False,
                            "response": "관련 정보를 찾을 수 없습니다.",
                            "error": "No search results found"
                        }
                        
                except Exception as e2:
                    return {
                        "success": False,
                        "response": f"답변 생성 및 검색에 실패했습니다: {str(e2)}",
                        "error": str(e2)
                    }
                    
        except Exception as e:
            print(f"❌ 메시지 처리 중 예상치 못한 오류: {e}")
            return {
                "success": False,
                "response": f"메시지 처리 중 오류가 발생했습니다: {str(e)}",
                "error": str(e)
            }


# 전역 서비스 인스턴스 (서버 시작시 한 번만 생성)
chatbot_service = None


def get_chatbot_service() -> ChatBotService:
    """
    ChatBot 서비스 인스턴스 반환
    FastAPI dependency injection에서 사용
    """
    global chatbot_service
    if chatbot_service is None:
        chatbot_service = ChatBotService()
    return chatbot_service