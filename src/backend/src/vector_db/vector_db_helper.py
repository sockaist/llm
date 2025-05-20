from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, PointIdsList, FilterSelector
from qdrant_client.models import SearchRequest, SearchParams, NamedVector
from qdrant_client.http.models import ScoredPoint
import numpy as np 
from embedding import content_embedder
from vector_db_main import FORMATS
import os


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
    raw_text = data["content"]
    
    chunks = content_embedder(raw_text) 

    id = client.count(
        collection_name = col_name,
        exact=True
    ).count + 1

    points = []

    for t,v in chunks:
        payload = {}
        payload["text"] = t

        for name in FORMATS[col_name]:
            payload[name] = data[name]

        new_p = PointStruct(
            id= id,
            vector= {"vector": v},
            payload= payload
        )
        print(v,payload)

        id += 1 
        points.append(new_p)
    
    client.upsert(collection_name=col_name, points=points)


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
    # 기존 벡터 정보 가져오기 (기존 텍스트 기반 재임베딩)
    raw_text = updated_data["content"]
    chunks = content_embedder(raw_text)

    points = []
    new_id = id
    for t, v in chunks:
        payload = {"text": t}
        for name in FORMATS[col_name]:
            payload[name] = updated_data.get(name, "")

        points.append(PointStruct(
            id=new_id,
            vector={"vector": v},
            payload=payload
        ))
        new_id += 1

    client.upsert(collection_name=col_name, points=points)

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

    cnt=0
    for filename in os.listdir(folder_path):
        if(n != 0 and cnt > n): break
        cnt += 1
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                print(f"uploading: {filename} → '{col_name}'")
                create_doc_upsert(client, col_name, data)

            except Exception as e:
                print(f"Error ({filename}): {e}")