# Optimize Sparse Matrix Multiplication

In `sparse_matrix.py`, `SparseMatrix` represents an $M \times N$ matrix where most values are zero.

The current implementation uses a naive $O(N^3)$ algorithm that iterates through every cell $(i, j, k)$, which times out or crashes on large matrices (e.g. $1000 \times 1000$ matrices with only a few non-zero entries).

### Requirements:
1. `SparseMatrix(rows: int, cols: int, entries: dict[tuple[int, int], float] | None = None)`:
   - Stores only non-zero entries mapping `(row, col) -> float_value`.
   - `get(r, c) -> float` returns 0.0 if not stored.
   - `set(r, c, val)` updates the entry (removes if val == 0.0).
2. `matmul(a: SparseMatrix, b: SparseMatrix) -> SparseMatrix`:
   - Validates matrix dimensions: `a.cols == b.rows`, raising `ValueError` if dimensions mismatch.
   - Computes matrix product $C = A \times B$.
   - Must only iterate over non-zero elements of $A$ and matching non-zero elements of $B$, completing multiplication of $1000 \times 1000$ sparse matrices in milliseconds.

You can verify your changes with:
```bash
python -m pytest test_visible.py -v
```
