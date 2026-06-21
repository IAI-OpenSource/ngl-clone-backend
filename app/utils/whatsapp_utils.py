import re
import unicodedata
from typing import Optional


def phone_from_wa_jid(wa_jid: str) -> Optional[str]:
    """
    Extrait le numéro de téléphone depuis un WhatsApp JID.
    """
    if not wa_jid:
        return None

    # enlève tout ce qui suit @
    number = wa_jid.split("@", 1)[0]

    # enlève les suffixes type :1 (multi-device WhatsApp)
    number = number.split(":", 1)[0]

    # garde uniquement chiffres et +
    number = re.sub(r"[^\d+]", "", number)

    return number or None

def generate_random_numeric_password(length: int = 6) -> str:
    """
    Génère un mot de passe numérique aléatoire de la longueur spécifiée.

    Args:
        length (int): La longueur du mot de passe à générer. Par défaut, 6.

    Returns:
        str: Un mot de passe numérique aléatoire.
    """
    import random
    return ''.join(random.choices('0123456789', k=length))


def normalize_slug(text: str) -> str:
    text = text.lower()

    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("utf-8")

    text = re.sub(r"[^a-z0-9]+", "-", text)

    text = text.strip("-")

    return text
