from src.llm import QueryMaker, InputChecker, FilterGenerator, InputNormalizer
import json
import sys
import os

# 프로젝트 루트 디렉토리를 파이썬 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def main():
    """
    inputChecker, queryMaker, FilterGenerator를 사용하는 메인 함수
    """
    api_key = "GOOGLE_API_KEY"  # 환경 변수에서 API 키 가져오기
    if not api_key:
        print("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        return

    checker = InputChecker(api_key=api_key)
    maker = QueryMaker(api_key=api_key)
    filter_generator = FilterGenerator(api_key=api_key)
    normalizer = InputNormalizer(api_key=api_key)

    while True:
        user_input = input("사용자 질문 (종료하려면 'exit' 입력): ")
        if user_input.lower() == 'exit':
            break

        # 입력 변형
        normalizer_result = normalizer.process_query(user_input)
        print("\n입력 변형 결과:")
        print(normalizer_result["output"])

        # 입력 검사
        check_result = checker.process_query(user_input)
        is_valid = check_result["is_valid"].lower() == "true"
        
        if(is_valid):
            # 쿼리 생성
            query_result = maker.process_query(normalizer_result)
            print("\n쿼리 생성 결과:")
            print(json.dumps(query_result, indent=4, ensure_ascii=False))

            # 필터 생성
            filter_result = filter_generator.process_query(normalizer_result)
            print("\n필터 생성 결과:")
            print(json.dumps(filter_result, indent=4, ensure_ascii=False))

        else:
            print("\n부적절한 입력으로 인해 쿼리 및 필터 생성을 중단합니다.\n다른 입력으로 다시 시도해주세요.")

if __name__ == "__main__":
    main()