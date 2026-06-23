from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import ALLOWED_ORIGINS


def setup_app_cors(app: FastAPI) -> None:
    """Configure les CORS pour l'application FastAPI"""

    # Liste des origines autorisées
    origins = ALLOWED_ORIGINS.split(",")

    print(f"Configuration CORS : {origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
