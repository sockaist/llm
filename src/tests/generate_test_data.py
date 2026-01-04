"""
실제 사용 패턴을 반영한 테스트 데이터 생성
- 다양한 쿼리 타입 (짧은/긴, 키워드/의미적, 단일/복합)
- 실제 문서 샘플링
"""

import asyncio
import json
import random
import os
from typing import List
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

# Adjust import based on your actual path
from llm_backend.server.vector_server.core.resource_pool import acquire_manager


def extract_keywords(text: str, top_k: int = 5) -> List[str]:
    """
    간단한 키워드 추출 (TF-IDF 대신 길이/빈도 기반 단순화)
    실제로는 KeyBERT 등을 쓰면 더 좋음
    """
    if not text:
        return []

    # 간단한 불용어 처리
    stopwords = {
        "이",
        "가",
        "은",
        "는",
        "을",
        "를",
        "의",
        "에",
        "로",
        "test",
        "demo",
        "sample",
    }
    words = [w for w in text.split() if len(w) > 1 and w not in stopwords]

    # 빈도 계산
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1

    # 상위 K개
    sorted_words = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_k]]


def extract_sentences(text: str) -> List[str]:
    """문장 단위 분리"""
    if not text:
        return []
    # 단순 마침표/줄바꿈 기준
    sentences = [
        s.strip() for s in text.replace("\n", ".").split(".") if len(s.strip()) > 10
    ]
    return sentences


async def generate_test_queries_from_db(
    output_path: str = "src/tests/test_queries.json", num_queries: int = 300
):
    print(f"Generating {num_queries} test queries from DB...")

    queries = []

    with acquire_manager() as mgr:
        # Get all collections
        collections_resp = mgr.client.get_collections()
        collections = [c.name for c in collections_resp.collections]

        if not collections:
            print("No collections found via Qdrant!")
            return

        print(f"Found collections: {collections}")

        all_docs = []
        # Sample documents from each collection
        for col in collections:
            try:
                # Scroll more docs for better diversity
                points, _ = mgr.client.scroll(
                    collection_name=col,
                    limit=50,  # Limit per collection to ensure mix
                    with_payload=True,
                    with_vectors=False,
                )
                count = 0
                for p in points:
                    payload = p.payload or {}
                    # Try various keys for text content
                    text_content = (
                        payload.get("content")
                        or payload.get("contents")
                        or payload.get("text")
                        or payload.get("description")
                        or payload.get("summary")
                        or payload.get("title")  # Last resort
                    )

                    if text_content and len(str(text_content)) > 10:
                        doc_id = payload.get("db_id") or p.id
                        all_docs.append(
                            {"id": doc_id, "text": str(text_content), "collection": col}
                        )
                        count += 1
                if count > 0:
                    print(f"  - {col}: {count} docs")
            except Exception:
                # print(f"Error scrolling collection {col}: {e}")
                pass

    if not all_docs:
        print("No documents found with 'text' payload.")
        # Fallback to dummy data if DB is empty for testing flow
        return

    print(f"Sampled {len(all_docs)} documents.")

    # Generate queries
    print("Generating queries with increased difficulty...")
    for _ in range(num_queries):
        doc = random.choice(all_docs)
        text = doc["text"]

        # Randomly choose query type including new 'multi_hop'
        q_type = random.choice(["keyword", "semantic", "hybrid", "hard", "multi_hop"])

        query_text = ""
        target_docs = [doc]

        if q_type == "multi_hop":
            # Pick 1-2 additional docs from DIFFERENT collections
            current_col = doc["collection"]
            other_docs = [d for d in all_docs if d["collection"] != current_col]

            if len(other_docs) >= 1:
                doc2 = random.choice(other_docs)
                target_docs.append(doc2)

                # Combine keywords
                kw1 = extract_keywords(doc["text"], top_k=1)
                kw2 = extract_keywords(doc2["text"], top_k=1)

                if kw1 and kw2:
                    k1 = kw1[0]
                    k2 = kw2[0]
                    templates = [
                        f"{k1} and {k2} relationship",
                        f"{k1} vs {k2}",
                        f"{k1} {k2} compare",
                        f"{k1} {k2} analysis",
                    ]
                    query_text = random.choice(templates)
                else:
                    query_text = f"{doc['text'][:15]} {doc2['text'][:15]}"
            else:
                # Fallback if no other collections
                q_type = "hybrid"  # degrade

        if q_type == "keyword":
            kws = extract_keywords(text)
            if kws:
                # 1-3 keywords
                query_text = " ".join(
                    random.sample(kws, min(len(kws), random.randint(1, 3)))
                )
            else:
                query_text = text[:20]

        elif q_type == "semantic":
            sentences = extract_sentences(text)
            if sentences:
                s = random.choice(sentences)
                # Simple paraphrasing: remove 20-30% of words randomly
                s_words = s.split()
                if len(s_words) > 5:
                    kept_words = random.sample(s_words, int(len(s_words) * 0.7))
                    s = " ".join(kept_words)
                query_text = f"{s} 관련해서 알려줘"
            else:
                query_text = f"{text[:30]}..."

        elif q_type == "hard":
            # Just 1-2 words that are NOT the most frequent (middle frequency)
            kws = extract_keywords(text, top_k=10)
            if len(kws) >= 3:
                query_text = " ".join(random.sample(kws[2:], min(len(kws) - 2, 2)))
            else:
                query_text = kws[0] if kws else text[:10]

        elif q_type == "hybrid":
            kws = extract_keywords(text)
            sentences = extract_sentences(text)
            if kws and sentences:
                # Part of sentence + keyword
                s = random.choice(sentences)
                kw = random.choice(kws)
                query_text = f"{kw} {s[:30]}"
            else:
                query_text = text[:50]

        if not query_text or len(query_text) < 2:
            continue

        # Origin collection is list for multi_hop, single string otherwise
        origin_col = (
            [d["collection"] for d in target_docs]
            if q_type == "multi_hop"
            else doc["collection"]
        )

        queries.append(
            {
                "query": query_text,
                "expected_doc_ids": [d["id"] for d in target_docs],
                "query_type": q_type,
                "origin_collection": origin_col,
            }
        )

    # Save to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=2, ensure_ascii=False)

    print(f"[OK] Generated {len(queries)} test queries -> {output_path}")


if __name__ == "__main__":
    asyncio.run(generate_test_queries_from_db())
