#!/usr/bin/env python3
import sys
import os
import uuid
import json
from unittest.mock import MagicMock

def create_mock_module(name):
    m = MagicMock()
    m.__spec__ = MagicMock()
    m.__spec__.name = name
    return m

# 1. Mock External Libs that might be imported by other utils

sys.modules["qdrant_client"] = MagicMock()
sys.modules["qdrant_client.models"] = MagicMock()
sys.modules["qdrant_client.http"] = MagicMock()
sys.modules["qdrant_client.http.models"] = MagicMock()
sys.modules["dotenv"] = MagicMock()
sys.modules["psutil"] = MagicMock()


# 2. Mock Internal Heavy Dependencies BEFORE importing ingest_manager
# This prevents ingest_manager from triggering imports of sklearn/transformers
# But __init__ of vectorstore imports vector_db_manager -> logger -> psutil
# So we must mock psutil with spec
sys.modules["psutil"] = create_mock_module("psutil")

sys.modules["llm_backend.vectorstore.sparse_helper"] = MagicMock()

sys.modules["llm_backend.vectorstore.splade_module"] = MagicMock()
# Also mock vector_db_helper's dependencies if needed, but we might want to test vector_db_helper itself?
# vector_db_helper imports embedding, splade_module, sparse_helper.
sys.modules["llm_backend.vectorstore.embedding"] = MagicMock()

# Add src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from llm_backend.utils.id_helper import make_doc_hash_id_from_json, generate_point_id
from llm_backend.vectorstore import ingest_manager
from llm_backend.vectorstore import vector_db_helper

def test_id_helper():
    print("=== Testing id_helper.py ===")
    data = {"content": "Hello World", "id": "123"}
    db_id = make_doc_hash_id_from_json(data)
    
    point_id_1 = generate_point_id(db_id)
    point_id_2 = generate_point_id(db_id)
    
    print(f"db_id: {db_id}")
    print(f"Point ID 1: {point_id_1}")
    print(f"Point ID 2: {point_id_2}")
    
    if point_id_1 == point_id_2:
        print("PASS: IDs are deterministic")
    else:
        print("FAIL: IDs are NOT deterministic")
        sys.exit(1)
        
    # Different data
    data2 = {"content": "Hello World Modified", "id": "123"}
    db_id2 = make_doc_hash_id_from_json(data2)
    point_id_3 = generate_point_id(db_id2)
    print(f"Point ID 3 (diff data): {point_id_3}")
    
    if point_id_1 != point_id_3:
        print("PASS: Different data produces different ID")
    else:
        print("FAIL: Different data produced same ID")
        sys.exit(1)
    print()

def test_ingest_manager():
    print("=== Testing ingest_manager.upsert_document ===")
    
    # Mock Manager
    mock_manager = MagicMock()
    mock_manager.dense_model.encode.return_value = [0.1] * 768
    mock_manager.client.upsert = MagicMock()
    
    col = "test_collection"
    data = {"content": "Test Content", "id": "test_1"}
    
    # Run Upsert
    ingest_manager.upsert_document(mock_manager, col, data)
    
    # Capture arguments
    if not mock_manager.client.upsert.called:
         print("FAIL: client.upsert was not called")
         sys.exit(1)

    call_args = mock_manager.client.upsert.call_args
    _, kwargs = call_args
    points = kwargs['points']
    
    first_point_id = str(points[0].id)
    print(f"First Upsert Point ID: {first_point_id}")
    
    # Run Upsert Again
    ingest_manager.upsert_document(mock_manager, col, data)
    
    call_args_2 = mock_manager.client.upsert.call_args
    _, kwargs_2 = call_args_2
    points_2 = kwargs_2['points']
    
    second_point_id = str(points_2[0].id)
    print(f"Second Upsert Point ID: {second_point_id}")
    
    if first_point_id == second_point_id:
        print("PASS: ingest_manager produced consistent ID")
    else:
        print("FAIL: ingest_manager produced different IDs for same data")
        sys.exit(1)
    print()

def test_vector_db_helper():
    print("=== Testing vector_db_helper.create_doc_upsert ===")
    
    mock_client = MagicMock()
    mock_dense_model = MagicMock()
    mock_dense_model.encode.return_value = [0.1] * 768
    
    # Mock content_embedder manually since we mocked the module
    # vector_db_helper uses 'content_embedder' imported from embedding
    # But since we mocked 'llm_backend.vectorstore.embedding', the import inside vector_db_helper
    # is already a mock. We just need to configure it.
    
    vector_db_helper.content_embedder.return_value = [("Test Content Chunk", {})]
    
    col = "test_collection"
    data = {"content": "Test Content", "id": "test_1"}
    
    # Run 1
    vector_db_helper.create_doc_upsert(mock_client, col, data, dense_model=mock_dense_model)
    points_1 = mock_client.upsert.call_args[1]['points']
    pid_1 = str(points_1[0].id)
    
    # Run 2
    vector_db_helper.create_doc_upsert(mock_client, col, data, dense_model=mock_dense_model)
    points_2 = mock_client.upsert.call_args[1]['points']
    pid_2 = str(points_2[0].id)
    
    print(f"Helper Run 1 ID: {pid_1}")
    print(f"Helper Run 2 ID: {pid_2}")
    
    if pid_1 == pid_2:
        print("PASS: vector_db_helper produced consistent ID")
    else:
        print("FAIL: vector_db_helper produced different IDs")
        sys.exit(1)
    print()

if __name__ == "__main__":
    try:
        test_id_helper()
        test_ingest_manager()
        test_vector_db_helper()
        print("ALL TESTS PASSED")
    except Exception as e:
        print(f"TEST FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
