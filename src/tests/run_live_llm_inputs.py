import os
import json
from llm_backend.llm.inputChecker import OpenAIInputChecker
from llm_backend.llm.inputNormalizer import OpenAIInputNormalizer
from llm_backend.llm.filterGenerator import OpenAIFilterGenerator

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        print("OPENAI_API_KEY가 설정되지 않았습니다.")
        print("예) export OPENAI_API_KEY=sk-xxxx")
        return

    print("OpenAI 연결 성공")
    print(f"모델: {model}\n")

    # 클래스 초기화
    checker = OpenAIInputChecker(api_key=api_key, model=model)
    normalizer = OpenAIInputNormalizer(api_key=api_key, model=model)
    fgen = OpenAIFilterGenerator(api_key=api_key, model=model)

    # 1. 입력 검증
    print("[1] InputChecker 결과:")
    user_inputs = ["안녕하세요", "욕설이야", "금지어 포함 문장"]
    for msg in user_inputs:
        result = checker.check_input(msg)
        print(f" - '{msg}' → is_valid = {result}")

    # 2. 입력 정규화
    print("\n[2] InputNormalizer 결과:")
    msgs = ["ㅎㅇ", "졸업요건 알려줘", "ㄱㅅ"]
    for msg in msgs:
        out = normalizer.normalize_input(msg)
        print(f" - '{msg}' → '{out}'")

    # 3. 필터 생성
    print("\n[3] FilterGenerator 결과:")
    queries = ["최근 전산학부 공지 알려줘", "10월 전산학부 뉴스 모아줘", "지난주 홍보자료"]
    for msg in queries:
        out = fgen.generate_filters(msg)
        print(f" - '{msg}' → {json.dumps(out, ensure_ascii=False)}")

    print("\n모든 테스트 완료.")

if __name__ == "__main__":
    main()