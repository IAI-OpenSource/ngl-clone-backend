from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_app_cors(app: FastAPI) -> None:
    """Configure les CORS pour l'application FastAPI"""

    # Liste des origines autorisées
    origins = [
        "http://localhost",
        # "autre origine autorisée"
    ]  # Rien pour le moment

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
