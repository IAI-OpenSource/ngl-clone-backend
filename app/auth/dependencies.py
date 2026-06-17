from uuid import UUID

from fastapi import Depends, status, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from app.cache.base.cache_wrapper import CacheWrapper, get_redis
from app.db.session import get_db
from app.schemas.user_schemas import ReadUser
from app.services.session_service import SessionService
from app.auth.cookie_manager import CookieManager
from app.auth.jwt_manager import JWTManager
from app.core.config import JWT_COOKIE_ACCESS_ID, ACCESS_SECRET_KEY
from app.services.user_service import UserService
from app.core.config import JWT_THREAD_ACCESS_ID
from app.schemas.thread_schemas import ThreadAuthPayload
from app.services.auth_thread_service import AuthThreadService


class _UserAuthDependencies:

    def __init__(
        self,
        db: AsyncSession,
        response: Response,
        request: HTTPConnection,
        cache: CacheWrapper,
    ):
        self.db = db
        self.cookie = CookieManager(response=response, request=request)
        self.session_service = SessionService(self.db, cache)
        self.user_service = UserService(self.db, cache)

    async def get_current_user(self) -> ReadUser:
        """Fonction permettant de return le user actuellement connecter.
        Elle sera utiliser pr securiser certaine routes en exigant le token
        d'authentificatiion obtenu lors du login


        Args:
            self: Comme argument on prend par défaut l'objet _UserAuthDependencies()
            comme ça on a accès a une session de la bd et une instance cookie de la
            class CookieManager()

        Raises:
            HTTPException: Aucun clé d'access fourni !
            HTTPException: Clé d'accès invalide
            HTTPException: user.error
        Returns:
            ReadUser: return un objet ReadUser qui est les infos de user actuellement connecter
        """

        access_token = self.cookie.get_cookie(cookie_id=JWT_COOKIE_ACCESS_ID)

        if access_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Vous n'etes pas connecté",
            )

        payload = JWTManager.decode_access_token(
            token=access_token, enc_dec_key=ACCESS_SECRET_KEY
        )

        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé d'accès invalide"
            )

        user_session = await self.session_service.service_find_session_by_sid(
            sid=UUID(payload["sid"])
        )

        if user_session.is_error():
            raise HTTPException(
                status_code=user_session.status_code, detail=user_session.error
            )

        user = await self.user_service.service_find_user_by_id(
            user_session.data.user_id
        )

        if user.is_error():
            raise HTTPException(detail=user.error, status_code=user.status_code)

        return user.data


class _ThreadAuthDependencies:
    def __init__(
            self,
            db: AsyncSession,
            response: Response,
            request: HTTPConnection,
            cache: CacheWrapper,
    ):
        self.db = db
        self.cookie = CookieManager(response=response, request=request)
        self._thread_svc = AuthThreadService(self.db, cache, response, request)

    def get_connected_thread(self) -> ThreadAuthPayload:
        access_token = self.cookie.get_cookie(cookie_id=JWT_THREAD_ACCESS_ID)

        if access_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Vous n'etes connecté à aucun thread",
            )

        payload = JWTManager.decode_access_token(
            token=access_token, enc_dec_key=ACCESS_SECRET_KEY
        )

        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé d'accès invalide"
            )

        return ThreadAuthPayload.model_validate(payload)

# Fonction pour instancier ta classe avec tout ce qu'il faut
def _get_user_auth_deps(
    request: HTTPConnection,
    response: Response,
    db: AsyncSession = Depends(get_db),
    cache: CacheWrapper = Depends(get_redis),
) -> _UserAuthDependencies:
    return _UserAuthDependencies(db=db, response=response, request=request, cache=cache)

def _get_thread_auth_deps(
    request: HTTPConnection,
    response: Response,
    db: AsyncSession = Depends(get_db),
    cache: CacheWrapper = Depends(get_redis),
) -> _ThreadAuthDependencies:
    return _ThreadAuthDependencies(db=db, response=response, request=request, cache=cache)


# Dépendance finale pour récupérer le user
async def get_current_user(
    auth_deps: _UserAuthDependencies = Depends(_get_user_auth_deps),
) -> ReadUser:
    return await auth_deps.get_current_user()

# Dépendance finale pour récupérer le thread connecté
def get_connected_thread(
    auth_deps: _ThreadAuthDependencies = Depends(_get_thread_auth_deps),
) -> ThreadAuthPayload:
    return auth_deps.get_connected_thread()
