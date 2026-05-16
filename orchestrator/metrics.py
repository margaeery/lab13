class Metrics:
    def __init__(self):
        self._tasks_processed = 0

    def increment(self) -> None:
        self._tasks_processed += 1

    @property
    def tasks_processed(self) -> int:
        return self._tasks_processed
