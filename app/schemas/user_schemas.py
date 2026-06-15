## Ce fichier contient les différents schémas concernant les opérations
# sur la table utilisateur/user


from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field

from uuid import UUID

from app.db.models.enums.enums import SexeType, UserType
from app.schemas.globals.api_base_response import ApiBaseResponse, DefaultAppApiResponse


class CreateUser(BaseModel):
    """Schémas de validation de la création d'un utilisateur (Création de compte)"""

    username: str = Field(description="Nom d'utilisateur")
    password: str = Field(description="Mot de passe de l'utilisateur", min_length=8)
    sexe: SexeType = Field(description="Sexe de l'utilisateur")


class LoginData(BaseModel):
    """Schéma de validation des données de connexion (login)"""

    username: str = Field(description="Nom d'utilisateur")
    password: str = Field(description="Mot de passe de l'utilisateur")


class UpdateUserData(BaseModel):
    """Schéma de validation des données pour permettre à un utilisateur de mettre à jour"""

    username: Optional[str] = None
    sexe: Optional[SexeType] = None


class ReadUser(BaseModel):
    """Schémas de validation des infos d'un utilisateur"""

    id: UUID = Field(description="Identifiant de l'utilisateur")
    username: str
    sexe: SexeType
    role: UserType
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


ReadUser.model_rebuild()


class UserInfos(DefaultAppApiResponse[ReadUser]):
    """Infos sur un utilisateur"""


class ListUserInfos(DefaultAppApiResponse[List[ReadUser]]):
    """Liste des utilisateurs"""
