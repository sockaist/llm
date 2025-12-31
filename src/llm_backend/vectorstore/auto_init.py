from qdrant_client import QdrantClient
import os
import json
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, SparseIndexParams
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace
from llm_backend.vectorstore.vector_db_manager import VectorDBManager
from llm_backend.utils.id_helper import make_doc_hash_id_from_json
from llm_backend.vectorstore.vector_db_helper import create_doc_upsert
from llm_backend.vectorstore.config import FORMATS



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
            trace(f"Checking schema for {col_name}")
            info = client.get_collection(col_name)
            getattr(info.config.params, "vectors", None)
            sparse_vecs = getattr(info.config.params, "sparse_vectors", None)

            if not sparse_vecs or "sparse" not in sparse_vecs or "splade" not in sparse_vecs:
                logger.warning(f"[Schema Mismatch] '{col_name}' missing sparse vectors → will recreate")
                recreate = True
        except Exception as e:
            logger.warning(f"[Missing Collection] '{col_name}' not found → will recreate ({e})")
            recreate = True

        if recreate:
            try:
                client.delete_collection(col_name)
                logger.info(f"[Delete] Removed old collection '{col_name}'")
            except Exception:
                logger.warning(f"Failed to delete collection '{col_name}', may not exist")

            logger.info(f"[Recreate] Creating new collection '{col_name}' with full schema...")
            client.recreate_collection(
                collection_name=col_name,
                vectors_config=target_schema,
                sparse_vectors_config=target_sparse_schema,
            )
        else:
            logger.info(f"[OK] Collection '{col_name}' matches expected schema.")


def init_recreate_collections(client: QdrantClient):
    """
    명시적으로 dense/sparse/splade 컬렉션을 모두 새로 만든다.
    """
    for col_name in ["notion.notice", "notion.marketing"]:
        logger.info(f"Recreating collection: {col_name}")
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



def init_upsertall(client, base_path: str):
    """
    base_path 아래 FORMATS에 정의된 모든 폴더를 스캔하여
    각 JSON 문서를 DB에 업로드한다.
    각 문서는 make_doc_hash_id_from_json()으로 생성된 db_id를 사용.
    vector_db_helper.create_doc_upsert()을 직접 호출하여 일관된 업서트 경로 유지.
    """
    mgr = VectorDBManager()
    trace_msg = f"[InitUpsertAll] Scanning base_path={base_path}"
    print(trace_msg)
    logger.info(trace_msg)

    for col_name in FORMATS.keys():
        folder_path = os.path.join(base_path, col_name.replace(".", "/"))
        if not os.path.exists(folder_path):
            logger.warning(f"[InitUpsertAll] Folder not found: {folder_path}")
            continue

        logger.info(f"[InitUpsertAll] Processing folder → {folder_path} → collection: {col_name}")
        files = [f for f in os.listdir(folder_path) if f.endswith(".json")]

        success, fail = 0, 0
        for f in files:
            file_path = os.path.join(folder_path, f)
            try:
                with open(file_path, "r", encoding="utf-8") as fp:
                    data = json.load(fp)

                # db_id는 JSON 전체 기반으로 생성
                db_id = make_doc_hash_id_from_json(data)
                data["db_id"] = db_id  # payload에도 저장

                # 통일된 업서트 함수 사용 (vector_db_helper)
                create_doc_upsert(client, col_name, data, dense_model=mgr.dense_model)
                success += 1

            except Exception as e:
                fail += 1
                logger.error(f"[InitUpsertAll] Upsert failed for {f}: {e}")

        logger.info(
            f"[InitUpsertAll] {col_name}: {success} succeeded, {fail} failed "
            f"({folder_path})"
        )

    logger.info("[InitUpsertAll] Completed all collections.")