
import os
import sys
import redis
import sqlite3
import shutil
from qdrant_client import QdrantClient

# Add src to path for imports
current_dir = os.getcwd()
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

from vectordb.core.config import Config
from vectordb.core.logger import setup_logger

logger = setup_logger("reset_system")

def reset_all():
    cfg = Config.load()
    logger.info("Starting VortexDB System Reset...")

    # 1. Flush Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.flushall()
        logger.info(f"[1/3] Redis flushed ({redis_url}).")
    except Exception as e:
        logger.warning(f"Redis flush failed: {e}")

    # 2. Delete Qdrant Collections
    try:
        qdrant_url = f"http://{cfg.vectordb.host}:{cfg.vectordb.port}"
        client = QdrantClient(url=qdrant_url)
        collections = ["demo_collection", "semantic_cache"]
        for col in collections:
            try:
                client.delete_collection(col)
                logger.info(f"[2/3] Deleted Qdrant collection: {col}")
            except Exception:
                logger.info(f"[2/3] Collection '{col}' did not exist.")
    except Exception as e:
        logger.warning(f"Qdrant reset failed: {e}")

    # 3. Wipe Security DB
    try:
        db_path = "security.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info("[3/3] Security database deleted.")
        else:
            logger.info("[3/3] Security database not found, skipping.")
    except Exception as e:
        logger.warning(f"Security DB wipe failed: {e}")

    logger.info("VortexDB System Reset Complete.")

if __name__ == "__main__":
    reset_all()
