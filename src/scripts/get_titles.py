from llm_backend.server.vector_server.core.resource_pool import acquire_manager

def get_actual_titles(col_name='benchmark.real.phase5'):
    with acquire_manager() as mgr:
        res, _ = mgr.client.scroll(collection_name=col_name, limit=100, with_payload=True)
        titles = set()
        for p in res:
            t = p.payload.get('title')
            if t:
                titles.add(t)
        
        for t in sorted(list(titles)):
            print(f"- {t}")

if __name__ == "__main__":
    get_actual_titles()
