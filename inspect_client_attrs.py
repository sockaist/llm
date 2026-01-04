from qdrant_client import QdrantClient
import inspect

client = QdrantClient(url="http://localhost:6333", api_key="test_key")
print(f"Attrs: {list(client.__dict__.keys())}")
if hasattr(client, 'rest_uri'):
    print(f"rest_uri: {client.rest_uri}")
if hasattr(client, '_client'):
    print(f"_client attrs: {list(client._client.__dict__.keys())}")
