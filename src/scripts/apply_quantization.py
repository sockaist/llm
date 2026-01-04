import sys
import os

sys.path.append(os.path.join(os.getcwd(), "src"))

from llm_backend.server.vector_server.core.resource_pool import acquire_manager
from llm_backend.vectorstore.quantization_manager import get_scalar_quantization_config


def apply_quantization_all():
    print("Applying Scalar Quantization to all collections...")
    with acquire_manager() as mgr:
        resp = mgr.client.get_collections()
        collections = [c.name for c in resp.collections]

        quant_cfg = get_scalar_quantization_config()

        for col in collections:
            print(f"Updating '{col}'...")
            try:
                mgr.client.update_collection(
                    collection_name=col, quantization_config=quant_cfg
                )
                print(f"[OK] Successfully updated '{col}'")
            except Exception as e:
                print(f"[FAIL] Failed to update '{col}': {e}")


if __name__ == "__main__":
    apply_quantization_all()
