"""Hidden acceptance tests for Pipeline."""

from pipeline import Pipeline  # ty: ignore[unresolved-import]


def test_onion_execution_order():
    p = Pipeline()
    order = []

    def m1(ctx, next_fn):
        order.append("m1_pre")
        ctx["m1"] = True
        res = next_fn(ctx)
        order.append("m1_post")
        return res

    def m2(ctx, next_fn):
        order.append("m2_pre")
        ctx["m2"] = True
        res = next_fn(ctx)
        order.append("m2_post")
        return res

    p.use(m1).use(m2)
    final_ctx = p.execute({"input": 42})

    assert order == ["m1_pre", "m2_pre", "m2_post", "m1_post"]
    assert final_ctx["m1"] is True
    assert final_ctx["m2"] is True
    assert final_ctx["input"] == 42


def test_middleware_error_interception():
    p = Pipeline()

    def error_catcher(ctx, next_fn):
        try:
            return next_fn(ctx)
        except ValueError:
            ctx["recovered"] = True
            return ctx

    def faulty(ctx, next_fn):
        raise ValueError("boom")

    p.use(error_catcher).use(faulty)
    res = p.execute({})
    assert res.get("recovered") is True
