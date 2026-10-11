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

    b_by_row: dict[int, list[tuple[int, float]]] = {}
    for (br, bc), bval in b.entries.items():
        b_by_row.setdefault(br, []).append((bc, bval))

    c_entries: dict[tuple[int, int], float] = {}
    for (ar, ac), aval in a.entries.items():
        for bc, bval in b_by_row.get(ac, ()):
            c_entries[(ar, bc)] = c_entries.get((ar, bc), 0.0) + aval * bval

    filtered = {k: v for k, v in c_entries.items() if v != 0.0}
    return SparseMatrix(a.rows, b.cols, filtered)
