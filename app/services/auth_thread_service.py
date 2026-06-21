from datetime import datetime, timezone, timedelta
from logging import getLogger
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.thread_cache import ThreadCache
from app.globals.cache_duration import CacheDuration
from app.repositories.thread_repository import ThreadRepository
from starlette.requests import HTTPConnection
from app.auth.cookie_manager import CookieManager
from app.auth.jwt_manager import JWTManager
from fastapi import Response
from app.core.config import (
    JWT_THREAD_ACCESS_ID,
    ACCESS_SECRET_KEY,
    REFRESH_TOKEN_EXPIRES_SECONDES,
)
from app.globals.businnes_error import AppError, AppErrorType
from app.schemas.globals.utils_schemas import StringMessage
from app.schemas.thread_schemas import InternalReadThread, ThreadAuthPayload
from app.utils.security_utils import verify_password

from . import ServiceResult, DefaultAppServiceResult
from ..cache.base.cache_wrapper import CacheWrapper
from ..globals.services_names import ServicesNames

logger = getLogger(__name__)

TOKEN_TTL = timedelta(days=7)


class AuthThreadService:

    def __init__(self, db: AsyncSession,
                 cache: CacheWrapper,
                 response: Response,
                 request: HTTPConnection,):
        self.__db = db
        self.__thread_cache = ThreadCache(cache)
        self.__thread_repo = ThreadRepository(self.__db)
        self.__cookie_manager = CookieManager(response=response, request=request)

        self._service_name = ServicesNames.THREAD_SERVICE

    async def service_connect_thread(
        self, thread_id: UUID, thread_password: str | None = None
    ) -> DefaultAppServiceResult[StringMessage]:
        """Logique métier de connexion à un thread (récupération du thread et de ses messages)."""

        searched_thread: InternalReadThread

        cache_res = await self.__thread_cache.get_raw_thread_from_cache(thread_id)

        if cache_res is not None:
            searched_thread = cache_res
        else:
            thread_repo = await self.__thread_repo.get_thread_by_id(thread_id=thread_id)

            if thread_repo.is_error():
                logger.error(f"Erreur: {thread_repo.error}")
                return thread_repo.to_service_error(service_name=self._service_name)

            searched_thread = InternalReadThread.model_validate(
                thread_repo.data
            )

            await self.__thread_cache.set_raw_thread_in_cache(
                thread=searched_thread, ttl=CacheDuration.TWENTY_MINUTES
            )


        if searched_thread.password_hash and (thread_password is None or not verify_password(
                thread_password, searched_thread.password_hash
        )):
            logger.error(
                f"Erreur: Mot de passe incorrect pour le thread {thread_id}"
            )
            return ServiceResult.service_failure(
                service_name=self._service_name,
                status_code=400,
                error=AppError(
                    error_type=AppErrorType.LOCKED_CONTENT,
                    error_message="Mot de passe incorrect pour ce thread frérot",
                ),
            )

        access_token = JWTManager.create_access_token(
            data_to_encode=ThreadAuthPayload(
                thread_id=str(searched_thread.id),
                slug=searched_thread.slug,
                exp=datetime.now(timezone.utc) + TOKEN_TTL,
            ).model_dump(),
            enc_dec_key=ACCESS_SECRET_KEY,
        )

        self.__cookie_manager.add_cookie(
            cookie_id=JWT_THREAD_ACCESS_ID,
            value=access_token,
            age=REFRESH_TOKEN_EXPIRES_SECONDES,
        )


        return ServiceResult.service_success(
            data=StringMessage(message="Connexion au thread réusssi"),
            service_name=self._service_name,
        )
