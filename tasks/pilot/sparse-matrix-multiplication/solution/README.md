# Solution

Group entries of B by row, then iterate over non-zero entries of A:
```python
def matmul(a: SparseMatrix, b: SparseMatrix) -> SparseMatrix:
    if a.cols != b.rows:
        raise ValueError("Incompatible dimensions")
    b_by_row: dict[int, list[tuple[int, float]]] = {}
    for (br, bc), bval in b.entries.items():
        b_by_row.setdefault(br, []).append((bc, bval))

    c_entries: dict[tuple[int, int], float] = {}
    for (ar, ac), aval in a.entries.items():
        if ac in b_by_row:
            for bc, bval in b_by_row[ac]:
                c_entries[(ar, bc)] = c_entries.get((ar, bc), 0.0) + aval * bval

    # filter zeros
    filtered = {k: v for k, v in c_entries.items() if v != 0.0}
    return SparseMatrix(a.rows, b.cols, filtered)
```
