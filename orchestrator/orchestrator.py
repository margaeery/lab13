import asyncio
import json
import logging
from typing import Any, Optional
from nats.aio.client import Client as NATS
from nats.aio.subscription import Subscription

from .models import Task, Result

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        nats_url: str = "nats://localhost:4222",
        timeout: float = 10.0,
    ):
        self.nats_url = nats_url
        self.timeout = timeout
        self.nc: Optional[NATS] = None
        self.sub: Optional[Subscription] = None
        self._pending: dict[str, asyncio.Future] = {}

    async def connect(self) -> None:
        self.nc = NATS()
        await self.nc.connect(self.nats_url)
        self.sub = await self.nc.subscribe("tasks.completed", cb=self._on_result)
        logger.info("orchestrator connected")

    async def disconnect(self) -> None:
        if self.sub:
            await self.sub.unsubscribe()
        if self.nc:
            await self.nc.close()
        logger.info("orchestrator disconnected")

    async def send_task(self, task: Task) -> Result:
        if not self.nc or self.nc.is_closed:
            raise RuntimeError("orchestrator not connected")

        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[task.id] = future

        await self.nc.publish(
            f"tasks.{task.type}",
            json.dumps(task.to_dict()).encode(),
        )
        logger.info("task sent: %s", task.id)

        try:
            result_data = await asyncio.wait_for(future, timeout=self.timeout)
            return Result.from_dict(result_data)
        except asyncio.TimeoutError:
            logger.warning("task timeout: %s", task.id)
            return Result(
                task_id=task.id,
                success=False,
                output=None,
                error="timeout",
            )
        finally:
            self._pending.pop(task.id, None)

    async def _on_result(self, msg) -> None:
        try:
            data = json.loads(msg.data.decode())
            task_id = data.get("task_id")
            if not task_id:
                return

            future = self._pending.pop(task_id, None)
            if future and not future.done():
                future.set_result(data)
                logger.info("result received: %s", task_id)
        except Exception as e:
            logger.error("failed to process result: %s", e)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
