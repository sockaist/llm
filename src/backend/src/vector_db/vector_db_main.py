from qdrant_client import QdrantClient
from qdrant_client.models import Distance, NamedVector
from sentence_transformers import SentenceTransformer
from reranker_module import combine_scores, print_rerank_summary
from embedding import content_embedder
from vector_db_helper import (
    create_doc_upsert, read_doc, update_doc, delete_doc,
    search_doc, initialize_col, upsert_folder
)
from init import init_recreate_collections, auto_recreate_collections
from config import QDRANT_API_KEY, QDRANT_URL
from sparse_helper import bm25_fit, bm25_encode
from splade_module import splade_encode
import json
import os
import numpy as np
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pecab._tokenizer")


# 설정
INIT = True
folder_path = "../../../../data/"
base_path = "../../../../data/"
col_name = "notion.marketing"
query = "몰입캠프가 언제 진행하는지 알려줘."

# Qdrant 연결
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# Dense model 로드
dense_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
print("Dense model loaded successfully")


# 초기화 및 업서트
if INIT:
    print("Recreating collections in Qdrant...")
    #init_recreate_collections(client)
    auto_recreate_collections(client)
    
    print("Fitting BM25 model from corpus...")
    all_texts = []
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".json"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                        text = data.get("content") or data.get("contents")
                        if text:
                            all_texts.append(text)
                    except json.JSONDecodeError:
                        continue

    if all_texts:
        bm25_fit(all_texts)
        print(f"BM25 fitted on {len(all_texts)} documents.")
    else:
        print("No texts found for BM25 fitting.")

    print("Uploading documents to Qdrant...")
    upsert_folder(client, folder_path + "notion/notice", "notion.notice", dense_model=dense_model)
    upsert_folder(client, folder_path + "notion/marketing", "notion.marketing", dense_model=dense_model)
    print("All collections initialized successfully.")


# 검색 실행
print(f"\nSearching for '{query}' in collection '{col_name}'...")

# Query vector 생성
dense_query_vec = dense_model.encode(query)
bm25_query_vec = bm25_encode(query)
splade_query_vec = splade_encode(query)

# Dense 검색
dense_results = client.search(
    collection_name=col_name,
    query_vector=NamedVector(name="dense", vector=dense_query_vec),
    limit=20
)

# Sparse 검색
sparse_results = client.search(
    collection_name=col_name,
    query_vector=NamedVector(name="sparse", vector=bm25_query_vec),
    limit=20
)

# SPLADE 검색
splade_results = client.search(
    collection_name=col_name,
    query_vector=NamedVector(name="splade", vector=splade_query_vec),
    limit=20
)

# 점수 병합 (reranker)
reranked = combine_scores(
    dense_results,
    sparse_results,
    splade_results,
    w_dense=0.6,
    w_sparse=0.25,
    w_splade=0.15
)

# 결과 출력
print_rerank_summary(reranked, client, col_name, top_n=10)
print("Reranking complete.")