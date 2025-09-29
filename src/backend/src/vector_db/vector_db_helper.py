from qdrant_client import QdrantClient, models
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, PointIdsList, FilterSelector
from qdrant_client.models import SearchRequest, SearchParams, NamedVector
from qdrant_client.http.models import ScoredPoint
import numpy as np 
import json
import os
from embedding import content_embedder
from config import FORMATS


from typing import List, Dict, Any


def create_doc_upsert(client, col_name, data):
    """
    This function embed data and insert it at collection named "col_name".

    Args:
        client: qdrant client for cur DB
        col_name: collection name
        data: json data to upsert
    
    Returns:
        none

    """
    try:
        # 데이터 검증
        if not data:
            print("Warning: Empty data provided to create_doc_upsert")
            return
        
        if "content" in data:
            raw_text = data["content"]
        elif "contents" in data:
            raw_text = data["contents"]
        else:
            raw_text = ""
        
        id = data["id"]
        exist = client.count(
            collection_name=col_name,
            count_filter=models.Filter(
                must=[models.FieldCondition(
                    key="id",  # payload에 저장한 키 이름
                    match=models.MatchValue(value=id),
                )]
            ),
            exact=False,  # 대략치면 더 빠름, 정확히 필요하면 True
        ).count > 0
        
        if exist:
            print(f"Info: Document with id {id} already exists in {col_name}, skipping upsert.")
            return

        
        if not raw_text or not raw_text.strip():
            print(f"Warning: Empty content in data for collection {col_name}")
            print(f"Data keys: {list(data.keys()) if data else 'None'}")
            return
        
        print(f"Processing text of length: {len(raw_text)}")
        chunks = content_embedder(raw_text) 

        if not chunks:
            print(f"Warning: No chunks generated for data in collection {col_name}")
            return

        id = client.count(
            collection_name = col_name,
            exact=True
        ).count + 1

        points = []

        for t,v in chunks:
            payload = {}
            payload["text"] = t

            # FORMATS에 정의된 필드들만 추가
            if col_name in FORMATS:
                for name in FORMATS[col_name]:
                    payload[name] = data.get(name, "")
            else:
                print(f"Warning: Collection {col_name} not found in FORMATS")

            new_p = PointStruct(
                id= id,
                vector= {"vector": v},
                payload= payload
            )
            print(f"Created point {id} with vector shape: {v.shape if hasattr(v, 'shape') else len(v)}")

            id += 1 
            points.append(new_p)
        
        if points:
            client.upsert(collection_name=col_name, points=points)
            print(f"Successfully upserted {len(points)} points to {col_name}")
        else:
            print(f"No points to upsert for collection {col_name}")
            
    except Exception as e:
        print(f"Error in create_doc_upsert for collection {col_name}: {e}")
        print(f"Data: {data}")
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
    """
    This function finds top-k docs by query in collection col_name, with defined DISTANCE

    Args: 
        client: Qdrant client for cur DB
        query: text query, will be embeded
        col_name: collection name to be searched
        k: take top-k results
    
    Returns:
        searched_points: top-k results in list type
    """
    from embedding import model  # content_embedder의 모델 (sentence-transformers 등)
    query_vector = model.encode(query)
    print(query_vector.shape)

    results = client.search(
        collection_name=col_name,
        query_vector=NamedVector(
            name="vector",
            vector=query_vector
        ),
        limit=k,
    )

    return results  # List[ScoredPoint]


def upsert_folder(client, folder_path, col_name, n=0):
    """
    This function upserts all data in folder_path in collection col_name

    Args:
        client:  Qdrant client for cur DB
        folder_path: folder path
        col_name : name of collection to add
        n: number of data to add, set 0 to add all data
    
    Return: 
        none    
    """
    try:
        if not os.path.exists(folder_path):
            print(f"Error: Folder path {folder_path} does not exist")
            return
            
        json_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
        if not json_files:
            print(f"Warning: No JSON files found in {folder_path}")
            return
            
        print(f"Found {len(json_files)} JSON files in {folder_path}")

        cnt = 0
        successful_uploads = 0
        failed_uploads = 0
        
        for filename in json_files:
            if n != 0 and cnt >= n:
                break
            cnt += 1
            
            file_path = os.path.join(folder_path, filename)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"Uploading {cnt}/{len(json_files) if n == 0 else min(n, len(json_files))}: {filename} → '{col_name}'")
                client.create_payload_index(
                    collection_name=col_name,
                    field_name="id",                   # payload의 키 이름
                    field_schema=models.PayloadSchemaType.INTEGER,  # 또는 "integer"
                    wait=True,                         # 인덱스 빌드 완료까지 대기
                )
                create_doc_upsert(client, col_name, data)
                successful_uploads += 1

            except json.JSONDecodeError as e:
                print(f"JSON decode error in {filename}: {e}")
                failed_uploads += 1
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                failed_uploads += 1
                
        print(f"Upload summary for {col_name}: {successful_uploads} successful, {failed_uploads} failed")
        
    except Exception as e:
        print(f"Error in upsert_folder for {folder_path}: {e}")
        raise