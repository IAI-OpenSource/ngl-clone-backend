from __future__ import annotations

from typing import Any


class EvolutionError(Exception):
    """Exception de base pour toutes les erreurs Evolution Go."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status={self.status_code}, msg={self})"


class EvolutionAuthError(EvolutionError):
    """API key invalide ou absente (HTTP 401/403)."""


class EvolutionNotFoundError(EvolutionError):
    """Ressource introuvable — instance, groupe, etc. (HTTP 404)."""


class EvolutionConnectionError(EvolutionError):
    """Impossible de joindre le serveur Evolution Go."""


class EvolutionInstanceError(EvolutionError):
    """Instance WhatsApp déconnectée ou dans un état invalide."""


class EvolutionRateLimitError(EvolutionError):
    """Trop de requêtes (HTTP 429)."""


class EvolutionNotInitializedError(EvolutionError):
    """Singleton non initialisé — appeler EvolutionAPIClient.initialize() d'abord."""
