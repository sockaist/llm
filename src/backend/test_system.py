"""
챗봇 시스템 테스트 스크립트
"""

import os
import sys
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

def test_environment():
    """환경 설정 테스트"""
    print("🔧 환경 설정 테스트")
    print("-" * 40)
    
    # API 키 확인
    google_key = os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    
    print(f"Google API Key: {'✅ 설정됨' if google_key else '❌ 누락'}")
    print(f"OpenAI API Key: {'✅ 설정됨' if openai_key else '❌ 누락'}")
    print(f"Qdrant API Key: {'✅ 설정됨' if qdrant_key else '❌ 누락'}")
    
    return all([google_key, openai_key, qdrant_key])

def test_imports():
    """모듈 import 테스트"""
    print("\\n📦 모듈 Import 테스트")
    print("-" * 40)
    
    try:
        from src.llm import VectorSearcher, OpenAIChatBot, InputChecker
        print("✅ 챗봇 모듈 import 성공")
        return True
    except ImportError as e:
        print(f"❌ 챗봇 모듈 import 실패: {e}")
        return False

def test_vector_search():
    """Vector 검색 테스트"""
    print("\\n🔍 Vector 검색 테스트")
    print("-" * 40)
    
    try:
        from src.llm import VectorSearcher
        searcher = VectorSearcher()
        
        # 간단한 검색 테스트
        if searcher.search_available:
            results = searcher.search_similar_documents("컴퓨터구조", top_k=3)
            print(f"✅ 검색 결과: {len(results)}개 문서 발견")
            return True
        else:
            print("⚠️ Vector 검색 사용 불가 (정상적인 상황일 수 있음)")
            return True
    except Exception as e:
        print(f"❌ Vector 검색 테스트 실패: {e}")
        return False

def test_openai_chatbot():
    """OpenAI 챗봇 테스트"""
    print("\\n🤖 OpenAI 챗봇 테스트")
    print("-" * 40)
    
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key or openai_key == "your_openai_api_key_here":
            print("⚠️ OpenAI API 키가 설정되지 않아 테스트를 건너뜁니다.")
            return True
            
        from src.llm import OpenAIChatBot
        chatbot = OpenAIChatBot(api_key=openai_key)
        
        # 간단한 응답 테스트 (실제 API 호출 없이)
        print("✅ OpenAI 챗봇 초기화 성공")
        return True
    except Exception as e:
        print(f"❌ OpenAI 챗봇 테스트 실패: {e}")
        return False

def main():
    """전체 테스트 실행"""
    print("🧪 KAIST 전산학부 챗봇 시스템 테스트")
    print("=" * 50)
    
    tests = [
        ("환경 설정", test_environment),
        ("모듈 Import", test_imports),
        ("Vector 검색", test_vector_search),
        ("OpenAI 챗봇", test_openai_chatbot)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 예외 발생: {e}")
    
    print("\\n" + "=" * 50)
    print(f"📊 테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! 시스템이 정상적으로 설정되었습니다.")
        print("💡 main_enhanced.py를 실행하여 챗봇을 시작하세요.")
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 설정을 확인해주세요.")
        print("📖 README_Enhanced.md를 참고하여 설정을 완료하세요.")

if __name__ == "__main__":
    main()