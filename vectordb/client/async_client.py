import httpx
import uuid
import asyncio
import logging
from typing import List, Dict, Any, Optional

from vectordb.core.config import Config, ConfigObject
from vectordb.core.handler import JSONHandler

class AsyncVectorDBClient:
    """
    Asynchronous Python Client for VectorDB (httpx).
    """
    
    def __init__(self, config: Optional[ConfigObject] = None, api_key: Optional[str] = None):
        self.config = config or Config.load()
        self.host = self.config.server.host
        if self.host == "0.0.0.0":
            self.host = "127.0.0.1"
        self.port = self.config.server.port
        self.base_url = f"http://{self.host}:{self.port}"
        self.api_key = api_key or self.config.vectordb.api_key
        
        self.handler = JSONHandler(strategy='auto')
        self.headers = {}
        if self.api_key:
             self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        self.logger = logging.getLogger("vectordb.async_client")

    async def search(self, text: str, top_k: int = 10, collection: Optional[str] = None, alpha: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute Hybrid Search Async.
        """
        request_id = str(uuid.uuid4())[:8]
        req_headers = {**self.headers, "X-Correlation-ID": request_id}
        
        payload = {
            "query_text": text,
            "top_k": top_k,
            "collections": [collection] if collection else None
        }
        if alpha is not None:
             payload["alpha"] = alpha
             
        self.logger.info(f"[{request_id}] AsyncSearch: {text}")
        
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.post("/query/hybrid", json=payload, headers=req_headers)
            resp.raise_for_status()
            return resp.json()

    async def list_collections(self) -> List[str]:
        """List all available collections."""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            resp = await client.get("/health/status", headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            return list(data.get("collections", {}).keys())

    async def upsert(self, collection: str, documents: List[Dict[str, Any]], batch_size: int = 100) -> Dict[str, Any]:
        """
        Upsert documents Async (with batching).
        """
        request_id = str(uuid.uuid4())[:8]
        req_headers = {**self.headers, "X-Correlation-ID": request_id}
        total_upserted = 0
        
        async with httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout) as client:
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i+batch_size]
                processed_batch = [self.handler.process(doc) for doc in batch]
                
                payload = {"collection": collection, "documents": processed_batch}
                
                self.logger.info(f"[{request_id}] AsyncUpsert batch {i//batch_size + 1}")
                resp = await client.post(
                    "/crud/upsert_batch",
                    json=payload,
                    headers=req_headers
                )
                resp.raise_for_status()
                total_upserted += len(batch)

        return {"status": "success", "count": total_upserted}
