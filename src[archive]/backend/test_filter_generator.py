import os
from .src.llm.filterGenerator import OpenAIFilterGenerator

def test_filter_generator():
    # 환경 변수에서 API 키 불러오기
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    # 필터 생성기 초기화
    generator = OpenAIFilterGenerator(api_key=api_key)

    # 테스트할 예시 문장들
    queries = [
        "현재 랩인턴 모집중인 랩 알려줘",
    ]

    # 각 문장별 결과 출력
    for q in queries:
        print(f"\n입력 문장: {q}")
        result = generator.generate_filters(q)
        print("출력 결과:", result)

if __name__ == "__main__":
    test_filter_generator()