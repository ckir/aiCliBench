from sparse_matrix import SparseMatrix, matmul


def test_identity():
    m = SparseMatrix(2, 2, {(0, 0): 1.0, (1, 1): 1.0})
    res = matmul(m, m)
    assert res.get(0, 0) == 1.0
