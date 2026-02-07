from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from playwright.sync_api import Download, Page
from playwright.sync_api import TimeoutError as PWTimeoutError


@dataclass(frozen=True)
class EtaCredentials:
    username: str
    password: str


_MONTHS_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_MONTHS_NUM_TO_NAME = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


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

    # Date picker
    _SEL_DATE_BUTTON = (
        r'#jbf-body > controls\:page-header > header > div.page-context > div.page-header-main-region '
        r'> div.page-header-actions-region > controls\:toolbar > div > '
        r'div.toolbar-items-list.toolbar-items-list--no-menu-button > div:nth-child(2) > '
        r'controls\:toolbar-items\:toolbar-dispatch-console-date-range-picker > div > button'
    )
    _SEL_DATEPICKER_ROOT = r'div[id^="dp"] div.ui-datepicker-inline.ui-datepicker'
    _SEL_DATEPICKER_PREV = r'div[id^="dp"] a.ui-datepicker-prev'
    _SEL_DATEPICKER_NEXT = r'div[id^="dp"] a.ui-datepicker-next'
    _SEL_DATE_TITLES = r'div[id^="dp"] .ui-datepicker-title'
    _SEL_MONTH = ".ui-datepicker-month"
    _SEL_YEAR = ".ui-datepicker-year"

    # Acciones / Exportar (toolbar)
    _SEL_ACTIONS_BUTTON = 'button[aria-label="Acciones"]'
    _SEL_ACTIONS_MENU = "div.app-menu-container"
    _SEL_EXPORT_BUTTON = (
        'button.toolbar-menu-button.menu-item:'
        'has(span.toolbar-menu-button-title:text-is("Exportar"))'
    )

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

        # Espera breve por respuesta
        self.page.wait_for_timeout(800)

        max_sessions_msg = self.page.locator('text=Se ha superado el número máximo de sesiones').first
        if max_sessions_msg.count() > 0 and max_sessions_msg.is_visible():
            suppress_cb = self.page.locator('label:has-text("Suprimir la sesión y conexión de usuario más antiguas")').first

            try:
                suppress_cb.click()
            except Exception:
                suppress_cb.locator('input[type="checkbox"]').first.click()

            self.page.fill(self._SEL_PASSWORD, creds.password)
            self.page.click(self._SEL_SUBMIT)

        self.page.wait_for_load_state("networkidle")

    def assert_logged_in(self) -> None:
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
    # FECHAS
    # ---------------------------

    def _wait_datepicker_visible(self, timeout_ms: int = 8000) -> None:
        self.page.wait_for_function(
            """() => {
            const roots = Array.from(document.querySelectorAll('div[id^="dp"] div.ui-datepicker-inline.ui-datepicker'));
            for (const el of roots) {
                const s = getComputedStyle(el);
                const visible = s.display !== 'none' && s.visibility !== 'hidden' && el.getClientRects().length > 0;
                if (visible) return true;
            }
            return false;
        }""",
            timeout=timeout_ms,
        )

    def _wait_actions_menu_visible(self, timeout_ms: int = 8000) -> None:
        self.page.wait_for_function(
            """() => {
            const menus = Array.from(document.querySelectorAll('div.app-menu-container'));
            for (const el of menus) {
                const s = getComputedStyle(el);
                const visible = s.display !== 'none' && s.visibility !== 'hidden' && el.getClientRects().length > 0;
                if (visible) return true;
            }
            return false;
        }""",
            timeout=timeout_ms,
        )

    def _open_datepicker(self) -> None:
        self.page.keyboard.press("Escape")
        self.page.wait_for_timeout(150)

        btn = self.page.locator(self._SEL_DATE_BUTTON).first
        btn.wait_for(state="visible", timeout=12000)
        btn.scroll_into_view_if_needed()

        for _ in range(4):
            try:
                btn.click(timeout=1500)
            except Exception:
                btn.click(force=True)

            try:
                self._wait_datepicker_visible(timeout_ms=2000)
                return
            except Exception:
                try:
                    btn.press("Enter")
                except Exception:
                    pass
                self.page.wait_for_timeout(200)

        raise RuntimeError("No se pudo abrir el calendario (datepicker inline no apareció visible).")

    def _get_visible_months(self) -> list[tuple[int, int]]:
        titles = self.page.locator(self._SEL_DATE_TITLES)
        titles.first.wait_for(state="attached", timeout=4000)

        visible: list[tuple[int, int]] = []
        count = titles.count()
        for i in range(count):
            title = titles.nth(i)
            month_name = (title.locator(self._SEL_MONTH).text_content() or "").strip().lower()
            year_text = (title.locator(self._SEL_YEAR).text_content() or "").strip()
            month_val = _MONTHS_ES.get(month_name)
            if not month_val or not year_text.isdigit():
                continue
            visible.append((int(year_text), month_val))

        if not visible:
            raise RuntimeError("No pude leer mes/año del datepicker (ui-datepicker-title).")

        return visible

    def set_dispatch_date(self, target: date) -> None:
        self._open_datepicker()
        self._wait_datepicker_visible(timeout_ms=8000)

        wanted = (target.year, target.month)

        for _ in range(36):
            visible = self._get_visible_months()
            if wanted in visible:
                break

            before = self.page.locator(self._SEL_DATE_TITLES).first.inner_text()
            if wanted < visible[0]:
                self.page.locator(self._SEL_DATEPICKER_PREV).first.click(force=True)
            elif wanted > visible[-1]:
                self.page.locator(self._SEL_DATEPICKER_NEXT).first.click(force=True)
            else:
                self.page.locator(self._SEL_DATEPICKER_PREV).first.click(force=True)
            self.page.wait_for_function(
                """({sel, prevTxt}) => {
        const el = document.querySelector(sel);
        return el && el.innerText !== prevTxt;
    }""",
                arg={"sel": self._SEL_DATE_TITLES, "prevTxt": before},
                timeout=4000,
            )

        day_link = self.page.locator(
            f'{self._SEL_DATEPICKER_ROOT} '
            f'td:not(.ui-datepicker-other-month):not(.ui-state-disabled) '
            f'a:text-is("{target.day}")'
        ).first

        day_link.wait_for(state="visible", timeout=6000)
        day_link.click(force=True)
        expected = target.strftime("%d %B %Y").lower()
        btn = self.page.locator(self._SEL_DATE_BUTTON).first
        for _ in range(40):
            txt = (btn.text_content() or "").lower()
            if (
                str(target.year) in txt
                and (f"{target.day}" in txt or f"{target.day:02d}" in txt)
            ) or (expected and expected in txt):
                break
            self.page.wait_for_timeout(250)

        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(400)

        expected_month = _MONTHS_NUM_TO_NAME[target.month]
        expected_day = f"{target.day:02d}"
        btn = self.page.locator(self._SEL_DATE_BUTTON).first
        for _ in range(20):
            text = (btn.text_content() or "").lower()
            if (
                expected_month in text
                and str(target.year) in text
                and (expected_day in text or str(target.day) in text)
            ):
                break
            self.page.wait_for_timeout(250)

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
        try:
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(150)
        except Exception:
            pass

        actions_btn = self.page.locator(self._SEL_ACTIONS_BUTTON).first
        actions_btn.wait_for(state="visible", timeout=12000)
        actions_btn.scroll_into_view_if_needed()

        opened = False
        for _ in range(4):
            try:
                actions_btn.click(timeout=1500)
            except Exception:
                actions_btn.click(force=True)

            try:
                self._wait_actions_menu_visible(timeout_ms=2000)
                opened = True
                break
            except Exception:
                self.page.wait_for_timeout(200)

        if not opened:
            raise RuntimeError("No se desplegó el menú de 'Acciones' (app-menu-container no quedó visible).")

        export_span = self.page.locator(
            'div.app-menu-container span.toolbar-menu-button-title:text-is("Exportar")'
        ).first
        export_span.wait_for(state="attached", timeout=8000)
        export_btn = export_span.locator("xpath=ancestor::button[1]").first

        try:
            with self.page.expect_download(timeout=60000) as dl_info:
                export_btn.click(force=True)
            return dl_info.value
        except PWTimeoutError as e:
            raise RuntimeError("No se detectó download después de pulsar Exportar.") from e