"""Ana sayfa: modül kartları (başlat/durdur/restart) ve canlı log paneli."""
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from ..config import Module
from ..runner import SYSTEM_ID, ModuleRunner
from .widgets import LogView, StatusBadge, format_uptime

CARD_COLUMNS = 3


class ModuleCard(QFrame):
    def __init__(self, module: Module, runner: ModuleRunner, on_select, parent=None):
        super().__init__(parent)
        self.module_id = module.id
        self.runner = runner
        self.on_select = on_select
        self.setObjectName("Card")
        self.setMinimumWidth(260)
        self.setFixedHeight(150)

        title = QLabel(module.name)
        title.setObjectName("CardTitle")
        first_line = module.command.strip().splitlines()[0] if module.command.strip() else ""
        desc = QLabel(module.description or first_line)
        desc.setObjectName("Muted")
        desc.setWordWrap(True)
        desc.setToolTip(module.command)

        self.badge = StatusBadge()
        self.uptime = QLabel()
        self.uptime.setObjectName("Muted")
        status_row = QHBoxLayout()
        status_row.addWidget(self.badge)
        status_row.addStretch()
        status_row.addWidget(self.uptime)

        self.btn_start = QPushButton("Başlat")
        self.btn_start.setObjectName("Primary")
        self.btn_stop = QPushButton("Durdur")
        self.btn_stop.setObjectName("Danger")
        self.btn_restart = QPushButton("Restart")
        self.btn_start.clicked.connect(lambda: runner.start(self.module_id))
        self.btn_stop.clicked.connect(lambda: runner.stop(self.module_id))
        self.btn_restart.clicked.connect(lambda: runner.restart(self.module_id))
        buttons = QHBoxLayout()
        for b in (self.btn_start, self.btn_stop, self.btn_restart):
            buttons.addWidget(b)

        lay = QVBoxLayout(self)
        lay.addWidget(title)
        lay.addWidget(desc)
        lay.addStretch()
        lay.addLayout(status_row)
        lay.addLayout(buttons)

        proc = runner.proc(module.id)
        proc.state_changed.connect(self.update_state)
        self.update_state(proc.state.value)

    def update_state(self, state: str) -> None:
        self.badge.set_state(state)
        alive = state in ("starting", "running", "stopping")
        self.btn_start.setEnabled(not alive)
        self.btn_stop.setEnabled(alive and state != "stopping")
        self.btn_restart.setEnabled(state != "stopping")
        self.tick()

    def tick(self) -> None:
        started = self.runner.proc(self.module_id).started_at
        self.uptime.setText(format_uptime(time.time() - started) if started else "")

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event):
        self.on_select(self.module_id)
        super().mousePressEvent(event)


class LogPanel(QWidget):
    def __init__(self, runner: ModuleRunner, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.views: dict[str, LogView] = {}
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Seçili modüle komut gönder (ör. PX4 konsoluna: commander status)")
        self.input.returnPressed.connect(self._send)
        btn_send = QPushButton("Gönder")
        btn_send.clicked.connect(self._send)
        btn_clear = QPushButton("Logu Temizle")
        btn_clear.clicked.connect(lambda: self.current_view() and self.current_view().clear())
        row = QHBoxLayout()
        row.addWidget(self.input, 1)
        row.addWidget(btn_send)
        row.addWidget(btn_clear)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.tabs, 1)
        lay.addLayout(row)

        self.ensure_tab(SYSTEM_ID, "Sistem")

    def ensure_tab(self, module_id: str, name: str) -> None:
        if module_id in self.views:
            idx = self.tabs.indexOf(self.views[module_id])
            self.tabs.setTabText(idx, name)
            return
        view = LogView()
        self.views[module_id] = view
        self.tabs.addTab(view, name)
        self.runner.proc(module_id).output.connect(view.append_text)

    def sync(self, modules: list[Module]) -> None:
        ids = {m.id for m in modules} | {SYSTEM_ID}
        for mid in list(self.views):
            if mid not in ids:
                view = self.views.pop(mid)
                self.tabs.removeTab(self.tabs.indexOf(view))
                view.deleteLater()
        for m in modules:
            self.ensure_tab(m.id, m.name)
        # Sekme sırası modül sırasını izlesin; Sistem en sonda.
        order = [m.id for m in modules] + [SYSTEM_ID]
        for target, mid in enumerate(order):
            self.tabs.tabBar().moveTab(self.tabs.indexOf(self.views[mid]), target)

    def select(self, module_id: str) -> None:
        if module_id in self.views:
            self.tabs.setCurrentWidget(self.views[module_id])

    def current_id(self) -> str | None:
        w = self.tabs.currentWidget()
        return next((mid for mid, v in self.views.items() if v is w), None)

    def current_view(self) -> LogView | None:
        return self.tabs.currentWidget()

    def _send(self) -> None:
        text = self.input.text()
        mid = self.current_id()
        if mid is None:
            return
        proc = self.runner.proc(mid)
        if proc.send_input(text):
            self.views[mid].append_text(f"> {text}")
            self.input.clear()
        else:
            self.views[mid].append_text("[hangar] Modül çalışmıyor, komut gönderilemedi.")


