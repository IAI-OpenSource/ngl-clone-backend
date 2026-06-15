import os

from dotenv import load_dotenv

load_dotenv()  ## Permet de charger les configs depuis le fichier .env

APP_PORT: int = int(os.getenv("APP_PORT", 8000))

# Environnement courant, on doit définir à LOCAL si on est en local et à PRODUCTION si on est sur le serveur
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LOCAL") or ""

IS_LOCAL_ENVIRONMENT: bool = ENVIRONMENT.upper() == "LOCAL"
IS_PRODUCTION_ENVIRONMENT: bool = ENVIRONMENT.upper() == "PRODUCTION"

# Username de la db
DATABASE_USER: str = os.getenv("DATABASE_USER") or ""

# Driver avec lequel on communique en low-level avec la bd
DATABASE_PILOT: str = os.getenv("DATABASE_PILOT") or ""

# Le type de bd
DATABASE_TYPE: str = os.getenv("DATABASE_TYPE") or ""

# MDP de la db
DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD") or ""

# Lien vers la db, à définir directement avec le port de connexion
DATABASE_HOST: str = os.getenv("DATABASE_HOST") or ""

# Nom de la db
DATABASE_NAME: str = os.getenv("DATABASE_NAME") or ""

# Clé secrete pour hashage et autres
ACCESS_SECRET_KEY: str = os.getenv("SECRET_KEY") or ""
REFRESH_TOKEN_SECRET_KEY: str = os.getenv("REFRESH_TOKEN_SECRET_KEY") or ""

# Algorithme de hashage qu'on va utiliser
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

# Minutes par défauts après lequel les tokens JWT s'expirent
JWT_EXPIRES_SECONDES: int = int(os.getenv("JWT_EXPIRES_SECONDES", 3600))
REFRESH_TOKEN_EXPIRES_SECONDES: int = int(
    os.getenv("REFRESH_TOKEN_EXPIRES_SECONDES", 7 * 24 * 3600)
)

## les IDs des cookies
JWT_COOKIE_ACCESS_ID: str = "_SECURE_TOKEN"  ## encoder ID de le session
SID_REF_COOKIE: str = "_SID_REFRESH"  ## encoder le refresh token

## url redis
REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
LOG_DIR = "logs"
