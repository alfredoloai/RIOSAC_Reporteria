from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
from playwright.sync_api import Download, Page
from playwright.sync_api import TimeoutError as PWTimeoutError, sync_playwright

from core.config.settings import load_settings
from core.infra.playwright.browser import BrowserSession, create_session
from core.infra.playwright.eta_client import EtaClient, EtaCredentials
from core.layers.capa_d.manifest import ProcessedManifest


GENERAL_LABELS: List[str] = [
    "Orden de trabajo",
    "ID de actividad",
    "Tipo de actividad",
    "Grupo",
    "Corte Acometida",
    "Tecnología",
    "Franja",
    "Estado de actividad",
    "Dirección",
    "Provincia",
    "Ciudad",
    "Parroquia",
    "Coordenada X",
    "Coordenada Y",
    "Referencia",
    "Zona de trabajo",
    "Duración",
    "Inicio – Fin",
]

VENTA_LABELS: List[str] = [
    "Canal de Venta",
    "Ejecutivo de Venta",
    "Agencia",
]

CIERRE_LABELS: List[str] = [
    "Observaciones de cierre",
]


@dataclass(frozen=True)
class OrderDetail:
    order_id: str
    data: Dict[str, str]


class DetailExtractor:
    def __init__(
        self,
        month: str,
        overwrite: bool,
        logger=None,
        *,
        session: Optional[BrowserSession] = None,
        eta_client: Optional[EtaClient] = None,
    ) -> None:
        self.month = month
        self.overwrite = overwrite
        self.logger = logger
        self.settings = load_settings()
        self.manifest = ProcessedManifest(Path(self.settings.paths.manifests_dir) / f"capa_d_{month}.json")
        self.queue_path = self.settings.paths.data_dir / "masters" / "capa_c" / f"queue_ids_{month}.json"
        self.output_dir = self.settings.paths.data_dir / "masters" / "capa_d"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_path = self.output_dir / f"capa_d_{month}.parquet"
        self._external_session = session
        self._external_client = eta_client

    # ---------------------------
    # Helpers
    # ---------------------------

    def _load_queue(self) -> list[str]:
        if not self.queue_path.exists():
            raise FileNotFoundError(f"No existe la queue para el mes {self.month}: {self.queue_path}")
        payload = json.loads(self.queue_path.read_text(encoding="utf-8"))
        ids = payload.get("ids", [])
        return [str(x) for x in ids]

    def _clean_value(self, raw: str) -> str:
        """
        Corrige el caso típico del UI donde aparece pegado 'Error' al final:
          - 'NOError' -> 'NO'
          - '07-10Error' -> '07-10'
        y normaliza espacios.
        """
        if raw is None:
            return ""
        s = " ".join(str(raw).split()).strip()

        # Quitar sufijo "Error" pegado o separado
        s = re.sub(r"(?:\s*Error)\s*$", "", s).strip()
        s = re.sub(r"Error\s*$", "", s).strip()  # por si viene pegado

        return s

    def _read_field_text(self, page: Page, labels: Iterable[str]) -> str:
        """
        Lee el valor asociado a un label en la vista de detalles.
        Estrategia:
          1) Buscar el label en varias variantes (label/div/span).
          2) Tomar el valor más cercano (mismo contenedor o hermano).
          3) Limpiar el valor y retornar el primero no vacío.
        """
        for label in labels:
            label_txt = str(label).strip()
            if not label_txt:
                continue

            candidates = [
                page.locator(f".form-element__label:has-text('{label_txt}')").first,
                page.locator(f".button-upload__label:has-text('{label_txt}')").first,
                page.locator(f"label:has-text('{label_txt}')").first,
                page.locator(f"div:has-text('{label_txt}')").first,
                page.locator(f"span:has-text('{label_txt}')").first,
            ]

            found = None
            for loc in candidates:
                try:
                    loc.wait_for(state="visible", timeout=1500)
                    found = loc
                    break
                except Exception:
                    continue

            if not found:
                continue

            try:
                value = found.evaluate(
                    """(el, labelText) => {
  const norm = (s) => (s || '').replace(/\\s+/g,' ').trim();

  // 1) Caso ideal: dentro de un contenedor tipo "form-element-row"
  const row =
    el.closest('.form-element-row') ||
    el.closest('.form-element') ||
    el.parentElement;

  // Intentar encontrar el "value" típico en la misma fila
  const pickValueNode = (root) => {
    if (!root) return null;

    // algunos UIs separan label y value con clases
    let v =
      root.querySelector('.form-element__value') ||
      root.querySelector('.form-element__text') ||
      root.querySelector('.form-element__content') ||
      null;

    if (v) return v;

    // si no hay clases, probar con el hermano inmediato del label
    if (el.nextElementSibling) return el.nextElementSibling;

    // o el siguiente bloque dentro del row (muy común: label arriba, valor abajo)
    const kids = Array.from(root.children || []);
    const idx = kids.indexOf(el);
    if (idx >= 0 && kids[idx + 1]) return kids[idx + 1];

    return null;
  };

  const valueNode = pickValueNode(row);

  let txt = '';
  if (valueNode) {
    txt = norm(valueNode.innerText || '');
  }

  // Si el texto contiene el label al inicio (por layouts raros), quitarlo
  if (txt && txt.toLowerCase().startsWith(labelText.toLowerCase())) {
    txt = norm(txt.slice(labelText.length));
  }

  // 2) Fallback: clonar contenedor y borrar labels
  if (!txt && row) {
    const clone = row.cloneNode(true);
        const kill = clone.querySelectorAll('.form-element__label, label, .button-upload__label, .button-upload__action');
    kill.forEach(n => n.remove());
    txt = norm(clone.innerText || '');
    if (txt.toLowerCase().startsWith(labelText.toLowerCase())) {
      txt = norm(txt.slice(labelText.length));
    }
  }

  // 3) Fallback extra: buscar un hermano siguiente del contenedor
  if (!txt && row && row.nextElementSibling) {
    const nxt = row.nextElementSibling;
    txt = norm(nxt.innerText || '');
    if (txt.toLowerCase().startsWith(labelText.toLowerCase())) {
      txt = norm(txt.slice(labelText.length));
    }
  }

  return txt;
}""",
                    label_txt,
                )
                cleaned = self._clean_value(value)
                if cleaned:
                    return cleaned
            except Exception:
                continue

        return ""

    def _click_tab_if_exists(self, page: Page, text: str) -> bool:
        tab = page.locator(f'a.button.inline:has-text("{text}")').first
        try:
            tab.wait_for(state="visible", timeout=2000)
            tab.click(force=True)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(350)
            return True
        except Exception:
            return False

    def _go_back_to_detalles(self, page: Page) -> None:
        """
        Vuelve a la pantalla 'Detalles de actividad' cuando entraste
        a secciones como Info Venta.
        """
        back_candidates = [
            page.locator('a:has-text("Detalles de actividad")').first,
            page.locator('button:has-text("Detalles de actividad")').first,
            page.locator('text=< Detalles de actividad').first,
            page.locator('text=Detalles de actividad').first,
        ]

        for loc in back_candidates:
            try:
                if loc.count() == 0:
                    continue
                loc.wait_for(state="visible", timeout=1200)
                loc.click(force=True)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(350)
                break
            except Exception:
                continue

        # Asegurar que estamos en detalles
        try:
            page.locator("text=Orden de trabajo").first.wait_for(state="visible", timeout=8000)
        except Exception:
            pass

    def _download_signature_base64(self, page: Page) -> str:
        btn = page.locator("a.download-button").first
        try:
            btn.wait_for(state="visible", timeout=2500)
        except Exception:
            return ""

        try:
            with page.expect_download(timeout=20000) as dl_info:
                btn.click(force=True)

            download: Download = dl_info.value
            temp_path = download.path()

            if temp_path:
                data = temp_path.read_bytes()
                # Borra el archivo temporal del download (según soporte Playwright)
                try:
                    download.delete()
                except Exception:
                    pass
                return base64.b64encode(data).decode("ascii")
        except PWTimeoutError:
            return ""
        except Exception:
            return ""

        return ""

    # ---------------------------
    # Search
    # ---------------------------

    def _focus_search(self, page: Page):
        candidates = [
            page.locator('input[placeholder="Buscar en actividades"]').first,
            page.locator('input[placeholder*="Buscar en activ"]').first,
            page.locator('header input[placeholder*="Buscar"]').first,
            page.locator('input[type="search"][placeholder*="Buscar"]').first,
            page.locator('input[type="search"]').first,
        ]

        for loc in candidates:
            try:
                loc.wait_for(state="visible", timeout=8000)
                loc.scroll_into_view_if_needed()
                loc.click(timeout=2000, force=True)
                return loc
            except Exception:
                continue

        # fallback
        try:
            page.locator("header").click(timeout=2000, force=True)
        except Exception:
            pass

        return page.locator('input[type="search"]').first

    def _search_and_open(self, page: Page, order_id: str) -> bool:
        field = self._focus_search(page)

        # limpiar
        try:
            field.click(force=True)
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
        except Exception:
            try:
                field.fill("")
            except Exception:
                pass

        # escribir
        try:
            page.keyboard.type(str(order_id), delay=35)
        except Exception:
            try:
                field.type(str(order_id), delay=35)
            except Exception:
                return False

        # disparar búsqueda
        try:
            page.keyboard.press("Enter")
        except Exception:
            pass

        # esperar resultados
        results = page.locator(".global-search-found-item[role='link']")
        try:
            results.first.wait_for(state="visible", timeout=10000)
        except Exception:
            # si aparece "Sin resultados"
            try:
                if page.locator("text=Sin resultados").first.is_visible():
                    return False
            except Exception:
                pass
            return False

        # click al resultado exacto si existe
        exact = page.locator(".global-search-found-item[role='link']", has_text=str(order_id)).first
        try:
            exact.wait_for(state="visible", timeout=3000)
            exact.click(force=True)
        except Exception:
            try:
                results.first.click(force=True)
            except Exception:
                return False

        page.wait_for_timeout(700)

        # ya en detalles
        try:
            page.locator("text=Orden de trabajo").first.wait_for(state="visible", timeout=12000)
        except Exception:
            return False

        return True

    # ---------------------------
    # Extract
    # ---------------------------

    def _extract_general(self, page: Page) -> Dict[str, str]:
        data: Dict[str, str] = {}
        for label in GENERAL_LABELS:
            data[label] = self._read_field_text(page, [label])
        return data

    def _extract_info_venta(self, page: Page) -> Dict[str, str]:
        out = {label: "" for label in VENTA_LABELS}

        # Puede no existir
        if not self._click_tab_if_exists(page, "Info Venta"):
            return out

        # Esperar a que se renderice
        try:
            page.locator("text=Canal de Venta").first.wait_for(state="visible", timeout=8000)
        except Exception:
            pass

        for label in VENTA_LABELS:
            out[label] = self._read_field_text(page, [label])

        # IMPORTANTÍSIMO: volver a Detalles antes de continuar
        self._go_back_to_detalles(page)
        return out

    def _extract_info_cierre(self, page: Page) -> Dict[str, str]:
        out = {label: "" for label in CIERRE_LABELS}

        # SIEMPRE debe existir; si por algo no hace click, seguimos igual y tratamos de leer.
        self._click_tab_if_exists(page, "Info. Cierre")

        try:
            page.locator("text=Observaciones de cierre").first.wait_for(state="visible", timeout=8000)
        except Exception:
            pass

        for label in CIERRE_LABELS:
            out[label] = self._read_field_text(page, [label])

        out["Firma Cliente"] = self._download_signature_base64(page)
        return out

    def _process_order(self, page: Page, order_id: str) -> Optional[OrderDetail]:
        if not self.overwrite and self.manifest.is_processed(order_id):
            if self.logger:
                self.logger.info("Skip (manifest): %s", order_id)
            return None

        opened = self._search_and_open(page, order_id)
        if not opened:
            if self.logger:
                self.logger.warning("No se encontró resultado para %s", order_id)
            return None

        record: Dict[str, str] = {}
        try:
            record.update(self._extract_general(page))

            # Info Venta (si existe). Si no existe, se queda en blanco.
            record.update(self._extract_info_venta(page))

            # SIEMPRE cerrar al final
            record.update(self._extract_info_cierre(page))

        except Exception as exc:
            if self.logger:
                self.logger.exception("Error extrayendo %s: %s", order_id, exc)
            return None

        self.manifest.mark_processed(order_id)
        return OrderDetail(order_id=order_id, data=record)

    # ---------------------------
    # Run
    # ---------------------------

    def run(self) -> Path:
        ids = self._load_queue()
        if not ids:
            raise RuntimeError(f"Queue {self.queue_path} vacía")

        collected: list[Dict[str, str]] = []

        if self._external_session and self._external_client:
            session = self._external_session
            client = self._external_client
            owns_session = False
        else:
            owns_session = True

        if owns_session:
            with sync_playwright() as pw:
                session = create_session(
                    pw,
                    headless=self.settings.pw_headless,
                    slow_mo_ms=self.settings.pw_slowmo_ms,
                    timeout_ms=self.settings.pw_timeout_ms,
                )
                client = EtaClient(session.page, self.settings.eta_base_url)
                creds = EtaCredentials(
                    username=self.settings.eta_username,
                    password=self.settings.eta_password,
                )

                if self.logger:
                    self.logger.info("Login ETA...")
                client.login(creds)
                client.assert_logged_in()
                if self.logger:
                    self.logger.info("Login OK")

                try:
                    for order_id in ids:
                        detail = self._process_order(session.page, order_id)
                        if detail:
                            collected.append(detail.data)
                finally:
                    try:
                        client.logout()
                    except Exception:
                        pass
                    session.close()
        else:
            for order_id in ids:
                detail = self._process_order(session.page, order_id)
                if detail:
                    collected.append(detail.data)

        df = pd.DataFrame(collected)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        df.to_parquet(self.output_path, index=False)
        return self.output_path


def extract_details(
    month: str,
    overwrite: bool = False,
    logger=None,
    *,
    session: Optional[BrowserSession] = None,
    eta_client: Optional[EtaClient] = None,
) -> Path:
    extractor = DetailExtractor(
        month=month,
        overwrite=overwrite,
        logger=logger,
        session=session,
        eta_client=eta_client,
    )
    return extractor.run()