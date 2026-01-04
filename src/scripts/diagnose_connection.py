import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager


def check():
    print("Checking Qdrant...")
    with acquire_manager() as mgr:
        cols = mgr.client.get_collections().collections
        print("Collections:", [c.name for c in cols])

        count = mgr.client.count(collection_name="csweb.research").count
        print(f"csweb.research count: {count}")

        # Scroll sample
        res, _ = mgr.client.scroll("csweb.research", limit=1, with_payload=True)
        if res:
            print(f"Sample Payload Keys: {res[0].payload.keys()}")
            print(f"Sample Text: {res[0].payload.get('text')}")
        else:
            print("Scroll returned empty.")


if __name__ == "__main__":
    check()
