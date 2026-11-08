from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DemoJobRequest(BaseModel):
    duration_seconds: int = Field(
        default=3,
        ge=1,
        le=30,
        description="Simulated job duration in seconds",
    )


class JobEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    task_id: str
    task_name: str
    event_type: str
    occurred_at: datetime

    worker_name: str | None = None
    queue_name: str | None = None
    attempt: int

    exception_type: str | None = None
    exception_message: str | None = None
    traceback: str | None = None

    exchange: str | None = None
    routing_key: str | None = None


class JobSummary(BaseModel):
    task_id: str
    task_name: str
    status: str
    occurred_at: datetime

    worker_name: str | None = None
    queue_name: str | None = None
    attempt: int

    exception_type: str | None = None
    exception_message: str | None = None

    exchange: str | None = None
    routing_key: str | None = None


class JobDetail(BaseModel):
    task_id: str
    task_name: str
    status: str
    events: list[JobEventResponse]


class JobListResponse(BaseModel):
    items: list[JobSummary]
    total: int = Field(ge=0)