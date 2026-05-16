import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import pytest
from nats.aio.client import Client as NATS

from orchestrator.orchestrator import Orchestrator
from orchestrator.models import create_appointment_task, Task, Result

logging.basicConfig(level=logging.INFO)

NATS_URL = "nats://localhost:4222"
TIMEOUT = 10.0


@pytest.fixture
async def nats_client():
    nc = NATS()
    await nc.connect(NATS_URL)
    yield nc
    await nc.close()


@pytest.fixture
async def orchestrator():
    orch = Orchestrator(nats_url=NATS_URL, timeout=TIMEOUT)
    await orch.connect()
    yield orch
    await orch.disconnect()


@pytest.mark.asyncio
async def test_successful_appointment_booking(orchestrator):
    task = create_appointment_task(
        full_name="Иванов Иван Иванович",
        birth_date="1990-01-01",
        contact="ivan@example.com",
        specialty="Терапевт",
        preferred_date_time=datetime.now(timezone.utc) + timedelta(days=2),
        type_="offline",
    )

    result = await orchestrator.send_task(task)

    assert result.task_id == task.id
    assert result.success is True
    assert "date_time" in result.output
    assert "location" in result.output
    assert result.output["location"].startswith("Cabinet")


@pytest.mark.asyncio
async def test_online_appointment_booking(orchestrator):
    task = create_appointment_task(
        full_name="Петров Петр Петрович",
        birth_date="1985-05-15",
        contact="petr@example.com",
        specialty="Кардиолог",
        preferred_date_time=datetime.now(timezone.utc) + timedelta(days=3),
        type_="online",
    )

    result = await orchestrator.send_task(task)

    assert result.task_id == task.id
    assert result.success is True
    assert result.output["location"].startswith("https://")


@pytest.mark.asyncio
async def test_duplicate_slot_rejected(orchestrator):
    same_time = datetime.now(timezone.utc) + timedelta(days=5)

    task1 = create_appointment_task(
        full_name="Пациент А",
        birth_date="2000-01-01",
        contact="a@example.com",
        specialty="Хирург",
        preferred_date_time=same_time,
        type_="offline",
    )

    task2 = create_appointment_task(
        full_name="Пациент Б",
        birth_date="2001-01-01",
        contact="b@example.com",
        specialty="Хирург",
        preferred_date_time=same_time,
        type_="offline",
    )

    result1 = await orchestrator.send_task(task1)
    await asyncio.sleep(0.5)
    result2 = await orchestrator.send_task(task2)

    assert result1.success is True
    assert result2.success is False
    assert "booked" in result2.output.lower()


@pytest.mark.asyncio
async def test_past_date_rejected(orchestrator):
    task = create_appointment_task(
        full_name="Сидоров Сидор",
        birth_date="1978-03-20",
        contact="sidor@example.com",
        specialty="Невролог",
        preferred_date_time=datetime.now(timezone.utc) - timedelta(days=1),
        type_="offline",
    )

    result = await orchestrator.send_task(task)

    assert result.success is False
    assert "future" in result.output.lower()


@pytest.mark.asyncio
async def test_invalid_type_rejected(orchestrator):
    task = create_appointment_task(
        full_name="Кузнецов Кузьма",
        birth_date="1995-07-10",
        contact="kuzma@example.com",
        specialty="Дерматолог",
        preferred_date_time=datetime.now(timezone.utc) + timedelta(days=1),
        type_="invalid_type",
    )

    result = await orchestrator.send_task(task)

    assert result.success is False
    assert "offline or online" in result.output.lower()


@pytest.mark.asyncio
async def test_empty_name_rejected(orchestrator):
    task = create_appointment_task(
        full_name="",
        birth_date="1995-07-10",
        contact="empty@example.com",
        specialty="Офтальмолог",
        preferred_date_time=datetime.now(timezone.utc) + timedelta(days=1),
        type_="offline",
    )

    result = await orchestrator.send_task(task)

    assert result.success is False
    assert "full name" in result.output.lower()


@pytest.mark.asyncio
async def test_result_published_to_completed_topic(nats_client):
    orch = Orchestrator(nats_url=NATS_URL, timeout=TIMEOUT)
    await orch.connect()

    received = []

    async def handler(msg):
        data = json.loads(msg.data.decode())
        received.append(data)

    sub = await nats_client.subscribe("tasks.completed", cb=handler)

    task = create_appointment_task(
        full_name="Тестов Тест",
        birth_date="1980-01-01",
        contact="test@example.com",
        specialty="Уролог",
        preferred_date_time=datetime.now(timezone.utc) + timedelta(days=4),
        type_="offline",
    )

    await orch.send_task(task)
    await asyncio.sleep(1)

    await sub.unsubscribe()
    await orch.disconnect()

    assert len(received) >= 1
    assert received[0]["task_id"] == task.id
    assert "success" in received[0]