class DashboardPage(QWidget):
    def __init__(self, runner: ModuleRunner, title: str = "Kontrol Paneli", start_label: str = "Tümünü Başlat",
                 stop_label: str = "Tümünü Durdur", on_start_all=None, parent=None):
        super().__init__(parent)
        self.runner = runner
        self.cards: dict[str, ModuleCard] = {}

        title = QLabel(title)
        title.setObjectName("PageTitle")
        self.btn_start_all = QPushButton(f"▶  {start_label}")
        self.btn_start_all.setObjectName("Primary")
        self.btn_start_all.setToolTip("'Tümünü Başlat'a dahil modülleri sırayla, hazır olmalarını bekleyerek açar.")
        self.btn_stop_all = QPushButton(f"■  {stop_label}")
        self.btn_stop_all.setObjectName("Danger")
        self.btn_cleanup = QPushButton("Artıkları Temizle")
        self.btn_cleanup.setToolTip("Arkada asılı kalmış gz / px4 / agent süreçlerini öldürür.")
        self.btn_start_all.clicked.connect(on_start_all or runner.start_all)
        self.btn_stop_all.clicked.connect(runner.stop_all)
        self.btn_cleanup.clicked.connect(self._cleanup)
        runner.sequence_running.connect(lambda on: self.btn_start_all.setEnabled(not on))

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.btn_start_all)
        top.addWidget(self.btn_stop_all)
        top.addWidget(self.btn_cleanup)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(10)
        self.grid.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self.grid_host)

        self.logs = LogPanel(runner)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(scroll)
        splitter.addWidget(self.logs)
        splitter.setChildrenCollapsible(False)
        scroll.setMinimumHeight(170)
        self.logs.setMinimumHeight(150)
        splitter.setSizes([480, 300])

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(splitter, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)
        self.rebuild()

    def rebuild(self) -> None:
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w:
                w.hide()  # deleteLater bir sonraki olay döngüsünde siler; o ana kadar görünmesin
                w.setParent(None)
                w.deleteLater()
        self.cards.clear()
        modules = self.runner.cfg.modules
        for i, m in enumerate(modules):
            card = ModuleCard(m, self.runner, self.select)
            self.cards[m.id] = card
            self.grid.addWidget(card, i // CARD_COLUMNS, i % CARD_COLUMNS)
        for c in range(CARD_COLUMNS):
            self.grid.setColumnStretch(c, 1)
        self.grid.setRowStretch(len(modules) // CARD_COLUMNS + 1, 1)
        self.logs.sync(modules)

    def select(self, module_id: str) -> None:
        for mid, card in self.cards.items():
            card.set_selected(mid == module_id)
        self.logs.select(module_id)

    def _tick(self) -> None:
        for card in self.cards.values():
            card.tick()

    def _cleanup(self) -> None:
        answer = QMessageBox.question(
            self, "Artıkları temizle",
            "Arkada kalmış simülasyon süreçleri zorla kapatılacak:\n\n"
            + self.runner.cfg.cleanup_command.strip() + "\n\nDevam edilsin mi?",
        )
        if answer == QMessageBox.Yes:
            self.logs.select(SYSTEM_ID)
            self.runner.run_cleanup()
