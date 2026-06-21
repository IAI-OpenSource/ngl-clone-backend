from app.whatsapp.base.client_handler import client_command_handler
from app.whatsapp.base.commmand import Command
from app.whatsapp.funcs.map_group import map_group_handler
from app.whatsapp.funcs.thread_commands import (
    ngl_status_handler,
    lock_thread_handler,
    unlock_thread_handler,
    edit_thread_handler,
    help_handler,
    docs_handler,
)

client_command_handler.include_command(
    Command(
        "/map_group",
        True,
        map_group_handler
    )
)

# Nouvelles commandes
client_command_handler.include_command(
    Command(
        "/ngl",
        False,
        ngl_status_handler
    )
)

client_command_handler.include_command(
    Command(
        "/lock",
        True,
        lock_thread_handler
    )
)

client_command_handler.include_command(
    Command(
        "/unlock",
        True,
        unlock_thread_handler
    )
)

client_command_handler.include_command(
    Command(
        "/edit-name",
        True,
        edit_thread_handler
    )
)

client_command_handler.include_command(
    Command(
        "/edit-desc",
        True,
        edit_thread_handler
    )
)

client_command_handler.include_command(
    Command(
        "/edit-slug",
        True,
        edit_thread_handler
    )
)

client_command_handler.include_command(
    Command(
        "/help",
        False,
        help_handler
    )
)

client_command_handler.include_command(
    Command(
        "/docs",
        False,
        docs_handler
    )
)
