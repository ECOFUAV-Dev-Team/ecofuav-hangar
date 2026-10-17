"""Modül tanımlarının (modules.yaml) okunması ve yazılması."""
import shlex
import shutil
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

import yaml

from .paths import DEFAULT_MODULES_FILE, USER_MODULES_FILE, expand


@dataclass
class Module:
    """Ana sayfada kart olarak görünen, başlatılıp durdurulabilen bir komut."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = "Yeni Modül"
    description: str = ""
    workdir: str = "~"
    use_global_setup: bool = True
    setup: list[str] = field(default_factory=list)
    command: str = ""
    env: dict[str, str] = field(default_factory=dict)
    # Çıktıda bu regex görülünce modül "hazır" sayılır (ör. PX4: "Ready for takeoff").
    ready_pattern: str = ""
    ready_timeout: float = 60.0
    # "Tümünü Başlat" sırasında bu modülden sonra beklenecek ek süre (sn).
    start_delay: float = 0.0
    # Durdururken SIGINT'ten sonra SIGTERM'e geçmeden önce beklenecek süre (sn).
    stop_timeout: float = 10.0
    # Süreç grubu kapandıktan sonra çalışacak ek temizlik komutu.
    stop_command: str = ""
    start_all: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Module":
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in (data or {}).items() if k in known}
        if isinstance(kwargs.get("setup"), str):
            kwargs["setup"] = [line for line in kwargs["setup"].splitlines() if line.strip()]
        kwargs["setup"] = [str(s) for s in kwargs.get("setup") or []]
        kwargs["env"] = {str(k): str(v) for k, v in (kwargs.get("env") or {}).items()}
        for key in ("ready_timeout", "start_delay", "stop_timeout"):
            if key in kwargs:
                kwargs[key] = float(kwargs[key])
        for key in ("name", "description", "workdir", "command", "ready_pattern", "stop_command"):
            if kwargs.get(key) is None:
                kwargs.pop(key, None)
            elif key in kwargs:
                kwargs[key] = str(kwargs[key])
        return cls(**kwargs)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LauncherConfig:
    global_setup: list[str] = field(default_factory=list)
    cleanup_command: str = ""
    modules: list[Module] = field(default_factory=list)

    def find(self, module_id: str) -> Module | None:
        return next((m for m in self.modules if m.id == module_id), None)

    @classmethod
    def from_dict(cls, data: dict) -> "LauncherConfig":
        data = data or {}
        modules = [Module.from_dict(m) for m in data.get("modules") or []]
        seen = set()
        for m in modules:  # elle düzenlenmiş dosyada tekrar eden id olmasın
            if m.id in seen:
                m.id = uuid.uuid4().hex[:8]
            seen.add(m.id)
        return cls(
            global_setup=[str(s) for s in data.get("global_setup") or []],
            cleanup_command=str(data.get("cleanup_command") or ""),
            modules=modules,
        )

    def to_dict(self) -> dict:
        return {
            "global_setup": list(self.global_setup),
            "cleanup_command": self.cleanup_command,
            "modules": [m.to_dict() for m in self.modules],
        }


class _Dumper(yaml.SafeDumper):
    pass


def _str_representer(dumper, value: str):
    # Çok satırlı komutlar YAML'da okunaklı "|" bloğu olarak yazılsın.
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_Dumper.add_representer(str, _str_representer)


def load_config(path: Path = USER_MODULES_FILE) -> LauncherConfig:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(DEFAULT_MODULES_FILE, path)
    with open(path, encoding="utf-8") as f:
        return LauncherConfig.from_dict(yaml.safe_load(f))


def save_config(cfg: LauncherConfig, path: Path = USER_MODULES_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.dump(cfg.to_dict(), f, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=1000)
    tmp.replace(path)


def build_script(cfg: LauncherConfig, module: Module) -> str:
    """Modülü çalıştıracak bash betiğini oluşturur."""
    workdir = expand(module.workdir or "~")
    lines = [
        f"cd {shlex.quote(workdir)} || {{ echo {shlex.quote('[hangar] Çalışma klasörü bulunamadı: ' + workdir)}; exit 1; }}"
    ]
    setup = (cfg.global_setup if module.use_global_setup else []) + module.setup
    for step in setup:
        if not step.strip():
            continue
        msg = shlex.quote(f"[hangar] Hazırlık komutu başarısız: {step}")
        lines.append(f"{step} || {{ echo {msg}; exit 1; }}")
    lines.append(module.command)
    return "\n".join(lines) + "\n"
