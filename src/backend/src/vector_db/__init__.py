from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from embedding import content_embedder
from vector_db_helper import create_doc_upsert
import json


# 컬렉션(테이블) 생성, only once
client.recreate_collection(
    collection_name="portal.job",
    vectors_config={
        "vector": VectorParams(
            size=VECTOR_SIZE, # 벡터 차원 수
            distance=DISTANCE  # 유사도 계산 방식
        )
    }
)