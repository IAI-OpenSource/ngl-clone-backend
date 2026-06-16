"""
Schémas Pydantic pour les messages (messages).
Ces schémas définissent quels attributs sont exposés au front.
"""
import re
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums.enums import WAStatus
from app.schemas.globals.api_base_response import DefaultAppApiResponse
from app.utils.security_utils import has_too_many_repeated_chars


class CreateMessage(BaseModel):
    """Schéma pour la création d'un message."""

    content: str = Field(description="Contenu du message", min_length=1, max_length=500)

    @classmethod
    def validate_content(cls, value: str) -> str:
        # Message vide ou uniquement des espaces
        if not value or not value.strip():
            raise ValueError("Le message ne peut pas être vide.")

        # Liens
        url_pattern = re.compile(
            r"(https?://|www\.|[a-zA-Z0-9-]+\.(com|net|org|io|dev|fr|tg|edu)\b)",
            re.IGNORECASE,
        )

        if url_pattern.search(value):
            raise ValueError("Pas de lien ici tchaléééééé")

        repeated_chars_pattern = re.compile(r"(.)\1{7,}")

        if repeated_chars_pattern.search(value) or has_too_many_repeated_chars(value):
            raise ValueError("Soit plus sérieux orrrrrrrrrrrrh")

        return value


class UpdateMessage(BaseModel):
    """Schéma pour la mise à jour d'un message."""

    content: Optional[str] = Field(description="Contenu du message", min_length=1)
    is_hidden: Optional[bool] = Field(description="Indique si le message est masqué")
    hidden_reason: Optional[str] = Field(description="Raison du masquage du message")


class ReadMessage(BaseModel):
    """Schéma pour la lecture d'un message - expose les champs nécessaires au front."""

    id: UUID = Field(description="ID unique du message")
    thread_id: UUID = Field(description="ID du thread auquel le message appartient")
    content: str = Field(description="Contenu du message")
    wa_message_id: Optional[str] = Field(description="ID du message WhatsApp")
    wa_status: WAStatus = Field(description="Statut de synchronisation WhatsApp")
    wa_forwarded_at: Optional[datetime] = Field(description="Date de transfert WhatsApp")
    is_hidden: bool = Field(description="Indique si le message est masqué")
    hidden_reason: Optional[str] = Field(description="Raison du masquage du message")
    created_at: datetime = Field(description="Date de création du message")

    model_config = ConfigDict(from_attributes=True)


ReadMessage.model_rebuild()


# Schémas enveloppes pour les réponses API
class MessageInfos(DefaultAppApiResponse[ReadMessage]):
    """Schéma enveloppe pour un message unique."""


class ListMessagesInfos(DefaultAppApiResponse[List[ReadMessage]]):
    """Schéma enveloppe pour une liste de messages."""
