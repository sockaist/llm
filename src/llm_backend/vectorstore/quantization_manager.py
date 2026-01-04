"""Quantization configurations for Qdrant optimization."""

from qdrant_client import models


def get_scalar_quantization_config():
    """
    Returns Scalar Quantization (int8) configuration.
    Reduces memory usage by ~75% and speeds up search.
    Best for Cosine distance.
    """
    return models.ScalarQuantization(
        scalar=models.ScalarQuantizationConfig(
            type=models.ScalarType.INT8,
            quantile=0.99,
            always_ram=True,
        )
    )


def get_product_quantization_config(ratio: int = 4):
    """
    Returns Product Quantization configuration.
    Can reduce memory usage by up to 90%+.
    Better for Euclidean or larger vectors, but higher accuracy loss than Scalar.
    """
    return models.ProductQuantization(
        product=models.ProductQuantizationConfig(
            compression=models.CompressionRatio.X4
            if ratio == 4
            else models.CompressionRatio.X8,
            always_ram=True,
        )
    )


def get_hnsw_config(m: int = 16, ef_construct: int = 100):
    """
    Returns HNSW index configuration.
    m: Number of edges per node (default 16). Increase for better accuracy, slower search.
    ef_construct: Number of neighbors to consider during construction (default 100).
    """
    return models.HnswConfigDiff(
        m=m,
        ef_construct=ef_construct,
        full_scan_threshold=1000,
        on_disk=False,  # Keep in RAM for performance
    )


def get_optimization_config():
    """
    Returns recommended optimizers config for production.
    """
    return models.OptimizersConfigDiff(
        indexing_threshold=5000,  # Start HNSW building earlier for small collections
        memmap_threshold=20000,  # Use memmap after 20k points
    )
