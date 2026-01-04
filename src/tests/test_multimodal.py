import asyncio
import os
import sys
from PIL import Image

# Priority for local 'src'
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.collection_manager import create_collection
from llm_backend.vectorstore.multimodal_processor import MultimodalProcessor
from qdrant_client.models import VectorParams, Distance, PointStruct


async def test_multimodal():
    print("=== Testing Phase 5: Multimodal RAG ===")

    col_name = "test.multimodal"
    processor = MultimodalProcessor()

    with acquire_manager() as mgr:
        # 1. Create Collection with CLIP dimension (512)
        print(f"Creating collection '{col_name}'...")
        extra = {"image": VectorParams(size=512, distance=Distance.COSINE)}
        create_collection(
            mgr, col_name, vector_size=768, force=True, extra_vectors=extra
        )

        # 2. Index local images
        image_paths = [
            "/Users/bagjimin/.gemini/antigravity/brain/5fffda67-50f4-46b3-ad71-4bb25160ad55/ai_chip_diagram_1767021654109.png",
            "/Users/bagjimin/.gemini/antigravity/brain/5fffda67-50f4-46b3-ad71-4bb25160ad55/ocean_research_ship_1767021669132.png",
        ]

        points = []
        for i, path in enumerate(image_paths):
            print(f"Processing image {i + 1}: {os.path.basename(path)}...")
            img = Image.open(path)
            emb = processor.encode_image(img)

            payload = {
                "source": os.path.basename(path),
                "desc": "AI Diagram" if "ai_chip" in path else "Research Ship",
            }
            points.append(PointStruct(id=i, vector={"image": emb}, payload=payload))

        mgr.client.upsert(collection_name=col_name, points=points)
        print(f"Indexed {len(points)} images.")

        # 3. Test Text-to-Image Search
        queries = ["neural network diagram", "big boat in the ocean"]

        for q in queries:
            print(f"\nQuery: '{q}'")
            results = await processor.search_images_by_text(
                mgr.client, col_name, q, top_k=1
            )
            for r in results:
                print(f"- Found: {r.payload['source']} (Score: {r.score:.4f})")


if __name__ == "__main__":
    asyncio.run(test_multimodal())
