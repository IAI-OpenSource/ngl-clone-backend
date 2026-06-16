from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, Request
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.base.cache_wrapper import CacheWrapper, get_redis
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.globals.businnes_error import AppError
from app.schemas.globals.api_base_response import ApiBaseResponse
from app.schemas.thread_schemas import ReadThread, ThreadInfos, ListThreadsInfos
from app.services.thread_service import ThreadService
from app.schemas.globals.utils_schemas import GlobalStringResponse, StringMessage
from app.schemas.thread_schemas import ThreadAuthRequest
from app.services.auth_thread_service import AuthThreadService

router = APIRouter(prefix="/threads", tags=[ApiTags.THREADS])


def get_thread_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheWrapper, Depends(get_redis)],
) -> ThreadService:
    return ThreadService(db, cache)


def get_auth_thread_service(
    response: Response,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheWrapper, Depends(get_redis)],
) -> AuthThreadService:
    return AuthThreadService(db, cache, response, request)


@router.get("/", response_model=ListThreadsInfos)
async def get_all_threads(
    response: Response,
    thread_service: Annotated[ThreadService, Depends(get_thread_service)],
) -> ApiBaseResponse[list[ReadThread], AppError]:
    """Route pour récupérer tous les threads."""

    service_result = await thread_service.service_find_all_threads()

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get("/slug/{slug}", response_model=ThreadInfos)
async def get_thread_by_slug(
    slug: Annotated[str, Path(..., description="Le slug du thread à récupérer")],
    response: Response,
    thread_service: Annotated[ThreadService, Depends(get_thread_service)],
) -> ApiBaseResponse[ReadThread, AppError]:
    """Route pour récupérer un thread par son slug."""

    service_result = await thread_service.service_find_thread_by_slug(slug=slug)

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get("/{thread_id}", response_model=ThreadInfos)
async def get_thread_by_id(
    thread_id: Annotated[UUID, Path(..., description="ID du thread à récupérer")],
    response: Response,
    thread_service: Annotated[ThreadService, Depends(get_thread_service)],
) -> ApiBaseResponse[ReadThread, AppError]:
    """Route pour récupérer un thread par son ID."""

    service_result = await thread_service.service_find_thread_by_id(thread_id=thread_id)

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get("/{thread_id}/auth", response_model=GlobalStringResponse, tags=[ApiTags.AUTHENTIFICATION])
async def get_thread_by_id(
    thread_id: Annotated[
        UUID, Path(..., description="ID du thread auquel on ve se connecter")
    ],
    body: ThreadAuthRequest,
    response: Response,
    thread_service: Annotated[AuthThreadService, Depends(get_auth_thread_service)],
) -> ApiBaseResponse[StringMessage, AppError]:
    """Route pour se connecter à un thread par son ID.
    Cette route peut être utilisée pour vérifier l'existence du thread et obtenir les informations nécessaires à la connexion (comme le slug).
    """

    service_result = await thread_service.service_connect_thread(thread_id=thread_id, thread_password=body.password)

    return service_result.to_HTTP_api_base_response(reponse=response)
