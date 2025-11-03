from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, PointIdsList, FilterSelector
from qdrant_client.models import SearchRequest, SearchParams, NamedVector
from qdrant_client.http.models import ScoredPoint
import numpy as np 
import json
import os
from embedding import content_embedder
from config import FORMATS
from splade_module import splade_encode  # SPLADE 모델 함수 (별도 모듈로 정의)
from sparse_helper import bm25_encode    # BM25 희소 인코더 함수
from embedding import model as dense_model
from qdrant_client.models import SparseVector

from typing import List, Dict, Any



def create_doc_upsert(client, col_name, data, dense_model=None):
    """
    Create and upsert a document into the Qdrant collection with
    Dense (SentenceTransformer), Sparse (BM25), and SPLADE vectors.
    """
    try:
        if not data:
            print(f"Empty data skipped for collection {col_name}")
            return

        raw_text = data.get("content") or data.get("contents") or ""
        if not raw_text.strip():
            print(f"Empty content in data (ID={data.get('id')}) for {col_name}")
            return

        # 문서 ID 확인
        doc_id = data.get("id", None)
        if doc_id is None:
            print(f"Missing 'id' in document for {col_name}")
            return

        # 중복 여부 확인
        exist = client.count(
            collection_name=col_name,
            count_filter=models.Filter(
                must=[models.FieldCondition(
                    key="id",
                    match=models.MatchValue(value=doc_id),
                )]
            ),
            exact=False,
        ).count > 0
        if exist:
            print(f"Document ID={doc_id} already exists in {col_name}, skipping.")
            return

        # Dense, Sparse, Splade 벡터 생성
        if dense_model is None:
            raise ValueError("Dense model is not loaded. Please pass dense_model parameter.")

        dense_vec = dense_model.encode(raw_text)
        if isinstance(dense_vec, np.ndarray):
            dense_vec = dense_vec.tolist()
        elif isinstance(dense_vec, list):
            dense_vec = [float(x) for x in dense_vec]
        else:
            raise TypeError(f"Unexpected dense_vec type: {type(dense_vec)}")

        # Sparse/BM25 및 SPLADE 벡터를 SparseVector로 변환
        bm25_dict = bm25_encode(raw_text)
        splade_dict = splade_encode(raw_text)

        sparse_vec = SparseVector(
            indices=[int(k) for k in bm25_dict.keys()],
            values=[float(v) for v in bm25_dict.values()]
        )
        splade_vec = SparseVector(
            indices=[int(k) for k in splade_dict.keys()],
            values=[float(v) for v in splade_dict.values()]
        )

        # 청킹
        chunks = content_embedder(raw_text)
        if not chunks:
            print(f"No chunks generated for ID={doc_id}")
            return

        # Qdrant 포인트 생성
        points = []
        base_id = client.count(collection_name=col_name, exact=True).count + 1

        for i, (chunk_text, _) in enumerate(chunks):
            payload = {"text": chunk_text, "parent_id": doc_id}
            if col_name in FORMATS:
                for key in FORMATS[col_name]:
                    payload[key] = data.get(key, "")

            # 핵심: SparseVector 타입으로 Qdrant에 전달
            point = PointStruct(
                id=base_id + i,
                vector={
                    "dense": dense_vec,
                    "sparse": sparse_vec,
                    "splade": splade_vec
                },
                payload=payload
            )
            points.append(point)

        # 업서트
        if points:
            client.upsert(collection_name=col_name, points=points)
            print(f"Upserted ID={doc_id} ({len(points)} chunks) → {col_name}")
        else:
            print(f"No points upserted for ID={doc_id}")

    except Exception as e:
        print(f"Error in create_doc_upsert for collection {col_name}: {e}")
        print(f"Document ID: {data.get('id')}")
        raise

