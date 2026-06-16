"""
Schémas Pydantic pour les threads (groupes de discussion).
Ces schémas définissent quels attributs sont exposés au front.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.globals.api_base_response import DefaultAppApiResponse


class CreateThread(BaseModel):
    """Schéma pour la création d'un thread."""

    name: str = Field(description="Nom du thread", min_length=1, max_length=100)
    slug: str = Field(description="Slug unique du thread", min_length=1, max_length=50)
    description: Optional[str] = Field(description="Description du thread")
    wa_group_jid: str = Field(description="ID de groupe WhatsApp", max_length=100)
    wa_group_name: Optional[str] = Field(description="Nom du groupe WhatsApp", max_length=100)
    password_hash: str = Field(description="Hash du mot de passe du thread")


class UpdateThread(BaseModel):
    """Schéma pour la mise à jour d'un thread."""

    name: Optional[str] = Field(description="Nom du thread", min_length=1, max_length=100)
    description: Optional[str] = Field(description="Description du thread")
    wa_group_name: Optional[str] = Field(description="Nom du groupe WhatsApp", max_length=100)
    is_active: Optional[bool] = Field(description="Indique si le thread est actif")

class ThreadAuthPayload(BaseModel):
    thread_id: str
    slug: str
    exp: datetime

class ThreadAuthRequest(BaseModel):
    """Schéma pour la requête d'authentification d'un thread."""
    password: Optional[str] = Field(description="Mot de passe du thread si le thread en a un", min_length=1, max_length=100)

class ReadThread(BaseModel):
    """Schéma pour la lecture d'un thread - expose les champs nécessaires au front."""

    id: UUID = Field(description="ID unique du thread")
    name: str = Field(description="Nom du thread")
    slug: str = Field(description="Slug unique du thread")
    description: Optional[str] = Field(description="Description du thread")
    wa_group_jid: str = Field(description="ID de groupe WhatsApp")
    wa_group_name: Optional[str] = Field(description="Nom du groupe WhatsApp")
    is_active: bool = Field(description="Indique si le thread est actif")
    last_wa_sync_at: Optional[datetime] = Field(description="Dernière synchronisation WhatsApp")
    created_at: datetime = Field(description="Date de création du thread")
    updated_at: datetime = Field(description="Date de dernière mise à jour du thread")

    model_config = ConfigDict(from_attributes=True)


ReadThread.model_rebuild()

class InternalForLoginReadThread(BaseModel):
    """"""
    id: UUID = Field(description="ID unique du thread")
    name: str = Field(description="Nom du thread")
    slug: str = Field(description="Slug unique du thread")
    description: Optional[str] = Field(description="Description du thread")
    wa_group_jid: str = Field(description="ID de groupe WhatsApp")
    wa_group_name: Optional[str] = Field(description="Nom du groupe WhatsApp")
    is_active: bool = Field(description="Indique si le thread est actif")
    last_wa_sync_at: Optional[datetime] = Field(
        description="Dernière synchronisation WhatsApp"
    )
    created_at: datetime = Field(description="Date de création du thread")
    updated_at: datetime = Field(description="Date de dernière mise à jour du thread")
    password_hash: str = Field(description="Hash du mot de passe du thread")

    model_config = ConfigDict(from_attributes=True)

InternalForLoginReadThread.model_rebuild()


# Schémas enveloppes pour les réponses API
class ThreadInfos(DefaultAppApiResponse[ReadThread]):
    """Schéma enveloppe pour un thread unique."""


class ListThreadsInfos(DefaultAppApiResponse[List[ReadThread]]):
    """Schéma enveloppe pour une liste de threads."""
