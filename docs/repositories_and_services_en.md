# Implementation of Repositories & Services

This document explains best practices for structuring the data access layer (Repository) and the business logic layer (Service).

---

> **📄 Documentation Available in French**
> A French version of this document is available: [repositories_and_services_fr.md](./repositories_and_services_fr.md)

---

## 1. Repository Layer (Data Access)

The exclusive role of a Repository is to execute SQL queries and return the result as a `CrudResult` object.

### 1.1. Design and Dependencies
- **`@dataclass`**: Repositories are decorated with `@dataclass` to simplify the injection of the async database session `db: AsyncSession`.
- **Global Exception Handling**: All queries are wrapped in a `try/except` block. Errors are redirected to [RepositoriesUtils](../app/repositories/helpers/repositories_utils.py) to ensure:
  1. Automatic rollback of the database session (`await session.rollback()`) to prevent corrupted transactional states.
  2. Automatic translation of integrity errors (via the model's `IntegrityMapperMixin`).
  3. Anonymization and logging of internal errors (HTTP 500).

### Standard Repository Skeleton:
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
        """Function to insert a product into the database."""
        try:
            product = Product(
                code=product_data.code,
                price=product_data.price,
                owner_id=product_data.owner_id
            )
            self.db.add(product)
            await self.db.commit()
            await self.db.refresh(product)
            
            logger.info("Product added successfully!")
            return CrudResult.crud_success(
                data=product, status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            # Handles IntegrityError (e.g., duplicate code) and automatically rolls back the session
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Product
            )

    async def get_product_by_code(self, code: str) -> DefaultAppCrudResult[Product]:
        """Function to retrieve a product by its unique code."""
        try:
            stmt = select(Product).where(Product.code == code)
            result = await self.db.execute(stmt)
            product = result.scalar_one_or_none()

            if product is None:
                logger.info("Product not found")
                return CrudResult.crud_failure(
                    AppError(
                        error_type=AppErrorType.NOT_FOUND,
                        error_message="Product does not exist",
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

## 2. Service Layer (Business Logic)

A Service orchestrates business logic. It coordinates database reads and writes, caching, and business calculations.

### 2.1. Design and Dependencies
- **Direct Injection**: The service constructor receives raw connections (`db: AsyncSession`, `cache: CacheWrapper`) as parameters.
- **Internal Instantiation**: The service itself instantiates its internal Repositories and Cachers. This avoids exposing the data access or cache plumbing in HTTP routers.
- **Error Conversion (`to_service_error`)**: Errors returned by the Repository layer (`CrudResult` failure) are properly propagated to the service by calling `.to_service_error(service_name=self._service_name)`. The HTTP code and error structure are thus fully preserved.

### Standard Service Skeleton:
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
        # Internal instantiation of sub-dependencies
        self.__product_cache = ProductCache(cache)
        self.__product_repo = ProductRepository(self.__db)
        self._service_name = "PRODUCT_SERVICE"

    async def service_find_product_by_code(self, code: str) -> DefaultAppServiceResult[ReadProduct]:
        """Retrieves a product (checks cache first, then database)."""
        
        # 1. Attempt to read from Redis cache
        product_cached = await self.__product_cache.get_product_from_cache(code)
        if product_cached is not None:
            return ServiceResult.service_success(data=product_cached)

        # 2. If not in cache, read from database
        product_db = await self.__product_repo.get_product_by_code(code)
        if product_db.is_error():
            # Conversion and proper propagation of the error
            return product_db.to_service_error(service_name=self._service_name)

        # 3. Validation and formatting via Pydantic schema
        read_product = ReadProduct.model_validate(product_db.data)

        # 4. Async storage in Redis cache
        await self.__product_cache.set_product_in_cache(
            product=read_product, ttl=CacheDuration.TWENTY_MINUTES
        )

        return ServiceResult.service_success(
            data=read_product,
            service_name=self._service_name
        )

    async def service_create_product(self, product_data: CreateProduct) -> DefaultAppServiceResult[ReadProduct]:
        """Creates a product, adds it to the database, and populates the cache."""
        
        product_db = await self.__product_repo.insert_product(product_data=product_data)
        if product_db.is_error():
            return product_db.to_service_error(service_name=self._service_name)

        read_product = ReadProduct.model_validate(product_db.data)

        # Populate cache immediately after creation
        await self.__product_cache.set_product_in_cache(
            product=read_product, ttl=CacheDuration.TWENTY_MINUTES
        )

        return ServiceResult.service_success(
            data=read_product,
            status_code=product_db.status_code,
            service_name=self._service_name
        )
```
