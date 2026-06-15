# AGENTS.MD

> Stack: FastAPI · PostgreSQL (asyncpg) · Redis · Celery · SQLAlchemy 2 (async) · Alembic · Python 3.11 (Docker) / 3.12 (local)
> Updated: 2026-06-15

## Overview

A production-ready FastAPI backend template implementing a strict layered architecture (Router → Service → Repository → Cache). It ships with JWT-based dual-cookie authentication, Redis caching via a typed wrapper, Celery task scaffolding, and Alembic migrations. The project serves as a reusable starting point for new Python API services.

## Repository Structure

```
app/
├── main.py                   # Application entrypoint, mounts routers + middleware
├── core/
│   ├── config.py             # All env vars loaded via python-dotenv
│   └── logging_config.py     # RotatingFileHandler (local) + console handler
├── db/
│   ├── __init__.py           # add_all_tables() — model registration for Alembic
│   ├── config.py             # DATABASE_URL, async engine, Base class
│   ├── session.py            # get_db() async generator dependency
│   ├── models/               # SQLAlchemy ORM models (user.py, session.py, enums/)
│   └── mixins/               # IntegrityMapperMixin for constraint→message mapping
├── schemas/
│   ├── user_schemas.py       # Pydantic models: CreateUser, ReadUser, LoginData, etc.
│   ├── session_schemas.py    # Session Pydantic models
│   └── globals/              # ApiBaseResponse, utils_schemas, others_schemas
├── repositories/
│   ├── __init__.py           # CrudResult, DefaultAppCrudResult
│   ├── user_repository.py    # DB queries returning CrudResult
│   ├── session_repository.py
│   └── helpers/              # RepositoriesUtils (error translation)
├── services/
│   ├── __init__.py           # ServiceResult, DefaultAppServiceResult
│   ├── user_service.py       # Business logic, cache-first reads
│   ├── auth_service.py       # Login/logout/refresh flows
│   └── session_service.py
├── cache/
│   ├── base/
│   │   ├── cache_wrapper.py  # CacheWrapper, CacheManager singleton, get_redis()
│   │   └── cache_key.py      # CacheKey with placeholder validation
│   ├── helpers/
│   │   ├── availables.py     # AvailableCacheKeys enum
│   │   ├── keys_factory.py   # CacheKeysFactory mapping
│   │   └── cache_utils.py
│   ├── user_cache.py         # Entity-specific cache class
│   └── session_cache.py
├── routers/
│   └── v1/
│       ├── base_router.py    # v1_api_router, includes all sub-routers
│       └── auth_router.py    # Example router with DI factories
├── auth/
│   ├── dependencies.py       # get_current_user dependency
│   ├── jwt_manager.py        # JWT creation / decoding
│   ├── cookie_manager.py     # HTTP-only cookie get/set/delete
│   ├── role_checker.py       # Role-based access control
│   └── role_depends.py
├── globals/
│   ├── app_result.py         # GenericAppResult[D, E] base class
│   ├── businnes_error.py     # AppError, AppErrorType enum
│   ├── services_names.py     # ServicesNames constants
│   ├── messages.py           # User-facing error message strings
│   ├── cache_duration.py     # CacheDuration constants (seconds)
│   ├── api_tags.py           # Swagger tag constants
│   └── others_constants.py   # COMMON_API_RESPONSES
├── middlewares/
│   ├── setup.py              # Registers all middleware
│   ├── exception_handler_middleware.py
│   └── request_logging_middleware.py
├── integrations/
│   └── __init__.py           # IntegrationServiceResult for third-party calls
├── settings/
│   ├── app_lifespan.py       # FastAPI lifespan (startup/shutdown)
│   ├── cors.py               # CORS configuration
│   └── dependencies_health.py
├── utils/
│   ├── security_utils.py     # argon2 hashing + verification
│   └── pagination_cursor_utils.py
└── worker/
    ├── celery_app.py          # Celery app config (broker=Redis)
    └── tasks/                 # Celery task modules

migrations/                    # Alembic migration scripts
docs/                          # Detailed architecture docs (EN + FR)
docker-compose.yml             # db (Postgres 15), redis (Redis 7), api
Dockerfile                     # Multi-stage Python 3.11-slim
Makefile                       # Docker and migration commands
```

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start dev server (local, no Docker)
python app/main.py

