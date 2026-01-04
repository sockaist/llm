from qdrant_client import QdrantClient
import inspect

client = QdrantClient(location="memory")
print(f"Has client.http? {hasattr(client, 'http')}")
if hasattr(client, 'http'):
    print(f"Has points_api? {hasattr(client.http, 'points_api')}")
    if hasattr(client.http, 'points_api'):
        print("Points API Methods:")
        for name, _ in inspect.getmembers(client.http.points_api):
            if "search" in name:
                print(name)
