from typing import Optional, List
from uuid import UUID

from logging import getLogger

from app.cache.base.cache_key import CacheKey
from app.cache.base.cache_wrapper import CacheWrapper
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.cache_utils import CacheUtils
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.globals.cache_duration import CacheDuration

from app.schemas.thread_schemas import ReadThread
from app.schemas.message_schemas import ReadMessage
from app.schemas.member_schemas import ReadMember
from app.schemas.thread_schemas import InternalReadThread

logger = getLogger(__name__)


class ThreadCache:
    """Classe de gestion du cache pour les threads."""

    def __init__(self, cache: CacheWrapper):
        self.cache = cache

    @staticmethod
    def create_thread_cache_key(thread_id: UUID) -> CacheKey:
        """Crée une clé de cache pour un thread.

        Args:
            thread_id: ID du thread concerné

        Returns:
            CacheKey: Instance de CacheKey formatée avec l'ID du thread
        """
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.THREAD_OBJECT
        ).set_arguments(id=str(thread_id))


    async def set_raw_thread_in_cache(self, thread : InternalReadThread, ttl: int = CacheDuration.TWENTY_MINUTES) -> None:
        """Enregistre un thread dans le cache à partir d'une instance de InternalForLoginReadThread.

        Args:
            thread: Instance de InternalForLoginReadThread à mettre en cache
            ttl: Durée de vie en secondes
        """
        try:
            cache_key = CacheKeysFactory.get_cache_key(
                AvailableCacheKeys.INTERNAL_THREAD_RAW_OBJECT
            ).set_arguments(id=str(thread.id))

            await self.cache.save_pydantic_model_in_cache(
                key=cache_key, model_instance=thread, expire_seconds=ttl
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_raw_thread_from_cache(self, thread_id: UUID) -> Optional[InternalReadThread]:
        """Récupère un thread brut (InternalForLoginReadThread) depuis le cache.

        Args:
            thread_id: ID du thread à récupérer

        Returns:
            Optional[InternalReadThread]: Le thread brut si trouvé, None sinon
        """
        try:
            cache_key = CacheKeysFactory.get_cache_key(
                AvailableCacheKeys.INTERNAL_THREAD_RAW_OBJECT
            ).set_arguments(id=str(thread_id))

            return await self.cache.get_pydantic_model_from_cache(
                key=cache_key, model_class=InternalReadThread
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def invalidate_raw_thread_in_cache(self, thread_id: UUID) -> None:
        """Invalide un thread brut (InternalForLoginReadThread) dans le cache.

        Args:
            thread_id: ID du thread à invalider
        """
        try:
            cache_key = CacheKeysFactory.get_cache_key(
                AvailableCacheKeys.INTERNAL_THREAD_RAW_OBJECT
            ).set_arguments(id=str(thread_id))

            await self.cache.delete_in_cache(key=cache_key)
            logger.info(f"Cache du thread brut invalidé pour l'ID : {thread_id}")
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def set_thread_in_cache(
        self, thread: ReadThread, ttl: int = CacheDuration.TWENTY_MINUTES
    ) -> None:
        """Enregistre un thread dans le cache.

        Args:
            thread: Instance de ReadThread à mettre en cache
            ttl: Durée de vie en secondes
        """
        try:
            cache_key = self.create_thread_cache_key(thread.id)
            await self.cache.save_pydantic_model_in_cache(
                key=cache_key, model_instance=thread, expire_seconds=ttl
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_thread_from_cache(self, thread_id: UUID) -> Optional[ReadThread]:
        """Récupère un thread depuis le cache.

        Args:
            thread_id: ID du thread à récupérer

        Returns:
            Optional[ReadThread]: Le thread si trouvé, None sinon
        """
        try:
            cache_key = self.create_thread_cache_key(thread_id)
            return await self.cache.get_pydantic_model_from_cache(
                key=cache_key, model_class=ReadThread
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def invalid_thread_in_cache(self, thread_id: UUID) -> None:
        """Invalide un thread dans le cache.

        Args:
            thread_id: ID du thread à invalider
        """
        try:
            cache_key = self.create_thread_cache_key(thread_id)
            await self.cache.delete_in_cache(key=cache_key)
            logger.info(f"Cache thread invalidé pour l'ID : {thread_id}")
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    # Méthodes pour la liste des threads
    @staticmethod
    def create_threads_list_cache_key() -> CacheKey:
        """Crée une clé de cache pour la liste de tous les threads.

        Returns:
            CacheKey: Instance de CacheKey pour la liste des threads
        """
        return CacheKeysFactory.get_cache_key(AvailableCacheKeys.THREADS_LIST)

    async def set_threads_list_in_cache(
        self, threads: List[ReadThread], ttl: int
    ) -> None:
        """Enregistre la liste de tous les threads dans le cache.

        Args:
            threads: Liste des threads à mettre en cache
            ttl: Durée de vie en secondes
        """
        try:
            cache_key = self.create_threads_list_cache_key()
            await self.cache.save_list_in_cache(
                key=cache_key, value=threads, expire_seconds=ttl
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_threads_list_from_cache(self) -> Optional[List[ReadThread]]:
        """Récupère la liste de tous les threads depuis le cache.

        Returns:
            Optional[List[ReadThread]]: La liste des threads si trouvée, None sinon
        """
        try:
            cache_key = self.create_threads_list_cache_key()
            cached_list = await self.cache.get_list_from_cache(key=cache_key)
            if cached_list is None:
                return None
            # Convertir la liste de dicts en liste de ReadThread
            return [ReadThread.model_validate_json(item) for item in cached_list]
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def invalid_threads_list_in_cache(self) -> None:
        """Invalide la liste de tous les threads dans le cache."""
        try:
            cache_key = self.create_threads_list_cache_key()
            await self.cache.delete_in_cache(key=cache_key)
            logger.info("Cache de la liste des threads invalidé")
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    # Méthodes pour la liste des messages d'un thread
    @staticmethod
    def create_messages_by_thread_cache_key(thread_id: UUID) -> CacheKey:
        """Crée une clé de cache pour la liste des messages d'un thread.

        Args:
            thread_id: ID du thread concerné

        Returns:
            CacheKey: Instance de CacheKey pour la liste des messages du thread
        """
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.MESSAGES_BY_THREAD_LIST
        ).set_arguments(id=str(thread_id))

    async def set_messages_by_thread_in_cache(
        self, thread_id: UUID, messages: List[ReadMessage], ttl: int
    ) -> None:
        """Enregistre la liste des messages d'un thread dans le cache.

        Args:
            thread_id: ID du thread
            messages: Liste des messages à mettre en cache
            ttl: Durée de vie en secondes
        """
        try:
            cache_key = self.create_messages_by_thread_cache_key(thread_id)
            await self.cache.save_list_in_cache(
                key=cache_key, value=messages, expire_seconds=ttl
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_messages_by_thread_from_cache(
        self, thread_id: UUID
    ) -> Optional[List[ReadMessage]]:
        """Récupère la liste des messages d'un thread depuis le cache.

        Args:
            thread_id: ID du thread

        Returns:
            Optional[List[ReadMessage]]: La liste des messages si trouvée, None sinon
        """
        try:
            cache_key = self.create_messages_by_thread_cache_key(thread_id)
            cached_list = await self.cache.get_list_from_cache(key=cache_key)
            if cached_list is None:
                return None
            # Convertir la liste de dicts en liste de ReadMessage
            return [ReadMessage.model_validate_json(item) for item in cached_list]
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def invalid_messages_by_thread_in_cache(self, thread_id: UUID) -> None:
        """Invalide la liste des messages d'un thread dans le cache.

        Args:
            thread_id: ID du thread
        """
        try:
            cache_key = self.create_messages_by_thread_cache_key(thread_id)
            await self.cache.delete_in_cache(key=cache_key)
            logger.info(f"Cache des messages du thread {thread_id} invalidé")
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    # Méthodes pour la liste des membres d'un thread
    @staticmethod
    def create_members_by_thread_cache_key(thread_id: UUID) -> CacheKey:
        """Crée une clé de cache pour la liste des membres d'un thread.

        Args:
            thread_id: ID du thread concerné

        Returns:
            CacheKey: Instance de CacheKey pour la liste des membres du thread
        """
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.MEMBERS_BY_THREAD_LIST
        ).set_arguments(id=str(thread_id))

    async def set_members_by_thread_in_cache(
        self, thread_id: UUID, members: List[ReadMember], ttl: int
    ) -> None:
        """Enregistre la liste des membres d'un thread dans le cache.

        Args:
            thread_id: ID du thread
            members: Liste des membres à mettre en cache
            ttl: Durée de vie en secondes
        """
        try:
            cache_key = self.create_members_by_thread_cache_key(thread_id)
            await self.cache.save_list_in_cache(
                key=cache_key, value=members, expire_seconds=ttl
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_members_by_thread_from_cache(
        self, thread_id: UUID
    ) -> Optional[List[ReadMember]]:
        """Récupère la liste des membres d'un thread depuis le cache.

        Args:
            thread_id: ID du thread

        Returns:
            Optional[List[ReadMember]]: La liste des membres si trouvée, None sinon
        """
        try:
            cache_key = self.create_members_by_thread_cache_key(thread_id)
            cached_list = await self.cache.get_list_from_cache(key=cache_key)
            if cached_list is None:
                return None
            # Convertir la liste de dicts en liste de ReadMember
            return [ReadMember.model_validate_json(item) for item in cached_list]
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def invalid_members_by_thread_in_cache(self, thread_id: UUID) -> None:
        """Invalide la liste des membres d'un thread dans le cache.

        Args:
            thread_id: ID du thread
        """
        try:
            cache_key = self.create_members_by_thread_cache_key(thread_id)
            await self.cache.delete_in_cache(key=cache_key)
            logger.info(f"Cache des membres du thread {thread_id} invalidé")
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    @staticmethod
    def _create_thread_by_wa_group_cache_key(wa_group_jid: str) -> CacheKey:
        """Crée une clé de cache pour un thread par JID du groupe WhatsApp.

        Args:
            wa_group_jid: JID du groupe WhatsApp

        Returns:
            CacheKey: Instance de CacheKey pour le thread
        """
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.THREAD_BY_WA_GROUP_OBJECT
        ).set_arguments(wa_group_jid=wa_group_jid)

    async def set_thread_by_wa_group_in_cache(
        self, wa_group_jid: str, thread: ReadThread, ttl: int = CacheDuration.TWENTY_MINUTES
    ) -> None:
        """Enregistre un thread dans le cache indexé par wa_group_jid.

        Args:
            wa_group_jid: JID du groupe WhatsApp
            thread: Thread à mettre en cache
            ttl: Durée de vie en secondes
        """
        try:
            cache_key = self._create_thread_by_wa_group_cache_key(wa_group_jid)
            await self.cache.save_pydantic_model_in_cache(
                key=cache_key, model_instance=thread, expire_seconds=ttl
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_thread_by_wa_group_from_cache(self, wa_group_jid: str) -> Optional[ReadThread]:
        """Récupère un thread depuis le cache indexé par wa_group_jid.

        Args:
            wa_group_jid: JID du groupe WhatsApp

        Returns:
            ReadThread si trouvé, None sinon
        """
        try:
            cache_key = self._create_thread_by_wa_group_cache_key(wa_group_jid)
            return await self.cache.get_pydantic_model_from_cache(
                key=cache_key, model_class=ReadThread
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def invalid_thread_by_wa_group_in_cache(self, wa_group_jid: str) -> None:
        """Invalide un thread dans le cache indexé par wa_group_jid.

        Args:
            wa_group_jid: JID du groupe WhatsApp
        """
        try:
            cache_key = self._create_thread_by_wa_group_cache_key(wa_group_jid)
            await self.cache.delete_in_cache(key=cache_key)
            logger.info(f"Cache du thread par wa_group_jid {wa_group_jid} invalidé")
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
