# Python SDK Reference (Korean)

`vectordb` 패키지는 VortexDB 서버와 상호작용하기 위한 공식 파이썬 클라이언트입니다.

## 설치 및 초기화

```bash
pip install .
```

### 클라이언트 유형
1.  **VectorDBClient (Sync)**: `requests` 기반. 데이터 수집 스크립트나 터미널 도구에 적합합니다.
2.  **AsyncVectorDBClient (Async)**: `httpx` 기반. FastAPI 등 비동기 웹 프레임워크에 적합합니다.
3.  **VectorDBManager (Library)**: 서버 없이 파이썬 코드 내에서 직접 DB 및 모델을 로드하여 사용합니다.

### 초기 생성 예시
```python
from vectordb.client.sync_client import VectorDBClient

# 1. 환경 변수/기본값 사용
client = VectorDBClient()

# 2. 명시적 주소 및 키 설정
client = VectorDBClient(base_url="http://10.20.30.40:8000", api_key="your_jwt_token")
```

---

## 설정 및 옵션 (Configuration)

VortexDB는 다양한 설정 옵션을 제공하며, **환경 변수(Environment Variable)** > **YAML 설정 파일** > **기본값** 순으로 우선순위가 적용됩니다.

### 1. 주요 환경 변수
| 환경 변수 | 설명 | 기본값 |
| :--- | :--- | :--- |
| `VECTORDB_ENV` | 실행 환경 (`development` / `production`) | `development` |
| `VECTORDB_HOST` | API 서버 호스트 | `0.0.0.0` |
| `VECTORDB_PORT` | API 서버 포트 | `8000` |
| `VECTORDB_API_KEY` | (Legacy) 마스터 API 키 | `None` |
| `QDRANT_URL` | Qdrant 벡터 DB 주소 | `http://localhost:6333` |
| `QDRANT_API_KEY` | Qdrant 접속 키 (필요 시) | `None` |
| `DEFAULT_COLLECTION_NAME`| 기본 타겟 컬렉션 이름 | `notion.marketing` |

### 2. 모델 및 알고리즘 설정
고급 검색 기능을 튜닝하기 위한 설정입니다.

| 환경 변수 | 설명 | 기본값 |
| :--- | :--- | :--- |
| `VECTOR_MODEL_PATH` | Dense 임베딩 모델 경로/이름 | `./bge-m3-finetuned-academic` |
| `BM25_PATH` | BM25(Sparse) 인덱스 파일 경로 | `./models/bm25_vectorizer.pkl` |
| `SPLADE_MODEL_NAME` | SPLADE(Neural Sparse) 모델 이름 | `yjoonjang/splade-ko-v1` |
| `SPLADE_DEVICE` | SPLADE 연산 장치 (`cpu` / `cuda`) | `cpu` |
| `SPLADE_THRESHOLD` | 토큰 활성화 임계값 (0.0~1.0) | `0.01` |

---

## 라이브러리 모드 (Library Mode)

HTTP 요청 없이 코드 내에서 직접 `VectorDBManager`를 사용하여 검색 파이프라인을 실행합니다.

```python
from llm_backend.vectorstore.vector_db_manager import VectorDBManager

# 초기화
db = VectorDBManager(
    url="http://localhost:6333",
    default_collection="sockaist",
    pipeline_config={
        "use_dense": True,
        "use_sparse": True,   # BM25
        "use_splade": True,   # SPLADE
        "use_reranker": True, # Reranking
        "weights": {
            "dense": 0.4,
            "sparse": 0.1,
            "splade": 0.5
        }
    }
)
```

### 검색 옵션 (Search Parameters)
`search()` 메소드 호출 시 사용 가능한 상세 옵션입니다.

- **`query_text`** (str): 검색할 쿼리 문자열 (필수)
- **`top_k`** (int): 반환할 결과 개수 (기본: 10)
- **`alpha`** (float): 하이브리드 검색 가중치 (0.0 ~ 1.0)
    - `1.0`: Dense(의미) 검색 100%
    - `0.0`: Sparse(키워드) 검색 100%
    - `0.5`: 50:50 조화
- **`filter_`** (dict, optional): Qdrant 메타데이터 필터

---

## 인증 (Authentication)

VortexDB는 보안을 위해 JWT 기반 인증을 사용합니다.

### CLI를 통한 로그인
터미널에서 먼저 로그인을 수행하면 자격 증명이 `~/.vortex/credentials`에 저장되어, 클라이언트 생성 시 별도의 키 없이도 자동 인증됩니다.
```bash
python -m vectordb login
```

### 코드 내에서의 로그인 (Dynamic Auth)
```python
# 비밀번호 기반으로 새 토큰 획득 및 설정
# (Interactive Search Shell 내에서 LOGIN 명령어로도 가능)
```

---

## 데이터 관리 (Ingestion & CRUD)

### 배치 업로드 (Batch Upsert)
대량의 데이터를 효율적으로 업로드하며, 내부적으로 자동 청킹(Chunking)을 수행합니다.

```python
docs = [
    {"id": "doc_1", "content": "긴 텍스트...", "author": "홍길동"},
    {"id": "doc_2", "content": "또 다른 문서...", "author": "이몽룡"}
]

# wait=True 설정 시 처리가 완료될 때까지 폴링(Polling)합니다.
client.upsert(collection="my_data", documents=docs, wait=True)
```

### 단일 문서 조회
```python
doc = client.get_document(collection="my_data", db_id="doc_1")
```

---

## 비동기 클라이언트 (Async Client)

고성능 비동기 처리가 필요한 경우 사용합니다.

```python
from vectordb.client.async_client import AsyncVectorDBClient

async def main():
    client = AsyncVectorDBClient()
    results = await client.search("테스트 쿼리")
    await client.upsert("coll", [{"content": "Async data"}])

import asyncio
asyncio.run(main())
```

---

## 오류 처리 및 재시도

SDK는 일시적인 네트워크 순전 등을 극복하기 위해 **지수 백오프(Exponential Backoff)** 기반의 자동 재시도 로직을 포함하고 있습니다.

```python
from requests.exceptions import HTTPError

try:
    client.search("...")
except HTTPError as e:
    if e.response.status_code == 403:
        print("권한이 없습니다. 로그인을 확인하세요.")
```
