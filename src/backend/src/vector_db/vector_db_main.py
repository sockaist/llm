# Instal Docker: brew install --cask docker
# pip install 'qdrant-client[fastembed]'

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

client = QdrantClient(url = "http://localhost:6333")

# 2) 컬렉션(테이블) 생성
client.recreate_collection(
    collection_name="my_collection",
    vectors_config={
        "vector": VectorParams(
            size=128,             # 벡터 차원 수
            distance=Distance.COSINE  # 유사도 계산 방식
        )
    }
)

# 3) 벡터(포인트) 삽입
points = [
    PointStruct(id=1, vector=[0.1]*128, payload={"text": "첫 번째 문서"}),
    PointStruct(id=2, vector=[0.2]*128, payload={"text": "두 번째 문서"}),
]
client.upsert(collection_name="my_collection", points=points)

# 4) 유사도 검색 (쿼리 벡터를 넣고 top-2 검색)
results = client.search(
    collection_name="my_collection",
    query_vector=[0.15]*128,
    limit=2
)

for hit in results:
    print(f"ID={hit.id}, 거리={hit.score:.4f}, payload={hit.payload}")
