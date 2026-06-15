from pydantic import BaseModel, Field

from app.schemas.globals.api_base_response import DefaultAppApiResponse


class AuthErrorMessage(BaseModel):
    detail: str = Field(
        description="Message d'erreur en cas de probleme d'authentification ou d'autorisation"
    )


class InternalServerErrorSchema(DefaultAppApiResponse[None]):
    """Schéma de réponse pour les erreurs internes du serveur (500 Internal Server Error)"""

    success: bool = Field(False)
    status_code: int = Field(default=500)
