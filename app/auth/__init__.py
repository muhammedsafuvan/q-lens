from functools import lru_cache

from app.auth.registry import StrategyRegistry
from app.auth.service import AuthenticationService
from app.auth.strategies.google_oidc import GoogleOIDCStrategy


@lru_cache
def get_authentication_service() -> AuthenticationService:
    registry = StrategyRegistry()

    registry.register(GoogleOIDCStrategy())

    return AuthenticationService(registry)
