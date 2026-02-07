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
    H2.1: Login estable + verificación básica.
    H2.2: Export CSV (RAW).
    """

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/") + "/"

    def goto_login(self) -> None:
        self.page.goto(self.base_url, wait_until="domcontentloaded")

    def login(self, creds: EtaCredentials) -> None:
        """
        Login genérico (placeholder de selectores).
        En el siguiente paso ajustamos selectores exactos según el DOM real.
        """
        self.goto_login()

        # TODO(H2): Ajustar selectores reales del portal
        # Ejemplos típicos (no asumir): input[name="username"], input[type="password"]
        # Aquí solo dejamos el flujo y fallará hasta que pongamos selectores reales.
        self.page.fill('input[name="username"]', creds.username)
        self.page.fill('input[name="password"]', creds.password)
        self.page.click('button[type="submit"]')

        # Espera a que cargue algo post-login (placeholder)
        self.page.wait_for_load_state("networkidle")

    def assert_logged_in(self) -> None:
        """
        Verificación robusta por descarte:
        - Si aún existe un campo de usuario/password visible, asumimos que NO está logueado.
        - Caso contrario, consideramos login OK (por ahora).
        Luego en H2.2 lo refinamos con un selector post-login definitivo (menú/usuario).
        """
        # Si estos inputs están visibles, seguimos en login
        username_visible = self.page.locator('input[name="username"]').first.is_visible()
        password_visible = self.page.locator('input[name="password"]').first.is_visible()

        if username_visible or password_visible:
            raise RuntimeError(f"No se detectó login exitoso: formulario de login sigue visible. url={self.page.url}")