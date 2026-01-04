import sys
import pickle
import numpy as np
from qdrant_client import models

# Simulate 50 docs
dense_vec = [0.1] * 1024
sparse_vec = models.SparseVector(indices=[1, 2, 3], values=[0.1, 0.2, 0.3])

points = []
for i in range(50):
    point = models.PointStruct(
        id=str(i),
        vector={
            "dense": dense_vec,
            "sparse": sparse_vec,
            "splade": sparse_vec
        },
        payload={"data": "x" * 100}
    )
    points.append(point)

size = sys.getsizeof(points)
print(f"List size: {size} bytes")
print(f"Pickled size: {len(pickle.dumps(points))} bytes")
