"""Kurulum sayfası: takımın sabitlediği sürümleri gösterir ve tek tıkla kurar."""
import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import installer
from ..paths import APP_DIR, VERSIONS_FILE
from ..process import ManagedProcess, child_env
from .widgets import LogView

COL_NAME, COL_REQUIRED, COL_INSTALLED, COL_STATUS, COL_ACTION = range(5)


class _CheckSignals(QObject):
    result = Signal(str, str)  # bileşen id, yüklü sürüm
    done = Signal()


class InstallPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vs = installer.VersionSet()
        self.installed: dict[str, str] = {}
        self.buttons: dict[str, QPushButton] = {}
        self._queue: list[str] = []
        self._running_id: str | None = None

        self.proc = ManagedProcess("Kurulum", self)
        self.proc.finished.connect(self._on_install_finished)
        self.signals = _CheckSignals()
        self.signals.result.connect(self._on_check_result)
        self.signals.done.connect(lambda: self.btn_refresh.setEnabled(True))

        title = QLabel("Kurulum")
        title.setObjectName("PageTitle")
        self.info = QLabel()
        self.info.setObjectName("Muted")
        self.btn_refresh = QPushButton("Kontrol Et")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_pull = QPushButton("Sürüm Listesini Güncelle (git pull)")
        self.btn_pull.setVisible(installer.is_git_checkout())
        self.btn_pull.clicked.connect(self._git_pull)
        self.btn_missing = QPushButton("Eksikleri Kur")
        self.btn_missing.setObjectName("Primary")
        self.btn_missing.clicked.connect(self._install_missing)
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setObjectName("Danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addSpacing(12)
        top.addWidget(self.info)
        top.addStretch()
        top.addWidget(self.btn_pull)
        top.addWidget(self.btn_refresh)
        top.addWidget(self.btn_missing)
        top.addWidget(self.btn_cancel)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Bileşen", "Takım sürümü", "Sende yüklü", "Durum", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        for col in (COL_REQUIRED, COL_INSTALLED, COL_ACTION):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.Fixed)
        self.table.setColumnWidth(COL_STATUS, 150)

        self.log = LogView()
        self.proc.output.connect(self.log.append_text)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.table, 3)
        lay.addWidget(QLabel("Kurulum çıktısı"))
        lay.addWidget(self.log, 2)

        self.reload()

    # --- liste ---------------------------------------------------------------------

    def reload(self) -> None:
        try:
            self.vs = installer.load_versions()
        except Exception as e:  # bozuk yaml kullanıcıya gösterilsin
            self.info.setText(f"{VERSIONS_FILE} okunamadı: {e}")
            return
        self.info.setText(f"Takım sürüm seti: {self.vs.team_version}")
        self.buttons.clear()
        self.table.setRowCount(len(self.vs.components))
        for row, comp in enumerate(self.vs.components):
            name = QTableWidgetItem(comp.name)
            name.setToolTip(comp.description)
            self.table.setItem(row, COL_NAME, name)
            self.table.setItem(row, COL_REQUIRED, QTableWidgetItem(comp.required))
            self.table.setItem(row, COL_INSTALLED, QTableWidgetItem("…"))
            self.table.setItem(row, COL_STATUS, QTableWidgetItem(""))
            btn = QPushButton("Kur")
            btn.clicked.connect(lambda _=False, cid=comp.id: self._install([cid]))
            self.buttons[comp.id] = btn
            self.table.setCellWidget(row, COL_ACTION, btn)
        self.refresh()

    def refresh(self) -> None:
        self.btn_refresh.setEnabled(False)
        vs = self.vs

        def work():
            for comp in vs.components:
                self.signals.result.emit(comp.id, installer.check_installed(vs, comp))
            self.signals.done.emit()

        threading.Thread(target=work, daemon=True).start()

    def _row(self, cid: str) -> int:
        return next(i for i, c in enumerate(self.vs.components) if c.id == cid)

    def _on_check_result(self, cid: str, installed: str) -> None:
        if not any(c.id == cid for c in self.vs.components):
            return
        comp = self.vs.components[self._row(cid)]
        self.installed[cid] = installed
        row = self._row(cid)
        self.table.item(row, COL_INSTALLED).setText(installed or "—")
        status = self.table.item(row, COL_STATUS)
        btn = self.buttons[cid]
        if installer.is_up_to_date(comp, installed):
            status.setText("✅ Güncel")
            status.setForeground(Qt.green)
            btn.setText("Yeniden Kur")
        elif installed:
            status.setText("⚠️ Farklı sürüm")
            status.setForeground(Qt.yellow)
            btn.setText("Güncelle")
        else:
            status.setText("❌ Yüklü değil")
            status.setForeground(Qt.red)
            btn.setText("Kur")

    # --- kurulum -------------------------------------------------------------------

    def _install_missing(self) -> None:
        missing = [c.id for c in self.vs.components if not installer.is_up_to_date(c, self.installed.get(c.id, ""))]
        if not missing:
            QMessageBox.information(self, "Kurulum", "Her şey takım sürümüyle aynı.")
            return
        self._install(missing)

    def _install(self, ids: list[str]) -> None:
        if self.proc.is_alive():
            return
        names = "\n".join("• " + self.vs.components[self._row(i)].name for i in ids)
        answer = QMessageBox.question(
            self, "Kurulum",
            f"Şunlar kurulacak:\n{names}\n\nBazı adımlar yönetici şifresi isteyecek ve uzun sürebilir. Devam?",
        )
        if answer != QMessageBox.Yes:
            return
        self._queue = list(ids)
        self._set_busy(True)
        self._next()

    def _next(self) -> None:
        if not self._queue:
            self._running_id = None
            self._set_busy(False)
            self.proc.output.emit("[hangar] Kurulum kuyruğu bitti.")
            self.refresh()
            return
        cid = self._queue.pop(0)
        comp = self.vs.components[self._row(cid)]
        self._running_id = cid
        self.proc.output.emit(f"\n========== {comp.name} ({comp.required}) ==========")
        self.table.item(self._row(cid), COL_STATUS).setText("⏳ Kuruluyor…")
        self.proc.start(installer.install_script(self.vs, comp), installer.component_env(self.vs, comp))

    def _on_install_finished(self, rc: int) -> None:
        if self._running_id is None:
            return
        if self._running_id == "__git__":
            self._running_id = None
            self._set_busy(False)
            self.reload()
            return
        if rc != 0:
            comp = self.vs.components[self._row(self._running_id)]
            self.proc.output.emit(f"[hangar] {comp.name} kurulumu başarısız (kod {rc}). Kuyruk durduruldu.")
            self._queue = []
        self._next()

    def _cancel(self) -> None:
        self._queue = []
        self.proc.stop(timeout=5)

    def _set_busy(self, busy: bool) -> None:
        for btn in self.buttons.values():
            btn.setEnabled(not busy)
        self.btn_missing.setEnabled(not busy)
        self.btn_pull.setEnabled(not busy)
        self.btn_refresh.setEnabled(not busy)
        self.btn_cancel.setEnabled(busy)

    def _git_pull(self) -> None:
        if self.proc.is_alive():
            return
        self._running_id = "__git__"
        self._set_busy(True)
        self.proc.start(f"git -C '{APP_DIR}' pull --ff-only", child_env())
