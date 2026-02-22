from __future__ import annotations

from pathlib import Path

from ui.views.main_window import MainWindow


def main() -> None:
	project_root = Path(__file__).resolve().parents[1]
	app = MainWindow(project_root=project_root)
	app.mainloop()


if __name__ == "__main__":
	main()
