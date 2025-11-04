from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, SparseIndexParams
from embedding import content_embedder
from vector_db_helper import upsert_folder
from config import FORMATS

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, SparseIndexParams


def auto_recreate_collections(client: QdrantClient):
    """
    컬렉션의 Dense/Sparse/Splade 벡터 스키마를 검증하고,
    불일치 시 자동 삭제 후 재생성.
    """
    target_schema = {
        "dense": VectorParams(size=768, distance=Distance.COSINE),
    }
    target_sparse_schema = {
        "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False)),
        "splade": SparseVectorParams(index=SparseIndexParams(on_disk=False)),
    }

    for col_name in ["notion.notice", "notion.marketing"]:
        recreate = False
        try:
            info = client.get_collection(col_name)
            vecs = getattr(info.config.params, "vectors", None)
            sparse_vecs = getattr(info.config.params, "sparse_vectors", None)

            # Sparse 벡터 정의가 없거나 틀린 경우
            if not sparse_vecs or "sparse" not in sparse_vecs or "splade" not in sparse_vecs:
                print(f"[Schema Mismatch] '{col_name}' missing sparse vectors → will recreate")
                recreate = True
        except Exception:
            recreate = True

        if recreate:
            try:
                client.delete_collection(col_name)
                print(f"[Delete] Removed old collection '{col_name}'")
            except Exception:
                pass

            print(f"[Recreate] Creating new collection '{col_name}' with full schema...")
            client.recreate_collection(
                collection_name=col_name,
                vectors_config=target_schema,
                sparse_vectors_config=target_sparse_schema,
            )
        else:
            print(f"[OK] Collection '{col_name}' matches expected schema.")


def init_recreate_collections(client: QdrantClient):
    """
    명시적으로 dense/sparse/splade 컬렉션을 모두 새로 만든다.
    """
    for col_name in ["notion.notice", "notion.marketing"]:
        print(f"Recreating collection: {col_name}")
        client.recreate_collection(
            collection_name=col_name,
            vectors_config={
                "dense": VectorParams(size=768, distance=Distance.COSINE),
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False)),
                "splade": SparseVectorParams(index=SparseIndexParams(on_disk=False)),
            },
        )


def init_upsertall(client, path):
    """
    path 아래 모든 폴더의 JSON 파일을 DB에 업로드
    """
    for col_name in FORMATS.keys():
        folder_name = col_name.replace(".", "/")
        upsert_folder(client, path + folder_name, col_name)