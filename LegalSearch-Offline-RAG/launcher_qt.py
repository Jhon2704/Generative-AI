from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ui_adapter import BackendAdapter  # noqa: E402
from ui_layout import MainWindow  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    adapter = BackendAdapter()
    window = MainWindow(adapter)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
