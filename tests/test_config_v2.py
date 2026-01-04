
import os
import sys

# Adjust path to find vectordb package
sys.path.append(os.getcwd())

from vectordb.core.config import Config

def test_defaults():
    print("--- Test 1: Defaults (Dev) ---")
    # Force default
    if "VECTORDB_ENV" in os.environ:
        del os.environ["VECTORDB_ENV"]
        
    cfg = Config.load(env="development")
    print(f"Env: {cfg.app.env}")
    print(f"Security Tier: {cfg.security.tier}")
    
    # Defaults has tier: 1, but development.yaml override has tier: 0
    assert cfg.security.tier == 0, f"Expected Tier 0 (Dev), got {cfg.security.tier}"
    print("[PASS] Defaults + Dev Override passed")

def test_production():
    print("\n--- Test 2: Production Override ---")
    cfg = Config.load(env="production")
    print(f"Env: {cfg.app.env}")
    print(f"Workers: {cfg.server.workers}")
    
    # Production.yaml has workers: 8
    assert cfg.server.workers == 8, f"Expected 8 workers, got {cfg.server.workers}"
    print("[PASS] Production Override passed")

def test_env_var():
    print("\n--- Test 3: Env Var Override ---")
    os.environ["VECTORDB_PORT"] = "9999"
    
    cfg = Config.load(env="development")
    print(f"Port: {cfg.vectordb.port}")
    
    assert cfg.vectordb.port == 9999, f"Expected 9999, got {cfg.vectordb.port}"
    print("[PASS] Env Var Override passed")

if __name__ == "__main__":
    test_defaults()
    test_production()
    test_env_var()
