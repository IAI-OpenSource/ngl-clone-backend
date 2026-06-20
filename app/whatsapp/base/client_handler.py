from app.integrations.evolution_client import EvolutionAPIClient
from app.schemas.webhook_schemas import MessageEvent
from app.whatsapp.base.commmand import Command

from logging import getLogger
async def not_understand(ctx: EvolutionAPIClient, data: MessageEvent):
    await ctx.send_text(number=data.data.groupData.JID, text="Parle bien")

_default_command = Command(
    cmd_func=not_understand,
    cmd_path="",
    admin_only=False
)
async def _send_unauthorized_message(evo: EvolutionAPIClient, group_jid: str):
    await evo.send_text(number=group_jid, text="Vous n'avez pas la permission d'exécuter cette commande.")

logger = getLogger(__name__)
class Whathsappclientwrapper:

    def __init__(self):
        self._commands_mapper: dict[str, Command] = {}

    def include_command(self, cmd: Command):
        error: str | None = None
        
        # Vérifier que la commande commence par /
        if not cmd.cmd_path.strip().startswith("/"):
            error = f"Erreur sur la commande {cmd.cmd_path}: doit commencer par un slash (/)"
        
        # Vérifier que la commande n'existe pas déjà
        elif cmd.cmd_path in self._commands_mapper:
            error = f"Erreur sur la commande {cmd.cmd_path}: doublon, cette commande existe déjà"

        if error:
            raise ValueError(error)

        self._commands_mapper[cmd.cmd_path] = cmd
        logger.info(f"Commande {cmd.cmd_path} ajoutée avec succès")

    @staticmethod
    async def _execute(cmd: Command, event: MessageEvent):
        await cmd.cmd_func(EvolutionAPIClient.get_instance(), event)

    async def process(self, event: MessageEvent, event_cmd: str):
        evo_instance = EvolutionAPIClient.get_instance()

        cmd = self._commands_mapper.get(event_cmd, _default_command)

        if cmd.admin_only:
            # Vérifier si l'utilisateur est admin dans le groupe
            sender_jid = event.data.Info.Sender
            is_user_admin = any(
                p.PhoneNumber == sender_jid and (p.IsAdmin or p.IsSuperAdmin)
                for p in event.data.groupData.Participants
            )
            if not is_user_admin:
                return await _send_unauthorized_message(evo_instance, event.data.groupData.JID)
        await self._execute(cmd, event)
        return None


client_command_handler: Whathsappclientwrapper = Whathsappclientwrapper()