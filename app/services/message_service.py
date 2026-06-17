from logging import getLogger
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.message_cache import MessageCache
from app.cache.thread_cache import ThreadCache
from app.globals.cache_duration import CacheDuration
from app.repositories.message_repository import MessageRepository
from app.schemas.message_schemas import CreateMessage, ReadMessage
from app.schemas.thread_schemas import ThreadAuthPayload

from . import ServiceResult, DefaultAppServiceResult
from .thread_service import ThreadService
from ..cache.base.cache_wrapper import CacheWrapper
from ..globals.services_names import ServicesNames

logger = getLogger(__name__)


class MessageService:

    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.__db = db
        self.__cache = cache
        self.__message_cache = MessageCache(cache)
        self.__thread_cache = ThreadCache(cache)
        self.__message_repo = MessageRepository(self.__db)
        self._service_name = ServicesNames.MESSAGE_SERVICE

    async def service_find_message_by_id(
        self, message_id: UUID, connected_thread: ThreadAuthPayload
    ) -> DefaultAppServiceResult[ReadMessage]:
        """Logique métier de récupération d'un message par ID."""

        thread_svc = ThreadService(self.__db, self.__cache)

        message_from_cache = await self.__message_cache.get_message_from_cache(
            message_id=message_id
        )

        if message_from_cache is not None:
            verif = await thread_svc.verify_can_interract_with_thread(
                message_from_cache.thread_id, connected_thread
            )
            if verif.is_error():
                return ServiceResult.service_failure(error=verif.error)
            return ServiceResult.service_success(data=message_from_cache)

        message_repo = await self.__message_repo.get_message_by_id(
            message_id=message_id
        )

        if message_repo.is_error():
            logger.error(f"Erreur: {message_repo.error}")
            return message_repo.to_service_error(service_name=self._service_name)

        read_message = ReadMessage.model_validate(message_repo.data)

        await self.__message_cache.set_message_in_cache(
            message=read_message, ttl=CacheDuration.TWENTY_MINUTES
        )

        verif = await thread_svc.verify_can_interract_with_thread(
            read_message.thread_id, connected_thread
        )
        if verif.is_error():
            return ServiceResult.service_failure(error=verif.error)
        return ServiceResult.service_success(
            data=read_message,
            service_name=self._service_name,
        )

    async def service_get_messages_by_thread_id(
        self,
        thread_id: UUID,
    ) -> DefaultAppServiceResult[list[ReadMessage]]:
        """Logique métier de récupération des messages d'un thread."""

        messages_from_cache = (
            await self.__thread_cache.get_messages_by_thread_from_cache(
                thread_id=thread_id
            )
        )

        if messages_from_cache is not None:
            return ServiceResult.service_success(data=messages_from_cache)

        messages_repo = await self.__message_repo.get_messages_by_thread_id(
            thread_id=thread_id,
        )

        if messages_repo.is_error():
            logger.error(f"Erreur: {messages_repo.error}")
            return messages_repo.to_service_error(service_name=self._service_name)

        read_messages = [
            ReadMessage.model_validate(message) for message in messages_repo.data
        ]

        await self.__thread_cache.set_messages_by_thread_in_cache(
            thread_id=thread_id,
            messages=read_messages,
            ttl=CacheDuration.TWENTY_MINUTES,
        )

        return ServiceResult.service_success(
            data=read_messages,
            service_name=self._service_name,
        )

    async def service_create_message(
        self, message_data: CreateMessage, thread_id: str
    ) -> DefaultAppServiceResult[ReadMessage]:
        """Logique métier pour ajouter un message à un thread."""
        thread_id_uuid = UUID(thread_id)

        message_repo = await self.__message_repo.insert_message(
            thread_id=thread_id_uuid,
            content=message_data.content,
        )

        if message_repo.is_error():
            logger.error(f"Erreur: {message_repo.error}")
            return message_repo.to_service_error(service_name=self._service_name)

        read_message = ReadMessage.model_validate(message_repo.data)

        await self.__message_cache.set_message_in_cache(
            message=read_message, ttl=CacheDuration.TWENTY_MINUTES
        )

        await self.__thread_cache.invalid_messages_by_thread_in_cache(
            thread_id=thread_id_uuid
        )

        return ServiceResult.service_success(
            data=read_message,
            status_code=message_repo.status_code,
            service_name=self._service_name,
        )
