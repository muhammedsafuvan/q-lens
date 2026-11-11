from uuid import UUID

from pydantic import BaseModel, Field


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    id: UUID
    email: str
    name: str | None
    avatar_url: str | None
    workspace_id: UUID
