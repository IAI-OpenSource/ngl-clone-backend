# Results and Errors Management (Generic Results & Errors)

This document explains how the application's standardized return system works and how to use it to manage both success data and errors in a type-safe manner across the **Repository**, **Service**, **Integration**, and **API** layers.

The source code associated with this system is located in [app/globals/app_result.py](../app/globals/app_result.py).

---

> **📄 Documentation Available in French**
> A French version of this document is available: [results_and_errors_fr.md](./results_and_errors_fr.md)

---

## 1. Basic Principles

All internal application responses inherit from a generic base class: `GenericAppResult[D, E]`.
- **`D`** represents the type of data returned in case of **success** (e.g., a Pydantic model, a primitive type, `None`, etc.).
- **`E`** represents the type of error returned in case of **failure** (by default, `AppError`).

The system provides three specialized classes for each architecture layer:
1. **`CrudResult[D, E]`** ([Repository](../app/repositories/__init__.py) layer)
2. **`ServiceResult[D, E]`** ([Service](../app/services/__init__.py) layer)
3. **`IntegrationServiceResult[D, E]`** ([External Integrations](../app/integrations/__init__.py) layer)

---

## 2. Standard Usage (Default Errors: `AppError`)

In most cases, the default [AppError](../app/globals/businnes_error.py) is sufficient.

To simplify writing and improve code readability, type aliases preconfigured with `AppError` are available:
- **`DefaultAppCrudResult[D]`** is an alias for `CrudResult[D, AppError]`
- **`DefaultAppServiceResult[D]`** is an alias for `ServiceResult[D, AppError]`
- **`DefaultAppIntegrationServiceResult[D]`** is an alias for `IntegrationServiceResult[D, AppError]`
- **`DefaultAppApiResponse[D]`** is an alias for `ApiBaseResponse[D, AppError]`

These aliases require only one generic parameter (the success data type `D`).

### Example in a Repository:

```python
from app.repositories import DefaultAppCrudResult, CrudResult
from app.schemas.user_schemas import ReadUser  # Pydantic model
from app.globals.businnes_error import AppError, AppErrorType

async def get_user_by_id(user_id: UUID) -> DefaultAppCrudResult[User]:
    user = await db.get(User, user_id)
    if not user:
        # The default error is AppError
        error = AppError(
            error_type=AppErrorType.NOT_FOUND,
            error_message="User does not exist."
        )
        return CrudResult.crud_failure(error, status_code=404)

    return CrudResult.crud_success(user)
```

### Example in a Service (Propagation and Conversion):

```python
from app.services import DefaultAppServiceResult, ServiceResult
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import ReadUser

async def get_user_profile(user_id: UUID) -> DefaultAppServiceResult[ReadUser]:
    # Call to repository
    repo_res = await UserRepository(db).get_user_by_id(user_id)

    if repo_res.is_error():
        # Direct conversion of the CrudResult error into a ServiceResult error.
        # The error type (AppError) and status code (404) are preserved.
        return repo_res.to_service_error(service_name="UserService")

    read_user = ReadUser.model_validate(repo_res.data)
    return ServiceResult.service_success(read_user)
```

---

## 3. Advanced Usage (Custom Errors)

If an operation requires a specific error structure (e.g., complex validation errors, details specific to a third-party service), you can define a custom error model and pass it as the second generic parameter.

### Step 1: Define the Custom Error Model
```python
from pydantic import BaseModel

class PaymentErrorDetail(BaseModel):
    transaction_id: str
    failure_code: str
    user_message: str
```

### Step 2: Specify the Error Type in the Result
```python
from app.services import ServiceResult

def process_payment(amount: float) -> ServiceResult[PaymentResponse, PaymentErrorDetail]:
    payment_status, details = stripe_client.charge(amount)
    
    if not payment_status:
        custom_err = PaymentErrorDetail(
            transaction_id=details.id,
            failure_code=details.code,
            user_message="Your balance is insufficient."
        )
        return ServiceResult.service_failure(custom_err, status_code=402)
        
    return ServiceResult.service_success(PaymentResponse(status="success"))
```

---

## 4. API Integration & OpenAPI / Swagger Generation

For FastAPI to correctly generate interactive documentation (Swagger UI) and validate the HTTP response, you must configure your route's return.

