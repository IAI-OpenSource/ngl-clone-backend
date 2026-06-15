# Cache System

This document details the application's cache architecture, centralized cache key registration, and best practices for usage.

---

> **📄 Documentation Available in French**
> A French version of this document is available: [caching_system_fr.md](./caching_system_fr.md)

---

## 1. Design Principles

To avoid having hardcoded cache keys scattered throughout the application, which leads to duplicates and collision risks, the template centralizes everything in type-safe structures:
1. **`BaseCacheEntity`** (defined in [app/cache/helpers/availables.py](../app/cache/helpers/availables.py)): Base format strings (with placeholders like `{id}`).
2. **`AvailableCacheKeys`** (in [availables.py](../app/cache/helpers/availables.py)): Enum listing all exposed keys.
3. **`CacheKey`** (defined in [app/cache/base/cache_key.py](../app/cache/base/cache_key.py)): Represents a cache key with its dynamic parameters.
4. **`CacheKeysFactory`** (defined in [app/cache/helpers/keys_factory.py](../app/cache/helpers/keys_factory.py)): Provides the `CacheKey` instance preconfigured with a guaranteed unique number of placeholders.

---

## 2. Process for Adding a New Cache Key

When adding a new entity to cache (e.g., `Product`), strictly follow these 3 steps:

### Step 1: Register the Entity Format
In the `BaseCacheEntity` class of the file [app/cache/helpers/availables.py](../app/cache/helpers/availables.py):
```python
class BaseCacheEntity:
    USER = "entity:user:{id}"
    SESSION = "entity:session:{id}"
    PRODUCT = "entity:product:{code}"  # <-- NEW ENTITY
```

### Step 2: Add the Key to the Enum
In the `AvailableCacheKeys` enum of the same file:
```python
class AvailableCacheKeys(str, Enum):
    USER_OBJECT = BaseCacheEntity.USER
    SESSION_OBJECT = BaseCacheEntity.SESSION
    PRODUCT_OBJECT = BaseCacheEntity.PRODUCT  # <-- NEW ENUM KEY
```

### Step 3: Configure and Map the Key in the Factory
In the `CacheKeysFactory` class of the file [app/cache/helpers/keys_factory.py](../app/cache/helpers/keys_factory.py), add the key to the private `__cache_keys_mapping` dictionary, indicating the required number of placeholders (here `1` for `{code}`):
```python
    __cache_keys_mapping: dict[AvailableCacheKeys, CacheKey] = {
        AvailableCacheKeys.USER_OBJECT: CacheKey.new_key(
            AvailableCacheKeys.USER_OBJECT, 1
        ),
        AvailableCacheKeys.SESSION_OBJECT: CacheKey.new_key(
            AvailableCacheKeys.SESSION_OBJECT, 1
        ),
        AvailableCacheKeys.PRODUCT_OBJECT: CacheKey.new_key(
            AvailableCacheKeys.PRODUCT_OBJECT, 1  # <-- ADD MAPPING
        ),
    }
```

---

## 3. Usage in Code: The "Cacher" Pattern

> [!IMPORTANT]
> **Never perform cache operations (direct read/write) in Services or Repositories.**
> You must create a dedicated management class (a "Cacher") in the `app/cache/` package (like [app/cache/user_cache.py](../app/cache/user_cache.py)).

This class encapsulates the `CacheWrapper` and exposes explicit methods for saving, reading, and especially **easily invalidating** cache data.

### Skeleton of a Cache Class:
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
        # Retrieval of the centralized key and injection of the dynamic value
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
        """Essential method to invalidate cache after a database update or deletion"""
        try:
            key = self.create_product_cache_key(product_code)
            await self.cache.delete_in_cache(key=key)
            logger.info(f"Product cache invalidated for code: {product_code}")
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
```

---

## 4. Advanced Features of `CacheWrapper`

The [CacheWrapper](../app/cache/base/cache_wrapper.py) provides complex operations:
- **Automatic Serialization**: Automatic handling of dictionaries, lists, and Pydantic models (`save_pydantic_model_in_cache`).
- **Atomic Operations**: `incr_in_cache` and `decr_in_cache` for safe incrementation.
- **Sets**: `add_to_a_set` and `get_from_a_set` for manipulating unique set structures.
- **Redis Pub/Sub**: Publishing (`pub_sub_publish_message`) and async listening via generators (`pub_sub_channel_listener`).
- **Redis Streams**: Reading and writing adapted to distributed queues, with support for consumer groups (`stream_create_group`, `stream_read_group`, `stream_ack`).
