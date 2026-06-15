# FastAPI Project Template - Clean Architecture

This project serves as a starting structure (boilerplate/template) for developing resilient, high-performance, and scalable web applications and REST APIs with FastAPI. It implements a strict separation of responsibilities (Clean Architecture) and rigorous typing at all levels.

---

> **🌍 Documentation Available in Other Languages**
> - [Français (French)](./README_fr.md)

---

## 1. Detailed Documentation Index

To deeply understand the different components of the application and recommended patterns, please refer to the following documents:

- [📂 Architecture Overview & Data Flow - EN](./docs/architecture_overview_en.md) / [FR](./docs/architecture_overview_fr.md) : Conceptual model (Router ➔ Service ➔ Repository ➔ Cache) and lifecycle.
- [📂 Database & Models - EN](./docs/database_and_models_en.md) / [FR](./docs/database_and_models_fr.md) : SQLAlchemy 2.0, `IntegrityMapperMixin` mixin, and constraint management.
- [📂 Results & Errors Management - EN](./docs/results_and_errors_en.md) / [FR](./docs/results_and_errors_fr.md) : `GenericAppResult` return model and subclasses (`CrudResult`, `ServiceResult`, `IntegrationServiceResult`).
- [📂 Cache System - EN](./docs/caching_system_en.md) / [FR](./docs/caching_system_fr.md) : Type-safe Redis cache registration and usage via Factory.
- [📂 Authentication & Security (RBAC) - EN](./docs/auth_and_security_en.md) / [FR](./docs/auth_and_security_fr.md) : Dual cookie (Access/Refresh), `HttpOnly` authentication, and role dependencies.
- [📂 Repositories & Services - EN](./docs/repositories_and_services_en.md) / [FR](./docs/repositories_and_services_fr.md) : Data and business logic modules writing and structuring.
- [📂 API Routers & Middlewares - EN](./docs/routers_and_schemas_en.md) / [FR](./docs/routers_and_schemas_fr.md) : Premium Swagger configuration, Pydantic validation, and diagnostic middlewares.

---

## 2. Development Workflow (Adding a Feature)

When adding a new entity to the application (e.g., a `Product`), you must follow this step-by-step cycle to respect the template paradigm:

```mermaid
graph TD
    A[1. Database Model & Constraints] --> B[2. Import tables & Alembic Migration]
    B --> C[3. Pydantic Schemas]
    C --> D[4. Repository & CRUD]
    D --> E[5. Cache Keys Definition & Cacher]
    E --> F[6. Business Service]
    F --> G[7. Router & API Registration]
```

### Step 1: Create the Database Model
Create the model file in `app/db/models/product.py`.
- Inherit from `Base` (which integrates `MappedAsDataclass`) and `IntegrityMapperMixin`.
- Define all table constraints (uniques, foreign keys, checks) as explicit constants at the top of the file.
- Fill in the `ERROR_MESSAGES` dictionary mapping SQL constraints to user error messages.
- For automatic columns (ID, timestamps, relationships), use `init=False`.

