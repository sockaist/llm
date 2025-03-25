# KAIST 전산학부 챗봇 파이프라인

이 문서는 KAIST 전산학부 챗봇 파이프라인의 구성 요소와 각 단계에 대해 설명합니다. 파이프라인은 사용자의 입력을 처리하여 유효성을 검사하고, 적절한 검색 쿼리를 생성하며, 필터를 추출하는 과정으로 나뉩니다.

## 파이프라인 구성 요소

이 파이프라인은 다음 세 가지 주요 모듈로 구성됩니다:
0. 입력 변환
- 사용자의 입력을 LLM이 알아먹을 수 있도록 변환(은어, 줄임말 등)


1. **입력 검사 (inputChecker)**  
   - **목적**: 사용자의 입력이 챗봇의 목적에 부합하는지를 검사합니다.
   - **주요 작업**:
     - 사용자의 입력이 전산학부 챗봇의 목적에 맞는지 확인합니다.
     - 입력이 부적절한 경우에는 `false`를 반환하고, 적절한 경우에는 `true`를 반환합니다.
   - **사용 예시**:
     - `true`: "전산학부 MT 일정은 언제인가요?"
     - `false`: "오늘 날씨가 어떤가요?" -> false인 경우 대화를 종료 및 반환(
  
2. **쿼리 생성 (queryMaker)**  
   - **목적**: 사용자의 질문에서 핵심 키워드를 추출하여, 해당 정보를 검색할 수 있는 5개의 다양한 자연어 쿼리를 생성합니다.
   - **주요 작업**:
     - 사용자의 질문을 분석하여, 해당 질문을 기반으로 검색 가능한 쿼리들을 생성합니다.
     - 쿼리는 검색 엔진 또는 챗봇의 지식베이스에서 효율적으로 검색될 수 있도록 다양한 표현을 사용합니다.
   - **사용 예시**:
     - 사용자 질문: "전산학부 학사 과정 로드맵 알려줘."
     - 생성된 쿼리: 
       ```json
       [
         "전산학부 학사 과정 로드맵",
         "컴퓨터 과학 학부 로드맵",
         "KAIST 전산 학사 과정 안내",
         "전산학부 졸업 과정",
         "컴퓨터 과학 학부 교육 과정"
       ]
       ```

3. **필터 생성 (FilterGenerator)**  
   - **목적**: 사용자의 질문을 기반으로 검색 결과를 좁힐 수 있는 필터를 생성합니다. 주로 특정 날짜 범위와 필터 단어를 추출합니다.
   - **주요 작업**:
     - 사용자의 질문에서 날짜 범위와 중요한 키워드를 추출하여, 검색 결과를 보다 구체적으로 필터링합니다.
     - 날짜 범위는 'YYYY-MM-DD' 형식으로 처리하며, 필터 단어는 최대 3개까지 추출할 수 있습니다.
   - **사용 예시**:
     - 사용자 질문: "2024년 전산학부 행사 알려줘."
     - 생성된 필터: 
       ```json
       {
         "start_date": "2024-01-01",
         "end_date": "2024-12-31",
         "filter_words": ["행사"]
       }
       ```

## 파이프라인 흐름

### 1. 사용자 입력 처리
사용자가 챗봇에 입력한 메시지는 첫 번째 단계인 **입력 검사 (inputChecker)**로 전달됩니다.

### 2. 입력 검사
`inputChecker`는 사용자의 입력이 챗봇의 목적에 부합하는지를 검사합니다.
- **유효한 입력**: 예를 들어, "전산학부 학사 과정에 대해 알려주세요."와 같은 질문은 `true`를 반환합니다.
- **유효하지 않은 입력**: 예를 들어, "오늘 날씨는 어떤가요?"와 같은 질문은 `false`를 반환합니다.

### 3. 쿼리 생성 (조건이 유효한 경우)
입력 검사가 `true`를 반환하면, 그 다음 단계는 **쿼리 생성 (queryMaker)**입니다.
- `queryMaker`는 사용자의 질문을 분석하여 검색을 위한 5개의 다양한 자연어 쿼리를 생성합니다.
- 예를 들어, 사용자가 "전산학부 학사 과정 로드맵"을 요청하면, `queryMaker`는 다양한 형태의 쿼리를 생성하여 검색을 가능하게 합니다.

### 4. 필터 생성 (조건이 유효한 경우)
쿼리 생성이 완료되면, **필터 생성 (FilterGenerator)** 단계로 넘어갑니다.
- 이 단계에서는 사용자의 질문에서 날짜 범위와 필터 단어를 추출하여 검색 결과를 좁힙니다.
- 예를 들어, "2024년 전산학부 행사 알려줘."라는 질문은 "2024-01-01"부터 "2024-12-31"까지의 날짜 범위와 "행사"라는 필터 단어를 생성합니다.

### 5. 최종 결과
필터와 쿼리가 생성되면, 사용자는 이를 기반으로 정보를 검색하고, 적절한 답변을 제공받을 수 있습니다.

## 코드 흐름 예시

```python
def main():
    api_key = "YOUR_GOOGLE_API_KEY"
    
    if not api_key:
        print("GOOGLE_API_KEY 환경 변수가 설정되지 않았습니다.")
        return
    
    # 각 모듈 초기화
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