from typing import Optional
from uuid import UUID

from logging import getLogger

from app.cache.base.cache_key import CacheKey
from app.cache.base.cache_wrapper import CacheWrapper
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.cache_utils import CacheUtils
from app.cache.helpers.keys_factory import CacheKeysFactory

from app.schemas.member_schemas import ReadMember

logger = getLogger(__name__)


class MemberCache:
    """Classe de gestion du cache pour les membres."""

    def __init__(self, cache: CacheWrapper):
        self.cache = cache

    @staticmethod
    def create_member_cache_key(member_id: UUID) -> CacheKey:
        """Crée une clé de cache pour un membre.
        
        Args:
            member_id: ID du membre concerné
            
        Returns:
            CacheKey: Instance de CacheKey formatée avec l'ID du membre
        """
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.MEMBER_OBJECT
        ).set_arguments(id=str(member_id))

    async def set_member_in_cache(
        self, member: ReadMember, ttl: int
    ) -> None:
        """Enregistre un membre dans le cache.
        
        Args:
            member: Instance de ReadMember à mettre en cache
            ttl: Durée de vie en secondes
        """
        try:
            cache_key = self.create_member_cache_key(member.id)
            await self.cache.save_pydantic_model_in_cache(
                key=cache_key, model_instance=member, expire_seconds=ttl
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_member_from_cache(
        self, member_id: UUID
    ) -> Optional[ReadMember]:
        """Récupère un membre depuis le cache.
        
        Args:
            member_id: ID du membre à récupérer
            
        Returns:
            Optional[ReadMember]: Le membre si trouvé, None sinon
        """
        try:
            cache_key = self.create_member_cache_key(member_id)
            return await self.cache.get_pydantic_model_from_cache(
                key=cache_key, model_class=ReadMember
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def invalid_member_in_cache(self, member_id: UUID) -> None:
        """Invalide un membre dans le cache.
        
        Args:
            member_id: ID du membre à invalider
        """
        try:
            cache_key = self.create_member_cache_key(member_id)
            await self.cache.delete_in_cache(key=cache_key)
            logger.info(f"Cache member invalidé pour l'ID : {member_id}")
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
