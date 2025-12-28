"""
개선된 KAIST 전산학부 챗봇 메인 애플리케이션
Vector DB 검색과 OpenAI API를 활용한 지능형 응답 시스템 (OpenAI 전용)
"""

from src.llm import OpenAIInputChecker, OpenAIInputNormalizer, VectorSearcher, OpenAIChatBot
import json
import sys
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def main():
    """
    Vector DB 검색과 OpenAI를 활용한 챗봇 메인 함수
    """
    
    # OpenAI API 키 설정
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_api_key:
        print("❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        return

    try:
        # 구성 요소 초기화
        print("🚀 챗봇 시스템 초기화 중...")

        model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
        
        # OpenAI 기반 입력 검증 및 정규화
        checker = OpenAIInputChecker(api_key=openai_api_key)
        normalizer = OpenAIInputNormalizer(api_key=openai_api_key)
        
        # Vector DB 검색기
        vector_searcher = VectorSearcher()
        
        # OpenAI 챗봇
        openai_chatbot = OpenAIChatBot(api_key=openai_api_key)
        
        print("✅ 시스템 초기화 완료!")
        
        # 부팅 메시지로 시스템 워밍업
        print("🔄 시스템 워밍업 중...")
        boot_input = "이 메세지는 백엔드 서버 부팅 시 llm의 부팅 및 JSON 파싱을 위해 사용됩니다. 해당 메세지를 무시하세요."
        try:
            normalizer.normalize_input(boot_input)
            checker.check_input(boot_input)
            print("✅ 시스템 워밍업 완료!")
        except Exception as e:
            print(f"⚠️ 워밍업 중 경고: {e}")

        print("\\n" + "="*60)
        print("🎓 KAIST 전산학부 지능형 챗봇에 오신 것을 환영합니다!")
        print("="*60)
        print("💡 이 챗봇은 다음 기능을 제공합니다:")
        print("   • 전산학부 학사/교과 과정 정보")
        print("   • 전산학부 행사 및 프로그램 안내")
        print("   • 학생 지원 시스템 정보")
        print("   • Vector DB 기반 관련 정보 검색")
        print("   • OpenAI 기반 지능형 응답")
        print("\\n💭 질문을 입력하세요 (종료: 'exit', 도움말: 'help')")
        print("-"*60)

        while True:
            try:
                user_input = input("\\n👤 질문: ").strip()
                
                if user_input.lower() == 'exit':
                    print("\\n👋 챗봇을 종료합니다. 좋은 하루 되세요!")
                    break
                    
                if user_input.lower() == 'help':
                    show_help()
                    continue
                    
                if not user_input:
                    print("❓ 질문을 입력해주세요.")
                    continue

                print("\\n🔍 질문을 분석하고 있습니다...")
                print(f"👤 사용자 질문: {user_input}")
                
                normalized_query = user_input
                # # 1단계: 입력 정규화
                # try:
                #     normalized_query = normalizer.normalize_input(user_input)
                #     print(f"📝 정규화된 질문: {normalized_query}")
                # except Exception as e:
                #     print(f"⚠️ 입력 정규화 중 오류: {e}")
                #     normalized_query = user_input

                #2단계: 입력 유효성 검사
                try:
                    is_valid = checker.check_input(user_input)
                    
                    if not is_valid:
                        print("\\n❌ 죄송합니다. 해당 질문은 KAIST 전산학부 관련 질문이 아닌 것 같습니다.")
                        print("💡 전산학부 학사과정, 행사, 교수진, 시설 등에 대해 질문해주세요.")
                        continue
                        
                except Exception as e:
                    print(f"⚠️ 입력 검증 중 오류: {e}")
                    print("🤖 입력 검증을 건너뛰고 답변을 생성합니다.")


                # 최종단계: Vector DB 검색 및 OpenAI 응답 생성
                print("🔍 관련 정보를 검색하고 답변을 생성하는 중...")
                
                try:
                    # 응답 생성 (Vector DB 검색 포함)
                    response = openai_chatbot.generate_response(normalized_query, use_vector_search=True)
                    
                    print("\\n" + "="*60)
                    print("🤖 답변:")
                    print("-"*60)
                    print(response)
                    print("="*60)
                    
                except Exception as e:
                    print(f"\\n❌ 답변 생성 중 오류가 발생했습니다: {e}")
                    
                    # 대안: Vector DB 검색만 수행
                    try:
                        print("🔄 대안 검색을 시도합니다...")
                        search_results = vector_searcher.search_similar_documents(normalized_query, top_k=5)
                        
                        if search_results:
                            print("\\n📚 검색된 관련 정보:")
                            print("-"*40)
                            formatted_results = vector_searcher.format_search_results(search_results)
                            print(formatted_results)
                        else:
                            print("\\n❓ 관련 정보를 찾을 수 없습니다.")
                    except Exception as e2:
                        print(f"❌ 검색도 실패했습니다: {e2}")

            except KeyboardInterrupt:
                print("\\n\\n👋 챗봇을 종료합니다.")
                break
            except Exception as e:
                print(f"\\n❌ 예상치 못한 오류가 발생했습니다: {e}")
                print("🔄 다시 시도해주세요.")

    except Exception as e:
        print(f"❌ 시스템 초기화 실패: {e}")
        print("🔧 환경 설정과 API 키를 확인해주세요.")

def show_help():
    """도움말 표시"""
    print("\\n" + "="*60)
    print("📖 KAIST 전산학부 챗봇 도움말")
    print("="*60)
    print("💡 질문 예시:")
    print("   • '컴퓨터구조 수업 정보 알려줘'")
    print("   • '전산학부 교수님들 명단이 궁금해'") 
    print("   • '인공지능 관련 최신 소식 있어?'")
    print("   • '전산학부 행사 일정 알려줘'")
    print("   • '졸업 요건이 뭐야?'")
    print("\\n🔧 명령어:")
    print("   • 'help' - 이 도움말 표시")
    print("   • 'exit' - 챗봇 종료")
    print("="*60)

if __name__ == "__main__":
    main()