# Start all services via Docker Compose
make start_docker              # docker compose up -d

# Stop Docker services
make stop_docker               # docker compose down

# Build Docker images
make build_docker              # docker compose build
make rebuild_docker            # docker compose build --no-cache

# Restart API container only
make restart_api               # docker compose restart api

# Apply DB migrations (inside Docker)
make migrate-up                # alembic upgrade head

# Generate a new migration (inside Docker)
make migrate-gen msg="description here"   # alembic revision --autogenerate -m "..."

# Rollback last migration (inside Docker)
make migrate-down              # alembic downgrade -1

# Run Celery worker [VERIFY] (worker service is commented out in docker-compose.yml)
celery -A app.worker.celery_app worker --loglevel=info
```

There is no test framework, linter, formatter, or type-checker configured in this repository.

## Code Style

### File naming

Use `snake_case` for all Python files.
Examples: `user_service.py`, `auth_router.py`, `cache_wrapper.py`.

### Import ordering

Group imports in this order, separated by blank lines:
1. Standard library (`uuid`, `datetime`, `logging`, `typing`)
2. Third-party (`fastapi`, `sqlalchemy`, `pydantic`, `redis`)
3. Application-absolute (`from app.core.config import ...`)
4. Application-relative (`from . import ServiceResult`, `from ..cache.base.cache_wrapper import ...`)

```python
from logging import getLogger
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.user_cache import UserCache
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import CreateUser, ReadUser

from . import ServiceResult, DefaultAppServiceResult
from ..cache.base.cache_wrapper import CacheWrapper
from ..globals.services_names import ServicesNames
```

### Class vs function

Use classes for services, repositories, cache classes, and models.
Use standalone functions for FastAPI dependencies (`get_db`, `get_redis`, `get_current_user`).
Use `@dataclass` for repository classes.

### Type annotations

Annotate all function signatures with return types.
Use `Mapped[T]` + `mapped_column()` for SQLAlchemy model fields.
Use Pydantic `Field(...)` with `description=` for schema fields.

### Comments

Codebase comments and user-facing error messages are in **French**.
Maintain this convention when adding new code.

## Architecture Patterns

### Layered architecture (strict)

Every request flows through exactly four layers. Never skip a layer.

```
Router  →  Service  →  Repository  →  Database
                    →  Cache (Redis)
```

### Result type chain

Every layer returns a typed result object. Never return raw dicts or raise exceptions for business errors.

```
Repository  →  CrudResult[D, E]           (app/repositories/__init__.py)
Service     →  ServiceResult[D, E]        (app/services/__init__.py)
Router      →  ApiBaseResponse[D, E]      (via .to_HTTP_api_base_response())
Integration →  IntegrationServiceResult   (app/integrations/__init__.py)
```

Use `DefaultAppCrudResult[D]` as shorthand for `CrudResult[D, AppError]`.
Use `DefaultAppServiceResult[D]` as shorthand for `ServiceResult[D, AppError]`.

### Router pattern

Every router file follows this structure:

```python
router = APIRouter(prefix="/entity", tags=[ApiTags.TAG_NAME])

# DI factory functions — inject db + redis, return service instances
def get_entity_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheWrapper, Depends(get_redis)],
) -> EntityService:
    return EntityService(db, cache)

# Route handler — call service, convert to HTTP response
@router.post("/action", response_model=EntityInfos)
async def action(
    data: CreateEntity,
    response: Response,
    service: Annotated[EntityService, Depends(get_entity_service)],
) -> ApiBaseResponse[ReadEntity, AppError]:
    result = await service.service_do_action(data)
    return result.to_HTTP_api_base_response(reponse=response)
