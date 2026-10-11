# Solution

Match logic:
```python
import re


def _pattern_to_regex(pattern: str) -> re.Pattern:
    parts = pattern.split(".")
    regex_parts = []
    for part in parts:
        if part == "**":
            regex_parts.append(r".*")
        elif part == "*":
            regex_parts.append(r"[^.]+")
        else:
            regex_parts.append(re.escape(part))
    return re.compile(f"^{r'\.'.join(regex_parts)}$")
```
