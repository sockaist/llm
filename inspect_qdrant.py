from qdrant_client import QdrantClient
import inspect

print("Instantiating Client...")
client = QdrantClient(location="memory") # Test in memory
print(f"Client Type: {type(client)}")
print(f"Has 'search'? {hasattr(client, 'search')}")
print(f"Has 'query_points'? {hasattr(client, 'query_points')}")
print(f"Has 'scroll'? {hasattr(client, 'scroll')}")
print("-" * 20)
print("Methods:")
for name, method in inspect.getmembers(client):
    if not name.startswith("_"):
        print(name)
