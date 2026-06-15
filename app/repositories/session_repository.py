from dataclasses import dataclass
import logging
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.session import Session
from app.globals.businnes_error import AppError, AppErrorType
from app.repositories import DefaultAppCrudResult, CrudResult
from app.repositories.helpers.repositories_utils import RepositoriesUtils
from app.schemas.session_schemas import CreateSession
from app.utils.security_utils import hasher_password
from app.globals.messages import Messages
from fastapi import status
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SessionRepository:

    db: AsyncSession

    async def insert_session(
        self, session_data: CreateSession
    ) -> DefaultAppCrudResult[Session]:
        """Fonction pour insérer une session en bd"""

        try:

            stmt = (
                insert(Session)
                .values(
                    **session_data.model_dump(exclude={"ref_token"}),
                    refresh_token_hash=hasher_password(session_data.ref_token)
                )
                .returning(Session)
            )

            result = await self.db.execute(stmt)
            db_session = result.scalar_one()
            await self.db.commit()

            logger.info("Session ajoutée avec succès !")
            return CrudResult.crud_success(
                db_session, status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Session
            )

    async def get_session_by_sid(self, sid: UUID) -> DefaultAppCrudResult[Session]:
        """Fonction pour récupérer une session à partir de son ID"""

        try:

            stmt = select(Session).where(Session.id == sid)
            result = await self.db.execute(stmt)
            session = result.scalar_one_or_none()

            if session is None:
                logger.info("Session non Trouvé")
                return CrudResult.crud_failure(
                    AppError(
                        error_message=Messages.NOT_FOUND,
                        error_type=AppErrorType.NOT_FOUND,
                    ),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            logger.info("Session récupérer avec succès !")
            return CrudResult.crud_success(session)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Session
            )

    async def delete_session(self, sid: UUID) -> DefaultAppCrudResult[None]:
        """Fonction pour supprimer une session à partir de son ID"""
        try:
            session = await self.get_session_by_sid(sid)

            if session.is_error():
                return CrudResult.crud_failure(
                    session.error, status_code=session.status_code
                )

            await self.db.delete(session.data)
            await self.db.commit()

            return CrudResult.crud_success(None, status_code=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Session
            )

    async def revoke_session(self, sid: UUID) -> DefaultAppCrudResult[None]:
        """Fonction pour révoquer une session à partir de son ID"""
        try:
            session = await self.get_session_by_sid(sid)

            if session.is_error():
                return CrudResult.crud_failure(
                    session.error, status_code=session.status_code
                )

            session = session.data

            session.expires_at = datetime.now()

            await self.db.commit()

            return CrudResult.crud_success(None, status_code=status.HTTP_200_OK)
        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, Session
            )
