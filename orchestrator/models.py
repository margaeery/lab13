from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
import uuid


@dataclass
class Task:
    id: str
    type: str
    payload: dict

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            type=data["type"],
            payload=data["payload"],
        )


@dataclass
class Result:
    task_id: str
    success: bool
    output: Any
    agent_id: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Result":
        return cls(
            task_id=data["task_id"],
            agent_id=data.get("agent_id"),
            success=data["success"],
            output=data.get("output"),
            error=data.get("error"),
        )


def create_appointment_task(
    full_name: str,
    birth_date: str,
    contact: str,
    specialty: str,
    preferred_date_time: datetime,
    type_: str,
) -> Task:
    return Task(
        id=str(uuid.uuid4()),
        type="appointment",
        payload={
            "full_name": full_name,
            "birth_date": birth_date,
            "contact": contact,
            "specialty": specialty,
            "preferred_date_time": preferred_date_time.isoformat(),
            "type": type_,
        },
    )
