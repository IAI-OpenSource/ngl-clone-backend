try:
    import uvloop

    uvloop.install()  # Nouvelle event loop optimisé à mort
    print("uvloop installé avec succès.")
except (
    Exception
) as exc:  # Désolé pour ceux qui sont sur Windows, uvloop n'est pas compatible avec ce système d'exploitation, du coup on catch l'erreur et on continue avec la boucle standard d'asyncio
    print(
        f"Erreur lors de l'installation d'uvloop: {exc.__class__.__name__}\nFallBack à la boucle standard Asyncio."
    )


from app.core.config import APP_PORT
from app.middlewares.setup import setup_middlewares

from app.settings.app_lifespan import lifespan
from app.settings.cors import setup_app_cors

from app.routers.v1.base_router import v1_api_router

import uvicorn
from fastapi import FastAPI

app = FastAPI(lifespan=lifespan, title="FastApi Template Backend", version="1.0.0")

setup_app_cors(app)

setup_middlewares(app)

app.include_router(v1_api_router)


# Route de monitoring
@app.api_route("/health", methods=["GET", "HEAD", "POST"], include_in_schema=False)
def health():
    """Route de monitoring"""
    return {"message": "running"}


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Running :)"}


# Utile exclusivement pour debugger en local, ne s'execute pas si on lance le serveur via Docker normalement
if __name__ == "__main__":
    conf = uvicorn.Config(app, port=APP_PORT, log_level="info")
    server = uvicorn.Server(conf)
    server.run()
