# HTTP Routers, Pydantic Schemas & Middlewares

This document describes the operation of the API layer, the configuration of responses for quality Swagger, and global middlewares.

---

> **📄 Documentation Available in French**
> A French version of this document is available: [routers_and_schemas_fr.md](./routers_and_schemas_fr.md)

---

## 1. Routers & Service Dependencies

FastAPI routers receive requests, validate incoming data, and immediately delegate work to the relevant services.

### 1.1. Service Injection
Service injection is done at the route function signature level using `Annotated` and `Depends`. Local factory functions (like `get_user_service`) create service instances by injecting infrastructure resources (database and cache):

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.cache.base.cache_wrapper import get_redis, CacheWrapper
from app.services.user_service import UserService

router = APIRouter(prefix="/users")

def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheWrapper, Depends(get_redis)]
) -> UserService:
    return UserService(db, cache)
```

---

## 2. Premium Configuration for Swagger / OpenAPI

To obtain clean and professional Swagger UI documentation, without auto-generated schemas with unreadable names (e.g., `ApiBaseResponse_ReadUser_AppError_`), strictly follow the following rule:

> [!IMPORTANT]
> - **`response_model` (FastAPI)**: Always use a concrete subclass inheriting from `DefaultAppApiResponse[T]` (e.g., `UserInfos`). This concrete type drives the OpenAPI documentation and final serialization.
> - **Return annotation (`-> ...` Python)**: Use `ApiBaseResponse[D, E]` (e.g., `ApiBaseResponse[ReadUser, AppError]`). This is the actual type returned by the helper method `to_HTTP_api_base_response()`, which prevents static type checker complaints.

### Complete Example of a Clean Route:
```python
# 1. Definition of the concrete schema (in app/schemas/user_schemas.py)
class UserInfos(DefaultAppApiResponse[ReadUser]):
    """Response wrapper schema for user information"""

# 2. Usage in the router (in app/routers/v1/auth_router.py)
@router.get("/me", response_model=UserInfos)
async def me(
    response: Response,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiBaseResponse[ReadUser, AppError]:
    """Retrieve information of the currently logged-in user"""
    
    service_res = auth_service.get_me(user=current_user)
    
    # to_HTTP_api_base_response injects the HTTP status and builds the ApiBaseResponse
    return service_res.to_HTTP_api_base_response(reponse=response)
```

---

## 3. Global Middlewares

The HTTP request processing cycle is secured by middlewares that intercept requests and responses.

### 3.1. Uncaught Exception Handling (`exception_handler_middleware.py`)
This middleware intercepts all uncaught Python exceptions within the application (which would otherwise appear as raw errors or empty responses):
- Logs the complete error traceback via `logger.exception`.
- Translates and returns a standardized HTTP 500 JSON response respecting the [DefaultAppApiResponse](../app/schemas/globals/api_base_response.py) schema, containing the `UNKNOWN_ERROR` error with the user message: *"An internal error occurred. Please try again later."*

### 3.2. Logging and Slow Request Alert (`request_logging_middleware.py`)
This middleware traces each incoming and outgoing HTTP request.
- Logs the HTTP method, URL path of the request, returned status code, and exact execution duration in seconds.
- **Slow Request Alert**: If a request's execution time exceeds **1 second**, a `WARNING` level log is automatically generated with the `SLOW REQUEST` tag to facilitate identification of heavy requests or database issues.
