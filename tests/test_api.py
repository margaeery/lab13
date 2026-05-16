from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from api.dependencies import get_task_service
from api.main import app
from orchestrator.models import Result


app.state.skip_orchestrator_lifespan = True


class SuccessService:
    async def submit_appointment(self, request):
        return Result(
            task_id="task-1",
            success=True,
            output={
                "date_time": request.preferred_date_time.isoformat(),
                "location": "Cabinet 12",
            },
            agent_id="agent-1",
        )


class ValidationErrorService:
    async def submit_appointment(self, request):
        return Result(
            task_id="task-2",
            success=False,
            output="slot is already booked",
            agent_id="agent-2",
        )


class TimeoutService:
    async def submit_appointment(self, request):
        return Result(
            task_id="task-3",
            success=False,
            output=None,
            error="timeout",
        )


class UnavailableService:
    async def submit_appointment(self, request):
        raise RuntimeError("orchestrator not connected")


def build_payload() -> dict:
    return {
        "full_name": "Иванов Иван",
        "birth_date": "1990-01-01",
        "contact": "ivan@example.com",
        "specialty": "Терапевт",
        "preferred_date_time": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        "type": "offline",
    }


def test_create_appointment_success():
    app.dependency_overrides[get_task_service] = lambda: SuccessService()

    with TestClient(app) as client:
        response = client.post("/tasks/appointment", json=build_payload())

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["agent_id"] == "agent-1"


def test_create_appointment_returns_bad_request_for_business_error():
    app.dependency_overrides[get_task_service] = lambda: ValidationErrorService()

    with TestClient(app) as client:
        response = client.post("/tasks/appointment", json=build_payload())

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"]["output"] == "slot is already booked"


def test_create_appointment_returns_gateway_timeout():
    app.dependency_overrides[get_task_service] = lambda: TimeoutService()

    with TestClient(app) as client:
        response = client.post("/tasks/appointment", json=build_payload())

    app.dependency_overrides.clear()

    assert response.status_code == 504
    assert response.json()["detail"] == "task execution timed out"


def test_create_appointment_returns_service_unavailable():
    app.dependency_overrides[get_task_service] = lambda: UnavailableService()

    with TestClient(app) as client:
        response = client.post("/tasks/appointment", json=build_payload())

    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == "orchestrator not connected"


def test_create_appointment_returns_unprocessable_entity_for_invalid_body():
    app.dependency_overrides[get_task_service] = lambda: SuccessService()

    invalid_payload = build_payload()
    invalid_payload["full_name"] = ""

    with TestClient(app) as client:
        response = client.post("/tasks/appointment", json=invalid_payload)

    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_healthcheck():
    app.dependency_overrides[get_task_service] = lambda: SuccessService()

    with TestClient(app) as client:
        response = client.get("/health")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}