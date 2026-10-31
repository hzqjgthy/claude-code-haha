from collections.abc import Callable
from threading import Lock

from claude_code_py.ui.state.app_state import ReplAppState

StateSubscriber = Callable[[ReplAppState], None]
StateUpdater = Callable[[ReplAppState], ReplAppState]


class AppStateStore:
    def __init__(self, initial_state: ReplAppState) -> None:
        self._state = initial_state
        self._lock = Lock()
        self._subscribers: list[StateSubscriber] = []

    def get_state(self) -> ReplAppState:
        with self._lock:
            return self._state

    def set_state(self, state: ReplAppState) -> ReplAppState:
        with self._lock:
            self._state = state
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber(state)
        return state

    def update(self, updater: StateUpdater) -> ReplAppState:
        with self._lock:
            next_state = updater(self._state)
            self._state = next_state
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber(next_state)
        return next_state

    def subscribe(self, subscriber: StateSubscriber) -> Callable[[], None]:
        with self._lock:
            self._subscribers.append(subscriber)

        def unsubscribe() -> None:
            with self._lock:
                self._subscribers = [
                    candidate
                    for candidate in self._subscribers
                    if candidate is not subscriber
                ]

        return unsubscribe
