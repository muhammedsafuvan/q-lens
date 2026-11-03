from pydantic import BaseModel, Field


class DemoJobRequest(BaseModel):
    duration_seconds: int = Field(
        default=3,
        ge=1,
        le=30,
        description="Simulated job duration in seconds",
    )
