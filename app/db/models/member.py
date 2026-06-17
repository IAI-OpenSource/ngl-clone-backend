"""
Modèle pour la table members.
Gère les membres (utilisateurs WhatsApp) de la plateforme.
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
    from app.db.models.message_mention import MessageMention
    from app.db.models.thread_member import ThreadMember


# Noms des contraintes
UQ_MEMBERS_WA_JID = "uq_members_wa_jid"
IDX_MEMBERS_WA_JID = "idx_members_wa_jid"
IDX_MEMBERS_IS_ACTIVE = "idx_members_is_active"
IDX_MEMBERS_CREATED_AT = "idx_members_created_at"


class Member(Base, IntegrityMapperMixin):
    """Représentation d'un membre (utilisateur WhatsApp)."""

    __tablename__ = "members"

    # Propriétés de base
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, init=False
    )

    # Identifiants WhatsApp
    wa_jid: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    wa_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Informations utilisateur
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Statut
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, init=False
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
        Index(UQ_MEMBERS_WA_JID, "wa_jid", unique=True),
        Index(IDX_MEMBERS_WA_JID, "wa_jid"),
        Index(IDX_MEMBERS_IS_ACTIVE, "is_active"),
        Index(IDX_MEMBERS_CREATED_AT, "created_at", postgresql_using="btree"),
    )

    # Relations
    thread_members: Mapped[list["ThreadMember"]] = relationship(
        "ThreadMember",
        back_populates="member",
        cascade="all, delete-orphan",
        uselist=True,
        init=False,
    )
    message_mentions: Mapped[list["MessageMention"]] = relationship(
        "MessageMention",
        back_populates="member",
        cascade="all, delete-orphan",
        uselist=True,
        init=False,
    )

    # Messages d'erreur
    ERROR_MESSAGES = {
        UQ_MEMBERS_WA_JID: "Un membre existe déjà avec cet identifiant WhatsApp.",
    }