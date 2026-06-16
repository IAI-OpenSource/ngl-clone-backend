"""
Repository pour la table wa_delivery_log.
Gère les opérations CRUD sur les logs de livraison WhatsApp.
"""

from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.wa_delivery_log import WADeliveryLog
from app.db.models.enums.enums import WAStatus
from app.repositories import DefaultAppCrudResult, CrudResult
from app.repositories.helpers.repositories_utils import RepositoriesUtils

logger = getLogger(__name__)


@dataclass
class WADeliveryLogRepository:
    """Repository pour la gestion des logs de livraison WhatsApp."""

    db: AsyncSession

    async def insert_delivery_log(
        self,
        message_id: UUID,
        delivery_status: WAStatus,
        error_code: Optional[str] = None,
        error_msg: Optional[str] = None,
        payload: Optional[dict] = None,
        attempted_at: Optional[datetime] = None,
    ) -> DefaultAppCrudResult[WADeliveryLog]:
        """Fonction pour insérer un log de livraison en base de données."""
        try:
            delivery_log = WADeliveryLog(
                message_id=message_id,
                status=delivery_status,
                error_code=error_code,
                error_msg=error_msg,
                payload=payload,
            )
            # attempted_at a init=False, on l'assigne après
            if attempted_at is not None:
                delivery_log.attempted_at = attempted_at
            
            self.db.add(delivery_log)
            await self.db.commit()
            await self.db.refresh(delivery_log)

            logger.info(f"Log de livraison pour message {message_id} ajouté avec succès !")
            return CrudResult.crud_success(
                data=delivery_log, status_code=status.HTTP_201_CREATED
            )

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WADeliveryLog
            )

    async def get_delivery_log_by_id(
        self, log_id: UUID
    ) -> DefaultAppCrudResult[WADeliveryLog]:
        """Fonction pour récupérer un log de livraison à partir de son ID."""
        try:
            stmt = select(WADeliveryLog).where(WADeliveryLog.id == log_id)
            result = await self.db.execute(stmt)
            delivery_log = result.scalar_one_or_none()

            if delivery_log is None:
                logger.info(f"Log de livraison avec ID {log_id} non trouvé")
                return CrudResult.crud_failure(
                    RepositoriesUtils.not_found_error("Log de livraison inexistant"),
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            return CrudResult.crud_success(data=delivery_log)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(
                e, self.db, logger
            )

    async def get_delivery_logs_by_message_id(
        self, message_id: UUID
    ) -> DefaultAppCrudResult[list[WADeliveryLog]]:
        """Fonction pour récupérer tous les logs de livraison d'un message."""
        try:
            stmt = select(WADeliveryLog).where(WADeliveryLog.message_id == message_id)
            result = await self.db.execute(stmt)
            delivery_logs = list(result.scalars().all())

            return CrudResult.crud_success(data=delivery_logs)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WADeliveryLog
            )

    async def get_delivery_logs_by_status(
        self, delivery_status: WAStatus
    ) -> DefaultAppCrudResult[list[WADeliveryLog]]:
        """Fonction pour récupérer tous les logs de livraison par statut."""
        try:
            stmt = select(WADeliveryLog).where(WADeliveryLog.status == delivery_status)
            result = await self.db.execute(stmt)
            delivery_logs = list(result.scalars().all())

            return CrudResult.crud_success(data=delivery_logs)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WADeliveryLog
            )

    async def get_failed_delivery_logs(
        self
    ) -> DefaultAppCrudResult[list[WADeliveryLog]]:
        """Fonction pour récupérer tous les logs de livraison en échec."""
        try:
            stmt = select(WADeliveryLog).where(WADeliveryLog.status == WAStatus.FAILED)
            result = await self.db.execute(stmt)
            delivery_logs = list(result.scalars().all())

            return CrudResult.crud_success(data=delivery_logs)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WADeliveryLog
            )

    async def update_delivery_log_status(
        self,
        log_id: UUID,
        delivery_status: WAStatus,
        error_code: Optional[str] = None,
        error_msg: Optional[str] = None,
    ) -> DefaultAppCrudResult[WADeliveryLog]:
        """Fonction pour mettre à jour le statut d'un log de livraison."""
        try:
            old_log = await self.get_delivery_log_by_id(log_id)

            if old_log.is_error():
                return old_log

            old_log.data.status = delivery_status
            if error_code is not None:
                old_log.data.error_code = error_code
            if error_msg is not None:
                old_log.data.error_msg = error_msg

            await self.db.commit()

            logger.info(f"Log de livraison {log_id} mis à jour avec succès")
            return CrudResult.crud_success(data=old_log.data)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WADeliveryLog
            )

    async def delete_delivery_log(self, log_id: UUID) -> DefaultAppCrudResult[None]:
        """Fonction pour supprimer un log de livraison de la base de données."""
        try:
            delivery_log = await self.get_delivery_log_by_id(log_id)

            if delivery_log.is_error():
                return CrudResult.crud_failure(
                    delivery_log.error, status_code=delivery_log.status_code
                )

            await self.db.delete(delivery_log.data)
            await self.db.commit()

            logger.info(f"Log de livraison {log_id} supprimé avec succès")
            return CrudResult.crud_success(None, status_code=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, WADeliveryLog
            )
