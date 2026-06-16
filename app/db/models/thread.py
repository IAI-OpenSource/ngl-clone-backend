"""
Modèle pour la table threads.
Gère les groupes de discussion (threads) avec synchronisation WhatsApp.
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
    Boolean,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base
from app.db.mixins.integrity_error_mixin import IntegrityMapperMixin

if TYPE_CHECKING:
    from app.db.models.message import Message
    from app.db.models.thread_member import ThreadMember
    from app.db.models.wa_sync_log import WASyncLog


# Noms des contraintes
UQ_THREADS_SLUG = "uq_threads_slug"
UQ_THREADS_WA_GROUP_JID = "uq_threads_wa_group_jid"
IDX_THREADS_WA_GROUP_JID = "idx_threads_wa_group_jid"
IDX_THREADS_IS_ACTIVE = "idx_threads_is_active"
IDX_THREADS_CREATED_AT = "idx_threads_created_at"


class Thread(Base, IntegrityMapperMixin):
    """Représentation d'un thread/groupe de discussion."""

    __tablename__ = "threads"

    # Propriétés de base
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, init=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Informations WhatsApp
    wa_group_jid: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    wa_group_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Sécurité
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Statut
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, init=False
    )

    # Synchronisation WhatsApp
    last_wa_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, init=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False, init=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        init=False,
    )

    # Index
    __table_args__ = (
        Index(UQ_THREADS_SLUG, "slug", unique=True),
        Index(UQ_THREADS_WA_GROUP_JID, "wa_group_jid", unique=True),
        Index(IDX_THREADS_WA_GROUP_JID, "wa_group_jid"),
        Index(IDX_THREADS_IS_ACTIVE, "is_active"),
        Index(IDX_THREADS_CREATED_AT, "created_at", postgresql_using="btree"),
    )

    # Relations
    members: Mapped[list["ThreadMember"]] = relationship(
        "ThreadMember",
        back_populates="thread",
        cascade="all, delete-orphan",
        uselist=True,
        init=False,
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="thread",
        cascade="all, delete-orphan",
        uselist=True,
        init=False,
    )
    wa_sync_logs: Mapped[list["WASyncLog"]] = relationship(
        "WASyncLog",
        back_populates="thread",
        cascade="all, delete-orphan",
        uselist=True,
        init=False,
    )

    # Messages d'erreur
    ERROR_MESSAGES = {
        UQ_THREADS_SLUG: "Un thread existe déjà avec ce slug.",
        UQ_THREADS_WA_GROUP_JID: "Un thread existe déjà avec cet identifiant de groupe WhatsApp.",
    }