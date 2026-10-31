def normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").strip()
