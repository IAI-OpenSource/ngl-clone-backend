from logging import getLogger

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

from app.core.config import REDIS_URL
from app.worker.tasks import add_all_tasks
from app.worker.tasks.base.async_loop_manager import AsyncLoopManager

logger = getLogger(__name__)
celery_app: Celery = Celery("app", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    broker_url=REDIS_URL,
    task_reject_on_worker_lost=True,
)


@worker_process_init.connect
def init_worker_resources(**_kwargs: object) -> None:
    """Déclenché une fois par worker process, après le fork."""
    manager = AsyncLoopManager()
    manager.start_browser_resources()
    logger.info("Worker Celery : ressources async initialisées.")


@worker_process_shutdown.connect
def teardown_worker_resources(**_kwargs: object) -> None:
    """Déclenché à l'arrêt du worker process — ferme proprement les ressources."""
    AsyncLoopManager().close()
    logger.info("Worker Celery : ressources async fermées.")


add_all_tasks()  # Permet d'importer tous les tasks pour que celery puisse les découvrir et les exécuter.

celery_app.autodiscover_tasks(["app.worker.tasks"])
