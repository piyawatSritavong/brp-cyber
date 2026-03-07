from threading import Lock


class RuntimeState:
    def __init__(self) -> None:
        self._kill_switch_enabled = False
        self._lock = Lock()

    def set_kill_switch(self, enabled: bool) -> None:
        with self._lock:
            self._kill_switch_enabled = enabled

    def is_kill_switch_enabled(self) -> bool:
        with self._lock:
            return self._kill_switch_enabled


runtime_state = RuntimeState()
