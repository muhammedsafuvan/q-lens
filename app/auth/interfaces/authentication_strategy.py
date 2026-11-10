from abc import ABC, abstractmethod
from typing import Any

from fastapi import Request
from starlette.responses import RedirectResponse


class AuthenticationStrategy(ABC):
    """Abstract strategy for external identity providers."""

    @property
    @abstractmethod
    def provider(self) -> str:
        """Return the provider identifier."""
        raise NotImplementedError

    @abstractmethod
    async def authorization_redirect(
        self,
        request: Request,
        redirect_uri: str,
    ) -> RedirectResponse:
        """Redirect the user to the identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def authenticate_callback(
        self,
        request: Request,
    ) -> dict[str, Any]:
        """Validate the provider callback and return verified identity data."""
        raise NotImplementedError
