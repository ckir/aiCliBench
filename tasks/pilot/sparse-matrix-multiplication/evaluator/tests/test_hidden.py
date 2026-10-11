"""Hidden acceptance tests for Sparse Matrix."""

import time

from sparse_matrix import SparseMatrix, matmul  # ty: ignore[unresolved-import]


def test_correctness_and_performance():
    # 1000 x 1000 matrices with sparse entries
    N = 1000
    a = SparseMatrix(N, N)
    b = SparseMatrix(N, N)

    # Put a few diagonal and non-diagonal entries
    for i in range(0, N, 10):
        a.set(i, (i + 1) % N, 2.0)
        b.set((i + 1) % N, (i + 2) % N, 3.0)

    start = time.perf_counter()
    c = matmul(a, b)
    elapsed = time.perf_counter() - start

    # Must complete fast (< 0.2s)
    assert elapsed < 0.2, f"Matrix multiplication too slow: {elapsed:.3f}s"
    assert c.get(0, 2) == 6.0
    assert c.get(10, 12) == 6.0
