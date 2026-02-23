from __future__ import annotations

import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Optional


@dataclass(frozen=True)
class CmdResult:
	returncode: int


class CommandRunner:
	"""Execute commands on a background thread streaming stdout to callbacks."""

	def __init__(self, project_root: Path) -> None:
		self.project_root = project_root
		self._lock = threading.Lock()
		self._running = False

	@property
	def running(self) -> bool:
		with self._lock:
			return self._running

	def run(
		self,
		args: list[str],
		*,
		on_line: Callable[[str], None],
		on_done: Callable[[CmdResult], None],
	) -> None:
		with self._lock:
			if self._running:
				on_line("[WARN] Ya hay un proceso corriendo.\n")
				return
			self._running = True

		def _worker() -> None:
			try:
				on_line(f"$ {' '.join(args)}\n\n")
				proc = subprocess.Popen(
					args,
					cwd=str(self.project_root),
					stdout=subprocess.PIPE,
					stderr=subprocess.STDOUT,
					text=True,
					bufsize=1,
				)
				assert proc.stdout is not None
				for line in proc.stdout:
					on_line(line)
				rc = proc.wait()
				on_done(CmdResult(returncode=rc))
			except Exception as exc:  # pragma: no cover - UI safety net
				on_line(f"\n[ERROR] {exc}\n")
				on_done(CmdResult(returncode=1))
			finally:
				with self._lock:
					self._running = False

		threading.Thread(target=_worker, daemon=True).start()


def py_cmd(module: str, extra: Optional[list[str]] = None) -> list[str]:
	extra = extra or []
	return [sys.executable, "-m", module, *extra]


def full_pipeline_cmd(start: date, end: date) -> list[str]:
	return py_cmd(
		"core.pipeline.full_run",
		["--start", start.isoformat(), "--end", end.isoformat()],
	)
