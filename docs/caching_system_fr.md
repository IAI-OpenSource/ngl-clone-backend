# Le Système de Cache

Ce document détaille l'architecture du cache de l'application, l'enregistrement des clés de cache centralisées et les bonnes pratiques d'utilisation.

---

> **📄 Documentation Available in English**
> An English version of this document is available: [caching_system_en.md](./caching_system_en.md)

---

## 1. Principes de Conception
Pour éviter d'avoir des clés de cache codées en dur ("hardcoded") éparpillées dans l'application, ce qui amène à des doublons et des risques de collisions, le template centralise tout dans des structures type-safe :
1. **`BaseCacheEntity`** (définie dans [app/cache/helpers/availables.py](../app/cache/helpers/availables.py)) : Chaînes de format de base (avec placeholders comme `{id}`).
2. **`AvailableCacheKeys`** (dans [availables.py](../app/cache/helpers/availables.py)) : Enum listant toutes les clés exposées.
3. **`CacheKey`** (définie dans [app/cache/base/cache_key.py](../app/cache/base/cache_key.py)) : Représente une clé de cache avec ses paramètres dynamiques.
4. **`CacheKeysFactory`** (définie dans [app/cache/helpers/keys_factory.py](../app/cache/helpers/keys_factory.py)) : Fournit l'instance de `CacheKey` préconfigurée avec un nombre de placeholders garanti unique.

---

## 2. Processus d'Ajout d'une Nouvelle Clé de Cache

Lors de l'ajout d'une nouvelle entité à mettre en cache (ex: `Product`), suivez scrupuleusement ces 3 étapes :

### Étape 1 : Enregistrer le format de l'entité
Dans la classe `BaseCacheEntity` du fichier [app/cache/helpers/availables.py](../app/cache/helpers/availables.py) :
```python
class BaseCacheEntity:
    USER = "entity:user:{id}"
    SESSION = "entity:session:{id}"
    PRODUCT = "entity:product:{code}"  # <-- NOUVELLE ENTITÉ
```

### Étape 2 : Ajouter la clé dans l'enum
Dans l'enum `AvailableCacheKeys` du même fichier :
```python
class AvailableCacheKeys(str, Enum):
    USER_OBJECT = BaseCacheEntity.USER
    SESSION_OBJECT = BaseCacheEntity.SESSION
    PRODUCT_OBJECT = BaseCacheEntity.PRODUCT  # <-- NOUVELLE CLÉ ENUM
```

### Étape 3 : Configurer et mapper la clé dans la Factory
Dans la classe `CacheKeysFactory` du fichier [app/cache/helpers/keys_factory.py](../app/cache/helpers/keys_factory.py), ajoutez la clé au dictionnaire privé `__cache_keys_mapping` en indiquant le nombre de placeholders requis (ici `1` pour `{code}`) :
```python
    __cache_keys_mapping: dict[AvailableCacheKeys, CacheKey] = {
        AvailableCacheKeys.USER_OBJECT: CacheKey.new_key(
            AvailableCacheKeys.USER_OBJECT, 1
        ),
        AvailableCacheKeys.SESSION_OBJECT: CacheKey.new_key(
            AvailableCacheKeys.SESSION_OBJECT, 1
        ),
        AvailableCacheKeys.PRODUCT_OBJECT: CacheKey.new_key(
            AvailableCacheKeys.PRODUCT_OBJECT, 1  # <-- AJOUT MAPPING
        ),
    }
```

---

## 3. Utilisation dans le Code : Le Pattern "Cacher"

> [!IMPORTANT]
> **Ne faites jamais d'opérations de cache (lecture/écriture directe) dans les Services ou les Repositories.**
> Vous devez créer une classe de gestion dédiée (un "Cacher") dans le package `app/cache/` (comme [app/cache/user_cache.py](../app/cache/user_cache.py)).

Cette classe encapsule le wrapper `CacheWrapper` et expose des méthodes explicites pour enregistrer, lire et surtout **invalider facilement** les données du cache.

### Squelette d'une classe de cache :
```python
# app/cache/product_cache.py
from typing import Optional
from uuid import UUID
from logging import getLogger

from app.cache.base.cache_key import CacheKey
from app.cache.base.cache_wrapper import CacheWrapper
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.cache_utils import CacheUtils
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.schemas.product_schemas import ReadProduct

logger = getLogger(__name__)

class ProductCache:
    def __init__(self, cache: CacheWrapper):
        self.cache = cache

    @staticmethod
    def create_product_cache_key(product_code: str) -> CacheKey:
        # Récupération de la clé centralisée et injection de la valeur dynamique
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.PRODUCT_OBJECT
        ).set_arguments(code=product_code)

    async def set_product_in_cache(self, product: ReadProduct, ttl: int) -> None:
        try:
            key = self.create_product_cache_key(product.code)
            await self.cache.save_pydantic_model_in_cache(
                key=key, model_instance=product, expire_seconds=ttl
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_product_from_cache(self, product_code: str) -> Optional[ReadProduct]:
        try:
            key = self.create_product_cache_key(product_code)
            return await self.cache.get_pydantic_model_from_cache(
                key=key, model_class=ReadProduct
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def invalid_product_in_cache(self, product_code: str) -> None:
        """Méthode essentielle pour invalider le cache après une mise à jour ou suppression BD"""
        try:
            key = self.create_product_cache_key(product_code)
            await self.cache.delete_in_cache(key=key)
            logger.info(f"Cache produit invalidé pour le code : {product_code}")
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
```

---

## 4. Fonctionnalités Avancées de `CacheWrapper`

Le wrapper [CacheWrapper](../app/cache/base/cache_wrapper.py) met à disposition des opérations complexes :
- **Sérialisation Automatique** : Gestion automatique des dictionnaires, listes et modèles Pydantic (`save_pydantic_model_in_cache`).
- **Opérations Atomiques** : `incr_in_cache` et `decr_in_cache` pour l'incrémentation sûre.
- **Sets (Ensembles)** : `add_to_a_set` et `get_from_a_set` pour manipuler des structures d'ensembles uniques.
- **Redis Pub/Sub** : Publication (`pub_sub_publish_message`) et écoute asynchrone via des générateurs (`pub_sub_channel_listener`).
- **Redis Streams (Flux)** : Lecture et écriture adaptées aux files d'attente distribuées, avec support des groupes de consommateurs (`stream_create_group`, `stream_read_group`, `stream_ack`).
