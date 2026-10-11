"""CSV dialect sniffer and parser."""


def sniff_delimiter(sample: str, candidates: tuple[str, ...] = (",", "\t", ";", "|")) -> str:
    # Stub
    return ","


def parse_tabular_data(text: str, delimiter: str | None = None) -> list[dict[str, str]]:
    # Stub
    return []
