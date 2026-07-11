from asyncio import gather
from logging import getLogger
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.message_cache import MessageCache
from app.cache.thread_cache import ThreadCache
from app.globals.cache_duration import CacheDuration
from app.repositories.message_repository import MessageRepository
from app.schemas.message_schemas import CreateMessage, ReadMessage, PaginatedMessagesResponse
from app.schemas.thread_schemas import ThreadAuthPayload
from . import ServiceResult, DefaultAppServiceResult
from .rate_limiter_service import RateLimiterService
from .thread_service import ThreadService
from ..cache.base.cache_wrapper import CacheWrapper
from ..db.models.member import Member
from ..db.models.message import Message
from ..globals.businnes_error import AppError, AppErrorType
from ..globals.services_names import ServicesNames
from ..schemas.member_schemas import ReadMember
from ..worker.celery_app import celery_app
from ..worker.tasks.base.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)


class MessageService:

    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.__db = db
        self.__cache = cache
        self.__message_cache = MessageCache(cache)
        self.__thread_cache = ThreadCache(cache)
        self.__message_repo = MessageRepository(self.__db)
        self._service_name = ServicesNames.MESSAGE_SERVICE

    @staticmethod
    def _format_message_with_mentions(message_data: tuple[Message, list[Member]]) -> ReadMessage:
        """Formate un message avec ses mentions pour l'affichage."""
        read_message = ReadMessage.model_validate(message_data[0])
        read_message.mentionned_members = [ReadMember.model_validate(m) for m in message_data[1]]
        return read_message

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

        message_repo = await self.__message_repo.get_message_by_id_with_mentions(
            message_id=message_id
        )

        if message_repo.is_error():
            logger.error(f"Erreur: {message_repo.error}")
            return message_repo.to_service_error(service_name=self._service_name)

        read_message = self._format_message_with_mentions(message_repo.data)

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

        messages_repo = await self.__message_repo.get_messages_by_thread_id_with_mentions(
            thread_id=thread_id,
        )

        if messages_repo.is_error():
            logger.error(f"Erreur: {messages_repo.error}")
            return messages_repo.to_service_error(service_name=self._service_name)

        read_messages = [
            self._format_message_with_mentions(message) for message in messages_repo.data
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

    async def service_get_messages_by_thread_id_paginated(
        self,
        thread_id: UUID,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> DefaultAppServiceResult[PaginatedMessagesResponse]:
        """Logique métier de récupération paginée des messages d'un thread avec curseur.
        
        Cette méthode gère :
        - La récupération depuis le cache si disponible
        - La requête en base de données avec pagination par curseur
        - Le cache des résultats paginés
        - La gestion des erreurs
        
        Args:
            thread_id: L'ID du thread
            limit: Nombre de messages par page (par défaut 20)
            cursor: Curseur de pagination encodé (base64). None pour la première page.
        
        Returns:
            ServiceResult contenant PaginatedMessagesResponse avec:
                - messages: Liste des messages de la page
                - has_next_page: True s'il y a une page suivante
                - next_cursor: Curseur pour la page suivante
                - has_previous_page: True s'il y a une page précédente
                - previous_cursor: Curseur pour la page précédente
        """

        # Validation défensive du limit (au cas où la méthode est appelée hors contexte FastAPI)
        if not (1 <= limit <= 100):
            limit = max(1, min(100, limit))
            logger.warning(f"Valeur de limit hors bornes, ajustée à {limit}")

        # Essayer de récupérer depuis le cache d'abord

        cached_paginated = await self.__thread_cache.get_paginated_messages_from_cache(
            thread_id=thread_id,
            cursor=cursor,
            limit=limit,
        )

        if cached_paginated is not None:
            return ServiceResult.service_success(data=cached_paginated)

        # Récupérer depuis la base de données
        messages_repo = await self.__message_repo.get_messages_by_thread_id_paginated(
            thread_id=thread_id,
            limit=limit,
            cursor=cursor,
            is_hidden=False,  # Par défaut, on exclut les messages cachés
        )

        if messages_repo.is_error():
            logger.error(f"Erreur: {messages_repo.error}")
            return messages_repo.to_service_error(service_name=self._service_name)

        messages_with_mentions, has_next_page, has_previous_page, next_cursor, previous_cursor = messages_repo.data

        # Formater les messages
        read_messages = [
            self._format_message_with_mentions(message) for message in messages_with_mentions
        ]

        # Créer la réponse paginée
        paginated_response = PaginatedMessagesResponse(
            messages=read_messages,
            has_next_page=has_next_page,
            next_cursor=next_cursor,
            has_previous_page=has_previous_page,
            previous_cursor=previous_cursor
        )

        # Mettre en cache les résultats paginés
        await self.__thread_cache.set_paginated_messages_in_cache(
            thread_id=thread_id,
            paginated_response=paginated_response,
            cursor=cursor,
            limit=limit,
        )

        return ServiceResult.service_success(
            data=paginated_response,
            service_name=self._service_name,
        )

    async def service_create_message(
        self, message_data: CreateMessage, user_payload: ThreadAuthPayload,
    ) -> DefaultAppServiceResult[ReadMessage]:
        """Logique métier pour ajouter un message à un thread."""
        thread_id_uuid = UUID(user_payload.thread_id)

        # Vérifier le rate limiting
        rate_limit_service = RateLimiterService(self.__cache)

        rate_limit_check_res = await rate_limit_service.check_message_rate_limit(
            user_payload
        )
        if rate_limit_check_res.is_error():
            return ServiceResult.service_failure(
                error=rate_limit_check_res.error,
                status_code=rate_limit_check_res.status_code
            )
        try:
            CreateMessage.validate_content(message_data.content)
        except ValueError as e:
            return ServiceResult.service_failure(error=AppError(
                error_message=str(e),
                error_type=AppErrorType.BAD_REQUEST
            ), status_code=400)

        # Vérifier que le thread autorise la création de nouveaux messages
        thread_svc = ThreadService(self.__db, self.__cache)
        verif = await thread_svc.verify_thread_allows_posting(thread_id_uuid)
        if verif.is_error():
            return ServiceResult.service_failure(error=verif.error, status_code=verif.status_code)

        message_repo = await self.__message_repo.insert_message(
            thread_id=thread_id_uuid,
            content=message_data.content,
            mentioned_member_ids=message_data.mentionned_member_ids
        )

        if message_repo.is_error():
            logger.error(f"Erreur: {message_repo.error}")
            return message_repo.to_service_error(service_name=self._service_name)

        celery_app.send_task(
            WorkersTaskNames.SEND_MESSAGE_TO_GROUP,
            kwargs={"message_id": str(message_repo.data.id)},
        )

        read_message = ReadMessage.model_validate(message_repo.data)

        # Invalider le cache de la liste complète ET le cache paginé
        gather(
            self.__thread_cache.invalid_messages_by_thread_in_cache(
                thread_id=thread_id_uuid
            ),
            self.__thread_cache.invalid_paginated_messages_in_cache(
                thread_id=thread_id_uuid
            ),
            return_exceptions=True,
        )

        return ServiceResult.service_success(
            data=read_message,
            status_code=message_repo.status_code,
            service_name=self._service_name,
        )
