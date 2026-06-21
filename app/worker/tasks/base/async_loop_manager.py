import asyncio
import threading
from logging import getLogger
from pathlib import Path
from typing import TypeVar, Coroutine

from app.integrations.whatsapp.card_generator import CardGenerator
from app.integrations.whatsapp.base.evolution_client import (
    EvolutionAPIClient,
    initialize_evolution_client,
)

T = TypeVar("T")

logger = getLogger(__name__)


class AsyncLoopManager:
    """
    Singleton pour gérer une boucle d'événements asynchrone partagée dans les
    tâches Celery.
    """

    _instance: "AsyncLoopManager | None" = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._loop = None
        self._resources_started = False

    def __new__(cls) -> "AsyncLoopManager":
        # Garantit une seule instance (et donc une seule loop) par process,
        # peu importe combien de fois AsyncLoopManager() est appelé.
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._resources_started = False
                    cls._instance = instance
        return cls._instance

    # ── API d'origine (préservée) ────────────────────────────────────────────

    def get_loop(self) -> asyncio.AbstractEventLoop:
        """Retourne la boucle d'événements asynchrone partagée, en la créant si besoin."""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            logger.info("AsyncLoopManager: nouvelle boucle asyncio créée.")
        return self._loop

    def run_async(self, coroutine: Coroutine[None, None, T]) -> T:
        """Exécute une coroutine dans la boucle d'événements partagée."""
        loop = self.get_loop()
        return loop.run_until_complete(coroutine)

    # ── Gestion du cycle de vie Chromium / singletons async ──────────────────

    def start_browser_resources(
        self,
    ) -> None:
        """
        Initialise EvolutionAPIClient et CardGenerator (lance Chromium) DANS
        la boucle gérée par ce manager.

        À appeler une seule fois par worker process — typiquement dans le
        signal Celery worker_process_init, JAMAIS au niveau module (fork()
        partagerait sinon un Chromium déjà lancé entre tous les workers,
        ce qui corrompt les file descriptors et provoque des crashs aléatoires).

        Le navigateur reste attaché à cette loop pour toute la durée de vie
        du worker — il ne doit jamais être relancé sur une autre loop.
        """
        if self._resources_started:
            logger.warning(
                "AsyncLoopManager: ressources déjà initialisées, appel ignoré."
            )
            return

        async def _init() -> None:
            await initialize_evolution_client()

            # Déterminer dynamiquement le dossier 'static' du package 'app'
            # afin d'éviter d'utiliser un chemin absolu '/static' qui est
            # incorrect dans le conteneur/worker.
            # __file__ -> .../app/worker/tasks/base/async_loop_manager.py
            # parents[3] correspond au dossier 'app'
            project_app_dir = Path(__file__).resolve().parents[3]
            templates_dir = str(project_app_dir / "integrations/whatsapp/templates")

            logger.info("AsyncLoopManager: templates_dir calculé pour CardGenerator = %s (exists=%s)", templates_dir, Path(templates_dir).exists())

            CardGenerator.initialize(templates_dir=templates_dir)
            await CardGenerator.get_instance().start()

        self.run_async(_init())
        self._resources_started = True
        logger.info("AsyncLoopManager: Evolution client + Chromium initialisés.")

    def close(self) -> None:
        """
        Ferme proprement Chromium, le client HTTP, puis la boucle elle-même.
        À appeler au shutdown du worker (signal worker_process_shutdown).
        """
        if self._loop is None or self._loop.is_closed():
            return

        if self._resources_started:

            async def _teardown() -> None:
                await EvolutionAPIClient.teardown()
                await CardGenerator.teardown()

            try:
                self.run_async(_teardown())
            except Exception as e:
                logger.exception(
                    f"AsyncLoopManager: erreur pendant la fermeture des ressources. {e}"
                )
            self._resources_started = False

        self._loop.close()
        logger.info("AsyncLoopManager: boucle asyncio fermée.")


task_async_loop_manager = AsyncLoopManager()
