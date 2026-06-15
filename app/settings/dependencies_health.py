import asyncio
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy import text

from app.cache.base.cache_wrapper import cache_manager
from app.db.config import engine

logger = logging.getLogger(__name__)

DEPENDENCY_CHECK_TIMEOUT_SECONDS = 5


async def _check_database() -> None:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


async def _check_cache() -> None:
    redis_cache = cache_manager.get_redis_connection_from_pool()
    try:
        await redis_cache.ping()
    finally:
        await redis_cache.close()
        await cache_manager.disconnect_pool()


async def _run_dependency_check(
    name: str, check: Callable[[], Awaitable[None]]
) -> None:
    try:
        await asyncio.wait_for(check(), timeout=DEPENDENCY_CHECK_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning(
            "Dependance %s indisponible au demarrage: (%s: %s)",
            name,
            exc.__class__.__name__,
            exc,
        )
    else:
        logger.info("Dependance %s disponible au demarrage", name)


async def check_startup_dependencies() -> None:
    await asyncio.gather(
        _run_dependency_check("database", _check_database),
        _run_dependency_check("cache", _check_cache),
    )
