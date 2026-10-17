"""Filo sayfası: İHA ekle/kaldır ve birden fazla aracı aynı simülasyonda uçur."""
import copy

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QTableWidget,
    QTabWidget, QVBoxLayout, QWidget,
)

from ..fleet import MODELS, PLACEHOLDER_HELP, FleetConfig, Vehicle, build_modules, load_fleet, save_fleet
from ..runner import ModuleRunner
from .dashboard import DashboardPage

COL_ON, COL_NAME, COL_MODEL, COL_AUTOSTART, COL_X, COL_Y, COL_NODE = range(7)
MANY_VEHICLES = 5


class FleetPage(QWidget):
    message = Signal(str)

    def __init__(self, main_runner: ModuleRunner, parent=None):
        super().__init__(parent)
        self.main_runner = main_runner
        self.fleet: FleetConfig = load_fleet()
        self.runner = ModuleRunner(build_modules(self.fleet, main_runner.cfg), self)
        self.runner.message.connect(self.message)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_editor(), "Filo Düzeni")
        self.flight = DashboardPage(self.runner, title="Filo", start_label="Filoyu Başlat",
                                    stop_label="Filoyu Durdur", on_start_all=self._start_fleet)
        self.tabs.addTab(self.flight, "Uçuş")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.tabs)
        self._load_into_form()
        self._set_dirty(False)

    # --- düzen sekmesi -------------------------------------------------------------

    def _build_editor(self) -> QWidget:
        title = QLabel("Filo")
        title.setObjectName("PageTitle")
        self.dirty_label = QLabel("")
        self.dirty_label.setObjectName("Muted")
        btn_save = QPushButton("Kaydet")
        btn_save.setObjectName("Primary")
        btn_save.clicked.connect(self.save)
        top = QHBoxLayout()
        top.addWidget(title)
        top.addSpacing(12)
        top.addWidget(self.dirty_label)
        top.addStretch()
        top.addWidget(btn_save)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Etkin", "Ad", "Model", "Airframe", "X (m)", "Y (m)", "Eşlik eden komut"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        header = self.table.horizontalHeader()
        for col in (COL_ON, COL_MODEL, COL_AUTOSTART, COL_X, COL_Y):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_NAME, QHeaderView.Interactive)
        self.table.setColumnWidth(COL_NAME, 150)
        header.setSectionResizeMode(COL_NODE, QHeaderView.Stretch)

        btn_add = QPushButton("+ İHA Ekle")
        btn_add.setObjectName("Primary")
        btn_add.clicked.connect(self._add_vehicle)
        btn_remove = QPushButton("Seçiliyi Kaldır")
        btn_remove.clicked.connect(self._remove_vehicle)
        self.count_label = QLabel()
        self.count_label.setObjectName("Muted")
        row = QHBoxLayout()
        row.addWidget(btn_add)
        row.addWidget(btn_remove)
        row.addSpacing(12)
        row.addWidget(self.count_label)
        row.addStretch()

        help_label = QLabel(
            "İlk etkin araç Gazebo'yu açar, diğerleri aynı dünyaya katılır. ROS 2'de her araç "
            "<b>/px4_&lt;no&gt;/fmu/…</b> altında görünür; QGroundControl hepsini otomatik bulur.<br>"
            f"Eşlik eden komutta kullanılabilenler: {PLACEHOLDER_HELP}"
        )
        help_label.setObjectName("Muted")
        help_label.setWordWrap(True)

        self.f_px4_dir = QLineEdit()
        self.f_world = QLineEdit()
        self.f_headless = QCheckBox("Gazebo arayüzünü açma (headless, daha hafif)")
        self.f_agent = QCheckBox("XRCE-DDS Agent'ı filo ile birlikte başlat")
        self.f_companion_setup = QPlainTextEdit()
        self.f_companion_setup.setObjectName("Log")
        self.f_companion_setup.setFixedHeight(50)
        form = QFormLayout()
        form.addRow("PX4 klasörü", self.f_px4_dir)
        form.addRow("Gazebo dünyası", self.f_world)
        form.addRow("", self.f_headless)
        form.addRow("", self.f_agent)
        form.addRow("Eşlik eden komut\nhazırlığı", self.f_companion_setup)
        settings = QGroupBox("Simülasyon ayarları")
        settings.setLayout(form)

        for w in (self.f_px4_dir, self.f_world):
            w.textEdited.connect(self._mark_dirty)
        for w in (self.f_headless, self.f_agent):
            w.toggled.connect(self._mark_dirty)
        self.f_companion_setup.textChanged.connect(self._mark_dirty)
        self.table.itemChanged.connect(self._mark_dirty)

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addLayout(top)
        lay.addWidget(self.table, 1)
        lay.addLayout(row)
        lay.addWidget(help_label)
        lay.addWidget(settings)
        return page

    def _load_into_form(self) -> None:
        self._loading = True
        self.f_px4_dir.setText(self.fleet.px4_dir)
        self.f_world.setText(self.fleet.world)
        self.f_headless.setChecked(self.fleet.headless)
        self.f_agent.setChecked(self.fleet.start_agent)
        self.f_companion_setup.setPlainText("\n".join(self.fleet.companion_setup))
        self.table.setRowCount(0)
        self._row_ids: list[str] = []
        for v in self.fleet.vehicles:
            self._append_row(v)
        self._loading = False
        self._update_count()

    def _append_row(self, v: Vehicle) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._row_ids.append(v.id)

        on = QCheckBox()
        on.setChecked(v.enabled)
        on.toggled.connect(self._mark_dirty)
        on.toggled.connect(self._update_count)
        holder = QWidget()
        hl = QHBoxLayout(holder)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setAlignment(Qt.AlignCenter)
        hl.addWidget(on)
        self.table.setCellWidget(row, COL_ON, holder)

        name = QLineEdit(v.name)
        name.textEdited.connect(self._mark_dirty)
        self.table.setCellWidget(row, COL_NAME, name)

        model = QComboBox()
        model.setEditable(True)
        model.addItems(list(MODELS))
        model.setCurrentText(v.model)
        self.table.setCellWidget(row, COL_MODEL, model)

        autostart = QSpinBox()
        autostart.setRange(0, 99999)
        autostart.setValue(v.autostart)
        autostart.valueChanged.connect(self._mark_dirty)
        self.table.setCellWidget(row, COL_AUTOSTART, autostart)

        # Model seçilince airframe numarası da otomatik gelsin.
        def on_model(text, box=autostart):
            if text in MODELS:
                box.setValue(MODELS[text])
            self._mark_dirty()
        model.currentTextChanged.connect(on_model)

        for col, value in ((COL_X, v.x), (COL_Y, v.y)):
            box = QDoubleSpinBox()
            box.setRange(-1000, 1000)
            box.setDecimals(1)
            box.setValue(value)
            box.valueChanged.connect(self._mark_dirty)
            self.table.setCellWidget(row, col, box)

        node = QLineEdit(v.companion_command)
        node.setPlaceholderText("ör. ros2 run iha_control offboard_node --ros-args -r __ns:=/{ns}")
        node.textEdited.connect(self._mark_dirty)
        self.table.setCellWidget(row, COL_NODE, node)

    def _read_form(self) -> FleetConfig:
        cfg = FleetConfig(
            px4_dir=self.f_px4_dir.text().strip() or "~/PX4-Autopilot",
            world=self.f_world.text().strip() or "default",
            headless=self.f_headless.isChecked(),
            start_agent=self.f_agent.isChecked(),
            companion_setup=[l for l in self.f_companion_setup.toPlainText().splitlines() if l.strip()],
        )
        for row, vid in enumerate(self._row_ids):
            cell = self.table.cellWidget
            cfg.vehicles.append(Vehicle(
                id=vid,
                enabled=cell(row, COL_ON).findChild(QCheckBox).isChecked(),
                name=cell(row, COL_NAME).text().strip() or f"İHA-{row + 1}",
                model=cell(row, COL_MODEL).currentText().strip() or "gz_x500",
                autostart=cell(row, COL_AUTOSTART).value(),
                x=cell(row, COL_X).value(),
                y=cell(row, COL_Y).value(),
                companion_command=cell(row, COL_NODE).text().strip(),
            ))
        return cfg

    def _add_vehicle(self) -> None:
        current = self._read_form()
        n = len(current.vehicles)
        # Yeni aracı diğerlerinden 3 m uzağa, sırayla sağa/sola yerleştir.
        y = 3.0 * ((n + 1) // 2) * (1 if n % 2 else -1)
        template = current.vehicles[-1] if current.vehicles else Vehicle()
        v = Vehicle(name=f"İHA-{n + 1}", model=template.model, autostart=template.autostart,
                    x=template.x if current.vehicles else 0.0, y=y, companion_command=template.companion_command)
        self._loading = True
        self._append_row(v)
        self._loading = False
        self.table.selectRow(self.table.rowCount() - 1)
        self._update_count()
        self._set_dirty(True)

    def _remove_vehicle(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Kaldır", "Önce tablodan bir İHA seçin.")
            return
        name = self.table.cellWidget(row, COL_NAME).text()
        if QMessageBox.question(self, "Kaldır", f"'{name}' filodan kaldırılsın mı?") != QMessageBox.Yes:
            return
        self.table.removeRow(row)
        del self._row_ids[row]
        self._update_count()
        self._set_dirty(True)

    def _update_count(self, *_):
        total = self.table.rowCount()
        active = sum(
            1 for r in range(total)
            if self.table.cellWidget(r, COL_ON) and self.table.cellWidget(r, COL_ON).findChild(QCheckBox).isChecked()
        )
        text = f"{active} / {total} İHA etkin"
        if active > MANY_VEHICLES:
            text += f"  ·  ⚠️ {MANY_VEHICLES}'ten fazla araç laptopta simülasyonu yavaşlatabilir"
        self.count_label.setText(text)

    def _mark_dirty(self, *_):
        if not getattr(self, "_loading", False):
            self._set_dirty(True)

    def _set_dirty(self, dirty: bool) -> None:
        self.dirty = dirty
        self.dirty_label.setText("● Kaydedilmemiş değişiklikler var" if dirty else "")

    def save(self) -> None:
        self.fleet = self._read_form()
        try:
            save_fleet(self.fleet)
        except OSError as e:
            QMessageBox.critical(self, "Kaydedilemedi", str(e))
            return
        self._set_dirty(False)
        self.apply()
        self.message.emit("Filo kaydedildi. Çalışan araçlar yeni ayarları restart sonrası kullanır.")

    def apply(self) -> None:
        """Filoyu ve ana ayarları (genel hazırlık, temizlik komutu) yeniden modüllere çevirir."""
        self.runner.set_config(build_modules(self.fleet, self.main_runner.cfg))
        self.flight.rebuild()

    # --- çalıştırma -------------------------------------------------------------------

    def _start_fleet(self) -> None:
        if self.dirty:
            if QMessageBox.question(self, "Filo", "Kaydedilmemiş değişiklikler var. Kaydedip başlatılsın mı?") != QMessageBox.Yes:
                return
            self.save()
        if not self.fleet.active():
            QMessageBox.information(self, "Filo", "Etkin İHA yok. 'Filo Düzeni' sekmesinden ekleyin.")
            return
        busy = [self.main_runner.cfg.find(mid).name for mid, p in self.main_runner.procs.items()
                if p.is_alive() and self.main_runner.cfg.find(mid)]
        if busy:
            answer = QMessageBox.question(
                self, "Çakışma olabilir",
                "Kontrol Paneli'nde çalışan modüller var:\n• " + "\n• ".join(busy)
                + "\n\nTek araçlık PX4 SITL ya da ikinci bir Agent filo ile çakışır. Önce bunlar durdurulsun mu?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if answer == QMessageBox.Cancel:
                return
            if answer == QMessageBox.Yes:
                self.main_runner.stop_all()
                self.message.emit("Kontrol Paneli modülleri durduruluyor, ardından filo başlayacak…")
                self._start_when_main_stopped(60)
                return
        self.runner.start_all()

    def _start_when_main_stopped(self, tries_left: int) -> None:
        # Agent portu (8888) ve Gazebo serbest kalmadan filo başlamasın.
        if not self.main_runner.any_alive():
            self.runner.start_all()
        elif tries_left > 0:
            QTimer.singleShot(500, lambda: self._start_when_main_stopped(tries_left - 1))
        else:
            self.message.emit("Kontrol Paneli modülleri 30 sn içinde kapanmadı; filo başlatılmadı.")
