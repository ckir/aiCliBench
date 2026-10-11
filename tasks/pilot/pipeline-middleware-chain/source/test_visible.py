from pipeline import Pipeline


def test_empty_pipeline():
    p = Pipeline()
    ctx = {"val": 1}
    assert p.execute(ctx) == {"val": 1}
