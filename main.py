#!/usr/bin/env python3
"""ECOFUAV Hangar: Gazebo / PX4 / ROS 2 ortamını terminalsiz yönetir."""
import signal
import sys

if not sys.platform.startswith("linux"):
    sys.exit("Bu uygulama yalnızca Linux'ta (veya Windows'ta WSL2 içinde) çalışır.")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from hangar import APP_NAME
from hangar.ui.main_window import MainWindow
from hangar.ui.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName("ecofuav-hangar")
    apply_theme(app)
    window = MainWindow()
    window.show()

    # Terminalden Ctrl+C gelirse modülleri düzgünce kapatarak çık.
    signal.signal(signal.SIGINT, lambda *_: window.close())
    timer = QTimer()
    timer.timeout.connect(lambda: None)  # Python'un sinyalleri işleyebilmesi için
    timer.start(250)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
