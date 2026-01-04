"""Collection and snapshot management helpers for Qdrant."""

from __future__ import annotations


from qdrant_client import models

from llm_backend.utils.logger import logger

from .quantization_manager import (
    get_scalar_quantization_config,
    get_hnsw_config,
    get_optimization_config,
)


def create_collection(
    manager,
    name: str,
    vector_size: int,
    distance: str | models.Distance = "Cosine",
    force: bool = False,
    include_sparse: bool = True,
    include_splade: bool = True,
    use_quantization: bool = True,
    extra_vectors: dict[str, models.VectorParams] | None = None,
) -> None:
    """Create or recreate a collection with production-ready optimizations."""

    if isinstance(distance, str):
        distance = {
            "Cosine": models.Distance.COSINE,
            "Dot": models.Distance.DOT,
            "Euclid": models.Distance.EUCLID,
        }.get(distance, models.Distance.COSINE)

    if force:
        try:
            manager.client.delete_collection(name)
        except Exception:
            pass

    vectors_cfg = {
        "dense": models.VectorParams(size=vector_size, distance=distance),
        "title": models.VectorParams(size=vector_size, distance=distance),
    }
    if extra_vectors:
        vectors_cfg.update(extra_vectors)
    sparse_cfg = {}
    if include_sparse:
        sparse_cfg["sparse"] = models.SparseVectorParams(
            index=models.SparseIndexParams(on_disk=False)
        )
    if include_splade:
        sparse_cfg["splade"] = models.SparseVectorParams(
            index=models.SparseIndexParams(on_disk=False)
        )

    # collection_exists may raise 404 on some client/server versions instead of returning False
    exists = False
    try:
        manager.client.get_collection(name)
        exists = True
    except Exception:
        exists = False

    if exists:
        manager.client.delete_collection(name)

    manager.client.create_collection(
        collection_name=name,
        vectors_config=vectors_cfg,
        sparse_vectors_config=sparse_cfg if sparse_cfg else None,
        quantization_config=get_scalar_quantization_config()
        if use_quantization
        else None,
        hnsw_config=get_hnsw_config(),
        optimizers_config=get_optimization_config(),
    )
    logger.info(f"Created collection '{name}' with HNSW & Optimizer tuning.")

    try:
        manager.client.create_payload_index(
            collection_name=name,
            field_name="db_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True,
        )
        logger.info(f"[create_collection] Created 'db_id' payload index for '{name}'")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            f"[create_collection] Failed to create payload index for '{name}': {exc}"
        )


def delete_collection(manager, name: str) -> None:
    """Delete a single collection if it exists."""
    manager.client.delete_collection(name)
    logger.info(f"Deleted collection '{name}'")


def delete_all_collections(manager) -> int:
    """Drop every collection in the Qdrant instance."""
    cols = manager.client.get_collections().collections or []
    count = 0
    for col in cols:
        try:
            manager.client.delete_collection(col.name)
            count += 1
            logger.info(f"Deleted collection '{col.name}'")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to delete collection '{col.name}': {exc}")
    return count
