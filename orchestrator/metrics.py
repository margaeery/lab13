from threading import Lock


class Metrics:
    def __init__(self):
        self._tasks_processed = 0
        self._retries = 0
        self._lock = Lock()

    def increment(self) -> None:
        with self._lock:
            self._tasks_processed += 1

    def record_retry(self) -> None:
        with self._lock:
            self._retries += 1

    @property
    def tasks_processed(self) -> int:
        with self._lock:
            return self._tasks_processed

    @property
    def retries(self) -> int:
        with self._lock:
            return self._retries