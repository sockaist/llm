import json

def analyze():
    with open("benchmark_fallback_fix.json", "r") as f:
        data = json.load(f)
        
    with open("src/tests/comparison_queries.json", "r") as f:
        queries = json.load(f)
        
    # Map query text to origin collection
    q_map = {q["query"]: q.get("origin_collection", "unknown") for q in queries}
    
    col_stats = {}
    
    for detail in data["details"]:
        q_text = detail["query"]
        col = q_map.get(q_text, "unknown")
        
        if col not in col_stats:
            col_stats[col] = {"hits": 0, "total": 0, "mrr_sum": 0.0}
            
        col_stats[col]["total"] += 1
        col_stats[col]["mrr_sum"] += (1.0 / detail["hit_rank"]) if detail["hit_rank"] > 0 else 0
        if detail["hit_rank"] > 0 and detail["hit_rank"] <= 5: # NDCG@5 logic roughly
             col_stats[col]["hits"] += 1
             
    print(f"{'Collection':<20} | {'Total':<5} | {'Hit@5':<5} | {'MRR':<5}")
    print("-" * 45)
    for col, stats in col_stats.items():
        total = stats["total"]
        if total == 0:
            continue
        hit_rate = stats["hits"] / total
        mrr = stats["mrr_sum"] / total
        print(f"{col:<20} | {total:<5} | {hit_rate:.1%} | {mrr:.3f}")

if __name__ == "__main__":
    analyze()
