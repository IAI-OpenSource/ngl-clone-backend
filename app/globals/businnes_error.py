from enum import Enum

from pydantic import BaseModel, Field


class AppErrorType(str, Enum):
    LOCKED_CONTENT = "LOCKED_CONTENT"
    NOT_FOUND = "NOT_FOUND"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"


class AppError(BaseModel):
    """Modèle de données pour représenter une erreur métier."""

    error_type: AppErrorType = Field(
        title="Type d'erreur métier",
        description="Le type d'erreur métier qui s'est produite, utilisé pour catégoriser les"
        " erreurs et faciliter la gestion des erreurs dans coté frontend",
    )

    error_message: str = Field(
        title="Champ des erreurs affichable directement à l'utilisateur (Texte User friendly)",
        description="Présent seulement si la requete à échouée ou si quelque chose s'est mal pa"
        "ssé durant le traitement",
    )

    def __str__(self):
        return f"AppError(type={self.error_type}, message={self.error_message})"
