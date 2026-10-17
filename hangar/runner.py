"""Modül tanımlarını çalışan süreçlerle eşler; toplu başlatma sırasını yönetir."""
from PySide6.QtCore import QObject, QTimer, Signal

from .config import LauncherConfig, build_script
from .process import ManagedProcess, State, child_env

SYSTEM_ID = "__system__"


class ModuleRunner(QObject):
    message = Signal(str)
    sequence_running = Signal(bool)

    def __init__(self, cfg: LauncherConfig, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.procs: dict[str, ManagedProcess] = {}
        self.system = ManagedProcess("Sistem", self)
        self._queue: list[str] = []
        self._waiting_for: str | None = None
        self._seq_gen = 0

    # --- modül başına işlemler -------------------------------------------------

    def proc(self, module_id: str) -> ManagedProcess:
        if module_id == SYSTEM_ID:
            return self.system
        if module_id not in self.procs:
            module = self.cfg.find(module_id)
            p = ManagedProcess(module.name if module else module_id, self)
            p.ready.connect(lambda mid=module_id: self._on_ready(mid))
            p.state_changed.connect(lambda state, mid=module_id: self._on_state(mid, state))
            self.procs[module_id] = p
        return self.procs[module_id]

    def set_config(self, cfg: LauncherConfig) -> None:
        self.cfg = cfg
        for mid, p in list(self.procs.items()):
            module = cfg.find(mid)
            if module is None:
                p.stop()
            else:
                p.name = module.name

    def _start_kwargs(self, module_id: str) -> dict:
        module = self.cfg.find(module_id)
        return {
            "script": build_script(self.cfg, module),
            "env": child_env(module.env),
            "ready_pattern": module.ready_pattern,
        }

    def start(self, module_id: str) -> None:
        module = self.cfg.find(module_id)
        if module is None:
            return
        if not module.command.strip():
            self.message.emit(f"'{module.name}' için komut tanımlı değil.")
            return
        self.proc(module_id).start(**self._start_kwargs(module_id))

    def stop(self, module_id: str) -> None:
        module = self.cfg.find(module_id)
        if module is None:
            return
        self.proc(module_id).stop(module.stop_timeout, module.stop_command)

    def restart(self, module_id: str) -> None:
        module = self.cfg.find(module_id)
        if module is None or not module.command.strip():
            return
        p = self.proc(module_id)
        kwargs = self._start_kwargs(module_id)
        p.output.emit("[hangar] Yeniden başlatılıyor…")
        p.stop(module.stop_timeout, module.stop_command, then=lambda: p.start(**kwargs))

    def any_alive(self) -> bool:
        return any(p.is_alive() for p in self.procs.values()) or self.system.is_alive()

    def run_cleanup(self) -> None:
        cmd = self.cfg.cleanup_command.strip()
        if not cmd:
            self.message.emit("Temizlik komutu tanımlı değil (Modüller sayfası > Genel ayarlar).")
            return
        self.system.start(cmd, child_env())

    # --- toplu başlat / durdur ---------------------------------------------------

    def start_all(self) -> None:
        self.cancel_sequence()
        self._queue = [m.id for m in self.cfg.modules if m.start_all and m.command.strip()]
        if not self._queue:
            self.message.emit("'Tümünü Başlat'a dahil modül yok.")
            return
        self.sequence_running.emit(True)
        self._launch_next(self._seq_gen)

    def cancel_sequence(self) -> None:
        self._seq_gen += 1
        self._queue = []
        self._waiting_for = None
        self.sequence_running.emit(False)

    def stop_all(self) -> None:
        self.cancel_sequence()
        for module in reversed(self.cfg.modules):
            if module.id in self.procs and self.procs[module.id].is_alive():
                self.stop(module.id)

    def _launch_next(self, gen: int) -> None:
        if gen != self._seq_gen:
            return
        if not self._queue:
            self.message.emit("Tüm modüller başlatıldı.")
            self.sequence_running.emit(False)
            return
        mid = self._queue.pop(0)
        module = self.cfg.find(mid)
        if module is None:
            self._launch_next(gen)
            return
        p = self.proc(mid)
        if not p.is_alive():
            self.start(mid)
            if not p.is_alive():
                self.message.emit(f"'{module.name}' başlatılamadı, sıra durduruldu.")
                self.cancel_sequence()
                return
        if module.ready_pattern and not p.is_ready:
            self.message.emit(f"'{module.name}' hazır olması bekleniyor…")
            self._waiting_for = mid
            QTimer.singleShot(int(module.ready_timeout * 1000), lambda: self._on_ready_timeout(gen, mid))
        else:
            self.message.emit(f"'{module.name}' başlatıldı.")
            QTimer.singleShot(int(module.start_delay * 1000), lambda: self._launch_next(gen))

    def _on_ready(self, mid: str) -> None:
        if self._waiting_for != mid:
            return
        self._waiting_for = None
        module = self.cfg.find(mid)
        self.message.emit(f"'{module.name}' hazır.")
        gen = self._seq_gen
        QTimer.singleShot(int(module.start_delay * 1000), lambda: self._launch_next(gen))

    def _on_ready_timeout(self, gen: int, mid: str) -> None:
        if gen != self._seq_gen or self._waiting_for != mid:
            return
        self._waiting_for = None
        module = self.cfg.find(mid)
        self.message.emit(f"'{module.name}' {module.ready_timeout:.0f} sn içinde hazır olmadı, devam ediliyor.")
        self._launch_next(gen)

    def _on_state(self, mid: str, state: str) -> None:
        if self._waiting_for == mid and state in (State.CRASHED.value, State.STOPPED.value):
            module = self.cfg.find(mid)
            self.message.emit(f"'{module.name}' hazır olmadan kapandı, toplu başlatma durduruldu.")
            self.cancel_sequence()
