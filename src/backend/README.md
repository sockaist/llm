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
