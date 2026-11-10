import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("API key name cannot be empty.")

        return value


class APIKeyCreatedResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    key: str
    key_prefix: str
    created_at: datetime


class APIKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by_user_id: uuid.UUID | None
    name: str
    key_prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class APIKeyRevokeRequest(BaseModel):
    revoked: Literal[True]
