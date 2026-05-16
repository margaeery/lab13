import json
from unittest.mock import AsyncMock, patch

import pytest

from orchestrator.models import Task
from orchestrator.orchestrator import Orchestrator


class Message:
    def __init__(self, data: bytes):
        self.data = data


@pytest.fixture
def orchestrator_instance():
    return Orchestrator(nats_url="nats://test:4222", timeout=0.01, max_retries=2)


@pytest.mark.asyncio
async def test_connect_creates_nats_subscription(orchestrator_instance):
    subscription = AsyncMock()
    client = AsyncMock()
    client.subscribe = AsyncMock(return_value=subscription)

    with patch("orchestrator.orchestrator.NATS", return_value=client):
        await orchestrator_instance.connect()

    client.connect.assert_awaited_once_with("nats://test:4222")
    client.subscribe.assert_awaited_once()
    assert orchestrator_instance.nc is client
    assert orchestrator_instance.sub is subscription


@pytest.mark.asyncio
async def test_send_task_returns_result_with_mocked_nats(orchestrator_instance):
    client = AsyncMock()
    client.is_closed = False
    orchestrator_instance.nc = client

    async def publish(subject, payload):
        task_data = json.loads(payload.decode())
        result = {
            "task_id": task_data["id"],
            "success": True,
            "output": {"status": "processed"},
            "agent_id": "mock-agent",
        }
        await orchestrator_instance._on_result(Message(json.dumps(result).encode()))

    client.publish.side_effect = publish

    task = Task(id="unit-task-1", type="appointment", payload={"value": 1})
    result = await orchestrator_instance.send_task(task)

    client.publish.assert_awaited_once()
    assert result.success is True
    assert result.task_id == task.id
    assert result.output == {"status": "processed"}
    assert result.agent_id == "mock-agent"
    assert orchestrator_instance.metrics.tasks_processed == 1


@pytest.mark.asyncio
async def test_send_task_retries_and_succeeds_on_second_attempt(orchestrator_instance):
    client = AsyncMock()
    client.is_closed = False
    orchestrator_instance.nc = client
    attempts = 0

    async def publish(subject, payload):
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            task_data = json.loads(payload.decode())
            result = {
                "task_id": task_data["id"],
                "success": True,
                "output": {"attempt": attempts},
                "agent_id": "retry-agent",
            }
            await orchestrator_instance._on_result(Message(json.dumps(result).encode()))

    client.publish.side_effect = publish

    task = Task(id="unit-task-2", type="appointment", payload={"value": 2})
    result = await orchestrator_instance.send_task(task)

    assert result.success is True
    assert result.output == {"attempt": 2}
    assert attempts == 2
    assert orchestrator_instance.metrics.retries == 1
    assert orchestrator_instance.metrics.tasks_processed == 1


@pytest.mark.asyncio
async def test_send_task_returns_timeout_with_mocked_nats(orchestrator_instance):
    client = AsyncMock()
    client.is_closed = False
    orchestrator_instance.nc = client

    task = Task(id="unit-task-3", type="appointment", payload={"value": 3})
    result = await orchestrator_instance.send_task(task)

    assert client.publish.await_count == 2
    assert result.success is False
    assert result.error == "timeout"
    assert result.task_id == task.id
    assert orchestrator_instance.metrics.retries == 1
    assert orchestrator_instance.metrics.tasks_processed == 1


@pytest.mark.asyncio
async def test_disconnect_closes_subscription_and_connection(orchestrator_instance):
    subscription = AsyncMock()
    client = AsyncMock()
    orchestrator_instance.sub = subscription
    orchestrator_instance.nc = client

    await orchestrator_instance.disconnect()

    subscription.unsubscribe.assert_awaited_once()
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_task_raises_when_not_connected():
    instance = Orchestrator(nats_url="nats://test:4222", timeout=0.01, max_retries=1)
    task = Task(id="unit-task-4", type="appointment", payload={})

    with pytest.raises(RuntimeError, match="orchestrator not connected"):
        await instance.send_task(task)