# utils/security.py
from collections import Counter

from fastapi import Request
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Création d'un hasher Argon2
ph = PasswordHasher()

def has_too_many_repeated_chars(text: str, threshold: float = 0.7) -> bool:
    text = text.replace(" ", "")

    if len(text) < 10:
        return False

    most_common_count = Counter(text).most_common(1)[0][1]

    return most_common_count / len(text) > threshold

def hasher_password(password: str) -> str:
    """function pour hasher les mots de pass utilisateur dans
     base de donnée

    Args:
        password (str): mot de passe claire soumis par le user

    Returns:
        str: retourne un mot de passe crypter: c'est un str
    """

    return ph.hash(password.encode("utf-8"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """function pour verifier le mot de passe lors de login

    Args:
        plain_password (str): c'est le mot de pass en clair fourni lors du login
        hashed_password (str):c'est le  mot de pass crypter qui se trouve dans la database

    Returns:
        bool: retourn true si ca match sinon false si les mots de passe sont differents
    """

    try:
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False


def get_real_ip(request: Request) -> str:
    """fonction nous parmettant de récupéré une address ip dans la requete

    Args:
        request (Request): on prend request de fastapi

    Returns:
        str: on retour le ip en str
    """
    # 1. On regarde d'abord le header X-Forwarded-For (injecté par le proxy)
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # pyrefly: ignore [unnecessary-type-conversion]
        return str(x_forwarded_for.split(",")[0].strip())

    # 2. Sinon, on utilise request.client
    if request.client:
        # pyrefly: ignore [unnecessary-type-conversion]
        return str(request.client.host)

    # 3. Fallback si rien n'est trouvé
    return "unknown"
