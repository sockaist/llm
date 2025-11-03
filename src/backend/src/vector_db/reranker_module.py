# reranker_module.py
import numpy as np

def normalize_scores(score_dict):
    """
    각 점수 사전을 0~1 범위로 정규화
    """
    if not score_dict:
        return {}
    values = np.array(list(score_dict.values()))
    min_v, max_v = values.min(), values.max()
    if max_v - min_v < 1e-8:
        return {k: 0.5 for k in score_dict}  # 모든 점수가 동일하면 0.5로 고정
    return {k: (v - min_v) / (max_v - min_v) for k, v in score_dict.items()}


def combine_scores(
    dense_results,
    sparse_results,
    splade_results,
    w_dense=0.6,
    w_sparse=0.25,
    w_splade=0.15,
):
    """
    Dense, Sparse(BM25), SPLADE 점수를 가중합으로 통합하여 리랭킹.

    Args:
        dense_results: Qdrant 결과 리스트 (ScoredPoint[])
        sparse_results: Qdrant 결과 리스트 (ScoredPoint[])
        splade_results: Qdrant 결과 리스트 (ScoredPoint[])
        w_dense, w_sparse, w_splade: 각 점수 가중치 비율

    Returns:
        List of (id, score, payload) sorted by combined score
    """
    dense_dict = {r.id: r.score for r in dense_results}
    sparse_dict = {r.id: r.score for r in sparse_results}
    splade_dict = {r.id: r.score for r in splade_results}

    dense_norm = normalize_scores(dense_dict)
    sparse_norm = normalize_scores(sparse_dict)
    splade_norm = normalize_scores(splade_dict)

    all_ids = set(dense_norm.keys()) | set(sparse_norm.keys()) | set(splade_norm.keys())

    combined = {}
    for pid in all_ids:
        combined[pid] = (
            w_dense * dense_norm.get(pid, 0)
            + w_sparse * sparse_norm.get(pid, 0)
            + w_splade * splade_norm.get(pid, 0)
        )

    ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)
    return ranked


def print_rerank_summary(ranked, client, col_name, top_n=10):
    """
    rerank 결과 요약 출력 (문서 ID와 제목만)
    """
    print("\n=== RERANKED RESULTS ===")
    for idx, (pid, score) in enumerate(ranked[:top_n]):
        doc = client.retrieve(collection_name=col_name, ids=[pid], with_payload=True)
        if doc:
            payload = doc[0].payload
            title = payload.get("title", "(no title)")
            print(f"{idx+1:02d}. ID={pid}, score={score:.4f}, title={title}")
    print("=========================\n")