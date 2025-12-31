import sys
import os
import asyncio

sys.path.append(os.path.join(os.getcwd(), 'src'))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager

async def monitor_ingestion():
    print("Monitoring ingestion progress...")
    last_counts = {}
    stable_count = 0
    
    with acquire_manager() as mgr:
        while True:
            resp = mgr.client.get_collections()
            collections = [c.name for c in resp.collections]
            
            total_docs = 0
            current_counts = {}
            for col in collections:
                info = mgr.client.get_collection(col)
                cnt = info.points_count
                current_counts[col] = cnt
                total_docs += cnt
            
            print(f"Total Docs: {total_docs} | Counts: {current_counts}")
            
            if total_docs > 0:
                # Check stability
                if current_counts == last_counts:
                    stable_count += 1
                else:
                    stable_count = 0
                
                last_counts = current_counts
                
                # If stable for 3 checks (15s) and > 2000 docs (approx), we are good
                if stable_count >= 3 and total_docs > 2000:
                    print("Ingestion seems complete and stable.")
                    break
            
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(monitor_ingestion())
