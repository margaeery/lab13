from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AppointmentRequest(BaseModel):
    full_name: str = Field(min_length=1)
    birth_date: str = Field(min_length=1)
    contact: str = Field(min_length=1)
    specialty: str = Field(min_length=1)
    preferred_date_time: datetime
    type: str = Field(min_length=1)


class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    success: bool
    output: Any = None
    agent_id: Optional[str] = None
    error: Optional[str] = None
