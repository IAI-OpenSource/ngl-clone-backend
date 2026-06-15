"""
Modèle pour la table users.
Tous les utilisateurs de la plateforme.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Index,
    String,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base
from app.db.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums.enums import SexeType, UserType

if TYPE_CHECKING:
    # Import your models here for avoid circular imports and keep IDE type cheek
    from app.db.models.session import Session

# Noms des contraintes
UQ_USERS_USERNAME = "uq_users_username"
IDX_USERS_CREATED_AT_ID = "idx_users_created_at_id"
IDX_USERS_ROLE = "idx_users_role"
IDX_USERS_DELETED_AT = "idx_users_deleted_at"


class User(Base, IntegrityMapperMixin):
    """Utilisateurs de la plateforme (étudiants, modérateurs, etc.)."""

    __tablename__ = "users"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    sexe: Mapped[SexeType] = mapped_column(SQLEnum(SexeType), nullable=False)

    # Rôle et permissions
    role: Mapped[UserType] = mapped_column(
        SQLEnum(UserType), default=UserType.USER, nullable=False, init=False
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
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

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, init=False
    )

    # Index
    __table_args__ = (
        Index(
            IDX_USERS_CREATED_AT_ID,
            created_at,
            id,
            postgresql_where=(deleted_at == None),
        ),
        Index(
            UQ_USERS_USERNAME,
            username,
            unique=True,
            postgresql_where=(deleted_at == None),
        ),
        Index(IDX_USERS_ROLE, role, postgresql_where=(deleted_at == None)),
        Index(IDX_USERS_DELETED_AT, deleted_at, postgresql_where=(deleted_at != None)),
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=True,
        init=False,
    )

    # Messages d'erreur
    ERROR_MESSAGES = {
        UQ_USERS_USERNAME: "Ce nom d'utilisateur est déjà pris.",
    }
