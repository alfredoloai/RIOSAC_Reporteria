from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import Download, Page
from playwright.sync_api import TimeoutError as PWTimeoutError


@dataclass(frozen=True)
class EtaCredentials:
    username: str
    password: str


class EtaClient:
    """
    Cliente ETAdirect:
    - login / assert / logout
    - seleccionar cuadrilla (grupo)
    - export CSV desde Acciones -> Exportar
    """

    # Login (te funcionan)
    _SEL_USERNAME = 'input[name="username"]'
    _SEL_PASSWORD = 'input[name="password"]'
    _SEL_SUBMIT = 'button[type="submit"]'

    # Avatar / menú usuario
    _SEL_HEADER_AVATAR_INITIALS = r'#ofs-main header div.user-menu-region .placeholder-initials'
    _SEL_USER_MENU_BUTTON = r'#ofs-main header div.user-menu-region button'

    # Árbol de cuadrillas (panel izquierdo)
    _SEL_TREE = 'div.toa-panel-content.edtree'
    # Cada grupo se identifica por el texto en span.rtl-prov-name dentro del botón edt-label
    # Ej: "Riosactelcom / Loja"
    def _sel_group_label(self, group_name: str) -> str:
        # Se apoya en el texto visible del span
        return f'{self._SEL_TREE} button.edt-label:has(span.rtl-prov-name:has-text("{group_name}"))'

    # Acciones / Exportar
    _SEL_ACTIONS_BUTTON = 'button[aria-label="Acciones"][data-ofsc-role="button-active-area"]'
    _SEL_EXPORT_OPTION = (
        'button.toolbar-menu-button.menu-item:'
        'has(span.toolbar-menu-button-title:has-text("Exportar"))'
    )
    _SEL_EXPORT_OPTION = "".join(_SEL_EXPORT_OPTION)

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/") + "/"

    def goto_login(self) -> None:
        self.page.goto(self.base_url, wait_until="domcontentloaded")

    def login(self, creds: EtaCredentials) -> None:
        self.goto_login()

        # Llenar credenciales
        self.page.fill(self._SEL_USERNAME, creds.username)
        self.page.fill(self._SEL_PASSWORD, creds.password)
        self.page.click(self._SEL_SUBMIT)

        # Espera a que responda el login (puede quedarse en la misma pantalla)
        self.page.wait_for_timeout(800)

        # Caso especial: excedió máximo de sesiones
        # En ese caso, hay un mensaje y un checkbox para suprimir sesiones antiguas.
        max_sessions_msg = self.page.locator('text=Se ha superado el número máximo de sesiones').first
        if max_sessions_msg.count() > 0 and max_sessions_msg.is_visible():
            # Checkbox: "Suprimir la sesión y conexión de usuario más antiguas"
            # Mejor selector por texto (robusto)
            suppress_cb = self.page.locator('label:has-text("Suprimir la sesión y conexión de usuario más antiguas")').first

            # Si el label no es clickeable, intenta con el input dentro del label
            try:
                suppress_cb.click()
            except Exception:
                suppress_cb.locator('input[type="checkbox"]').first.click()

            # Reingresar password (a veces se limpia o no se toma)
            self.page.fill(self._SEL_PASSWORD, creds.password)

            # Reintentar submit
            self.page.click(self._SEL_SUBMIT)

        # Espera post-login
        self.page.wait_for_load_state("networkidle")

    def assert_logged_in(self) -> None:
        """
        Login OK si las iniciales del header quedan visibles.
        """
        self.page.wait_for_load_state("domcontentloaded")

        initials = self.page.locator(self._SEL_HEADER_AVATAR_INITIALS).first
        initials.wait_for(state="visible", timeout=20000)

        txt = (initials.text_content() or "").strip()
        if not txt:
            raise RuntimeError("Login no confirmado: initials vacías en header.")

    def logout(self) -> None:
        btn = self.page.locator(self._SEL_USER_MENU_BUTTON).first
        btn.wait_for(state="visible", timeout=8000)
        btn.click(force=True)

        logout_item = self.page.locator('a.item-link:has-text("Cerrar sesión")').first
        logout_item.wait_for(state="visible", timeout=8000)
        logout_item.click(force=True)

        self.page.wait_for_load_state("networkidle")

    # ---------------------------
    # CUADRILLAS + EXPORT
    # ---------------------------

    def select_group(self, group_name: str) -> None:
        """
        Click en la cuadrilla (grupo) dentro del árbol de recursos.
        """
        locator = self.page.locator(self._sel_group_label(group_name)).first
        locator.wait_for(state="visible", timeout=12000)
        locator.click()
        # Espera a que la vista cargue/actualice
        self.page.wait_for_load_state("networkidle")

    def export_csv_from_actions(self) -> Download:
        actions_btn = self.page.locator(self._SEL_ACTIONS_BUTTON).first
        actions_btn.wait_for(state="visible", timeout=12000)
        actions_btn.click(force=True)

        export_item = self.page.locator(self._SEL_EXPORT_OPTION).first
        export_item.wait_for(state="visible", timeout=8000)

        try:
            with self.page.expect_download(timeout=30000) as dl_info:
                export_item.click(force=True)
            return dl_info.value
        except PWTimeoutError as e:
            raise RuntimeError(
                "No se detectó download después de pulsar Exportar. "
                "Probable diálogo nativo 'Guardar como' o descarga bloqueada."
            ) from e