"""Modül / makro ekleme ve düzenleme sayfası."""
import copy
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QVBoxLayout,
    QWidget,
)

from ..config import LauncherConfig, Module, load_config, save_config


def _text_box(placeholder: str, height: int = 70) -> QPlainTextEdit:
    box = QPlainTextEdit()
    box.setObjectName("Log")
    box.setPlaceholderText(placeholder)
    box.setFixedHeight(height)
    return box


def _seconds(maximum: float = 3600) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(0, maximum)
    box.setDecimals(1)
    box.setSuffix(" sn")
    return box


class ModuleEditorPage(QWidget):
    saved = Signal(object)  # LauncherConfig

    def __init__(self, cfg: LauncherConfig, parent=None):
        super().__init__(parent)
        self.cfg = copy.deepcopy(cfg)
        self._current: int = -1
        self._loading = False

        title = QLabel("Modüller")
        title.setObjectName("PageTitle")
        self.dirty_label = QLabel("")
        self.dirty_label.setObjectName("Muted")
        btn_import = QPushButton("İçe Aktar…")
        btn_export = QPushButton("Dışa Aktar…")
        btn_import.clicked.connect(self._import)
        btn_export.clicked.connect(self._export)
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setObjectName("Primary")
        self.btn_save.clicked.connect(self.save)
        top = QHBoxLayout()
        top.addWidget(title)
        top.addSpacing(12)
        top.addWidget(self.dirty_label)
        top.addStretch()
        top.addWidget(btn_import)
        top.addWidget(btn_export)
        top.addWidget(self.btn_save)

        # --- sol: liste ---
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_row_changed)
        btn_new = QPushButton("+ Yeni")
        btn_dup = QPushButton("Kopyala")
        btn_del = QPushButton("Sil")
        btn_up = QPushButton("↑")
        btn_down = QPushButton("↓")
        btn_new.clicked.connect(self._new)
        btn_dup.clicked.connect(self._duplicate)
        btn_del.clicked.connect(self._delete)
        btn_up.clicked.connect(lambda: self._move(-1))
        btn_down.clicked.connect(lambda: self._move(1))
        list_buttons = QHBoxLayout()
        for b in (btn_new, btn_dup, btn_del, btn_up, btn_down):
            list_buttons.addWidget(b)
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.addWidget(self.list, 1)
        left_lay.addLayout(list_buttons)

        # --- sağ: form ---
        self.f_name = QLineEdit()
        self.f_desc = QLineEdit()
        self.f_workdir = QLineEdit()
        btn_browse = QPushButton("…")
        btn_browse.setFixedWidth(36)
        btn_browse.clicked.connect(self._browse_workdir)
        workdir_row = QHBoxLayout()
        workdir_row.addWidget(self.f_workdir, 1)
        workdir_row.addWidget(btn_browse)
        self.f_use_global = QCheckBox("Genel hazırlık komutlarını da çalıştır (ör. ROS 2 source)")
        self.f_setup = _text_box("Her satır ayrı bir hazırlık komutu\nsource ~/iha_ws/install/setup.bash")
        self.f_command = _text_box("ros2 launch paket dosya.launch.py", 90)
        self.f_env = _text_box("ANAHTAR=DEĞER (her satıra bir tane)\nPX4_GZ_WORLD=default", 60)
        self.f_ready = QLineEdit()
        self.f_ready.setPlaceholderText("Regex, ör. Ready for takeoff (boş: başlar başlamaz hazır)")
        self.f_ready_timeout = _seconds()
        self.f_start_delay = _seconds()
        self.f_stop_timeout = _seconds(600)
        self.f_stop_cmd = QLineEdit()
        self.f_stop_cmd.setPlaceholderText("Durdurduktan sonra çalışacak ek temizlik komutu (opsiyonel)")
        self.f_start_all = QCheckBox("'Tümünü Başlat'a dahil et")

        form = QFormLayout()
        form.addRow("Ad", self.f_name)
        form.addRow("Açıklama", self.f_desc)
        form.addRow("Çalışma klasörü", workdir_row)
        form.addRow("", self.f_use_global)
        form.addRow("Hazırlık komutları", self.f_setup)
        form.addRow("Komut", self.f_command)
        form.addRow("Ortam değişkenleri", self.f_env)
        form.addRow("Hazır deseni", self.f_ready)
        form.addRow("Hazır bekleme sınırı", self.f_ready_timeout)
        form.addRow("Sonrasında bekle", self.f_start_delay)
        form.addRow("Kapanma süresi", self.f_stop_timeout)
        form.addRow("Durdurma sonrası komut", self.f_stop_cmd)
        form.addRow("", self.f_start_all)
        self.form_box = QGroupBox("Modül")
        self.form_box.setLayout(form)

        self.g_setup = _text_box("source /opt/ros/humble/setup.bash", 60)
        self.g_cleanup = _text_box("pkill -9 -f '[g]z sim'", 90)
        gform = QFormLayout()
        gform.addRow("Genel hazırlık\n(tüm modüller)", self.g_setup)
        gform.addRow("Artık temizleme\nkomutu", self.g_cleanup)
        global_box = QGroupBox("Genel ayarlar")
        global_box.setLayout(gform)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.addWidget(self.form_box)
        right_lay.addWidget(global_box)
        right_lay.addStretch()

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(splitter, 1)

        for w in (self.f_name, self.f_desc, self.f_workdir, self.f_ready, self.f_stop_cmd):
            w.textEdited.connect(self._mark_dirty)
        self.f_name.textEdited.connect(self._rename_current)
        for w in (self.f_setup, self.f_command, self.f_env, self.g_setup, self.g_cleanup):
            w.textChanged.connect(self._mark_dirty)
        for w in (self.f_ready_timeout, self.f_start_delay, self.f_stop_timeout):
            w.valueChanged.connect(self._mark_dirty)
        for w in (self.f_use_global, self.f_start_all):
            w.toggled.connect(self._mark_dirty)

        self._load_cfg(self.cfg, dirty=False)

    # --- form <-> model ----------------------------------------------------------

    def _load_cfg(self, cfg: LauncherConfig, dirty: bool) -> None:
        self._loading = True
        self.cfg = cfg
        self._current = -1
        self.list.clear()
        for m in cfg.modules:
            self.list.addItem(m.name)
        self.g_setup.setPlainText("\n".join(cfg.global_setup))
        self.g_cleanup.setPlainText(cfg.cleanup_command)
        self._loading = False
        self.list.setCurrentRow(0 if cfg.modules else -1)
        self._on_row_changed(self.list.currentRow())
        self._set_dirty(dirty)

    def _fill_form(self, m: Module | None) -> None:
        self._loading = True
        self.form_box.setEnabled(m is not None)
        m = m or Module(name="")
        self.f_name.setText(m.name)
        self.f_desc.setText(m.description)
        self.f_workdir.setText(m.workdir)
        self.f_use_global.setChecked(m.use_global_setup)
        self.f_setup.setPlainText("\n".join(m.setup))
        self.f_command.setPlainText(m.command)
        self.f_env.setPlainText("\n".join(f"{k}={v}" for k, v in m.env.items()))
        self.f_ready.setText(m.ready_pattern)
        self.f_ready_timeout.setValue(m.ready_timeout)
        self.f_start_delay.setValue(m.start_delay)
        self.f_stop_timeout.setValue(m.stop_timeout)
        self.f_stop_cmd.setText(m.stop_command)
        self.f_start_all.setChecked(m.start_all)
        self._loading = False

    def _commit_form(self) -> None:
        self.cfg.global_setup = [l for l in self.g_setup.toPlainText().splitlines() if l.strip()]
        self.cfg.cleanup_command = self.g_cleanup.toPlainText()
        if not (0 <= self._current < len(self.cfg.modules)):
            return
        m = self.cfg.modules[self._current]
        m.name = self.f_name.text().strip() or "İsimsiz"
        m.description = self.f_desc.text().strip()
        m.workdir = self.f_workdir.text().strip() or "~"
        m.use_global_setup = self.f_use_global.isChecked()
        m.setup = [l for l in self.f_setup.toPlainText().splitlines() if l.strip()]
        m.command = self.f_command.toPlainText().strip()
        env = {}
        for line in self.f_env.toPlainText().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                if k.strip():
                    env[k.strip()] = v.strip()
        m.env = env
        m.ready_pattern = self.f_ready.text().strip()
        m.ready_timeout = self.f_ready_timeout.value()
        m.start_delay = self.f_start_delay.value()
        m.stop_timeout = self.f_stop_timeout.value()
        m.stop_command = self.f_stop_cmd.text().strip()
        m.start_all = self.f_start_all.isChecked()

    def _on_row_changed(self, row: int) -> None:
        if self._loading:
            return
        if self._current != row:
            self._commit_form()
        self._current = row
        self._fill_form(self.cfg.modules[row] if 0 <= row < len(self.cfg.modules) else None)

    def _rename_current(self, text: str) -> None:
        item = self.list.item(self._current)
        if item:
            item.setText(text or "İsimsiz")

    def _mark_dirty(self, *_):
        if not self._loading:
            self._set_dirty(True)

    def _set_dirty(self, dirty: bool) -> None:
        self.dirty = dirty
        self.dirty_label.setText("● Kaydedilmemiş değişiklikler var" if dirty else "")

    # --- liste işlemleri ---------------------------------------------------------

    def _new(self) -> None:
        self._commit_form()
        self.cfg.modules.append(Module(name="Yeni Modül", start_all=False))
        self.list.addItem("Yeni Modül")
        self.list.setCurrentRow(len(self.cfg.modules) - 1)
        self.f_name.setFocus()
        self.f_name.selectAll()
        self._set_dirty(True)

    def _duplicate(self) -> None:
        if self._current < 0:
            return
        self._commit_form()
        src = self.cfg.modules[self._current]
        dup = Module.from_dict({**copy.deepcopy(src.to_dict()), "id": Module().id, "name": src.name + " (kopya)"})
        self.cfg.modules.insert(self._current + 1, dup)
        self.list.insertItem(self._current + 1, dup.name)
        self.list.setCurrentRow(self._current + 1)
        self._set_dirty(True)

    def _delete(self) -> None:
        row = self._current
        if row < 0:
            return
        name = self.cfg.modules[row].name
        if QMessageBox.question(self, "Sil", f"'{name}' silinsin mi?") != QMessageBox.Yes:
            return
        self._loading = True
        del self.cfg.modules[row]
        self.list.takeItem(row)
        self._loading = False
        self._current = -1
        new_row = min(row, len(self.cfg.modules) - 1)
        self.list.setCurrentRow(new_row)
        self._on_row_changed(new_row)
        self._set_dirty(True)

    def _move(self, delta: int) -> None:
        row = self._current
        target = row + delta
        if row < 0 or not (0 <= target < len(self.cfg.modules)):
            return
        self._commit_form()
        mods = self.cfg.modules
        mods[row], mods[target] = mods[target], mods[row]
        self._loading = True
        item = self.list.takeItem(row)
        self.list.insertItem(target, item)
        self.list.setCurrentRow(target)
        self._loading = False
        self._current = target
        self._set_dirty(True)

    def _browse_workdir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Çalışma klasörü", self.f_workdir.text())
        if path:
            self.f_workdir.setText(path)
            self._mark_dirty()

    # --- kaydet / içe-dışa aktar -------------------------------------------------

    def save(self) -> None:
        self._commit_form()
        try:
            save_config(self.cfg)
        except OSError as e:
            QMessageBox.critical(self, "Kaydedilemedi", str(e))
            return
        self._set_dirty(False)
        self.saved.emit(copy.deepcopy(self.cfg))

    def _export(self) -> None:
        self._commit_form()
        path, _ = QFileDialog.getSaveFileName(self, "Dışa aktar", "modules.yaml", "YAML (*.yaml *.yml)")
        if path:
            save_config(self.cfg, Path(path))

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "İçe aktar", "", "YAML (*.yaml *.yml)")
        if not path:
            return
        try:
            cfg = load_config(Path(path))
        except Exception as e:  # bozuk dosya kullanıcıya gösterilsin
            QMessageBox.critical(self, "İçe aktarılamadı", str(e))
            return
        self._load_cfg(cfg, dirty=True)
