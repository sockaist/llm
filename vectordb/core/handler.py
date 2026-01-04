from typing import Any, Dict, List, Optional, Union
import hashlib

class JSONHandler:
    """
    Universal JSON Handler for VectorDB v2.0
    - Flattens nested JSON for Qdrant payload compatibility.
    - Extracts meaningful text for vectorization.
    - Protects reserved fields.
    """
    
    RESERVED_FIELDS = {'_id', '_collection', '_vector', '_timestamp', '_hash'}
    
    def __init__(self, strategy: str = 'auto', schema: Optional[Dict[str, Any]] = None):
        """
        :param strategy: 'auto', 'concat_all', or 'custom'.
        :param schema: Optional schema definition for 'custom' strategy.
        """
        self.strategy = strategy
        self.schema = schema or {}

    def process(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a raw JSON document into a VectorDB payload.
        Steps:
        1. Sanitize (Remove reserved fields).
        2. Extract Text.
        3. Flatten Structure.
        4. Hash for change detection.
        """
        # Step 1: Copy and Sanitize
        data = doc.copy()
        for reserved in self.RESERVED_FIELDS:
            data.pop(reserved, None)
            
        # Step 2: Extract Text (from clean data)
        text = self._extract_text(data)
        
        # Step 3: Flatten
        flattened = self._flatten(data)
        
        # Step 4: Construct Payload
        # We store the original text in '_text' for embedding generation later.
        payload = {
            "_text": text,
            "_hash": self._hash_text(text),
            **flattened
        }
        
        return payload

    def _extract_text(self, doc: Dict[str, Any]) -> str:
        """Extract main text based on strategy."""
        if self.strategy == 'auto':
            # Priority: title -> name -> description -> content -> message -> text
            priority_fields = ['title', 'name', 'subject', 'description', 'content', 'message', 'text', 'body']
            for field in priority_fields:
                if field in doc and isinstance(doc[field], str) and doc[field].strip():
                    return doc[field]
            
            # Fallback: Top-level string values if no specific field found
            texts = []
            for k, v in doc.items():
                if isinstance(v, str) and len(v) < 1000: # Simple heuristic
                    texts.append(v)
            return " ".join(texts)

        elif self.strategy == 'concat_all':
            # Recursively gather all strings
            texts = []
            self._collect_all_texts(doc, texts, max_depth=5)
            return " ".join(texts)

        elif self.strategy == 'custom':
            # Use defined fields from schema
            fields = self.schema.get('text_fields', [])
            texts = []
            for f in fields:
                val = doc.get(f)
                if val:
                    texts.append(str(val))
            return " ".join(texts)
            
        return ""

    def _collect_all_texts(self, obj: Any, texts: List[str], max_depth: int, current_depth: int = 0):
        if current_depth > max_depth:
            return
            
        if isinstance(obj, dict):
            for v in obj.values():
                self._collect_all_texts(v, texts, max_depth, current_depth + 1)
        elif isinstance(obj, list):
            # Limit array processing to avoid explosion
            for item in obj[:10]:
                self._collect_all_texts(item, texts, max_depth, current_depth + 1)
        elif isinstance(obj, str) and obj.strip():
            texts.append(obj.strip())
        elif isinstance(obj, (int, float, bool)):
            texts.append(str(obj))

    def _flatten(self, obj: Dict[str, Any], prefix: str = "", result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Flatten nested dictionary.
        {'a': {'b': 1}} -> {'a_b': 1}
        Arrays: {'tags': ['x', 'y']} -> {'tags_0': 'x', 'tags_1': 'y'}
        """
        if result is None:
            result = {}
            
        for k, v in obj.items():
            key = f"{prefix}_{k}" if prefix else k
            
            if isinstance(v, dict):
                # Recurse
                self._flatten(v, key, result)
            elif isinstance(v, list):
                # Flatten list up to 10 items
                for i, item in enumerate(v[:10]):
                    if isinstance(item, dict):
                         self._flatten(item, f"{key}_{i}", result)
                    else:
                         result[f"{key}_{i}"] = item
            else:
                result[key] = v
                
        return result

    def _hash_text(self, text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]
