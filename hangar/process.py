"""Tek bir komutun süreç grubu olarak başlatılması, izlenmesi ve durdurulması.

Gazebo, PX4 ve ros2 launch arka planda çok sayıda alt süreç açar. Sadece ana
süreci öldürmek gzserver gibi süreçleri ortada bırakır. Bu yüzden her modül
kendi oturumunda (setsid) başlatılır ve durdururken tüm gruba sırasıyla
SIGINT -> SIGTERM -> SIGKILL gönderilir.
"""
import os
import re
import signal
import subprocess
import threading
import time
from enum import Enum

from PySide6.QtCore import QObject, Signal

from .paths import APP_DIR

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Za-z0-9]")

# Uygulamanın kendi Qt ayarları, alt süreçlerdeki Qt uygulamalarını (QGC, gz gui) bozmasın.
_QT_ENV_KEYS = ("QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH", "QML2_IMPORT_PATH", "QML_IMPORT_PATH")


class State(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    CRASHED = "crashed"


def child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    for key in _QT_ENV_KEYS:
        if "PySide6" in env.get(key, ""):
            env.pop(key)
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("RCUTILS_LOGGING_BUFFERED_STREAM", "1")
    env.setdefault("RCUTILS_COLORIZED_OUTPUT", "0")
    # Modül komutları repodaki dosyalara (ör. sim/px4) $HANGAR_DIR ile ulaşır.
    env.setdefault("HANGAR_DIR", str(APP_DIR))
    for key, value in (extra or {}).items():
        env[key] = os.path.expandvars(os.path.expanduser(value))
    return env


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _wait_group(pgid: int, timeout: float) -> bool:
    """Grup kapanırsa True döner."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _group_alive(pgid):
            return True
        time.sleep(0.1)
    return not _group_alive(pgid)


class ManagedProcess(QObject):
    output = Signal(str)
    state_changed = Signal(str)
    ready = Signal()
    finished = Signal(int)

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name
        self._lock = threading.RLock()
        self._proc: subprocess.Popen | None = None
        self._pgid: int | None = None
        self._state = State.STOPPED
        self._stop_requested = False
        self._reader_done = threading.Event()
        self._reader_done.set()
        self._ready_re: re.Pattern | None = None
        self.is_ready = False
        self.started_at: float | None = None
        self.last_exit_code: int | None = None

    @property
    def state(self) -> State:
        return self._state

    def is_alive(self) -> bool:
        return self._state in (State.STARTING, State.RUNNING, State.STOPPING)

    def _set_state(self, state: State) -> None:
        self._state = state
        self.state_changed.emit(state.value)

    def _log(self, text: str) -> None:
        self.output.emit(f"[hangar] {text}")

    def start(self, script: str, env: dict[str, str], cwd: str | None = None, ready_pattern: str = "") -> bool:
        with self._lock:
            if self.is_alive():
                return False
            self._stop_requested = False
            self.is_ready = False
            self._ready_re = None
            if ready_pattern:
                try:
                    self._ready_re = re.compile(ready_pattern)
                except re.error as e:
                    self._log(f"Geçersiz hazır deseni ({e}), yok sayılıyor.")
            self._set_state(State.STARTING)
            try:
                proc = subprocess.Popen(
                    ["bash", "-c", script],
                    cwd=cwd,
                    env=env,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    bufsize=0,
                )
            except OSError as e:
                self._log(f"Başlatılamadı: {e}")
                self._set_state(State.CRASHED)
                return False
            self._proc = proc
            self._pgid = proc.pid
            self.started_at = time.time()
            self.last_exit_code = None
            self._reader_done.clear()
            self._log(f"Başlatıldı (PID {proc.pid})")
            if self._ready_re is None:
                self._set_state(State.RUNNING)
            threading.Thread(target=self._read_loop, args=(proc,), daemon=True).start()
            return True

    def _emit_lines(self, lines: list[bytes]) -> None:
        text = "\n".join(ANSI_RE.sub("", line.decode("utf-8", "replace")) for line in lines)
        if self._ready_re and not self.is_ready and self._ready_re.search(text):
            self.is_ready = True
            if self._state == State.STARTING:
                self._set_state(State.RUNNING)
            self.output.emit(text)
            self.ready.emit()
            return
        self.output.emit(text)

    def _read_loop(self, proc: subprocess.Popen) -> None:
        fd = proc.stdout.fileno()
        pending = b""
        while True:
            try:
                data = os.read(fd, 65536)
            except OSError:
                break
            if not data:
                break
            pending += data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            *lines, pending = pending.split(b"\n")
            if lines:
                self._emit_lines(lines)
            if len(pending) > 65536:
                self._emit_lines([pending])
                pending = b""
        if pending:
            self._emit_lines([pending])
        rc = proc.wait()
        pgid = proc.pid
        # Ana kabuk bitse de gruptaki başka süreçler yaşıyorsa modül hâlâ çalışıyor sayılır.
        warned = False
        while not self._stop_requested and _group_alive(pgid):
            if not warned:
                self._log("Ana komut bitti ama gruptaki süreçler hâlâ çalışıyor.")
                warned = True
            time.sleep(1)
        with self._lock:
            self.last_exit_code = rc
            self._proc = None
            stop_requested = self._stop_requested
            if not stop_requested:
                self._pgid = None
                self.started_at = None
        self._reader_done.set()
        if not stop_requested:
            self._log(f"Süreç sonlandı (çıkış kodu {rc})")
            self._set_state(State.STOPPED if rc == 0 else State.CRASHED)
        self.finished.emit(rc)

    def stop(self, timeout: float = 10.0, stop_command: str = "", then=None) -> None:
        with self._lock:
            if self._pgid is None or self._state in (State.STOPPED, State.CRASHED):
                if then:
                    threading.Thread(target=then, daemon=True).start()
                return
            if self._state == State.STOPPING:
                return
            self._stop_requested = True
            pgid = self._pgid
            self._set_state(State.STOPPING)
        threading.Thread(target=self._stop_worker, args=(pgid, timeout, stop_command, then), daemon=True).start()

    def _stop_worker(self, pgid: int, timeout: float, stop_command: str, then) -> None:
        for sig, wait in ((signal.SIGINT, timeout), (signal.SIGTERM, 3.0), (signal.SIGKILL, 2.0)):
            if not _group_alive(pgid):
                break
            self._log(f"{sig.name} gönderiliyor…")
            try:
                os.killpg(pgid, sig)
            except ProcessLookupError:
                break
            if _wait_group(pgid, wait):
                break
        else:
            self._log("UYARI: Süreç grubu SIGKILL sonrası da kapanmadı.")
        self._reader_done.wait(5)
        if stop_command.strip():
            self._log("Temizlik komutu çalıştırılıyor…")
            try:
                res = subprocess.run(
                    ["bash", "-c", stop_command], env=child_env(), stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
                )
                if res.stdout:
                    self.output.emit(ANSI_RE.sub("", res.stdout.decode("utf-8", "replace")).rstrip())
            except subprocess.TimeoutExpired:
                self._log("Temizlik komutu 30 sn içinde bitmedi.")
        with self._lock:
            self._pgid = None
            self.started_at = None
        self._log("Durduruldu.")
        self._set_state(State.STOPPED)
        if then:
            then()

    def send_input(self, text: str) -> bool:
        with self._lock:
            proc = self._proc
        if proc is None or proc.stdin is None:
            return False
        try:
            proc.stdin.write((text + "\n").encode())
            proc.stdin.flush()
            return True
        except (BrokenPipeError, OSError, ValueError):
            return False
