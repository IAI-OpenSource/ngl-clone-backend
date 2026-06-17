"""
Schémas Pydantic pour les membres (members).
Ces schémas définissent quels attributs sont exposés au front.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.globals.api_base_response import DefaultAppApiResponse


class CreateMember(BaseModel):
    """Schéma pour la création d'un membre."""

    wa_jid: str = Field(description="ID WhatsApp unique du membre", max_length=100)
    wa_name: Optional[str] = Field(description="Nom WhatsApp du membre", max_length=100)
    display_name: Optional[str] = Field(description="Nom d'affichage du membre", max_length=100)
    phone_number: Optional[str] = Field(description="Numéro de téléphone du membre", max_length=20)
    avatar_url: Optional[str] = Field(description="URL de l'avatar du membre")


class UpdateMember(BaseModel):
    """Schéma pour la mise à jour d'un membre."""

    wa_name: Optional[str] = Field(description="Nom WhatsApp du membre", max_length=100)
    display_name: Optional[str] = Field(description="Nom d'affichage du membre", max_length=100)
    phone_number: Optional[str] = Field(description="Numéro de téléphone du membre", max_length=20)
    avatar_url: Optional[str] = Field(description="URL de l'avatar du membre")
    is_active: Optional[bool] = Field(description="Indique si le membre est actif")


class ReadMember(BaseModel):
    """Schéma pour la lecture d'un membre - expose les champs nécessaires au front."""

    id: UUID = Field(description="ID unique du membre")
    wa_jid: str = Field(description="ID WhatsApp unique du membre")
    wa_name: Optional[str] = Field(description="Nom WhatsApp du membre")
    display_name: Optional[str] = Field(description="Nom d'affichage du membre")
    phone_number: Optional[str] = Field(description="Numéro de téléphone du membre")
    avatar_url: Optional[str] = Field(description="URL de l'avatar du membre")
    is_active: bool = Field(description="Indique si le membre est actif")
    created_at: datetime = Field(description="Date de création du membre")
    updated_at: datetime = Field(description="Date de dernière mise à jour du membre")

    model_config = ConfigDict(from_attributes=True)


ReadMember.model_rebuild()


# Schémas enveloppes pour les réponses API
class MemberInfos(DefaultAppApiResponse[ReadMember]):
    """Schéma enveloppe pour un membre unique."""


class ListMembersInfos(DefaultAppApiResponse[List[ReadMember]]):
    """Schéma enveloppe pour une liste de membres."""
