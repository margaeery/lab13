import os

from fastapi import Request

from orchestrator.orchestrator import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, Orchestrator

from .services import OrchestratorTaskService, TaskService


def create_orchestrator() -> Orchestrator:
    timeout = float(os.getenv("ORCHESTRATOR_TIMEOUT", DEFAULT_TIMEOUT))
    max_retries = int(os.getenv("ORCHESTRATOR_MAX_RETRIES", DEFAULT_MAX_RETRIES))
    nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
    return Orchestrator(nats_url=nats_url, timeout=timeout, max_retries=max_retries)


def get_task_service(request: Request) -> TaskService:
    return OrchestratorTaskService(request.app.state.orchestrator)
