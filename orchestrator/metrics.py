class Metrics:
    def __init__(self):
        self._tasks_processed = 0
        self._retries = 0

    def increment(self) -> None:
        self._tasks_processed += 1

    def record_retry(self) -> None:
        self._retries += 1

    @property
    def tasks_processed(self) -> int:
        return self._tasks_processed

    @property
    def retries(self) -> int:
        return self._retries