from __future__ import annotations

from dataclasses import dataclass
from playwright.sync_api import Page


@dataclass(frozen=True)
class EtaCredentials:
    username: str
    password: str


class EtaClient:
    """
    Cliente mínimo para ETAdirect.
    - Login
    - Verificación de sesión (avatar usuario visible)
    - Logout (menú usuario -> Cerrar sesión)
    """

    # Login (estos te están funcionando hoy)
    _SEL_USERNAME = 'input[name="username"]'
    _SEL_PASSWORD = 'input[name="password"]'
    _SEL_SUBMIT = 'button[type="submit"]'

    # Avatar / menú usuario (según tu DOM real)
    # Opción 1: botón que contiene el web component del avatar
    _SEL_USER_MENU_BUTTON = (
        '#ofs-main div.user-menu-region button:has(visuals\\:technician-avatar)'
    )

    # Opción 2: el web component (para verificación)
    _SEL_AVATAR_COMPONENT = 'visuals\\:technician-avatar'

    # Contenedor del menú desplegado (tu tooltip)
    _SEL_MENU_CONTAINER = (
        "div.ui-tip.ui-widget.ui-corner-all.ui-widget-content."
        "legacy-manage-container.hang-tree.tip_container_bottomActivitiesPanel.ui-droppable"
    )

    # Logout link (tu captura: a.item-link)
    _SEL_LOGOUT = 'a.item-link:has-text("Cerrar sesión")'

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/") + "/"

    def goto_login(self) -> None:
        self.page.goto(self.base_url, wait_until="domcontentloaded")

    def login(self, creds: EtaCredentials) -> None:
        self.goto_login()
        self.page.fill(self._SEL_USERNAME, creds.username)
        self.page.fill(self._SEL_PASSWORD, creds.password)
        self.page.click(self._SEL_SUBMIT)
        self.page.wait_for_load_state("networkidle")

    def assert_logged_in(self) -> None:
        """
        Verificación REAL: el avatar de técnico/usuario debe estar visible post-login.
        """
        avatar = self.page.locator(self._SEL_AVATAR_COMPONENT).first
        avatar.wait_for(state="visible", timeout=8000)

    def logout(self) -> None:
        """
        Cierra sesión desde el menú de usuario.
        """
        # Si no hay avatar, asumimos que no hay sesión activa
        if self.page.locator(self._SEL_AVATAR_COMPONENT).count() == 0:
            return

        # Abre menú usuario (botón del avatar)
        btn = self.page.locator(self._SEL_USER_MENU_BUTTON).first
        btn.click()

        # Espera el contenedor del menú y hace click en "Cerrar sesión"
        menu = self.page.locator(self._SEL_MENU_CONTAINER).first
        menu.wait_for(state="visible", timeout=5000)
        menu.locator(self._SEL_LOGOUT).first.click()

        self.page.wait_for_load_state("networkidle")