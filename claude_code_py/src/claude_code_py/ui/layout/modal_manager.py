class ModalManager:
    def __init__(self) -> None:
        self._active_key: str | None = None

    @property
    def active_key(self) -> str | None:
        return self._active_key

    def should_present(self, key: str) -> bool:
        return key != self._active_key

    def mark_presented(self, key: str) -> None:
        self._active_key = key

    def clear(self) -> None:
        self._active_key = None
