"""
Modèles SQLAlchemy pour la base de données.
Basé sur le schéma PostgreSQL schema_final.sql
"""


# Modèles
def add_all_tables():
    from app.db.models.user import User
    from app.db.models.session import Session
    from app.db.models.thread import Thread
    from app.db.models.member import Member
    from app.db.models.thread_member import ThreadMember
    from app.db.models.message import Message
    from app.db.models.message_mention import MessageMention
    from app.db.models.wa_delivery_log import WADeliveryLog
    from app.db.models.wa_sync_log import WASyncLog


add_all_tables()
