from typing import Any

from app.schemas.globals.others_schemas import AuthErrorMessage, InternalServerErrorSchema

_ResponseSchemasType = dict[int | str, dict[str, Any]]
class ApiUtilsSchemas:
    COMMON_API_RESPONSES: _ResponseSchemasType = {
        500: {
            "description": "Internal Server Error",
            "model": InternalServerErrorSchema,
        },
    }

    AUTH_REQUIRED_RESPONSES: _ResponseSchemasType = {
        401: {"description": "Unauthorized", "model": AuthErrorMessage},
        403: {"description": "Forbidden", "model": AuthErrorMessage},
    }
