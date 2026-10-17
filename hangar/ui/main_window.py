import time

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QListWidget, QVBoxLayout, QMainWindow, QMessageBox, QProgressDialog,
    QStackedWidget, QWidget,
)

from .. import APP_NAME, __version__
from ..config import LauncherConfig, load_config
from ..paths import ICON_FILE, USER_MODULES_FILE
from ..runner import ModuleRunner
from .dashboard import DashboardPage
from .fleet_page import FleetPage
from .install_page import InstallPage
from .module_editor import ModuleEditorPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.setWindowIcon(QIcon(str(ICON_FILE)))
        self.resize(1280, 820)

        try:
            cfg = load_config()
        except Exception as e:  # bozuk modules.yaml uygulamayı açılmaz hale getirmesin
            QMessageBox.critical(None, "Modül dosyası okunamadı", f"{USER_MODULES_FILE}\n\n{e}\n\nBoş liste ile açılıyor.")
            cfg = LauncherConfig()
        self.runner = ModuleRunner(cfg, self)
        self.runner.message.connect(lambda msg: self.statusBar().showMessage(msg, 8000))

        self.dashboard = DashboardPage(self.runner)
        self.editor = ModuleEditorPage(cfg)
        self.editor.saved.connect(self._on_config_saved)
        self.fleet = FleetPage(self.runner)
        self.fleet.message.connect(lambda msg: self.statusBar().showMessage(msg, 8000))
        self.install = InstallPage()

        self.stack = QStackedWidget()
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFrameShape(QListWidget.NoFrame)
        self.sidebar.setIconSize(QSize(18, 18))
        for label, page in (
            ("🚀  Kontrol Paneli", self.dashboard),
            ("✈️  Filo", self.fleet),
            ("🧩  Modüller", self.editor),
            ("📦  Kurulum", self.install),
        ):
            self.sidebar.addItem(label)
            self.stack.addWidget(page)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        brand = QLabel(f'<span style="font-size:15pt; font-weight:700; letter-spacing:1px;">{APP_NAME.split()[0]}</span>'
                       f'<br><span style="color:#8b949e;">{" ".join(APP_NAME.split()[1:])} · v{__version__}</span>')
        brand.setObjectName("Brand")
        side = QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(190)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(0, 0, 0, 0)
        side_lay.setSpacing(0)
        side_lay.addWidget(brand)
        side_lay.addWidget(self.sidebar, 1)
        lay.addWidget(side)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage(f"Modül dosyası: {USER_MODULES_FILE}", 8000)

    def _on_config_saved(self, cfg: LauncherConfig) -> None:
        self.runner.set_config(cfg)
        self.dashboard.rebuild()
        self.fleet.apply()
        self.statusBar().showMessage("Modüller kaydedildi. Çalışan modüller yeni ayarları restart sonrası kullanır.", 8000)

    def closeEvent(self, event):
        if self.fleet.dirty:
            answer = QMessageBox.question(
                self, "Kaydedilmemiş değişiklikler",
                "Filoda kaydedilmemiş değişiklikler var. Kaydedilsin mi?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if answer == QMessageBox.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.Save:
                self.fleet.save()

        if self.editor.dirty:
            answer = QMessageBox.question(
                self, "Kaydedilmemiş değişiklikler",
                "Modüllerde kaydedilmemiş değişiklikler var. Kaydedilsin mi?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if answer == QMessageBox.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.Save:
                self.editor.save()

        alive = self.runner.any_alive() or self.fleet.runner.any_alive() or self.install.proc.is_alive()
        if alive:
            answer = QMessageBox.question(
                self, "Çıkış",
                "Çalışan modüller var. Hepsi durdurulup çıkılsın mı?",
                QMessageBox.Yes | QMessageBox.Cancel,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self._stop_everything()
        event.accept()

    def _stop_everything(self) -> None:
        self.runner.stop_all()
        self.fleet.runner.stop_all()
        self.runner.system.stop(timeout=2)
        self.fleet.runner.system.stop(timeout=2)
        self.install.proc.stop(timeout=5)
        dialog = QProgressDialog("Modüller durduruluyor…", None, 0, 0, self)
        dialog.setMinimumDuration(0)
        dialog.show()
        deadline = time.monotonic() + 40
        while (self.runner.any_alive() or self.fleet.runner.any_alive() or self.install.proc.is_alive()) and time.monotonic() < deadline:
            QApplication.processEvents()
            time.sleep(0.05)
        dialog.close()
