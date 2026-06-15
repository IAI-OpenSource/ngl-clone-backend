# Implémentation des Repositories & Services

Ce document explique les bonnes pratiques pour structurer la couche d'accès aux données (Repository) et la couche de logique métier (Service).

---

> **📄 Documentation Available in English**
> An English version of this document is available: [repositories_and_services_en.md](./repositories_and_services_en.md)

---

## 1. La Couche Repository (Accès Données)

Le rôle exclusif d'un Repository est d'exécuter des requêtes SQL et de retourner le résultat sous la forme d'un objet `CrudResult`.

### 1.1. Conception et Dépendances
- **`@dataclass`** : Les repositories sont décorés avec `@dataclass` pour simplifier l'injection de la session de base de données asynchrone `db: AsyncSession`.
- **Gestion Globale des Exceptions** : Toutes les requêtes sont enveloppées dans un bloc `try/except`. Les erreurs sont redirigées vers [RepositoriesUtils](../app/repositories/helpers/repositories_utils.py) pour assurer :
  1. Le rollback automatique de la session de base de données (`await session.rollback()`) pour éviter les états transactionnels corrompus.
  2. La traduction automatique des erreurs d'intégrité (via le mixin de modèle `IntegrityMapperMixin`).
  3. L'anonymisation et l'enregistrement de trace (logging) pour les erreurs internes (HTTP 500).

### Squelette Standard d'un Repository :
```python
# app/repositories/product_repository.py
from dataclasses import dataclass
from logging import getLogger
from uuid import UUID

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.product import Product
from app.schemas.product_schemas import CreateProduct
from app.repositories import DefaultAppCrudResult, CrudResult
from app.repositories.helpers.repositories_utils import RepositoriesUtils

logger = getLogger(__name__)

@dataclass
class ProductRepository:
    db: AsyncSession

    async def insert_product(self, product_data: CreateProduct) -> DefaultAppCrudResult[Product]:
        """Fonction pour insérer un produit en base de données."""
        try:
            product = Product(
                code=product_data.code,
                price=product_data.price,
                owner_id=product_data.owner_id
            )
            self.db.add(product)
            await self.db.commit()
            await self.db.refresh(product)
            
            logger.info("Produit ajouté avec succès !")
            return CrudResult.crud_success(
                data=product, status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            # Gère les IntegrityError (ex: code doublon) et rollback automatiquement la session
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Product
            )

    async def get_product_by_code(self, code: str) -> DefaultAppCrudResult[Product]:
        """Fonction pour récupérer un produit par son code unique."""
        try:
            stmt = select(Product).where(Product.code == code)
            result = await self.db.execute(stmt)
            product = result.scalar_one_or_none()

            if product is None:
                logger.info("Produit non trouvé")
                return CrudResult.crud_failure(
                    AppError(
                        error_type=AppErrorType.NOT_FOUND,
                        error_message="Produit inexistant",
                    ),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=product)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )
```

---

## 2. La Couche Service (Logique Métier)

Un Service orchestre la logique métier. Il coordonne les lectures et écritures en base de données, la mise en cache et les calculs métier.

### 2.1. Conception et Dépendances
- **Injection Directe** : Le constructeur d'un service reçoit en paramètres les connexions brutes (`db: AsyncSession`, `cache: CacheWrapper`).
- **Instanciation Interne** : Le service instancie lui-même ses Repositories et Cachers internes. Cela évite d'exposer la plomberie d'accès aux données ou au cache dans les routeurs HTTP.
- **Conversion d'Erreurs (`to_service_error`)** : Les erreurs retournées par la couche Repository (`CrudResult` d'échec) sont propagées proprement au service en appelant `.to_service_error(service_name=self._service_name)`. Le code HTTP et la structure de l'erreur sont ainsi intégralement préservés.

### Squelette Standard d'un Service :
```python
# app/services/product_service.py
from logging import getLogger
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.base.cache_wrapper import CacheWrapper
from app.cache.product_cache import ProductCache
from app.repositories.product_repository import ProductRepository
from app.schemas.product_schemas import CreateProduct, ReadProduct
from app.globals.cache_duration import CacheDuration
from app.globals.services_names import ServicesNames
from app.services import ServiceResult, DefaultAppServiceResult

logger = getLogger(__name__)

class ProductService:
    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.__db = db
        # Instanciation interne des sous-dépendances
        self.__product_cache = ProductCache(cache)
        self.__product_repo = ProductRepository(self.__db)
        self._service_name = "PRODUCT_SERVICE"

    async def service_find_product_by_code(self, code: str) -> DefaultAppServiceResult[ReadProduct]:
        """Récupère un produit (vérifie le cache en premier, puis la base de données)."""
        
        # 1. Tentative de lecture depuis le cache Redis
        product_cached = await self.__product_cache.get_product_from_cache(code)
        if product_cached is not None:
            return ServiceResult.service_success(data=product_cached)

        # 2. Si absent du cache, lecture en base de données
        product_db = await self.__product_repo.get_product_by_code(code)
        if product_db.is_error():
            # Conversion et propagation propre de l'erreur
            return product_db.to_service_error(service_name=self._service_name)

        # 3. Validation et formatage via schéma Pydantic
        read_product = ReadProduct.model_validate(product_db.data)

        # 4. Enregistrement asynchrone dans le cache Redis
        await self.__product_cache.set_product_in_cache(
            product=read_product, ttl=CacheDuration.TWENTY_MINUTES
        )

        return ServiceResult.service_success(
            data=read_product,
            service_name=self._service_name
        )

    async def service_create_product(self, product_data: CreateProduct) -> DefaultAppServiceResult[ReadProduct]:
        """Crée un produit, l'ajoute en base de données et peuple le cache."""
        
        product_db = await self.__product_repo.insert_product(product_data=product_data)
        if product_db.is_error():
            return product_db.to_service_error(service_name=self._service_name)

        read_product = ReadProduct.model_validate(product_db.data)

        # Peuple le cache immédiatement après création
        await self.__product_cache.set_product_in_cache(
            product=read_product, ttl=CacheDuration.TWENTY_MINUTES
        )

        return ServiceResult.service_success(
            data=read_product,
            status_code=product_db.status_code,
            service_name=self._service_name
        )
```
