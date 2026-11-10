from app.auth.interfaces.authentication_strategy import AuthenticationStrategy


class StrategyRegistry:
    """Registers and resolves authentication providers."""

    def __init__(self) -> None:
        self._strategies: dict[str, AuthenticationStrategy] = {}

    def register(self, strategy: AuthenticationStrategy) -> None:
        self._strategies[strategy.provider] = strategy

    def get(self, provider: str) -> AuthenticationStrategy:
        strategy = self._strategies.get(provider)

        if strategy is None:
            raise ValueError(f"Authentication provider '{provider}' is not supported.")

        return strategy