### Approach A: Direct Generic Specification
You can directly annotate your route with `ApiBaseResponse[DataType, ErrorType]`:

```python
from fastapi import APIRouter, Response
from app.schemas.globals.api_base_response import ApiBaseResponse

router = APIRouter()

@router.post("/pay", response_model=ApiBaseResponse[PaymentResponse, PaymentErrorDetail])
async def pay(response: Response) -> ApiBaseResponse[PaymentResponse, PaymentErrorDetail]:
    service_res = payment_service.process_payment(100.0)
    
    # to_HTTP_api_base_response handles the correct instantiation of the response schema
    # and modifies the HTTP status_code of the Response object
    return service_res.to_HTTP_api_base_response(response)
```

### Approach B: By Subclassing (Recommended for Cleaner Swagger)
Direct use of nested generic types can sometimes generate hard-to-read auto-generated schema names in Swagger (e.g., `ApiBaseResponse_PaymentResponse_PaymentErrorDetail_`).

For a premium Swagger rendering and explicit schemas, create a concrete subclass:

```python
# app/schemas/payment.py
from app.schemas.globals.api_base_response import ApiBaseResponse

class PaymentApiResponse(ApiBaseResponse[PaymentResponse, PaymentErrorDetail]):
    """Standardized response for payment operations"""
    # No need to redeclare fields, they are inherited and typed automatically!
```

Then in your router, use this subclass as `response_model`, but annotate the Python return with the type actually returned by `to_HTTP_api_base_response`.
The helper currently returns `ApiBaseResponse[D, E]`, not the concrete subclass `PaymentApiResponse`. A type checker cannot therefore automatically infer that `ApiBaseResponse[PaymentResponse, PaymentErrorDetail]` is compatible with `PaymentApiResponse`, even if FastAPI/Pydantic validate the response correctly at runtime.

```python
@router.post("/pay", response_model=PaymentApiResponse)
async def pay(response: Response) -> ApiBaseResponse[PaymentResponse, PaymentErrorDetail]:
    service_res = payment_service.process_payment(100.0)
    
    # The return is converted and validated properly
    return service_res.to_HTTP_api_base_response(response)
```

For simple routes that do not have a custom error schema, there is a preconfigured alias of `ApiBaseResponse` with `AppError`: `DefaultAppApiResponse[D]`. You can use it directly for clean Swagger documentation without having to specify the error type each time.

```python
from app.schemas.globals.api_base_response import DefaultAppApiResponse
from app.schemas.user_schemas import ReadUser

class ReadUserApiResponse(DefaultAppApiResponse[ReadUser]):
    """Standardized response for user operations"""
    # No need to redeclare fields, they are inherited and typed automatically!
```

Then in your router:
```python
@router.get("/users/{user_id}", response_model=ReadUserApiResponse)
async def read_user(user_id: UUID, response: Response) -> ApiBaseResponse[ReadUser, AppError]:
    service_res = await user_service.service_find_user_by_id(user_id)
    return service_res.to_HTTP_api_base_response(response)
```

In summary:
- `response_model=ReadUserApiResponse` serves FastAPI, output validation, and Swagger/OpenAPI.
- `-> ApiBaseResponse[ReadUser, AppError]` serves Python static typing, as it is the type actually returned by `to_HTTP_api_base_response`.
- Annotating the route with `-> ReadUserApiResponse` generally causes a typing error as long as the helper does not explicitly build this subclass.

---

## 5. Best Practices & Anti-patterns

> [!TIP]
> - **Always use class helpers** (`crud_success`, `service_failure`, etc.) instead of directly instantiating classes via `__init__`.
> - **Use the subclassing approach of `ApiBaseResponse` or `DefaultAppApiResponse` in `response_model`** for all public routes to keep your Swagger documentation clear and professional.
> - **Keep the return annotation aligned with the helper used**: with `to_HTTP_api_base_response`, annotate with `ApiBaseResponse[D, E]`, not the concrete OpenAPI subclass.

> [!WARNING]
> - **Do not shortcut typing** by using `Any` as the error type if you know the error structure. Specifying the structure allows the frontend to have rigorous typing generated via OpenAPI.
> - **Do not confuse `response_model` and return annotation**: `response_model` drives FastAPI/OpenAPI, the `-> ...` annotation drives the type checker.
