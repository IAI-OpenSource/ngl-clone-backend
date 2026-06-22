
from datetime import timedelta
from logging import getLogger

from app.cache.helpers.availables import AvailableCacheKeys
from app.core.config import RATE_LIMIT_MESSAGES_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS
from app.globals.businnes_error import AppError, AppErrorType
from app.schemas.thread_schemas import ThreadAuthPayload

from . import ServiceResult
from ..cache.helpers.keys_factory import CacheKeysFactory

logger = getLogger(__name__)


class RateLimiterService:
    """Service pour gérer le rate limiting des messages par client (identifier_id)."""

    def __init__(self, cache):
        """Initialise le service de rate limiting avec une instance de cache."""
        self.__cache = cache
        self._rate_limit_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.RATE_LIMIT_USER_MESSAGES)
        self._max_messages = RATE_LIMIT_MESSAGES_PER_MINUTE
        self._window_seconds = RATE_LIMIT_WINDOW_SECONDS

    async def check_message_rate_limit(self, thread_auth: ThreadAuthPayload) -> ServiceResult[bool]:
        """Vérifie si le client a dépassé la limite de messages.
        
        Utilise Redis INCR pour incrémenter atomiquement le compteur de messages
        pour ce client. Si c'est la première requête dans la fenêtre, crée
        la clé avec expiration.
        
        Args:
            thread_auth: Le ThreadAuthPayload contenant l'identifier_id du client
            
        Returns:
            ServiceResult avec True si la requête est autorisée, False si rate limité
        """
        identifier_id = thread_auth.identifier_id
        cache_key = self._rate_limit_key.set_arguments(user_id=identifier_id)
        
        try:
            # INCR incrémente atomiquement la valeur (ou l'initialise à 1 si elle n'existe pas)
            current_count = await self.__cache.incr_in_cache(cache_key)
            
            # Si c'est la première requête (count == 1), on set l'expiration
            if current_count == 1:
                await self.__cache.expire_in_cache(
                    cache_key, 
                    timedelta(seconds=self._window_seconds)
                )
            
            # Vérifie si le client a dépassé la limite
            if current_count > self._max_messages:
                logger.warning(
                    f"Rate limit dépassé pour le client {identifier_id}: "
                    f"{current_count} messages en {self._window_seconds} secondes"
                )
                return ServiceResult.service_failure(
                    service_name="rate_limiter",
                    status_code=429,
                    error=AppError(
                        error_type=AppErrorType.RATE_LIMIT_EXCEEDED,
                        error_message=f"Limite de {self._max_messages} messages par minute dépassée. "
                                       f"Veuillez attendre avant d'envoyer d'autres messages."
                    )
                )
            
            return ServiceResult.service_success(data=True)
            
        except Exception as e:
            logger.exception(f"Erreur lors de la vérification du rate limit: {e}")
            # En cas d'erreur Redis, on autorise la requête (fail-open)
            return ServiceResult.service_success(data=True)

    async def get_remaining_requests(self, thread_auth: ThreadAuthPayload) -> int:
        """Récupère le nombre de requêtes restantes pour le client.
        
        Args:
            thread_auth: Le ThreadAuthPayload contenant l'identifier_id du client
            
        Returns:
            Nombre de messages restants dans la fenêtre actuelle
        """
        identifier_id = thread_auth.identifier_id
        cache_key = self._rate_limit_key.set_arguments(user_id=identifier_id)
        
        try:
            current_count = await self.__cache.get_primitive_from_cache(cache_key)
            if current_count is None:
                return self._max_messages
            
            remaining = max(0, self._max_messages - int(current_count))
            return remaining
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération du count rate limit: {e}")
            return self._max_messages
