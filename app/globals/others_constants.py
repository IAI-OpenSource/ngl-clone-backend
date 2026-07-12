from app.core.config import SILENTED_GROUPS_JIDS

SUDO_USERS_JID: list[str] = [
    '166206694772894@lid'
]

UNAUTHORIZED_STICKER_URL = "http://ngl_clone_webhook_receiver:8000/sticker_webp"

MUST_SILENTED_GROUPS_JIDS = set(SILENTED_GROUPS_JIDS.split(','))