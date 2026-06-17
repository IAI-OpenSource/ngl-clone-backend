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
from app.schemas.thread_schemas import (
    CreateThread,
    ReadThread,
    ThreadInfos,
    ListThreadsInfos,
)
from app.services.thread_service import ThreadService
from app.schemas.globals.utils_schemas import GlobalStringResponse, StringMessage
from app.schemas.thread_schemas import ThreadAuthRequest
from app.services.auth_thread_service import AuthThreadService
from app.schemas.thread_schemas import ThreadAuthPayload
from app.auth.dependencies import get_connected_thread
from app.schemas.globals.api_utils_schemas import ApiUtilsSchemas

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


@router.post("/", response_model=ThreadInfos, summary="Créer un nouveau thread")
async def create_thread(
    thread_data: CreateThread,
    response: Response,
    thread_service: Annotated[ThreadService, Depends(get_thread_service)],
) -> ApiBaseResponse[ReadThread, AppError]:
    """Route pour créer un thread."""

    service_result = await thread_service.service_create_thread(thread_data=thread_data)

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get("/", response_model=ListThreadsInfos, summary="Lister tous les threads")
async def get_all_threads(
    response: Response,
    thread_service: Annotated[ThreadService, Depends(get_thread_service)],
) -> ApiBaseResponse[list[ReadThread], AppError]:
    """Route pour récupérer tous les threads."""

    service_result = await thread_service.service_find_all_threads()

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get(
    "/actual", response_model=ThreadInfos,
    tags=[ApiTags.AUTHENTIFICATION], summary="Obtenir le thread actuellement connecté",
    responses=ApiUtilsSchemas.AUTH_REQUIRED_RESPONSES
)
async def get_connected_thread(
        response: Response,
        thread: Annotated[ThreadAuthPayload, Depends(get_connected_thread)],
        thread_service: Annotated[ThreadService, Depends(get_thread_service)],
) -> ApiBaseResponse[ReadThread, AppError]:
    """Route pour obtenir le thread sur lequel le client est connecté actuellement, tu peux utiliser çà pour faire l'auth,
    Genre Firstly au chargement de l'app, tu fais une requete sur cette route pour savoir si le client est déjà connecté
     à un thread ou pas, si c'est le cas tu lui redirige vers la page du thread pour voir ou ajouter un message, si
     c'est pas le cas tu rediriges vers la route pour voir les threads et choisir celui auquel on veut se bind
    """

    service_result = await thread_service.service_find_thread_by_id(thread_id=UUID(thread.thread_id))

    return service_result.to_HTTP_api_base_response(reponse=response)

@router.get("/slug/{slug}", response_model=ThreadInfos, summary="Récupérer un thread par son slug")
async def get_thread_by_slug(
        slug: Annotated[str, Path(..., description="Le slug du thread à récupérer")],
        response: Response,
        thread_service: Annotated[ThreadService, Depends(get_thread_service)],
) -> ApiBaseResponse[ReadThread, AppError]:
    """Route pour récupérer un thread par son slug."""

    service_result = await thread_service.service_find_thread_by_slug(slug=slug)

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.post("/{thread_id}/auth", response_model=GlobalStringResponse, tags=[ApiTags.AUTHENTIFICATION], summary="Se connecter à un thread")
async def connect_to_a_thread(
    thread_id: Annotated[
        UUID, Path(..., description="ID du thread auquel on ve se connecter")
    ],
    body: ThreadAuthRequest,
    response: Response,
    thread_service: Annotated[AuthThreadService, Depends(get_auth_thread_service)],
) -> ApiBaseResponse[StringMessage, AppError]:
    """Route pour se connecter à un thread par son ID.
    """

    service_result = await thread_service.service_connect_thread(thread_id=thread_id, thread_password=body.password)

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get("/{thread_id}", response_model=ThreadInfos, summary="Récupérer un thread par son ID")
async def get_thread_by_id(
    thread_id: Annotated[UUID, Path(..., description="ID du thread à récupérer")],
    response: Response,
    thread_service: Annotated[ThreadService, Depends(get_thread_service)],
) -> ApiBaseResponse[ReadThread, AppError]:
    """Route pour récupérer un thread par son ID."""

    service_result = await thread_service.service_find_thread_by_id(thread_id=thread_id)

    return service_result.to_HTTP_api_base_response(reponse=response)





