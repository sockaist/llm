import sys
import os

# Priority for local 'src'
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.vectorstore.hp_tuner import get_optimized_hp


def test_maritime_trigger():
    print("=== Testing AutoRAG-HP: Maritime Strategy ===")
    query = "최근 항만 물동량 변화 및 선박 운항 현황 알려줘"
    cfg = {}

    hp = get_optimized_hp(query, cfg)

    print(f"Query: '{query}'")
    print(f"Dense Weight: {hp['dense_weight']}")
    print(f"Sparse Weight: {hp['sparse_weight']}")
    print(f"SPLADE Weight: {hp['splade_weight']}")
    print(f"Search K: {hp['search_k']}")

    # Assertions
    if hp["search_k"] == 100:
        print("\n[OK] Success: Maritime Strategy (Strategy C) triggered!")
    else:
        print("\n[FAIL] Failure: Maritime Strategy not triggered.")


if __name__ == "__main__":
    test_maritime_trigger()
