# 챗봇 프로젝트 (llm)

## 소개
이 프로젝트는 **OpenAI + PostgreSQL(pgvector)** 기반의 KAIST 전산학부 챗봇 백엔드와 데이터 파이프라인을 포함합니다.

## 요구사항
- Python 3.10 이상
- uv
- PostgreSQL (+ `pgvector` extension)

## 설치
```bash
cd llm
uv sync
```

## 환경 변수
`.env` 파일에 아래 값을 설정하세요.

```env
OPENAI_API_KEY=your_openai_api_key
# 둘 중 하나 사용 (POSTGRES_DSN 우선)
POSTGRES_DSN=host=localhost port=5432 dbname=postgres user=your_user password=your_password
DATABASE_URL=postgresql://your_user:your_password@localhost:5432/your_db
# 선택: 기본값 text-embedding-3-small
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## 실행

### API 서버 시작
```bash
uv run python src/backend/run_server.py
```

API 문서: `http://localhost:8000/docs`

## 현재 프로젝트 구조 (핵심)
- `src/backend/server/`: FastAPI 서버
- `src/backend/llm/`: 입력검증/정규화, 답변 생성, 검색 연동
- `src/backend/vector_db/`: pgvector 적재/검색
- `crawler/`: csweb/notion/portal 크롤러
- `data/`: 크롤링/정규화 데이터
- `DB/`: 별도 관계형/KG 스키마 및 시드 SQL

## 참고
csweb 크롤러에서 공지 본문이 이미지뿐인 경우 파싱 경고가 발생할 수 있습니다.
