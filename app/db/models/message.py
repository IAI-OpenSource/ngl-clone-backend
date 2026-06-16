"""
Modèle pour la table messages.
Gère les messages envoyés dans les threads avec synchronisation WhatsApp.
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
    Boolean,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base
from app.db.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums.enums import WAStatus

if TYPE_CHECKING:
    from app.db.models.thread import Thread
    from app.db.models.message_mention import MessageMention
    from app.db.models.wa_delivery_log import WADeliveryLog


# Noms des contraintes
FK_MESSAGES_THREAD = "fk_messages_thread"
IDX_MESSAGES_THREAD_CREATED = "idx_messages_thread_created"
IDX_MESSAGES_WA_STATUS = "idx_messages_wa_status"
IDX_MESSAGES_WA_STATUS_CREATED = "idx_messages_wa_status_created"


class Message(Base, IntegrityMapperMixin):
    """Représentation d'un message dans un thread."""

    __tablename__ = "messages"

    # Propriétés de base
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, init=False
    )

    # Relation avec le thread
    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE", name=FK_MESSAGES_THREAD),
        nullable=False,
    )

    # Contenu du message
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Identifiants WhatsApp
    wa_message_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    wa_status: Mapped[WAStatus] = mapped_column(
        SQLEnum(WAStatus), nullable=False, default=WAStatus.PENDING, init=False
    )
    wa_forwarded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, init=False
    )

    # Masquage du message
    is_hidden: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, init=False
    )
    hidden_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hidden_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, init=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, init=False
    )

    # Index
    __table_args__ = (
        Index(
            IDX_MESSAGES_THREAD_CREATED,
            "thread_id",
            "created_at",
            postgresql_using="btree",
        ),
        Index(
            IDX_MESSAGES_WA_STATUS_CREATED,
            "wa_status",
            "created_at",
            postgresql_where=wa_status.in_([WAStatus.PENDING, WAStatus.FAILED]),
        ),
    )

    # Relations
    thread: Mapped["Thread"] = relationship(
        "Thread",
        foreign_keys=[thread_id],
        back_populates="messages",
        uselist=False,
        init=False,
    )
    mentions: Mapped[list["MessageMention"]] = relationship(
        "MessageMention",
        back_populates="message",
        cascade="all, delete-orphan",
        uselist=True,
        init=False,
    )
    wa_delivery_logs: Mapped[list["WADeliveryLog"]] = relationship(
        "WADeliveryLog",
        back_populates="message",
        cascade="all, delete-orphan",
        uselist=True,
        init=False,
    )

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_MESSAGES_THREAD: "Le thread spécifié n'existe pas.",
    }