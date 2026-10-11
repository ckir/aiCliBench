# Solution

Recursive dispatcher chain:
```python
def execute(self, context: dict) -> dict:
    def dispatch(index: int, ctx: dict) -> dict:
        if index == len(self._middlewares):
            return ctx
        mw = self._middlewares[index]
        return mw(ctx, lambda next_ctx: dispatch(index + 1, next_ctx))

    return dispatch(0, dict(context))
```
