import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.logging_config import setup_logging, silencer_loggers_externes
from app.integrations.evolution_client import initialize_evolution_client, EvolutionAPIClient
from app.settings.dependencies_health import check_startup_dependencies


@asynccontextmanager
async def lifespan(_: FastAPI):

    # Code qui s'executera au démarrage de l'app FastApi
    try:
        setup_logging()
        silencer_loggers_externes()
        await check_startup_dependencies()
        await initialize_evolution_client()
    except Exception as e:
        print(
            f"Exception {e.__class__.__name__} lors du démarrade de l'application : {e}"
        )
        traceback.print_exc()

    # On expose l'appplication jusqu'à sa fin
    yield

    # Code qui s'executera au stop de l'app FastApi
    try:
        # Ferme proprement le client WhatsApp
        await EvolutionAPIClient.teardown()
        print("Bye Bye")
    except Exception as e:
        print(f"Exception {e.__class__.__name__} lors du stop de l'application : {e}")
        traceback.print_exc()
