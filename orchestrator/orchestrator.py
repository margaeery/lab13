import asyncio
import json
from typing import Optional
from nats.aio.client import Client as NATS
from nats.aio.subscription import Subscription

from .models import Task, Result
from .logger import setup_logging
from .metrics import Metrics

logger = setup_logging("orchestrator")

DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 10.0


class Orchestrator:
    def __init__(
        self,
        nats_url: str = "nats://localhost:4222",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.nats_url = nats_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.nc: Optional[NATS] = None
        self.sub: Optional[Subscription] = None
        self._pending: dict[str, asyncio.Future] = {}
        self.metrics = Metrics()

    async def connect(self) -> None:
        self.nc = NATS()
        await self.nc.connect(self.nats_url)
        self.sub = await self.nc.subscribe("tasks.completed", cb=self._on_result)
        logger.info("connected to NATS at %s", self.nats_url)

    async def disconnect(self) -> None:
        if self.sub:
            await self.sub.unsubscribe()
        if self.nc:
            await self.nc.close()
        logger.info(
            "disconnected, tasks_processed=%d retries=%d",
            self.metrics.tasks_processed,
            self.metrics.retries,
        )

    async def send_task(self, task: Task) -> Result:
        if not self.nc or self.nc.is_closed:
            logger.error("send_task failed: not connected")
            raise RuntimeError("orchestrator not connected")

        for attempt in range(1, self.max_retries + 1):
            future: asyncio.Future = asyncio.get_event_loop().create_future()
            self._pending[task.id] = future

            subject = f"tasks.{task.type}"
            await self.nc.publish(subject, json.dumps(task.to_dict()).encode())
            logger.info(
                "task sent | task_id=%s subject=%s attempt=%d/%d",
                task.id,
                subject,
                attempt,
                self.max_retries,
            )

            try:
                result_data = await asyncio.wait_for(future, timeout=self.timeout)
                self.metrics.increment()
                result = Result.from_dict(result_data)
                logger.info(
                    "task completed | task_id=%s success=%s",
                    task.id,
                    result.success,
                )
                return result
            except asyncio.TimeoutError:
                self._pending.pop(task.id, None)
                if attempt < self.max_retries:
                    self.metrics.record_retry()
                    logger.warning(
                        "task timeout, retrying | task_id=%s attempt=%d/%d timeout=%.1fs",
                        task.id,
                        attempt,
                        self.max_retries,
                        self.timeout,
                    )
                else:
                    self.metrics.increment()
                    logger.error(
                        "task exhausted all retries | task_id=%s max_retries=%d timeout=%.1fs",
                        task.id,
                        self.max_retries,
                        self.timeout,
                    )
                    return Result(
                        task_id=task.id,
                        success=False,
                        output=None,
                        error="timeout",
                    )

        self.metrics.increment()
        return Result(
            task_id=task.id,
            success=False,
            output=None,
            error="timeout",
        )

    async def _on_result(self, msg) -> None:
        try:
            data = json.loads(msg.data.decode())
            task_id = data.get("task_id")
            if not task_id:
                logger.warning("result without task_id ignored")
                return

            future = self._pending.pop(task_id, None)
            if future and not future.done():
                future.set_result(data)
                logger.debug("result matched | task_id=%s", task_id)
            else:
                logger.debug("result unmatched | task_id=%s", task_id)
        except Exception as e:
            logger.error("failed to process incoming result: %s", e)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
