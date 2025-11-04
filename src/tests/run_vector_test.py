# -*- coding: utf-8 -*-
import os
from llm_backend.vectorstore.vector_db_manager import VectorDBManager
from llm_backend.utils.logger import logger
from llm_backend.utils.debug import trace


def main():
    logger.info("[TEST] VectorDBManager 통합 테스트 시작")

    # --- 1. 초기화 ---
    trace("Initializing Qdrant Client and Manager")
    mgr = VectorDBManager(default_collection="notion.marketing")
    client = mgr.client

    # 기존 컬렉션 정리
    logger.info("[STEP 1] 기존 컬렉션 삭제 및 재생성")
    try:
        client.delete_collection("notion.marketing")
    except Exception:
        logger.warning("컬렉션이 존재하지 않아 delete 스킵")

    # db_id 인덱스가 자동 포함된 새 컬렉션 생성
    mgr.create_collection("notion.marketing", vector_size=768)

    # --- 2. BM25 학습 ---
    logger.info("[STEP 2] BM25 모델 학습")
    try:
        mgr.fit_bm25_from_json_folder("./data")
    except Exception as e:
        logger.error(f"BM25 학습 실패: {e}")

    # --- 3. 문서 업로드 ---
    logger.info("[STEP 3] JSON 문서 업로드 시작")
    mgr.upsert_folder(
        "/Users/bagjimin/Desktop/1. Projects/sockaist/llm/data/notion/marketing",
        "notion.marketing"
    )

    # --- 4. 기본 검색 ---
    logger.info("[STEP 4] 기본 검색 실행 (Full Pipeline + Reranker 포함)")
    query = "인공지능 인턴 모집"
    results = mgr.query(
        query_text=query,
        top_k=5,
        collections=["notion.marketing"]
    )
    mgr.log_results(results, title=f"Query: {query}")

    # --- 5. Cross-Encoder 비활성화 후 검색 ---
    logger.info("[STEP 5] Cross-Encoder 비활성화 후 검색 실행")
    mgr.pipeline_config["use_reranker"] = False
    results_no_ce = mgr.query(
        query_text=query,
        top_k=5,
        collections=["notion.marketing"]
    )
    mgr.log_results(results_no_ce, title="Query (No Cross-Encoder)")

    # --- 6. 첫 번째 문서 payload 업데이트 ---
    logger.info("[STEP 6] 첫 번째 문서 payload 업데이트")

    # db_id 기준으로 업데이트
    first_doc = results[0] if results else None
    if first_doc:
        first_doc_id = first_doc.get("db_id") or first_doc.get("id") or first_doc.get("doc_id")
        if first_doc_id:
            mgr.update_payload(
                "notion.marketing",
                doc_id=first_doc_id,
                new_payload={"verified": True},
                merge=True
            )
        else:
            logger.warning("[STEP 6] 문서 ID를 찾지 못했습니다 (id=None)")
    else:
        logger.warning("[STEP 6] 업데이트할 문서가 없습니다.")

    # --- 7. 업데이트 후 재검색 ---
    logger.info("[STEP 7] 업데이트 반영 후 검색 재실행")
    mgr.pipeline_config["use_reranker"] = True  # 다시 활성화
    results_updated = mgr.query(
        query_text=query,
        top_k=5,
        collections=["notion.marketing"]
    )
    mgr.log_results(results_updated, title="Query After Update")

    # --- 8. 첫 번째 문서 삭제 ---
    logger.info("[STEP 8] 첫 번째 문서 삭제")

    # db_id 기반 삭제
    if results_updated:
        first_doc = results_updated[0]
        db_id = first_doc.get("db_id") or first_doc.get("id")
        if db_id:
            mgr.delete_document("notion.marketing", db_id)
        else:
            logger.warning("[STEP 8] 삭제할 문서의 db_id를 찾지 못했습니다.")

    # --- 9. 키워드 기반 필터 검색 ---
    logger.info("[STEP 9] 필터 검색 테스트 (verified=True)")
    filtered_docs = mgr.filter_search(
        col="notion.marketing",
        filters={"verified": True},
        limit=5
    )
    mgr.log_results(filtered_docs, title="FilterSearch: verified=True")

    # --- 완료 ---
    logger.info("[TEST COMPLETE] VectorDBManager CRUD + Filter + Query 테스트 완료")


if __name__ == "__main__":
    main()