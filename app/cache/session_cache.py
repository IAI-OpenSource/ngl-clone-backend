from typing import Optional
from uuid import UUID

from logging import getLogger


from app.cache.base.cache_key import CacheKey
from app.cache.base.cache_wrapper import CacheWrapper
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.cache_utils import CacheUtils
from app.cache.helpers.keys_factory import CacheKeysFactory

from app.schemas.session_schemas import ReadSession

logger = getLogger(__name__)


class SessionCache:

    def __init__(self, cache: CacheWrapper):
        self.cache = cache

    @staticmethod
    def create_session_cache_key(session_id: UUID) -> CacheKey:
        """fonction de dépendance pour créer/formater la clé de cache d'une session donnée.
          Cette clé permettra de mettre en cache la donnée d'une session spécifique

        Args:
            session_id (UUID) : ID de la session concernée

        Returns:
            CacheKey: Retourne une instance de CacheKey
        """

        cache_key = CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.SESSION_OBJECT
        ).set_arguments(id=str(session_id))

        return cache_key

    async def set_session_in_cache(
        self, session_id: UUID, session: ReadSession, ttl: int
    ):
        """Fonction permettant de mettre les infos d'une session en cache."""

        try:
            cache_key = self.create_session_cache_key(session_id)

            await self.cache.save_pydantic_model_in_cache(
                key=cache_key, model_instance=session, expire_seconds=ttl
            )

        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_session_from_cache(self, session_id: UUID) -> Optional[ReadSession]:
        """Fonction permettant de récupérer les infos d'une session depuis le cache.

        Args:
            session_id (UUID) : On prend le ID de la session pour constituer la clé du cache

        Returns:
            Optional[ReadSession] : Retourne un ReadSession ou None si le cache est vide
        """

        try:

            cache_key = self.create_session_cache_key(session_id)

            session_in_cache = await self.cache.get_pydantic_model_from_cache(
                key=cache_key, model_class=ReadSession
            )

            if session_in_cache is None:
                logger.error(f"Session avec ID {session_id} non trouvée dans le cache.")
                return None

            return session_in_cache

        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def invalid_session_in_cache(self, session_id: UUID):
        """Fonction permettant de supprimer les infos d'une session du cache.

        Args:
            session_id (UUID) : On prend le ID de la session pour constituer la clé du cache

        Returns:
            None
        """

        try:

            cache_key = self.create_session_cache_key(session_id)

            await self.cache.delete_in_cache(key=cache_key)

        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
