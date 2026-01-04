import json
import random
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from llm_backend.server.vector_server.core.resource_pool import acquire_manager


def prepare_data():
    print("Preparing Fine-tuning Data...")

    # Use fresh queries generated from current DB state to ensure valid IDs
    with open("src/tests/test_queries.json", "r") as f:
        queries = json.load(f)

    training_data = []

    with acquire_manager() as mgr:
        # Pre-fetch all docs from research to serve as negatives
        # We focus on research collection mainly as it's the bottleneck
        research_docs = []
        try:
            scroll_res, _ = mgr.client.scroll(
                collection_name="csweb.research", limit=1000, with_payload=True
            )
            # Fix: Research docs might not have 'text', accept them anyway for now
            research_docs = (
                scroll_res  # [r for r in scroll_res if r.payload.get("text")]
            )
        except Exception as e:
            print(f"Error fetching research docs: {e}")

        print(f"Loaded {len(research_docs)} candidate docs for negatives.")

        for q in queries:
            qid = q.get("query")
            # We want to use our new instruction format
            # Instruction: Find academic profile for this query.
            # But BGE-M3 finetuning usually takes query and pos/neg. We can bake instruction into query.

            instruction = "Instruct: Find academic profile\nQuery: "
            query_text = f"{instruction}{qid}"

            target_ids = q.get("expected_doc_ids", [])
            col = q.get("origin_collection")

            if not target_ids:
                continue

            # print(f"Processing {qid} targeting {target_ids} in {col}")

            # Fetch Positive
            # We need to find the text for these IDs.
            # Using scroll with filter
            from qdrant_client import models

            pos_text = []
            try:
                # Debug: check if IDs match exactly or need casting
                # Assuming simple match first
                points, _ = mgr.client.scroll(
                    collection_name=col,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="db_id", match=models.MatchAny(any=target_ids)
                            )
                        ]
                    ),
                    with_payload=True,
                    limit=len(target_ids),
                )
                if not points:
                    print(f"DEBUG: No points found for {target_ids} in {col}")

                for p in points:
                    # Fix: Research collection uses 'content' not 'text' or might need construction
                    txt = p.payload.get("text") or p.payload.get("content")
                    if not txt:
                        # Fallback construction for research profile
                        lines = []
                        if p.payload.get("name"):
                            lines.append(f"Name: {p.payload['name']}")
                        if p.payload.get("professor"):
                            lines.append(f"Professor: {p.payload['professor']}")
                        if p.payload.get("field"):
                            lines.append(f"Field: {p.payload['field']}")
                        if p.payload.get("intro"):
                            lines.append(f"Intro: {p.payload['intro']}")
                        txt = " | ".join(lines)

                    if txt:
                        pos_text.append(txt)
            except Exception as e:
                print(f"Error fetching pos for {qid}: {e}")
                continue

            if not pos_text:
                continue

            # Negative Mining
            # Pick casual negatives from research collection (if query is research)
            # or random from generic.
            neg_text = []
            try:
                if col == "csweb.research" and research_docs:
                    # Pick 2 random docs that are NOT in target_ids
                    candidates = [
                        d
                        for d in research_docs
                        if d.id not in target_ids
                        and d.payload.get("db_id") not in target_ids
                    ]
                    if candidates:
                        samples = random.sample(candidates, min(2, len(candidates)))
                        for s in samples:
                            # Same fix for negatives
                            ntxt = s.payload.get("text") or s.payload.get("content")
                            if not ntxt:
                                lines = []
                                if s.payload.get("name"):
                                    lines.append(f"Name: {s.payload['name']}")
                                if s.payload.get("professor"):
                                    lines.append(f"Professor: {s.payload['professor']}")
                                if s.payload.get("field"):
                                    lines.append(f"Field: {s.payload['field']}")
                                ntxt = " | ".join(lines)
                            if ntxt:
                                neg_text.append(ntxt)
            except Exception as e:
                print(f"Error fetching negs for {qid}: {e}")
                # Don't continue, just have empty negs
                pass

            if not neg_text:
                # BGE training requires at least one negative
                continue

            # Construct standard JSONL format for FlagEmbedding
            # {"query": str, "pos": [str], "neg": [str]}
            record = {"query": query_text, "pos": pos_text, "neg": neg_text}
            training_data.append(record)

    print(f"Generated {len(training_data)} training examples.")

    with acquire_manager() as mgr:
        pass  # Just context manager

    with open("finetune_data.jsonl", "w") as f:
        for t in training_data:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    print("Saved to finetune_data.jsonl")


if __name__ == "__main__":
    prepare_data()
