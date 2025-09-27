# KAIST 전산학부 지능형 챗봇

Vector DB 검색과 OpenAI API를 활용한 KAIST 전산학부 학생 지원 챗봇입니다.

## 🚀 주요 기능

1. **Vector DB 기반 정보 검색**: 전산학부 관련 문서에서 유사한 정보를 최대 30개까지 검색
2. **OpenAI 기반 지능형 응답**: GPT 모델을 활용한 자연스러운 대화형 응답
3. **입력 검증 및 정규화**: OpenAI API를 활용한 질문 유효성 검사 및 정규화
4. **통합 정보 제공**: 검색된 정보와 AI 응답을 결합한 포괄적인 답변

## 📋 지원하는 정보

- 전산학부 학사 과정 및 교과 과정 정보
- 전산학부 행사 및 프로그램 안내
- 전산학부 내 학생 지원 시스템 정보
- 교수진 정보 및 연구 분야
- 최신 뉴스 및 공지사항
- 취업 정보 및 스타트업 정보

## 🛠️ 설치 및 설정

### 1. 의존성 설치

```bash
cd /Users/youngseocho/Desktop/socChatbot/llm/src/backend
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일에 다음 API 키를 설정하세요:

```bash
# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key_here

# Qdrant Vector DB 설정
QDRANT_URL=https://897a4e03-5fcc-42a2-b3e2-ed5ab54fd160.us-west-1-0.aws.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key_here

# 애플리케이션 설정
MODEL_NAME=gpt-4o-mini
VECTOR_SIZE=768
TOP_K_RESULTS=30
```

### 3. API 키 발급 방법

#### OpenAI API Key
1. [OpenAI Platform](https://platform.openai.com/api-keys)에서 API 키 발급
2. `.env` 파일의 `OPENAI_API_KEY`에 입력

## 🎯 사용 방법

### 기본 실행

```bash
cd /Users/youngseocho/Desktop/socChatbot/llm/src/backend
python main_enhanced.py
```

### 사용 예시

```
👤 질문: 컴퓨터구조 수업 정보 알려줘

🔍 질문을 분석하고 있습니다...
📝 정규화된 질문: 컴퓨터구조 수업에 대한 정보를 알려주세요
🔍 관련 정보를 검색하고 답변을 생성하는 중...

🤖 답변:
컴퓨터구조 수업에 대한 정보를 알려드리겠습니다...
```

### 지원 명령어

- `help`: 도움말 표시
- `exit`: 챗봇 종료

## 🏗️ 시스템 구조

```
llm/src/backend/
├── main_enhanced.py          # 개선된 메인 애플리케이션
├── src/llm/
│   ├── vector_searcher.py    # Vector DB 검색 모듈
│   ├── openai_chatbot.py     # OpenAI 챗봇 모듈
│   ├── parser_llm.py         # 기존 입력 검증/정규화 모듈
│   └── __init__.py           # 모듈 초기화
├── src/vector_db/            # Vector DB 관련 코드
│   ├── vector_db_helper.py   # DB 헬퍼 함수
│   ├── config.py             # 설정 파일
│   └── embedding.py          # 임베딩 처리
└── requirements.txt          # 의존성 목록
```

## 🔧 기술 스택

- **언어**: Python 3.8+
- **AI 모델**: 
  - OpenAI GPT-4o-mini (응답 생성 및 입력 검증)
  - Korean RoBERTa (문서 임베딩)
- **Vector DB**: Qdrant Cloud
- **기타**: sentence-transformers, scikit-learn, kss

## 📈 성능 특징

- **검색 속도**: Vector DB를 통한 빠른 유사 문서 검색
- **정확성**: 한국어 특화 임베딩 모델 사용
- **확장성**: 모듈형 구조로 쉬운 기능 추가 가능
- **안정성**: 포괄적인 오류 처리 및 대안 경로 제공

## 🐛 문제 해결

### Vector DB 연결 실패
- `QDRANT_API_KEY` 환경 변수 확인
- 네트워크 연결 상태 확인
- Qdrant 서비스 상태 확인

### OpenAI API 오류
- `OPENAI_API_KEY` 환경 변수 확인
- API 사용량 한도 확인
- API 키 권한 확인

### 한국어 처리 오류
- `kss` 패키지 설치 확인
- 입력 텍스트 인코딩 확인

## 📝 업데이트 로그

### v2.0.0 (현재)
- Vector DB 통합 검색 기능 추가
- OpenAI GPT 모델 통합
- 한국어 특화 임베딩 모델 적용
- 모듈형 구조로 리팩토링
- 포괄적인 오류 처리 개선

### v1.0.0 (기존)
- Google Gemini 기반 기본 챗봇
- 입력 검증 및 정규화 기능
- 쿼리 생성 및 필터링 기능

## 🤝 기여 방법

1. 이슈 등록
2. 기능 브랜치 생성
3. 코드 작성 및 테스트
4. Pull Request 생성

## 📄 라이선스

KAIST 전산학부 집행위원회 개발 프로젝트