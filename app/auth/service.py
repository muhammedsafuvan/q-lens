from typing import Any

from fastapi import HTTPException, Request, status
from starlette.responses import RedirectResponse

from app.auth.registry import StrategyRegistry


class AuthenticationService:
    """Coordinates authentication through registered strategies."""

    def __init__(self, registry: StrategyRegistry) -> None:
        self.registry = registry

    def get_strategy(self, provider: str):
        try:
            return self.registry.get(provider)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    async def authorization_redirect(
        self,
        provider: str,
        request: Request,
        redirect_uri: str,
    ) -> RedirectResponse:
        strategy = self.get_strategy(provider)

        return await strategy.authorization_redirect(
            request,
            redirect_uri,
        )

    async def authenticate_callback(
        self,
        provider: str,
        request: Request,
    ) -> dict[str, Any]:
        strategy = self.get_strategy(provider)

        return await strategy.authenticate_callback(request)
