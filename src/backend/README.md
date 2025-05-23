# KAIST 전산학부 챗봇 프로젝트

이 프로젝트는 KAIST 전산학부 학생들을 대상으로 최신 학사 정보(수업, 행사, 졸업 요건 등)를 제공하는 챗봇 시스템 구축을 목표로 합니다. 기존 Langchain의 기능들을 파이썬으로 커스텀 구현하여, 프롬프트 템플릿, 출력 파서, 체인 기능, 메모리 시스템 등 다양한 모듈을 활용하고 있습니다. 또한, 주기적인 크롤링과 외부 검색 API 연동(RAG 포함)을 통해 실시간 정보를 반영할 수 있도록 설계되었습니다.

## 주요 기능

- **프롬프트 템플릿 시스템**  
  - 동적 프롬프트 생성을 지원 (Simple, Jinja2 기반)
- **출력 파서**  
  - JSON, 리스트, XML, CSV 등 다양한 형식의 파싱 기능 제공
- **체인 기능**  
  - LLMChain, SequentialChain, RouterChain, TransformChain 등으로 복잡한 질의를 처리
- **메모리 시스템**  
  - ConversationBufferWindowMemory, ConversationSummaryMemory 등으로 대화 맥락 유지
- **데이터 파이프라인**  
  - **입력 검사 (inputChecker):** 입력의 유효성을 검증  
  - **쿼리 생성 (queryMaker):** 질문에서 5가지 자연어 쿼리 생성  
  - **필터 생성 (FilterGenerator):** 날짜 범위 및 키워드 필터 추출
- **외부 데이터 연동 (RAG)**  
  - 주기적 크롤링 및 KAIST 포탈 검색 연동, 구글 MCP 모듈 참고

## 시스템 아키텍처 개요

프로젝트는 크게 두 부분으로 구성됩니다:

1. **챗봇 코어**  
   커스텀 Langchain 모듈(프롬프트 템플릿, 출력 파서, 체인, 메모리 시스템 등)을 활용하여 LLM과 상호작용하는 핵심 기능을 담당합니다.

2. **데이터 파이프라인**  
   - **입력 검사:** 사용자의 입력이 챗봇의 목적(전산학부 관련 질문)에 부합하는지 확인합니다.
   - **쿼리 생성:** 입력에서 핵심 키워드를 추출하여, 다양한 검색 쿼리를 생성합니다.
   - **필터 생성:** 질문에서 날짜 범위와 필터 단어를 추출하여 검색 결과를 정제합니다.

이러한 구성은 복잡한 질의(예: 이수 학점 계산, 졸업 요건 분석, 추천 과목 선별, 학기별 시간표 생성 등)를 효과적으로 처리할 수 있게 합니다.

## 사용 예시

### 1. 기본 챗봇 사용

```python
from src.prompt import InstructionConfig
from src.chatbot import ChatBot
from src.output_parsers import JSONOutputParser

# JSON 출력 파서 생성
json_parser = JSONOutputParser()

# 프롬프트 템플릿 설정
instruction_config = InstructionConfig(
    instruction="당신은 {product}에 대한 정보를 제공하는 챗봇입니다.",
    input_variables=["product"],
    output_parser=json_parser,
    output_format={
        "product_name": "제품 이름 (문자열)",
        "description": "제품 설명 (문자열)",
        "price": "제품 가격 (숫자)"
    }
)

# ChatBot 생성
chatbot = ChatBot(instruction_config=instruction_config)

# 메시지 전송
response = chatbot.send_message("최신 스마트폰 정보 알려줘", product="스마트폰")
print(response)
```





# Langchain 커스텀 구현 라이브러리 - README

이 라이브러리는 Langchain의 주요 기능들을 파이썬으로 직접 구현한 것입니다. Langchain의 의존성 및 유지보수 문제를 해결하고, 더 사용자 친화적이며 객체 지향적인 코드를 제공합니다.

## 주요 기능

- **프롬프트 템플릿**: 동적인 프롬프트 생성을 지원하고 재사용성을 높이는 기능
- **다양한 출력 파서**: LLM의 답변을 다양한 형식으로 파싱하는 기능
- **체인 기능**: 여러 개의 LLM 호출, 프롬프트, 파서 등을 순차적으로 연결하는 기능
- **메모리 기능**: 챗봇과의 이전 대화 내용을 기억하고 활용하는 기능
- **ChatBot 클래스**: LLM 모델과의 상호작용을 관리하는 기능

## 설치 방법

```bash
# 저장소 클론
git clone https://github.com/yourusername/langchain_custom.git
cd langchain_custom

# 설치
pip install -e .

# 개발 의존성 포함 설치
pip install -e ".[dev]"
```

## 간단한 사용 예시

```python
from langchain_custom import InstructionConfig, ChatBot, JSONOutputParser

# JSON 출력 파서 생성
json_parser = JSONOutputParser()

# 프롬프트 템플릿 생성
instruction_config = InstructionConfig(
    instruction="당신은 {product}에 대한 정보를 제공하는 챗봇입니다.",
    input_variables=["product"],
    output_parser=json_parser,
    output_format={
        "product_name": "제품 이름 (문자열)",
        "description": "제품 설명 (문자열)",
        "price": "제품 가격 (숫자)"
    }
)

# ChatBot 생성
chatbot = ChatBot(instruction_config=instruction_config)

# 채팅 시작
chatbot.start_chat()

# 메시지 전송
response = chatbot.send_message("최신 스마트폰 정보 알려줘", product="스마트폰")
print(response)
```

## 자세한 사용법

자세한 사용법은 `documentation.md` 파일을 참조하세요.

## 테스트 실행

```bash
# 모든 테스트 실행
python -m unittest discover tests

# 특정 테스트 실행
python -m unittest tests/test_prompt_templates.py
```

## 라이선스

MIT License
