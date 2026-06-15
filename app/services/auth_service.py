## fichier contenant le service/logique métier de la table
## vous y trouverez les appels fonctions de repository
from datetime import UTC, datetime, timedelta
from logging import getLogger
import secrets
from uuid import UUID
from fastapi import HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.cookie_manager import CookieManager
from app.auth.jwt_manager import JWTManager
from app.core.config import (
    ACCESS_SECRET_KEY,
    JWT_COOKIE_ACCESS_ID,
    JWT_EXPIRES_SECONDES,
    SID_REF_COOKIE,
    REFRESH_TOKEN_EXPIRES_SECONDES,
)
from app.schemas.session_schemas import CreateSession
from app.services.session_service import SessionService
from app.utils.security_utils import verify_password
from app.cache.user_cache import UserCache
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import LoginData, ReadUser
from app.globals.cache_duration import CacheDuration
from fastapi import status
from . import ServiceResult, DefaultAppServiceResult
from ..cache.base.cache_wrapper import CacheWrapper
from ..globals.businnes_error import AppError, AppErrorType
from ..globals.services_names import ServicesNames
from ..schemas.globals.utils_schemas import StringMessage

logger = getLogger(__name__)


class AuthService:

    def __init__(
        self,
        db: AsyncSession,
        cache: CacheWrapper,
        response: Response,
        request: Request,
    ):
        self.__db = db
        self.__user_cache = UserCache(cache)
        self.__user_repo = UserRepository(self.__db)
        self.__session_service = SessionService(self.__db, cache)
        self.__cookie_manager = CookieManager(response=response, request=request)
        self._service_name = ServicesNames.AUTH_SERVICE

    async def login(self, login_data: LoginData) -> DefaultAppServiceResult[ReadUser]:
        """Logique métier pour récupérer un utilisateur à partir de
        son email: Beaucoup plus spécial pour la connexion"""

        db_user = await self.__user_repo.get_user_by_username(
            username=login_data.username
        )

        if db_user.is_error():
            return db_user.to_service_error(service_name=self._service_name)

        user_read = ReadUser.model_validate(db_user.data)
        if not verify_password(
            plain_password=login_data.password,
            hashed_password=db_user.data.password_hash,
        ):
            return ServiceResult.service_failure(
                error=AppError(
                    error_type=AppErrorType.UNAUTHORIZED,
                    error_message="Nom d'utilisateur ou mot de passe incorrect",
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
                service_name=self._service_name,
            )

        refresh_token = secrets.token_urlsafe(16)

        db_user_session = CreateSession(
            user_id=user_read.id,
            ref_token=refresh_token,
            ip_address=None,  ## géré cette partie après
            user_agent=self.__cookie_manager.request.headers.get("user-agent"),
            expires_at=datetime.now(UTC) + timedelta(days=1),  # 1 jours pour les test
        )
        created_session = await self.__session_service.service_create_session(
            db_user_session
        )
        if created_session.is_error():
            return ServiceResult.service_failure(
                error=created_session.error,
                status_code=created_session.status_code,
                service_name=self._service_name,
            )

        ## on cré ensuite le access plus court 15 min
        access_token = JWTManager.create_access_token(
            data_to_encode={"sid": str(created_session.data.id)},
            enc_dec_key=ACCESS_SECRET_KEY,
        )
        ref_token = JWTManager.create_access_token(
            data_to_encode={
                "sid": str(created_session.data.id),
                "ref_token_hash": created_session.data.refresh_token_hash,
            },
            enc_dec_key=ACCESS_SECRET_KEY,
        )

        self.__cookie_manager.add_cookie(
            cookie_id=JWT_COOKIE_ACCESS_ID,
            value=access_token,
            age=JWT_EXPIRES_SECONDES,
        )
        self.__cookie_manager.add_cookie(
            cookie_id=SID_REF_COOKIE,
            value=ref_token,
            age=REFRESH_TOKEN_EXPIRES_SECONDES,
        )

        await self.__user_cache.set_user_in_cache(
            user=user_read, ttl=CacheDuration.TWENTY_MINUTES
        )

        return ServiceResult.service_success(
            data=user_read, service_name=self._service_name
        )

    def _get_session_attributes(self) -> tuple[UUID, str]:
        access_token = self.__cookie_manager.get_cookie(cookie_id=SID_REF_COOKIE)
        if access_token is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'etes pas connecté",
            )

        payload = JWTManager.decode_access_token(
            token=access_token, enc_dec_key=ACCESS_SECRET_KEY
        )
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé d'accès invalide"
            )

        return UUID(payload["sid"]), payload["ref_token_hash"]

    ## ----------------- Service refresh token ------------------------ ##
    async def service_manage_refresh(self) -> DefaultAppServiceResult[StringMessage]:
        """Logique métier pour gérer le refresh token"""

        session_id, ref_token_hash = self._get_session_attributes()
        user_session = await self.__session_service.service_find_session_by_sid(
            sid=session_id
        )

        if user_session.is_error():
            raise HTTPException(
                status_code=user_session.status_code, detail=user_session.error
            )

        if user_session.data.refresh_token_hash != ref_token_hash:
            return ServiceResult.service_failure(
                error=AppError(
                    error_type=AppErrorType.UNAUTHORIZED,
                    error_message="Session invalide",
                ),
                status_code=status.HTTP_403_FORBIDDEN,
                service_name=self._service_name,
            )

        ## si la session est valide et est la bonne on cré un nouveau access token puis le cookie
        access_token = JWTManager.create_access_token(
            data_to_encode={"sid": str(user_session.data.id)},
            enc_dec_key=ACCESS_SECRET_KEY,
        )
        self.__cookie_manager.add_cookie(
            cookie_id=JWT_COOKIE_ACCESS_ID, value=access_token, age=JWT_EXPIRES_SECONDES
        )

        return ServiceResult.service_success(
            data=StringMessage(message="Nouveau access Token créé avec success"),
            service_name=self._service_name,
        )

    ## ---------------- Service pour gérer les déconnexion / logout ------------------ ##
    async def service_logout_account(self) -> DefaultAppServiceResult[StringMessage]:
        """Logique métier pour gérer les déconnexion / logout"""

        revoke_res = await self.__session_service.revoke_session(
            self._get_session_attributes()[0]
        )

        if revoke_res.is_error():
            return ServiceResult.service_failure(
                error=revoke_res.error,
                status_code=revoke_res.status_code,
                service_name=self._service_name,
            )
        ## qd le user veux se déconnecter, on supprime tou ses cookies simplement
        self.__cookie_manager.delete_cookie(cookie_id=JWT_COOKIE_ACCESS_ID)
        self.__cookie_manager.delete_cookie(cookie_id=SID_REF_COOKIE)

        return ServiceResult.service_success(
            data=StringMessage(message="Déconnexion effectué avec succès"),
            service_name=self._service_name,
        )

    def get_me(self, user: ReadUser) -> DefaultAppServiceResult[ReadUser]:
        """Logique métier pour récupérer les infos de l'utilisateur actuellement connecté"""

        return ServiceResult.service_success(
            data=user,
            service_name=self._service_name,
        )
