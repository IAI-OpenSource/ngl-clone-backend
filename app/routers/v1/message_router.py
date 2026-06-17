from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.base.cache_wrapper import CacheWrapper, get_redis
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.globals.businnes_error import AppError
from app.schemas.globals.api_base_response import ApiBaseResponse
from app.schemas.message_schemas import (
    CreateMessage,
    ListMessagesInfos,
    MessageInfos,
    ReadMessage,
)
from app.services.message_service import MessageService
from app.schemas.thread_schemas import ThreadAuthPayload
from app.auth.dependencies import get_connected_thread

router = APIRouter(prefix="/messages", tags=[ApiTags.MESSAGES])


def get_message_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheWrapper, Depends(get_redis)],
) -> MessageService:
    return MessageService(db, cache)


@router.post("/", response_model=MessageInfos)
async def create_message(
    message_data: CreateMessage,
    response: Response,
    thread: Annotated[ThreadAuthPayload, Depends(get_connected_thread)],
    message_service: Annotated[MessageService, Depends(get_message_service)],
) -> ApiBaseResponse[ReadMessage, AppError]:
    """Route pour ajouter un message à un thread."""

    service_result = await message_service.service_create_message(
        message_data=message_data,
        thread_id=thread.thread_id
    )

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get("/thread/", response_model=ListMessagesInfos)
async def get_thread_messages(
    response: Response,
    message_service: Annotated[MessageService, Depends(get_message_service)],
    thread: Annotated[ThreadAuthPayload, Depends(get_connected_thread)],
) -> ApiBaseResponse[list[ReadMessage], AppError]:
    """Route pour récupérer les messages du thread auquel on est actuellemnt connecté"""

    service_result = await message_service.service_get_messages_by_thread_id(
        thread_id=UUID(thread.thread_id)
    )

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.get("/{message_id}", response_model=MessageInfos)
async def get_message_by_id(
    message_id: Annotated[UUID, Path(..., description="ID du message à récupérer")],
    response: Response,
    message_service: Annotated[MessageService, Depends(get_message_service)],
    thread: Annotated[ThreadAuthPayload, Depends(get_connected_thread)],
) -> ApiBaseResponse[ReadMessage, AppError]:
    """Route pour récupérer un message par son ID."""

    service_result = await message_service.service_find_message_by_id(
        message_id=message_id,
        connected_thread=thread
    )

    return service_result.to_HTTP_api_base_response(reponse=response)
