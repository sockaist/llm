"""
Semantic Cache Implementation (Qdrant-based).
"""

import time
import json
from typing import List, Dict, Any, Optional
from qdrant_client import models
import hashlib
from llm_backend.utils.logger import logger

CACHE_COLLECTION = "semantic_cache"


class SemanticCache:
    """
    Qdrant-based Semantic Cache.
    Stores query vectors and results.
    """

    @staticmethod
    def init_cache(client, vector_size: int = 1024):
        """Ensure cache collection exists."""
        try:
            if not client.collection_exists(CACHE_COLLECTION):
                logger.info(f"[SemanticCache] Creating '{CACHE_COLLECTION}'...")
                client.create_collection(
                    collection_name=CACHE_COLLECTION,
                    vectors_config=models.VectorParams(
                        size=vector_size, distance=models.Distance.COSINE
                    ),
                )
        except Exception as e:
            logger.warning(f"[SemanticCache] Init failed: {e}")

    @staticmethod
    def get(
        client,
        query_vector: List[float],
        query_text: str,
        threshold: float = 0.95,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Search for semantically similar previous queries.
        Must match user_context to prevent information leak.
        """
        if client is None or query_vector is None:
            return None

        try:
            # Build Filter
            must_filters = []

            # 1. Multi-Tenancy Filter
            if user_context:
                user_info = (
                    user_context.get("user", {})
                    if "user" in user_context
                    else user_context
                )
                user_id = user_info.get("id") or user_info.get("user_id") or "anonymous"
                role = user_info.get("role") or user_info.get("user_role") or "guest"

                # We hash the user context to create a secure key
                # Or we can just store user_id in payload.
                # Let's use user_id field in payload.
                if role != "admin":  # Admins might see all? No, cache should be strict.
                    must_filters.append(
                        models.FieldCondition(
                            key="user_id", match=models.MatchValue(value=user_id)
                        )
                    )

            # Search
            search_result = client.search(
                collection_name=CACHE_COLLECTION,
                query_vector=query_vector,
                limit=1,
                score_threshold=threshold,
                query_filter=models.Filter(must=must_filters) if must_filters else None,
            )

            if search_result:
                hit = search_result[0]
                logger.debug(
                    f"[SemanticCache] Hit! Score: {hit.score:.4f} for '{query_text}'"
                )
                payload = hit.payload
                # Check strict text match if needed, but semantic is fuzzy.
                # Let's return cached results.
                if "results_json" in payload:
                    return json.loads(payload["results_json"])

        except Exception as e:
            logger.debug(f"[SemanticCache] Get failed: {e}")

        return None

    @staticmethod
    def set(
        client,
        query_vector: List[float],
        results: List[Dict[str, Any]],
        query_text: str,
        user_context: Optional[Dict[str, Any]] = None,
        ttl: int = 3600,
    ):
        """
        Store results in semantic cache.
        """
        if client is None or query_vector is None or not results:
            return

        try:
            # Prepare payload
            user_id = "anonymous"
            if user_context:
                user_id = user_context.get("user_id", "anonymous")

            # Create a unique point ID for the cache entry (must be UUID)
            from llm_backend.utils.id_helper import generate_point_id

            # Hash seed for determinism
            hash_seed = hashlib.sha256((query_text + user_id).encode()).hexdigest()
            point_id = generate_point_id(hash_seed)

            payload = {
                "query_text": query_text,
                "user_id": user_id,
                "created_at": time.time(),
                "results_json": json.dumps(results, default=str),
            }

            client.upsert(
                collection_name=CACHE_COLLECTION,
                points=[
                    models.PointStruct(
                        id=point_id, vector=query_vector, payload=payload
                    )
                ],
            )
        except Exception as e:
            logger.warning(f"[SemanticCache] Set failed: {e}")
