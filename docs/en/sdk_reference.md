# Python SDK Reference

The `vectordb` package is the official Python client for interacting with the VortexDB server.

## Installation & Initialization

```bash
pip install .
```

### Client Types
1.  **VectorDBClient (Sync)**: Built on `requests`. Ideal for data ingestion scripts or CLI tools.
2.  **AsyncVectorDBClient (Async)**: Built on `httpx`. Ideal for asynchronous web frameworks like FastAPI.
3.  **VectorDBManager (Library)**: Use the DB and models directly within Python code without a server.

### Initialization Examples
```python
from vectordb.client.sync_client import VectorDBClient

# 1. Use Environment Variables / Defaults
client = VectorDBClient()

# 2. Explicit Configuration
client = VectorDBClient(base_url="http://10.20.30.40:8000", api_key="your_jwt_token")
```

---

## Configuration & Options

VortexDB offers various configuration options. The priority order is: **Environment Variables** > **YAML Config File** > **Defaults**.

### 1. Key Environment Variables
| Env Variable | Description | Default |
| :--- | :--- | :--- |
| `VECTORDB_ENV` | Execution Environment (`development` / `production`) | `development` |
| `VECTORDB_HOST` | API Server Host | `0.0.0.0` |
| `VECTORDB_PORT` | API Server Port | `8000` |
| `VECTORDB_API_KEY` | (Legacy) Master API Key | `None` |
| `QDRANT_URL` | Qdrant Vector DB URL | `http://localhost:6333` |
| `QDRANT_API_KEY` | Qdrant Key (if required) | `None` |
| `DEFAULT_COLLECTION_NAME`| Default Target Collection | `notion.marketing` |

### 2. Model & Algorithm Settings
Settings for tuning advanced search capabilities.

| Env Variable | Description | Default |
| :--- | :--- | :--- |
| `VECTOR_MODEL_PATH` | Dense Embedding Model Path/Name | `./bge-m3-finetuned-academic` |
| `BM25_PATH` | BM25 (Sparse) Index Path | `./models/bm25_vectorizer.pkl` |
| `SPLADE_MODEL_NAME` | SPLADE (Neural Sparse) Model Name | `yjoonjang/splade-ko-v1` |
| `SPLADE_DEVICE` | SPLADE Device (`cpu` / `cuda`) | `cpu` |
| `SPLADE_THRESHOLD` | Token Activation Threshold (0.0~1.0) | `0.01` |

---

## Library Mode

Run the search pipeline directly within your Python code without HTTP requests using `VectorDBManager`.

```python
from llm_backend.vectorstore.vector_db_manager import VectorDBManager

# Initialize
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

# Search Example
results = db.search(
    query_text="Scholarship criteria",
    top_k=3,
    alpha=0.5
)
print(results)
```

### Search Parameters
Detailed options for the `search()` method.

- **`query_text`** (str): The query string (Required).
- **`top_k`** (int): Number of results to return (Default: 10).
- **`alpha`** (float): Hybrid search weighting (0.0 ~ 1.0).
    - `1.0`: Dense (Semantic) Search 100%
    - `0.0`: Sparse (Keyword) Search 100%
    - `0.5`: 50:50 Balance
- **`filter_`** (dict, optional): Qdrant metadata filters.

---

## Authentication

VortexDB uses JWT-based authentication for security.

### Login via CLI
Log in via terminal first. Credentials are saved to `~/.vortex/credentials`, allowing the client to auto-authenticate.
```bash
python -m vectordb login
```

### Dynamic Auth in Code
```python
# Acquire and set a new token using password
# (Also possible via LOGIN command in Interactive Search Shell)
```

---

## Data Management (Ingestion & CRUD)

### Batch Upsert
Efficiently upload large amounts of data. Automatic chunking is performed internally.

```python
docs = [
    {"id": "doc_1", "content": "Long text...", "author": "Alice"},
    {"id": "doc_2", "content": "Another document...", "author": "Bob"}
]

# Set wait=True to poll until completion.
client.upsert(collection="my_data", documents=docs, wait=True)
```

### Get Document
```python
doc = client.get_document(collection="my_data", db_id="doc_1")
```

---

## Async Client

Use when high-performance asynchronous processing is required.

```python
from vectordb.client.async_client import AsyncVectorDBClient

async def main():
    client = AsyncVectorDBClient()
    results = await client.search("test query")
    await client.upsert("coll", [{"content": "Async data"}])

import asyncio
asyncio.run(main())
```

---

## Error Handling & Retries

The SDK includes **Exponential Backoff** logic to automatically retry temporary network failures.

```python
from requests.exceptions import HTTPError

try:
    client.search("...")
except HTTPError as e:
    if e.response.status_code == 403:
        print("Unauthorized. Please check your login.")
```
