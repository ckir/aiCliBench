"""Sparse Matrix implementation."""

from __future__ import annotations


class SparseMatrix:
    def __init__(
        self, rows: int, cols: int, entries: dict[tuple[int, int], float] | None = None
    ) -> None:
        self.rows = rows
        self.cols = cols
        self.entries: dict[tuple[int, int], float] = entries or {}

    def get(self, r: int, c: int) -> float:
        return self.entries.get((r, c), 0.0)

    def set(self, r: int, c: int, val: float) -> None:
        if val == 0.0:
            self.entries.pop((r, c), None)
        else:
            self.entries[(r, c)] = val


def matmul(a: SparseMatrix, b: SparseMatrix) -> SparseMatrix:
    if a.cols != b.rows:
        raise ValueError(f"Incompatible dimensions: {a.cols} != {b.rows}")

    # Slow O(N^3) dense iteration that times out on sparse matrices
    c = SparseMatrix(a.rows, b.cols)
    for i in range(a.rows):
        for j in range(b.cols):
            s = 0.0
            for k in range(a.cols):
                s += a.get(i, k) * b.get(k, j)
            if s != 0.0:
                c.set(i, j, s)
    return c
