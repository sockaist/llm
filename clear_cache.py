from llm_backend.server.vector_server.core.cache_manager import bump_collection_epoch
import os
import sys

# Add src to path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.append(os.path.join(project_root, 'src'))

if __name__ == "__main__":
    col = "csweb"
    new_v = bump_collection_epoch(col)
    print(f"Collection '{col}' epoch bumped to {new_v}. Cache invalidated.")
