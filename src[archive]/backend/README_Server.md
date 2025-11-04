# KAIST 전산학부 ChatBot FastAPI 서버

KAIST 전산학부 학생 지원을 위한 지능형 챗봇의 REST API 서버입니다.

## 주요 기능

- 🤖 OpenAI GPT 기반 자연어 처리
- 🔍 Vector DB (Qdrant) 기반 정보 검색
- 📚 전산학부 특화 정보 제공
- ⚡ FastAPI 기반 고성능 REST API
- 🔄 실시간 질의응답

## 설치 및 실행

### 1. 필요 패키지 설치 (conda 사용 권장)

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정(api key는 노션 참고)

`.env` 파일을 생성하고 다음 내용을 추가하세요:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

### 3. 서버 실행

#### 방법 1: Python 스크립트 실행
```bash
python run_server.py
```

#### 방법 2: Uvicorn 직접 실행
```bash
uvicorn src.server.server:app --host 0.0.0.0 --port 8000 --reload
```

서버가 성공적으로 시작되면 다음 주소로 접속할 수 있습니다:
- 서버: http://localhost:8000
- API 문서: http://localhost:8000/docs

## API 엔드포인트

### GET /
- 루트 엔드포인트
- 서버 정보 반환

### GET /health
- 서비스 상태 확인
- 모든 컴포넌트의 상태 정보 제공

### POST /chat
- 채팅 대화 엔드포인트
- 사용자 질문에 대한 챗봇 응답 제공

**요청 예시:**
```json
{
  "message": "전산학부 졸업 요건이 뭐야?",
  "use_vector_search": true
}
```

**응답 예시:**
```json
{
  "response": "KAIST 전산학부 졸업 요건은...",
  "success": true,
  "message": "답변 생성 완료"
}
```

### GET /info
- API 정보 제공
- 사용 가능한 기능 및 엔드포인트 목록

## 아키텍처

```
src/
├── server/
│   ├── __init__.py          # 서버 패키지 초기화
│   ├── server.py            # FastAPI 애플리케이션
│   ├── models.py            # Pydantic 모델 정의
│   └── chatbot_service.py   # ChatBot 서비스 클래스
├── llm/                     # LLM 관련 모듈들
│   ├── openai_chatbot.py    # OpenAI ChatBot
│   ├── vector_searcher.py   # Vector DB 검색
│   └── openai_parser.py     # 입력 처리
└── backend/
    ├── main.py              # 기존 콘솔 애플리케이션
    └── requirements.txt     # 의존성 목록
```

## 개발 참고사항

### ChatBot 서비스 초기화
- 서버 시작시 한 번만 실행됨
- OpenAI API 클라이언트, Vector DB 검색기 등 모든 컴포넌트 초기화
- 시스템 워밍업을 통한 첫 응답 지연 최소화

### 요청 처리 흐름
1. 사용자 입력 수신
2. 입력 정규화 (OpenAI 기반)
3. 입력 유효성 검사 (선택적)
4. Vector DB 검색 및 컨텍스트 생성
5. OpenAI API를 통한 최종 응답 생성

### 에러 처리
- 각 단계별 예외 처리
- 대안 검색 시스템 (OpenAI 실패시 Vector DB만 사용)
- 구조화된 에러 응답

## 트러블슈팅

### 1. OPENAI_API_KEY 오류
```
❌ OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.
```
→ `.env` 파일에 올바른 OpenAI API 키 설정

### 2. Vector DB 연결 실패
→ Qdrant 서버가 실행 중인지 확인

### 3. 패키지 import 오류
```bash
pip install -r requirements.txt
```

## 라이센스

KAIST 전산학부 집행위원회