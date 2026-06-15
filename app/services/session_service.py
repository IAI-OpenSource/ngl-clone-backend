from logging import getLogger

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from asyncio import gather
from app.cache.base.cache_wrapper import CacheWrapper
from app.cache.session_cache import SessionCache
from app.globals.cache_duration import CacheDuration
from app.repositories.session_repository import SessionRepository
from app.schemas.session_schemas import CreateSession, ReadSession
from fastapi import status
from . import ServiceResult, DefaultAppServiceResult
from ..globals.businnes_error import AppError, AppErrorType
from ..globals.services_names import ServicesNames

logger = getLogger(__name__)


class SessionService:

    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.__db = db
        self.__session_cache = SessionCache(cache)
        self.__session_repo = SessionRepository(self.__db)
        self._service_name = ServicesNames.SESSION_SERVICE

    async def service_create_session(
        self, session_data: CreateSession
    ) -> DefaultAppServiceResult[ReadSession]:
        """Logique Métier concernant l'insertion d'une session en BD"""

        session_repo = await self.__session_repo.insert_session(
            session_data=session_data
        )

        if session_repo.is_error():
            logger.error(f"Erreur: {session_repo.error}")
            return session_repo.to_service_error(service_name=self._service_name)

        session_read = ReadSession.model_validate(session_repo.data)
        await self.__session_cache.set_session_in_cache(
            session_id=session_repo.data.id,
            session=session_read,
            ttl=CacheDuration.TWENTY_MINUTES,
        )

        return ServiceResult.service_success(
            data=session_read, status_code=session_repo.status_code
        )

    async def service_find_session_by_sid(
        self, sid: UUID
    ) -> DefaultAppServiceResult[ReadSession]:
        """Logique métier de récupération d'une session by SID"""

        session_cache_data = await self.__session_cache.get_session_from_cache(
            session_id=sid
        )

        if session_cache_data is not None and session_cache_data.is_valid_session():
            return ServiceResult.service_success(
                data=session_cache_data, status_code=status.HTTP_200_OK
            )

        bd_session = await self.__session_repo.get_session_by_sid(sid)

        if bd_session.is_error():
            logger.error(f"Erreur: {bd_session.error}")
            return bd_session.to_service_error(service_name=self._service_name)

        session_read = ReadSession.model_validate(bd_session.data)

        if not session_read.is_valid_session():
            delete_task = [
                self.__session_repo.delete_session(bd_session.data.id),
                self.__session_cache.invalid_session_in_cache(
                    session_id=bd_session.data.id
                ),
            ]
            results = await gather(*delete_task, return_exceptions=True)
            for i, task in enumerate(delete_task):
                if isinstance(results[i], Exception):
                    logger.warning(f"Échec suppression {i}: {results[i]}")

            return ServiceResult.service_failure(
                error=AppError(
                    error_type=AppErrorType.UNKNOWN_ERROR,
                    error_message="Invalid Session",
                ),
                status_code=status.HTTP_403_FORBIDDEN,
                service_name=self._service_name,
            )

        await self.__session_cache.set_session_in_cache(
            session_id=session_read.id,
            session=session_read,
            ttl=CacheDuration.TWENTY_MINUTES,
        )

        return ServiceResult.service_success(
            data=session_read,
            status_code=status.HTTP_200_OK,
        )

    async def revoke_session(self, sid: UUID) -> DefaultAppServiceResult[None]:
        """Logique métier pour révoquer une session"""

        update_session = await self.__session_repo.revoke_session(sid)

        if update_session.is_error():
            logger.error(f"Erreur: {update_session.error}")
            return update_session.to_service_error(service_name=self._service_name)

        await self.__session_cache.invalid_session_in_cache(session_id=sid)

        return ServiceResult.service_success(
            data=None,
            status_code=update_session.status_code,
        )
