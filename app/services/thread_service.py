from logging import getLogger
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.thread_cache import ThreadCache
from app.globals.cache_duration import CacheDuration
from app.repositories.thread_repository import ThreadRepository
from app.schemas.thread_schemas import ReadThread

from . import ServiceResult, DefaultAppServiceResult
from ..cache.base.cache_wrapper import CacheWrapper
from ..globals.services_names import ServicesNames

logger = getLogger(__name__)


class ThreadService:

    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.__db = db
        self.__thread_cache = ThreadCache(cache)
        self.__thread_repo = ThreadRepository(self.__db)
        self._service_name = ServicesNames.THREAD_SERVICE

    async def service_find_thread_by_id(
        self, thread_id: UUID
    ) -> DefaultAppServiceResult[ReadThread]:
        """Logique métier de récupération d'un thread par ID."""

        thread_from_cache = await self.__thread_cache.get_thread_from_cache(
            thread_id=thread_id
        )

        if thread_from_cache is not None:
            return ServiceResult.service_success(data=thread_from_cache)

        thread_repo = await self.__thread_repo.get_thread_by_id(thread_id=thread_id)

        if thread_repo.is_error():
            logger.error(f"Erreur: {thread_repo.error}")
            return thread_repo.to_service_error(service_name=self._service_name)

        read_thread = ReadThread.model_validate(thread_repo.data)

        await self.__thread_cache.set_thread_in_cache(
            thread=read_thread, ttl=CacheDuration.TWENTY_MINUTES
        )

        return ServiceResult.service_success(
            data=read_thread,
            service_name=self._service_name,
        )

    async def service_find_thread_by_slug(
        self, slug: str
    ) -> DefaultAppServiceResult[ReadThread]:
        """Logique métier de récupération d'un thread par slug."""

        thread_repo = await self.__thread_repo.get_thread_by_slug(slug=slug)

        if thread_repo.is_error():
            logger.error(f"Erreur: {thread_repo.error}")
            return thread_repo.to_service_error(service_name=self._service_name)

        read_thread = ReadThread.model_validate(thread_repo.data)

        await self.__thread_cache.set_thread_in_cache(
            thread=read_thread, ttl=CacheDuration.TWENTY_MINUTES
        )

        return ServiceResult.service_success(
            data=read_thread,
            service_name=self._service_name,
        )

    async def service_find_all_threads(self) -> DefaultAppServiceResult[list[ReadThread]]:
        """Logique métier de récupération de tous les threads."""

        threads_from_cache = await self.__thread_cache.get_threads_list_from_cache()

        if threads_from_cache is not None:
            return ServiceResult.service_success(
                data=threads_from_cache,
                service_name=self._service_name,
            )

        thread_repo = await self.__thread_repo.get_all_threads()

        if thread_repo.is_error():
            logger.error(f"Erreur: {thread_repo.error}")
            return thread_repo.to_service_error(service_name=self._service_name)

        read_threads = [ReadThread.model_validate(thread) for thread in thread_repo.data]

        await self.__thread_cache.set_threads_list_in_cache(
            threads=read_threads, ttl=CacheDuration.TWENTY_MINUTES
        )

        return ServiceResult.service_success(
            data=read_threads,
            service_name=self._service_name,
        )
