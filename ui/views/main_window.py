from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import customtkinter as ctk

from ui.controllers.actions import (
	CommandRunner,
	build_master_cmd,
	export_raw_cmd,
	queue_ids_cmd,
	run_clean_cmd,
)


def _parse_date(value: str) -> date:
	value = value.strip()
	return datetime.strptime(value, "%Y-%m-%d").date()


class MainWindow(ctk.CTk):
	def __init__(self, project_root: Path) -> None:
		super().__init__()

		self.project_root = project_root
		self.runner = CommandRunner(project_root)

		self.title("RIOSAC - Control Panel (dev)")
		self.geometry("980x640")

		top = ctk.CTkFrame(self)
		top.pack(fill="x", padx=12, pady=12)

		ctk.CTkLabel(top, text="Start (YYYY-MM-DD):").grid(row=0, column=0, padx=8, pady=8, sticky="w")
		self.start_entry = ctk.CTkEntry(top, width=140)
		self.start_entry.grid(row=0, column=1, padx=8, pady=8, sticky="w")

		ctk.CTkLabel(top, text="End (YYYY-MM-DD):").grid(row=0, column=2, padx=8, pady=8, sticky="w")
		self.end_entry = ctk.CTkEntry(top, width=140)
		self.end_entry.grid(row=0, column=3, padx=8, pady=8, sticky="w")

		today = date.today().isoformat()
		self.start_entry.insert(0, today)
		self.end_entry.insert(0, today)

		btns = ctk.CTkFrame(self)
		btns.pack(fill="x", padx=12, pady=(0, 12))

		self.btn_export = ctk.CTkButton(btns, text="1) Export RAW (Capa A)", command=self.on_export_raw)
		self.btn_export.pack(side="left", padx=8, pady=10)

		self.btn_clean = ctk.CTkButton(btns, text="2) Clean (Capa B)", command=self.on_clean)
		self.btn_clean.pack(side="left", padx=8, pady=10)

		self.btn_master = ctk.CTkButton(btns, text="3) Build Masters (Capa B)", command=self.on_master)
		self.btn_master.pack(side="left", padx=8, pady=10)

		self.btn_open_data = ctk.CTkButton(btns, text="Abrir /data", command=self.open_data_folder)
		self.btn_open_data.pack(side="right", padx=8, pady=10)

		self.btn_open_logs = ctk.CTkButton(btns, text="Abrir /logs", command=self.open_logs_folder)
		self.btn_open_logs.pack(side="right", padx=8, pady=10)

		self.btn_queue = ctk.CTkButton(btns, text="4) Queue IDs (Capa C)", command=self.on_queue_ids)
		self.btn_queue.pack(side="left", padx=8, pady=10)

		self.output = ctk.CTkTextbox(self, wrap="none")
		self.output.pack(fill="both", expand=True, padx=12, pady=(0, 12))
		self._write("Listo. Flujo recomendado: Export RAW -> Clean -> Build Masters\n\n")

	def _set_buttons_enabled(self, enabled: bool) -> None:
		state = "normal" if enabled else "disabled"
		self.btn_export.configure(state=state)
		self.btn_clean.configure(state=state)
		self.btn_master.configure(state=state)
		self.btn_open_data.configure(state=state)
		self.btn_open_logs.configure(state=state)
		self.btn_queue.configure(state=state)

	def _write(self, text: str) -> None:
		self.output.insert("end", text)
		self.output.see("end")

	def _run_cmd(self, args: list[str]) -> None:
		self._set_buttons_enabled(False)

		def on_line(line: str) -> None:
			self.after(0, lambda: self._write(line))

		def on_done(result) -> None:
			def _finish() -> None:
				self._write(f"\n[EXIT] returncode={result.returncode}\n\n")
				self._set_buttons_enabled(True)

			self.after(0, _finish)

		self.runner.run(args, on_line=on_line, on_done=on_done)

	def on_export_raw(self) -> None:
		try:
			start = _parse_date(self.start_entry.get())
			end = _parse_date(self.end_entry.get())
			if end < start:
				raise ValueError("End no puede ser menor que Start.")
		except Exception as exc:
			self._write(f"[ERROR] Fechas inválidas: {exc}\n\n")
			return

		self._run_cmd(export_raw_cmd(start, end))

	def on_clean(self) -> None:
		self._run_cmd(run_clean_cmd())

	def on_master(self) -> None:
		self._run_cmd(build_master_cmd())

	def on_queue_ids(self) -> None:
		try:
			end = _parse_date(self.end_entry.get())
		except Exception as exc:
			self._write(f"[ERROR] Fecha End inválida: {exc}\n\n")
			return

		month = end.strftime("%Y-%m")
		self._run_cmd(queue_ids_cmd(month))

	def open_data_folder(self) -> None:
		path = self.project_root / "data"
		os.startfile(path)

	def open_logs_folder(self) -> None:
		path = self.project_root / "logs"
		os.startfile(path)
