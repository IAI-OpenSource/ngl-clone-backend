# Database, SQLAlchemy Models & Integrity Error Translation

This document details the modeling rules with SQLAlchemy 2.0, the use of explicit named constraints, and the operation of the integrity error translation mixin.

---

> **📄 Documentation Available in French**
> A French version of this document is available: [database_and_models_fr.md](./database_and_models_fr.md)

---

## 1. Base Modeling (Modern SQLAlchemy 2.0)

The template uses the modern declarative base with automatic support for Python **dataclasses** (`MappedAsDataclass` and `DeclarativeBase`).
All SQLAlchemy models are located under [app/db/models/](../app/db/models) and must inherit from both `Base` (defined in [app/db/config.py](../app/db/config.py)) and `IntegrityMapperMixin`.

### 1.1. Mandatory Writing Conventions
1. **Strict typing via `Mapped[Type]`**: All table attributes must be explicitly typed.
2. **Use of `mapped_column`**: Always use `mapped_column(...)` to configure the SQL column behavior.
3. **Initialization control (`init=False`)**: For all auto-generated or database-managed attributes (e.g., unique ID, timestamps, soft-delete, default roles, relationships), explicitly add `init=False` in the `mapped_column()` constructor.
4. **Typed relationships with strings**: To avoid circular imports during execution, specify the name of the related class as a string (`Mapped[list["Session"]] = relationship("Session", ...)`).

---

## 2. Definition and Naming of Constraints

> [!IMPORTANT]
> **No constraint should be left anonymous or implicitly managed by SQLAlchemy.**
> All constraints (Unique Indexes, Foreign Keys, Check Constraints, Search Indexes) must be explicitly named as constants defined at the top of the model file.

### Constraint naming conventions:
- **Unique Key (Unique Constraint)**: `uq_[table]_[column_1]_[column_2]...` (e.g., `uq_users_username`)
- **Index**: `idx_[table]_[column_1]_[column_2]...` (e.g., `idx_users_created_at_id`)
- **Foreign Key**: `fk_[source_table]_[target_table]` (e.g., `fk_sessions_user`)
- **Validation Constraint (Check Constraint)**: `chk_[table]_[condition]` (e.g., `chk_sessions_expires_after_creation`)

---

## 3. Integrity Error Translation via `IntegrityMapperMixin`

The [IntegrityMapperMixin](../app/db/mixins/integrity_error_mixin.py) intercepts constraint violations returned by the async database driver (`asyncpg`) and transforms them into user-friendly messages.

### Operation:
1. A database constraint (e.g., `uq_users_username`) is violated during a `commit()`.
2. SQLAlchemy raises an `IntegrityError`.
3. The `asyncpg` driver exposes the raw PostgreSQL error containing the exact name of the violated constraint (`constraint_name`).
4. `IntegrityMapperMixin.translate_integrity_error(exception)` retrieves this name and matches it with the `ERROR_MESSAGES` dictionary defined within the model class.
5. If a match exists, the application returns the configured friendly message with an HTTP 400 (Bad Request) status.

---

## 4. Typical Structure / Model Skeleton

Here is the recommended file skeleton when creating a new model (e.g., `Product`):

```python
"""
Model for the products table.
Manages the products available on the platform.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Index, String, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.config import Base
from app.db.mixins.integrity_error_mixin import IntegrityMapperMixin

if TYPE_CHECKING:
    # Contains imports exclusive to static typing
    # Import other models here to avoid circular imports
    from app.db.models.user import User

# Definition of constraint names as explicit constants
UQ_PRODUCTS_CODE = "uq_products_code"
FK_PRODUCTS_OWNER = "fk_products_owner"
CHK_PRODUCTS_POSITIVE_PRICE = "chk_products_positive_price"
IDX_PRODUCTS_CREATED_AT = "idx_products_created_at"

class Product(Base, IntegrityMapperMixin):
    """Representation of a product."""

    __tablename__ = "products"

    # Base properties
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name=FK_PRODUCTS_OWNER),
        nullable=False
    )

    # Timestamps (managed automatically)
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

    # Table arguments for indexes and table-level constraints
    __table_args__ = (
        Index(IDX_PRODUCTS_CREATED_AT, created_at),
        Index(UQ_PRODUCTS_CODE, code, unique=True),
        CheckConstraint("price >= 0", name=CHK_PRODUCTS_POSITIVE_PRICE),
    )

    # Relationships (init=False to avoid having to pass the object during simple instantiation)
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
        uselist=False,
        init=False
    )

    # Error mapping dictionary for IntegrityMapperMixin
    ERROR_MESSAGES = {
        UQ_PRODUCTS_CODE: "A product already exists with this unique code.",
        FK_PRODUCTS_OWNER: "The specified owner does not exist.",
        CHK_PRODUCTS_POSITIVE_PRICE: "A product's price cannot be negative.",
    }
```
