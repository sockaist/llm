
import sys
import os
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from llm_backend.vectorstore.vector_db_manager import VectorDBManager
from llm_backend.vectorstore.sparse_engine import init_sparse_engine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    if len(sys.argv) < 2:
        data_path = "./data"
    else:
        data_path = sys.argv[1]
        
    print(f"Training BM25 from: {data_path}")
    
    if not os.path.exists(data_path):
        print(f"Error: Path {data_path} does not exist!")
        sys.exit(1)
        
    # Initialize engine directly
    count = init_sparse_engine(data_path=data_path, force_retrain=True)
    print("BM25 Training Complete.")

if __name__ == "__main__":
    main()
