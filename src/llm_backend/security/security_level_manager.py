
from typing import Dict, Any
from qdrant_client import QdrantClient, models
from llm_backend.security.access_control import AccessControl
from llm_backend.utils.logger import logger

class SecurityLevelManager:
    """
    Manages security level updates for documents (Phase 14).
    """

    def __init__(self, client: QdrantClient):
        self.client = client

    def update_security_level(self, 
                              collection_name: str, 
                              doc_id: str, 
                              new_level: int, 
                              user_context: Dict[str, Any]) -> bool:
        """
        Update the 'access_level' of a document if authorized.
        """
        # Validate level
        if not (1 <= new_level <= 4):
            logger.warning(f"[Security] Invalid level {new_level}")
            return False

        # 1. Retrieve current metadata
        # Note: We need payload to check tenant_id
        results = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(
                must=[models.FieldCondition(key="db_id", match=models.MatchValue(value=doc_id))]
            ),
            limit=1,
            with_payload=True
        )
        
        points = results[0]
        if not points:
            logger.warning(f"[Security] Document {doc_id} not found")
            return False
            
        point = points[0]
        payload = point.payload
        
        # 2. Check Permissions
        if not AccessControl.can_change_security_level(user_context, payload):
            logger.warning(f"[Security] Denied: User {user_context.get('user_id')} cannot change level for {doc_id}")
            raise PermissionError("Unauthorized to change security level")

        # 3. Apply Update
        try:
            self.client.set_payload(
                collection_name=collection_name,
                payload={"access_level": new_level},
                points=[point.id]
            )
            logger.info(f"[Security] Updated level for {doc_id} to {new_level} by {user_context.get('user_id')}")
            return True
        except Exception as e:
            logger.error(f"[Security] Failed to update payload: {e}")
            return False
