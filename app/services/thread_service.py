from logging import getLogger
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.thread_cache import ThreadCache
from app.globals.cache_duration import CacheDuration
from app.repositories.thread_repository import ThreadRepository
from app.repositories.thread_member_repository import ThreadMemberRepository
from app.schemas.thread_schemas import (
    CreateThread,
    ReadThread,
    ReadThreadWithUserConnectionInfo,
)
from app.schemas.member_schemas import ReadMember
from app.db.models.thread import Thread
from app.globals.businnes_error import AppError, AppErrorType
from app.schemas.thread_schemas import ThreadAuthPayload

from . import ServiceResult, DefaultAppServiceResult
from ..cache.base.cache_wrapper import CacheWrapper
from ..globals.services_names import ServicesNames

logger = getLogger(__name__)


class ThreadService:

    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.__db = db
        self.__thread_cache = ThreadCache(cache)
        self.__thread_repo = ThreadRepository(self.__db)
        self.__thread_member_repo = ThreadMemberRepository(self.__db)
        self._service_name = ServicesNames.THREAD_SERVICE

    @staticmethod
    def _build_read_thread_schemas(thread_bd_data : Thread) -> ReadThread:
        th = ReadThread.model_validate(thread_bd_data)
        if thread_bd_data.password_hash is not None:
            th.has_password = True

        return th

    async def verify_can_interract_with_thread(
        self, thread: ReadThread | Thread | UUID, user_token: ThreadAuthPayload
    ) -> DefaultAppServiceResult[None]:
        usable_thread: ReadThread
        if isinstance(thread, UUID):
            read_request = await self.service_find_thread_by_id(thread_id=thread)
            if read_request.is_error():
                return ServiceResult.service_failure(error=AppError(
                error_message=read_request.error.error_message,
                error_type=read_request.error.error_type
            ), status_code=read_request.status_code)
            usable_thread = read_request.data
        elif isinstance(thread, Thread):
            usable_thread = self._build_read_thread_schemas(thread)
        elif isinstance(thread, ReadThread):
            usable_thread = thread
        else:
            logger.error(f"Type de thread non supporté: {type(thread)}")
            return ServiceResult.service_failure(error=AppError(
                error_message="pffffffffffff",
                error_type=AppErrorType.UNKNOWN_ERROR
            ), status_code=400)

        if usable_thread.has_password and str(usable_thread.id) != user_token.thread_id:
            logger.error(f"Thread {usable_thread.id} a un mot de passe et l'utilisateur n'a pas le bon token.")
            return ServiceResult.service_failure(error=AppError(
                error_message="Tu ne peux pas communiquer avec ce thread poto, connecte toii au thread d'bord",
                error_type=AppErrorType.LOCKED_CONTENT
            ), status_code=400)
        return ServiceResult.service_success(data=None)

    async def verify_thread_allows_posting(
        self, thread: ReadThread | Thread | UUID
    ) -> DefaultAppServiceResult[None]:
        """Vérifie si le thread autorise la création de nouveaux messages (non verrouillé)."""
        usable_thread: ReadThread
        if isinstance(thread, UUID):
            read_request = await self.service_find_thread_by_id(thread_id=thread)
            if read_request.is_error():
                return ServiceResult.service_failure(error=AppError(
                    error_message=read_request.error.error_message,
                    error_type=read_request.error.error_type
                ), status_code=read_request.status_code)
            usable_thread = read_request.data
        elif isinstance(thread, Thread):
            usable_thread = self._build_read_thread_schemas(thread)
        elif isinstance(thread, ReadThread):
            usable_thread = thread
        else:
            logger.error(f"Type de thread non supporté pour vérification du verrouillage: {type(thread)}")
            return ServiceResult.service_failure(error=AppError(
                error_message="Type de thread non supporté",
                error_type=AppErrorType.UNKNOWN_ERROR
            ), status_code=400)

        if getattr(usable_thread, "is_currently_locked", False):
            logger.info(f"Thread {usable_thread.id} est actuellement verrouillé. Opération interdite.")
            return ServiceResult.service_failure(error=AppError(
                error_message="Ce thread est actuellement bloqué, vous ne pouvez pas poster de nouveaux messages.",
                error_type=AppErrorType.LOCKED_CONTENT
            ), status_code=400)

        return ServiceResult.service_success(data=None)

    @staticmethod
    def _verify_user_connected_to_thread(
        thread: ReadThread, user_token: ThreadAuthPayload | None
    ) -> ReadThreadWithUserConnectionInfo:
        res = ReadThreadWithUserConnectionInfo.model_validate(thread)
        if user_token is not None and user_token.thread_id == str(thread.id):
            res.is_connected = True
        return res

    async def service_find_thread_by_id(
        self, thread_id: UUID,
        optionnal_user_connected_thread: ThreadAuthPayload | None = None
    ) -> DefaultAppServiceResult[ReadThreadWithUserConnectionInfo]:
        """Logique métier de récupération d'un thread par ID."""

        thread_from_cache = await self.__thread_cache.get_thread_from_cache(
            thread_id=thread_id
        )

        if thread_from_cache is not None:
            thread_from_cache = self._verify_user_connected_to_thread(thread_from_cache, optionnal_user_connected_thread)
            return ServiceResult.service_success(data=thread_from_cache)

        thread_repo = await self.__thread_repo.get_thread_by_id(thread_id=thread_id)

        if thread_repo.is_error():
            logger.error(f"Erreur: {thread_repo.error}")
            return thread_repo.to_service_error(service_name=self._service_name)

        read_thread = self._build_read_thread_schemas(thread_repo.data)

        await self.__thread_cache.set_thread_in_cache(
            thread=read_thread, ttl=CacheDuration.TWENTY_MINUTES
        )

        read_thread = self._verify_user_connected_to_thread(read_thread, optionnal_user_connected_thread)

        return ServiceResult.service_success(
            data=read_thread,
            service_name=self._service_name,
        )

    async def service_find_thread_by_slug(
        self,
        slug: str,
        optionnal_user_connected_thread: ThreadAuthPayload | None = None,
    ) -> DefaultAppServiceResult[ReadThreadWithUserConnectionInfo]:
        """Logique métier de récupération d'un thread par slug."""

        thread_repo = await self.__thread_repo.get_thread_by_slug(slug=slug)

        if thread_repo.is_error():
            logger.error(f"Erreur: {thread_repo.error}")
            return thread_repo.to_service_error(service_name=self._service_name)

        read_thread = self._build_read_thread_schemas(thread_repo.data)

        await self.__thread_cache.set_thread_in_cache(
            thread=read_thread, ttl=CacheDuration.TWENTY_MINUTES
        )

        read_thread = self._verify_user_connected_to_thread(read_thread, optionnal_user_connected_thread)

        return ServiceResult.service_success(
            data=read_thread,
            service_name=self._service_name,
        )

    async def service_find_all_threads(
            self,
            optionnal_user_connected_thread: ThreadAuthPayload | None = None
    ) -> DefaultAppServiceResult[list[ReadThreadWithUserConnectionInfo]]:
        """Logique métier de récupération de tous les threads."""

        threads_from_cache = await self.__thread_cache.get_threads_list_from_cache()

        if threads_from_cache is not None:
            threads_from_cache = [self._verify_user_connected_to_thread(t, optionnal_user_connected_thread) for t in threads_from_cache]
            return ServiceResult.service_success(
                data=threads_from_cache,
                service_name=self._service_name,
            )

        thread_repo = await self.__thread_repo.get_all_threads()

        if thread_repo.is_error():
            logger.error(f"Erreur: {thread_repo.error}")
            return thread_repo.to_service_error(service_name=self._service_name)

        read_threads = [self._build_read_thread_schemas(thread) for thread in thread_repo.data]

        await self.__thread_cache.set_threads_list_in_cache(
            threads=read_threads, ttl=CacheDuration.TWENTY_MINUTES
        )

        read_threads = [self._verify_user_connected_to_thread(thread, optionnal_user_connected_thread) for thread in read_threads]

        return ServiceResult.service_success(
            data=read_threads,
            service_name=self._service_name,
        )

    async def service_create_thread(
        self, thread_data: CreateThread
    ) -> DefaultAppServiceResult[ReadThread]:
        """Logique métier pour créer un thread."""

        thread_repo = await self.__thread_repo.insert_thread(thread_data=thread_data)

        if thread_repo.is_error():
            logger.error(f"Erreur: {thread_repo.error}")
            return thread_repo.to_service_error(service_name=self._service_name)

        read_thread = self._build_read_thread_schemas(thread_repo.data)

        await self.__thread_cache.set_thread_in_cache(
            thread=read_thread, ttl=CacheDuration.TWENTY_MINUTES
        )
        await self.__thread_cache.invalid_threads_list_in_cache()

        return ServiceResult.service_success(
            data=read_thread,
            status_code=thread_repo.status_code,
            service_name=self._service_name,
        )

    async def service_get_thread_members(
        self, thread_id: UUID, include_inactive: bool = False
    ) -> DefaultAppServiceResult[List[ReadMember]]:
        """Logique métier pour récupérer les membres d'un thread.

        Args:
            thread_id: ID du thread
            include_inactive: Si True, inclut les membres inactifs ou ayant quitté

        Returns:
            Liste de ReadMember (membres du thread)

        Processus:
            1. Vérifie le cache pour les membres du thread
            2. Si non trouvé, récupère depuis la base de données
            3. Met en cache le résultat
            4. Retourne les membres
        """
        # Vérifier le cache
        members_from_cache = await self.__thread_cache.get_members_by_thread_from_cache(
            thread_id=thread_id
        )

        if members_from_cache is not None:
            return ServiceResult.service_success(
                data=members_from_cache,
                service_name=self._service_name,
            )

        # Récupérer depuis la base de données
        thread_members_repo = await self.__thread_member_repo.get_thread_members_with_details(
            thread_id=thread_id, include_inactive=include_inactive
        )

        if thread_members_repo.is_error():
            logger.error(f"Erreur lors de la récupération des membres du thread: {thread_members_repo.error}")
            return thread_members_repo.to_service_error(service_name=self._service_name)

        # Convertir ThreadMember en ReadMember
        read_members = [ReadMember.model_validate(thread_member.member) for thread_member in thread_members_repo.data]

        # Mettre en cache
        await self.__thread_cache.set_members_by_thread_in_cache(
            thread_id=thread_id, members=read_members, ttl=CacheDuration.TWENTY_MINUTES
        )

        return ServiceResult.service_success(
            data=read_members,
            service_name=self._service_name,
        )
