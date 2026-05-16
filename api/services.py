from typing import Protocol

from orchestrator.models import Result, create_appointment_task
from orchestrator.orchestrator import Orchestrator

from .models import AppointmentRequest


class TaskService(Protocol):
    async def submit_appointment(self, request: AppointmentRequest) -> Result:
        ...


class OrchestratorTaskService:
    def __init__(self, orchestrator: Orchestrator):
        self.orchestrator = orchestrator

    async def submit_appointment(self, request: AppointmentRequest) -> Result:
        task = create_appointment_task(
            full_name=request.full_name,
            birth_date=request.birth_date,
            contact=request.contact,
            specialty=request.specialty,
            preferred_date_time=request.preferred_date_time,
            type_=request.type,
        )
        return await self.orchestrator.send_task(task)
