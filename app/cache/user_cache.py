from typing import Optional
from uuid import UUID

from logging import getLogger


from app.cache.base.cache_key import CacheKey
from app.cache.base.cache_wrapper import CacheWrapper
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.cache_utils import CacheUtils

from app.cache.helpers.keys_factory import CacheKeysFactory
from app.schemas.user_schemas import ReadUser

logger = getLogger(__name__)


class UserCache:

    def __init__(self, cache: CacheWrapper):
        self.user_cache = cache

    @staticmethod
    def create_user_cache_key(user_id: UUID) -> CacheKey:

        cache_key = CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.USER_OBJECT
        ).set_arguments(id=str(user_id))

        return cache_key

    async def set_user_in_cache(self, user: ReadUser, ttl: int):
        """Fonction pour mettre un utilisateur en cache"""

        try:

            cache_key = self.create_user_cache_key(user_id=user.id)

            await self.user_cache.save_pydantic_model_in_cache(
                key=cache_key, model_instance=user, expire_seconds=ttl
            )

        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_user_from_cache(self, user_id: UUID) -> Optional[ReadUser]:
        """Fonction pour récupérer un utilisateur depuis le cache"""

        try:

            cache_key = self.create_user_cache_key(user_id)

            user_in_cache = await self.user_cache.get_pydantic_model_from_cache(
                key=cache_key, model_class=ReadUser
            )

            return user_in_cache

        except Exception as e:

            CacheUtils.traiter_exceptions(e, logger)

    async def invalid_user_in_cache(self, user_id: UUID):
        """Fonction pour invalider un utilisateur dans le cache"""

        try:

            cache_key = self.create_user_cache_key(user_id)

            await self.user_cache.delete_in_cache(key=cache_key)

        except Exception as e:

            CacheUtils.traiter_exceptions(e, logger)
