from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.base.cache_key import CacheKey


class CacheKeysFactory:
    """Factory pour créer des instances de CacheKey à partir d'AvailableCacheKeys, en utilisant une mapping pré-définie
    pour garantir l'unicité des clés de cache et faciliter la création de clés de cache formatées avec les arguments
    appropriés lors de leur utilisation dans les opérations de cache."""

    # Tableau de mapping entre les enums de AvailableCacheKeys et les instances de CacheKey correspondantes,
    # avec un nombre de placeholders défini pour chaque clé de cache, ce qui permet de centraliser la définition des
    # clés de cache et d'assurer leur unicité dans le système de cache

    __cache_keys_mapping: dict[AvailableCacheKeys, CacheKey] = {
        AvailableCacheKeys.USER_OBJECT: CacheKey.new_key(
            AvailableCacheKeys.USER_OBJECT, 1
        ),
        AvailableCacheKeys.SESSION_OBJECT: CacheKey.new_key(
            AvailableCacheKeys.SESSION_OBJECT, 1
        ),
    }

    @classmethod
    def get_cache_key(cls, cache_key_enum: AvailableCacheKeys) -> CacheKey:
        """
        Récupère une instance de CacheKey à partir d'un enum de AvailableCacheKeys, en utilisant la mapping pré-définie
        pour garantir l'unicité des clés de cache et faciliter la création de clés de cache formatées avec les arguments
        appropriés lors de leur utilisation dans les opérations de cache.
        Args:
            cache_key_enum: Un enum de AvailableCacheKeys représentant la clé de cache souhaitée, qui doit être présente
             dans la mapping pré-définie pour garantir l'unicité des clés de cache et éviter les conflits dans le cache,
             si la clé n'est pas présente dans la mapping, une exception KeyError sera levée pour indiquer que la clé de cache demandée n'est pas définie dans le système de cache

        Returns:
            CacheKey: Une instance de CacheKey correspondant à la clé de cache demandée, prête à être utilisée pour formater la clé de cache lors de son utilisation dans les opérations de cache
        Raises:
            KeyError: Si la clé de cache demandée n'est pas présente dans la mapping pré-définie, indiquant que la clé
             de cache n'est pas définie dans le système de cache, ce qui permet de détecter les erreurs de configuration
             du cache et d'assurer que seules les clés de cache valides et définies sont utilisées dans les opérations
             de cache

        """
        return cls.__cache_keys_mapping[cache_key_enum]
