from pydantic import BaseModel, Field

from app.schemas.globals.api_base_response import ApiBaseResponse
from app.globals.businnes_error import AppError


class StringMessage(BaseModel):
    """Schémas pydantic pour le retour d'un message de type String"""

    message: str = Field(
        description="Le message de réponse relatif au résultat de l'opération, ce message là sera"
        " forcément pour un succès, si c'est echec ca sera dans le champ 'error'"
    )


class GlobalStringResponse(ApiBaseResponse[StringMessage, AppError]):
    """
    Réponse contennant uniquement un message de type string, utiliser pour les endpoints qui ne retournent
    pas de données spécifiques, mais juste un message de succès
    """
