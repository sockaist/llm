# VortexDB (LLM Vector Backend)

VortexDB는 **Qdrant** 기반의 고성능 벡터 데이터베이스 서버로, 하이브리드 검색(Dense + Sparse + Splade)과 정교한 재정렬(Rerank), 그리고 역할 기반 접근 제어(RBAC)를 제공합니다.

## 🔥 주요 기능 (Features)

*   **하이브리드 검색 (Hybrid Search)**
    *   **Dense**: `BAAI/bge-m3` 기반 의미론적 검색
    *   **Sparse**: BM25 (키워드 매칭) + SPLADE (의미론적 희소 벡터)
    *   **Rerank**: Cross-Encoder (`bge-reranker-v2-m3`)를 이용한 정밀 순위 재조정
    *   **Fusion**: RRF (Reciprocal Rank Fusion) 알고리즘을 통한 결과 최적화
*   **엔터프라이즈 보안 (Security)**
    *   **RBAC**: 사용자 역할(Admin, User, Guest) 및 테넌트 기반 데이터 격리
    *   **Secure Logging**: HMAC 서명을 통한 로그 무결성 보장 및 감사(Audit) 추적
    *   **API Security**: API Key 인증 및 미들웨어 기반 접근 제어
*   **프로덕션 수준 배포 (Production Ready)**
    *   Redis 캐싱 및 동시성 제어
    *   Docker & Docker Compose 기반의 간편한 배포
    *   Celery를 이용한 비동기 작업 처리

## 🏗 아키텍처 (Architecture)

```mermaid
graph TD
    Client[Client App] -->|REST API| Server[Vector Server (FastAPI)]
    Server -->|Auth & Audit| Middleware[Security Middleware]
    Middleware -->|Search Request| Pipeline[Search Pipeline]
    
    subgraph "Engines"
        Pipeline -->|Dense| DenseEng[Dense Engine]
        Pipeline -->|Sparse/Keywords| SparseEng[Sparse Engine (BM25/SPLADE)]
    end
    
    subgraph "Optimization"
        Pipeline -->|Rank| RerankEng[Rerank Engine]
        Pipeline -->|Merge| FusionEng[Fusion Engine (RRF)]
    end

    Server -->|Metadata/Cache| Redis[(Redis)]
    Server -->|Vectors| Qdrant[(Qdrant)]
```

## 🚀 시작하기 (Getting Started)

### 사전 요구 사항
*   Docker & Docker Compose
*   (로컬 실행 시) Python 3.10+

### 1. 환경 설정
`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 설정을 수정합니다.
```bash
cp .env.example .env
# .env 파일을 열어 VECTOR_API_KEY 등을 변경하세요.
```

### 2. Docker로 실행 (권장)
```bash
docker-compose up -d --build
```
*   **API Server**: `http://localhost:8000`
*   **Qdrant UI**: `http://localhost:6333/dashboard`

### 3. 로컬 개발 환경 실행
```bash
# 가상환경 생성 및 의존성 설치
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Qdrant 및 Redis 실행 (Docker 이용)
docker-compose up -d qdrant redis

# 서버 실행
python start.py
```

### 4. SDK (Python Client)
`src/llm_backend/client.py`를 통해 간편하게 서버와 통신할 수 있습니다.

```python
from llm_backend.client import VectorDBClient

client = VectorDBClient(base_url="http://localhost:8000")
client.upsert("my_collection", [{"id": "1", "content": "hello"}])
results = client.search("my_collection", "hello")
```

� **[Jupyter Notebook 튜토리얼](docs/examples/tutorial.ipynb)** 에서 상세 예제를 확인하세요.

## �📚 API 사용법 (Quick Guide)

### 헬스 체크
```http
GET /health
```

### 문서 업로드 (Upsert)
**Auth Required**: `x-api-key: YOUR_KEY`
```http
POST /api/v1/ingest/upsert
Content-Type: application/json

{
  "collection_name": "my_collection",
  "documents": [
    {
      "id": "doc1",
      "content": "이것은 테스트 문서입니다.",
      "metadata": {
        "title": "테스트",
        "tenant_id": "user_1",
        "access_level": 1
      }
    }
  ]
}
```

### 하이브리드 검색 (Search)
```http
POST /api/v1/search/query
Content-Type: application/json

{
  "collection_name": "my_collection",
  "query": "테스트 문서",
  "top_k": 5,
  "user_context": {
    "user_id": "user_1",
    "role": "user"
  }
}
```

## 📚 문서 (Documentation)
더 자세한 내용은 `docs/` 디렉토리를 참고하세요.
*   🇺🇸 [English Documentation](docs/en/README.md)
*   🇰🇷 [한국어 문서](docs/ko/README.md)
*   🐍 [Python Client SDK Guide](docs/examples/tutorial.ipynb)

## 🧪 테스트 (Testing)
전체 테스트 스위트 실행:
```bash
pytest src/tests/
```

## 📝 라이선스
MIT License