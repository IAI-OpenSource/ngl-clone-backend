"""
Modèles SQLAlchemy pour la base de données.
Basé sur le schéma PostgreSQL schema_final.sql
"""


# Modèles
def add_all_tables():
    from app.db.models.user import User
    from app.db.models.session import Session


add_all_tables()
