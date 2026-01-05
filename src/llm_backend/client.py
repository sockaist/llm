import os
import httpx
from typing import List, Dict, Optional, Union

class VectorDBClient:
    """
    VectorDB Client for interacting with the Vector Server via REST API.
    Async implementation.
    """
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("VECTOR_API_KEY")
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["x-api-key"] = self.api_key

    async def health(self) -> Dict:
        """Check server health."""
        async with httpx.AsyncClient(base_url=self.base_url) as client:
            resp = await client.get("/health")
            resp.raise_for_status()
            return resp.json()

    async def health_check(self) -> Dict:
        """Alias for health()."""
        return await self.health()
    
    async def get_job_status(self, job_id: str) -> Dict:
        """Check status of an async job."""
        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=10.0) as client:
            resp = await client.get(f"/batch/jobs/status/{job_id}")
            resp.raise_for_status()
            return resp.json()

    async def upsert(
        self, 
        collection_name: str, 
        documents: List[Dict], 
        wait: bool = True
    ) -> Dict:
        """
        Upsert documents into a collection.
        """
        # Server expects "collection" (BatchDocumentsRequest)
        payload = {
            "collection": collection_name,
            "documents": documents
        }
        # wait param not currently used in API payload but kept for SDK consistency
        
        # Endpoint: /batch/ingest (Async Job Queue)
        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=30.0) as client:
            resp = await client.post("/batch/ingest", json=payload)
            resp.raise_for_status()
            return resp.json() # Returns { "status": "queued", "job_id": "...", ... }

    # Alias for script compatibility
    async def upsert_documents(self, documents: List[Dict], tenant_id: str = "default", **kwargs) -> Dict:
        return await self.upsert(collection_name=tenant_id, documents=documents)

    async def search(
        self, 
        collection_name: str, 
        query: str, 
        top_k: int = 10,
        filters: Optional[Dict] = None,
        user_context: Optional[Dict] = None,
        **kwargs # Catch-all for compatibility
    ) -> List[Dict]:
        """
        Search for documents.
        """
        # Server expects QueryRequest: query_text, collections (list), top_k
        payload = {
            "collections": [collection_name],
            "query_text": query,
            "top_k": top_k,
            "filters": filters
        }
        
        # Endpoint: /query/hybrid
        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=120.0) as client:
            resp = await client.post("/query/hybrid", json=payload)
            resp.raise_for_status()
            result = resp.json()
            # Return "results" list directly for compatibility
            return result.get("results", [])
    
    async def delete(self, collection_name: str, doc_ids: List[str]) -> Dict:
        """Delete documents by ID."""
        payload = {
            "collection_name": collection_name,
            "document_ids": doc_ids
        }
        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers) as client:
            resp = await client.post("/api/v1/ingest/delete", json=payload)
            resp.raise_for_status()
            return resp.json()