### Step 2: Declare the Table & Generate Migration
1. Import your model within the `add_all_tables()` function in [app/db/__init__.py](file:///home/sevtify/Projets/fast-api-project-template/app/db/__init__.py) so Alembic can detect it:
   ```python
   def add_all_tables():
       from app.db.models.user import User
       from app.db.models.session import Session
       from app.db.models.product import Product  # <-- IMPORT
   ```
2. Generate the SQL migration file:
   ```bash
   alembic revision --autogenerate -m "Create product table"
   ```
3. Apply the migration to your local database:
   ```bash
   alembic upgrade head
   ```

### Step 3: Define Pydantic Schemas
In the `app/schemas/` folder, create `product_schemas.py`:
- Create request schemas (e.g., `CreateProduct`, `UpdateProduct`).
- Create the typed output schema (e.g., `ReadProduct` with `from_attributes = True`).
- Create the API response wrapper by inheriting from `DefaultAppApiResponse` (e.g., `ProductInfos(DefaultAppApiResponse[ReadProduct])`) for premium Swagger documentation.

### Step 4: Develop the Repository
Create the repository file in `app/repositories/product_repository.py`.
- Declare a class decorated with `@dataclass` receiving `db: AsyncSession`.
- Implement CRUD methods by wrapping queries in a `try/except` block.
- Intercept errors by redirecting exceptions to `RepositoriesUtils.traiter_errors_en_global` passing the entity model.
- Always return a `CrudResult` object (or `DefaultAppCrudResult`).

### Step 5: Configure Cache
1. Define the cache key pattern in `BaseCacheEntity` and `AvailableCacheKeys` (in [app/cache/helpers/availables.py](file:///home/sevtify/Projets/fast-api-project-template/app/cache/helpers/availables.py)).
2. Declare the key in `CacheKeysFactory` (in [app/cache/helpers/keys_factory.py](file:///home/sevtify/Projets/fast-api-project-template/app/cache/helpers/keys_factory.py)) with its number of placeholders.
3. Create a dedicated cache class `ProductCache` in `app/cache/product_cache.py` to isolate Redis accesses.

### Step 6: Code the Business Service
Create the service file in `app/services/product_service.py`.
- Take `db: AsyncSession` and `cache: CacheWrapper` in the `__init__` constructor.
- Internally instantiate `ProductRepository` and `ProductCache`.
- Implement business logic: read cache first, query repository on cache-miss, save read data in cache, and return a `ServiceResult` (or `DefaultAppServiceResult`).
- Propagate repository failures to the service via `repo_res.to_service_error(service_name=self._service_name)`.

### Step 7: Create and Register the API Router
Create the router file in `app/routers/v1/product_router.py`.
- Create the `APIRouter` instance with appropriate tags.
- Inject the service with `Depends(get_product_service)`.
- Set the route's `response_model` to your concrete wrapper (e.g., `response_model=ProductInfos`).
- Specify the return annotation `-> ApiBaseResponse[ReadProduct, AppError]`.
- Register the new router in the main router [app/routers/v1/base_router.py](file:///home/sevtify/Projets/fast-api-project-template/app/routers/v1/base_router.py) via `v1_api_router.include_router(product_router)`.

---

## 3. Running the Project Locally

### Prerequisites
- Python 3.11+
- PostgreSQL database (or Dockerized)
- Redis (for cache and Celery)

### Quick Start

1. **Clone the project and prepare the environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Configure environment variables**:
   Copy the `.env.example` file to `.env` and adjust the PostgreSQL and Redis access parameters.
3. **Run database migrations**:
   ```bash
   alembic upgrade head
   ```
4. **Start the development server**:
   ```bash
   # Uses uvicorn under the hood to run the application on the configured port
   python app/main.py
   ```
5. **Access API documentation**:
   Open your browser to [http://localhost:8000/docs](http://localhost:8000/docs) to view the interactive Swagger.

### Starting Celery Workers (Background Tasks)
If your project uses Celery for asynchronous processing, start the Celery worker from the project root:
```bash
celery -A app.worker.celery_app worker --loglevel=info
```

---

## 4. Docker & Quick Start

This project includes a complete Docker configuration that is **operational and ready to use** out of the box. The setup is designed for immediate use - just copy, paste, and run!

### GitHub Template Repository
This repository is configured as a **GitHub Template Repository**. You can create a new repository from this template with one click:
- Click "Use this template" on GitHub
- Select "Create a new repository"
- Clone your new repository and you're ready to go!

### Docker Compose Setup
The `docker-compose.yml` file provides a complete development environment with:
- **PostgreSQL 15** (Alpine) - Database service with health checks
- **Redis 7** (Alpine) - Cache and message broker with persistence
- **FastAPI Backend** - Main application server with auto-reload
- **Celery Worker** - Background task processing (commented out by default)

All services include:
- ✅ Health checks for automatic dependency management
- ✅ Volume persistence for data
- ✅ Automatic restart on failure
- ✅ Service dependencies (API waits for DB and Redis to be healthy)

### Environment Configuration
The `.env.example` file contains a **ready-to-use configuration**:

```env
ENVIRONMENT=LOCAL
DATABASE_USER=admin
DATABASE_PASSWORD=password
DATABASE_TYPE=postgresql
DATABASE_PILOT=asyncpg
DATABASE_HOST=db:5432
BD_OUTPUT_PORT=5433
DATABASE_NAME=app_db
SECRET_KEY=change-me
API_PORT=8000
REDIS_CACHE_PORT=6379
REDIS_URL=redis://app_redis:6379/0
```

**This configuration is fully operational** with the provided `docker-compose.yml`. Simply:
1. Copy `.env.example` to `.env`
2. Run `docker compose up -d`
3. Your application will be available at `http://localhost:8000`

### Makefile Commands
The included `Makefile` provides convenient shortcuts for common Docker operations:

| Command | Description |
|---------|-------------|
| `make build_docker` | Build Docker images |
| `make rebuild_docker` | Rebuild Docker images without cache |
| `make start_docker` | Start all services in detached mode |
| `make stop_docker` | Stop and remove all containers |
| `make restart_api` | Restart only the API service |
| `make migrate-up` | Run database migrations |
| `make migrate-down` | Rollback last migration |
| `make migrate-gen` | Generate new migration (use with: `make migrate-gen msg="your message"`) |

**Example workflow:**
```bash
# Start everything
make start_docker

# Run migrations
make migrate-up

# Stop everything
make stop_docker
```

> [!TIP]
> The Makefile automatically handles user permissions on Linux/Mac (avoiding file ownership issues) and works seamlessly on Windows with Docker Desktop.

---

## 📚 Documentation Language Notes

All documentation files in the `docs/` directory are available in both **English** and **French**:
- English versions have the `_en.md` suffix
- French versions have the `_fr.md` suffix

Each documentation file contains a notice at the top indicating the availability of the other language version.
