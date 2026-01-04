
import os
from vectordb.core.config import Config

def check_config():
    print(f"CWD: {os.getcwd()}")
    print(f"Env QDRANT_API_KEY: {os.getenv('QDRANT_API_KEY')}")
    
    cfg = Config.load()
    print(f"Config vectordb.api_key: '{cfg.vectordb.api_key}'")
    
    if cfg.vectordb.api_key == os.getenv('QDRANT_API_KEY'):
        print("MATCH: Config matches Env.")
    else:
        print("MISMATCH: Config does not match Env!")

if __name__ == "__main__":
    check_config()
