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

from typing import Annotated

from fastapi import Request

from app.integrations.whatsapp.webhook_handler import WebhookHandler, get_webhook_handler

# noinspection PyUnresolvedReferences
from app.integrations.whatsapp import commands_handlers # noqa Fichier d'import pour inclure les handlers de commandes dans le client WhatsApp

from app.settings.webhook_app_lifespan import webhook_app_lifespan

from fastapi import FastAPI, Depends

app = FastAPI(lifespan=webhook_app_lifespan, title="Internal Webhook Handler", version="1.0.0")


# Route de monitoring
@app.api_route("/health", methods=["GET", "HEAD", "POST"], include_in_schema=False)
def health():
    """Route de monitoring"""
    return {"message": "running"}


@app.post(
    "/webhook",
    response_model=None,
    summary="Webhook pour recevoir les événements WhatsApp",
    include_in_schema=False,
    status_code=204,
)
async def webhook(
    request: Request, handler: Annotated[WebhookHandler, Depends(get_webhook_handler)]
):
    try:
        await handler.handle_webhook(request)
    except Exception as e:
        print(f"Erreur lors du traitement du webhook: {e}")
