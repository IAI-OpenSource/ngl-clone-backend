from logging import getLogger
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.cache.user_cache import UserCache
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import (
    CreateUser,
    ReadUser,
    UpdateUserData,
)
from app.globals.cache_duration import CacheDuration

from . import ServiceResult, DefaultAppServiceResult
from ..cache.base.cache_wrapper import CacheWrapper
from ..globals.services_names import ServicesNames

logger = getLogger(__name__)


class UserService:

    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.__db = db
        self.__user_cache = UserCache(cache)
        self.__user_repo = UserRepository(self.__db)
        self._service_name = ServicesNames.USER_SERVICE

    ## -------------- Logique find user by id ------------------ ##
    async def service_find_user_by_id(
        self, user_id: UUID
    ) -> DefaultAppServiceResult[ReadUser]:
        """Logique métier de récupération d'un utilisateur par ID"""

        ## on cherche dans le cache d'abord
        user_data_from_cache = await self.__user_cache.get_user_from_cache(
            user_id=user_id
        )

        if user_data_from_cache is not None:
            return ServiceResult.service_success(
                data=user_data_from_cache,
            )

        ## si le cache est vide, on fait la requete BD
        user = await self.__user_repo.get_user_by_id(user_id=user_id)

        if user.is_error():
            logger.error(f"Erreur: {user.error}")
            return user.to_service_error(service_name=self._service_name)

        user_read = ReadUser.model_validate(user.data)

        await self.__user_cache.set_user_in_cache(
            user=user_read, ttl=CacheDuration.TWENTY_MINUTES
        )

        return ServiceResult.service_success(
            data=user_read,
            service_name=self._service_name,
        )

    ## -------------- Logique métier de création d'utilisateur ------------------ ##
    async def service_create_user(
        self, user_data: CreateUser
    ) -> DefaultAppServiceResult[ReadUser]:
        """Logique métier pour gérer la création d'un utilisateur"""

        db_user = await self.__user_repo.insert_user(user_data=user_data)

        if db_user.is_error():
            return db_user.to_service_error(service_name=self._service_name)

        read_user = ReadUser.model_validate(db_user.data)

        await self.__user_cache.set_user_in_cache(
            user=read_user,
            ttl=CacheDuration.TWENTY_MINUTES,
        )

        return ServiceResult.service_success(
            data=read_user,
            status_code=db_user.status_code,
            service_name=self._service_name,
        )

    ## -------------- Logique métier pour récupérer tous les utilisateurs ------------------ ##
    async def service_get_all_users(self) -> DefaultAppServiceResult[list[ReadUser]]:
        """Logique métier pour gérer la récupération de tous les utilisateurs"""

        users_repo = await self.__user_repo.get_all_users()

        if users_repo.is_error():
            return users_repo.to_service_error(service_name=self._service_name)

        return ServiceResult.service_success(
            data=[ReadUser.model_validate(user) for user in users_repo.data],
            service_name=self._service_name,
        )

    ## -------------- Logique métier pour mettre à jour les infos d'un utilisateur ------------------ ##
    async def service_update_user(
        self, user_id: UUID, user_update_data: UpdateUserData
    ) -> ServiceResult[ReadUser]:
        """Logique métier pour mettre à jour les informations d'un utilisateur"""

        new_user = await self.__user_repo.update_user(
            user_id=user_id, user_update_data=user_update_data
        )

        if new_user.is_error():
            return new_user.to_service_error(service_name=self._service_name)

        user_read = ReadUser.model_validate(new_user.data)

        await self.__user_cache.set_user_in_cache(
            user=user_read,
            ttl=CacheDuration.TWENTY_MINUTES,
        )

        return ServiceResult.service_success(
            data=user_read,
            service_name=self._service_name,
        )
