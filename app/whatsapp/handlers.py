from app.whatsapp.base.client_handler import client_command_handler
from app.whatsapp.base.commmand import Command
from app.whatsapp.funcs.map_group import map_group_handler

client_command_handler.include_command(
    Command(
        "/map_group",
        True,
        map_group_handler
    )
)