```

Register every new router in `app/routers/v1/base_router.py`:

```python
from app.routers.v1.entity_router import router as entity_router
v1_api_router.include_router(entity_router)
```

### Service pattern (cache-first)

Services check cache first, fall back to repository, then write-through to cache:

```python
class EntityService:
    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.__db = db
        self.__entity_cache = EntityCache(cache)
        self.__entity_repo = EntityRepository(self.__db)
        self._service_name = ServicesNames.ENTITY_SERVICE

    async def service_find_by_id(self, entity_id: UUID) -> DefaultAppServiceResult[ReadEntity]:
        # 1. Check cache
        cached = await self.__entity_cache.get_from_cache(entity_id)
        if cached is not None:
            return ServiceResult.service_success(data=cached)

        # 2. Fall back to DB
        repo_result = await self.__entity_repo.get_by_id(entity_id)
        if repo_result.is_error():
            return repo_result.to_service_error(service_name=self._service_name)

        # 3. Validate + cache
        read_model = ReadEntity.model_validate(repo_result.data)
        await self.__entity_cache.set_in_cache(read_model, ttl=CacheDuration.TWENTY_MINUTES)

        return ServiceResult.service_success(data=read_model, service_name=self._service_name)
```

### Repository pattern

Repositories are `@dataclass` classes. They receive `AsyncSession`, execute SQLAlchemy queries, and return `CrudResult`:

```python
@dataclass
class EntityRepository:
    db: AsyncSession

    async def get_by_id(self, entity_id: UUID) -> DefaultAppCrudResult[Entity]:
        try:
            stmt = select(Entity).where(Entity.id == entity_id).where(Entity.deleted_at == None)
            result = await self.db.execute(stmt)
            entity = result.scalar_one_or_none()
            if entity is None:
                return CrudResult.crud_failure(
                    AppError(error_type=AppErrorType.NOT_FOUND, error_message="..."),
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            return CrudResult.crud_success(data=entity)
        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(e, self.db, logger, Entity)
```

Use `RepositoriesUtils.traiter_errors_en_global()` for all exception handling in repositories.
This method handles both `IntegrityError` (via `IntegrityMapperMixin`) and unknown exceptions.

### Error propagation

Convert repository errors to service errors with `.to_service_error(service_name=...)`.
Convert service results to HTTP responses with `.to_HTTP_api_base_response(reponse=response)`.
Never construct `ApiBaseResponse` directly in routers.

### DB model convention

Every model inherits from `Base` (which is `MappedAsDataclass + DeclarativeBase`) and `IntegrityMapperMixin`.
Define an `ERROR_MESSAGES` dict mapping PostgreSQL constraint names to user-friendly French messages:

```python
class Entity(Base, IntegrityMapperMixin):
    __tablename__ = "entities"

    ERROR_MESSAGES = {
        "uq_entities_name": "Ce nom est déjà utilisé.",
    }
```

Use soft delete via `deleted_at` column. Filter with `.where(Entity.deleted_at == None)` in all queries.

### Alembic model registration

After creating a new model in `app/db/models/`, import it in `app/db/__init__.py` inside `add_all_tables()`:

```python
def add_all_tables():
    from app.db.models.user import User
    from app.db.models.session import Session
    from app.db.models.new_entity import NewEntity  # ADD HERE
```

This is required for Alembic autogenerate to detect the new table.

### Cache key system

1. Add a key template to `BaseCacheEntity` in `app/cache/helpers/availables.py`:
   ```python
   ENTITY = "entity:entity_name:{id}"
   ```
2. Add an `AvailableCacheKeys` enum entry pointing to that template.
3. Register it in `CacheKeysFactory.__cache_keys_mapping` in `app/cache/helpers/keys_factory.py`.
4. Create an entity-specific cache class in `app/cache/entity_cache.py`.

Use `CacheWrapper.save_pydantic_model_in_cache()` to store Pydantic models.
Use `CacheWrapper.get_pydantic_model_from_cache()` to retrieve them.
Use TTL constants from `CacheDuration` (e.g., `CacheDuration.TWENTY_MINUTES`).

### Authentication

Dual-cookie JWT: `_SECURE_TOKEN` (access, short-lived) + `_SID_REFRESH` (refresh, 7 days).
`CookieManager` handles HTTP-only cookies. `JWTManager` handles token creation/decoding.
Protect routes with `Depends(get_current_user)` from `app/auth/dependencies.py`.
Password hashing uses Argon2 via `app/utils/security_utils.py`.

## Environment Variables

Copy `.env.example` to `.env`. All variables are loaded via `python-dotenv` in `app/core/config.py`.

| Variable | Required | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `LOCAL` | `LOCAL` or `PRODUCTION` |
| `SECRET_KEY` | Yes | `change-me` | Access token signing key |
| `API_PORT` | No | `8000` | Port for uvicorn |
| `JWT_EXPIRES_MINUTES` | No | `3600` | Access token TTL (seconds despite name) |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `DATABASE_USER` | Yes | `admin` | PostgreSQL user |
| `DATABASE_PASSWORD` | Yes | `password` | PostgreSQL password |
| `DATABASE_TYPE` | Yes | `postgresql` | DB type for URL construction |
| `DATABASE_PILOT` | Yes | `asyncpg` | DB driver for URL construction |
| `DATABASE_HOST` | Yes | `db:5432` | DB host:port (use `db` for Docker) |
| `DATABASE_NAME` | Yes | `app_db` | PostgreSQL database name |
| `BD_OUTPUT_PORT` | No | `5433` | Host-mapped PostgreSQL port |
| `REDIS_URL` | Yes | `redis://app_redis:6379/0` | Redis connection URL |
| `REDIS_CACHE_PORT` | No | `6379` | Host-mapped Redis port |
| `START_PERIOD` | No | `5` | Docker healthcheck start period (seconds) |

## Adding a New Feature (end-to-end checklist)

Follow this exact sequence when adding a new entity or feature:

1. **DB model** → `app/db/models/new_entity.py` — inherit `Base, IntegrityMapperMixin`
2. **Register model** → import in `add_all_tables()` in `app/db/__init__.py`
3. **Generate migration** → `make migrate-gen msg="add new_entity table"`
4. **Apply migration** → `make migrate-up`
5. **Pydantic schemas** → `app/schemas/new_entity_schemas.py` — `Create`, `Read`, `Update` schemas
6. **Repository** → `app/repositories/new_entity_repository.py` — `@dataclass`, return `CrudResult`
7. **Cache key** → register in `availables.py` + `keys_factory.py`
8. **Cache class** → `app/cache/new_entity_cache.py`
9. **Service name** → add to `ServicesNames` in `app/globals/services_names.py`
10. **Service** → `app/services/new_entity_service.py` — cache-first logic, return `ServiceResult`
11. **API tag** → add to `ApiTags` in `app/globals/api_tags.py`
12. **Router** → `app/routers/v1/new_entity_router.py` — DI factories, `.to_HTTP_api_base_response()`
13. **Register router** → `app/routers/v1/base_router.py` — `v1_api_router.include_router(...)`

## Things an Agent Must NOT Do

1. **Never return raw dicts from services.** Always return `ServiceResult` via `.service_success()` or `.service_failure()`.

2. **Never construct `ApiBaseResponse` directly in a router.** Always call `service_result.to_HTTP_api_base_response(reponse=response)`.

3. **Never call `db.commit()` or `db.rollback()` in a service.** Transactions are managed by the repository layer and the `get_db()` session generator.

4. **Never create a `CacheKey` with its constructor.** Use `CacheKey.new_key()` via `CacheKeysFactory.get_cache_key()`, then call `.set_arguments()`.

5. **Never import a model directly for type hints that would cause circular imports.** Use `TYPE_CHECKING` guard:
   ```python
   from typing import TYPE_CHECKING
   if TYPE_CHECKING:
       from app.db.models.other_model import OtherModel
   ```

6. **Never skip the `add_all_tables()` registration.** Alembic will not detect unregistered models and migrations will be empty.

7. **Never forget soft-delete filtering.** Every `select()` query must include `.where(Entity.deleted_at == None)` unless explicitly querying deleted records.

## Documentation

Read these docs in `docs/` before making structural changes (EN versions listed, FR equivalents exist):

- `architecture_overview_en.md` — System architecture and data flow
- `repositories_and_services_en.md` — How to implement repos and services
- `caching_system_en.md` — Cache key organization and cache classes
- `results_and_errors_en.md` — Result typing and error propagation
- `auth_and_security_en.md` — Authentication flows and cookie usage
- `database_and_models_en.md` — DB models, mixins, and integrity mapping
- `routers_and_schemas_en.md` — Router patterns and Pydantic schemas
