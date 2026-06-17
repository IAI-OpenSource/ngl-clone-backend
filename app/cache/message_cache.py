from typing import Optional
from uuid import UUID

from logging import getLogger

from app.cache.base.cache_key import CacheKey
from app.cache.base.cache_wrapper import CacheWrapper
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.cache_utils import CacheUtils
from app.cache.helpers.keys_factory import CacheKeysFactory

from app.schemas.message_schemas import ReadMessage

logger = getLogger(__name__)


class MessageCache:
    """Classe de gestion du cache pour les messages."""

    def __init__(self, cache: CacheWrapper):
        self.cache = cache

    @staticmethod
    def create_message_cache_key(message_id: UUID) -> CacheKey:
        """Crée une clé de cache pour un message.
        
        Args:
            message_id: ID du message concerné
            
        Returns:
            CacheKey: Instance de CacheKey formatée avec l'ID du message
        """
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.MESSAGE_OBJECT
        ).set_arguments(id=str(message_id))

    async def set_message_in_cache(
        self, message: ReadMessage, ttl: int
    ) -> None:
        """Enregistre un message dans le cache.
        
        Args:
            message: Instance de ReadMessage à mettre en cache
            ttl: Durée de vie en secondes
        """
        try:
            cache_key = self.create_message_cache_key(message.id)
            await self.cache.save_pydantic_model_in_cache(
                key=cache_key, model_instance=message, expire_seconds=ttl
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_message_from_cache(
        self, message_id: UUID
    ) -> Optional[ReadMessage]:
        """Récupère un message depuis le cache.
        
        Args:
            message_id: ID du message à récupérer
            
        Returns:
            Optional[ReadMessage]: Le message si trouvé, None sinon
        """
        try:
            cache_key = self.create_message_cache_key(message_id)
            return await self.cache.get_pydantic_model_from_cache(
                key=cache_key, model_class=ReadMessage
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def invalid_message_in_cache(self, message_id: UUID) -> None:
        """Invalide un message dans le cache.
        
        Args:
            message_id: ID du message à invalider
        """
        try:
            cache_key = self.create_message_cache_key(message_id)
            await self.cache.delete_in_cache(key=cache_key)
            logger.info(f"Cache message invalidé pour l'ID : {message_id}")
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
