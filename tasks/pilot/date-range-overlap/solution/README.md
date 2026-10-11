# Solution

```python
def contains(self, dt: datetime) -> bool:
    return self.start <= dt < self.end


def overlaps(self, other: DateRange) -> bool:
    return self.start < other.end and other.start < self.end
```
