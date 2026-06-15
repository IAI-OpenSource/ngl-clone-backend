from logging import getLogger

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.globals.businnes_error import AppError, AppErrorType
from app.globals.messages import Messages
from app.schemas.globals.api_base_response import DefaultAppApiResponse

logger = getLogger("exception_handler")


async def handle_exceptions(request: Request, call_next) -> Response:
    """
    Middleware pour intercepter et gérer les exceptions globales non gérées par FastAPI.

    Ce middleware:
    1. Log l'exception avec le traceback complet pour le débogage
    2. Retourne une réponse 500 standardisée utilisant ApiBaseResponse

    Args:
        request: La requête entrante
        call_next: Fonction pour appeler le prochain middleware/endpoint

    Returns:
        Response: La réponse HTTP (soit normale, soit une réponse d'erreur 500)
    """
    try:
        return await call_next(request)
    except Exception as e:
        # Logger l'exception avec le traceback complet
        logger.exception(
            f"Exception non gérée: {e.__class__.__name__} - {e}", exc_info=e
        )

        error_response = DefaultAppApiResponse.error_response(
            error_message=AppError(
                error_type=AppErrorType.UNKNOWN_ERROR,
                error_message=Messages.INTERNAL_SERVER_ERROR,
            ),
            response=Response(),
            status_code=500,
        )

        return JSONResponse(content=error_response.model_dump(), status_code=500)
