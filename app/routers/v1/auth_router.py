from typing import Annotated
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.base.cache_wrapper import get_redis, CacheWrapper
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.globals.businnes_error import AppError
from app.schemas.globals.api_base_response import ApiBaseResponse
from app.schemas.globals.utils_schemas import GlobalStringResponse, StringMessage
from app.schemas.user_schemas import CreateUser, LoginData, ReadUser, UserInfos
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=[ApiTags.AUTHENTIFICATION])


def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheWrapper, Depends(get_redis)],
) -> UserService:
    return UserService(db, cache)


def get_auth_service(
    response: Response,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: Annotated[CacheWrapper, Depends(get_redis)],
) -> AuthService:
    return AuthService(db, cache, response, request)


## ------------ Route pour créer un compte ------------ ##
@router.post("/register", response_model=UserInfos)
async def register(
    user_data: CreateUser,
    response: Response,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> ApiBaseResponse[ReadUser, AppError]:
    """Route pour Inscription utilisateur: Création de compte"""

    service_result = await user_service.service_create_user(user_data=user_data)

    return service_result.to_HTTP_api_base_response(reponse=response)


@router.post("/login", response_model=UserInfos)
async def login(
    login_data: LoginData,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiBaseResponse[ReadUser, AppError]:
    """Route d'authentification pour se connecter"""

    auth_service_result = await auth_service.login(login_data=login_data)

    return auth_service_result.to_HTTP_api_base_response(reponse=response)


## ------------- Route pour refresh le token et générer un nouveau access -------------- ##
@router.post(
    "/refresh",
    response_model=GlobalStringResponse,
)
async def refresh_token(
    response: Response, auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> ApiBaseResponse[StringMessage, AppError]:
    """Route d'authentification pour verifier le OTP"""

    auth_service_result = await auth_service.service_manage_refresh()

    return auth_service_result.to_HTTP_api_base_response(reponse=response)


## ------------- Route pour logout / se déconnecter -------------- ##
@router.post(
    "/logout",
    response_model=GlobalStringResponse,
)
async def logout(
    response: Response, auth_service: Annotated[AuthService, Depends(get_auth_service)]
) -> ApiBaseResponse[StringMessage, AppError]:
    """Route d'authentification pour logout / se déconnecter"""

    auth_service_result = await auth_service.service_logout_account()

    return auth_service_result.to_HTTP_api_base_response(reponse=response)


@router.get("/me", response_model=UserInfos)
async def me(
    response: Response,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiBaseResponse[ReadUser, AppError]:
    """Route pour récupérer les infos de l'utilisateur actuellement connecté"""

    res = auth_service.get_me(user=current_user)
    return res.to_HTTP_api_base_response(reponse=response)
