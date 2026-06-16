# Base de Données, Modèles SQLAlchemy & Traduction d'Erreurs d'Intégrité

Ce document détaille les règles de modélisation avec SQLAlchemy 2.0, l'usage des contraintes nommées explicites et le fonctionnement du mixin de traduction d'erreurs d'intégrité.

---

> **📄 Documentation Available in English**
> An English version of this document is available: [database_and_models_en.md](./database_and_models_en.md)

---

## 1. Modélisation de Base (SQLAlchemy 2.0 Moderne)

Le template utilise la base déclarative moderne avec support automatique des **dataclasses** Python (`MappedAsDataclass` et `DeclarativeBase`).
Tous les modèles SQLAlchemy sont localisés sous [app/db/models/](../app/db/models) et doivent hériter à la fois de `Base` (définie dans [app/db/config.py](../app/db/config.py)) et de `IntegrityMapperMixin`.

### 1.1. Conventions d'Écriture Obligatoires
1. **Typage strict via `Mapped[Type]`** : Tous les attributs de table doivent être typés de manière explicite.
2. **Usage de `mapped_column`** : Toujours utiliser `mapped_column(...)` pour configurer le comportement de la colonne SQL.
3. **Contrôle d'initialisation (`init=False`)** : Pour tous les attributs auto-générés ou gérés par défaut par la base de données (ex: ID unique autogénéré, timestamps, soft-delete, rôles par défaut, relations), ajoutez explicitement `init=False` dans le constructeur `mapped_column()`.
4. **Relations typées avec chaînes de caractères** : Pour éviter les imports circulaires lors de l'exécution, spécifiez le nom de la classe reliée sous forme de chaîne de caractères (`Mapped[list["Session"]] = relationship("Session", ...)`).

---

## 2. Définition et Nommage des Contraintes

> [!IMPORTANT]
> **Aucune contrainte ne doit être laissée anonyme ou gérée implicitement par SQLAlchemy.** 
> Toutes les contraintes (Index uniques, Foreign Keys, Check Constraints, Index de recherche) doivent être nommées de façon explicite sous forme de constantes définies en haut du fichier du modèle.

### Conventions de nommage des contraintes :
- **Clé Unique (Unique Key)** : `uq_[table]_[colonne_1]_[colonne_2]...` (ex: `uq_users_username`)
- **Index** : `idx_[table]_[colonne_1]_[colonne_2]...` (ex: `idx_users_created_at_id`)
- **Clé Étrangère (Foreign Key)** : `fk_[table_source]_[table_cible]` (ex: `fk_sessions_user`)
- **Contrainte de Validation (Check Constraint)** : `chk_[table]_[condition]` (ex: `chk_sessions_expires_after_creation`)

---

## 3. Traduction des Erreurs d'Intégrité via `IntegrityMapperMixin`

Le mixin [IntegrityMapperMixin](../app/db/mixins/integrity_error_mixin.py) intercepte les violations de contraintes renvoyées par le driver de base de données asynchrone (`asyncpg`) et les transforme en messages lisibles (User Friendly).

### Fonctionnement :
1. Une contrainte BD (ex: `uq_users_username`) est violée lors d'un `commit()`.
2. SQLAlchemy lève une `IntegrityError`.
3. Le driver `asyncpg` expose l'erreur PostgreSQL brute contenant le nom exact de la contrainte violée (`constraint_name`).
4. `IntegrityMapperMixin.translate_integrity_error(exception)` récupère ce nom et le fait correspondre avec le dictionnaire `ERROR_MESSAGES` défini au sein de la classe du modèle.
5. Si une correspondance existe, l'application retourne le message friendly configuré avec un code HTTP 400 (Bad Request).

---

## 4. Structure Type / Squelette d'un Modèle SQLAlchemy

Voici le squelette de fichier recommandé lors de la création d'un nouveau modèle (ex: `Product`) :

```python
"""
Modèle pour la table products.
Gère les produits disponibles sur la plateforme.
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
    # Contient les imports exclusifs pour le typage statique
    # Importez les autres modèles ici pour éviter les imports circulaires
    from app.db.models.user import User

# Définition des noms de contraintes sous forme de constantes explicites
UQ_PRODUCTS_CODE = "uq_products_code"
FK_PRODUCTS_OWNER = "fk_products_owner"
CHK_PRODUCTS_POSITIVE_PRICE = "chk_products_positive_price"
IDX_PRODUCTS_CREATED_AT = "idx_products_created_at"

class Product(Base, IntegrityMapperMixin):
    """Représentation d'un produit."""

    __tablename__ = "products"

    # Propriétés de base
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name=FK_PRODUCTS_OWNER),
        nullable=False
    )

    # Timestamps (gérés automatiquement)
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

    # Table arguments pour les index et contraintes de niveau table
    __table_args__ = (
        Index(IDX_PRODUCTS_CREATED_AT, created_at),
        Index(UQ_PRODUCTS_CODE, code, unique=True),
        CheckConstraint("price >= 0", name=CHK_PRODUCTS_POSITIVE_PRICE),
    )

    # Relations (init=False pour éviter de devoir passer l'objet lors de l'instanciation simple)
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_id],
        uselist=False,
        init=False
    )

    # Dictionnaire de mappage d'erreurs pour IntegrityMapperMixin
    ERROR_MESSAGES = {
        UQ_PRODUCTS_CODE: "Un produit existe déjà avec ce code unique.",
        FK_PRODUCTS_OWNER: "Le propriétaire spécifié n'existe pas.",
        CHK_PRODUCTS_POSITIVE_PRICE: "Le prix d'un produit ne peut pas être négatif.",
    }
```

---

## 5. Import des Modèles

> [!IMPORTANT]
> **Tous les modèles doivent être importés dans `app/db/__init__.py` via la fonction `add_all_tables()`.**
> Ne pas exporter les modèles depuis `app/db/models/__init__.py`.

### Pourquoi ce pattern ?
Le pattern d'import centralisé dans `app/db/__init__.py` garantit que :
- Tous les modèles sont chargés au démarrage de l'application
- Il n'y a pas de problèmes d'imports circulaires
- La base de données est initialisée correctement

### Comment l'implémenter ?
1. **Créer votre modèle** dans `app/db/models/` (ex: `thread.py`)
2. **Ajouter l'import** dans `app/db/__init__.py` :

```python
# app/db/__init__.py
def add_all_tables():
    from app.db.models.user import User
    from app.db.models.session import Session
    from app.db.models.thread import Thread
    # Ajoutez ici tous vos nouveaux modèles
    
add_all_tables()
```
