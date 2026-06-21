from dataclasses import dataclass
from typing import Callable, Awaitable, Any

from app.integrations.whatsapp.base.evolution_client import EvolutionAPIClient
from app.schemas.webhook_schemas import MessageEvent


@dataclass
class Command:
        cmd_path: str
        admin_only: bool
        cmd_func: Callable[[EvolutionAPIClient, MessageEvent], Awaitable[Any]]
