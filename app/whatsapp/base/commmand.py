from dataclasses import dataclass
from typing import Callable


@dataclass
class Command:
        cmd_path: str
        admin_only: bool
        cmd_func: Callable
