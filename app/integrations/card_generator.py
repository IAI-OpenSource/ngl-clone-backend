from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar, Self

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from playwright.async_api import (
    Browser,
    Page,
    Playwright,
    async_playwright,
    ViewportSize,
)

logger = logging.getLogger(__name__)


class CardGeneratorError(Exception):
    """Erreur lors de la génération d'une carte."""


class CardGeneratorNotInitializedError(CardGeneratorError):
    """Singleton non initialisé — appeler CardGenerator.initialize() d'abord."""


class CardGenerator:
    """
    Générateur de cartes-images via Playwright (HTML/CSS → screenshot PNG).

    ─── Singleton (usage recommandé) ───────────────────────────────────────

        # 1. Initialisation au démarrage (FastAPI lifespan)
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with CardGenerator.initialize(templates_dir="templates/cards") as gen:
                yield

        # 2. Accès depuis n'importe où
        gen = CardGenerator.get_instance()
        image_bytes = await gen.render(
            template_name="message_card.html",
            context={"text": "...", "thread_name": "TC2-A"},
        )

    ─── Context manager direct (scripts, tests) ────────────────────────────

        async with CardGenerator(templates_dir="templates/cards") as gen:
            png_bytes = await gen.render("message_card.html", {"text": "Hello"})
    """

    _singleton: ClassVar["CardGenerator | None"] = None

    DEFAULT_VIEWPORT: ClassVar[dict[str, int]] = {"width": 800, "height": 800}

    # ── Init ─────────────────────────────────────────────────────────────────

    def __init__(
        self,
        templates_dir: str | Path,
        *,
        viewport: dict[str, int] | None = None,
        device_scale_factor: float = 2.0,  # 2x = rendu net (Retina-like) pour WhatsApp
    ) -> None:
        """
        Args:
            templates_dir:       Dossier contenant les templates HTML (Jinja2)
            viewport:            Taille de la fenêtre de rendu (défaut 800x800)
            device_scale_factor: Facteur de résolution (2.0 = image 2x plus nette)
        """
        self._templates_dir = Path(templates_dir)
        self._viewport = ViewportSize(**(viewport or self.DEFAULT_VIEWPORT))
        self._device_scale_factor = device_scale_factor

        self._jinja_env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=select_autoescape(["html"]),
        )

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def __aenter__(self) -> Self:
        await self.start()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.stop()

    async def start(self) -> None:
        """Lance Chromium et ouvre une page persistante."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage"],  # évite les crashs liés au /dev/shm limité en conteneur Docker
        )
        self._page = await self._browser.new_page(
            viewport=self._viewport,
            device_scale_factor=self._device_scale_factor,
        )
        logger.info("CardGenerator: Chromium démarré (viewport=%s, scale=%s)",
                    self._viewport, self._device_scale_factor)

    async def stop(self) -> None:
        """Ferme la page, le navigateur et l'instance Playwright."""
        if self._page:
            await self._page.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("CardGenerator: Chromium fermé.")

    # ── Singleton API ─────────────────────────────────────────────────────────

    @classmethod
    def initialize(
        cls,
        templates_dir: str | Path,
        *,
        viewport: dict[str, int] | None = None,
        device_scale_factor: float = 2.0,
        force: bool = False,
    ) -> "CardGenerator":
        """Crée et enregistre le singleton. Lève RuntimeError si déjà initialisé."""
        if cls._singleton is not None and not force:
            raise RuntimeError(
                "CardGenerator déjà initialisé. Utilise force=True pour réinitialiser."
            )
        cls._singleton = cls(
            templates_dir,
            viewport=viewport,
            device_scale_factor=device_scale_factor,
        )
        return cls._singleton

    @classmethod
    def get_instance(cls) -> "CardGenerator":
        """Retourne le singleton. Lève CardGeneratorNotInitializedError sinon."""
        if cls._singleton is None:
            raise CardGeneratorNotInitializedError(
                "CardGenerator non initialisé. Appelle CardGenerator.initialize(...) au démarrage."
            )
        return cls._singleton

    @classmethod
    async def as_dependency(cls) -> "CardGenerator":
        """FastAPI dependency injection."""
        return cls.get_instance()

    @classmethod
    async def teardown(cls) -> None:
        """Ferme le singleton (lifespan shutdown)."""
        if cls._singleton is not None:
            await cls._singleton.stop()
            cls._singleton = None

    # ── Rendu ─────────────────────────────────────────────────────────────────

    async def render(
        self,
        template_name: str,
        context: dict[str, object],
        *,
        selector: str | None = "#card",
        viewport_override: ViewportSize | None = None,
    ) -> bytes:
        """
        Rend un template HTML avec le contexte donné et retourne un PNG.

        Args:
            template_name:     Nom du fichier .html dans templates_dir
            context:           Variables Jinja2 à injecter dans le template
            selector:          Sélecteur CSS de l'élément à capturer (None = page entière).
                               Recommandé : englober ta carte dans <div id="card">...</div>
                               pour capturer uniquement son contenu, sans marge de page.
            viewport_override: Override ponctuel de la taille de viewport pour ce render

        Returns:
            Bytes PNG de l'image générée.
        """
        if self._page is None:
            raise CardGeneratorError("Page non initialisée — appelle start() d'abord.")

        template: Template = self._jinja_env.get_template(template_name)
        html = template.render(**context)

        if viewport_override:
            await self._page.set_viewport_size(viewport_override)

        await self._page.set_content(html, wait_until="networkidle")

        if selector:
            element = await self._page.wait_for_selector(selector, state="attached")
            if element is None:
                raise CardGeneratorError(f"Sélecteur introuvable dans le template : {selector}")
            screenshot = await element.screenshot(type="png")
        else:
            screenshot = await self._page.screenshot(type="png", full_page=True)

        if viewport_override:
            await self._page.set_viewport_size(self._viewport)

        return screenshot

    async def render_html_string(
        self,
        html: str,
        *,
        selector: str | None = "#card",
    ) -> bytes:
        """
        Variante de render() acceptant du HTML brut (sans passer par Jinja2).
        Utile pour du HTML construit dynamiquement côté Python.
        """
        if self._page is None:
            raise CardGeneratorError("Page non initialisée — appelle start() d'abord.")

        await self._page.set_content(html, wait_until="networkidle")

        if selector:
            element = await self._page.wait_for_selector(selector, state="attached")
            if element is None:
                raise CardGeneratorError(f"Sélecteur introuvable : {selector}")
            return await element.screenshot(type="png")

        return await self._page.screenshot(type="png", full_page=True)