def read_doc(client, col_name, id):
    """
    This function read document with id of collection named col_name

    Args:
        client: Qdrant client for cur DB
        col_name: collection name
        id: requested data id

    Returns:
        data: PointStruct() type data from Qdrant DB

    """
    response = client.retrieve(
        collection_name=col_name,
        ids=[id],
        with_payload=True,
        with_vectors=True
    )
    return response[0] if response else None

def update_doc(client, col_name, id, updated_data):
    """
    This function read document with id of collection named col_name

    Args:
        client: Qdrant client for cur DB
        col_name: collection name
        id: requested data id
        updated_data: json data to be updated

    Returns:
        none

    """
    try:
        # 데이터 검증
        if not updated_data:
            print(f"Warning: Empty updated_data provided for id {id}")
            return
            
        raw_text = updated_data.get("content", "")
        
        if not raw_text or not raw_text.strip():
            print(f"Warning: Empty content in updated_data for id {id}")
            return
            
        chunks = content_embedder(raw_text)
        
        if not chunks:
            print(f"Warning: No chunks generated for updated data id {id}")
            return

        points = []
        new_id = id
        for t, v in chunks:
            payload = {"text": t}
            
            if col_name in FORMATS:
                for name in FORMATS[col_name]:
                    payload[name] = updated_data.get(name, "")
            else:
                print(f"Warning: Collection {col_name} not found in FORMATS")

            points.append(PointStruct(
                id=new_id,
                vector={"vector": v},
                payload=payload
            ))
            new_id += 1

        if points:
            client.upsert(collection_name=col_name, points=points)
            print(f"Successfully updated {len(points)} points for id {id}")
        else:
            print(f"No points to update for id {id}")
            
    except Exception as e:
        print(f"Error in update_doc for id {id}: {e}")
        raise

def delete_doc(client, col_name,id):
    """
    This function read document with id of collection named col_name

    Args:
        client: Qdrant client for cur DB
        col_name: collection name
        id: requested data id

    Returns:
        none

    """
    client.delete(
        collection_name=col_name,
        points_selector=PointIdsList(points=[id])
    )


def initialize_col(client, col_name):
     """
    This function deletes all points in collection col_name

    Args:
        client: Qdrant client for cur DB
        col_name: collection name

    Returns:
        none

    """
     client.delete(
        collection_name=col_name,
        points_selector=FilterSelector(
            filter=Filter(must=[]) 
        )
    )


def search_doc(client, query, col_name, k):
    from embedding import model as dense_model
    query_vector = dense_model.encode(query)

    results = client.search(
        collection_name=col_name,
        query_vector=NamedVector(
            name="dense",  # ← 수정됨 (기존: "vector")
            vector=query_vector
        ),
        limit=k,
    )
    return results


def upsert_folder(client, folder_path, col_name, n=0, dense_model=None):
    """
    Upsert all JSON documents in a folder into a Qdrant collection.
    """
    try:
        if not os.path.exists(folder_path):
            print(f"Folder path not found: {folder_path}")
            return

        json_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
        if not json_files:
            print(f"No JSON files found in {folder_path}")
            return

        print(f"Found {len(json_files)} JSON files in {folder_path}")

        success, fail = 0, 0
        for i, filename in enumerate(json_files):
            if n and i >= n:
                break
            file_path = os.path.join(folder_path, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                doc_id = data.get("id", "?")
                print(f"Uploading {i+1}/{len(json_files)}: {filename} [ID={doc_id}]")

                # id 인덱스 생성 (없으면)
                client.create_payload_index(
                    collection_name=col_name,
                    field_name="id",
                    field_schema=models.PayloadSchemaType.INTEGER,
                    wait=True,
                )

                create_doc_upsert(client, col_name, data, dense_model=dense_model)
                success += 1

            except json.JSONDecodeError as e:
                print(f"JSON decode error in {filename}: {e}")
                fail += 1
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                fail += 1

        print(f"Upload summary for {col_name}: {success} succeeded, {fail} failed")

    except Exception as e:
        print(f"Error in upsert_folder for {folder_path}: {e}")
        raise