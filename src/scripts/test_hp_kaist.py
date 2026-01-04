import sys
import os

# Priority for local 'src'
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.vectorstore.hp_tuner import get_optimized_hp


def test_kaist_trigger():
    print("=== Testing AutoRAG-HP: KAIST CS/Internal Strategy ===")

    # Test Case 1: Administrative (Title Centric)
    query_admin = "전산학부 졸업 이수 요건 알려줘"
    hp_admin = get_optimized_hp(query_admin, {})
    print(f"\nQuery (Admin): '{query_admin}'")
    print(f"- Title Weight: {hp_admin['title_weight']} (Expected high)")
    print(f"- Search K: {hp_admin['search_k']} (Expected low/precise)")

    # Test Case 2: Research (Recall Expanded)
    query_tech = "최신 생성형 AI 연구 및 논문 동향"
    hp_tech = get_optimized_hp(query_tech, {})
    print(f"\nQuery (Research): '{query_tech}'")
    print(f"- SPLADE Weight: {hp_tech['splade_weight']} (Expected boost)")
    print(f"- Search K: {hp_tech['search_k']} (Expected high/broad)")

    # Assertions
    success = True
    if hp_admin["title_weight"] < 0.8:
        print("\n[FAIL] Admin Strategy failed (Title Weight too low)")
        success = False
    if hp_tech["search_k"] < 100:
        print("\n[FAIL] Research Strategy failed (Search K too low)")
        success = False

    if success:
        print(
            "\n[OK] Success: KAIST Domain Strategies (Admin/Research) triggered correctly!"
        )


if __name__ == "__main__":
    test_kaist_trigger()
