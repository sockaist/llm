# Langchain 커스텀 구현 라이브러리 사용 설명서

이 문서는 Langchain의 주요 기능들을 파이썬으로 직접 구현한 라이브러리의 사용법을 설명합니다. 이 라이브러리는 Langchain의 의존성 및 유지보수 문제를 해결하고, 더 사용자 친화적이며 객체 지향적인 코드를 제공합니다.

## 목차

1. [설치 및 시작하기](#설치-및-시작하기)
2. [프롬프트 템플릿 시스템](#프롬프트-템플릿-시스템)
3. [출력 파서](#출력-파서)
4. [ChatBot 클래스](#chatbot-클래스)
5. [체인 기능](#체인-기능)
6. [메모리 시스템](#메모리-시스템)
7. [통합 사용 예제](#통합-사용-예제)
8. [테스트 및 디버깅](#테스트-및-디버깅)

## 설치 및 시작하기

### 요구 사항

- Python 3.8 이상
- (선택) Jinja2: 고급 템플릿 기능 사용 시 필요
- (선택) Pydantic: PydanticOutputParser 사용 시 필요
- (선택) PyYAML: YAMLOutputParser 사용 시 필요

### 설치 방법

이 라이브러리는 압축 파일로 제공됩니다. 압축을 풀고 프로젝트에 포함시켜 사용하세요.

```python
# 기본 사용 예시
from src.prompt import InstructionConfig
from src.chatbot import ChatBot
from src.output_parsers import JSONOutputParser

# 프롬프트 설정
instruction_config = InstructionConfig(
    instruction="당신은 {product}에 대한 정보를 제공하는 챗봇입니다.",
    input_variables=["product"]
)

# ChatBot 생성
chatbot = ChatBot(instruction_config=instruction_config)

# 메시지 전송
response = chatbot.send_message("안녕하세요!", product="스마트폰")
print(response)
```

## 프롬프트 템플릿 시스템

프롬프트 템플릿 시스템은 동적인 프롬프트 생성을 지원하고 재사용성을 높이는 기능을 제공합니다.

### 주요 클래스

#### BasePromptTemplate

모든 프롬프트 템플릿의 기본 추상 클래스입니다.

```python
from src.prompt import BasePromptTemplate

# 이 클래스는 직접 인스턴스화하지 않고 상속하여 사용합니다.
```

#### StringPromptTemplate

문자열 기반 프롬프트 템플릿의 기본 클래스입니다.

```python
from src.prompt import StringPromptTemplate

# 이 클래스는 직접 인스턴스화하지 않고 상속하여 사용합니다.
```

#### SimplePromptTemplate

Python의 format 메서드를 사용하는 간단한 프롬프트 템플릿입니다.

```python
from src.prompt import SimplePromptTemplate

template = SimplePromptTemplate(
    template="안녕하세요, {name}님! 오늘 {weather} 날씨에 어떻게 지내세요?",
    input_variables=["name", "weather"]
)

result = template.format(name="홍길동", weather="맑은")
print(result)  # 출력: 안녕하세요, 홍길동님! 오늘 맑은 날씨에 어떻게 지내세요?
```

#### Jinja2PromptTemplate

Jinja2 템플릿 엔진을 사용하는 고급 프롬프트 템플릿입니다.

```python
from src.prompt import Jinja2PromptTemplate

template = Jinja2PromptTemplate(
    template="안녕하세요, {{ name }}님! {% if weather %}오늘 {{ weather }} 날씨에 {% endif %}어떻게 지내세요?",
    input_variables=["name", "weather"]
)

# 모든 변수 값 채우기
result = template.format(name="홍길동", weather="맑은")
print(result)  # 출력: 안녕하세요, 홍길동님! 오늘 맑은 날씨에 어떻게 지내세요?

# 선택적 변수 생략
result = template.format(name="홍길동", weather=None)
print(result)  # 출력: 안녕하세요, 홍길동님! 어떻게 지내세요?
```

#### InstructionConfig

프롬프트 템플릿, 출력 형식, 예시 등을 포함하는 통합 설정 클래스입니다.

```python
from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser

# 기본 InstructionConfig 생성
instruction_config = InstructionConfig(
    instruction="당신은 {product}에 대한 정보를 제공하는 챗봇입니다.",
    input_variables=["product"],
    output_format={
        "product_name": "제품 이름 (문자열)",
        "description": "제품 설명 (문자열)",
        "price": "제품 가격 (숫자)"
    },
    examples=[
        {"input": "최신 스마트폰 정보 알려줘", "output": '{"product_name": "갤럭시 S24", "description": "삼성의 최신 플래그십 스마트폰입니다.", "price": 1200000}'},
    ],
    output_parser=JSONOutputParser()
)

# 변수 값 채우기
formatted_instruction = instruction_config.format_instruction(product="스마트폰")
print(formatted_instruction)

# 예시 포맷
examples = instruction_config.format_examples()
print(examples)

# 완전한 프롬프트 생성
complete_prompt = instruction_config.format_complete_prompt(product="스마트폰")
print(complete_prompt)
```

## 출력 파서

출력 파서는 LLM의 답변을 다양한 형식으로 파싱할 수 있도록 지원합니다.

### 주요 클래스

#### BaseOutputParser

모든 출력 파서의 기본 추상 클래스입니다.

```python
from src.output_parsers import BaseOutputParser

# 이 클래스는 직접 인스턴스화하지 않고 상속하여 사용합니다.
```

#### JSONOutputParser

JSON 형식의 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import JSONOutputParser

parser = JSONOutputParser()

# 정상적인 JSON 파싱
json_text = '{"name": "홍길동", "age": 30, "city": "서울"}'
result = parser.parse(json_text)
print(result)  # 출력: {'name': '홍길동', 'age': 30, 'city': '서울'}

# 코드 블록 내 JSON 파싱
json_with_codeblock = '```json\n{"name": "홍길동", "age": 30, "city": "서울"}\n```'
result = parser.parse(json_with_codeblock)
print(result)  # 출력: {'name': '홍길동', 'age': 30, 'city': '서울'}

# 형식 지침 출력
print(parser.get_format_instructions())
```

#### ListOutputParser

리스트 형식의 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import ListOutputParser

parser = ListOutputParser()

# 개행으로 구분된 리스트 파싱
list_text = "항목1\n항목2\n항목3"
result = parser.parse(list_text)
print(result)  # 출력: ['항목1', '항목2', '항목3']

# 사용자 정의 구분자 사용
custom_parser = ListOutputParser(separator="|")
list_text = "항목1|항목2|항목3"
result = custom_parser.parse(list_text)
print(result)  # 출력: ['항목1', '항목2', '항목3']
```

#### CommaSeparatedListOutputParser

쉼표로 구분된 리스트 형식의 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import CommaSeparatedListOutputParser

parser = CommaSeparatedListOutputParser()

# 쉼표로 구분된 리스트 파싱
list_text = "항목1, 항목2, 항목3"
result = parser.parse(list_text)
print(result)  # 출력: ['항목1', '항목2', '항목3']
```

#### StructuredOutputParser

구조화된 출력 형식의 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import StructuredOutputParser

schema = {
    "name": "이름",
    "age": "나이",
    "city": "도시"
}
parser = StructuredOutputParser(schema=schema)

# JSON 형식 파싱
json_text = '{"name": "홍길동", "age": 30, "city": "서울"}'
result = parser.parse(json_text)
print(result)  # 출력: {'name': '홍길동', 'age': 30, 'city': '서울'}

# 키-값 형식 파싱
key_value_text = "name: 홍길동\nage: 30\ncity: 서울"
result = parser.parse(key_value_text)
print(result)  # 출력: {'name': '홍길동', 'age': '30', 'city': '서울'}
```

#### XMLOutputParser

XML 형식의 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import XMLOutputParser

parser = XMLOutputParser(root_tag="person", tags=["name", "age", "city"])

# XML 파싱
xml_text = "<person><name>홍길동</name><age>30</age><city>서울</city></person>"
result = parser.parse(xml_text)
print(result)  # 출력: {'name': '홍길동', 'age': '30', 'city': '서울'}

# 태그 지정 없이 모든 태그 파싱
general_parser = XMLOutputParser()
xml_text = "<data><item>항목1</item><item>항목2</item><info>추가 정보</info></data>"
result = general_parser.parse(xml_text)
print(result)  # 출력: {'item': ['항목1', '항목2'], 'info': '추가 정보'}
```

#### RegexParser

정규 표현식을 사용하여 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import RegexParser

# 이메일과 전화번호 추출 정규식
parser = RegexParser(
    regex_pattern=r"이메일: ([\w.%+-]+@[\w.-]+\.[a-zA-Z]{2,}), 전화번호: (\d{2,3}-\d{3,4}-\d{4})",
    output_keys=["email", "phone"]
)

# 정규식 패턴 매칭
text = "사용자 정보 - 이메일: user@example.com, 전화번호: 010-1234-5678"
result = parser.parse(text)
print(result)  # 출력: {'email': 'user@example.com', 'phone': '010-1234-5678'}
```

#### MarkdownOutputParser

마크다운 형식의 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import MarkdownOutputParser

parser = MarkdownOutputParser(headers_to_include=["소개", "특징", "결론"])

# 마크다운 파싱
markdown_text = """
# 소개
이것은 소개 섹션입니다.

# 특징
- 특징 1
- 특징 2

# 사용법
사용법에 대한 설명입니다.

# 결론
결론 내용입니다.
"""
result = parser.parse(markdown_text)
print(result)  # 출력: 소개와 특징, 결론 섹션만 포함된 마크다운
```

#### CSVOutputParser

CSV 형식의 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import CSVOutputParser

parser = CSVOutputParser(column_names=["이름", "나이", "도시"])

# CSV 파싱
csv_text = """
이름,나이,도시
홍길동,30,서울
김철수,25,부산
이영희,35,대전
"""
result = parser.parse(csv_text)
print(result)  # 출력: [{'이름': '홍길동', '나이': '30', '도시': '서울'}, ...]
```

#### DatetimeOutputParser

날짜 및 시간 정보를 파싱하는 파서입니다.

```python
from src.output_parsers import DatetimeOutputParser

parser = DatetimeOutputParser()

# 날짜 및 시간 파싱
text = "회의는 2023-05-15 14:30에 시작합니다."
result = parser.parse(text)
print(result)  # 출력: {'date': '2023-05-15', 'time': '14:30:00'}
```

#### CustomFunctionOutputParser

사용자 정의 함수를 사용하여 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import CustomFunctionOutputParser

# 사용자 정의 파싱 함수
def parse_product_info(text):
    lines = text.strip().split('\n')
    result = {}
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip()
    return result

parser = CustomFunctionOutputParser(
    parse_func=parse_product_info,
    format_instructions="제품 정보를 '키: 값' 형식으로 작성해주세요."
)

# 사용자 정의 함수로 파싱
text = """
제품명: 스마트폰
가격: 1,000,000원
제조사: 삼성전자
"""
result = parser.parse(text)
print(result)  # 출력: {'제품명': '스마트폰', '가격': '1,000,000원', '제조사': '삼성전자'}
```

#### CombiningOutputParser

여러 파서를 조합하여 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import CombiningOutputParser, JSONOutputParser, ListOutputParser

# 여러 파서 조합
parsers = {
    "json": JSONOutputParser(),
    "list": ListOutputParser()
}
parser = CombiningOutputParser(parsers=parsers)

# 여러 형식이 포함된 텍스트 파싱
text = """
여기 JSON 데이터가 있습니다:
{"name": "홍길동", "age": 30}

그리고 여기 리스트가 있습니다:
항목1
항목2
항목3
"""
result = parser.parse(text)
print(result)  # 출력: {'json': {'name': '홍길동', 'age': 30}, 'list': ['항목1', '항목2', '항목3']}
```

#### AutoFixOutputParser

파싱 실패 시 자동으로 수정을 시도하는 파서입니다.

```python
from src.output_parsers import AutoFixOutputParser, JSONOutputParser

# JSON 파서를 자동 수정 기능으로 감싸기
base_parser = JSONOutputParser()
parser = AutoFixOutputParser(parser=base_parser)

# 오류가 있는 JSON 파싱 시도
invalid_json = '{"name": "홍길동", "age": 30, "city": "서울",}'  # 후행 쉼표 오류
try:
    result = parser.parse(invalid_json)
    print(result)  # 출력: {'name': '홍길동', 'age': 30, 'city': '서울'}
except ValueError as e:
    print(f"자동 수정 실패: {e}")
```

#### PydanticOutputParser

Pydantic 모델을 사용하여 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# Pydantic 모델 정의
class Person(BaseModel):
    name: str = Field(description="사람의 이름")
    age: int = Field(description="사람의 나이")
    city: str = Field(description="거주 도시")

parser = PydanticOutputParser(pydantic_model=Person)

# JSON을 Pydantic 모델로 파싱
json_text = '{"name": "홍길동", "age": 30, "city": "서울"}'
result = parser.parse(json_text)
print(result)  # 출력: Person(name='홍길동', age=30, city='서울')
print(f"이름: {result.name}, 나이: {result.age}, 도시: {result.city}")
```

#### YAMLOutputParser

YAML 형식의 텍스트를 파싱하는 파서입니다.

```python
from src.output_parsers import YAMLOutputParser

parser = YAMLOutputParser()

# YAML 파싱
yaml_text = """
name: 홍길동
age: 30
city: 서울
hobbies:
  - 독서
  - 영화 감상
  - 여행
"""
result = parser.parse(yaml_text)
print(result)  # 출력: {'name': '홍길동', 'age': 30, 'city': '서울', 'hobbies': ['독서', '영화 감상', '여행']}
```

## ChatBot 클래스

ChatBot 클래스는 LLM 모델과 상호작용하는 기능을 제공합니다.

### 주요 메서드

#### 초기화

```python
from src.chatbot import ChatBot
from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser

# 기본 ChatBot 생성
chatbot = ChatBot(
    model_name="default",
    temperature=0.7,
    max_output_tokens=200,
    system_instruction="당신은 친절한 도우미입니다."
)

# InstructionConfig를 사용한 ChatBot 생성
instruction_config = InstructionConfig(
    instruction="당신은 {product}에 대한 정보를 제공하는 챗봇입니다.",
    input_variables=["product"],
    output_parser=JSONOutputParser()
)

chatbot = ChatBot(
    instruction_config=instruction_config
)
```

#### 채팅 시작

```python
# 채팅 세션 시작
chatbot.start_chat()
```

#### 메시지 전송

```python
# 기본 메시지 전송
response = chatbot.send_message("안녕하세요!")
print(response)

# 변수 값을 포함한 메시지 전송
response = chatbot.send_message("최신 스마트폰 정보 알려줘", product="스마트폰")
print(response)
```

#### 대화 기록 관리

```python
# 대화 기록 가져오기
conversation_history = chatbot.get_conversation_history()
for message in conversation_history:
    print(f"{message['role']}: {message['content']}")

# 대화 기록 초기화
chatbot.clear_conversation_history()
```

#### 대화형 실행

```python
# 대화형 모드로 실행
chatbot.run()
```

## 체인 기능

체인 기능은 여러 개의 LLM 호출, 프롬프트, 파서 등을 순차적으로 연결하여 복잡한 작업을 수행할 수 있는 메커니즘을 제공합니다.

### 주요 클래스

#### Chain

모든 체인의 기본 추상 클래스입니다.

```python
from src.chain import Chain

# 이 클래스는 직접 인스턴스화하지 않고 상속하여 사용합니다.
```

#### LLMChain

LLM을 사용하는 기본 체인입니다.

```python
from src.chain import LLMChain
from src.chatbot import ChatBot
from src.prompt import InstructionConfig
from src.output_parsers import ListOutputParser

# 프롬프트 템플릿 생성
prompt = InstructionConfig(
    instruction="다음 주제에 대한 세 가지 핵심 포인트를 알려주세요: {topic}",
    input_variables=["topic"],
    output_parser=ListOutputParser()
)

# ChatBot 생성
chatbot = ChatBot(
    system_instruction="당신은 교육 콘텐츠 전문가입니다."
)

# LLMChain 생성
chain = LLMChain(
    chatbot=chatbot,
    prompt=prompt,
    output_key="points"
)

# 체인 실행
result = chain.run({"topic": "인공지능의 미래", "user_input": "인공지능의 미래에 대해 알려주세요"})
print(result["points"])
```

#### SequentialChain

여러 체인을 순차적으로 실행하는 체인입니다.

```python
from src.chain import SequentialChain, LLMChain
from src.chatbot import ChatBot
from src.prompt import InstructionConfig
from src.output_parsers import ListOutputParser

# 첫 번째 체인: 주제에 대한 핵심 포인트 생성
points_prompt = InstructionConfig(
    instruction="다음 주제에 대한 세 가지 핵심 포인트를 알려주세요: {topic}",
    input_variables=["topic"],
    output_parser=ListOutputParser()
)

points_chatbot = ChatBot(
    system_instruction="당신은 교육 콘텐츠 전문가입니다."
)

points_chain = LLMChain(
    chatbot=points_chatbot,
    prompt=points_prompt,
    output_key="points"
)

# 두 번째 체인: 핵심 포인트를 바탕으로 요약 생성
summary_prompt = InstructionConfig(
    instruction="다음 핵심 포인트를 바탕으로 {topic}에 대한 간결한 요약을 작성해주세요:\n{points}",
    input_variables=["topic", "points"]
)

summary_chatbot = ChatBot(
    system_instruction="당신은 전문 작가입니다."
)

summary_chain = LLMChain(
    chatbot=summary_chatbot,
    prompt=summary_prompt,
    output_key="summary"
)

# SequentialChain 생성
sequential_chain = SequentialChain(
    chains=[points_chain, summary_chain],
    input_variables=["topic"],
    output_variables=["points", "summary"]
)

# 체인 실행
result = sequential_chain.run({"topic": "기후 변화"})
print(f"핵심 포인트: {result['points']}")
print(f"요약: {result['summary']}")
```

#### RouterChain

조건에 따라 다른 체인을 실행하는 라우터 체인입니다.

```python
from src.chain import RouterChain, LLMChain
from src.chatbot import ChatBot
from src.prompt import InstructionConfig

# 라우팅 함수 정의
def router_func(inputs):
    query = inputs.get("query", "").lower()
    if "날씨" in query or "기온" in query:
        return "weather"
    elif "뉴스" in query or "소식" in query:
        return "news"
    else:
        return "general"

# 날씨 체인
weather_prompt = InstructionConfig(
    instruction="다음 지역의 날씨 정보를 제공해주세요: {query}",
    input_variables=["query"]
)

weather_chatbot = ChatBot(
    system_instruction="당신은 기상 정보 전문가입니다."
)

weather_chain = LLMChain(
    chatbot=weather_chatbot,
    prompt=weather_prompt,
    output_key="response"
)

# 뉴스 체인
news_prompt = InstructionConfig(
    instruction="다음 주제에 대한 최신 뉴스를 알려주세요: {query}",
    input_variables=["query"]
)

news_chatbot = ChatBot(
    system_instruction="당신은 뉴스 기자입니다."
)

news_chain = LLMChain(
    chatbot=news_chatbot,
    prompt=news_prompt,
    output_key="response"
)

# 일반 체인
general_prompt = InstructionConfig(
    instruction="다음 질문에 답변해주세요: {query}",
    input_variables=["query"]
)

general_chatbot = ChatBot(
    system_instruction="당신은 친절한 도우미입니다."
)

general_chain = LLMChain(
    chatbot=general_chatbot,
    prompt=general_prompt,
    output_key="response"
)

# RouterChain 생성
router_chain = RouterChain(
    router_func=router_func,
    destination_chains={
        "weather": weather_chain,
        "news": news_chain,
        "general": general_chain
    }
)

# 체인 실행
weather_result = router_chain.run({"query": "서울 날씨 어때요?"})
print(f"날씨 질문 응답: {weather_result['response']}")

news_result = router_chain.run({"query": "최신 기술 뉴스 알려줘"})
print(f"뉴스 질문 응답: {news_result['response']}")
```

#### TransformChain

입력 데이터를 변환하는 체인입니다.

```python
from src.chain import TransformChain

# 변환 함수 정의
def transform_func(inputs):
    text = inputs.get("text", "")
    
    # 단어 수 계산
    word_count = len(text.split())
    
    # 문자 수 계산
    char_count = len(text)
    
    # 문장 수 계산
    sentence_count = len([s for s in text.split('.') if s.strip()])
    
    return {
        "word_count": word_count,
        "char_count": char_count,
        "sentence_count": sentence_count,
        "text": text  # 원본 텍스트도 유지
    }

# TransformChain 생성
transform_chain = TransformChain(
    transform_func=transform_func,
    input_variables=["text"],
    output_variables=["word_count", "char_count", "sentence_count", "text"]
)

# 체인 실행
text = "이것은 예시 문장입니다. 이 문장은 텍스트 분석을 위한 것입니다. 파이썬으로 텍스트를 분석해봅시다."
result = transform_chain.run({"text": text})

print(f"단어 수: {result['word_count']}")
print(f"문자 수: {result['char_count']}")
print(f"문장 수: {result['sentence_count']}")
```

## 메모리 시스템

메모리 시스템은 챗봇과의 이전 대화 내용을 기억하고 활용하여 맥락 있는 대화를 가능하게 합니다.

### 주요 클래스

#### Memory

모든 메모리 시스템의 기본 추상 클래스입니다.

```python
from src.memory import Memory

# 이 클래스는 직접 인스턴스화하지 않고 상속하여 사용합니다.
```

#### BufferMemory

단순한 버퍼 기반 메모리 시스템입니다.

```python
from src.memory import BufferMemory

# BufferMemory 생성
memory = BufferMemory(
    memory_key="chat_history",
    input_key="input",
    output_key="output"
)

# 대화 컨텍스트 저장
memory.save_context(
    inputs={"input": "안녕하세요!"},
    outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
)

memory.save_context(
    inputs={"input": "오늘 날씨 어때요?"},
    outputs={"output": "오늘은 맑고 화창한 날씨입니다."}
)

# 메모리 변수 로드
memory_variables = memory.load_memory_variables()
print(memory_variables["chat_history"])

# 메모리 초기화
memory.clear()
```

#### ConversationBufferWindowMemory

최근 k개의 대화만 기억하는 윈도우 기반 메모리 시스템입니다.

```python
from src.memory import ConversationBufferWindowMemory

# ConversationBufferWindowMemory 생성 (최근 2개 대화만 유지)
memory = ConversationBufferWindowMemory(
    k=2,
    memory_key="chat_history",
    input_key="input",
    output_key="output"
)

# 여러 대화 컨텍스트 저장
memory.save_context(
    inputs={"input": "안녕하세요!"},
    outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
)

memory.save_context(
    inputs={"input": "당신은 누구인가요?"},
    outputs={"output": "저는 AI 챗봇입니다."}
)

memory.save_context(
    inputs={"input": "오늘 날씨 어때요?"},
    outputs={"output": "오늘은 맑고 화창한 날씨입니다."}
)

# 메모리 변수 로드 (최근 2개 대화만 포함)
memory_variables = memory.load_memory_variables()
print(memory_variables["chat_history"])
```

#### ConversationSummaryMemory

대화 내용을 요약하여 저장하는 메모리 시스템입니다.

```python
from src.memory import ConversationSummaryMemory
from src.chatbot import ChatBot

# ChatBot 생성
chatbot = ChatBot(
    system_instruction="당신은 대화 요약 전문가입니다."
)

# ConversationSummaryMemory 생성
memory = ConversationSummaryMemory(
    chatbot=chatbot,
    memory_key="chat_summary",
    input_key="input",
    output_key="output"
)

# 여러 대화 컨텍스트 저장
for i in range(10):
    memory.save_context(
        inputs={"input": f"질문 {i}"},
        outputs={"output": f"답변 {i}"}
    )

# 메모리 변수 로드 (요약된 대화)
memory_variables = memory.load_memory_variables()
print(memory_variables["chat_summary"])
```

#### ConversationTokenBufferMemory

토큰 수를 기준으로 대화를 관리하는 메모리 시스템입니다.

```python
from src.memory import ConversationTokenBufferMemory

# ConversationTokenBufferMemory 생성 (최대 50 토큰 제한)
memory = ConversationTokenBufferMemory(
    max_token_limit=50,
    memory_key="chat_history",
    input_key="input",
    output_key="output"
)

# 여러 대화 컨텍스트 저장
memory.save_context(
    inputs={"input": "안녕하세요!"},
    outputs={"output": "안녕하세요! 무엇을 도와드릴까요?"}
)

memory.save_context(
    inputs={"input": "인공지능에 대해 알려주세요."},
    outputs={"output": "인공지능은 인간의 학습능력, 추론능력, 지각능력을 인공적으로 구현한 컴퓨터 시스템입니다."}
)

# 메모리 변수 로드 (토큰 제한에 따라 일부 대화만 포함될 수 있음)
memory_variables = memory.load_memory_variables()
print(memory_variables["chat_history"])

# 현재 토큰 수 확인
print(f"현재 토큰 수: {memory.current_token_count}")
```

## 통합 사용 예제

다음은 모든 기능을 통합하여 사용하는 예제입니다.

### 질문 응답 시스템

```python
from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser, ListOutputParser
from src.chatbot import ChatBot
from src.chain import LLMChain, SequentialChain, TransformChain
from src.memory import ConversationBufferWindowMemory

# 1. 메모리 시스템 설정
memory = ConversationBufferWindowMemory(
    k=5,
    memory_key="chat_history",
    input_key="input",
    output_key="output",
    return_messages=True
)

# 2. 질문 분석을 위한 체인 설정
question_analysis_prompt = InstructionConfig(
    instruction="다음 질문을 분석하여 주요 키워드를 추출해주세요: {question}",
    input_variables=["question"],
    output_parser=ListOutputParser()
)

question_analysis_chatbot = ChatBot(
    system_instruction="당신은 텍스트 분석 전문가입니다."
)

question_analysis_chain = LLMChain(
    chatbot=question_analysis_chatbot,
    prompt=question_analysis_prompt,
    output_key="keywords"
)

# 3. 답변 생성을 위한 체인 설정
answer_prompt = InstructionConfig(
    instruction="""
다음 질문에 대한 답변을 JSON 형식으로 작성해주세요:
질문: {question}

추출된 키워드: {keywords}

이전 대화 내용:
{chat_history}
""",
    input_variables=["question", "keywords", "chat_history"],
    output_parser=JSONOutputParser(),
    output_format={
        "answer": "질문에 대한 답변",
        "sources": "참고 자료 (있는 경우)",
        "confidence": "답변의 확신도 (0-100)"
    }
)

answer_chatbot = ChatBot(
    system_instruction="당신은 지식이 풍부한 도우미입니다."
)

answer_chain = LLMChain(
    chatbot=answer_chatbot,
    prompt=answer_prompt,
    output_key="response"
)

# 4. 변환 체인 설정 (메모리 업데이트 및 결과 포맷팅)
def transform_func(inputs):
    # 메모리 업데이트
    memory.save_context(
        inputs={"input": inputs["question"]},
        outputs={"output": inputs["response"]["answer"]}
    )
    
    # 결과 포맷팅
    return {
        "formatted_answer": f"답변: {inputs['response']['answer']}\n"
                           f"확신도: {inputs['response']['confidence']}%\n"
                           f"참고 자료: {inputs['response']['sources']}"
    }

transform_chain = TransformChain(
    transform_func=transform_func,
    input_variables=["question", "response"],
    output_variables=["formatted_answer"]
)

# 5. 전체 체인 설정
qa_chain = SequentialChain(
    chains=[question_analysis_chain, answer_chain, transform_chain],
    input_variables=["question"],
    output_variables=["keywords", "response", "formatted_answer"]
)

# 6. 시스템 실행
print("질문 응답 시스템을 시작합니다. 종료하려면 '종료'를 입력하세요.")

while True:
    question = input("\n질문: ")
    if question.lower() == '종료':
        break
    
    # 메모리에서 대화 기록 로드
    chat_history = memory.load_memory_variables()["chat_history"]
    chat_history_str = ""
    
    if chat_history:
        for msg in chat_history:
            chat_history_str += f"사용자: {msg['input']}\n시스템: {msg['output']}\n"
    
    # 체인 실행
    result = qa_chain.run({
        "question": question,
        "chat_history": chat_history_str
    })
    
    # 결과 출력
    print(result["formatted_answer"])
```

### 다중 도메인 지식 시스템

```python
from src.prompt import InstructionConfig
from src.output_parsers import JSONOutputParser
from src.chatbot import ChatBot
from src.chain import LLMChain, RouterChain, TransformChain, SequentialChain

# 1. 도메인 라우팅 함수
def domain_router(inputs):
    query = inputs.get("query", "").lower()
    
    if any(word in query for word in ["과학", "물리", "화학", "생물"]):
        return "science"
    elif any(word in query for word in ["역사", "사건", "인물", "시대"]):
        return "history"
    elif any(word in query for word in ["기술", "컴퓨터", "프로그래밍", "코딩"]):
        return "technology"
    else:
        return "general"

# 2. 각 도메인별 체인 설정
# 2.1 과학 도메인
science_prompt = InstructionConfig(
    instruction="다음 과학 관련 질문에 답변해주세요: {query}",
    input_variables=["query"],
    output_format={
        "answer": "과학적 답변",
        "field": "관련 과학 분야 (물리학, 화학, 생물학 등)",
        "confidence": "답변의 확신도 (0-100)"
    },
    output_parser=JSONOutputParser()
)

science_chatbot = ChatBot(
    system_instruction="당신은 과학 전문가입니다."
)

science_chain = LLMChain(
    chatbot=science_chatbot,
    prompt=science_prompt,
    output_key="result"
)

# 2.2 역사 도메인
history_prompt = InstructionConfig(
    instruction="다음 역사 관련 질문에 답변해주세요: {query}",
    input_variables=["query"],
    output_format={
        "answer": "역사적 답변",
        "period": "관련 시대 또는 연도",
        "confidence": "답변의 확신도 (0-100)"
    },
    output_parser=JSONOutputParser()
)

history_chatbot = ChatBot(
    system_instruction="당신은 역사 전문가입니다."
)

history_chain = LLMChain(
    chatbot=history_chatbot,
    prompt=history_prompt,
    output_key="result"
)

# 2.3 기술 도메인
technology_prompt = InstructionConfig(
    instruction="다음 기술 관련 질문에 답변해주세요: {query}",
    input_variables=["query"],
    output_format={
        "answer": "기술적 답변",
        "tech_area": "관련 기술 분야",
        "confidence": "답변의 확신도 (0-100)"
    },
    output_parser=JSONOutputParser()
)

technology_chatbot = ChatBot(
    system_instruction="당신은 기술 전문가입니다."
)

technology_chain = LLMChain(
    chatbot=technology_chatbot,
    prompt=technology_prompt,
    output_key="result"
)

# 2.4 일반 도메인
general_prompt = InstructionConfig(
    instruction="다음 질문에 답변해주세요: {query}",
    input_variables=["query"],
    output_format={
        "answer": "일반적인 답변",
        "topic": "관련 주제",
        "confidence": "답변의 확신도 (0-100)"
    },
    output_parser=JSONOutputParser()
)

general_chatbot = ChatBot(
    system_instruction="당신은 다양한 지식을 갖춘 도우미입니다."
)

general_chain = LLMChain(
    chatbot=general_chatbot,
    prompt=general_prompt,
    output_key="result"
)

# 3. 도메인 라우터 체인 설정
router_chain = RouterChain(
    router_func=domain_router,
    destination_chains={
        "science": science_chain,
        "history": history_chain,
        "technology": technology_chain,
        "general": general_chain
    }
)

# 4. 결과 포맷팅 체인
def format_result(inputs):
    result = inputs["result"]
    domain = inputs.get("_router_key", "unknown")
    
    formatted_answer = f"[도메인: {domain}]\n"
    formatted_answer += f"답변: {result['answer']}\n"
    formatted_answer += f"확신도: {result['confidence']}%\n"
    
    if domain == "science":
        formatted_answer += f"과학 분야: {result['field']}"
    elif domain == "history":
        formatted_answer += f"시대/연도: {result['period']}"
    elif domain == "technology":
        formatted_answer += f"기술 분야: {result['tech_area']}"
    elif domain == "general":
        formatted_answer += f"관련 주제: {result['topic']}"
    
    return {"formatted_answer": formatted_answer, "_router_key": domain}

format_chain = TransformChain(
    transform_func=format_result,
    input_variables=["result", "_router_key"],
    output_variables=["formatted_answer", "_router_key"]
)

# 5. 전체 체인 설정
knowledge_chain = SequentialChain(
    chains=[router_chain, format_chain],
    input_variables=["query"],
    output_variables=["formatted_answer", "_router_key"]
)

# 6. 시스템 실행
print("다중 도메인 지식 시스템을 시작합니다. 종료하려면 '종료'를 입력하세요.")
print("도메인: 과학, 역사, 기술, 일반")

while True:
    query = input("\n질문: ")
    if query.lower() == '종료':
        break
    
    # 체인 실행
    result = knowledge_chain.run({"query": query})
    
    # 결과 출력
    print(result["formatted_answer"])
```

## 테스트 및 디버깅

라이브러리의 각 구성 요소를 테스트하고 디버깅하는 방법입니다.

### 프롬프트 템플릿 테스트

```python
from src.prompt import SimplePromptTemplate, InstructionConfig

# 간단한 템플릿 테스트
template = SimplePromptTemplate(
    template="안녕하세요, {name}님!",
    input_variables=["name"]
)

result = template.format(name="홍길동")
assert result == "안녕하세요, 홍길동님!"
print("SimplePromptTemplate 테스트 성공")

# InstructionConfig 테스트
instruction_config = InstructionConfig(
    instruction="당신은 {role}입니다.",
    input_variables=["role"]
)

result = instruction_config.format(role="선생님")
assert result == "당신은 선생님입니다."
print("InstructionConfig 테스트 성공")
```

### 출력 파서 테스트

```python
from src.output_parsers import JSONOutputParser, ListOutputParser

# JSON 파서 테스트
json_parser = JSONOutputParser()
json_text = '{"name": "홍길동", "age": 30}'
result = json_parser.parse(json_text)
assert result["name"] == "홍길동" and result["age"] == 30
print("JSONOutputParser 테스트 성공")

# 리스트 파서 테스트
list_parser = ListOutputParser()
list_text = "항목1\n항목2\n항목3"
result = list_parser.parse(list_text)
assert result == ["항목1", "항목2", "항목3"]
print("ListOutputParser 테스트 성공")
```

### ChatBot 테스트

```python
from src.chatbot import ChatBot

# 기본 ChatBot 테스트
chatbot = ChatBot(
    system_instruction="당신은 테스트 챗봇입니다."
)

chatbot.start_chat()
response = chatbot.send_message("안녕하세요!")
print(f"ChatBot 응답: {response}")

# 대화 기록 테스트
history = chatbot.get_conversation_history()
assert len(history) == 2  # 사용자 메시지와 챗봇 응답
print("ChatBot 대화 기록 테스트 성공")
```

### 체인 테스트

```python
from src.chain import TransformChain

# TransformChain 테스트
def transform_func(inputs):
    text = inputs.get("text", "")
    return {"length": len(text), "text": text}

transform_chain = TransformChain(
    transform_func=transform_func,
    input_variables=["text"],
    output_variables=["length", "text"]
)

result = transform_chain.run({"text": "테스트 텍스트"})
assert result["length"] == 7
print("TransformChain 테스트 성공")
```

### 메모리 시스템 테스트

```python
from src.memory import BufferMemory

# BufferMemory 테스트
memory = BufferMemory(
    memory_key="chat_history",
    input_key="input",
    output_key="output"
)

memory.save_context(
    inputs={"input": "테스트 입력"},
    outputs={"output": "테스트 출력"}
)

memory_variables = memory.load_memory_variables()
assert "chat_history" in memory_variables
print("BufferMemory 테스트 성공")
```

## 결론

이 라이브러리는 Langchain의 주요 기능들을 파이썬으로 직접 구현하여 의존성 및 유지보수 문제를 해결하고, 더 사용자 친화적이며 객체 지향적인 코드를 제공합니다. 프롬프트 템플릿, 출력 파서, ChatBot, 체인 기능, 메모리 시스템 등의 기능을 통해 LLM 기반 애플리케이션을 쉽게 개발할 수 있습니다.

각 구성 요소는 모듈화되어 있어 필요한 기능만 선택적으로 사용할 수 있으며, 확장성이 뛰어나 새로운 기능을 쉽게 추가할 수 있습니다. 예제 코드와 통합 사용 예제를 참고하여 라이브러리를 효과적으로 활용하세요.
