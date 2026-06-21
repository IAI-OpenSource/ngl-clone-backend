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
    description: Optional[str] = Field(None, description="Description du thread")
    wa_group_jid: str = Field(description="ID de groupe WhatsApp", max_length=100)
    wa_group_name: Optional[str] = Field(None, description="Nom du groupe WhatsApp", max_length=100)
    password: Optional[str] = Field(
        None,
        description="Mot de passe optionnel du thread",
        min_length=1,
        max_length=100,
    )


class UpdateThread(BaseModel):
    """Schéma pour la mise à jour d'un thread."""

    name: Optional[str] = Field(description="Nom du thread", min_length=1, max_length=100)
    description: Optional[str] = Field(description="Description du thread")
    wa_group_name: Optional[str] = Field(description="Nom du groupe WhatsApp", max_length=100)
    is_active: Optional[bool] = Field(description="Indique si le thread est actif")
    is_currently_locked: Optional[bool] = Field(description="Indique si le thread est actuellement bloqué pour les nouveaux messages")

class ThreadAuthPayload(BaseModel):
    thread_id: str
    slug: str
    exp: datetime

class ThreadAuthRequest(BaseModel):
    """Schéma pour la requête d'authentification d'un thread."""
    password: Optional[str] = Field(None, description="Mot de passe du thread si le thread en a un", min_length=1, max_length=100)

class ReadThread(BaseModel):
    """Schéma pour la lecture d'un thread - expose les champs nécessaires au front."""

    id: UUID = Field(description="ID unique du thread")
    name: str = Field(description="Nom du thread")
    slug: str = Field(description="Slug unique du thread")
    description: Optional[str] = Field(None, description="Description du thread")
    wa_group_jid: str = Field(description="ID de groupe WhatsApp")
    wa_group_name: Optional[str] = Field(None, description="Nom du groupe WhatsApp")
    is_active: bool = Field(description="Indique si le thread est actif")
    is_currently_locked: bool = Field(default=False, description="Indique si le thread est actuellement bloqué pour les nouveaux messages")
    last_wa_sync_at: Optional[datetime] = Field(None, description="Dernière synchronisation WhatsApp")
    created_at: datetime = Field(description="Date de création du thread")
    updated_at: datetime = Field(description="Date de dernière mise à jour du thread")
    has_password: bool =Field(default=False, description="Indique si le thread est protégé par un mot de passe, "
                                                        "donc si c'est True tu affiche une dialog pour rentrer le mot "
                                                        "de passe, sinon tu peux directement se connecter au thread")

    model_config = ConfigDict(from_attributes=True)


ReadThread.model_rebuild()

class ReadThreadWithUserConnectionInfo(ReadThread):
    """Schéma pour la lecture d'un thread avec les infos de connexion de l'utilisateur."""

    is_connected: bool = Field(default=False, description="Indique si l'utilisateur est connecté à ce thread")

class InternalReadThread(BaseModel):
    """Schéma interne pour la lecture d'un thread - expose tous les champs nécessaires au back."""

    id: UUID = Field(description="ID unique du thread")
    name: str = Field(description="Nom du thread")
    slug: str = Field(description="Slug unique du thread")
    description: Optional[str] = Field(description="Description du thread")
    wa_group_jid: str = Field(description="ID de groupe WhatsApp")
    wa_group_name: Optional[str] = Field(description="Nom du groupe WhatsApp")
    is_active: bool = Field(description="Indique si le thread est actif")
    is_currently_locked: bool = Field(default=False, description="Indique si le thread est actuellement bloqué pour les nouveaux messages")
    last_wa_sync_at: Optional[datetime] = Field(
        description="Dernière synchronisation WhatsApp"
    )
    created_at: datetime = Field(description="Date de création du thread")
    updated_at: datetime = Field(description="Date de dernière mise à jour du thread")
    password_hash: Optional[str] = Field(None, description="Hash du mot de passe du thread")

    model_config = ConfigDict(from_attributes=True)

InternalReadThread.model_rebuild()


# Schémas enveloppes pour les réponses API
class ThreadInfos(DefaultAppApiResponse[ReadThread]):
    """Schéma enveloppe pour un thread unique."""

class ThreadWithUserConnectionInfo(DefaultAppApiResponse[ReadThreadWithUserConnectionInfo]):
    """Schéma enveloppe pour un thread unique avec les infos de connexion de l'utilisateur."""

class ListThreadsInfos(DefaultAppApiResponse[List[ReadThreadWithUserConnectionInfo]]):
    """Schéma enveloppe pour une liste de threads."""
