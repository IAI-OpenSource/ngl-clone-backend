"""
Modèle pour la table wa_sync_log.
Logs de synchronisation des groupes WhatsApp.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Index,
    String,
    ForeignKey,
    Integer,
    JSON,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base
from app.db.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums.enums import WASyncType

if TYPE_CHECKING:
    from app.db.models.thread import Thread


# Noms des contraintes
FK_WA_SYNC_LOG_THREAD = "fk_wa_sync_log_thread"
IDX_WA_SYNC_THREAD = "idx_wa_sync_thread"


class WASyncLog(Base, IntegrityMapperMixin):
    """Représentation d'un log de synchronisation WhatsApp."""

    __tablename__ = "wa_sync_log"

    # Propriétés de base
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, init=False
    )

    # Relation avec le thread
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE", name=FK_WA_SYNC_LOG_THREAD),
        nullable=False,
    )

    # Type de synchronisation
    sync_type: Mapped[WASyncType] = mapped_column(
        SQLEnum(WASyncType), nullable=False
    )

    # Identifiant WhatsApp
    wa_jid: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Statistiques de synchronisation
    members_added: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, init=False
    )
    members_removed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, init=False
    )

    # Payload JSON
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, init=False
    )

    # Index
    __table_args__ = (
        Index(
            IDX_WA_SYNC_THREAD,
            "thread_id",
            "created_at",
            postgresql_using="btree",
        ),
    )

    # Relations
    thread: Mapped["Thread"] = relationship(
        "Thread",
        foreign_keys=[thread_id],
        back_populates="wa_sync_logs",
        uselist=False,
        init=False,
    )

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_WA_SYNC_LOG_THREAD: "Le thread spécifié n'existe pas.",
    }