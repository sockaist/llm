from llm_backend.server.vector_server.core.resource_pool import acquire_manager

def add_test_metadata():
    col = "benchmark.real.phase7"
    with acquire_manager() as mgr:
        print(f"Adding test metadata to {col}...")
        
        # Get first 5 points
        res, _ = mgr.client.scroll(collection_name=col, limit=5, with_payload=True)
        for p in res:
            new_payload = p.payload.copy()
            new_payload["department"] = "CS"
            new_payload["category"] = "graduation"
            new_payload["year"] = "2024"
            
            mgr.client.set_payload(
                collection_name=col,
                payload=new_payload,
                points=[p.id]
            )
            print(f"Updated point {p.id} with CS/graduation/2024")

if __name__ == "__main__":
    add_test_metadata()
