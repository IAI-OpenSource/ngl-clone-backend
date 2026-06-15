## fichier contenant le repository de la table user
## vous y trouverez les requetes base de donnée

from dataclasses import dataclass
from datetime import UTC, datetime
from logging import getLogger
from uuid import UUID


from app.utils.security_utils import hasher_password
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.schemas.user_schemas import (
    CreateUser,
    UpdateUserData,
)
from app.repositories import DefaultAppCrudResult, CrudResult
from fastapi import status

from .helpers.repositories_utils import RepositoriesUtils
from ..db.models.enums.enums import UserType
from ..globals.businnes_error import AppError, AppErrorType

logger = getLogger(__name__)


@dataclass
class UserRepository:

    db: AsyncSession

    async def insert_user(
        self, user_data: CreateUser, is_admin: bool = False
    ) -> DefaultAppCrudResult[User]:
        """Fonction pour insérer un utilisateur dans la base de donnée"""

        try:
            user = User(
                password_hash=hasher_password(user_data.password),
                username=user_data.username,
                sexe=user_data.sexe,
            )
            if is_admin:
                user.role = UserType.ADMIN

            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)

            logger.info("Utilisateur ajoutée avec succès !")
            return CrudResult.crud_success(
                data=user, status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, User
            )

    async def get_user_by_id(self, user_id: UUID) -> DefaultAppCrudResult[User]:
        """Fonction pour récupérer un utilisateur à partir de son ID"""

        try:

            stmt = select(User).where(User.id == user_id).where(User.deleted_at == None)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                logger.info("Utilisateur non Trouvé")
                return CrudResult.crud_failure(
                    AppError(
                        error_type=AppErrorType.NOT_FOUND,
                        error_message="Utilisateur inexistant",
                    ),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=user)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_user_by_username(self, username: str) -> DefaultAppCrudResult[User]:
        """Fonction pour récupérer un utilisateur à partir de son nom d'utilisateur"""

        try:
            stmt = select(User).where(User.username == username).where(User.deleted_at == None)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if user is None:
                logger.info("Utilisateur non Trouvé")
                return CrudResult.crud_failure(
                    AppError(
                        error_type=AppErrorType.NOT_FOUND,
                        error_message="Utilisateur inexistant",
                    ),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=user)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_all_users(self) -> DefaultAppCrudResult[list[User]]:
        """Fonction pour récupérer tous les utilisateurs de la base de donnée"""

        try:
            stmt = select(User).where(User.deleted_at == None)

            result = await self.db.execute(stmt)
            users = list(result.scalars().all())

            return CrudResult.crud_success(data=users)
        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, User
            )

    async def update_user(
        self, user_id: UUID, user_update_data: UpdateUserData
    ) -> DefaultAppCrudResult[User]:
        """Fonction pour mettre à jour un utilisateur dans la base de donnée"""

        try:

            old_user = await self.get_user_by_id(user_id=user_id)

            if old_user.is_error():
                return old_user

            if user_update_data.username:
                old_user.data.username = user_update_data.username

            if user_update_data.sexe:
                old_user.data.sexe = user_update_data.sexe

            old_user.data.updated_at = datetime.now(UTC)

            await self.db.commit()

            logger.info("Utilisateur mis à jour avec succès")
            return CrudResult.crud_success(data=old_user.data)
        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, User
            )
