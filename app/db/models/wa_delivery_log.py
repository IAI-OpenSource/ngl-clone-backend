"""
Modèle pour la table wa_delivery_log.
Logs de livraison des messages WhatsApp.
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
    Text,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base
from app.db.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums.enums import WAStatus

if TYPE_CHECKING:
    from app.db.models.message import Message


# Noms des contraintes
FK_WA_DELIVERY_LOG_MESSAGE = "fk_wa_delivery_log_message"
IDX_WA_DELIVERY_MESSAGE = "idx_wa_delivery_message"


class WADeliveryLog(Base, IntegrityMapperMixin):
    """Représentation d'un log de livraison WhatsApp."""

    __tablename__ = "wa_delivery_log"

    # Propriétés de base
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, init=False
    )

    # Relation avec le message
    message_id: Mapped[UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE", name=FK_WA_DELIVERY_LOG_MESSAGE),
        nullable=False,
    )

    # Statut de livraison
    status: Mapped[WAStatus] = mapped_column(
        SQLEnum(WAStatus), nullable=False
    )

    # Erreurs
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Payload JSON
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, init=False
    )

    # Index
    __table_args__ = (
        Index(
            IDX_WA_DELIVERY_MESSAGE,
            "message_id",
            "attempted_at",
            postgresql_using="btree",
        ),
    )

    # Relations
    message: Mapped["Message"] = relationship(
        "Message",
        foreign_keys=[message_id],
        back_populates="wa_delivery_logs",
        uselist=False,
        init=False,
    )

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_WA_DELIVERY_LOG_MESSAGE: "Le message spécifié n'existe pas.",
    }